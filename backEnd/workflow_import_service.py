"""工作流导入：JSON / 含 ComfyUI 元数据的 PNG，节点识别与创建子工作流。"""
from __future__ import annotations

import json
import re
import struct
import zlib
from typing import Any

from config import WORKFLOW_TEMPLATE_ID
from workflow_meta_service import (
    VARIANT_PREFIX,
    _infer_meta_from_template,
    _variant_json_path,
    allocate_variant_id,
    load_meta,
    sanitize_variant_id,
    save_meta,
)
from workflow_service import (
    _is_api_prompt,
    discover_lora_nodes,
    discover_workflow_targets,
    save_workflow_file,
)

# 可编辑 + 常见管线节点（视为已识别）
_INFRA_CLASS_TYPES = frozenset({
    "CheckpointLoaderSimple",
    "CLIPSetLastLayer",
    "LoraLoader",
    "LoraLoaderModelOnly",
    "CLIPTextEncode",
    "KSampler",
    "KSamplerAdvanced",
    "EmptyLatentImage",
    "SaveImage",
    "PreviewImage",
    "VAELoader",
    "VAEDecode",
    "VAEEncode",
    "LatentUpscale",
    "LatentUpscaleBy",
    "ImageScale",
    "UpscaleModelLoader",
    "ImageUpscaleWithModel",
    "LoadImage",
    "ControlNetLoader",
    "ControlNetApply",
    "ControlNetApplyAdvanced",
    "Note",
    "Reroute",
})


def _load_recognized_class_types() -> frozenset[str]:
    from workflow_service import _load_editable_rules

    types = set(_INFRA_CLASS_TYPES)
    for rule in _load_editable_rules():
        types.update(rule.get("class_types") or [])
    return frozenset(types)


def _read_png_text_chunks(data: bytes) -> dict[str, str]:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("不是有效的 PNG 文件")
    pos = 8
    out: dict[str, str] = {}
    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        chunk_type = data[pos + 4 : pos + 8]
        chunk_data = data[pos + 8 : pos + 8 + length]
        pos += 8 + length + 4
        if chunk_type == b"tEXt":
            sep = chunk_data.find(b"\x00")
            if sep >= 0:
                key = chunk_data[:sep].decode("latin-1", errors="replace")
                val = chunk_data[sep + 1 :].decode("utf-8", errors="replace")
                out[key] = val
        elif chunk_type == b"iTXt":
            parts = chunk_data.split(b"\x00", 5)
            if len(parts) >= 6:
                key = parts[0].decode("latin-1", errors="replace")
                compressed = parts[1] == b"\x01"
                raw = parts[5]
                if compressed:
                    try:
                        raw = zlib.decompress(raw)
                    except zlib.error:
                        continue
                out[key] = raw.decode("utf-8", errors="replace")
    return out


def _parse_workflow_payload(raw: bytes, *, filename: str = "") -> tuple[str, dict, str]:
    """返回 (source, data, format_hint)。"""
    name = (filename or "").lower()
    if name.endswith(".json") or raw.lstrip()[:1] in (b"{", b"["):
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise ValueError(f"JSON 解析失败: {e}") from e
        if not isinstance(data, dict):
            raise ValueError("工作流 JSON 须为对象")
        fmt = "api" if _is_api_prompt(data) else "ui"
        return "json", data, fmt

    if name.endswith(".png") or raw.startswith(b"\x89PNG"):
        chunks = _read_png_text_chunks(raw)
        prompt_raw = chunks.get("prompt")
        if not prompt_raw:
            raise ValueError("PNG 中未找到 ComfyUI 工作流元数据（prompt 字段）")
        try:
            data = json.loads(prompt_raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"PNG 内 prompt 不是有效 JSON: {e}") from e
        if not isinstance(data, dict):
            raise ValueError("PNG 内 prompt 格式无效")
        fmt = "api" if _is_api_prompt(data) else "ui"
        return "png", data, fmt

    raise ValueError("请上传 .json 工作流或含 ComfyUI 元数据的 .png 图片")


