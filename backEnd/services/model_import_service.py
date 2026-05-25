"""模型下载与导入 ComfyUI/models 目录。"""
from __future__ import annotations

import logging
import re
import threading
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlparse

from config import MODEL_PREVIEW_EXTENSIONS
import model_paths_service
from model_parser.http_client import download_file, get_bytes
from model_parser.media_utils import is_static_image_url, is_video_url
from model_parser.source_url_utils import format_with_source_url
from services import import_job_store

log = logging.getLogger("custom_project.model_import")

VALID_FOLDERS = model_paths_service.VALID_FOLDERS
MAX_PREVIEW_IMAGES = 3

ProgressFn = Callable[[dict[str, Any]], None]


def models_dir(folder: str) -> Path:
    return model_paths_service.resolve_folder_path(folder)


def _safe_filename(name: str) -> str:
    name = unquote(name).replace("\\", "/").split("/")[-1].strip()
    name = re.sub(r'[<>:"|?*]', "_", name)
    return name or "model.safetensors"


def _asset_dir_for_model(model_path: Path) -> Path:
    return model_path.parent / model_path.stem


def _write_description_txt(
    asset_dir: Path,
    translated: str,
    original: str,
    source: str,
    *,
    source_url: str = "",
) -> Path:
    asset_dir.mkdir(parents=True, exist_ok=True)
    body = (translated or "").strip()
    if not body:
        body = (original or "").strip()
    header = f"# 模型说明\n\n来源: {source}\n\n"
    if original.strip() and translated.strip() and original.strip() != translated.strip():
        header += "## 原文\n\n" + original.strip() + "\n\n## 译文\n\n"
    full = format_with_source_url(source_url, header + body)
    path = asset_dir / "模型说明.txt"
    path.write_text(full, encoding="utf-8")
    return path


def _emit(on_progress: ProgressFn | None, **fields: Any) -> None:
    if on_progress:
        on_progress(fields)


def _download_preview_images(
    asset_dir: Path,
    urls: list[str],
    *,
    max_images: int = MAX_PREVIEW_IMAGES,
    on_progress: ProgressFn | None = None,
) -> list[str]:
    urls = [
        u
        for u in urls
        if u and not is_video_url(u) and is_static_image_url(u)
    ][:max_images]
    saved = []
    total = len(urls)
    for i, url in enumerate(urls):
        _emit(
            on_progress,
            phase="downloading_preview",
            message=f"正在下载参考图 {i + 1}/{total}…",
            previewIndex=i + 1,
            previewTotal=total,
            progress=None,
        )
        try:
            data = get_bytes(url)
            ext = ".png"
            parsed = urlparse(url)
            suffix = Path(parsed.path).suffix.lower()
            if suffix in MODEL_PREVIEW_EXTENSIONS:
                ext = suffix
            dest = asset_dir / f"preview_{i + 1:02d}{ext}"
            dest.write_bytes(data)
            saved.append(str(dest))
        except Exception as e:
            log.warning("参考图下载失败 %s: %s", url, e)
    return saved


