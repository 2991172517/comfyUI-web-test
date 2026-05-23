"""manifest 分类树构建与数据库内部分类 ID。"""
from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Any


def source_key_for_manifest(manifest_path: Path) -> str:
    """多 manifest 合并时区分来源，避免 source_category_id 冲突。"""
    resolved = str(manifest_path.resolve())
    digest = hashlib.sha256(resolved.encode()).hexdigest()[:10]
    return f"{manifest_path.stem}_{digest}"


def build_category_tree(manifest: dict) -> dict:
    root_id = (manifest.get("rootCategoryId") or "").strip()
    root_name = (manifest.get("rootCategoryName") or "标签库").strip()
    categories = list(manifest.get("categories") or [])

    by_id: dict[str, dict[str, Any]] = {}
    for c in categories:
        cid = (c.get("id") or "").strip()
        if not cid:
            continue
        by_id[cid] = {
            "id": cid,
            "name": (c.get("name") or cid).strip(),
            "parentId": (c.get("parentId") or "").strip(),
            "order": int(c.get("order") or 0),
            "children": [],
        }

    # 根节点可能也在 categories 里
    if root_id and root_id not in by_id:
        by_id[root_id] = {
            "id": root_id,
            "name": root_name,
            "parentId": "root",
            "order": 0,
            "children": [],
        }
    elif root_id and root_id in by_id:
        by_id[root_id]["name"] = root_name or by_id[root_id]["name"]

    child_parent_ids = {root_id, "root"} if root_id else {"root"}

    orphans: list[dict] = []
    for node in by_id.values():
        pid = node["parentId"]
        if pid in child_parent_ids or (root_id and pid == root_id):
            orphans.append(node)
        elif pid in by_id:
            by_id[pid]["children"].append(node)
        else:
            orphans.append(node)

    def sort_nodes(nodes: list[dict]) -> None:
        nodes.sort(key=lambda n: (n.get("order", 0), n.get("name", "")))
        for n in nodes:
            sort_nodes(n["children"])

    if root_id and root_id in by_id:
        root_node = by_id[root_id]
        for node in orphans:
            if node["id"] != root_id:
                root_node["children"].append(node)
        sort_nodes(root_node["children"])
        tree = [root_node]
    else:
        sort_nodes(orphans)
        tree = orphans

    return {
        "rootCategoryId": root_id,
        "rootCategoryName": root_name,
        "tree": tree,
    }


def flatten_tree_paths(tree: list[dict], prefix: str = "") -> dict[str, str]:
    """category_id -> 面包屑路径"""
    out: dict[str, str] = {}

    def walk(nodes: list[dict], path: str) -> None:
        for n in nodes:
            name = n.get("name") or n.get("id") or ""
            cid = n.get("id") or ""
            full = f"{path} / {name}".strip(" /") if path else name
            if cid:
                out[cid] = full
            walk(n.get("children") or [], full)

    walk(tree, prefix)
    return out


def resolve_internal_category_id(conn: sqlite3.Connection, category_id: str) -> str:
    """将 manifest UUID 或内部数字 id 统一解析为 DB 内部分类 id 字符串。"""
    cid = (category_id or "").strip()
    if not cid:
        return ""
    if cid.isdigit():
        row = conn.execute("SELECT id FROM categories WHERE id = ?", (int(cid),)).fetchone()
        if row:
            return str(row["id"])
    row = conn.execute(
        "SELECT id FROM categories WHERE source_category_id = ? ORDER BY id LIMIT 1",
        (cid,),
    ).fetchone()
    if row:
        return str(row["id"])
    return cid


