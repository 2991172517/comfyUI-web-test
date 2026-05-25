"""提示词词库补全 API。"""
from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

import vocabulary as vocabulary_service
from vocabulary import manager as vocabulary_manager

log = logging.getLogger("custom_project.api.vocabulary")

router = APIRouter(prefix="/api/vocabulary", tags=["vocabulary"])


@router.get("/suggest")
def vocabulary_suggest(
    q: str = Query("", description="当前正在输入的 token"),
    limit: int = Query(12, ge=1, le=50),
):
    q = (q or "").strip()
    if len(q) < 1:
        return {"items": [], "query": q, "tookMs": 0}
    if len(q) > 64:
        return {"items": [], "query": q, "tookMs": 0}
    try:
        return vocabulary_service.suggest(q, limit=limit)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        log.exception("vocabulary suggest failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/stats")
def vocabulary_stats():
    try:
        stats = vocabulary_service.index_stats()
        return stats
    except Exception as e:
        log.exception("vocabulary stats failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


class ResolveBody(BaseModel):
    values: list[str] = Field(default_factory=list, max_length=2000)


@router.post("/resolve")
def vocabulary_resolve(body: ResolveBody):
    try:
        return vocabulary_service.resolve(body.values)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        log.exception("vocabulary resolve failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/merge-manifest")
async def vocabulary_merge_manifest(
    file: UploadFile = File(..., description="manifest v2 JSON 文件"),
    dry_run: bool = Query(False, description="仅预览合并统计，不写盘"),
):
    """并入主 manifest 并自动重建索引（无需重启后端）。"""
    try:
        raw = await file.read()
        if len(raw) > 80 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="文件过大（上限 80MB）")
        return vocabulary_service.merge_manifest_upload(raw, dry_run=dry_run)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        log.exception("vocabulary merge-manifest failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


class MergeManifestBody(BaseModel):
    version: int = 2
    rootCategoryId: str | None = None
    rootCategoryName: str | None = None
    categories: list[dict] = Field(default_factory=list)
    prompts: list[dict] = Field(default_factory=list)


@router.post("/merge-manifest/json")
def vocabulary_merge_manifest_json(
    body: MergeManifestBody,
    dry_run: bool = Query(False),
):
    """JSON body 方式并入（与文件上传等价）。"""
    try:
        return vocabulary_service.merge_manifest_json(
            body.model_dump(),
            dry_run=dry_run,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        log.exception("vocabulary merge-manifest json failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/merge-manifest/schema")
def vocabulary_merge_schema():
    """返回 manifest v2 字段说明（供前端展示）。"""
    return {
        "ok": True,
        "version": 2,
        "description": "Prompt Gallery / WeiLin 导出格式",
        "requiredTopLevel": ["categories", "prompts"],
        "optionalTopLevel": ["version", "rootCategoryId", "rootCategoryName", "exportedAt"],
        "categoryFields": {
            "id": "分类唯一 ID（字符串）",
            "name": "显示名称",
            "parentId": "父分类 id，顶层父为 root 或根节点 id",
            "order": "排序整数",
        },
        "promptFields": {
            "id": "可选，词条 ID",
            "name": "显示名 / 中文说明",
            "value": "写入提示词的英文 tag 文本（去重键之一）",
            "categoryId": "所属分类 id（去重键之一）",
        },
        "dedupRules": [
            "分类：相同 id 已存在则跳过",
            "词条：相同 categoryId + value（忽略大小写）只保留一条",
        ],
        "example": {
            "version": 2,
            "rootCategoryId": "my-root-id",
            "rootCategoryName": "导入词库",
            "categories": [
                {"id": "my-root-id", "name": "导入词库", "parentId": "root", "order": 0},
                {"id": "cat-1", "name": "人物", "parentId": "my-root-id", "order": 1},
            ],
            "prompts": [
                {
                    "id": "p-1",
                    "name": "1girl",
                    "value": "1girl",
                    "categoryId": "cat-1",
                }
            ],
        },
    }


@router.post("/rebuild")
def vocabulary_rebuild():
    try:
        vocabulary_service.ensure_index(force=True)
        return vocabulary_service.index_stats()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        log.exception("vocabulary rebuild failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/categories/tree")
def vocabulary_category_tree():
    try:
        vocabulary_service.ensure_index()
        return vocabulary_manager.category_tree()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        log.exception("vocabulary category tree failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/prompts")
def vocabulary_list_prompts(
    categoryId: str = Query(..., min_length=1),
    q: str = Query(""),
    offset: int = Query(0, ge=0),
    limit: int = Query(80, ge=1, le=200),
):
    try:
        return vocabulary_manager.list_prompts(
            categoryId, q=q, offset=offset, limit=limit
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        log.exception("vocabulary list prompts failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


class PromptCreateBody(BaseModel):
    categoryId: str = Field(..., min_length=1)
    value: str = Field(..., min_length=1, max_length=512)
    name: str = Field(default="", max_length=256)


@router.post("/prompts")
def vocabulary_create_prompt(body: PromptCreateBody):
    try:
        return vocabulary_manager.add_prompt(
            category_id=body.categoryId,
            value=body.value.strip(),
            name=(body.name or body.value).strip(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        log.exception("vocabulary create prompt failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


class PromptDeleteBody(BaseModel):
    categoryId: str = Field(..., min_length=1)
    value: str = Field(..., min_length=1, max_length=512)


@router.delete("/prompts")
def vocabulary_delete_prompt(body: PromptDeleteBody):
    try:
        result = vocabulary_manager.delete_prompt(
            category_id=body.categoryId,
            value=body.value.strip(),
        )
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail="词条不存在")
        return result
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        log.exception("vocabulary delete prompt failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


class SettingsBody(BaseModel):
    defaultWeight: float = Field(..., ge=0.05, le=2.0)


class TagPreferenceBody(BaseModel):
    categoryId: str = Field(..., min_length=1)
    value: str = Field(..., min_length=1, max_length=512)
    preference: str = Field(
        default="neutral",
        description="like | dislike | neutral（清除偏好）",
    )


class CategoryDeleteBody(BaseModel):
    categoryId: str = Field(..., min_length=1)


@router.get("/settings")
def vocabulary_get_settings():
    try:
        return vocabulary_manager.get_settings()
    except Exception as e:
        log.exception("vocabulary get settings failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/tag-preference")
def vocabulary_set_tag_preference(body: TagPreferenceBody):
    try:
        return vocabulary_manager.set_prompt_preference(
            category_id=body.categoryId,
            value=body.value.strip(),
            preference=body.preference,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        log.exception("vocabulary set tag preference failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/categories")
def vocabulary_delete_category(body: CategoryDeleteBody):
    try:
        return vocabulary_manager.delete_category(category_id=body.categoryId)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        log.exception("vocabulary delete category failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/categories/{category_id}/count")
def vocabulary_category_count(category_id: str):
    try:
        total = vocabulary_manager.category_prompt_count(category_id)
        return {"categoryId": category_id, "total": total}
    except Exception as e:
        log.exception("vocabulary category count failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/settings")
def vocabulary_put_settings(body: SettingsBody):
    try:
        return vocabulary_manager.update_settings(default_weight=body.defaultWeight)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        log.exception("vocabulary put settings failed")
        raise HTTPException(status_code=500, detail=str(e)) from e
