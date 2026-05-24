"""工作流核心链：Checkpoint + LoRA 链增删改（非全节点画布）。"""
from __future__ import annotations

import copy
import json
from typing import Any

from config import WORKFLOW_TEMPLATE_ID
from workflow_meta_service import (
    VARIANT_PREFIX,
    get_effective_meta,
    load_meta,
    save_meta,
)
from workflow_service import (
    LORA_CLASS_TYPES,
    apply_overrides,
    discover_lora_nodes,
    is_master_workflow,
    load_workflow_file,
    save_workflow_file,
    _sort_node_id,
)

MAX_LORA_SLOTS = 5
MAX_STYLE_SLOTS = 1


def _next_node_id(prompt: dict) -> str:
    nums = [int(k) for k in prompt if str(k).isdigit()]
    return str(max(nums) + 1 if nums else 100)


def _checkpoint_and_clip(meta: dict) -> tuple[str, str]:
    topo = meta.get("topology") or {}
    return str(topo.get("checkpoint_node", "1")), str(topo.get("clip_set_last_layer", "2"))


def _lora_slots(meta: dict) -> list[dict]:
    return list((meta.get("topology") or {}).get("lora_slots") or [])


def _set_lora_slots(meta: dict, slots: list[dict]) -> None:
    meta.setdefault("topology", {})["lora_slots"] = slots


def _upstream_for_insert(prompt: dict, meta: dict, after_node_id: str | None) -> tuple[list, list]:
    ckpt, clip = _checkpoint_and_clip(meta)
    if not after_node_id:
        slots = _lora_slots(meta)
        if not slots:
            return [ckpt, 0], [clip, 0]
        last = slots[-1]
        if last.get("role") == "style" and len(slots) > 1:
            after_node_id = slots[-2]["node_id"]
        else:
            after_node_id = last["node_id"]
    after = str(after_node_id)
    if after == ckpt:
        return [ckpt, 0], [clip, 0]
    node = prompt.get(after, {})
    if node.get("class_type") in LORA_CLASS_TYPES:
        return [after, 0], [after, 1]
    if after == clip:
        return [ckpt, 0], [clip, 0]
    return [ckpt, 0], [clip, 0]


def _rebuild_clip_routing(prompt: dict, meta: dict) -> None:
    topo = meta.setdefault("topology", {})
    slots = _lora_slots(meta)
    style_slot = next((s for s in slots if s.get("role") == "style"), None)
    char_slots = [s for s in slots if s.get("role") != "style"]
    last_char = str(char_slots[-1]["node_id"]) if char_slots else None
    ckpt, clip = _checkpoint_and_clip(meta)

    pos = topo.get("positive_encode") or {}
    neg = topo.get("negative_encode") or {}
    pos_nid = str(pos.get("node_id", "3"))
    neg_nid = str(neg.get("node_id", "4"))

    if last_char and pos_nid in prompt:
        topo["positive_encode"] = {**pos, "clip_source_node": last_char}
        prompt[pos_nid].setdefault("inputs", {})["clip"] = [last_char, 1]
    elif pos_nid in prompt:
        topo["positive_encode"] = {**pos, "clip_source_node": clip}
        prompt[pos_nid].setdefault("inputs", {})["clip"] = [clip, 0]

    if style_slot and neg_nid in prompt:
        sid = str(style_slot["node_id"])
        topo["negative_encode"] = {**neg, "clip_source_node": sid}
        prompt[neg_nid].setdefault("inputs", {})["clip"] = [sid, 1]
    elif last_char and neg_nid in prompt:
        topo["negative_encode"] = {**neg, "clip_source_node": last_char}
        prompt[neg_nid].setdefault("inputs", {})["clip"] = [last_char, 1]
    elif neg_nid in prompt:
        topo["negative_encode"] = {**neg, "clip_source_node": clip}
        prompt[neg_nid].setdefault("inputs", {})["clip"] = [clip, 0]

    ks1 = str(topo.get("ksampler_pass1", "5"))
    ks2 = str(topo.get("ksampler_pass2", "14"))
    tail = str(style_slot["node_id"]) if style_slot else (last_char or ckpt)
    for ks in (ks1, ks2):
        if ks in prompt:
            prompt[ks].setdefault("inputs", {})["model"] = [tail, 0]

    if style_slot:
        fallback = last_char or ckpt
        fb_clip = [fallback, 1] if fallback != ckpt else [clip, 0]
        bypass = topo.setdefault("style_bypass_when_disabled", {})
        bypass["node_id"] = str(style_slot["node_id"])
        bypass["fallback_node_id"] = fallback
        bypass["rewire"] = [
            {
                "target_node": neg_nid,
                "input_key": "clip",
                "source": [clip, 0] if fallback == ckpt else fb_clip,
            },
            {"target_node": ks1, "input_key": "model", "source": [fallback, 0]},
            {"target_node": ks2, "input_key": "model", "source": [fallback, 0]},
        ]
    else:
        topo.pop("style_bypass_when_disabled", None)


