"""模型源解析与导入 API。"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from model_parser.site_router import SiteRouter
from services import import_job_store, model_import_service

log = logging.getLogger("custom_project.api.model_sources")

router = APIRouter(prefix="/api/model-sources", tags=["model-sources"])
_site_router = SiteRouter()


class ImportModelBody(BaseModel):
    site: str
    folder: str = Field(description="checkpoints | loras")
    filename: str
    download_url: str | None = None
    download_model: bool = True
    import_metadata_only: bool = False
    description_original: str = ""
    description_translated: str = ""
    preview_image_urls: list[str] = Field(default_factory=list)
    model_id: str | None = None
    version_id: str | int | None = None
    source_url: str = ""
    civitai_api_token: str = Field(default="", description="前端 localStorage 中的 Civitai API Key")


@router.get("/settings")
def model_sources_settings():
    from model_parser.civitai.auth import get_civitai_api_token

    token = get_civitai_api_token()
    return {
        "ok": True,
        "civitaiTokenConfigured": bool(token),
        "civitaiTokenHint": (
            "已配置 CIVITAI_API_TOKEN"
            if token
            else "服务端未配置 Token；可在前端填写 API Key（保存于浏览器 localStorage）"
        ),
        "civitaiAccountUrl": "https://civitai.com/user/account",
    }


@router.get("/parse")
def parse_model_url(url: str = Query(..., description="Civitai 或 Shakker 模型页链接")):
    try:
        result = _site_router.parse_url(url)
        return {"ok": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/version/{site}/{version_id}")
def get_version_detail(
    site: str,
    version_id: str,
    model_id: str | None = Query(None, description="Shakker 需要 modelUuid"),
    model_description: str | None = Query(
        None,
        description="已废弃：请仅传 modelId，由服务端拉取模型页说明",
    ),
):
    try:
        # 不再通过 query 传长文本（易触发 413）；有 modelId 时由服务端获取
        plain = (model_description or "").strip() if model_description else ""
        detail = _site_router.get_version_detail(
            site,
            version_id,
            model_id=model_id,
            model_description_plain=plain,
        )
        return {"ok": True, **detail}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post("/import")
def start_import(body: ImportModelBody):
    """启动异步导入，返回 jobId；轮询 GET /import/{jobId} 获取进度。"""
    try:
        preview_urls = (body.preview_image_urls or [])[: model_import_service.MAX_PREVIEW_IMAGES]
        job_id = model_import_service.start_import_async(
            {
                "site": body.site,
                "folder": body.folder,
                "filename": body.filename,
                "download_url": body.download_url,
                "download_model": body.download_model,
                "import_metadata_only": body.import_metadata_only,
                "description_original": body.description_original,
                "description_translated": body.description_translated,
                "preview_image_urls": preview_urls,
                "source_url": body.source_url,
                "civitai_api_token": body.civitai_api_token,
            }
        )
        return {"ok": True, "jobId": job_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        log.exception("启动导入失败")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/import/{job_id}")
def get_import_status(job_id: str):
    job = import_job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="导入任务不存在")
    return {"ok": True, **job}
