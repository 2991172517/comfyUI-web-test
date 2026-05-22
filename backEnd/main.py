import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

import batch_service
import batch_store
import comfy_client
import favorites_service
import job_service
import model_preview_service
import model_folder_service
import workflow_service
import ws_tracker
from config import API_HOST, API_PORT, COMFYUI_URL, WORKFLOW_TEMPLATE_ID, WORKFLOWS_DIR
import prompt_defaults_service
import batch_prompt_service
import batch_task_service
import global_reference_service
import global_prompt_config_service
import prompt_build_service
import model_node_catalog_service
import workflow_node_catalog_service
import auth_service
import campaign_service
import prompt_preset_service
import workflow_chain_service
import workflow_meta_service
from logging_config import setup_logging
from routers.model_sources import router as model_sources_router
from routers.model_manifest import router as model_manifest_router

setup_logging()
log = logging.getLogger("custom_project.api")

app = FastAPI(title="ComfyUI CustomProject API", version="0.1.0")
app.include_router(model_sources_router)
app.include_router(model_manifest_router)


@app.middleware("http")
async def log_requests(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        log.info("%s %s -> %s", request.method, request.url.path, response.status_code)
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 无需登录即可访问的 API（登录页、健康检查、图片预览 URL）
_PUBLIC_API_PREFIXES = (
    "/api/auth/login",
    "/api/auth/admin/login",
    "/api/health",
    "/api/model-previews/",
    "/api/view",
)


def _extract_access_token(request: Request) -> str:
    token = (request.headers.get("X-Access-Token") or "").strip()
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip() or token
    return token


@app.middleware("http")
async def require_auth_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)
    path = request.url.path
    if not path.startswith("/api/"):
        return await call_next(request)
    for prefix in _PUBLIC_API_PREFIXES:
        if path.startswith(prefix) or path == prefix.rstrip("/"):
            return await call_next(request)
    token = _extract_access_token(request)
    if not auth_service.validate_session(token):
        return JSONResponse(
            status_code=401,
            content={"detail": "未登录或会话已失效，请重新登录"},
        )
    if request.method == "DELETE" and not auth_service.is_admin(token):
        return JSONResponse(
            status_code=403,
            content={"detail": "仅管理员可执行删除操作"},
        )
    if (
        request.method == "POST"
        and path.rstrip("/").endswith("/delete-items")
        and not auth_service.is_admin(token)
    ):
        return JSONResponse(
            status_code=403,
            content={"detail": "仅管理员可执行删除操作"},
        )
    if path.startswith("/api/admin/") and not auth_service.is_admin(token):
        return JSONResponse(
            status_code=403,
            content={"detail": "需要管理员权限"},
        )
    return await call_next(request)


class CreateVariantBody(BaseModel):
    variant_id: str
    display_name: str | None = None


class WorkflowMetaBody(BaseModel):
    display_name: str | None = None
    style_enabled: bool | None = None
    style_enabled_default: bool | None = None


class PromptDefaultsBody(BaseModel):
    positive: dict[str, Any] | None = None
    negative: dict[str, Any] | None = None
    merge_mode: str | None = None


class LoraChainItemBody(BaseModel):
    node_id: str
    lora_name: str | None = None
    strength_model: float | None = None
    strength_clip: float | None = None
    title: str | None = None


class EssentialsBody(BaseModel):
    display_name: str | None = None
    style_enabled: bool | None = None
    checkpoint: dict[str, Any] | None = None
    lora_chain: list[LoraChainItemBody] | None = None


class AddLoraSlotBody(BaseModel):
    role: str = "character"
    after_node_id: str | None = None
    lora_name: str = "None"
    title: str | None = None


class DeleteOutputsBody(BaseModel):
    images: list[dict[str, Any]] | None = None


class LoraAxisRule(BaseModel):
    node_id: str | None = None
    alias: str = ""
    enabled: bool = True
    start: float = 0.5
    step: float = 0.1
    direction: str = "up"
    count: int = 4


class LoraAxisConfig(BaseModel):
    """工作流内单个 LoRA 的批量扫参/固定权重配置。"""
    node_id: str
    enabled: bool = False
    alias: str = ""
    sweep_role: str | None = None  # "A" | "B"
    start: float = 0.3
    step: float = 0.1
    direction: str = "up"
    count: int = 4
    fixed_strength_model: float | None = None
    fixed_strength_clip: float | None = None
    lora_name: str | None = None


class FavoriteImageBody(BaseModel):
    filename: str
    subfolder: str = ""
    type: str = "output"


class FavoriteBody(BaseModel):
    workflow_id: str
    image: FavoriteImageBody
    source: str = "single"
    prompt_id: str | None = None
    batch_id: str | None = None
    grid_ia: int | None = None
    grid_ib: int | None = None
    label: str | None = None
    seed: int | None = None
    overrides: dict[str, dict[str, Any]] | None = None
    loras_snapshot: list[dict[str, Any]] | None = None


class PromptSideFixedBody(BaseModel):
    prefix: str = ""
    suffix: str = ""


class OpenModelFolderBody(BaseModel):
    folder: str = Field(description="checkpoints | loras")


class RandomPromptGroupBody(BaseModel):
    id: str = ""
    name: str = ""
    enabled: bool = True
    target: str = "positive"
    pick_mode: str = "random"
    prompts: list[str] = []
    weights: list[float] = Field(default_factory=list)


