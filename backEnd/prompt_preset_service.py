"""提示词预设：固定正/负 + 随机组，供单张/批量导入。"""
from __future__ import annotations

import copy
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prompt_build_service import normalize_prompt_layers as normalize_batch_prompts
from config import PROJECT_ROOT

PRESETS_PATH = PROJECT_ROOT / "config" / "prompt_presets.json"


def _empty_store() -> dict:
    return {"schema_version": 1, "presets": []}


def load_presets_store() -> dict:
    if not PRESETS_PATH.is_file():
        return _empty_store()
    with open(PRESETS_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_presets_store(data: dict) -> dict:
    PRESETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PRESETS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data


def list_presets() -> list[dict]:
    store = load_presets_store()
    items = []
    for p in store.get("presets") or []:
        cfg = normalize_batch_prompts(p)
        items.append({
            "id": p.get("id"),
            "name": p.get("name", ""),
            "description": p.get("description", ""),
            "updated_at": p.get("updated_at"),
            "positive": cfg.get("positive", ""),
            "negative": cfg.get("negative", ""),
            "fixed": cfg["fixed"],
            "random_groups": cfg["random_groups"],
            "merge": cfg.get("merge"),
            "random_group_count": len(cfg["random_groups"]),
        })
    return items


def get_preset(preset_id: str) -> dict | None:
    for p in load_presets_store().get("presets") or []:
        if str(p.get("id")) == str(preset_id):
            return _public_preset(p)
    return None


def _public_preset(raw: dict) -> dict:
    cfg = normalize_batch_prompts(raw)
    return {
        "id": raw.get("id"),
        "name": raw.get("name", ""),
        "description": raw.get("description", ""),
        "updated_at": raw.get("updated_at"),
        "positive": cfg.get("positive", ""),
        "negative": cfg.get("negative", ""),
        "fixed": cfg["fixed"],
        "random_groups": cfg["random_groups"],
        "merge": cfg.get("merge"),
    }


def create_preset(name: str, body: dict) -> dict:
    store = load_presets_store()
    pid = str(uuid.uuid4())[:8]
    cfg = normalize_batch_prompts(body)
    entry = {
        "id": pid,
        "name": (name or "未命名预设").strip(),
        "description": str(body.get("description", "")).strip(),
        "positive": cfg.get("positive", ""),
        "negative": cfg.get("negative", ""),
        "fixed": cfg["fixed"],
        "random_groups": cfg["random_groups"],
        "merge": cfg.get("merge"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    store.setdefault("presets", []).append(entry)
    save_presets_store(store)
    return _public_preset(entry)


def update_preset(preset_id: str, body: dict) -> dict:
    store = load_presets_store()
    presets = store.get("presets") or []
    for i, p in enumerate(presets):
        if str(p.get("id")) != str(preset_id):
            continue
        fixed_in = body["fixed"] if "fixed" in body else p.get("fixed")
        groups_in = body["random_groups"] if "random_groups" in body else p.get("random_groups")
        merged_body = {**p, **body}
        if fixed_in is not None:
            merged_body["fixed"] = fixed_in
        if groups_in is not None:
            merged_body["random_groups"] = groups_in
        cfg = normalize_batch_prompts(merged_body)
        updated = {
            **p,
            "name": body["name"] if "name" in body else p.get("name"),
            "description": body.get("description", p.get("description", "")),
            "positive": cfg.get("positive", ""),
            "negative": cfg.get("negative", ""),
            "fixed": cfg["fixed"],
            "random_groups": cfg["random_groups"],
            "merge": cfg.get("merge"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        presets[i] = updated
        save_presets_store(store)
        return _public_preset(updated)
    raise ValueError(f"预设不存在: {preset_id}")


def delete_preset(preset_id: str) -> bool:
    store = load_presets_store()
    presets = store.get("presets") or []
    new_list = [p for p in presets if str(p.get("id")) != str(preset_id)]
    if len(new_list) == len(presets):
        raise ValueError(f"预设不存在: {preset_id}")
    store["presets"] = new_list
    save_presets_store(store)
    return True
