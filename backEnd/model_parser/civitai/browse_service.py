"""Civitai 模型列表 / 搜索（GET /api/v1/models）。"""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode

from model_parser.civitai.metadata_extractor import MetadataExtractor
from model_parser.civitai.model_service import ModelService
from model_parser.html_utils import html_to_plain_text
from model_parser.http_client import CIVITAI_API_BASE, get_json

log = logging.getLogger("custom_project.model_parser.civitai.browse")

ALLOWED_TYPES = frozenset({
    "Checkpoint",
    "LORA",
    "LoCon",
    "DoRA",
    "Controlnet",
    "VAE",
    "TextualInversion",
    "AestheticGradient",
    "Hypernetwork",
    "Upscaler",
})

ALLOWED_SORT = frozenset({
    "Highest Rated",
    "Most Downloaded",
    "Newest",
})

ALLOWED_PERIOD = frozenset({
    "AllTime",
    "Year",
    "Month",
    "Week",
    "Day",
})

BROWSE_PRESETS = [
    {
        "id": "hot-checkpoint",
        "label": "热门 Checkpoint",
        "types": "Checkpoint",
        "sort": "Most Downloaded",
        "period": "Month",
        "query": "",
    },
    {
        "id": "hot-lora",
        "label": "热门 LoRA",
        "types": "LORA",
        "sort": "Most Downloaded",
        "period": "Month",
        "query": "",
    },
    {
        "id": "style-lora",
        "label": "风格 LoRA",
        "types": "LORA",
        "sort": "Most Downloaded",
        "period": "Month",
        "query": "",
        "tag": "style",
    },
    {
        "id": "new-checkpoint",
        "label": "最新 Checkpoint",
        "types": "Checkpoint",
        "sort": "Newest",
        "period": "Week",
        "query": "",
    },
]


def list_presets() -> list[dict]:
    return [dict(p) for p in BROWSE_PRESETS]


def _normalize_types(types: str | None) -> str | None:
    if not types or not str(types).strip():
        return None
    parts = [t.strip() for t in str(types).split(",") if t.strip()]
    valid = [t for t in parts if t in ALLOWED_TYPES]
    return ",".join(valid) if valid else None


CONTENT_MODES = frozenset({"sfw", "nsfw", "all"})


def _build_page_url(
    model_id: int | str,
    version_id: int | str | None,
    *,
    is_nsfw: bool = False,
) -> str:
    """NSFW 模型链到 civitai.red（红 C 站），其余链到 civitai.com（蓝 C 站）。"""
    host = "civitai.red" if is_nsfw else "civitai.com"
    base = f"https://{host}/models/{model_id}"
    if version_id:
        return f"{base}?modelVersionId={version_id}"
    return base


def _resolve_content_mode(content: str | None, nsfw_legacy: bool | None = None) -> str:
    mode = (content or "sfw").strip().lower()
    if mode not in CONTENT_MODES:
        mode = "sfw"
    if nsfw_legacy is True and mode == "sfw":
        mode = "nsfw"
    return mode


def _card_from_model(data: dict) -> dict:
    versions = data.get("modelVersions") or []
    latest = versions[0] if versions else {}
    version_id = latest.get("id")
    images = latest.get("images") or []
    preview = MetadataExtractor.pick_preview_image(images)
    model_type = data.get("type") or ""
    stats = data.get("stats") or {}
    creator = data.get("creator") or {}
    tags_raw = data.get("tags") or []
    tags = [
        t if isinstance(t, str) else (t.get("name") or "")
        for t in tags_raw
        if (t if isinstance(t, str) else t.get("name"))
    ]
    return {
        "id": data.get("id"),
        "name": data.get("name", ""),
        "type": model_type,
        "creator": creator.get("username") or creator.get("name") or "",
        "nsfw": bool(data.get("nsfw")),
        "description": html_to_plain_text(data.get("description") or "")[:280],
        "tags": tags[:8],
        "downloadCount": stats.get("downloadCount") or data.get("downloadCount"),
        "rating": stats.get("rating"),
        "ratingCount": stats.get("ratingCount"),
        "latestVersionId": version_id,
        "latestVersionName": latest.get("name", ""),
        "baseModel": latest.get("baseModel", ""),
        "thumbnailUrl": preview.get("url") if preview else None,
        "previewMedia": preview,
        "pageUrl": _build_page_url(
            data.get("id"),
            version_id,
            is_nsfw=bool(data.get("nsfw")),
        ),
        "suggestedFolder": ModelService.suggest_folder(model_type),
        "versionsCount": len(versions),
    }