def _to_api_prompt(data: dict, fmt: str) -> dict:
    if fmt == "api":
        return data
    from comfy_client import get_object_info
    from ui_workflow import ui_to_api

    try:
        return ui_to_api(data, get_object_info())
    except Exception as e:
        raise ValueError(f"UI 工作流无法转换为 API 格式: {e}") from e


def _node_title(node_id: str, node: dict) -> str:
    meta = node.get("_meta") or {}
    title = meta.get("title") or node.get("class_type") or node_id
    return str(title)


def analyze_workflow_prompt(prompt: dict) -> dict[str, Any]:
    recognized_types = _load_recognized_class_types()
    recognized: list[dict[str, str]] = []
    unrecognized: list[dict[str, str]] = []

    for node_id, node in sorted(prompt.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else x[0]):
        if not isinstance(node, dict):
            continue
        class_type = str(node.get("class_type") or "")
        title = _node_title(str(node_id), node)
        entry = {
            "node_id": str(node_id),
            "class_type": class_type,
            "title": title,
        }
        if class_type in recognized_types:
            recognized.append(entry)
        else:
            unrecognized.append(entry)

    loras = discover_lora_nodes(prompt)
    targets = discover_workflow_targets(prompt)
    ckpt = next(
        (
            {
                "node_id": nid,
                "ckpt_name": n.get("inputs", {}).get("ckpt_name"),
            }
            for nid, n in prompt.items()
            if n.get("class_type") == "CheckpointLoaderSimple"
        ),
        None,
    )

    return {
        "node_count": len([k for k in prompt if isinstance(prompt.get(k), dict)]),
        "recognized": recognized,
        "unrecognized": unrecognized,
        "unrecognized_names": [f"{n['title']} ({n['class_type']} #{n['node_id']})" for n in unrecognized],
        "checkpoint": ckpt,
        "lora_count": len(loras),
        "loras": loras,
        "targets": targets,
        "can_import": bool(ckpt) or len(loras) > 0 or len(recognized) > 0,
        "warnings": [] if ckpt else ["未检测到 CheckpointLoaderSimple 节点"],
    }


def infer_topology_from_prompt(prompt: dict) -> dict[str, Any]:
    """从 API prompt 推断 meta.topology（导入子工作流用）。"""
    ckpt_nid = next(
        (str(nid) for nid, n in prompt.items() if n.get("class_type") == "CheckpointLoaderSimple"),
        "1",
    )
    clip_nid = next(
        (str(nid) for nid, n in prompt.items() if n.get("class_type") == "CLIPSetLastLayer"),
        "2",
    )
    loras = discover_lora_nodes(prompt)
    slots = []
    for i, l in enumerate(loras):
        role = "style" if i == len(loras) - 1 and len(loras) > 1 else "character"
        slots.append({
            "node_id": l["node_id"],
            "role": role,
            "kind": "lora_chain",
            "optional": role == "style",
            "sweepable": True,
            "title": l.get("title") or ("Style LoRA" if role == "style" else "角色 LoRA"),
        })

    encodes = sorted(
        [(str(nid), n) for nid, n in prompt.items() if n.get("class_type") == "CLIPTextEncode"],
        key=lambda x: int(x[0]) if x[0].isdigit() else x[0],
    )
    pos_nid = encodes[0][0] if encodes else "3"
    neg_nid = encodes[1][0] if len(encodes) > 1 else "4"
    char_nid = slots[0]["node_id"] if slots else ckpt_nid
    style_slot = next((s for s in slots if s.get("role") == "style"), None)

    ksamplers = sorted(
        [str(nid) for nid, n in prompt.items() if n.get("class_type") == "KSampler"],
        key=lambda x: int(x) if x.isdigit() else x,
    )
    save_nid = next(
        (str(nid) for nid, n in prompt.items() if n.get("class_type") == "SaveImage"),
        "8",
    )

    rewire = []
    if style_slot and char_nid:
        rewire = [
            {"target_node": neg_nid, "input_key": "clip", "source": [char_nid, 1]},
            {"target_node": ksamplers[0], "input_key": "model", "source": [char_nid, 0]}
            if ksamplers
            else None,
        ]
        rewire = [r for r in rewire if r]
        if len(ksamplers) > 1:
            rewire.append(
                {"target_node": ksamplers[1], "input_key": "model", "source": [char_nid, 0]},
            )

    return {
        "checkpoint_node": ckpt_nid,
        "clip_set_last_layer": clip_nid,
        "lora_slots": slots,
        "positive_encode": {"node_id": pos_nid, "clip_source_node": char_nid},
        "negative_encode": {
            "node_id": neg_nid,
            "clip_source_node": style_slot["node_id"] if style_slot else char_nid,
        },
        "ksampler_pass1": ksamplers[0] if ksamplers else "5",
        "ksampler_pass2": ksamplers[1] if len(ksamplers) > 1 else "14",
        "save_image": save_nid,
        "style_bypass_when_disabled": {
            "node_id": style_slot["node_id"] if style_slot else None,
            "fallback_node_id": char_nid,
            "rewire": rewire,
        },
        "future_conditioning_style": {"enabled": False},
    }


