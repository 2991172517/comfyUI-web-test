"""HTTP 客户端：超时、重试、同步/异步。"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

import aiohttp
import requests

from model_parser.civitai.auth import (
    apply_civitai_download_auth,
    civitai_request_headers,
    get_civitai_api_token,
    is_civitai_download_url,
    resolve_civitai_token,
)

log = logging.getLogger("custom_project.model_parser.http")

DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF = 1.5

CIVITAI_API_BASE = "https://civitai.com/api/v1"
DEFAULT_HEADERS = {
    "User-Agent": "ComfyUI-CustomProject/1.0 (+model-parser)",
    "Accept": "application/json",
}


def _request_sync(method: str, url: str, **kwargs) -> Any:
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    kwargs.setdefault("headers", {**DEFAULT_HEADERS, **kwargs.pop("headers", {})})
    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.request(method, url, **kwargs)
            resp.raise_for_status()
            if resp.headers.get("content-type", "").startswith("application/json"):
                return resp.json()
            return resp.content
        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES - 1:
                import time

                time.sleep(RETRY_BACKOFF ** attempt)
                log.warning("重试 %s %s (%s/%s): %s", method, url, attempt + 2, MAX_RETRIES, e)
    raise RuntimeError(f"请求失败: {url}") from last_err


async def _request_async(method: str, url: str, **kwargs) -> Any:
    kwargs.setdefault("timeout", aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT))
    headers = {**DEFAULT_HEADERS, **kwargs.pop("headers", {})}
    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.request(method, url, **kwargs) as resp:
                    resp.raise_for_status()
                    if resp.content_type and "json" in resp.content_type:
                        return await resp.json()
                    return await resp.read()
        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_BACKOFF ** attempt)
                log.warning("异步重试 %s %s: %s", method, url, e)
    raise RuntimeError(f"异步请求失败: {url}") from last_err


def get_json(url: str, params: dict | None = None) -> Any:
    return _request_sync("GET", url, params=params)


def get_bytes(url: str, **kwargs) -> bytes:
    data = _request_sync("GET", url, **kwargs)
    if isinstance(data, bytes):
        return data
    if isinstance(data, dict):
        raise RuntimeError("期望二进制内容，收到 JSON")
    return bytes(data)


def _format_download_error(
    err: Exception, url: str, *, request_token: str | None = None
) -> RuntimeError:
    if isinstance(err, requests.HTTPError) and err.response is not None:
        code = err.response.status_code
        if code == 401 and is_civitai_download_url(url):
            if not resolve_civitai_token(request_token):
                return RuntimeError(
                    "Civitai 下载需要 API Token（401 未授权）。请在前端「模型导入」页填写 API Key 并保存，"
                    "或在 https://civitai.com/user/account 创建后写入环境变量 CIVITAI_API_TOKEN。"
                )
            return RuntimeError(
                "Civitai 下载被拒绝（401）：请检查 CIVITAI_API_TOKEN 是否有效、未过期，"
                "或该模型是否要求登录/会员权限。"
            )
        if code == 403:
            return RuntimeError(f"Civitai 下载被拒绝（403）：{url}")
    msg = f"下载失败: {url}"
    if str(err):
        msg = f"{msg} ({err})"
    return RuntimeError(msg)


def download_file(
    url: str,
    dest_path: str | "Path",
    *,
    on_progress: Callable[[int, int | None], None] | None = None,
    civitai_token: str | None = None,
) -> None:
    """流式下载大文件，on_progress(downloaded_bytes, total_bytes|None)。"""
    from pathlib import Path

    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    fetch_url = apply_civitai_download_auth(url, request_token=civitai_token)
    headers = civitai_request_headers(
        {**DEFAULT_HEADERS, "Accept": "*/*"},
        request_token=civitai_token,
    )
    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            with requests.get(
                fetch_url,
                stream=True,
                timeout=(30, 3600),
                headers=headers,
                allow_redirects=True,
            ) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("content-length") or 0) or None
                downloaded = 0
                with open(dest, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=512 * 1024):
                        if not chunk:
                            continue
                        f.write(chunk)
                        downloaded += len(chunk)
                        if on_progress:
                            on_progress(downloaded, total)
                return
        except Exception as e:
            last_err = e
            if dest.is_file():
                dest.unlink(missing_ok=True)
            if attempt < MAX_RETRIES - 1:
                import time

                time.sleep(RETRY_BACKOFF ** attempt)
    raise _format_download_error(last_err, url, request_token=civitai_token) from last_err


async def get_json_async(url: str, params: dict | None = None) -> Any:
    return await _request_async("GET", url, params=params)
