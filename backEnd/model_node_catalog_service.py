"""节点管理：从本地 ComfyUI 模型目录列出 Checkpoint / LoRA，并保存按文件名的默认参数。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import comfy_client
from config import PROJECT_ROOT

MODEL_NODE_DEFAULTS_PATH = PROJECT_ROOT / "config" / "model_node_defaults.json"
LEGACY_WORKFLOW_DEFAULTS_PATH = PROJECT_ROOT / "config" / "workflow_node_defaults.json"


def _empty_store() -> dict:
    return {
        "schema_version": 2,
        "default_checkpoint": "",
        "loras": {},
    }


def load_store() -> dict:
    if not MODEL_NODE_DEFAULTS_PATH.is_file():
        store = _empty_store()
        _migrate_legacy_workflow_defaults(store)
        return store
    try:
        with open(MODEL_NODE_DEFAULTS_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        data = _empty_store()
    if data.get("schema_version") != 2:
        data = _empty_store()
        _migrate_legacy_workflow_defaults(data)
    loras = data.get("loras")
    if not isinstance(loras, dict):
        data["loras"] = {}
    data.setdefault("default_checkpoint", "")
    return data


def save_store(data: dict) -> dict:
    MODEL_NODE_DEFAULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "schema_version": 2,
        "default_checkpoint": str(data.get("default_checkpoint") or ""),
        "loras": data.get("loras") or {},
    }
    with open(MODEL_NODE_DEFAULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    return out


def _migrate_legacy_workflow_defaults(store: dict) -> None:
    """从旧版按工作流槽位配置迁移为按 LoRA 文件名。"""
    if not LEGACY_WORKFLOW_DEFAULTS_PATH.is_file():
        return
    try:
        with open(LEGACY_WORKFLOW_DEFAULTS_PATH, encoding="utf-8") as f:
            legacy = json.load(f)
    except (OSError, json.JSONDecodeError):
        return
    loras = store.setdefault("loras", {})
    for wf_entry in (legacy.get("workflows") or {}).values():
        ckpt = (wf_entry.get("checkpoint") or {}).get("ckpt_name")
        if ckpt and not store.get("default_checkpoint"):
            store["default_checkpoint"] = str(ckpt)
        for slot in wf_entry.get("lora_slots") or []:
            name = str(slot.get("lora_name") or "").strip()
            if not name:
                continue
            entry: dict[str, Any] = loras.get(name) or {}
            if slot.get("strength_model") is not None:
                entry["strength_model"] = float(slot["strength_model"])
            if slot.get("strength_clip") is not None:
                entry["strength_clip"] = float(slot["strength_clip"])
            loras[name] = entry


def _list_local_models(folder: str) -> list[str]:
    try:
        files = comfy_client.list_models(folder)
        return sorted(str(x) for x in files if x)
    except (ValueError, RuntimeError):
        return []


def list_model_catalog() -> dict[str, Any]:
    store = load_store()
    default_ckpt = str(store.get("default_checkpoint") or "")
    lora_saved: dict = store.get("loras") or {}

    checkpoints = []
    for name in _list_local_models("checkpoints"):
        checkpoints.append({
            "name": name,
            "folder": "checkpoints",
            "is_default": name == default_ckpt,
        })

    loras = []
    for name in _list_local_models("loras"):
        saved = lora_saved.get(name) or {}
        loras.append({
            "name": name,
            "folder": "loras",
            "strength_model": saved.get("strength_model"),
            "strength_clip": saved.get("strength_clip"),
        })

    return {
        "default_checkpoint": default_ckpt,
        "checkpoints": checkpoints,
        "loras": loras,
        "counts": {
            "checkpoints": len(checkpoints),
            "loras": len(loras),
        },
    }


def save_model_catalog(payload: dict) -> dict:
    store = load_store()
    if "default_checkpoint" in payload:
        store["default_checkpoint"] = str(payload.get("default_checkpoint") or "")
    loras_in = payload.get("loras")
    if loras_in is not None:
        merged = dict(store.get("loras") or {})
        for item in loras_in:
            if isinstance(item, dict):
                name = str(item.get("name") or "").strip()
                if not name:
                    continue
                entry: dict[str, Any] = {}
                if item.get("strength_model") is not None:
                    entry["strength_model"] = float(item["strength_model"])
                if item.get("strength_clip") is not None:
                    entry["strength_clip"] = float(item["strength_clip"])
                if entry:
                    merged[name] = entry
                elif name in merged:
                    del merged[name]
            elif isinstance(item, str) and item.strip():
                merged.pop(item.strip(), None)
        store["loras"] = merged
    save_store(store)
    return list_model_catalog()


def lora_defaults_by_name(lora_name: str) -> dict[str, Any] | None:
    name = str(lora_name or "").strip()
    if not name:
        return None
    store = load_store()
    entry = (store.get("loras") or {}).get(name)
    if not entry:
        return None
    patch: dict[str, Any] = {}
    if entry.get("strength_model") is not None:
        patch["strength_model"] = float(entry["strength_model"])
    if entry.get("strength_clip") is not None:
        patch["strength_clip"] = float(entry["strength_clip"])
    return patch or None


def default_checkpoint_name() -> str | None:
    name = str(load_store().get("default_checkpoint") or "").strip()
    return name or None
