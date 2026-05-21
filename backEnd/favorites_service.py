"""收藏：仅 JSON 记录参数快照 + 原图路径引用（不复制图片）。"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import COMFYUI_ROOT
from job_service import build_view_url, resolve_image_path

import workflow_service

FAVORITES_DIR = COMFYUI_ROOT / "user" / "default" / "favorites"
FAVORITES_INDEX = FAVORITES_DIR / "favorites.json"


def _ensure_dirs() -> None:
    FAVORITES_DIR.mkdir(parents=True, exist_ok=True)


def _load_index() -> list[dict]:
    _ensure_dirs()
    if not FAVORITES_INDEX.is_file():
        return []
    try:
        with open(FAVORITES_INDEX, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _save_index(items: list[dict]) -> None:
    _ensure_dirs()
    with open(FAVORITES_INDEX, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def _favorite_key(entry: dict) -> str:
    img = entry.get("image") or {}
    return "|".join([
        str(entry.get("workflow_id", "")),
        str(img.get("subfolder", "")),
        str(img.get("filename", "")),
        str(entry.get("prompt_id", "")),
        str(entry.get("batch_id", "")),
        str(entry.get("grid_ia", "")),
        str(entry.get("grid_ib", "")),
    ])


def _image_exists(filename: str, subfolder: str, folder_type: str) -> bool:
    try:
        return Path(resolve_image_path(filename, subfolder, folder_type)).is_file()
    except (OSError, ValueError):
        return False


def _extract_params_snapshot(workflow_id: str, overrides: dict | None, body: dict) -> dict:
    """保存完整 overrides，便于恢复工作流并改提示词再生成。"""
    overrides = overrides or {}
    snapshot: dict[str, Any] = {
        "checkpoint": None,
        "loras": [],
        "seed": body.get("seed"),
        "sampler": {},
        "prompt_nodes": {},
        "overrides": overrides,
    }

    if body.get("loras_snapshot"):
        snapshot["loras"] = body["loras_snapshot"]
    elif workflow_id:
        try:
            prompt = workflow_service.build_api_prompt(workflow_id, overrides)
            for meta in workflow_service.discover_lora_nodes(prompt):
                nid = meta["node_id"]
                patch = overrides.get(nid, {})
                snapshot["loras"].append({
                    "node_id": nid,
                    "lora_name": meta.get("lora_name"),
                    "short_name": meta.get("short_name"),
                    "strength_model": patch.get("strength_model", meta.get("strength_model")),
                    "strength_clip": patch.get("strength_clip", meta.get("strength_clip")),
                })
            for node_id, node in prompt.items():
                ct = node.get("class_type", "")
                inp = node.get("inputs", {})
                patch = overrides.get(str(node_id), {})
                if ct == "CheckpointLoaderSimple":
                    snapshot["checkpoint"] = patch.get("ckpt_name") or inp.get("ckpt_name")
                elif ct == "KSampler":
                    snapshot["sampler"] = {
                        k: patch.get(k, inp.get(k))
                        for k in ("seed", "steps", "cfg", "sampler_name", "scheduler", "denoise")
                        if k in inp or k in patch
                    }
                    if snapshot["seed"] is None:
                        snapshot["seed"] = snapshot["sampler"].get("seed")
                elif ct == "CLIPTextEncode" and "text" in inp:
                    text = str(patch.get("text", inp.get("text", "")))
                    snapshot["prompt_nodes"][str(node_id)] = text
        except (FileNotFoundError, ValueError):
            pass

    if not snapshot["checkpoint"]:
        for _nid, patch in overrides.items():
            if "ckpt_name" in patch:
                snapshot["checkpoint"] = patch["ckpt_name"]
                break

    if not snapshot["prompt_nodes"] and overrides:
        try:
            from prompt_defaults_service import load_defaults
            from prompt_merge_service import resolve_encode_nodes

            encode = resolve_encode_nodes(load_defaults())
            for nid in encode.values():
                patch = overrides.get(str(nid), {})
                if patch.get("text"):
                    snapshot["prompt_nodes"][str(nid)] = str(patch["text"])
        except (ImportError, OSError, ValueError, TypeError):
            pass
        for nid in ("3", "4"):
            patch = overrides.get(str(nid), {})
            if patch.get("text") and str(nid) not in snapshot["prompt_nodes"]:
                snapshot["prompt_nodes"][str(nid)] = str(patch["text"])

    if not snapshot["sampler"] and overrides:
        for nid in ("5", "14"):
            patch = overrides.get(str(nid), {})
            if not patch:
                continue
            for k in ("seed", "steps", "cfg", "sampler_name", "scheduler", "denoise"):
                if patch.get(k) is not None and k not in snapshot["sampler"]:
                    snapshot["sampler"][k] = patch[k]
        if snapshot["seed"] is None and snapshot["sampler"].get("seed") is not None:
            snapshot["seed"] = snapshot["sampler"]["seed"]

    return snapshot


def _entry_to_public(entry: dict) -> dict:
    out = dict(entry)
    out.pop("asset_path", None)
    img = entry.get("image") or {}
    filename = img.get("filename", "")
    subfolder = img.get("subfolder", "")
    folder_type = img.get("type", "output")
    exists = _image_exists(filename, subfolder, folder_type) if filename else False
    out["image_exists"] = exists
    out["image"] = {
        **img,
        "url": build_view_url(filename, subfolder, folder_type) if exists else None,
    }
    return out


def list_favorites() -> list[dict]:
    items = sorted(_load_index(), key=lambda x: x.get("created_at", ""), reverse=True)
    return [_entry_to_public(x) for x in items]


def get_favorite(favorite_id: str) -> dict | None:
    for item in _load_index():
        if item.get("id") == favorite_id:
            return _entry_to_public(item)
    return None


def find_by_image_key(body: dict) -> dict | None:
    key = _favorite_key({
        "workflow_id": body.get("workflow_id"),
        "image": body.get("image"),
        "prompt_id": body.get("prompt_id"),
        "batch_id": body.get("batch_id"),
        "grid_ia": body.get("grid_ia"),
        "grid_ib": body.get("grid_ib"),
    })
    for item in _load_index():
        if _favorite_key(item) == key:
            return item
    return None


def add_favorite(body: dict) -> dict:
    existing = find_by_image_key(body)
    if existing:
        return _entry_to_public(existing)

    _ensure_dirs()
    favorite_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    image = body.get("image") or {}
    filename = image.get("filename")
    if not filename:
        raise ValueError("缺少图片 filename")

    subfolder = image.get("subfolder", "")
    folder_type = image.get("type", "output")

    params = _extract_params_snapshot(
        body.get("workflow_id", ""),
        body.get("overrides"),
        body,
    )

    entry = {
        "id": favorite_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "workflow_id": body.get("workflow_id"),
        "source": body.get("source", "single"),
        "prompt_id": body.get("prompt_id"),
        "batch_id": body.get("batch_id"),
        "grid_ia": body.get("grid_ia"),
        "grid_ib": body.get("grid_ib"),
        "label": body.get("label"),
        "image": {
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type,
        },
        "params": params,
    }

    items = _load_index()
    items.append(entry)
    _save_index(items)
    return _entry_to_public(entry)


def remove_favorite(favorite_id: str) -> dict:
    items = _load_index()
    found = None
    kept = []
    for item in items:
        if item.get("id") == favorite_id:
            found = item
        else:
            kept.append(item)
    if not found:
        raise FileNotFoundError("收藏不存在")

    _save_index(kept)
    return {"ok": True, "id": favorite_id}


def toggle_favorite(body: dict) -> dict:
    existing = find_by_image_key(body)
    if existing:
        remove_favorite(existing["id"])
        return {"ok": True, "favorited": False, "id": existing["id"]}
    entry = add_favorite(body)
    return {"ok": True, "favorited": True, "id": entry["id"], "entry": entry}
