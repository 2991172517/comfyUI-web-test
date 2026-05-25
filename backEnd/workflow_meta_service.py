"""工作流元数据：拓扑、分类、Style 开关（LoRA 链 / 未来 conditioning）。"""
from __future__ import annotations

import copy
import json
import re
import uuid
from pathlib import Path
from typing import Any

from config import (
    WORKFLOW_SEED_ID,
    WORKFLOW_TEMPLATE_ID,
    WORKFLOW_VARIANTS_DIR,
    WORKFLOWS_DIR,
)
from workflow_categories import category_for_meta, normalize_category

META_SUFFIX = ".meta.json"
VARIANT_PREFIX = "variants/"


def variant_id_from_meta_filename(filename: str) -> str:
    """test_chain_edit.meta.json → test_chain_edit（避免 stem 变成 test_chain_edit.meta）。"""
    name = filename
    if name.endswith(META_SUFFIX):
        return name[: -len(META_SUFFIX)]
    if name.endswith(".json"):
        return name[: -len(".json")]
    return name


def normalize_variant_workflow_id(workflow_id: str) -> str:
    """修正历史错误 ID：variants/test_chain_edit.meta → variants/test_chain_edit。"""
    if not workflow_id.startswith(VARIANT_PREFIX):
        return workflow_id
    vid = workflow_id.split("/", 1)[1]
    if vid.endswith(".meta"):
        vid = vid[: -len(".meta")]
        return f"{VARIANT_PREFIX}{vid}"
    return workflow_id


def _meta_path_for_workflow(workflow_id: str) -> Path:
    workflow_id = normalize_variant_workflow_id(workflow_id)
    if workflow_id.startswith(VARIANT_PREFIX):
        name = workflow_id.split("/", 1)[1]
        return WORKFLOW_VARIANTS_DIR / f"{name}{META_SUFFIX}"
    return WORKFLOWS_DIR / f"{workflow_id}{META_SUFFIX}"


def sanitize_variant_id(raw: str) -> str:
    return re.sub(r"[^\w\-]+", "_", (raw or "").strip()).strip("_")


def _variant_exists(safe: str) -> bool:
    return _variant_json_path(safe, strict=False).exists() or (
        WORKFLOW_VARIANTS_DIR / f"{safe}{META_SUFFIX}"
    ).exists()


def allocate_variant_id(base: str | None = None) -> str:
    """分配唯一子工作流 ID；base 可为显示名或文件名 stem。"""
    safe = sanitize_variant_id(base) if base else ""
    if not safe:
        safe = f"variant_{uuid.uuid4().hex[:8]}"
    candidate = safe
    n = 2
    while _variant_exists(candidate):
        candidate = f"{safe}_{n}"
        n += 1
    return candidate


def _variant_json_path(variant_id: str, *, strict: bool = True) -> Path:
    safe = sanitize_variant_id(variant_id)
    if not safe and strict:
        raise ValueError("子工作流 ID 无效")
    return WORKFLOW_VARIANTS_DIR / f"{safe}.json"