class PromptMergeOptionsBody(BaseModel):
    global_before_workflow: bool = False
    random_before_workflow: bool = False


class BatchPromptsBody(BaseModel):
    enabled: bool | None = True
    positive: str | None = None
    negative: str | None = None
    fixed: dict[str, Any] | None = None
    random_groups: list[RandomPromptGroupBody] | None = None
    merge: PromptMergeOptionsBody | None = None


class GlobalPromptConfigBody(BaseModel):
    enabled: bool = True
    positive: str = ""
    negative: str = ""
    random_groups: list[RandomPromptGroupBody] | None = None
    merge: PromptMergeOptionsBody | None = None


class BatchPromptConfigBody(BaseModel):
    enabled: bool | None = True
    positive: str | None = None
    negative: str | None = None
    fixed: dict[str, Any] | None = None
    random_groups: list[RandomPromptGroupBody] | None = None
    merge: PromptMergeOptionsBody | None = None


class PromptPresetBody(BaseModel):
    name: str = ""
    description: str = ""
    positive: str | None = None
    negative: str | None = None
    fixed: dict[str, Any] | None = None
    random_groups: list[RandomPromptGroupBody] | None = None
    merge: PromptMergeOptionsBody | None = None


class PromptMergePreviewBody(BaseModel):
    workflow_id: str
    overrides: dict[str, dict[str, Any]] = {}
    style_enabled: bool | None = None
    batch_prompts: BatchPromptsBody | None = None
    prompt_seed: int | None = None
    prompt_global_priority: bool | None = None


class OverridesBody(BaseModel):
    overrides: dict[str, dict[str, Any]] = {}
    style_enabled: bool | None = None
    batch_prompts: BatchPromptsBody | None = None
    prompt_seed: int | None = None


class DeleteBatchItemsBody(BaseModel):
    indices: list[int] = []


class CampaignTaskBody(BaseModel):
    task_id: str | None = None
    label: str | None = None
    workflow_id: str
    batch_payload: dict[str, Any] = {}


class CreateCampaignBody(BaseModel):
    name: str = ""
    tasks: list[CampaignTaskBody] = []


class SaveBatchTaskBody(BaseModel):
    name: str = ""
    description: str = ""
    workflow_id: str
    workflow_display_name: str = ""
    planned_total: int = 0
    batch_payload: dict[str, Any] = {}


class RunBatchTasksBody(BaseModel):
    task_ids: list[str] = []


class BatchGridBody(BaseModel):
    style_enabled: bool | None = None
    batch_prompts: BatchPromptsBody | None = None
    lora_axes: list[LoraAxisConfig] | None = None
    lora_a: LoraAxisRule | None = None
    lora_b: LoraAxisRule | None = None
    count_a: int | None = None
    count_b: int | None = None
    seed_mode: str = "fixed"
    seed: int | None = None
    save_node_id: str | None = None
    seed_node_id: str | None = None
    filename_template: str | None = None
    base_overrides: dict[str, dict[str, Any]] | None = None
    sync_clip: bool = True
    repeat_count: int | None = None
    stop_on_error: bool = True
    prompt_global_priority: bool | None = None


class AuthLoginBody(BaseModel):
    code: str = ""


class AuthAdminLoginBody(BaseModel):
    username: str = ""
    password: str = ""


class InviteCodeBody(BaseModel):
    code: str = ""
    note: str = ""
    expires_at: str | None = None
    max_uses: int = 1
    single_quota_per_login: int = 5
    enabled: bool = True


class InviteCodeUpdateBody(BaseModel):
    code: str | None = None
    note: str | None = None
    expires_at: str | None = None
    max_uses: int | None = None
    single_quota_per_login: int | None = None
    used_count: int | None = None
    enabled: bool | None = None


def _forbid_invite_batch(request: Request) -> None:
    try:
        auth_service.assert_batch_allowed(_extract_access_token(request))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


def _forbid_invite_workflow_config(request: Request) -> None:
    try:
        auth_service.assert_workflow_config_allowed(_extract_access_token(request))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


def _require_single_quota(request: Request) -> None:
    ok, err = auth_service.can_queue_single(_extract_access_token(request))
    if not ok:
        raise HTTPException(status_code=403, detail=err or "单图额度不足")


@app.post("/api/auth/login")
def api_auth_login(body: AuthLoginBody):
    result = auth_service.login_with_code(body.code)
    if not result.get("ok"):
        raise HTTPException(status_code=401, detail=result.get("error") or "邀请码无效")
    return result


@app.post("/api/auth/admin/login")
def api_auth_admin_login(body: AuthAdminLoginBody):
    result = auth_service.login_admin(body.username, body.password)
    if not result.get("ok"):
        raise HTTPException(status_code=401, detail=result.get("error") or "登录失败")
    return result


@app.get("/api/auth/me")
def api_auth_me(request: Request):
    info = auth_service.session_info(_extract_access_token(request))
    if not info.get("ok"):
        raise HTTPException(status_code=401, detail="未登录")
    return info


@app.post("/api/auth/logout")
def api_auth_logout(request: Request):
    auth_service.logout_session(_extract_access_token(request))
    return {"ok": True}


@app.get("/api/admin/invites")
def api_admin_list_invites():
    return {"ok": True, "invites": auth_service.list_invites()}


