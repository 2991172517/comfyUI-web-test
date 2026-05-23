"""Tag 词库管理：分类树、词条增删、默认权重。"""
from __future__ import annotations

from pathlib import Path

from config import VOCABULARY_DB_PATH, VOCABULARY_USER_PATH

from . import index
from .service import ensure_index
from .user_store import (
    add_deletion,
    add_user_prompt,
    load,
    remove_user_prompt,
    save,
)


def category_tree() -> dict:
    ensure_index()
    return index.get_category_tree(Path(VOCABULARY_DB_PATH))


def list_prompts(
    category_id: str,
    *,
    q: str = "",
    offset: int = 0,
    limit: int = 80,
) -> dict:
    ensure_index()
    return index.list_prompts_in_category(
        Path(VOCABULARY_DB_PATH),
        category_id,
        q=q,
        offset=offset,
        limit=limit,
    )


def get_settings() -> dict:
    data = load(Path(VOCABULARY_USER_PATH))
    return {"defaultWeight": float(data.get("defaultWeight", 1.0))}


def update_settings(*, default_weight: float) -> dict:
    path = Path(VOCABULARY_USER_PATH)
    data = load(path)
    w = float(default_weight)
    if w < 0.05 or w > 2.0:
        raise ValueError("defaultWeight 须在 0.05～2.0 之间")
    data["defaultWeight"] = round(w, 2)
    save(path, data)
    return get_settings()


def add_prompt(*, category_id: str, value: str, name: str) -> dict:
    ensure_index()
    db = Path(VOCABULARY_DB_PATH)
    user_path = Path(VOCABULARY_USER_PATH)
    data = load(user_path)
    add_user_prompt(data, category_id=category_id, value=value, name=name)
    save(user_path, data)
    index.insert_vocab_prompt(
        db,
        category_id=category_id,
        value=value,
        name=name,
        source_id="user",
    )
    return {"ok": True}


def delete_prompt(*, category_id: str, value: str) -> dict:
    ensure_index()
    db = Path(VOCABULARY_DB_PATH)
    user_path = Path(VOCABULARY_USER_PATH)
    source = index.vocab_source_for(db, category_id=category_id, value=value)
    if not source:
        return {"ok": False, "reason": "not_found"}

    data = load(user_path)
    if source == "user":
        remove_user_prompt(data, category_id, value)
    else:
        add_deletion(data, category_id, value)
    save(user_path, data)
    index.delete_vocab_prompt(db, category_id=category_id, value=value)
    return {"ok": True}
