"""词库服务：懒加载构建索引 + 查询。"""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from config import VOCABULARY_DB_PATH, VOCABULARY_MANIFEST_PATH, VOCABULARY_USER_PATH

from . import index

log = logging.getLogger("custom_project.vocabulary")

_index_lock = threading.Lock()
_ready = False


def ensure_index(force: bool = False) -> None:
    global _ready
    manifest = Path(VOCABULARY_MANIFEST_PATH)
    db_path = Path(VOCABULARY_DB_PATH)
    user_path = Path(VOCABULARY_USER_PATH)

    if _ready and not force and not index.needs_rebuild(
        manifest, db_path, user_path=user_path
    ):
        return

    with _index_lock:
        if _ready and not force and not index.needs_rebuild(
            manifest, db_path, user_path=user_path
        ):
            return
        if not manifest.is_file():
            raise FileNotFoundError(f"词库 manifest 不存在: {manifest}")
        t0 = time.perf_counter()
        index.build_index(manifest, db_path, user_path=user_path)
        _ready = True
        log.info("词库索引就绪 (%.1fs)", time.perf_counter() - t0)


def suggest(query: str, limit: int = 12) -> dict:
    ensure_index()
    t0 = time.perf_counter()
    items = index.suggest(Path(VOCABULARY_DB_PATH), query, limit=max(limit, 50))
    items = _sort_suggest_by_preference(items)[:limit]
    took_ms = int((time.perf_counter() - t0) * 1000)
    return {"items": items, "query": query, "tookMs": took_ms}


def _sort_suggest_by_preference(items: list) -> list:
    from .user_store import load, preference_map

    prefs = preference_map(load(Path(VOCABULARY_USER_PATH)))
    pref_order = {"like": 0, "dislike": 2}

    def key(item: dict) -> tuple:
        cid = (item.get("categoryId") or item.get("category_id") or "").strip()
        val = (item.get("insertText") or item.get("insert_text") or "").strip().lower()
        pref = prefs.get((cid, val))
        label = (item.get("label") or val).lower()
        return (pref_order.get(pref, 1), label, val)

    return sorted(items, key=key)


def index_stats() -> dict:
    return index.get_stats(Path(VOCABULARY_DB_PATH))


def resolve(values: list[str]) -> dict:
    ensure_index()
    t0 = time.perf_counter()
    items = index.resolve_values(Path(VOCABULARY_DB_PATH), values)
    took_ms = int((time.perf_counter() - t0) * 1000)
    return {"items": items, "tookMs": took_ms}
