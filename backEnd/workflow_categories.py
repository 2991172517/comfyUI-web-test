"""工作流一级分类（替代母版 / 子工作流树形结构）。"""
from __future__ import annotations

from config import WORKFLOW_HIDDEN_IDS, WORKFLOW_TEMPLATE_ID, WORKFLOW_VARIANTS_DIR

VARIANT_PREFIX = "variants/"

WORKFLOW_CATEGORIES = [
    {"id": "generate", "label": "文生图"},
    {"id": "inpaint", "label": "局部重绘"},
    {"id": "upscale", "label": "高清放大"},
    {"id": "other", "label": "其他"},
]

DEFAULT_WORKFLOW_CATEGORY = "generate"
_CATEGORY_IDS = {c["id"] for c in WORKFLOW_CATEGORIES}


def normalize_category(value: str | None) -> str:
    raw = (value or "").strip().lower()
    if raw in _CATEGORY_IDS:
        return raw
    return DEFAULT_WORKFLOW_CATEGORY


def infer_category_from_workflow_id(workflow_id: str) -> str:
    low = (workflow_id or "").lower()
    if "inpaint" in low or "重绘" in workflow_id:
        return "inpaint"
    if "upscale" in low or "放大" in workflow_id or "高清" in workflow_id:
        return "upscale"
    return DEFAULT_WORKFLOW_CATEGORY


def infer_category_from_prompt(prompt: dict) -> str:
    """从 API prompt 节点类型推断分类（PNG 恢复导入用）。"""
    types: set[str] = set()
    for node in (prompt or {}).values():
        if isinstance(node, dict) and node.get("class_type"):
            types.add(str(node["class_type"]))
    if "InpaintModelConditioning" in types or "LoadImageMask" in types:
        return "inpaint"
    if "RTXVideoSuperResolution" in types and "KSampler" not in types:
        return "upscale"
    return DEFAULT_WORKFLOW_CATEGORY


def category_for_meta(workflow_id: str, meta: dict | None) -> str:
    if meta and meta.get("category"):
        return normalize_category(meta["category"])
    return infer_category_from_workflow_id(workflow_id)


def is_hidden_workflow(workflow_id: str) -> bool:
    if not workflow_id:
        return True
    if workflow_id in WORKFLOW_HIDDEN_IDS:
        return True
    if workflow_id == WORKFLOW_TEMPLATE_ID:
        return True
    return False


def is_user_workflow(workflow_id: str) -> bool:
    return workflow_id.startswith(VARIANT_PREFIX) and not is_hidden_workflow(workflow_id)


def categories_payload() -> list[dict]:
    return [dict(c) for c in WORKFLOW_CATEGORIES]
