"""模型说明中的访问链接行。"""
from __future__ import annotations

import re

SOURCE_URL_LINE_PREFIX = "访问链接:"


def normalize_source_url(url: str) -> str:
    u = (url or "").strip()
    if u and not u.startswith(("http://", "https://")):
        u = "https://" + u.lstrip("/")
    return u


def format_with_source_url(source_url: str, body: str) -> str:
    """在正文首行插入「访问链接: …」。"""
    url = normalize_source_url(source_url)
    text = (body or "").strip()
    if not url:
        return text
    prefix = f"{SOURCE_URL_LINE_PREFIX} {url}"
    if text.startswith(prefix):
        return text
    first_line = text.splitlines()[0].strip() if text else ""
    if first_line == url or first_line.startswith("http"):
        return text
    return f"{prefix}\n\n{text}" if text else prefix


def split_source_url_from_text(text: str) -> tuple[str | None, str]:
    """从说明文本解析首行链接，返回 (url, 剩余正文)。"""
    raw = text or ""
    if not raw.strip():
        return None, raw
    lines = raw.splitlines()
    first = lines[0].strip()
    if first.startswith(SOURCE_URL_LINE_PREFIX):
        url = normalize_source_url(first.split(":", 1)[1].strip())
        rest = "\n".join(lines[1:]).lstrip("\n")
        return url or None, rest
    if re.match(r"^https?://", first, re.I):
        rest = "\n".join(lines[1:]).lstrip("\n")
        return first, rest
    return None, raw
