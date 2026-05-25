"""SQLite 词库索引：构建与前缀/包含检索。"""
from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

from .categories import (
    build_tree_from_db,
    insert_categories_from_manifest,
    resolve_internal_category_id,
    source_key_for_manifest,
)
from .tag_weight import lookup_key_for_vocabulary
from .manifest_source import iter_manifest_prompts, iter_user_prompts, load_manifest
from .user_store import (
    deleted_set,
    fingerprint as user_fingerprint,
    load as load_user_data,
    migrate_user_category_ids,
    save as save_user_data,
)

SCHEMA_VERSION = "3"

_build_lock = threading.Lock()
_ready = False


def _fingerprint(path: Path) -> str:
    st = path.stat()
    return f"{int(st.st_mtime)}:{st.st_size}"


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    _ensure_categories_schema(conn)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            parent_id INTEGER,
            sort_order INTEGER DEFAULT 0,
            path_label TEXT,
            source_key TEXT NOT NULL DEFAULT 'default',
            source_category_id TEXT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_categories_source
            ON categories(source_key, source_category_id);
        CREATE TABLE IF NOT EXISTS vocab (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            insert_text TEXT NOT NULL,
            label TEXT NOT NULL,
            category TEXT,
            source_id TEXT NOT NULL,
            insert_lower TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_vocab_insert_lower ON vocab(insert_lower);
        CREATE INDEX IF NOT EXISTS idx_vocab_label ON vocab(label);
        """
    )
    _ensure_vocab_columns(conn)
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_vocab_category ON vocab(category_id);
        CREATE INDEX IF NOT EXISTS idx_vocab_cat_lower ON vocab(category_id, insert_lower);
        """
    )


def _ensure_categories_schema(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='categories'"
    ).fetchone()
    sql = (row["sql"] or "") if row else ""
    if row and "AUTOINCREMENT" not in sql.upper():
        conn.execute("DROP TABLE IF EXISTS categories")


def _category_path_label(conn: sqlite3.Connection, category_id: str) -> str:
    cid = resolve_internal_category_id(conn, category_id)
    if not cid or not cid.isdigit():
        return ""
    row = conn.execute(
        "SELECT path_label, name FROM categories WHERE id = ?",
        (int(cid),),
    ).fetchone()
    if not row:
        return ""
    return (row["path_label"] or row["name"] or "").strip()


def _remapped_deleted_set(conn: sqlite3.Connection, user_data: dict) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for item in user_data.get("deleted") or []:
        if not isinstance(item, dict):
            continue
        cid = resolve_internal_category_id(conn, item.get("categoryId", ""))
        out.add(deletion_key(cid, item.get("value", "")))
    return out


def _ensure_vocab_columns(conn: sqlite3.Connection) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(vocab)").fetchall()}
    if "category_id" not in cols:
        conn.execute("ALTER TABLE vocab ADD COLUMN category_id TEXT")