def _topology_is_stale(prompt: dict, meta: dict) -> bool:
    valid = {str(k) for k in prompt}
    topo = meta.get("topology") or {}
    for s in topo.get("lora_slots") or []:
        if str(s.get("node_id", "")) not in valid:
            return True
    bypass = topo.get("style_bypass_when_disabled") or {}
    for key in ("node_id", "fallback_node_id"):
        nid = bypass.get(key)
        if nid and str(nid) not in valid:
            return True
    for rule in bypass.get("rewire") or []:
        src = rule.get("source")
        if isinstance(src, list) and src and str(src[0]) not in valid:
            return True
    has_style = any(s.get("role") == "style" for s in topo.get("lora_slots") or [])
    if bypass and not has_style:
        return True
    return False


def repair_stale_topology(workflow_id: str) -> bool:
    """meta / prompt 拓扑不一致时重建连接并写回。返回是否修复。"""
    if is_master_workflow(workflow_id):
        return False
    fmt, prompt = load_workflow_file(workflow_id)
    if fmt != "api":
        return False
    meta = get_effective_meta(workflow_id)
    if not _topology_is_stale(prompt, meta):
        return False
    valid = {str(k) for k in prompt}
    pruned = [s for s in _lora_slots(meta) if str(s.get("node_id", "")) in valid]
    _set_lora_slots(meta, pruned)
    _rebuild_clip_routing(prompt, meta)
    save_workflow_file(workflow_id, prompt)
    save_meta(workflow_id, meta)
    return True


def get_workflow_essentials(workflow_id: str) -> dict:
    fmt, prompt = load_workflow_file(workflow_id)
    if fmt != "api":
        raise ValueError("仅支持 API 格式工作流")
    meta = get_effective_meta(workflow_id)
    ckpt_nid, _ = _checkpoint_and_clip(meta)
    ckpt_inputs = prompt.get(ckpt_nid, {}).get("inputs", {})
    slots = _lora_slots(meta)
    discovered = {x["node_id"]: x for x in discover_lora_nodes(prompt)}
    chain = []
    for s in slots:
        nid = str(s["node_id"])
        d = discovered.get(nid, {})
        chain.append({
            **s,
            "node_id": nid,
            "lora_name": d.get("lora_name", ""),
            "strength_model": d.get("strength_model", 1.0),
            "strength_clip": d.get("strength_clip", 1.0),
            "short_name": d.get("short_name", nid),
            "can_remove": True,
        })
    return {
        "workflow_id": workflow_id,
        "display_name": meta.get("display_name", workflow_id),
        "is_master": is_master_workflow(workflow_id),
        "style_enabled": meta.get("style_enabled", False),
        "checkpoint": {
            "node_id": ckpt_nid,
            "ckpt_name": ckpt_inputs.get("ckpt_name", ""),
        },
        "lora_chain": chain,
        "limits": {"max_loras": MAX_LORA_SLOTS, "max_style": MAX_STYLE_SLOTS},
    }


def apply_workflow_essentials(workflow_id: str, body: dict) -> dict:
    if is_master_workflow(workflow_id):
        raise ValueError("母版工作流只读，请另存为子工作流后修改")
    fmt, prompt = load_workflow_file(workflow_id)
    meta = get_effective_meta(workflow_id)
    overrides: dict[str, dict[str, Any]] = {}

    ckpt = body.get("checkpoint") or {}
    ckpt_nid = str(ckpt.get("node_id") or _checkpoint_and_clip(meta)[0])
    if ckpt.get("ckpt_name") is not None:
        overrides[ckpt_nid] = {"ckpt_name": ckpt["ckpt_name"]}

    for item in body.get("lora_chain") or []:
        nid = str(item.get("node_id", ""))
        if not nid:
            continue
        patch: dict[str, Any] = {}
        if item.get("lora_name") is not None:
            patch["lora_name"] = item["lora_name"]
        if item.get("strength_model") is not None:
            patch["strength_model"] = float(item["strength_model"])
        if item.get("strength_clip") is not None:
            patch["strength_clip"] = float(item["strength_clip"])
        if item.get("title"):
            prompt.setdefault(nid, {})["_meta"] = {
                **(prompt.get(nid, {}).get("_meta") or {}),
                "title": item["title"],
            }
        if patch:
            overrides[nid] = patch
        slots = _lora_slots(meta)
        for s in slots:
            if str(s["node_id"]) == nid:
                if item.get("title"):
                    s["title"] = item["title"]
                break

    prompt = apply_overrides(prompt, overrides)

    if body.get("style_enabled") is not None:
        meta["style_enabled"] = bool(body["style_enabled"])
    if body.get("display_name"):
        meta["display_name"] = body["display_name"]

    save_workflow_file(workflow_id, prompt)
    save_meta(workflow_id, meta)
    return get_workflow_essentials(workflow_id)