def analyze_import_file(raw: bytes, *, filename: str = "") -> dict[str, Any]:
    source, data, fmt = _parse_workflow_payload(raw, filename=filename)
    prompt = _to_api_prompt(data, fmt)
    analysis = analyze_workflow_prompt(prompt)
    return {
        "source": source,
        "format": "api",
        "original_format": fmt,
        **analysis,
    }


def import_as_variant(
    raw: bytes,
    *,
    variant_id: str | None = None,
    display_name: str | None = None,
    filename: str = "",
) -> dict[str, Any]:
    source, data, fmt = _parse_workflow_payload(raw, filename=filename)
    prompt = _to_api_prompt(data, fmt)
    analysis = analyze_workflow_prompt(prompt)

    if variant_id:
        safe = sanitize_variant_id(variant_id)
        if not safe:
            raise ValueError("子工作流 ID 无效")
        json_path = _variant_json_path(safe)
        if json_path.exists():
            raise ValueError(f"子工作流已存在: {safe}")
    else:
        stem = re.sub(r"\.(json|png)$", "", filename or "", flags=re.I)
        safe = allocate_variant_id(display_name or stem or None)

    json_path = _variant_json_path(safe)

    workflow_id = f"{VARIANT_PREFIX}{safe}"
    save_workflow_file(workflow_id, prompt)

    template_meta = load_meta(WORKFLOW_TEMPLATE_ID) or _infer_meta_from_template(WORKFLOW_TEMPLATE_ID)
    meta = {
        "schema_version": 1,
        "template_id": WORKFLOW_TEMPLATE_ID,
        "is_master": False,
        "variant_id": safe,
        "display_name": display_name or safe,
        "style_enabled": template_meta.get("style_enabled_default", False),
        "style_enabled_default": template_meta.get("style_enabled_default", False),
        "topology": infer_topology_from_prompt(prompt),
        "import_source": source,
        "import_original_format": fmt,
    }
    save_meta(workflow_id, meta)

    return {
        "id": workflow_id,
        "variant_id": safe,
        "display_name": meta["display_name"],
        "analysis": analysis,
    }


def delete_variant(workflow_id: str) -> dict[str, str]:
    from workflow_meta_service import META_SUFFIX, WORKFLOW_VARIANTS_DIR, normalize_variant_workflow_id

    workflow_id = normalize_variant_workflow_id(workflow_id)
    if not workflow_id.startswith(VARIANT_PREFIX):
        raise ValueError("只能删除子工作流")
    vid = workflow_id.split("/", 1)[1]
    json_path = _variant_json_path(vid)
    meta_path = WORKFLOW_VARIANTS_DIR / f"{vid}{META_SUFFIX}"
    if not json_path.is_file() and not meta_path.is_file():
        raise FileNotFoundError(f"子工作流不存在: {workflow_id}")
    if json_path.is_file():
        json_path.unlink()
    if meta_path.is_file():
        meta_path.unlink()
    return {"id": workflow_id, "variant_id": vid}