def build_index(
    manifest_path: Path,
    db_path: Path,
    *,
    user_path: Path | None = None,
) -> int:
    """从 manifest + 用户覆盖全量重建索引，返回写入条数。"""
    manifest_path = manifest_path.resolve()
    if not manifest_path.is_file():
        raise FileNotFoundError(f"manifest 不存在: {manifest_path}")

    user_data = load_user_data(user_path) if user_path else load_user_data(Path())
    ufp = (
        user_fingerprint(user_path.resolve())
        if user_path and user_path.is_file()
        else "missing"
    )

    manifest = load_manifest(manifest_path)
    source_key = source_key_for_manifest(manifest_path)

    conn = _connect(db_path)
    try:
        _init_schema(conn)
        conn.execute("DELETE FROM vocab")
        conn.execute("DELETE FROM categories")

        id_map, root_internal_id, root_name = insert_categories_from_manifest(
            conn, manifest, source_key
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            ("root_category_id", root_internal_id),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            ("root_category_name", root_name),
        )

        user_migrated = migrate_user_category_ids(user_data, conn)
        blocked = _remapped_deleted_set(conn, user_data)
        batch: list[tuple] = []
        count = 0
        t0 = time.perf_counter()

        def flush() -> None:
            nonlocal count
            if not batch:
                return
            conn.executemany(
                """
                INSERT INTO vocab (
                    insert_text, label, category, category_id, source_id, insert_lower
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                batch,
            )
            count += len(batch)
            batch.clear()

        def push(entry: dict) -> None:
            insert_text = entry["insert_text"]
            source_cat_id = entry.get("category_id") or ""
            cat_id = id_map.get(source_cat_id) or source_cat_id
            if deletion_key(cat_id, insert_text) in blocked:
                return
            label = entry["label"]
            category = entry.get("category") or _category_path_label(conn, cat_id)
            batch.append(
                (
                    insert_text,
                    label,
                    category,
                    cat_id,
                    entry.get("source_id") or "manifest",
                    insert_text.lower(),
                )
            )
            if len(batch) >= 5000:
                flush()

        fp = _fingerprint(manifest_path)
        for entry in iter_manifest_prompts(manifest_path):
            push(entry)
        for entry in iter_user_prompts(user_data.get("prompts") or []):
            entry = dict(entry)
            entry["category_id"] = resolve_internal_category_id(
                conn, entry.get("category_id") or ""
            )
            push(entry)

        flush()

        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            ("source_manifest", str(manifest_path)),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            ("source_fingerprint", fp),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            ("user_fingerprint", ufp),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            ("schema_version", SCHEMA_VERSION),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            ("built_at", str(int(time.time()))),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            ("entry_count", str(count)),
        )
        conn.commit()
        elapsed = time.perf_counter() - t0
        print(f"[vocabulary] 索引已构建: {count} 条, {elapsed:.1f}s")
        if user_migrated and user_path:
            save_user_data(user_path, user_data)
            ufp = user_fingerprint(user_path.resolve())
            conn.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                ("user_fingerprint", ufp),
            )
            conn.commit()
        return count
    finally:
        conn.close()


def deletion_key(category_id: str, value: str) -> tuple[str, str]:
    return ((category_id or "").strip(), (value or "").strip().lower())


def needs_rebuild(
    manifest_path: Path,
    db_path: Path,
    *,
    user_path: Path | None = None,
) -> bool:
    if not db_path.is_file():
        return True
    if not manifest_path.is_file():
        return False
    conn = _connect(db_path)
    try:
        _init_schema(conn)
        def _meta(key: str) -> str | None:
            row = conn.execute(
                "SELECT value FROM meta WHERE key = ?", (key,)
            ).fetchone()
            return row["value"] if row else None

        if _meta("schema_version") != SCHEMA_VERSION:
            return True
        if _meta("source_fingerprint") != _fingerprint(manifest_path):
            return True
        expected_user = (
            user_fingerprint(user_path.resolve())
            if user_path and user_path.is_file()
            else "missing"
        )
        if _meta("user_fingerprint") != expected_user:
            return True
        return False
    finally:
        conn.close()


def suggest(
    db_path: Path,
    query: str,
    *,
    limit: int = 12,
) -> list[dict]:
    """按匹配度返回建议列表。"""
    q = query.strip().lower()
    if not q or len(q) > 64:
        return []

    conn = _connect(db_path)
    try:
        like_prefix = f"{q}%"
        like_contains = f"%{q}%"
        rows = conn.execute(
            """
            SELECT insert_text, label, category, category_id, source_id,
                   CASE
                       WHEN insert_lower = ? THEN 100
                       WHEN insert_lower LIKE ? THEN 90
                       WHEN insert_lower LIKE ? THEN 80
                       WHEN label = ? THEN 70
                       WHEN label LIKE ? THEN 60
                       WHEN label LIKE ? THEN 50
                       ELSE 0
                   END AS score
            FROM vocab
            WHERE insert_lower LIKE ? OR label LIKE ?
            ORDER BY score DESC, length(insert_text) ASC
            LIMIT ?
            """,
            (
                q,
                like_prefix,
                like_contains,
                query.strip(),
                f"{query.strip()}%",
                like_contains,
                like_contains,
                like_contains,
                limit,
            ),
        ).fetchall()

        return [
            {
                "insertText": r["insert_text"],
                "label": r["label"],
                "category": r["category"] or None,
                "categoryId": r["category_id"] or None,
                "sourceId": r["source_id"],
                "score": r["score"],
            }
            for r in rows
        ]
    finally:
        conn.close()


def resolve_values(db_path: Path, values: list[str]) -> list[dict]:
    """按 value 精确匹配（不区分大小写），返回 label；未命中 known=False。"""
    if not values:
        return []

    conn = _connect(db_path)
    try:
        # 建立查询键 -> 原始 value 列表（保留用户大小写用于回写）
        key_to_values: dict[str, list[str]] = {}
        unique_keys: list[str] = []
        for raw in values:
            v = (raw or "").strip()
            if not v:
                continue
            k = v.lower()
            if k not in key_to_values:
                key_to_values[k] = []
                unique_keys.append(k)
            key_to_values[k].append(v)

        if not unique_keys:
            return []

        query_keys: list[str] = []
        seen_query: set[str] = set()
        for raw in values:
            v = (raw or "").strip()
            if not v:
                continue
            for key in (v.lower(), lookup_key_for_vocabulary(v).lower()):
                if key and key not in seen_query:
                    seen_query.add(key)
                    query_keys.append(key)

        found: dict[str, dict] = {}
        chunk_size = 400
        for i in range(0, len(query_keys), chunk_size):
            chunk = query_keys[i : i + chunk_size]
            placeholders = ",".join("?" * len(chunk))
            rows = conn.execute(
                f"""
                SELECT insert_text, label, category, insert_lower
                FROM vocab
                WHERE insert_lower IN ({placeholders})
                """,
                chunk,
            ).fetchall()
            for r in rows:
                found[r["insert_lower"]] = {
                    "insertText": r["insert_text"],
                    "label": r["label"] or r["insert_text"],
                    "category": r["category"] or None,
                    "known": True,
                }

        out: list[dict] = []
        for raw in values:
            v = (raw or "").strip()
            if not v:
                continue
            hit = found.get(v.lower()) or found.get(
                lookup_key_for_vocabulary(v).lower()
            )
            if hit:
                out.append({**hit, "value": v})
            else:
                out.append(
                    {
                        "value": v,
                        "insertText": v,
                        "label": "",
                        "category": None,
                        "known": False,
                    }
                )
        return out
    finally:
        conn.close()


def get_stats(db_path: Path) -> dict:
    if not db_path.is_file():
        return {"ready": False, "count": 0}
    conn = _connect(db_path)
    try:
        _init_schema(conn)
        count_row = conn.execute("SELECT value FROM meta WHERE key = ?", ("entry_count",)).fetchone()
        built_row = conn.execute("SELECT value FROM meta WHERE key = ?", ("built_at",)).fetchone()
        src_row = conn.execute("SELECT value FROM meta WHERE key = ?", ("source_manifest",)).fetchone()
        cat_count = conn.execute("SELECT COUNT(*) AS c FROM categories").fetchone()
        return {
            "ready": True,
            "count": int(count_row["value"]) if count_row else 0,
            "categoryCount": int(cat_count["c"]) if cat_count else 0,
            "builtAt": int(built_row["value"]) if built_row else None,
            "sourceManifest": src_row["value"] if src_row else None,
            "schemaVersion": SCHEMA_VERSION,
        }
    finally:
        conn.close()


def get_category_tree(db_path: Path) -> dict:
    conn = _connect(db_path)
    try:
        _init_schema(conn)
        return build_tree_from_db(conn)
    finally:
        conn.close()


def collect_descendant_category_ids(conn: sqlite3.Connection, category_id: str) -> list[str]:
    """分类及其全部子孙分类的内部分 id（含自身）。"""
    root = resolve_internal_category_id(conn, category_id)
    if not root:
        return []
    out: list[str] = []
    stack = [int(root)]
    seen: set[str] = set()
    while stack:
        cur = stack.pop()
        sid = str(cur)
        if sid in seen:
            continue
        seen.add(sid)
        out.append(sid)
        rows = conn.execute(
            "SELECT id FROM categories WHERE parent_id = ?",
            (cur,),
        ).fetchall()
        for r in rows:
            stack.append(int(r["id"]))
    return out


def count_prompts_in_category_subtree(db_path: Path, category_id: str) -> int:
    conn = _connect(db_path)
    try:
        cids = collect_descendant_category_ids(conn, category_id)
        if not cids:
            return 0
        placeholders = ",".join("?" * len(cids))
        row = conn.execute(
            f"SELECT COUNT(*) AS c FROM vocab WHERE category_id IN ({placeholders})",
            cids,
        ).fetchone()
        return int(row["c"]) if row else 0
    finally:
        conn.close()


def list_prompts_in_category(
    db_path: Path,
    category_id: str,
    *,
    q: str = "",
    offset: int = 0,
    limit: int = 80,
) -> dict:
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))
    q = (q or "").strip().lower()

    conn = _connect(db_path)
    try:
        cid = resolve_internal_category_id(conn, category_id)
        if not cid:
            return {"items": [], "total": 0, "offset": offset, "limit": limit}

        cids = collect_descendant_category_ids(conn, cid)
        if not cids:
            return {"items": [], "total": 0, "offset": offset, "limit": limit}

        placeholders = ",".join("?" * len(cids))
        where = f"category_id IN ({placeholders})"
        params: list = list(cids)
        if q:
            where += " AND (insert_lower LIKE ? OR label LIKE ?)"
            like = f"%{q}%"
            params.extend([like, like])

        total_row = conn.execute(
            f"SELECT COUNT(*) AS c FROM vocab WHERE {where}",
            params,
        ).fetchone()
        total = int(total_row["c"]) if total_row else 0

        rows = conn.execute(
            f"""
            SELECT insert_text, label, category, category_id, source_id
            FROM vocab
            WHERE {where}
            ORDER BY insert_lower ASC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()

        items = [
            {
                "value": r["insert_text"],
                "name": r["label"],
                "categoryId": r["category_id"],
                "categoryPath": r["category"] or None,
                "sourceId": r["source_id"],
            }
            for r in rows
        ]
        return {"items": items, "total": total, "offset": offset, "limit": limit}
    finally:
        conn.close()


def insert_vocab_prompt(
    db_path: Path,
    *,
    category_id: str,
    value: str,
    name: str,
    source_id: str = "user",
) -> None:
    v = (value or "").strip()
    cid = (category_id or "").strip()
    if not v or not cid:
        raise ValueError("value 与 categoryId 不能为空")

    conn = _connect(db_path)
    try:
        _init_schema(conn)
        cid = resolve_internal_category_id(conn, category_id)
        path_label = _category_path_label(conn, cid)
        conn.execute(
            "DELETE FROM vocab WHERE category_id = ? AND insert_lower = ?",
            (cid, v.lower()),
        )
        conn.execute(
            """
            INSERT INTO vocab (
                insert_text, label, category, category_id, source_id, insert_lower
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                v,
                (name or v).strip(),
                path_label or "",
                cid,
                source_id,
                v.lower(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def delete_vocab_prompt(db_path: Path, *, category_id: str, value: str) -> bool:
    v = (value or "").strip()
    if not v or not (category_id or "").strip():
        return False
    conn = _connect(db_path)
    try:
        cid = resolve_internal_category_id(conn, category_id)
        cur = conn.execute(
            "DELETE FROM vocab WHERE category_id = ? AND insert_lower = ?",
            (cid, v.lower()),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def vocab_source_for(
    db_path: Path, *, category_id: str, value: str
) -> str | None:
    conn = _connect(db_path)
    try:
        cid = resolve_internal_category_id(conn, category_id)
        row = conn.execute(
            """
            SELECT source_id FROM vocab
            WHERE category_id = ? AND insert_lower = ?
            """,
            (cid, (value or "").strip().lower()),
        ).fetchone()
        return row["source_id"] if row else None
    finally:
        conn.close()
