"""默认正/负提示词：与 CLIPTextEncode 合并（append 到工作流原文本后）。"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from config import PROJECT_ROOT, WORKFLOW_TEMPLATE_ID

DEFAULTS_PATH = PROJECT_ROOT / "config" / "prompt_defaults.json"


def load_defaults() -> dict:
    if not DEFAULTS_PATH.is_file():
        return _empty_defaults()
    with open(DEFAULTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_defaults(data: dict) -> None:
    DEFAULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DEFAULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _empty_defaults() -> dict:
    return {
        "schema_version": 1,
        "template_id": WORKFLOW_TEMPLATE_ID,
        "positive": {"node_id": "3", "field": "text", "prefix": "", "suffix": ""},
        "negative": {"node_id": "4", "field": "text", "prefix": "", "suffix": ""},
        "merge_mode": "append",
    }


from prompt_merge_service import merge_text_append


def _merge_text(base: str, prefix: str, suffix: str, mode: str) -> str:
    if mode == "replace":
        parts = []
        if prefix.strip():
            parts.append(prefix.strip())
        if suffix.strip():
            parts.append(suffix.strip())
        return "\n".join(parts) if parts else base
    return merge_text_append(base, prefix, suffix)


def apply_prompt_defaults(prompt: dict, defaults: dict | None = None) -> dict:
    cfg = defaults or load_defaults()
    result = copy.deepcopy(prompt)
    mode = cfg.get("merge_mode", "append")
    for side in ("positive", "negative"):
        spec = cfg.get(side) or {}
        nid = str(spec.get("node_id", ""))
        field = spec.get("field", "text")
        if not nid or nid not in result:
            continue
        inputs = result[nid].setdefault("inputs", {})
        if field not in inputs or isinstance(inputs[field], list):
            continue
        inputs[field] = _merge_text(
            str(inputs.get(field, "")),
            str(spec.get("prefix", "")),
            str(spec.get("suffix", "")),
            mode,
        )
    return result


def preview_merged_prompts(prompt: dict, defaults: dict | None = None) -> dict[str, str]:
    merged = apply_prompt_defaults(prompt, defaults)
    cfg = defaults or load_defaults()
    out: dict[str, str] = {}
    for side in ("positive", "negative"):
        spec = cfg.get(side) or {}
        nid = str(spec.get("node_id", ""))
        field = spec.get("field", "text")
        if nid in merged:
            val = merged[nid].get("inputs", {}).get(field, "")
            if not isinstance(val, list):
                out[side] = str(val)
    return out
