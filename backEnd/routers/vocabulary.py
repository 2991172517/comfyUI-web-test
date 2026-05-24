"""提示词词库补全 API。"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
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