def load_meta(workflow_id: str) -> dict | None:
    path = _meta_path_for_workflow(workflow_id)
    if not path.is_file():
        if workflow_id == WORKFLOW_TEMPLATE_ID or workflow_id.endswith(WORKFLOW_TEMPLATE_ID):
            return _infer_meta_from_template(workflow_id)
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_meta(workflow_id: str, meta: dict) -> None:
    path = _meta_path_for_workflow(workflow_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


def _infer_meta_from_template(workflow_id: str) -> dict:
    """无 meta 文件时从 First_api 结构推断（与 First_api.meta.json 一致）。"""
    from workflow_service import discover_lora_nodes, load_workflow_file

    fmt, data = load_workflow_file(workflow_id)
    if fmt != "api":
        raise ValueError("仅 API 工作流支持元数据推断")
    loras = discover_lora_nodes(data)
    slots = []
    for i, l in enumerate(loras):
        role = "style" if i == len(loras) - 1 and len(loras) > 1 else "character"
        slots.append({
            "node_id": l["node_id"],
            "role": role,
            "kind": "lora_chain",
            "optional": role == "style",
            "sweepable": True,
            "title": "Style LoRA" if role == "style" else "角色 LoRA",
        })
    style_node = slots[-1]["node_id"] if len(slots) > 1 else None
    char_node = slots[0]["node_id"] if slots else None
    rewire = []
    if style_node and char_node:
        rewire = [
            {"target_node": "4", "input_key": "clip", "source": [char_node, 1]},
            {"target_node": "5", "input_key": "model", "source": [char_node, 0]},
            {"target_node": "14", "input_key": "model", "source": [char_node, 0]},
        ]
    return {
        "schema_version": 1,
        "template_id": WORKFLOW_TEMPLATE_ID,
        "is_master": workflow_id == WORKFLOW_TEMPLATE_ID,
        "display_name": workflow_id,
        "style_enabled_default": False,
        "topology": {
            "lora_slots": slots,
            "style_bypass_when_disabled": {
                "node_id": style_node,
                "fallback_node_id": char_node,
                "rewire": rewire,
            },
            "future_conditioning_style": {"enabled": False},
        },
    }


def get_enabled_preview_node_ids(meta: dict) -> list[str]:
    """已勾选的 PreviewImage 节点 ID；默认空列表（不跑任何预览）。"""
    raw = meta.get("enabled_preview_node_ids")
    if raw is None:
        raw = (meta.get("topology") or {}).get("enabled_preview_node_ids")
    if not raw:
        return []
    return [str(x) for x in raw if str(x).strip()]


def get_effective_meta(workflow_id: str, runtime: dict | None = None) -> dict:
    meta = load_meta(workflow_id) or _infer_meta_from_template(
        WORKFLOW_TEMPLATE_ID if workflow_id.startswith(VARIANT_PREFIX) else workflow_id
    )
    meta = copy.deepcopy(meta)
    if runtime:
        meta.update({k: v for k, v in runtime.items() if k in ("style_enabled", "display_name")})
    if "style_enabled" not in meta:
        meta["style_enabled"] = meta.get("style_enabled_default", False)
    return meta


def list_variants() -> list[dict]:
    WORKFLOW_VARIANTS_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for path in sorted(WORKFLOW_VARIANTS_DIR.glob(f"*{META_SUFFIX}")):
        vid = variant_id_from_meta_filename(path.name)
        with open(path, encoding="utf-8") as f:
            meta = json.load(f)
        wid = f"{VARIANT_PREFIX}{vid}"
        items.append({
            "id": wid,
            "variant_id": vid,
            "display_name": meta.get("display_name", vid),
            "category": category_for_meta(wid, meta),
            "style_enabled": meta.get("style_enabled", meta.get("style_enabled_default", False)),
            "path": str(path),
        })
    return items


def create_variant(
    variant_id: str | None = None,
    display_name: str | None = None,
    *,
    category: str | None = None,
    copy_from: str | None = None,
) -> dict:
    if variant_id:
        safe = sanitize_variant_id(variant_id)
        if not safe:
            raise ValueError("子工作流 ID 无效")
        if _variant_exists(safe):
            raise ValueError(f"子工作流已存在: {safe}")
    else:
        safe = allocate_variant_id(display_name)
    json_path = _variant_json_path(safe)
    meta_path = WORKFLOW_VARIANTS_DIR / f"{safe}{META_SUFFIX}"
    workflow_id = f"{VARIANT_PREFIX}{safe}"
    cat = normalize_category(category)

    from workflow_service import load_workflow_file, save_workflow_file

    if copy_from:
        src_id = normalize_variant_workflow_id(copy_from.strip())
        if not src_id.startswith(VARIANT_PREFIX):
            raise ValueError("只能复制 variants/ 下的工作流")
        _, data = load_workflow_file(src_id)
        src_meta = load_meta(src_id) or {}
        topology = copy.deepcopy(src_meta.get("topology") or {})
        style_default = src_meta.get("style_enabled_default", False)
        cat = normalize_category(category or src_meta.get("category"))
    else:
        seed_id = WORKFLOW_SEED_ID
        try:
            _, data = load_workflow_file(seed_id)
        except FileNotFoundError:
            _, data = load_workflow_file(WORKFLOW_TEMPLATE_ID)
            seed_meta = load_meta(WORKFLOW_TEMPLATE_ID) or _infer_meta_from_template(WORKFLOW_TEMPLATE_ID)
            topology = copy.deepcopy(seed_meta.get("topology", {}))
            style_default = seed_meta.get("style_enabled_default", False)
        else:
            from workflow_import_service import infer_topology_from_prompt

            topology = infer_topology_from_prompt(data)
            seed_meta = load_meta(seed_id) or {}
            style_default = seed_meta.get("style_enabled_default", False)
        save_workflow_file(workflow_id, data)

    if copy_from:
        save_workflow_file(workflow_id, data)

    meta = {
        "schema_version": 1,
        "variant_id": safe,
        "category": cat,
        "display_name": display_name or safe,
        "style_enabled": style_default if copy_from else False,
        "style_enabled_default": style_default,
        "topology": topology,
    }
    if copy_from:
        meta["copied_from"] = src_id
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    return {
        "id": workflow_id,
        "variant_id": safe,
        "display_name": meta["display_name"],
        "category": cat,
        "workflow_path": str(json_path),
        "meta_path": str(meta_path),
    }


def apply_topology(prompt: dict, meta: dict) -> dict:
    """Style 关闭时绕过 style LoRA 节点；未来可扩展 conditioning Style。"""
    result = copy.deepcopy(prompt)
    if meta.get("style_enabled", True):
        return result

    topo = meta.get("topology") or {}
    bypass = topo.get("style_bypass_when_disabled") or {}
    valid_ids = {str(k) for k in result}
    for rule in bypass.get("rewire") or []:
        nid = str(rule.get("target_node"))
        key = rule.get("input_key")
        src = rule.get("source")
        if not (nid in result and key and src):
            continue
        if isinstance(src, list) and len(src) >= 1 and str(src[0]) not in valid_ids:
            continue
        result[nid].setdefault("inputs", {})[key] = copy.deepcopy(src)

    future = topo.get("future_conditioning_style") or {}
    if future.get("enabled") and future.get("node_id"):
        pass  # 预留：正向 conditioning 插入点

    return result


def lora_slots_from_meta(meta: dict, workflow_id: str | None = None) -> list[dict]:
    """供批量/前端展示：带 role、optional、sweepable。"""
    from workflow_service import discover_lora_nodes, load_workflow_file

    template_id = meta.get("template_id", WORKFLOW_TEMPLATE_ID)
    if workflow_id:
        wid = workflow_id
    elif meta.get("is_master"):
        wid = template_id
    elif meta.get("variant_id"):
        wid = f"{VARIANT_PREFIX}{meta['variant_id']}"
    else:
        wid = template_id

    try:
        _, data = load_workflow_file(wid)
    except FileNotFoundError:
        _, data = load_workflow_file(template_id)

    discovered = {x["node_id"]: x for x in discover_lora_nodes(data)}
    slot_list = meta.get("topology", {}).get("lora_slots", [])
    slots = []
    for s in slot_list:
        nid = str(s.get("node_id"))
        base = discovered.get(nid, {})
        slots.append({
            **base,
            "node_id": nid,
            "role": s.get("role", "lora"),
            "kind": s.get("kind", "lora_chain"),
            "optional": bool(s.get("optional", False)),
            "sweepable": bool(s.get("sweepable", True)),
            "title": s.get("title") or base.get("short_name", nid),
        })
    return slots


def enrich_workflow_detail(workflow_id: str, detail: dict, meta: dict | None = None) -> dict:
    m = meta or get_effective_meta(workflow_id)
    detail = copy.deepcopy(detail)
    detail["meta"] = m
    detail["style_enabled"] = m.get("style_enabled", False)
    detail["is_master"] = False
    detail["display_name"] = m.get("display_name", workflow_id)
    detail["category"] = category_for_meta(workflow_id, m)

    topo = m.get("topology", {})
    slot_by_id = {str(s["node_id"]): s for s in topo.get("lora_slots", [])}
    loras = []
    for l in detail.get("loras", []):
        extra = slot_by_id.get(l["node_id"], {})
        loras.append({**l, **{k: extra[k] for k in ("role", "kind", "optional", "sweepable", "title") if k in extra}})
    detail["loras"] = loras
    detail["lora_slots"] = list(topo.get("lora_slots", []))
    detail["prompt_encode"] = resolve_prompt_encode(
        m, detail.get("prompt") or {}, detail.get("nodes") or []
    )
    from workflow_service import discover_pipeline_nodes, discover_preview_nodes

    prompt = detail.get("prompt") or {}
    detail["pipeline_nodes"] = discover_pipeline_nodes(prompt)
    detail["preview_nodes"] = discover_preview_nodes(prompt)
    detail["enabled_preview_node_ids"] = get_enabled_preview_node_ids(m)
    return detail


def resolve_prompt_encode(meta: dict, prompt: dict, nodes: list[dict]) -> dict:
    """识别正向 / 负向 CLIPTextEncode 节点（优先 meta.topology）。"""
    topo = meta.get("topology") or {}
    node_by_id = {str(n.get("id")): n for n in nodes}

    def _info(spec: dict, side: str, fallback_title: str) -> dict:
        nid = str(spec.get("node_id") or "")
        n = node_by_id.get(nid, {})
        title = n.get("title") or fallback_title
        if nid and nid in prompt:
            raw = prompt[nid].get("inputs", {}).get("text", "")
            preview = "" if isinstance(raw, list) else str(raw)
        else:
            preview = ""
        return {
            "node_id": nid,
            "side": side,
            "title": title,
            "text_preview": preview[:120] + ("…" if len(preview) > 120 else ""),
        }

    pos_spec = topo.get("positive_encode") or {}
    neg_spec = topo.get("negative_encode") or {}
    positive = _info(pos_spec, "positive", "正向 CLIPTextEncode")
    negative = _info(neg_spec, "negative", "负向 CLIPTextEncode")

    clip_nodes = sorted(
        [n for n in nodes if n.get("group") == "提示词"],
        key=lambda x: int(x["id"]) if str(x.get("id", "")).isdigit() else x.get("id", ""),
    )
    if not positive.get("node_id") and clip_nodes:
        positive = _info({"node_id": clip_nodes[0]["id"]}, "positive", clip_nodes[0].get("title", ""))
    if not negative.get("node_id") and len(clip_nodes) > 1:
        negative = _info({"node_id": clip_nodes[1]["id"]}, "negative", clip_nodes[1].get("title", ""))
    elif not negative.get("node_id") and len(clip_nodes) == 1:
        negative = {"node_id": "", "side": "negative", "title": "未配置", "text_preview": ""}

    return {"positive": positive, "negative": negative}
