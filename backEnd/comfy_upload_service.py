"""上传图片到 ComfyUI input 目录，供 LoadImage / LoadImageMask 使用。"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config import COMFYUI_URL

log = logging.getLogger("custom_project.comfy_upload")

MAX_UPLOAD_BYTES = 32 * 1024 * 1024


def _multipart_body(
    fields: dict[str, str],
    file_field: str,
    filename: str,
    data: bytes,
    content_type: str = "image/png",
) -> tuple[bytes, str]:
    boundary = f"----comfyupload{uuid.uuid4().hex}"
    lines: list[bytes] = []
    for name, value in fields.items():
        lines.append(f"--{boundary}\r\n".encode())
        lines.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        lines.append(f"{value}\r\n".encode())
    lines.append(f"--{boundary}\r\n".encode())
    lines.append(
        f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'.encode()
    )
    lines.append(f"Content-Type: {content_type}\r\n\r\n".encode())
    lines.append(data)
    lines.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(lines)
    return body, f"multipart/form-data; boundary={boundary}"


def upload_image(
    data: bytes,
    filename: str,
    *,
    content_type: str | None = None,
    overwrite: bool = True,
    upload_type: str = "input",
    subfolder: str = "",
) -> dict[str, Any]:
    if not data:
        raise ValueError("文件为空")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"文件过大（上限 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB）")

    safe_name = (filename or "upload.png").replace("\\", "/").split("/")[-1].strip()
    if not safe_name:
        safe_name = "upload.png"

    fields: dict[str, str] = {"type": upload_type, "subfolder": subfolder}
    if overwrite:
        fields["overwrite"] = "true"

    body, content_type_hdr = _multipart_body(
        fields,
        "image",
        safe_name,
        data,
        content_type or "application/octet-stream",
    )
    url = f"{COMFYUI_URL.rstrip('/')}/upload/image"
    req = Request(
        url,
        data=body,
        headers={"Content-Type": content_type_hdr},
        method="POST",
    )
    try:
        with urlopen(req, timeout=120) as resp:
            raw = resp.read()
            if not raw:
                raise RuntimeError("ComfyUI 上传无响应")
            out = json.loads(raw.decode("utf-8"))
    except HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ComfyUI 上传失败 {e.code}: {detail}") from e
    except URLError as e:
        raise RuntimeError(f"无法连接 ComfyUI ({COMFYUI_URL})") from e

    name = str(out.get("name") or safe_name)
    log.info("uploaded to ComfyUI input: %s", name)
    return {
        "name": name,
        "subfolder": str(out.get("subfolder") or ""),
        "type": str(out.get("type") or upload_type),
    }
