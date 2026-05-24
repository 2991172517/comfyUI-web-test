"""用户词库覆盖：增删词条、默认权重（不直接改写大 manifest）。"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

_lock = threading.Lock()

DEFAULT_DATA: dict[str, Any] = {
    "defaultWeight": 1.0,
    "deleted": [],
    "prompts": [],
    "tagPreferences": [],
    "hiddenCategories": [],
}


def _normalize(data: dict | None) -> dict:
    base = dict(DEFAULT_DATA)
    if not data:
        return base
    base["defaultWeight"] = float(data.get("defaultWeight", 1.0))
    base["deleted"] = list(data.get("deleted") or [])
    base["prompts"] = list(data.get("prompts") or [])
    base["tagPreferences"] = list(data.get("tagPreferences") or [])
    base["hiddenCategories"] = list(data.get("hiddenCategories") or [])
    return base


def load(path: Path) -> dict:
    path = path.resolve()
    if not path.is_file():
        return _normalize(None)
    with _lock:
        with open(path, encoding="utf-8") as f:
            return _normalize(json.load(f))


def save(path: Path, data: dict) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = _normalize(data)
    with _lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)


def fingerprint(path: Path) -> str:
    path = path.resolve()
    if not path.is_file():
        return "missing"
    st = path.stat()
    return f"{int(st.st_mtime)}:{st.st_size}"


def deletion_key(category_id: str, value: str) -> tuple[str, str]:
    return ((category_id or "").strip(), (value or "").strip().lower())


def preference_key(category_id: str, value: str) -> tuple[str, str]:
    return deletion_key(category_id, value)


def preference_map(data: dict) -> dict[tuple[str, str], str]:
    out: dict[tuple[str, str], str] = {}
    for item in data.get("tagPreferences") or []:
        if not isinstance(item, dict):
            continue
        pref = (item.get("preference") or "").strip().lower()
        if pref not in ("like", "dislike"):
            continue
        key = preference_key(item.get("categoryId", ""), item.get("value", ""))
        if key[0] and key[1]:
            out[key] = pref
    return out


def set_tag_preference(
    data: dict, *, category_id: str, value: str, preference: str | None
) -> str | None:
    """设置 like / dislike；preference 为 neutral 或空则清除。"""
    cid = (category_id or "").strip()
    v = (value or "").strip()
    if not cid or not v:
        raise ValueError("categoryId 与 value 不能为空")
    pref = (preference or "").strip().lower()
    if pref in ("", "neutral", "none", "null"):
        pref = ""
    elif pref not in ("like", "dislike"):
        raise ValueError("preference 须为 like、dislike 或 neutral")

    key = preference_key(cid, v)
    kept = [
        p
        for p in (data.get("tagPreferences") or [])
        if not (
            isinstance(p, dict)
            and preference_key(p.get("categoryId", ""), p.get("value", "")) == key
        )
    ]
    if pref:
        kept.append({"categoryId": cid, "value": v, "preference": pref})
    data["tagPreferences"] = kept
    return pref or None


def hidden_category_set(data: dict) -> set[str]:
    out: set[str] = set()
    for cid in data.get("hiddenCategories") or []:
        s = str(cid or "").strip()
        if s:
            out.add(s)
    return out


def add_hidden_categories(data: dict, category_ids: list[str]) -> None:
    hidden = hidden_category_set(data)
    for cid in category_ids:
        s = (cid or "").strip()
        if s:
            hidden.add(s)
    data["hiddenCategories"] = sorted(hidden)


def deleted_set(data: dict) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for item in data.get("deleted") or []:
        if isinstance(item, dict):
            out.add(deletion_key(item.get("categoryId", ""), item.get("value", "")))
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            out.add(deletion_key(str(item[0]), str(item[1])))
    return out


def add_deletion(data: dict, category_id: str, value: str) -> None:
    key = deletion_key(category_id, value)
    existing = deleted_set(data)
    if key in existing:
        return
    data.setdefault("deleted", []).append(
        {"categoryId": key[0], "value": (value or "").strip()}
    )


def remove_user_prompt(data: dict, category_id: str, value: str) -> bool:
    v_lower = (value or "").strip().lower()
    cid = (category_id or "").strip()
    prompts = data.get("prompts") or []
    kept = [
        p
        for p in prompts
        if not (
            (p.get("categoryId") or "").strip() == cid
            and (p.get("value") or "").strip().lower() == v_lower
        )
    ]
    if len(kept) == len(prompts):
        return False
    data["prompts"] = kept
    return True


def add_user_prompt(data: dict, *, category_id: str, value: str, name: str) -> None:
    v = (value or "").strip()
    if not v:
        raise ValueError("value 不能为空")
    cid = (category_id or "").strip()
    if not cid:
        raise ValueError("categoryId 不能为空")
    remove_user_prompt(data, cid, v)
    data.setdefault("prompts", []).append(
        {
            "value": v,
            "name": (name or v).strip(),
            "categoryId": cid,
        }
    )


def migrate_user_category_ids(data: dict, conn) -> bool:
    """将用户覆盖文件中的 manifest UUID 迁移为 DB 内部分类 id。"""
    from .categories import resolve_internal_category_id

    changed = False

    def remap(cid: str) -> str:
        nonlocal changed
        raw = (cid or "").strip()
        if not raw:
            return raw
        resolved = resolve_internal_category_id(conn, raw)
        if resolved and resolved != raw:
            changed = True
            return resolved
        return raw

    for item in data.get("prompts") or []:
        if not isinstance(item, dict):
            continue
        old = item.get("categoryId", "")
        new = remap(old)
        if new != old:
            item["categoryId"] = new

    for item in data.get("deleted") or []:
        if not isinstance(item, dict):
            continue
        old = item.get("categoryId", "")
        new = remap(old)
        if new != old:
            item["categoryId"] = new

    for item in data.get("tagPreferences") or []:
        if not isinstance(item, dict):
            continue
        old = item.get("categoryId", "")
        new = remap(old)
        if new != old:
            item["categoryId"] = new

    remapped_hidden = []
    for cid in data.get("hiddenCategories") or []:
        old = str(cid or "").strip()
        if not old:
            continue
        new = remap(old)
        remapped_hidden.append(new)
    if remapped_hidden != list(data.get("hiddenCategories") or []):
        data["hiddenCategories"] = remapped_hidden
        changed = True

    return changed