def add_lora_slot(
    workflow_id: str,
    *,
    role: str = "character",
    after_node_id: str | None = None,
    lora_name: str = "None",
    title: str | None = None,
) -> dict:
    if is_master_workflow(workflow_id):
        raise ValueError("母版工作流只读")
    role = role if role in ("character", "style") else "character"
    fmt, prompt = load_workflow_file(workflow_id)
    meta = get_effective_meta(workflow_id)
    slots = _lora_slots(meta)
    if len(slots) >= MAX_LORA_SLOTS:
        raise ValueError(f"LoRA 链最多 {MAX_LORA_SLOTS} 个")
    if role == "style" and sum(1 for s in slots if s.get("role") == "style") >= MAX_STYLE_SLOTS:
        raise ValueError("每条工作流仅允许 1 个 Style LoRA")

    if role == "style":
        after_node_id = after_node_id or (slots[-1]["node_id"] if slots else _checkpoint_and_clip(meta)[0])
        insert_idx = len(slots)
    else:
        style_idx = next((i for i, s in enumerate(slots) if s.get("role") == "style"), len(slots))
        if after_node_id:
            insert_idx = next(
                (i + 1 for i, s in enumerate(slots) if str(s["node_id"]) == str(after_node_id)),
                style_idx,
            )
        else:
            insert_idx = style_idx
        if insert_idx > style_idx:
            insert_idx = style_idx
        if not after_node_id and insert_idx > 0:
            after_node_id = slots[insert_idx - 1]["node_id"]
        elif not after_node_id:
            after_node_id = _checkpoint_and_clip(meta)[0]

    model_in, clip_in = _upstream_for_insert(prompt, meta, after_node_id)
    new_id = _next_node_id(prompt)
    prompt[new_id] = {
        "class_type": "LoraLoader",
        "inputs": {
            "lora_name": lora_name,
            "strength_model": 0.65,
            "strength_clip": 0.65,
            "model": model_in,
            "clip": clip_in,
        },
        "_meta": {"title": title or ("Style LoRA" if role == "style" else "角色 LoRA")},
    }

    downstream = slots[insert_idx:]
    for s in downstream:
        nid = str(s["node_id"])
        if nid in prompt and prompt[nid].get("class_type") in LORA_CLASS_TYPES:
            prompt[nid]["inputs"]["model"] = [new_id, 0]
            prompt[nid]["inputs"]["clip"] = [new_id, 1]

    new_slot = {
        "node_id": new_id,
        "role": role,
        "kind": "lora_chain",
        "optional": role == "style",
        "sweepable": True,
        "title": title or ("Style LoRA" if role == "style" else "角色 LoRA"),
    }
    slots.insert(insert_idx, new_slot)
    _set_lora_slots(meta, slots)
    _rebuild_clip_routing(prompt, meta)
    save_workflow_file(workflow_id, prompt)
    save_meta(workflow_id, meta)
    return get_workflow_essentials(workflow_id)


def remove_lora_slot(workflow_id: str, node_id: str) -> dict:
    if is_master_workflow(workflow_id):
        raise ValueError("母版工作流只读")
    fmt, prompt = load_workflow_file(workflow_id)
    meta = get_effective_meta(workflow_id)
    slots = _lora_slots(meta)
    nid = str(node_id)
    idx = next((i for i, s in enumerate(slots) if str(s["node_id"]) == nid), -1)
    if idx < 0:
        raise ValueError(f"LoRA 节点不在链中: {nid}")

    removed = slots[idx]
    prev_id = slots[idx - 1]["node_id"] if idx > 0 else _checkpoint_and_clip(meta)[0]
    ckpt, clip = _checkpoint_and_clip(meta)
    if idx == 0:
        model_src, clip_src = [ckpt, 0], [clip, 0]
    else:
        model_src, clip_src = [str(prev_id), 0], [str(prev_id), 1]

    for s in slots[idx + 1 :]:
        sid = str(s["node_id"])
        if sid in prompt:
            prompt[sid]["inputs"]["model"] = model_src
            prompt[sid]["inputs"]["clip"] = clip_src

    del prompt[nid]
    slots.pop(idx)
    _set_lora_slots(meta, slots)
    _rebuild_clip_routing(prompt, meta)
    if removed.get("role") == "style":
        meta["style_enabled"] = False
    save_workflow_file(workflow_id, prompt)
    save_meta(workflow_id, meta)
    return get_workflow_essentials(workflow_id)