@app.post("/api/admin/invites")
def api_admin_create_invite(body: InviteCodeBody):
    try:
        row = auth_service.create_invite(body.model_dump())
        return {"ok": True, "invite": row}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.put("/api/admin/invites/{invite_id}")
def api_admin_update_invite(invite_id: str, body: InviteCodeUpdateBody):
    try:
        row = auth_service.update_invite(invite_id, body.model_dump(exclude_none=True))
        return {"ok": True, "invite": row}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.delete("/api/admin/invites/{invite_id}")
def api_admin_delete_invite(invite_id: str):
    try:
        auth_service.delete_invite(invite_id)
        return {"ok": True}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.get("/api/health")
def api_health():
    try:
        stats = comfy_client.health()
        return {
            "ok": True,
            "comfyui_url": COMFYUI_URL,
            "workflows_dir": str(WORKFLOWS_DIR),
            "stats": stats,
        }
    except RuntimeError as e:
        return {
            "ok": False,
            "comfyui_url": COMFYUI_URL,
            "workflows_dir": str(WORKFLOWS_DIR),
            "error": str(e),
        }


@app.get("/api/workflows")
def api_list_workflows():
    return {
        "workflows_dir": str(WORKFLOWS_DIR),
        "template_id": WORKFLOW_TEMPLATE_ID,
        "workflows": workflow_service.list_workflows(),
        "variants": workflow_meta_service.list_variants(),
    }


@app.get("/api/workflow-template")
def api_workflow_template():
    meta = workflow_meta_service.load_meta(WORKFLOW_TEMPLATE_ID)
    if not meta:
        meta = workflow_meta_service._infer_meta_from_template(WORKFLOW_TEMPLATE_ID)
    return {"ok": True, "template_id": WORKFLOW_TEMPLATE_ID, "meta": meta}


@app.get("/api/workflow-variants")
def api_list_workflow_variants():
    return {"ok": True, "variants": workflow_meta_service.list_variants()}


@app.post("/api/workflow-variants")
def api_create_workflow_variant(body: CreateVariantBody, request: Request):
    _forbid_invite_workflow_config(request)
    try:
        entry = workflow_meta_service.create_variant(
            body.variant_id,
            body.display_name,
        )
        return {"ok": True, **entry}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/prompt-defaults")
def api_get_prompt_defaults():
    cfg = prompt_defaults_service.load_defaults()
    return {"ok": True, "defaults": cfg}


@app.get("/api/global-prompt-config")
def api_get_global_prompt_config():
    cfg = global_prompt_config_service.load_global_prompt_config()
    return {"ok": True, "config": cfg}


@app.put("/api/global-prompt-config")
def api_put_global_prompt_config(body: GlobalPromptConfigBody):
    payload = {
        "enabled": body.enabled,
        "positive": body.positive,
        "negative": body.negative,
        "merge": body.merge.model_dump() if body.merge else {},
        "random_groups": [g.model_dump() for g in body.random_groups]
        if body.random_groups is not None
        else [],
    }
    saved = global_prompt_config_service.save_global_prompt_config(payload)
    return {"ok": True, "config": saved}


@app.post("/api/prompts/merge-preview")
def api_prompt_merge_preview(body: PromptMergePreviewBody):
    try:
        runtime = _effective_batch_prompts(body.batch_prompts)
        texts, picks, debug, segments = prompt_build_service.build_merged_encode_texts(
            body.workflow_id,
            body.overrides,
            runtime_raw=runtime,
            style_enabled=body.style_enabled,
            seed=body.prompt_seed,
            index=0,
            random_first_override=body.prompt_global_priority,
            log_source="merge_preview",
            include_segments=True,
        )
        return {
            "ok": True,
            "positive": texts.get("positive", ""),
            "negative": texts.get("negative", ""),
            "prompt_picks": picks,
            "merge_debug": debug,
            "segments": segments,
        }
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/prompt-presets")
def api_list_prompt_presets():
    return {"ok": True, "presets": prompt_preset_service.list_presets()}


@app.get("/api/prompt-presets/{preset_id}")
def api_get_prompt_preset(preset_id: str):
    entry = prompt_preset_service.get_preset(preset_id)
    if not entry:
        raise HTTPException(status_code=404, detail="预设不存在")
    return {"ok": True, "preset": entry}


@app.post("/api/prompt-presets")
def api_create_prompt_preset(body: PromptPresetBody):
    try:
        payload = _preset_payload_from_body(body)
        preset = prompt_preset_service.create_preset(body.name, payload)
        return {"ok": True, "preset": preset}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.put("/api/prompt-presets/{preset_id}")
def api_update_prompt_preset(preset_id: str, body: PromptPresetBody):
    try:
        payload = _preset_payload_from_body(body, for_update=True)
        preset = prompt_preset_service.update_preset(preset_id, payload)
        return {"ok": True, "preset": preset}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.delete("/api/prompt-presets/{preset_id}")
