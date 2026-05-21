import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from config import COMFYUI_URL

_object_info_cache: dict | None = None


def _request(method: str, path: str, data: dict | None = None, timeout: float = 120) -> Any:
    url = f"{COMFYUI_URL.rstrip('/')}{path}"
    body = None
    headers = {}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            if not raw:
                return None
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ComfyUI {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"无法连接 ComfyUI ({COMFYUI_URL})，请先启动 ComfyUI") from e


def health() -> dict:
    return _request("GET", "/system_stats")


def get_object_info(refresh: bool = False) -> dict:
    global _object_info_cache
    if _object_info_cache is None or refresh:
        _object_info_cache = _request("GET", "/object_info")
    return _object_info_cache


def list_models(folder: str) -> list[str]:
    return _request("GET", f"/models/{folder}")


def queue_prompt(
    prompt: dict,
    client_id: str | None = None,
    prompt_id: str | None = None,
) -> dict:
    payload: dict = {"prompt": prompt}
    if client_id:
        payload["client_id"] = client_id
    if prompt_id:
        payload["prompt_id"] = prompt_id
    return _request("POST", "/prompt", payload)


def get_history(prompt_id: str) -> dict:
    return _request("GET", f"/history/{prompt_id}")


def get_queue() -> dict:
    return _request("GET", "/queue")


def get_job(prompt_id: str) -> dict:
    return _request("GET", f"/api/jobs/{prompt_id}")


def delete_history(prompt_id: str) -> None:
    _request("POST", "/history", {"delete": [prompt_id]})


def interrupt() -> None:
    _request("POST", "/interrupt")


def fetch_view_image(filename: str, subfolder: str = "", folder_type: str = "output") -> tuple[bytes, str]:
    params = urllib.parse.urlencode({
        "filename": filename,
        "subfolder": subfolder or "",
        "type": folder_type,
    })
    url = f"{COMFYUI_URL.rstrip('/')}/view?{params}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            content_type = resp.headers.get("Content-Type", "image/png")
            return resp.read(), content_type
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ComfyUI {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"无法连接 ComfyUI ({COMFYUI_URL})") from e
