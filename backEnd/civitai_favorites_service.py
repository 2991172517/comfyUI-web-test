"""C 站模型收藏：按 Civitai API Key（哈希分桶）存于 config/civitai_favorites.json。"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import PROJECT_ROOT

log = logging.getLogger("custom_project.civitai_favorites")

STORE_FILE = PROJECT_ROOT / "config" / "civitai_favorites.json"
MAX_ITEMS_PER_KEY = 500
_lock = threading.Lock()

ALLOWED_CARD_KEYS = frozenset({
    "id",
    "name",
    "type",
    "creator",
    "nsfw",
    "description",
    "tags",
    "downloadCount",
    "rating",
    "ratingCount",
    "latestVersionId",
    "latestVersionName",
    "baseModel",
    "thumbnailUrl",
    "previewMedia",
    "pageUrl",
    "suggestedFolder",
    "versionsCount",
})


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _storage_key(civitai_api_token: str) -> str | None:
    token = (civitai_api_token or "").strip()
    if not token:
        return None
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return digest[:32]


def _load_store() -> dict[str, Any]:
    if not STORE_FILE.is_file():
        return {"by_key": {}}
    try:
        with open(STORE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("by_key"), dict):
            return data
    except (OSError, json.JSONDecodeError) as e:
        log.warning("读取 civitai_favorites.json 失败: %s", e)
    return {"by_key": {}}


def _save_store(data: dict[str, Any]) -> None:
    STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _sanitize_item(raw: dict[str, Any]) -> dict[str, Any]:
    out = {k: raw[k] for k in ALLOWED_CARD_KEYS if k in raw}
    mid = out.get("id")
    if mid is None:
        raise ValueError("收藏项缺少模型 id")
    out["id"] = int(mid) if str(mid).isdigit() else mid
    return out


def list_favorites(civitai_api_token: str) -> dict[str, Any]:
    key = _storage_key(civitai_api_token)
    if not key:
        return {"items": [], "requiresToken": True}
    with _lock:
        store = _load_store()
        bucket = store.get("by_key", {}).get(key) or {}
        items = bucket.get("items") if isinstance(bucket, dict) else []
        if not isinstance(items, list):
            items = []
        items = sorted(
            [i for i in items if isinstance(i, dict)],
            key=lambda x: x.get("savedAt") or "",
            reverse=True,
        )
    return {"items": items, "requiresToken": False, "count": len(items)}


def add_favorite(civitai_api_token: str, item: dict[str, Any]) -> dict[str, Any]:
    key = _storage_key(civitai_api_token)
    if not key:
        raise ValueError("请先在前端保存 Civitai API Key，再收藏模型")
    card = _sanitize_item(item)
    card["savedAt"] = _now_iso()
    model_id = card["id"]

    with _lock:
        store = _load_store()
        by_key = store.setdefault("by_key", {})
        bucket = by_key.setdefault(key, {"items": [], "updatedAt": None})
        items: list[dict] = bucket.get("items") if isinstance(bucket.get("items"), list) else []
        items = [i for i in items if isinstance(i, dict) and i.get("id") != model_id]
        items.insert(0, card)
        if len(items) > MAX_ITEMS_PER_KEY:
            items = items[:MAX_ITEMS_PER_KEY]
        bucket["items"] = items
        bucket["updatedAt"] = _now_iso()
        by_key[key] = bucket
        _save_store(store)

    return {"item": card, "count": len(items)}


def remove_favorite(civitai_api_token: str, model_id: str | int) -> dict[str, Any]:
    key = _storage_key(civitai_api_token)
    if not key:
        raise ValueError("请先保存 Civitai API Key")
    mid = int(model_id) if str(model_id).isdigit() else model_id

    with _lock:
        store = _load_store()
        by_key = store.get("by_key", {})
        bucket = by_key.get(key)
        if not isinstance(bucket, dict):
            return {"removed": False, "count": 0}
        items = [i for i in (bucket.get("items") or []) if isinstance(i, dict)]
        new_items = [i for i in items if i.get("id") != mid]
        removed = len(new_items) != len(items)
        bucket["items"] = new_items
        bucket["updatedAt"] = _now_iso()
        by_key[key] = bucket
        _save_store(store)

    return {"removed": removed, "count": len(new_items)}


def is_favorited(civitai_api_token: str, model_id: str | int) -> bool:
    key = _storage_key(civitai_api_token)
    if not key:
        return False
    mid = int(model_id) if str(model_id).isdigit() else model_id
    with _lock:
        store = _load_store()
        bucket = store.get("by_key", {}).get(key) or {}
        items = bucket.get("items") if isinstance(bucket, dict) else []
    return any(isinstance(i, dict) and i.get("id") == mid for i in (items or []))
