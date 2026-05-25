"""从 ComfyUI 输出 PNG 元数据构建「以此生成」恢复快照。"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from typing import Any

import job_service
import workflow_import_service as wis
import workflow_service as ws
from workflow_categories import infer_category_from_prompt
from workflow_import_service import (
    VARIANT_PREFIX,
    _read_png_text_chunks,
    _to_api_prompt,
    import_as_variant,
)
from workflow_meta_service import _variant_json_path

log = logging.getLogger(__name__)


def _extract_clip_texts(prompt: dict) -> tuple[str, str]:
    encodes: list[tuple[int, str, str]] = []
    for nid, node in prompt.items():
        if not isinstance(node, dict):
            continue
        if node.get("class_type") != "CLIPTextEncode":
            continue
        text = node.get("inputs", {}).get("text")
        if isinstance(text, str):
            encodes.append((_sort_nid(nid), str(nid), text))
    encodes.sort(key=lambda x: x[0])
    if not encodes:
        return "", ""
    pos = encodes[0][2]
    neg = encodes[1][2] if len(encodes) > 1 else ""
    return pos, neg


def _sort_nid(nid: str) -> int:
    try:
        return int(nid)
    except ValueError:
        return 0


def _extract_seed(prompt: dict) -> int | None:
    for node in prompt.values():
        if not isinstance(node, dict):
            continue
        if node.get("class_type") not in ("KSampler", "KSamplerAdvanced"):
            continue
        seed = node.get("inputs", {}).get("seed")
        if isinstance(seed, int):
            return seed
        if isinstance(seed, str) and seed.isdigit():
            return int(seed)
    return None


def overrides_from_embedded(base: dict, embedded: dict) -> dict[str, dict[str, Any]]:
    """对比磁盘工作流与 PNG 内嵌 prompt，生成 overrides。"""
    out: dict[str, dict[str, Any]] = {}
    for nid, enode in embedded.items():
        if not isinstance(enode, dict):
            continue
        bnode = base.get(nid)
        if not isinstance(bnode, dict):
            continue
        if bnode.get("class_type") != enode.get("class_type"):
            continue
        patch: dict[str, Any] = {}
        for key, val in (enode.get("inputs") or {}).items():
            if isinstance(val, list):
                continue
            if bnode.get("inputs", {}).get(key) != val:
                patch[key] = val
        if patch:
            out[str(nid)] = patch
    return out


def _batch_prompts_from_texts(positive: str, negative: str) -> dict[str, Any]:
    return {
        "enabled": True,
        "positive": positive or "",
        "negative": negative or "",
        "fixed": {"positive": {"prefix": "", "suffix": ""}, "negative": {"prefix": "", "suffix": ""}},
        "merge": {"global_before_workflow": False, "random_before_workflow": False},
        "random_groups": [],
        "random_bundle_groups": [],
    }


def _prompt_fingerprint(prompt: dict) -> str:
    raw = json.dumps(prompt, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _ensure_variant_from_png(raw: bytes, *, filename: str, display_stem: str) -> str:
    """将 PNG 内嵌工作流落盘为 variants/png_<hash>，已存在则复用。"""
    chunks = _read_png_text_chunks(raw)
    prompt_raw = chunks.get("prompt")
    if not prompt_raw:
        raise ValueError("PNG 中未找到 ComfyUI 工作流元数据（prompt 字段）")
    data = json.loads(prompt_raw)
    if not isinstance(data, dict):
        raise ValueError("PNG 内 prompt 格式无效")
    fmt = "api" if ws._is_api_prompt(data) else "ui"
    prompt = _to_api_prompt(data, fmt)
    fp = _prompt_fingerprint(prompt)
    vid = f"png_{fp}"
    workflow_id = f"{VARIANT_PREFIX}{vid}"
    if _variant_json_path(vid).is_file():
        return workflow_id
    stem = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", display_stem or "from_png")[:40] or "from_png"
    cat = infer_category_from_prompt(prompt)
    entry = import_as_variant(
        raw,
        variant_id=vid,
        display_name=f"PNG恢复·{stem}",
        category=cat,
        filename=filename or "restore.png",
    )
    return entry["id"]


def _try_resolve_local_workflow(
    embedded: dict,
    hint: str | None,
) -> tuple[str | None, dict[str, dict[str, Any]], str]:
    """返回 (workflow_id, overrides, reason)。"""
    hint = (hint or "").strip()
    candidates: list[str] = []
    if hint:
        candidates.append(hint)
    for entry in ws.list_workflows():
        wid = entry.get("id") or ""
        if wid and wid not in candidates:
            candidates.append(wid)

    best_id: str | None = None
    best_ov: dict[str, dict[str, Any]] = {}
    best_score = -1

    for wid in candidates[:40]:
        try:
            fmt, base = ws.load_workflow_file(wid)
        except (FileNotFoundError, ValueError):
            continue
        if fmt != "api" or not isinstance(base, dict):
            continue
        ov = overrides_from_embedded(base, embedded)
        score = len(ov)
        if wid == hint:
            score += 3
        if score > best_score:
            best_score = score
            best_id = wid
            best_ov = ov

    if best_id and best_score > 0:
        return best_id, best_ov, "matched_local"
    if hint:
        try:
            fmt, base = ws.load_workflow_file(hint)
            if fmt == "api":
                return hint, overrides_from_embedded(base, embedded), "hint_fallback"
        except (FileNotFoundError, ValueError):
            pass
    return None, {}, "no_match"


def build_restore_snapshot_from_image(
    *,
    filename: str,
    subfolder: str = "",
    folder_type: str = "output",
    fallback_snapshot: dict | None = None,
) -> dict[str, Any]:
    """
    优先解析 PNG 内嵌 prompt；无法解析时使用 fallback_snapshot。
    本地无匹配工作流时，自动导入 variants/png_<hash>。
    """
    fallback_snapshot = fallback_snapshot if isinstance(fallback_snapshot, dict) else None
    filepath = job_service.resolve_image_path(filename, subfolder, folder_type)
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"图片不存在: {filename}")

    raw = open(filepath, "rb").read()
    source = "png"
    messages: list[str] = []
    imported_variant = False

    try:
        chunks = _read_png_text_chunks(raw)
        prompt_raw = chunks.get("prompt")
        if not prompt_raw:
            raise ValueError("PNG 中未找到 ComfyUI 元数据")
        data = json.loads(prompt_raw)
        embedded = _to_api_prompt(data, "api" if ws._is_api_prompt(data) else "ui")
    except Exception as e:
        log.info("PNG 元数据解析失败 %s: %s", filename, e)
        if fallback_snapshot:
            source = "fallback_snapshot"
            snap = dict(fallback_snapshot)
            snap["restore_source"] = source
            msg = "图片无内嵌工作流，已使用记录中的快照"
            snap["restore_message"] = msg
            return {
                "ok": True,
                "source": source,
                "imported_variant": False,
                "snapshot": snap,
                "message": msg,
            }
        raise ValueError(f"无法从 PNG 读取工作流: {e}") from e

    positive, negative = _extract_clip_texts(embedded)
    seed = _extract_seed(embedded)
    batch_prompts = _batch_prompts_from_texts(positive, negative)

    hint = None
    if fallback_snapshot:
        hint = (fallback_snapshot.get("workflow_id") or "").strip() or None

    workflow_id, overrides, match_reason = _try_resolve_local_workflow(embedded, hint)

    if not workflow_id or match_reason == "no_match":
        workflow_id = _ensure_variant_from_png(
            raw,
            filename=filename,
            display_stem=os.path.splitext(filename)[0],
        )
        imported_variant = True
        overrides = {}
        messages.append(f"已从 PNG 导入子工作流「{workflow_id}」")
    elif match_reason == "matched_local":
        messages.append(f"已从 PNG 匹配本地工作流「{workflow_id}」")
    else:
        messages.append(f"已用记录工作流「{workflow_id}」并合并 PNG 参数")

    snap: dict[str, Any] = {
        "workflow_id": workflow_id,
        "overrides": overrides,
        "batch_prompts": batch_prompts,
        "seed": seed,
        "restore_source": "png_metadata",
        "imported_variant": imported_variant,
        "temporary_workflow": imported_variant or match_reason == "no_match",
        "restore_message": "",
    }

    if fallback_snapshot:
        for key in (
            "style_enabled",
            "prompt_global_priority",
            "seed_mode",
            "prompt_picks",
            "loras",
        ):
            if snap.get(key) is None and fallback_snapshot.get(key) is not None:
                snap[key] = fallback_snapshot[key]
        if not seed and fallback_snapshot.get("seed") is not None:
            snap["seed"] = fallback_snapshot["seed"]

    snap["restore_message"] = " · ".join(messages) if messages else ""

    return {
        "ok": True,
        "source": source,
        "imported_variant": imported_variant,
        "snapshot": snap,
        "message": snap["restore_message"],
        "has_png_prompt": True,
        "positive_preview": (positive or "")[:120],
        "negative_preview": (negative or "")[:80],
    }
