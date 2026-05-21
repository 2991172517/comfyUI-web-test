"""Shakker URL 解析。"""
from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

SHAKKER_HOSTS = frozenset({"www.shakker.ai", "shakker.ai"})


class ShakkerParser:
    PATH_RE = re.compile(r"/modelinfo/([a-f0-9]+)", re.I)

    @classmethod
    def is_shakker_url(cls, url: str) -> bool:
        try:
            host = urlparse(url.strip()).netloc.lower().replace("www.", "")
            return host in {"shakker.ai"} or "shakker.ai" in urlparse(url).netloc.lower()
        except Exception:
            return False

    @classmethod
    def parse_url(cls, url: str) -> dict:
        if not cls.is_shakker_url(url):
            raise ValueError("不是有效的 Shakker 链接")
        parsed = urlparse(url.strip())
        m = cls.PATH_RE.search(parsed.path)
        if not m:
            raise ValueError("无法从 URL 提取 modelUuid")
        model_uuid = m.group(1)
        qs = parse_qs(parsed.query)
        version_uuid = (qs.get("versionUuid") or [None])[0]
        return {
            "site": "shakker",
            "modelUuid": model_uuid,
            "versionUuid": version_uuid,
        }
