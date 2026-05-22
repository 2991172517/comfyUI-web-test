"""模型清单导出与批量下载 API。"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import model_manifest_service as manifest_svc
from services import import_job_store

log = logging.getLogger("custom_project.api.model_manifest")

router = APIRouter(prefix="/api/model-manifest", tags=["model-manifest"])


class ImportManifestBody(BaseModel):
    manifest: dict | None = Field(default=None, description="直接传入清单 JSON")
    manifest_path: str | None = Field(
        default=None,
        description="相对 CustomProject 或绝对路径；默认 config/models_manifest.json",
    )
    civitai_api_token: str = Field(default="", description="Civitai API Key")
    skip_existing: bool = Field(default=True, description="本地已有权重则跳过")
    import_metadata_when_exists: bool = Field(
        default=False,
        description="已存在时仅导入说明与预览图",
    )


@router.post("/export")
def export_models_manifest(
    save: bool = Query(True, description="是否写入 config/models_manifest.json"),
    include_catalog: bool = Query(True, description="是否附带 model_node_defaults 摘要"),
):
    try:
        manifest = manifest_svc.export_manifest(include_catalog=include_catalog)
        path = None
        if save:
            path = manifest_svc.save_manifest(manifest)
        return {
            "ok": True,
            "manifest": manifest,
            "savedPath": str(path) if path else None,
            "stats": manifest.get("stats"),
        }
    except Exception as e:
        log.exception("导出模型清单失败")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/export/file")
def download_models_manifest_file():
    path = manifest_svc.DEFAULT_MANIFEST_PATH
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="清单文件不存在，请先 POST /api/model-manifest/export",
        )
    return FileResponse(
        path,
        media_type="application/json",
        filename="models_manifest.json",
    )


@router.post("/import-all")
def start_import_all_from_manifest(body: ImportManifestBody):
    """按清单批量下载；本地已有则跳过。返回 jobId，轮询 GET /import/{jobId}。"""
    try:
        payload: dict = {
            "manifest": body.manifest,
            "manifest_path": body.manifest_path,
            "civitai_api_token": body.civitai_api_token,
            "skip_existing": body.skip_existing,
            "import_metadata_when_exists": body.import_metadata_when_exists,
        }
        if body.manifest is None and not body.manifest_path:
            default = manifest_svc.DEFAULT_MANIFEST_PATH
            if not default.is_file():
                raise ValueError(
                    "未提供 manifest，且默认清单不存在。请先导出或上传 models_manifest.json"
                )
        job_id = manifest_svc.start_batch_import_async(payload)
        return {"ok": True, "jobId": job_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        log.exception("启动批量导入失败")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/import/{job_id}")
def get_manifest_import_status(job_id: str):
    job = import_job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"ok": True, **job}
