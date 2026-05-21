"""统一全局提示词配置：正/负全文、随机组、开关与合并顺序。"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from config import PROJECT_ROOT
from prompt_defaults_service import load_defaults as load_legacy_defaults
from global_reference_service import load_global_reference_groups, normalize_groups

GLOBAL_PROMPT_CONFIG_PATH = PROJECT_ROOT / "config" / "global_prompt_config.json"
LEGACY_DEFAULTS_PATH = PROJECT_ROOT / "config" / "prompt_defaults.json"
LEGACY_REF_PATH = PROJECT_ROOT / "config" / "global_reference_groups.json"


def _empty_config() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "enabled": True,
        "positive": "",
        "negative": "",
        "random_groups": [],
        "merge": {
            "global_before_workflow": False,
            "random_before_workflow": False,
        },
    }


def _legacy_positive_text(side_spec: dict) -> str:
    prefix = str(side_spec.get("prefix", "")).strip()
    suffix = str(side_spec.get("suffix", "")).strip()
    parts = [p for p in (prefix, suffix) if p]
    return "\n".join(parts)


def _migrate_from_legacy() -> dict[str, Any]:
    cfg = _empty_config()
    if LEGACY_DEFAULTS_PATH.is_file():
        leg = load_legacy_defaults()
        cfg["positive"] = _legacy_positive_text(leg.get("positive") or {})
        cfg["negative"] = _legacy_positive_text(leg.get("negative") or {})
        if str(leg.get("merge_mode", "")).lower() == "replace":
            cfg["merge"]["global_before_workflow"] = True
    if LEGACY_REF_PATH.is_file():
        store = load_global_reference_groups()
        cfg["random_groups"] = normalize_groups(store.get("groups"))
    return cfg


def normalize_global_config(raw: dict | None) -> dict[str, Any]:
    cfg = _empty_config()
    if not raw:
        return cfg
    cfg["enabled"] = bool(raw.get("enabled", True))
    cfg["positive"] = str(raw.get("positive", ""))
    cfg["negative"] = str(raw.get("negative", ""))
    merge = raw.get("merge") or {}
    cfg["merge"] = {
        "global_before_workflow": bool(merge.get("global_before_workflow", False)),
        "random_before_workflow": bool(merge.get("random_before_workflow", False)),
    }
    groups = []
    for g in raw.get("random_groups") or []:
        prompts = [str(p).strip() for p in (g.get("prompts") or []) if str(p).strip()]
        if not prompts:
            continue
        gid = str(g.get("id") or "")
        if gid and not gid.startswith("global-"):
            gid = f"global-{gid}"
        groups.append({
            "id": gid or f"global-{len(groups)}",
            "name": str(g.get("name") or "参考组"),
            "enabled": bool(g.get("enabled", True)),
            "target": g.get("target") if g.get("target") in ("positive", "negative") else "positive",
            "prompts": prompts,
        })
    cfg["random_groups"] = groups
    return cfg


def load_global_prompt_config(*, force_migrate: bool = False) -> dict[str, Any]:
    if GLOBAL_PROMPT_CONFIG_PATH.is_file() and not force_migrate:
        try:
            with open(GLOBAL_PROMPT_CONFIG_PATH, encoding="utf-8") as f:
                return normalize_global_config(json.load(f))
        except (OSError, json.JSONDecodeError):
            pass
    cfg = _migrate_from_legacy()
    save_global_prompt_config(cfg)
    return cfg


def save_global_prompt_config(data: dict) -> dict:
    cfg = normalize_global_config(data)
    GLOBAL_PROMPT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GLOBAL_PROMPT_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    return cfg


def global_as_runtime_layers(cfg: dict | None = None) -> dict[str, Any]:
    """将全局层转为 prompt_build 使用的 runtime 形结构（含 random_groups）。"""
    g = normalize_global_config(cfg or load_global_prompt_config())
    return {
        "enabled": g["enabled"],
        "positive": g["positive"],
        "negative": g["negative"],
        "fixed": {"positive": {"prefix": "", "suffix": ""}, "negative": {"prefix": "", "suffix": ""}},
        "random_groups": copy.deepcopy(g["random_groups"]),
        "merge": copy.deepcopy(g["merge"]),
        "source": "global",
    }
