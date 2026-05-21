"""全局随机参考词组：每次生成时从各启用的组中各抽一条。"""
from __future__ import annotations

import copy
import json
import uuid
from pathlib import Path
from typing import Any

from config import PROJECT_ROOT

GLOBAL_REFERENCE_PATH = PROJECT_ROOT / "config" / "global_reference_groups.json"


def _empty_store() -> dict:
    return {"schema_version": 1, "groups": []}


def load_global_reference_groups() -> dict:
    if not GLOBAL_REFERENCE_PATH.is_file():
        return _empty_store()
    with open(GLOBAL_REFERENCE_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_global_reference_groups(data: dict) -> dict:
    GLOBAL_REFERENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GLOBAL_REFERENCE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data


def normalize_groups(raw: list | None) -> list[dict]:
    groups = []
    for g in raw or []:
        prompts = [str(p).strip() for p in (g.get("prompts") or []) if str(p).strip()]
        if not prompts:
            continue
        gid = str(g.get("id") or uuid.uuid4().hex[:8])
        if not gid.startswith("global-"):
            gid = f"global-{gid}"
        groups.append({
            "id": gid,
            "name": str(g.get("name") or "参考组"),
            "enabled": bool(g.get("enabled", True)),
            "target": g.get("target") if g.get("target") in ("positive", "negative") else "positive",
            "prompts": prompts,
        })
    return groups


def list_enabled_groups() -> list[dict]:
    store = load_global_reference_groups()
    return [g for g in normalize_groups(store.get("groups")) if g.get("enabled", True)]


def merge_with_global_batch_prompts(batch_prompts: dict | None) -> dict | None:
    """将全局参考组并入 batch_prompts.random_groups（不覆盖同名 id）。"""
    global_groups = list_enabled_groups()
    if not global_groups:
        return batch_prompts

    from batch_prompt_service import normalize_batch_prompts

    cfg = normalize_batch_prompts(batch_prompts)
    existing_ids = {g.get("id") for g in cfg.get("random_groups") or []}
    merged_groups = []
    for g in global_groups:
        if g["id"] not in existing_ids:
            merged_groups.append(copy.deepcopy(g))
    merged_groups.extend(cfg.get("random_groups") or [])
    cfg["random_groups"] = merged_groups
    return cfg
