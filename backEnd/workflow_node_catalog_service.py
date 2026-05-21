"""工作流节点目录：Checkpoint / LoRA 槽位默认配置。"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from config import PROJECT_ROOT
import workflow_service
import workflow_meta_service as wms

NODE_DEFAULTS_PATH = PROJECT_ROOT / "config" / "workflow_node_defaults.json"


def _empty_store() -> dict:
    return {"schema_version": 1, "workflows": {}}


def load_node_defaults() -> dict:
    if not NODE_DEFAULTS_PATH.is_file():
        return _empty_store()
    try:
        with open(NODE_DEFAULTS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return _empty_store()


def save_node_defaults(data: dict) -> dict:
    NODE_DEFAULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(NODE_DEFAULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data


def _read_workflow_node_values(workflow_id: str) -> dict[str, Any]:
    fmt, data = workflow_service.load_workflow_file(workflow_id)
    if fmt != "api":
        raise ValueError("节点目录仅支持 API 格式工作流")
    meta = wms.get_effective_meta(workflow_id)
    topo = meta.get("topology") or {}
    ckpt_nid = str(topo.get("checkpoint_node") or "1")
    out: dict[str, Any] = {
        "checkpoint": {"node_id": ckpt_nid, "ckpt_name": None},
        "lora_slots": [],
        "encode": {},
    }
    if ckpt_nid in data:
        out["checkpoint"]["ckpt_name"] = data[ckpt_nid].get("inputs", {}).get("ckpt_name")
    pos = topo.get("positive_encode") or {}
    neg = topo.get("negative_encode") or {}
    for side, spec in (("positive", pos), ("negative", neg)):
        nid = str(spec.get("node_id") or "")
        if nid in data:
            out["encode"][side] = {
                "node_id": nid,
                "text_preview": str(data[nid].get("inputs", {}).get("text", ""))[:200],
            }
    for slot in topo.get("lora_slots") or []:
        nid = str(slot.get("node_id") or "")
        if nid not in data:
            continue
        inp = data[nid].get("inputs", {})
        out["lora_slots"].append({
            "node_id": nid,
            "role": slot.get("role"),
            "title": slot.get("title"),
            "optional": bool(slot.get("optional")),
            "sweepable": bool(slot.get("sweepable")),
            "lora_name": inp.get("lora_name"),
            "strength_model": inp.get("strength_model"),
            "strength_clip": inp.get("strength_clip"),
        })
    return out


def get_workflow_catalog(workflow_id: str) -> dict[str, Any]:
    wid = workflow_id or "First_api"
    meta = wms.get_effective_meta(wid)
    live = _read_workflow_node_values(wid)
    store = load_node_defaults()
    saved = (store.get("workflows") or {}).get(wid) or {}

    ckpt_saved = saved.get("checkpoint") or {}
    checkpoint = {
        **live["checkpoint"],
        "ckpt_name": ckpt_saved.get("ckpt_name") or live["checkpoint"].get("ckpt_name"),
    }

    lora_slots = []
    saved_loras = {str(s.get("node_id")): s for s in saved.get("lora_slots") or []}
    for slot in live["lora_slots"]:
        nid = str(slot["node_id"])
        ov = saved_loras.get(nid) or {}
        lora_slots.append({
            **slot,
            "lora_name": ov.get("lora_name", slot.get("lora_name")),
            "strength_model": ov.get("strength_model", slot.get("strength_model")),
            "strength_clip": ov.get("strength_clip", slot.get("strength_clip")),
        })

    return {
        "workflow_id": wid,
        "display_name": meta.get("display_name") or wid,
        "topology": meta.get("topology") or {},
        "checkpoint": checkpoint,
        "lora_slots": lora_slots,
        "encode": live.get("encode") or {},
    }


def save_workflow_catalog(workflow_id: str, payload: dict) -> dict:
    wid = workflow_id or "First_api"
    store = load_node_defaults()
    workflows = store.setdefault("workflows", {})
    entry = {
        "checkpoint": payload.get("checkpoint") or {},
        "lora_slots": payload.get("lora_slots") or [],
    }
    workflows[wid] = entry
    save_node_defaults(store)
    return get_workflow_catalog(wid)


def list_all_catalogs() -> dict[str, Any]:
    """汇总所有 API 工作流的节点目录（无需前端先选工作流）。"""
    import workflow_service

    items: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for wf in workflow_service.list_workflows():
        wid = wf.get("id") or ""
        if wf.get("format") != "api":
            skipped.append({"workflow_id": wid, "reason": "非 API 格式"})
            continue
        try:
            cat = get_workflow_catalog(wid)
            items.append({
                **cat,
                "is_master": bool(wf.get("is_master")),
                "is_variant": bool(wf.get("is_variant")),
            })
        except (FileNotFoundError, ValueError) as e:
            skipped.append({"workflow_id": wid, "reason": str(e)})
    items.sort(key=lambda x: (not x.get("is_master"), x.get("is_variant"), x.get("workflow_id", "")))
    master = next((x["workflow_id"] for x in items if x.get("is_master")), None)
    if not master and items:
        master = items[0]["workflow_id"]
    return {
        "master_workflow_id": master,
        "workflows": items,
        "skipped": skipped,
    }


def save_all_catalogs(items: list[dict]) -> dict[str, Any]:
    for entry in items or []:
        wid = str(entry.get("workflow_id") or "").strip()
        if not wid:
            continue
        save_workflow_catalog(
            wid,
            {
                "checkpoint": entry.get("checkpoint"),
                "lora_slots": entry.get("lora_slots"),
            },
        )
    return list_all_catalogs()


def lora_defaults_for_apply(workflow_id: str, node_id: str, *, lora_name: str | None = None) -> dict[str, Any] | None:
    """优先按 LoRA 文件名读取节点管理中的默认权重。"""
    import model_node_catalog_service

    if lora_name:
        by_name = model_node_catalog_service.lora_defaults_by_name(lora_name)
        if by_name:
            return by_name
    cat = get_workflow_catalog(workflow_id)
    for slot in cat.get("lora_slots") or []:
        if str(slot.get("node_id")) == str(node_id):
            patch: dict[str, Any] = {}
            fname = lora_name or slot.get("lora_name")
            if fname:
                by_name = model_node_catalog_service.lora_defaults_by_name(str(fname))
                if by_name:
                    return by_name
            if slot.get("strength_model") is not None:
                patch["strength_model"] = float(slot["strength_model"])
            if slot.get("strength_clip") is not None:
                patch["strength_clip"] = float(slot["strength_clip"])
            return patch or None
    return None