def search_tags(*, query: str | None = None, page: int = 1, limit: int = 30) -> dict[str, Any]:
    """GET /api/v1/tags — 按名称搜索标签（用于筛选模型）。"""
    page_val = max(1, int(page or 1))
    limit_val = max(1, min(200, int(limit or 30)))
    params: dict[str, Any] = {"page": page_val, "limit": limit_val}
    q = (query or "").strip()
    if q:
        params["query"] = q
    url = f"{CIVITAI_API_BASE}/tags?{urlencode(params)}"
    log.info("GET %s", url)
    raw = get_json(url)
    items_raw = raw.get("items") if isinstance(raw, dict) else []
    if not isinstance(items_raw, list):
        items_raw = []
    meta = raw.get("metadata") if isinstance(raw, dict) else {}
    if not isinstance(meta, dict):
        meta = {}
    tags = []
    for item in items_raw:
        if isinstance(item, str):
            tags.append({"name": item, "link": None})
        elif isinstance(item, dict):
            tags.append({
                "name": item.get("name") or "",
                "link": item.get("link"),
            })
    tags = [t for t in tags if t.get("name")]
    return {
        "tags": tags,
        "metadata": {
            "totalItems": meta.get("totalItems"),
            "currentPage": meta.get("currentPage") or page_val,
            "pageSize": meta.get("pageSize") or limit_val,
            "totalPages": meta.get("totalPages"),
        },
    }


def browse_models(
    *,
    types: str | None = None,
    sort: str = "Most Downloaded",
    period: str = "Month",
    query: str | None = None,
    tag: str | None = None,
    cursor: str | None = None,
    page: int = 1,
    limit: int = 24,
    base_models: str | None = None,
    content: str = "sfw",
    nsfw: bool | None = None,
) -> dict[str, Any]:
    """
    列表/搜索模型。Civitai 的 page 参数不可靠（多页常重复），统一用 cursor 分页。
    首页不传 cursor；翻页传上一页 metadata.nextCursor。
    """
    sort_val = sort if sort in ALLOWED_SORT else "Most Downloaded"
    period_val = period if period in ALLOWED_PERIOD else "Month"
    page_val = max(1, int(page or 1))
    limit_val = max(1, min(100, int(limit or 24)))

    content_mode = _resolve_content_mode(content, nsfw)
    params: dict[str, Any] = {
        "limit": limit_val,
        "sort": sort_val,
        "period": period_val,
    }
    if content_mode == "sfw":
        params["nsfw"] = "false"
    elif content_mode == "nsfw":
        params["nsfw"] = "true"
    types_norm = _normalize_types(types)
    if types_norm:
        params["types"] = types_norm
    q = (query or "").strip()
    if q:
        params["query"] = q
    tag_norm = (tag or "").strip()
    if tag_norm:
        params["tag"] = tag_norm
    if base_models and str(base_models).strip():
        params["baseModels"] = str(base_models).strip()

    cur = (cursor or "").strip()
    if cur:
        params["cursor"] = cur
    elif page_val > 1:
        log.warning(
            "browse_models page=%s without cursor ignored (Civitai page pagination broken)",
            page_val,
        )

    url = f"{CIVITAI_API_BASE}/models?{urlencode(params)}"
    log.info("GET %s", url)
    raw = get_json(url)
    items_raw = raw.get("items") if isinstance(raw, dict) else raw
    if not isinstance(items_raw, list):
        items_raw = []

    meta = raw.get("metadata") if isinstance(raw, dict) else {}
    if not isinstance(meta, dict):
        meta = {}

    next_cursor = meta.get("nextCursor")
    if next_cursor is not None:
        next_cursor = str(next_cursor).strip() or None

    return {
        "items": [_card_from_model(m) for m in items_raw if isinstance(m, dict)],
        "metadata": {
            "totalItems": meta.get("totalItems"),
            "currentPage": page_val,
            "pageSize": meta.get("pageSize") or limit_val,
            "totalPages": meta.get("totalPages"),
            "nextCursor": next_cursor,
            "hasMore": bool(next_cursor),
            "nextPage": meta.get("nextPage"),
        },
        "query": {
            "types": types_norm,
            "sort": sort_val,
            "period": period_val,
            "query": q or None,
            "tag": tag_norm or None,
            "cursor": cur or None,
            "page": page_val,
            "limit": limit_val,
            "baseModels": base_models,
            "content": content_mode,
            "nsfw": content_mode == "nsfw",
        },
    }