def insert_categories_from_manifest(
    conn: sqlite3.Connection,
    manifest: dict,
    source_key: str,
) -> tuple[dict[str, str], str, str]:
    """
    从 manifest 写入 categories 表，使用 INTEGER AUTOINCREMENT 内部分类 id。
    返回 (manifest分类UUID -> 内部id, 根内部分类id, 根名称)
    """
    root_source_id = (manifest.get("rootCategoryId") or "").strip()
    root_name = (manifest.get("rootCategoryName") or "标签库").strip()
    raw = [c for c in (manifest.get("categories") or []) if (c.get("id") or "").strip()]
    by_source = {(c.get("id") or "").strip(): c for c in raw}

    id_map: dict[str, str] = {}
    root_internal_id: int | None = None

    if root_source_id:
        root_cat = by_source.get(root_source_id)
        root_display = (root_cat.get("name") if root_cat else None) or root_name
        root_order = int(root_cat.get("order") or 0) if root_cat else 0
        cur = conn.execute(
            """
            INSERT INTO categories (
                name, parent_id, sort_order, path_label, source_key, source_category_id
            )
            VALUES (?, NULL, ?, ?, ?, ?)
            """,
            (root_display.strip(), root_order, root_display.strip(), source_key, root_source_id),
        )
        root_internal_id = int(cur.lastrowid)
        id_map[root_source_id] = str(root_internal_id)

    pending = set(by_source.keys()) - {root_source_id}
    while pending:
        progressed = False
        for sid in list(pending):
            c = by_source[sid]
            pid = (c.get("parentId") or "").strip()
            parent_internal: int | None = None
            if pid in ("root", ""):
                parent_internal = root_internal_id
            elif pid == root_source_id:
                parent_internal = root_internal_id
            elif pid in id_map:
                parent_internal = int(id_map[pid])
            else:
                continue
            cur = conn.execute(
                """
                INSERT INTO categories (
                    name, parent_id, sort_order, path_label, source_key, source_category_id
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    (c.get("name") or sid).strip(),
                    parent_internal,
                    int(c.get("order") or 0),
                    "",
                    source_key,
                    sid,
                ),
            )
            id_map[sid] = str(cur.lastrowid)
            pending.remove(sid)
            progressed = True
        if not progressed and pending:
            for sid in list(pending):
                c = by_source[sid]
                cur = conn.execute(
                    """
                    INSERT INTO categories (
                        name, parent_id, sort_order, path_label, source_key, source_category_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        (c.get("name") or sid).strip(),
                        root_internal_id,
                        int(c.get("order") or 0),
                        "",
                        source_key,
                        sid,
                    ),
                )
                id_map[sid] = str(cur.lastrowid)
            pending.clear()

    tree_info = build_tree_from_db(conn)
    path_map = flatten_tree_paths(tree_info["tree"])
    for cid_str, path in path_map.items():
        if cid_str.isdigit():
            conn.execute(
                "UPDATE categories SET path_label = ? WHERE id = ?",
                (path, int(cid_str)),
            )

    return id_map, str(root_internal_id or ""), root_name


def build_tree_from_db(conn: sqlite3.Connection) -> dict:
    """从 categories 表构建前端用分类树（节点 id 为 DB 内部分类 id）。"""
    root_row = conn.execute(
        "SELECT value FROM meta WHERE key = ?", ("root_category_id",)
    ).fetchone()
    name_row = conn.execute(
        "SELECT value FROM meta WHERE key = ?", ("root_category_name",)
    ).fetchone()
    root_id = (root_row["value"] if root_row else "") or ""
    root_name = (name_row["value"] if name_row else "") or "标签库"

    rows = conn.execute(
        """
        SELECT id, name, parent_id, sort_order
        FROM categories
        ORDER BY sort_order, name
        """
    ).fetchall()
    if not rows:
        return {"rootCategoryId": root_id, "rootCategoryName": root_name, "tree": []}

    nodes: dict[str, dict[str, Any]] = {}
    for r in rows:
        nid = str(r["id"])
        nodes[nid] = {
            "id": nid,
            "name": r["name"],
            "parentId": str(r["parent_id"]) if r["parent_id"] is not None else "",
            "order": int(r["sort_order"] or 0),
            "children": [],
        }

    orphans: list[dict[str, Any]] = []
    for r in rows:
        nid = str(r["id"])
        node = nodes[nid]
        pid = r["parent_id"]
        if pid is not None and str(pid) in nodes:
            nodes[str(pid)]["children"].append(node)
        elif nid == root_id:
            continue
        elif root_id and root_id in nodes:
            nodes[root_id]["children"].append(node)
        else:
            orphans.append(node)

    def sort_nodes(node_list: list[dict]) -> None:
        node_list.sort(key=lambda n: (n.get("order", 0), n.get("name", "")))
        for n in node_list:
            sort_nodes(n.get("children") or [])

    if root_id and root_id in nodes:
        root_node = nodes[root_id]
        for node in orphans:
            if node["id"] != root_id:
                root_node["children"].append(node)
        sort_nodes(root_node["children"])
        tree = [root_node]
    else:
        sort_nodes(orphans)
        tree = orphans

    return {
        "rootCategoryId": root_id,
        "rootCategoryName": root_name,
        "tree": tree,
    }
