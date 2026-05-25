"""节点管理：从本地 ComfyUI 模型目录列出 Checkpoint / LoRA，并保存按文件名的默认参数。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import comfy_client
import model_paths_service
from config import PROJECT_ROOT

MODEL_NODE_DEFAULTS_PATH = PROJECT_ROOT / "config" / "model_node_defaults.json"
LEGACY_WORKFLOW_DEFAULTS_PATH = PROJECT_ROOT / "config" / "workflow_node_defaults.json"


SCHEMA_VERSION = 3


def _empty_store() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "default_checkpoint": "",
        "loras": {},
        "checkpoint_lora_compat": {},
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
    if data.get("schema_version") not in (2, SCHEMA_VERSION):
        data = _empty_store()
        _migrate_legacy_workflow_defaults(data)
    if data.get("schema_version") == 2:
        data["schema_version"] = SCHEMA_VERSION
        data.setdefault("checkpoint_lora_compat", {})
    loras = data.get("loras")
    if not isinstance(loras, dict):
        data["loras"] = {}
    compat = data.get("checkpoint_lora_compat")
    if not isinstance(compat, dict):
        data["checkpoint_lora_compat"] = {}
    data.setdefault("default_checkpoint", "")
    return data


def save_store(data: dict) -> dict:
    MODEL_NODE_DEFAULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "schema_version": SCHEMA_VERSION,
        "default_checkpoint": str(data.get("default_checkpoint") or ""),
        "loras": data.get("loras") or {},
        "checkpoint_lora_compat": data.get("checkpoint_lora_compat") or {},
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
    scanned = model_paths_service.list_model_filenames(folder)
    if scanned:
        return scanned
    try:
        files = comfy_client.list_models(folder)
        return sorted(str(x) for x in files if x)
    except (ValueError, RuntimeError):
        return []


def _normalize_lora_name_list(raw: list | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in raw or []:
        name = str(item or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out


def _compat_entry(raw: dict | None) -> dict[str, list[str]]:
    if not isinstance(raw, dict):
        return {"recommended": [], "not_recommended": []}
    rec = _normalize_lora_name_list(raw.get("recommended"))
    avoid = _normalize_lora_name_list(raw.get("not_recommended"))
    rec_set = set(rec)
    avoid = [n for n in avoid if n not in rec_set]
    return {"recommended": rec, "not_recommended": avoid}


def get_checkpoint_lora_compat(checkpoint_name: str) -> dict[str, Any]:
    """某 Checkpoint 的推荐 / 不推荐 LoRA 列表。"""
    ckpt = str(checkpoint_name or "").strip()
    if not ckpt:
        return {"checkpoint": "", "recommended": [], "not_recommended": [], "map": {}}
    store = load_store()
    compat_all = store.get("checkpoint_lora_compat") or {}
    entry = _compat_entry(compat_all.get(ckpt))
    lora_names = _list_local_models("loras")
    status_map: dict[str, str] = {}
    rec_set = set(entry["recommended"])
    avoid_set = set(entry["not_recommended"])
    for name in lora_names:
        if name in rec_set:
            status_map[name] = "recommended"
        elif name in avoid_set:
            status_map[name] = "not_recommended"
        else:
            status_map[name] = "neutral"
    return {
        "checkpoint": ckpt,
        "recommended": entry["recommended"],
        "not_recommended": entry["not_recommended"],
        "map": status_map,
    }


def save_checkpoint_lora_compat(
    checkpoint_name: str,
    *,
    recommended: list | None = None,
    not_recommended: list | None = None,
) -> dict[str, Any]:
    ckpt = str(checkpoint_name or "").strip()
    if not ckpt:
        raise ValueError("缺少 Checkpoint 名称")
    store = load_store()
    compat_all = dict(store.get("checkpoint_lora_compat") or {})
    entry = _compat_entry(compat_all.get(ckpt))
    if recommended is not None:
        entry["recommended"] = _normalize_lora_name_list(recommended)
    if not_recommended is not None:
        entry["not_recommended"] = _normalize_lora_name_list(not_recommended)
    rec_set = set(entry["recommended"])
    entry["not_recommended"] = [n for n in entry["not_recommended"] if n not in rec_set]
    compat_all[ckpt] = entry
    store["checkpoint_lora_compat"] = compat_all
    save_store(store)
    return get_checkpoint_lora_compat(ckpt)


def list_model_catalog() -> dict[str, Any]:
    store = load_store()
    default_ckpt = str(store.get("default_checkpoint") or "")
    lora_saved: dict = store.get("loras") or {}

    compat_all = store.get("checkpoint_lora_compat") or {}
    checkpoints = []
    for name in _list_local_models("checkpoints"):
        entry = _compat_entry(compat_all.get(name))
        checkpoints.append({
            "name": name,
            "folder": "checkpoints",
            "is_default": name == default_ckpt,
            "recommended_loras": entry["recommended"],
            "not_recommended_loras": entry["not_recommended"],
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


def remove_model_defaults(model_name: str, *, folder: str | None = None) -> None:
    """删除模型后清理 config 中保存的 LoRA 默认权重 / 默认 Checkpoint。"""
    name = str(model_name or "").strip()
    if not name:
        return
    store = load_store()
    changed = False
    if folder == "checkpoints" or folder is None:
        if store.get("default_checkpoint") == name:
            store["default_checkpoint"] = ""
            changed = True
        compat_all = store.get("checkpoint_lora_compat") or {}
        if name in compat_all:
            del compat_all[name]
            store["checkpoint_lora_compat"] = compat_all
            changed = True
    if folder == "loras" or folder is None:
        loras = store.get("loras") or {}
        if name in loras:
            del loras[name]
            store["loras"] = loras
            changed = True
        compat_all = dict(store.get("checkpoint_lora_compat") or {})
        compat_changed = False
        for ckpt, entry in list(compat_all.items()):
            if not isinstance(entry, dict):
                continue
            rec = [x for x in (entry.get("recommended") or []) if x != name]
            avoid = [x for x in (entry.get("not_recommended") or []) if x != name]
            if rec != entry.get("recommended") or avoid != entry.get("not_recommended"):
                compat_all[ckpt] = {"recommended": rec, "not_recommended": avoid}
                compat_changed = True
        if compat_changed:
            store["checkpoint_lora_compat"] = compat_all
            changed = True
    if changed:
        save_store(store)


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