def api_delete_prompt_preset(preset_id: str):
    try:
        prompt_preset_service.delete_preset(preset_id)
        return {"ok": True, "id": preset_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.get("/api/batch-prompt-config")
def api_get_batch_prompt_config():
    return {"ok": True, "config": batch_prompt_service.load_batch_prompt_config()}


@app.get("/api/global-reference-groups")
def api_get_global_reference_groups():
    store = global_reference_service.load_global_reference_groups()
    groups = global_reference_service.normalize_groups(store.get("groups"))
    return {"ok": True, "groups": groups}


@app.put("/api/global-reference-groups")
def api_put_global_reference_groups(body: BatchPromptConfigBody):
    groups = None
    if body.random_groups is not None:
        groups = [g.model_dump() for g in body.random_groups]
    saved = global_reference_service.save_global_reference_groups({
        "schema_version": 1,
        "groups": global_reference_service.normalize_groups(groups),
    })
    return {"ok": True, "groups": saved.get("groups", [])}


@app.put("/api/batch-prompt-config")
def api_put_batch_prompt_config(body: BatchPromptConfigBody):
    cfg = batch_prompt_service.load_batch_prompt_config()
    if body.fixed:
        cfg.setdefault("fixed", {})
        for k, v in body.fixed.items():
            cfg["fixed"][k] = v.model_dump() if hasattr(v, "model_dump") else v
    if body.random_groups is not None:
        cfg["random_groups"] = [g.model_dump() for g in body.random_groups]
    saved = batch_prompt_service.save_batch_prompt_config(
        batch_prompt_service.normalize_batch_prompts(cfg)
    )
    return {"ok": True, "config": saved}


@app.put("/api/prompt-defaults")
def api_put_prompt_defaults(body: PromptDefaultsBody):
    cfg = prompt_defaults_service.load_defaults()
    if body.positive is not None:
        cfg["positive"] = {**cfg.get("positive", {}), **body.positive}
    if body.negative is not None:
        cfg["negative"] = {**cfg.get("negative", {}), **body.negative}
    if body.merge_mode is not None:
        cfg["merge_mode"] = body.merge_mode
    prompt_defaults_service.save_defaults(cfg)
    return {"ok": True, "defaults": cfg}


@app.get("/api/workflows/{workflow_id:path}")
def api_get_workflow(workflow_id: str, style_enabled: bool | None = Query(None)):
    try:
        return workflow_service.get_workflow_detail(
            workflow_id, style_enabled=style_enabled
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/workflows/{workflow_id:path}/essentials")
def api_get_workflow_essentials(workflow_id: str):
    try:
        return {"ok": True, **workflow_chain_service.get_workflow_essentials(workflow_id)}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/node-catalog")
def api_list_node_catalog():
    """本地 Checkpoint / LoRA 列表 + 已保存的默认参数（节点管理页）。"""
    try:
        return {"ok": True, **model_node_catalog_service.list_model_catalog()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


class NodeCatalogSaveBody(BaseModel):
    default_checkpoint: str | None = None
    loras: list[dict[str, Any]] | None = None


class CheckpointLoraCompatBody(BaseModel):
    checkpoint: str = Field(description="Checkpoint 文件名")
    recommended: list[str] = Field(default_factory=list)
    not_recommended: list[str] = Field(default_factory=list)


@app.put("/api/node-catalog")
def api_put_node_catalog(body: NodeCatalogSaveBody):
    try:
        saved = model_node_catalog_service.save_model_catalog(body.model_dump(exclude_none=True))
        return {"ok": True, **saved}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/node-catalog/lora-compat")
def api_get_checkpoint_lora_compat(
    checkpoint: str = Query(..., description="当前 Checkpoint 文件名"),
):
    try:
        data = model_node_catalog_service.get_checkpoint_lora_compat(checkpoint)
        return {"ok": True, **data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.put("/api/node-catalog/lora-compat")
def api_put_checkpoint_lora_compat(body: CheckpointLoraCompatBody):
    try:
        data = model_node_catalog_service.save_checkpoint_lora_compat(
            body.checkpoint,
            recommended=body.recommended,
            not_recommended=body.not_recommended,
        )
        return {"ok": True, **data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/node-catalog/lora-defaults")
def api_lora_defaults_by_name(name: str = Query(..., description="LoRA 文件名")):
    patch = model_node_catalog_service.lora_defaults_by_name(name)
    return {"ok": True, "name": name, "defaults": patch}


@app.get("/api/workflows/{workflow_id:path}/node-catalog")
def api_get_workflow_node_catalog(workflow_id: str):
    try:
        return {"ok": True, **workflow_node_catalog_service.get_workflow_catalog(workflow_id)}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


class NodeCatalogBody(BaseModel):
    checkpoint: dict[str, Any] | None = None
    lora_slots: list[dict[str, Any]] | None = None


@app.put("/api/workflows/{workflow_id:path}/node-catalog")
def api_put_workflow_node_catalog(workflow_id: str, body: NodeCatalogBody, request: Request):
    _forbid_invite_workflow_config(request)
    try:
        saved = workflow_node_catalog_service.save_workflow_catalog(
            workflow_id,
            body.model_dump(exclude_none=True),
        )
        return {"ok": True, **saved}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.put("/api/workflows/{workflow_id:path}/essentials")
def api_put_workflow_essentials(workflow_id: str, body: EssentialsBody, request: Request):
    _forbid_invite_workflow_config(request)
    try:
        payload = body.model_dump(exclude_none=True)
        if body.lora_chain is not None:
            payload["lora_chain"] = [x.model_dump(exclude_none=True) for x in body.lora_chain]
        data = workflow_chain_service.apply_workflow_essentials(workflow_id, payload)
        return {"ok": True, **data}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/workflows/{workflow_id:path}/lora-slots")
def api_add_lora_slot(workflow_id: str, body: AddLoraSlotBody, request: Request):
    _forbid_invite_workflow_config(request)
    try:
        data = workflow_chain_service.add_lora_slot(
            workflow_id,
            role=body.role,
            after_node_id=body.after_node_id,
            lora_name=body.lora_name,
            title=body.title,
        )
        return {"ok": True, **data}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.delete("/api/workflows/{workflow_id:path}/lora-slots/{node_id}")
def api_remove_lora_slot(workflow_id: str, node_id: str):
    try:
        data = workflow_chain_service.remove_lora_slot(workflow_id, node_id)
        return {"ok": True, **data}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.put("/api/workflows/{workflow_id:path}/meta")
def api_update_workflow_meta(workflow_id: str, body: WorkflowMetaBody, request: Request):
    _forbid_invite_workflow_config(request)
    try:
        meta = workflow_meta_service.load_meta(workflow_id) or workflow_meta_service.get_effective_meta(
            workflow_id
        )
        if body.display_name is not None:
            meta["display_name"] = body.display_name
        if body.style_enabled is not None:
            meta["style_enabled"] = body.style_enabled
        if body.style_enabled_default is not None:
            meta["style_enabled_default"] = body.style_enabled_default
        workflow_meta_service.save_meta(workflow_id, meta)
        return {"ok": True, "id": workflow_id, "meta": meta}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.put("/api/workflows/{workflow_id:path}")
def api_save_workflow(workflow_id: str, body: OverridesBody, request: Request):
    _forbid_invite_workflow_config(request)
    try:
        workflow_service.save_with_overrides(workflow_id, body.overrides)
        return {"ok": True, "id": workflow_id}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/workflows/{workflow_id:path}/queue")
def api_queue_workflow(workflow_id: str, body: OverridesBody, request: Request):
    _require_single_quota(request)
    token = _extract_access_token(request)
    try:
        import history_service

        runtime = _effective_batch_prompts(body.batch_prompts)
        prompt_picks: list[dict] = []
        import prompt_defaults_service as pds
        import prompt_queue_log

        should_apply = prompt_build_service.should_apply_prompt_layers(runtime)
        if should_apply:
            merged, prompt_picks = prompt_build_service.build_text_overrides_for_queue(
                workflow_id,
                body.overrides,
                runtime,
                style_enabled=body.style_enabled,
                seed=body.prompt_seed,
                index=0,
                log_source="single_queue",
            )
            prompt = workflow_service.build_api_prompt(
                workflow_id,
                merged,
                style_enabled=body.style_enabled,
                apply_defaults=False,
            )
        else:
            merged = dict(body.overrides)
            prompt_picks = []
            prompt = workflow_service.build_api_prompt(
                workflow_id,
                merged,
                style_enabled=body.style_enabled,
                apply_defaults=True,
            )
            prompt_queue_log.append_event(
                "SINGLE_QUEUE_SKIP_MERGE",
                workflow_id=workflow_id,
                source="single_queue",
                extra={"should_apply": False, "batch_prompts": bool(runtime)},
            )
        encode = pds.load_defaults()
        encode_map = {
            "positive": str((encode.get("positive") or {}).get("node_id", "3")),
            "negative": str((encode.get("negative") or {}).get("node_id", "4")),
        }
        ov_clip = {}
        for side, nid in encode_map.items():
            ov_clip[nid] = str((merged.get(nid) or {}).get("text", ""))
        client_id = str(uuid.uuid4())
        prompt_id = str(uuid.uuid4())
        prompt_queue_log.log_comfyui_queue(
            workflow_id=workflow_id,
            source="single_queue",
            prompt_id=prompt_id,
            apply_defaults=not should_apply,
            layers_applied=should_apply,
            pick_records=prompt_picks,
            overrides_clip=ov_clip,
            final_prompt=prompt,
            encode_node_ids=encode_map,
        )
        result = comfy_client.queue_prompt(prompt, client_id=client_id, prompt_id=prompt_id)
        pid = result.get("prompt_id", prompt_id)
        ws_tracker.start_tracking(client_id, pid)
        history_service.persist_single_queued(
            prompt_id=pid,
            workflow_id=workflow_id,
            overrides=merged,
            style_enabled=body.style_enabled,
            batch_prompts=runtime,
            prompt_picks=prompt_picks,
        )
        out = {
            "ok": True,
            "prompt_id": pid,
            "client_id": client_id,
            "number": result.get("number"),
        }
        quota = auth_service.consume_single_quota(token)
        if quota:
            out.update(quota)
        return out
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


def _preset_payload_from_body(body: PromptPresetBody, *, for_update: bool = False) -> dict:
    payload: dict[str, Any] = {
        "description": body.description,
        "fixed": body.fixed,
    }
    if body.positive is not None:
        payload["positive"] = body.positive
    if body.negative is not None:
        payload["negative"] = body.negative
    if body.merge is not None:
        payload["merge"] = body.merge.model_dump()
    if body.random_groups is not None:
        payload["random_groups"] = [g.model_dump() for g in body.random_groups]
    elif not for_update:
        payload["random_groups"] = []
    return payload


def _batch_prompts_dict(body: BatchPromptsBody | BatchPromptConfigBody | None) -> dict | None:
    if not body:
        return None
    raw: dict[str, Any] = {}
    if body.enabled is not None:
        raw["enabled"] = body.enabled
    if body.positive is not None:
        raw["positive"] = body.positive
    if body.negative is not None:
        raw["negative"] = body.negative
    if body.merge is not None:
        raw["merge"] = body.merge.model_dump()
    if body.fixed:
        raw["fixed"] = {}
        for k, v in body.fixed.items():
            raw["fixed"][k] = v.model_dump() if hasattr(v, "model_dump") else v
    if body.random_groups is not None:
        raw["random_groups"] = [g.model_dump() for g in body.random_groups]
    return prompt_build_service.normalize_prompt_layers(raw)


def _effective_batch_prompts(body: BatchPromptsBody | BatchPromptConfigBody | None) -> dict | None:
    """当次提示词层（不含全局；全局由 prompt_build 自动并入）。"""
    raw = _batch_prompts_dict(body)
    if not raw:
        return None
    if prompt_build_service.layers_have_content(raw):
        return raw
    return None


def _batch_payload(body: BatchGridBody) -> dict:
    payload = {
        "style_enabled": body.style_enabled,
        "batch_prompts": _effective_batch_prompts(body.batch_prompts),
        "seed_mode": body.seed_mode,
        "seed": body.seed,
        "save_node_id": body.save_node_id,
        "seed_node_id": body.seed_node_id,
        "filename_template": body.filename_template,
        "base_overrides": body.base_overrides or {},
        "sync_clip": body.sync_clip,
        "repeat_count": body.repeat_count,
        "stop_on_error": body.stop_on_error,
        "prompt_global_priority": body.prompt_global_priority,
    }
    if body.lora_axes:
        payload["lora_axes"] = [a.model_dump() for a in body.lora_axes]
    else:
        la = body.lora_a or LoraAxisRule()
        lb = body.lora_b or LoraAxisRule()
        payload["lora_a"] = la.model_dump()
        payload["lora_b"] = lb.model_dump()
        if body.count_a is not None:
            payload["lora_a"]["count"] = body.count_a
        if body.count_b is not None:
            payload["lora_b"]["count"] = body.count_b
    return payload


@app.post("/api/workflows/{workflow_id:path}/batch/preview")
def api_batch_preview(workflow_id: str, body: BatchGridBody, request: Request):
    _forbid_invite_batch(request)
    try:
        plan = batch_service.build_grid_plan(workflow_id, _batch_payload(body))
        return {"ok": True, "plan": plan}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/workflows/{workflow_id:path}/batch")
def api_start_batch(workflow_id: str, body: BatchGridBody, request: Request):
    _forbid_invite_batch(request)
    try:
        payload = _batch_payload(body)
        plan = batch_service.build_grid_plan(workflow_id, payload)
        batch_id = plan["batch_id"]
        # 必须把同一 batch_id 传给后台线程，否则 run_batch 会再生成新 id，前端轮询 404
        payload["batch_id"] = batch_id
        batch_store.create(batch_id, {
            "batch_id": batch_id,
            "workflow_id": workflow_id,
            "status": "running",
            "plan": plan,
            "completed": 0,
            "total": plan["grid"]["total"],
            "items": [],
            "error": None,
            "cancel_requested": False,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "message": "批量已排队…",
        })
        batch_service.persist_batch_start(plan, payload)
        log.info(
            "POST batch workflow=%s batch_id=%s total=%d",
            workflow_id,
            batch_id,
            plan["grid"]["total"],
        )
        thread = threading.Thread(
            target=batch_service.run_batch,
            args=(workflow_id, payload),
            daemon=True,
            name=f"batch-{batch_id}",
        )
        thread.start()
        return {
            "ok": True,
            "batch_id": batch_id,
            "total": plan["grid"]["total"],
            "grid": plan["grid"],
            "output_dir": plan["output_dir"],
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/history")
def api_list_history(
    limit: int = Query(80, ge=1, le=200),
    checkpoint: str | None = Query(None),
    lora_name: str | None = Query(None),
    lora_weight: float | None = Query(None),
    lora_node: str | None = Query(None),
    type: str | None = Query(None, alias="type"),
):
    import history_service

    return {
        "ok": True,
        "records": history_service.list_history(
            limit,
            checkpoint=checkpoint,
            lora_name=lora_name,
            lora_weight=lora_weight,
            lora_node=lora_node,
            record_type=type,
        ),
    }


@app.get("/api/history/filter-options")
def api_history_filter_options(limit: int = Query(200, ge=1, le=500)):
    import history_service

    return {"ok": True, **history_service.get_filter_options(limit=limit)}


@app.get("/api/history/single/{prompt_id}")
def api_get_history_single(prompt_id: str):
    import history_service

    entry = history_service.get_single_detail(prompt_id)
    if not entry:
        raise HTTPException(status_code=404, detail="单抽记录不存在")
    return entry


@app.get("/api/history/batch/{batch_id}")
def api_get_history_batch(batch_id: str):
    import history_service

    entry = history_service.get_batch_detail(batch_id)
    if not entry:
        raise HTTPException(status_code=404, detail="批量记录不存在")
    return entry


@app.delete("/api/history/single/{prompt_id}")
def api_delete_history_single(prompt_id: str):
    import history_service

    if not history_service.get_single_detail(prompt_id):
        raise HTTPException(status_code=404, detail="单抽记录不存在")
    try:
        return history_service.delete_single_record(prompt_id)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.delete("/api/history/batch/{batch_id}")
def api_delete_history_batch(batch_id: str):
    import history_service

    if not batch_service.get_batch(batch_id) and not batch_service._read_manifest(batch_id):
        raise HTTPException(status_code=404, detail="批量记录不存在")
    try:
        return history_service.delete_batch_record(batch_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.post("/api/history/batch/{batch_id}/delete-items")
def api_delete_history_batch_items(batch_id: str, body: DeleteBatchItemsBody):
    import history_service

    if not batch_service.get_batch(batch_id) and not batch_service._read_manifest(batch_id):
        raise HTTPException(status_code=404, detail="批量记录不存在")
    try:
        return history_service.delete_batch_items(batch_id, body.indices)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/batches")
def api_list_batches(
    limit: int = Query(50, ge=1, le=200),
    task_id: str | None = Query(None),
):
    return {"ok": True, "batches": batch_service.list_batches(limit=limit, task_id=task_id)}


@app.get("/api/batches/{batch_id}")
def api_get_batch(batch_id: str):
    entry = batch_service.get_batch(batch_id)
    if not entry:
        raise HTTPException(status_code=404, detail="批量任务不存在")
    return entry


@app.post("/api/batches/{batch_id}/cancel")
def api_cancel_batch(batch_id: str):
    entry = batch_service.get_batch(batch_id)
    if not entry:
        raise HTTPException(status_code=404, detail="批量任务不存在")
    return batch_service.cancel_batch(batch_id)


@app.delete("/api/batches/{batch_id}")
def api_delete_batch(batch_id: str):
    entry = batch_service.get_batch(batch_id)
    if not entry:
        raise HTTPException(status_code=404, detail="批量任务不存在")
    return batch_service.delete_batch(batch_id)


@app.post("/api/jobs/{prompt_id}/cancel")
def api_cancel_job(prompt_id: str):
    try:
        return job_service.cancel_job(prompt_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/jobs/{prompt_id}")
def api_get_job(prompt_id: str):
    try:
        return job_service.get_job_detail(prompt_id)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.delete("/api/jobs/{prompt_id}/outputs")
def api_delete_job_outputs(prompt_id: str, body: DeleteOutputsBody | None = None):
    try:
        images = body.images if body else None
        return job_service.delete_job_outputs(prompt_id, images)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.get("/api/view")
def api_view_image(
    filename: str = Query(...),
    subfolder: str = Query(""),
    type: str = Query("output"),
):
    try:
        data, content_type = comfy_client.fetch_view_image(filename, subfolder, type)
        return Response(content=data, media_type=content_type)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


def _favorite_payload(body: FavoriteBody) -> dict:
    return {
        "workflow_id": body.workflow_id,
        "image": body.image.model_dump(),
        "source": body.source,
        "prompt_id": body.prompt_id,
        "batch_id": body.batch_id,
        "grid_ia": body.grid_ia,
        "grid_ib": body.grid_ib,
        "label": body.label,
        "seed": body.seed,
        "overrides": body.overrides or {},
        "loras_snapshot": body.loras_snapshot,
    }


@app.get("/api/favorites")
def api_list_favorites():
    return {"ok": True, "favorites": favorites_service.list_favorites()}


@app.post("/api/favorites")
def api_add_favorite(body: FavoriteBody):
    try:
        entry = favorites_service.add_favorite(_favorite_payload(body))
        return {"ok": True, "favorited": True, "entry": entry}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.post("/api/favorites/toggle")
def api_toggle_favorite(body: FavoriteBody):
    try:
        return favorites_service.toggle_favorite(_favorite_payload(body))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.get("/api/favorites/{favorite_id}")
def api_get_favorite(favorite_id: str):
    entry = favorites_service.get_favorite(favorite_id)
    if not entry:
        raise HTTPException(status_code=404, detail="收藏不存在")
    return entry


@app.delete("/api/favorites/{favorite_id}")
def api_remove_favorite(favorite_id: str):
    try:
        return favorites_service.remove_favorite(favorite_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.get("/api/models/folder-paths")
def api_model_folder_paths():
    paths = model_folder_service.list_folder_paths()
    return {"ok": True, "paths": paths}


@app.post("/api/models/open-folder")
def api_open_model_folder(body: OpenModelFolderBody):
    folder = str(body.folder or "").strip().lower()
    if folder not in ("checkpoints", "loras"):
        raise HTTPException(status_code=400, detail="folder 须为 checkpoints 或 loras")
    try:
        result = model_folder_service.open_in_file_manager(folder)
        return {"ok": result["ok"], **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/models/{folder}")
def api_models(folder: str, with_previews: bool = Query(False)):
    try:
        files = comfy_client.list_models(folder)
        if with_previews:
            enriched = model_preview_service.enrich_model_files(folder, files)
            return {"folder": folder, "files": files, "models": enriched}
        return {"folder": folder, "files": files}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


class ModelDescriptionBody(BaseModel):
    name: str = ""
    content: str = ""
    source_url: str = ""


@app.put("/api/models/{folder}/description")
def api_save_model_description(folder: str, body: ModelDescriptionBody):
    folder = str(folder or "").strip().lower()
    name = str(body.name or "").strip()
    if folder not in ("checkpoints", "loras"):
        raise HTTPException(status_code=400, detail="folder 须为 checkpoints 或 loras")
    if not name:
        raise HTTPException(status_code=400, detail="缺少模型文件名 name")
    try:
        return model_preview_service.write_summary_txt_for_model(
            folder,
            name,
            body.content,
            source_url=body.source_url,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.delete("/api/models/{folder}/item")
def api_delete_model_item(
    folder: str,
    name: str = Query(..., description="模型文件名"),
    delete_assets: bool = Query(True, description="是否删除同名资源目录"),
):
    folder = str(folder or "").strip().lower()
    if folder not in ("checkpoints", "loras"):
        raise HTTPException(status_code=400, detail="folder 须为 checkpoints 或 loras")
    if not name.strip():
        raise HTTPException(status_code=400, detail="缺少 name")
    try:
        result = model_preview_service.delete_model_from_disk(
            folder,
            name.strip(),
            delete_asset_dirs=delete_assets,
        )
        model_node_catalog_service.remove_model_defaults(name.strip(), folder=folder)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {e}") from e


@app.get("/api/models/{folder}/previews")
def api_model_previews(folder: str, name: str = Query(..., description="模型文件名，与 ComfyUI 列表一致")):
    try:
        assets = model_preview_service.get_model_assets(folder, name)
        return {
            "folder": folder,
            "model": name,
            "previews": assets["previews"],
            "has_preview": assets["has_preview"],
            "summary": assets["summary"],
            "has_summary": assets["has_summary"],
            "preview_root": model_preview_service.models_root_for_folder(folder),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/model-previews/{folder}/{file_path:path}")
def api_model_preview_file(folder: str, file_path: str):
    try:
        path = model_preview_service.resolve_preview_file(folder, file_path)
        if not path:
            raise HTTPException(status_code=404, detail="预览图不存在")
        data = path.read_bytes()
        ext = path.suffix.lower()
        media = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }.get(ext, "application/octet-stream")
        return Response(content=data, media_type=media)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/batch-tasks")
def api_list_batch_tasks():
    return {"ok": True, "tasks": batch_task_service.list_tasks()}


@app.get("/api/batch-tasks/{task_id}")
def api_get_batch_task(task_id: str):
    task = batch_task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"ok": True, "task": task}


@app.get("/api/batch-tasks/{task_id}/batches")
def api_get_batch_task_batches(task_id: str, limit: int = Query(50, ge=1, le=200)):
    task = batch_task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    batches = batch_service.list_batches(limit=limit, task_id=task_id)
    return {"ok": True, "task_id": task_id, "batches": batches}


@app.post("/api/batch-tasks")
def api_save_batch_task(body: SaveBatchTaskBody, request: Request):
    _forbid_invite_batch(request)
    try:
        entry = batch_task_service.save_task(
            body.name,
            body.workflow_id,
            body.batch_payload,
            workflow_display_name=body.workflow_display_name,
            description=body.description,
            planned_total=body.planned_total,
        )
        return {"ok": True, "task": entry}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.delete("/api/batch-tasks/{task_id}")
def api_delete_batch_task(task_id: str):
    try:
        batch_task_service.delete_task(task_id)
        return {"ok": True, "task_id": task_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.post("/api/batch-tasks/run")
def api_run_batch_tasks(body: RunBatchTasksBody, request: Request):
    _forbid_invite_batch(request)
    try:
        return batch_task_service.run_tasks_async(body.task_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/campaigns")
def api_list_campaigns(limit: int = Query(50, ge=1, le=200)):
    return {"ok": True, "campaigns": campaign_service.list_campaigns(limit=limit)}


@app.get("/api/campaigns/{campaign_id}")
def api_get_campaign(campaign_id: str):
    entry = campaign_service.get_campaign(campaign_id)
    if not entry:
        raise HTTPException(status_code=404, detail="任务计划不存在")
    return {"ok": True, "campaign": entry}


@app.post("/api/campaigns")
def api_create_campaign(body: CreateCampaignBody, request: Request):
    _forbid_invite_batch(request)
    tasks = [
        {
            "task_id": t.task_id,
            "label": t.label,
            "workflow_id": t.workflow_id,
            "batch_payload": t.batch_payload,
        }
        for t in body.tasks
    ]
    entry = campaign_service.create_campaign(body.name, tasks)
    return {"ok": True, "campaign": entry}


@app.post("/api/campaigns/{campaign_id}/run")
def api_run_campaign(campaign_id: str, request: Request):
    _forbid_invite_batch(request)
    entry = campaign_service.get_campaign(campaign_id)
    if not entry:
        raise HTTPException(status_code=404, detail="任务计划不存在")
    if entry.get("status") == "running":
        raise HTTPException(status_code=400, detail="任务计划已在运行")
    campaign_service.start_campaign_async(campaign_id)
    return {"ok": True, "campaign_id": campaign_id, "message": "任务计划已开始"}


@app.post("/api/campaigns/{campaign_id}/cancel")
def api_cancel_campaign(campaign_id: str):
    entry = campaign_service.get_campaign(campaign_id)
    if not entry:
        raise HTTPException(status_code=404, detail="任务计划不存在")
    return campaign_service.cancel_campaign(campaign_id)


if __name__ == "__main__":
    import uvicorn

    # 热重载会清空内存中的 batch_store，开发时易误判「任务不存在」
    use_reload = os.getenv("API_RELOAD", "").strip().lower() in ("1", "true", "yes")
    if use_reload:
        log.warning("API_RELOAD=1：修改代码会重启进程，进行中的批量状态会丢失")
    uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=use_reload)
