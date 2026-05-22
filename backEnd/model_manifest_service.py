"""本地模型清单导出与按清单批量下载（已存在则跳过）。"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from config import PROJECT_ROOT
from model_node_catalog_service import load_store
from model_parser.site_router import SiteRouter
from model_preview_service import VALID_FOLDERS, models_folder_dir, read_summary_txt_for_model
from services import import_job_store, model_import_service

log = logging.getLogger("custom_project.model_manifest")

MANIFEST_VERSION = 1
DEFAULT_MANIFEST_PATH = PROJECT_ROOT / "config" / "models_manifest.json"
MODEL_EXTENSIONS = frozenset({".safetensors", ".ckpt", ".pt", ".pth", ".bin"})
_site_router = SiteRouter()

ProgressFn = Callable[[dict[str, Any]], None]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_model_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in MODEL_EXTENSIONS


def list_local_model_names(folder: str) -> list[str]:
    """扫描 models/{folder} 下权重文件（含子目录，相对路径）。"""
    if folder not in VALID_FOLDERS:
        raise ValueError(f"不支持的目录: {folder}")
    root = models_folder_dir(folder)
    if not root.is_dir():
        return []
    names: list[str] = []
    for path in root.rglob("*"):
        if _is_model_file(path):
            names.append(str(path.relative_to(root)).replace("\\", "/"))
    return sorted(set(names))


def model_file_path(folder: str, name: str) -> Path:
    return models_folder_dir(folder) / name.replace("\\", "/")


def is_model_present(folder: str, name: str) -> bool:
    return model_file_path(folder, name).is_file()


def _parse_ids_from_source_url(source_url: str) -> dict[str, Any]:
    url = (source_url or "").strip()
    if not url:
        return {}
    try:
        site = SiteRouter.detect_site(url)
    except ValueError:
        return {}
    try:
        if site == "civitai":
            from model_parser.civitai.parser import CivitaiParser

            ids = CivitaiParser.parse_url(url)
            return {
                "site": "civitai",
                "model_id": str(ids.get("modelId") or ""),
                "version_id": str(ids["modelVersionId"]) if ids.get("modelVersionId") else "",
            }
        from model_parser.shakker.parser import ShakkerParser

        ids = ShakkerParser.parse_url(url)
        return {
            "site": "shakker",
            "model_id": str(ids.get("modelUuid") or ""),
            "version_id": str(ids.get("versionUuid") or ""),
        }
    except ValueError:
        return {"site": site}


def build_manifest_entry(folder: str, name: str) -> dict[str, Any]:
    path = model_file_path(folder, name)
    summary = read_summary_txt_for_model(folder, name)
    source_url = (summary or {}).get("sourceUrl") or ""
    ids = _parse_ids_from_source_url(source_url)
    size_bytes = path.stat().st_size if path.is_file() else 0
    asset_dir = (summary or {}).get("asset_dir") or Path(name).stem
    return {
        "folder": folder,
        "name": name,
        "local_exists": path.is_file(),
        "size_bytes": size_bytes,
        "source_url": source_url,
        "site": ids.get("site") or "",
        "model_id": ids.get("model_id") or "",
        "version_id": ids.get("version_id") or "",
        "has_summary": summary is not None,
        "asset_dir": asset_dir,
    }


def export_manifest(*, include_catalog: bool = True) -> dict[str, Any]:
    checkpoints = [build_manifest_entry("checkpoints", n) for n in list_local_model_names("checkpoints")]
    loras = [build_manifest_entry("loras", n) for n in list_local_model_names("loras")]
    manifest: dict[str, Any] = {
        "manifest_version": MANIFEST_VERSION,
        "exported_at": _utc_now(),
        "comfyui_root": str(model_import_service.models_dir("checkpoints").parent.parent),
        "checkpoints": checkpoints,
        "loras": loras,
        "stats": {
            "checkpoints_total": len(checkpoints),
            "loras_total": len(loras),
            "with_source_url": sum(
                1 for e in checkpoints + loras if (e.get("source_url") or "").strip()
            ),
            "local_exists": sum(
                1 for e in checkpoints + loras if e.get("local_exists")
            ),
        },
    }
    if include_catalog:
        store = load_store()
        manifest["catalog"] = {
            "default_checkpoint": store.get("default_checkpoint", ""),
            "loras": store.get("loras", {}),
            "checkpoint_lora_compat": store.get("checkpoint_lora_compat", {}),
        }
    return manifest


def save_manifest(manifest: dict[str, Any], path: Path | None = None) -> Path:
    target = path or DEFAULT_MANIFEST_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    target = path or DEFAULT_MANIFEST_PATH
    if not target.is_file():
        raise FileNotFoundError(f"清单文件不存在: {target}")
    with open(target, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("清单格式无效")
    return data


def iter_manifest_entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for key in ("checkpoints", "loras"):
        block = manifest.get(key)
        if isinstance(block, list):
            for item in block:
                if isinstance(item, dict) and item.get("name"):
                    row = dict(item)
                    row.setdefault("folder", key if key.endswith("s") else f"{key}s")
                    if row["folder"] == "checkpoint":
                        row["folder"] = "checkpoints"
                    entries.append(row)
    if not entries and isinstance(manifest.get("models"), list):
        entries = [dict(m) for m in manifest["models"] if isinstance(m, dict)]
    return entries


def pick_download_file(files: list[dict], preferred_name: str | None) -> dict | None:
    if not files:
        return None
    pref = (preferred_name or "").strip()
    if pref:
        for f in files:
            if (f.get("name") or "") == pref:
                return f
        for f in files:
            if pref in (f.get("name") or ""):
                return f
    for f in files:
        if (f.get("type") or "").lower() == "model":
            n = (f.get("name") or "").lower()
            if n.endswith(".safetensors"):
                return f
    for f in files:
        if (f.get("type") or "").lower() == "model":
            return f
    for f in files:
        if (f.get("name") or "").lower().endswith(".safetensors"):
            return f
    return files[0]


def resolve_import_body(entry: dict[str, Any], *, civitai_api_token: str = "") -> dict[str, Any]:
    """根据清单条目解析远程版本并构造 import_model 参数。"""
    folder = str(entry.get("folder") or "checkpoints").strip().lower()
    filename = str(entry.get("name") or "").strip()
    source_url = str(entry.get("source_url") or "").strip()
    if folder not in VALID_FOLDERS:
        raise ValueError(f"无效 folder: {folder}")
    if not filename:
        raise ValueError("缺少模型文件名 name")
    if not source_url:
        raise ValueError("缺少 source_url，无法远程下载")

    parsed = _site_router.parse_url(source_url)
    site = (parsed.get("site") or entry.get("site") or "civitai").lower()
    model_id = str(entry.get("model_id") or parsed.get("model", {}).get("id") or "").strip()
    version_id = entry.get("version_id") or parsed.get("selectedVersion")
    if version_id is not None:
        version_id = str(version_id).strip()
    if not version_id:
        versions = parsed.get("versions") or []
        if versions:
            sel = next((v for v in versions if v.get("selected")), versions[0])
            version_id = str(sel.get("versionId") or sel.get("versionUuid") or "").strip()
    if not version_id:
        raise ValueError(f"无法确定版本 ID: {filename}")

    model_plain = ""
    if site == "civitai" and model_id:
        try:
            from model_parser.html_utils import html_to_plain_text

            mdata = _site_router._civitai_models.fetch_model(int(model_id))
            model_plain = html_to_plain_text(mdata.get("description") or "")
        except Exception:
            pass

    detail = _site_router.get_version_detail(
        site,
        str(version_id),
        model_id=str(model_id) if model_id else None,
        model_description_plain=model_plain,
    )
    files = detail.get("files") or []
    picked = pick_download_file(files, filename)
    if not picked or not picked.get("downloadUrl"):
        raise ValueError(f"未找到可下载文件: {filename}")

    desc = detail.get("description") or detail.get("modelDescription") or ""
    from model_parser.source_url_utils import format_with_source_url

    description_original = format_with_source_url(source_url, desc)
    preview_urls = detail.get("staticPreviewUrls") or []
    if not preview_urls and detail.get("previewImage"):
        u = detail["previewImage"].get("url")
        if u:
            preview_urls = [u]

    return {
        "site": site,
        "folder": folder,
        "filename": picked.get("name") or filename,
        "download_url": picked.get("downloadUrl"),
        "download_model": True,
        "import_metadata_only": False,
        "description_original": description_original,
        "description_translated": "",
        "preview_image_urls": preview_urls[: model_import_service.MAX_PREVIEW_IMAGES],
        "source_url": source_url,
        "civitai_api_token": civitai_api_token,
    }


def _emit(on_progress: ProgressFn | None, **fields: Any) -> None:
    if on_progress:
        on_progress(fields)


def import_all_from_manifest(
    manifest: dict[str, Any],
    *,
    civitai_api_token: str = "",
    skip_existing: bool = True,
    import_metadata_when_exists: bool = False,
    on_progress: ProgressFn | None = None,
) -> dict[str, Any]:
    entries = iter_manifest_entries(manifest)
    total = len(entries)
    results: list[dict[str, Any]] = []
    counts = {"skipped": 0, "downloaded": 0, "failed": 0, "no_source": 0}

    _emit(
        on_progress,
        phase="batch_started",
        message=f"共 {total} 个条目",
        progress=0,
        total=total,
        index=0,
    )

    for i, entry in enumerate(entries):
        folder = str(entry.get("folder") or "checkpoints")
        name = str(entry.get("name") or "")
        pct = round((i / max(total, 1)) * 100, 1)
        _emit(
            on_progress,
            phase="batch_item",
            message=f"[{i + 1}/{total}] {name}",
            progress=pct,
            total=total,
            index=i + 1,
            currentName=name,
        )

        row: dict[str, Any] = {"folder": folder, "name": name, "status": "pending"}

        if skip_existing and is_model_present(folder, name):
            row["status"] = "skipped"
            row["message"] = "本地已存在，已跳过"
            counts["skipped"] += 1
            results.append(row)
            continue

        source_url = (entry.get("source_url") or "").strip()
        if not source_url:
            row["status"] = "no_source"
            row["message"] = "无访问链接，无法下载"
            counts["no_source"] += 1
            results.append(row)
            continue

        try:
            body = resolve_import_body(entry, civitai_api_token=civitai_api_token)
            if import_metadata_when_exists and is_model_present(folder, body["filename"]):
                body["download_model"] = False
                body["import_metadata_only"] = True
            result = model_import_service.import_model(
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
            )
            if result.get("ok"):
                row["status"] = "downloaded" if result.get("model_exists") else "ok"
                row["message"] = result.get("message", "完成")
                row["model_path"] = result.get("model_path")
                counts["downloaded"] += 1
            elif result.get("conflict"):
                row["status"] = "skipped"
                row["message"] = result.get("message", "已存在")
                counts["skipped"] += 1
            else:
                row["status"] = "failed"
                row["message"] = result.get("message", "导入失败")
                counts["failed"] += 1
        except Exception as e:
            log.exception("批量导入失败 %s/%s", folder, name)
            row["status"] = "failed"
            row["message"] = str(e)
            counts["failed"] += 1

        results.append(row)

    summary = {
        "ok": counts["failed"] == 0,
        "total": total,
        "counts": counts,
        "results": results,
        "finished_at": _utc_now(),
    }
    _emit(
        on_progress,
        phase="batch_completed",
        message=(
            f"完成：下载 {counts['downloaded']}，跳过 {counts['skipped']}，"
            f"无链接 {counts['no_source']}，失败 {counts['failed']}"
        ),
        progress=100,
        total=total,
        index=total,
        summary=summary,
    )
    return summary


def run_batch_import_job(job_id: str, body: dict[str, Any]) -> None:
    import_job_store.patch_job(job_id, status="running", phase="started", message="批量任务已开始…")

    def on_progress(evt: dict[str, Any]) -> None:
        patch: dict[str, Any] = {
            "status": "running",
            "phase": evt.get("phase", "running"),
            "message": evt.get("message", ""),
            "total": evt.get("total", 0),
            "index": evt.get("index", 0),
            "currentName": evt.get("currentName", ""),
        }
        if evt.get("progress") is not None:
            patch["progress"] = evt["progress"]
        if evt.get("summary") is not None:
            patch["batchSummary"] = evt["summary"]
        import_job_store.patch_job(job_id, **patch)

    try:
        manifest = body.get("manifest")
        if manifest is None:
            path = body.get("manifest_path")
            manifest = load_manifest(Path(path) if path else None)
        summary = import_all_from_manifest(
            manifest,
            civitai_api_token=body.get("civitai_api_token", ""),
            skip_existing=body.get("skip_existing", True),
            import_metadata_when_exists=body.get("import_metadata_when_exists", False),
            on_progress=on_progress,
        )
        import_job_store.patch_job(
            job_id,
            status="completed" if summary.get("ok") else "completed_with_errors",
            phase="completed",
            message=(
                f"下载 {summary['counts'].get('downloaded', 0)}，"
                f"跳过 {summary['counts'].get('skipped', 0)}，"
                f"失败 {summary['counts'].get('failed', 0)}"
            ),
            progress=100,
            result=summary,
            batchSummary=summary,
        )
    except Exception as e:
        log.exception("批量清单导入失败 job=%s", job_id)
        import_job_store.patch_job(
            job_id,
            status="failed",
            phase="failed",
            message=str(e),
            error=str(e),
        )


def start_batch_import_async(body: dict[str, Any]) -> str:
    job_id = import_job_store.create_job()
    import_job_store.patch_job(job_id, jobType="manifest_batch")
    thread = threading.Thread(
        target=run_batch_import_job,
        args=(job_id, body),
        name=f"manifest-batch-{job_id}",
        daemon=True,
    )
    thread.start()
    return job_id
