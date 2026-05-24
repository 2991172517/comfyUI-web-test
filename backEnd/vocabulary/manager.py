"""Tag 显示管理：分类树、词条增删、喜好排序、隐藏分类。"""
from __future__ import annotations

from pathlib import Path

from config import VOCABULARY_DB_PATH, VOCABULARY_USER_PATH

from . import index
from .service import ensure_index
from .user_store import (
    add_deletion,
    add_hidden_categories,
    add_user_prompt,
    hidden_category_set,
    load,
    preference_map,
    remove_user_prompt,
    save,
    set_tag_preference,
)

_PREFERENCE_SORT = {"like": 0, "dislike": 2}


def _user_data() -> dict:
    return load(Path(VOCABULARY_USER_PATH))


def _filter_tree(nodes: list[dict], hidden: set[str]) -> list[dict]:
    out: list[dict] = []
    for node in nodes or []:
        nid = (node.get("id") or "").strip()
        if nid and nid in hidden:
            continue
        children = _filter_tree(node.get("children") or [], hidden)
        out.append({**node, "children": children})
    return out


def _collect_subtree_ids(nodes: list[dict], target_id: str) -> list[str]:
    target_id = (target_id or "").strip()
    if not target_id:
        return []

    def walk(node: dict) -> list[str] | None:
        nid = (node.get("id") or "").strip()
        if nid == target_id:
            ids = [nid]
            for child in node.get("children") or []:
                ids.extend(_walk_all(child))
            return ids
        for child in node.get("children") or []:
            hit = walk(child)
            if hit:
                return hit
        return None

    def _walk_all(node: dict) -> list[str]:
        nid = (node.get("id") or "").strip()
        ids = [nid] if nid else []
        for child in node.get("children") or []:
            ids.extend(_walk_all(child))
        return ids

    for root in nodes or []:
        hit = walk(root)
        if hit:
            return hit
    if any((n.get("id") or "").strip() == target_id for n in nodes or []):
        node = next(n for n in nodes if (n.get("id") or "").strip() == target_id)
        return _walk_all(node)
    return []


def _attach_preferences(items: list[dict], prefs: dict) -> list[dict]:
    out = []
    for item in items:
        key = (
            (item.get("categoryId") or "").strip(),
            (item.get("value") or "").strip().lower(),
        )
        pref = prefs.get(key)
        enriched = dict(item)
        enriched["preference"] = pref if pref in ("like", "dislike") else None
        out.append(enriched)
    return out


def _sort_by_preference(items: list[dict]) -> list[dict]:
    def sort_key(item: dict) -> tuple:
        pref = item.get("preference")
        order = _PREFERENCE_SORT.get(pref, 1)
        name = (item.get("name") or item.get("value") or "").lower()
        value = (item.get("value") or "").lower()
        return (order, name, value)

    return sorted(items, key=sort_key)


def category_tree() -> dict:
    ensure_index()
    raw = index.get_category_tree(Path(VOCABULARY_DB_PATH))
    hidden = hidden_category_set(_user_data())
    if not hidden:
        return raw
    tree = _filter_tree(raw.get("tree") or [], hidden)
    return {**raw, "tree": tree}


def list_prompts(
    category_id: str,
    *,
    q: str = "",
    offset: int = 0,
    limit: int = 80,
) -> dict:
    ensure_index()
    db = Path(VOCABULARY_DB_PATH)
    raw = index.list_prompts_in_category(
        db,
        category_id,
        q=q,
        offset=0,
        limit=100000,
    )
    prefs = preference_map(_user_data())
    items = _sort_by_preference(_attach_preferences(raw.get("items") or [], prefs))
    total = len(items)
    start = max(0, int(offset))
    end = start + max(1, min(int(limit), 200))
    page = items[start:end]
    return {
        "items": page,
        "total": total,
        "offset": start,
        "limit": limit,
    }


def get_settings() -> dict:
    data = _user_data()
    return {
        "defaultWeight": float(data.get("defaultWeight", 1.0)),
        "hiddenCategoryCount": len(hidden_category_set(data)),
    }


def update_settings(*, default_weight: float) -> dict:
    path = Path(VOCABULARY_USER_PATH)
    data = load(path)
    w = float(default_weight)
    if w < 0.05 or w > 2.0:
        raise ValueError("defaultWeight 须在 0.05～2.0 之间")
    data["defaultWeight"] = round(w, 2)
    save(path, data)
    return get_settings()


def set_prompt_preference(
    *, category_id: str, value: str, preference: str | None
) -> dict:
    path = Path(VOCABULARY_USER_PATH)
    data = load(path)
    pref = set_tag_preference(
        data, category_id=category_id, value=value, preference=preference
    )
    save(path, data)
    return {"ok": True, "preference": pref}


def category_prompt_count(category_id: str) -> int:
    ensure_index()
    res = index.list_prompts_in_category(
        Path(VOCABULARY_DB_PATH),
        category_id,
        offset=0,
        limit=1,
    )
    return int(res.get("total") or 0)


def delete_category(*, category_id: str) -> dict:
    cid = (category_id or "").strip()
    if not cid:
        raise ValueError("categoryId 不能为空")
    ensure_index()
    raw = index.get_category_tree(Path(VOCABULARY_DB_PATH))
    ids = _collect_subtree_ids(raw.get("tree") or [], cid)
    if not ids:
        ids = [cid]
    path = Path(VOCABULARY_USER_PATH)
    data = load(path)
    add_hidden_categories(data, ids)
    save(path, data)
    return {"ok": True, "hiddenCategoryIds": ids}


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
