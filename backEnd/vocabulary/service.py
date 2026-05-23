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
    items = index.suggest(Path(VOCABULARY_DB_PATH), query, limit=limit)
    took_ms = int((time.perf_counter() - t0) * 1000)
    return {"items": items, "query": query, "tookMs": took_ms}


def index_stats() -> dict:
    return index.get_stats(Path(VOCABULARY_DB_PATH))


def resolve(values: list[str]) -> dict:
    ensure_index()
    t0 = time.perf_counter()
    items = index.resolve_values(Path(VOCABULARY_DB_PATH), values)
    took_ms = int((time.perf_counter() - t0) * 1000)
    return {"items": items, "tookMs": took_ms}
