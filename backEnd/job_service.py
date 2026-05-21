import os
from typing import Any
from urllib.parse import urlencode

from config import COMFYUI_ROOT

import comfy_client
import ws_tracker

OUTPUT_DIR = COMFYUI_ROOT / "output"
TEMP_DIR = COMFYUI_ROOT / "temp"
INPUT_DIR = COMFYUI_ROOT / "input"

TYPE_DIRS = {
    "output": OUTPUT_DIR,
    "temp": TEMP_DIR,
    "input": INPUT_DIR,
}


def build_view_url(filename: str, subfolder: str = "", folder_type: str = "output") -> str:
    params = urlencode({
        "filename": filename,
        "subfolder": subfolder or "",
        "type": folder_type,
    })
    return f"/api/view?{params}"


def collect_images_from_outputs(outputs: dict) -> list[dict]:
    images = []
    if not outputs:
        return images
    for node_id, node_outputs in outputs.items():
        if not isinstance(node_outputs, dict):
            continue
        for media_type, items in node_outputs.items():
            if media_type != "images" or not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict) or "filename" not in item:
                    continue
                filename = item["filename"]
                subfolder = item.get("subfolder") or ""
                folder_type = item.get("type", "output")
                images.append({
                    "id": f"{node_id}:{filename}",
                    "node_id": str(node_id),
                    "filename": filename,
                    "subfolder": subfolder,
                    "type": folder_type,
                    "url": build_view_url(filename, subfolder, folder_type),
                })
    return images


def resolve_image_path(filename: str, subfolder: str = "", folder_type: str = "output") -> str:
    base = TYPE_DIRS.get(folder_type, OUTPUT_DIR)
    if subfolder:
        path = os.path.join(base, subfolder, filename)
    else:
        path = os.path.join(base, filename)
    return os.path.normpath(os.path.abspath(path))


def safe_delete_image_file(filename: str, subfolder: str = "", folder_type: str = "output") -> bool:
    base = TYPE_DIRS.get(folder_type, OUTPUT_DIR)
    base_abs = os.path.abspath(base)
    filepath = resolve_image_path(filename, subfolder, folder_type)
    if not filepath.startswith(base_abs):
        raise ValueError("非法文件路径")
    if os.path.isfile(filepath):
        os.remove(filepath)
        return True
    return False


def get_job_detail(prompt_id: str) -> dict:
    tracked = ws_tracker.get_tracker_state(prompt_id)

    try:
        job = comfy_client.get_job(prompt_id)
    except RuntimeError as e:
        if "404" in str(e):
            if tracked:
                return _build_job_response(prompt_id, tracked, None)
            return {"id": prompt_id, "status": "unknown", "images": [], "message": "任务不存在"}
        raise

    return _build_job_response(prompt_id, tracked, job)


def _build_job_response(prompt_id: str, tracked: dict, job: dict | None) -> dict:
    status = job.get("status", "unknown") if job else tracked.get("status", "unknown")
    images = []
    message = ""

    if tracked.get("error") and status not in ("completed",):
        status = "failed"

    if status == "completed":
        if job:
            images = collect_images_from_outputs(job.get("outputs", {}))
        if images:
            try:
                import history_service
                history_service.try_finish_single_record(prompt_id)
            except Exception:
                pass
        if not images:
            message = "任务已完成，但未找到输出图片"
    elif status == "failed":
        err = (job or {}).get("execution_error") or {}
        message = tracked.get("error") or err.get("exception_message") or err.get("message") or "生成失败"
    elif status == "cancelled":
        message = "任务已取消或中断"
    elif status in ("in_progress", "finalizing"):
        node = tracked.get("current_node")
        message = f"正在生成…" + (f"（节点 #{node}）" if node else "")
    elif status == "pending":
        message = "排队等待中…"
    elif tracked.get("status") == "finalizing":
        status = "finalizing"
        message = "收尾中，正在读取输出…"

    return {
        "id": prompt_id,
        "status": status,
        "images": images,
        "message": message,
        "current_node": tracked.get("current_node"),
        "progress": tracked.get("progress"),
        "preview_output": (job or {}).get("preview_output"),
        "outputs_count": (job or {}).get("outputs_count", 0),
        "execution_error": (job or {}).get("execution_error"),
    }


def delete_job_outputs(prompt_id: str, images: list[dict] | None = None) -> dict:
    if images is None:
        detail = get_job_detail(prompt_id)
        images = detail.get("images", [])

    deleted = []
    failed = []
    for img in images:
        try:
            if safe_delete_image_file(img["filename"], img.get("subfolder", ""), img.get("type", "output")):
                deleted.append(img["filename"])
        except OSError as e:
            failed.append({"filename": img["filename"], "error": str(e)})

    try:
        comfy_client.delete_history(prompt_id)
    except RuntimeError:
        pass

    return {
        "ok": True,
        "prompt_id": prompt_id,
        "deleted_files": deleted,
        "failed": failed,
    }
