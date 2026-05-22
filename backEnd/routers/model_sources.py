"""模型源解析与导入 API。"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from model_parser.site_router import SiteRouter
from services import import_job_store, model_import_service

log = logging.getLogger("custom_project.api.model_sources")

router = APIRouter(prefix="/api/model-sources", tags=["model-sources"])
_site_router = SiteRouter()


class CivitaiFavoriteBody(BaseModel):
    civitai_api_token: str = Field(default="", description="浏览器 localStorage 中的 Civitai API Key")
    item: dict = Field(description="browse 卡片字段快照")


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


@router.get("/civitai/browse/presets")
def civitai_browse_presets():
    from model_parser.civitai.browse_service import list_presets

    return {"ok": True, "presets": list_presets()}


@router.get("/civitai/tags")
def civitai_search_tags(
    query: str | None = Query(None, description="标签名关键词"),
    page: int = Query(1, ge=1, le=100),
    limit: int = Query(30, ge=1, le=200),
):
    from model_parser.civitai.browse_service import search_tags

    try:
        data = search_tags(query=query, page=page, limit=limit)
        return {"ok": True, **data}
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/civitai/browse")
def civitai_browse_models(
    types: str | None = Query(None, description="Checkpoint,LORA 等，逗号分隔"),
    sort: str = Query("Most Downloaded"),
    period: str = Query("Month"),
    query: str | None = Query(None, description="全文搜索（需 cursor 翻页）"),
    tag: str | None = Query(None, description="按标签筛选，如 anime、character"),
    cursor: str | None = Query(None, description="上一页返回的 nextCursor"),
    page: int = Query(1, ge=1, le=500, description="仅用于前端展示页码"),
    limit: int = Query(24, ge=1, le=100),
    base_models: str | None = Query(None, alias="baseModels"),
    content: str = Query(
        "sfw",
        description="内容范围：sfw=蓝站(SFW)、nsfw=红站(NSFW)、all=不筛选",
    ),
    nsfw: bool | None = Query(None, description="已废弃，请用 content=nsfw"),
):
    from model_parser.civitai.browse_service import browse_models

    try:
        data = browse_models(
            types=types,
            sort=sort,
            period=period,
            query=query,
            tag=tag,
            cursor=cursor,
            page=page,
            limit=limit,
            base_models=base_models,
            content=content,
            nsfw=nsfw,
        )
        return {"ok": True, **data}
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


def _civitai_token_from(
    header: str | None,
    query: str | None,
    body_token: str | None = None,
) -> str:
    for raw in (header, query, body_token):
        t = (raw or "").strip()
        if t:
            return t
    return ""


@router.get("/civitai/favorites")
def civitai_list_favorites(
    civitai_api_token: str = Query("", alias="civitaiApiToken"),
    x_civitai_api_key: str | None = Header(None, alias="X-Civitai-Api-Key"),
):
    import civitai_favorites_service as fav_svc

    token = _civitai_token_from(x_civitai_api_key, civitai_api_token)
    data = fav_svc.list_favorites(token)
    return {"ok": True, **data}


@router.post("/civitai/favorites")
def civitai_add_favorite(body: CivitaiFavoriteBody):
    import civitai_favorites_service as fav_svc

    try:
        data = fav_svc.add_favorite(body.civitai_api_token, body.item)
        return {"ok": True, **data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/civitai/favorites/{model_id}")
def civitai_remove_favorite(
    model_id: str,
    civitai_api_token: str = Query("", alias="civitaiApiToken"),
    x_civitai_api_key: str | None = Header(None, alias="X-Civitai-Api-Key"),
):
    import civitai_favorites_service as fav_svc

    token = _civitai_token_from(x_civitai_api_key, civitai_api_token)
    try:
        data = fav_svc.remove_favorite(token, model_id)
        return {"ok": True, **data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


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
