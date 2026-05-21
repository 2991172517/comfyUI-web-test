"""Civitai API Token（下载模型必需，见 https://education.civitai.com/civitais-guide-to-downloading-via-api/）。"""
from __future__ import annotations

import os
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

# 环境变量 CIVITAI_API_TOKEN，或在 CustomProject/config/civitai_token.txt 首行（可选）
_TOKEN_CACHE: str | None = None


def _read_token_file() -> str:
    try:
        from config import PROJECT_ROOT

        path = PROJECT_ROOT / "config" / "civitai_token.txt"
        if path.is_file():
            line = path.read_text(encoding="utf-8").strip().splitlines()
            if line:
                return line[0].strip()
    except Exception:
        pass
    return ""


def get_civitai_api_token() -> str:
    global _TOKEN_CACHE
    if _TOKEN_CACHE is None:
        _TOKEN_CACHE = (os.getenv("CIVITAI_API_TOKEN") or _read_token_file()).strip()
    return _TOKEN_CACHE


def resolve_civitai_token(request_token: str | None = None) -> str:
    """优先使用本次请求携带的 Token（来自前端 localStorage），否则用服务端配置。"""
    t = (request_token or "").strip()
    if t:
        return t
    return get_civitai_api_token()


def is_civitai_download_url(url: str) -> bool:
    u = (url or "").lower()
    return "civitai.com/api/download" in u or "civitai.red/api/download" in u


def civitai_request_headers(extra: dict | None = None, *, request_token: str | None = None) -> dict:
    headers = dict(extra or {})
    token = resolve_civitai_token(request_token)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def apply_civitai_download_auth(url: str, *, request_token: str | None = None) -> str:
    """为下载 URL 附加 token 查询参数（与 Bearer 二选一或并用）。"""
    if not url or not is_civitai_download_url(url):
        return url
    token = resolve_civitai_token(request_token)
    if not token:
        return url
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    if "token" in qs and qs["token"][0]:
        return url
    qs["token"] = [token]
    new_query = urlencode(qs, doseq=True)
    return urlunparse(parsed._replace(query=new_query))
