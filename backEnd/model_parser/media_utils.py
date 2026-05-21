"""Civitai / 模型源媒体 URL 分类（静态图 vs 视频预览）。"""
from __future__ import annotations

from urllib.parse import urlparse

VIDEO_SUFFIXES = frozenset({".mp4", ".webm", ".mov", ".m4v"})
STATIC_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"})


def _path_lower(url: str) -> str:
    try:
        return (urlparse(url).path or "").lower()
    except Exception:
        return ""


def is_video_url(url: str | None) -> bool:
    if not url:
        return False
    path = _path_lower(url)
    return any(path.endswith(ext) for ext in VIDEO_SUFFIXES)


def is_static_image_url(url: str | None) -> bool:
    if not url:
        return False
    path = _path_lower(url)
    if any(path.endswith(ext) for ext in STATIC_IMAGE_SUFFIXES):
        return True
    if is_video_url(url):
        return False
    # Civitai 部分 CDN 链接无后缀，按非视频处理
    return True


def classify_image_entry(img: dict) -> str:
    """返回 'video' | 'image'。"""
    if not img:
        return "image"
    raw_type = str(img.get("type") or img.get("mimeType") or "").lower()
    url = str(img.get("url") or "")
    if "video" in raw_type or is_video_url(url):
        return "video"
    return "image"


def preview_entry(img: dict | None) -> dict | None:
    if not img or not img.get("url"):
        return None
    media = classify_image_entry(img)
    return {
        "url": img.get("url"),
        "width": img.get("width"),
        "height": img.get("height"),
        "nsfwLevel": img.get("nsfwLevel"),
        "mediaType": media,
        "isVideo": media == "video",
    }
