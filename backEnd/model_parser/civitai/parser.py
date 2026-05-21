"""Civitai URL 解析（禁止 HTML）。"""
from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

CIVITAI_HOSTS = frozenset(
    {"civitai.com", "www.civitai.com", "civitai.red", "www.civitai.red", "civitai.green", "www.civitai.green"}
)


class CivitaiParser:
    MODEL_PATH_RE = re.compile(r"/models/(\d+)", re.I)

    @classmethod
    def is_civitai_url(cls, url: str) -> bool:
        try:
            host = urlparse(url.strip()).netloc.lower().replace("www.", "")
            base = host.split(":")[0]
            return base in {h.replace("www.", "") for h in CIVITAI_HOSTS} or "civitai" in base
        except Exception:
            return False

    @classmethod
    def parse_url(cls, url: str) -> dict:
        parsed = urlparse(url.strip())
        host = parsed.netloc.lower()
        if not cls.is_civitai_url(url):
            raise ValueError("不是有效的 Civitai 链接")

        m = cls.MODEL_PATH_RE.search(parsed.path)
        if not m:
            raise ValueError("无法从 URL 提取 modelId")
        model_id = int(m.group(1))

        qs = parse_qs(parsed.query)
        version_id = None
        for key in ("modelVersionId", "modelVersionID", "versionId"):
            if key in qs and qs[key]:
                version_id = int(qs[key][0])
                break

        return {
            "site": "civitai",
            "modelId": model_id,
            "modelVersionId": version_id,
        }