def import_model(
    *,
    folder: str,
    filename: str,
    download_url: str | None,
    download_model: bool,
    import_metadata_only: bool,
    description_original: str = "",
    description_translated: str = "",
    preview_image_urls: list[str] | None = None,
    source_label: str = "civitai",
    source_url: str = "",
    civitai_api_token: str = "",
    on_progress: ProgressFn | None = None,
) -> dict:
    root = models_dir(folder)
    root.mkdir(parents=True, exist_ok=True)
    filename = _safe_filename(filename)
    model_path = root / filename
    asset_dir = _asset_dir_for_model(model_path)
    preview_image_urls = (preview_image_urls or [])[:MAX_PREVIEW_IMAGES]

    _emit(on_progress, phase="checking", message="检查本地文件…", progress=0)

    conflict = model_path.is_file()
    if download_model and download_url and not import_metadata_only:
        if conflict:
            return {
                "ok": False,
                "conflict": True,
                "existing_file": str(model_path),
                "folder": folder,
                "filename": filename,
                "asset_dir": str(asset_dir),
                "message": "模型文件已存在。可仅导入说明与参考图（import_metadata_only=true）。",
            }

        _emit(on_progress, phase="downloading_model", message="正在下载模型文件…", progress=0)

        def _model_progress(done: int, total: int | None) -> None:
            if total and total > 0:
                pct = min(99.0, round(done * 100 / total, 1))
                _emit(
                    on_progress,
                    phase="downloading_model",
                    message=f"正在下载模型… {pct}%",
                    progress=pct,
                )
            else:
                mb = done / (1024 * 1024)
                _emit(
                    on_progress,
                    phase="downloading_model",
                    message=f"正在下载模型… 已下载 {mb:.1f} MB",
                    progress=0,
                )

        log.info("下载模型 %s -> %s", download_url, model_path)
        download_file(
            download_url,
            model_path,
            on_progress=_model_progress,
            civitai_token=civitai_api_token or None,
        )
        _emit(on_progress, phase="downloading_model", message="模型下载完成", progress=100)
        conflict = False

    txt_path = None
    images_saved: list[str] = []
    need_meta = (
        description_translated.strip()
        or description_original.strip()
        or preview_image_urls
    )
    if need_meta:
        _emit(on_progress, phase="writing_description", message="正在写入说明文件…", progress=100)
        if description_translated.strip() or description_original.strip():
            txt_path = _write_description_txt(
                asset_dir,
                description_translated,
                description_original,
                source_label,
                source_url=source_url,
            )
        if preview_image_urls:
            images_saved = _download_preview_images(
                asset_dir, preview_image_urls, on_progress=on_progress
            )

    _emit(on_progress, phase="completed", message="导入完成", progress=100)

    return {
        "ok": True,
        "conflict": False,
        "folder": folder,
        "filename": filename,
        "model_path": str(model_path),
        "model_exists": model_path.is_file(),
        "asset_dir": str(asset_dir),
        "description_txt": str(txt_path) if txt_path else None,
        "preview_images": images_saved,
        "preview_count": len(images_saved),
        "message": "导入完成",
    }


def run_import_job(job_id: str, body: dict[str, Any]) -> None:
    import_job_store.patch_job(job_id, status="running", phase="started", message="任务已开始…")

    def on_progress(evt: dict[str, Any]) -> None:
        patch: dict[str, Any] = {
            "status": "running",
            "phase": evt.get("phase", "running"),
            "message": evt.get("message", ""),
            "previewIndex": evt.get("previewIndex", 0),
            "previewTotal": evt.get("previewTotal", 0),
        }
        if evt.get("progress") is not None:
            patch["progress"] = evt["progress"]
        import_job_store.patch_job(job_id, **patch)

    try:
        result = import_model(
            folder=body["folder"],
            filename=body["filename"],
            download_url=body.get("download_url"),
            download_model=body.get("download_model", True),
            import_metadata_only=body.get("import_metadata_only", False),
            description_original=body.get("description_original", ""),
            description_translated=body.get("description_translated", ""),
            preview_image_urls=body.get("preview_image_urls"),
            source_label=body.get("site", "civitai"),
            source_url=body.get("source_url", ""),
            civitai_api_token=body.get("civitai_api_token", ""),
            on_progress=on_progress,
        )
        if not result.get("ok") and result.get("conflict"):
            import_job_store.patch_job(
                job_id,
                status="conflict",
                phase="conflict",
                message=result.get("message", "模型已存在"),
                result=result,
            )
            return
        import_job_store.patch_job(
            job_id,
            status="completed",
            phase="completed",
            message=result.get("message", "导入完成"),
            progress=100,
            result=result,
        )
    except Exception as e:
        log.exception("导入任务失败 job=%s", job_id)
        import_job_store.patch_job(
            job_id,
            status="failed",
            phase="failed",
            message=str(e),
            error=str(e),
        )


def start_import_async(body: dict[str, Any]) -> str:
    job_id = import_job_store.create_job()
    thread = threading.Thread(
        target=run_import_job,
        args=(job_id, body),
        name=f"model-import-{job_id}",
        daemon=True,
    )
    thread.start()
    return job_id


def map_civitai_type_to_folder(model_type: str) -> str:
    t = (model_type or "").lower()
    if "checkpoint" in t:
        return "checkpoints"
    if any(x in t for x in ("lora", "locon", "lycoris")):
        return "loras"
    return "checkpoints"
