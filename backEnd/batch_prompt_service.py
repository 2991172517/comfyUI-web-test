"""批量提示词：固定追加 + 随机组（每组随机抽一条）。"""
from __future__ import annotations

import copy
import json
import uuid
from pathlib import Path
from typing import Any

from config import PROJECT_ROOT
from prompt_defaults_service import load_defaults
from prompt_merge_service import merge_text_append, patch_prompt_encode_text, resolve_encode_nodes
from reference_pick_service import pick_random_groups

BATCH_PROMPT_CONFIG_PATH = PROJECT_ROOT / "config" / "batch_prompt_config.json"


def _empty_config() -> dict:
    return {
        "schema_version": 1,
        "fixed": {
            "positive": {"prefix": "", "suffix": ""},
            "negative": {"prefix": "", "suffix": ""},
        },
        "random_groups": [],
    }


def load_batch_prompt_config() -> dict:
    if not BATCH_PROMPT_CONFIG_PATH.is_file():
        return _empty_config()
    with open(BATCH_PROMPT_CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_batch_prompt_config(data: dict) -> dict:
    BATCH_PROMPT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BATCH_PROMPT_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data


def normalize_batch_prompts(raw: dict | None) -> dict:
    cfg = _empty_config()
    if not raw:
        return cfg
    fixed = raw.get("fixed") or {}
    for side in ("positive", "negative"):
        side_in = fixed.get(side) or {}
        cfg["fixed"][side] = {
            "prefix": str(side_in.get("prefix", "")),
            "suffix": str(side_in.get("suffix", "")),
        }
    groups = []
    for g in raw.get("random_groups") or []:
        prompts = [str(p).strip() for p in (g.get("prompts") or []) if str(p).strip()]
        if not prompts:
            continue
        groups.append({
            "id": str(g.get("id") or uuid.uuid4().hex[:8]),
            "name": str(g.get("name") or "未命名组"),
            "enabled": bool(g.get("enabled", True)),
            "target": g.get("target") if g.get("target") in ("positive", "negative") else "positive",
            "prompts": prompts,
        })
    cfg["random_groups"] = groups
    return cfg


def apply_batch_prompt_layers(
    prompt: dict,
    batch_prompts: dict | None,
    *,
    picks: dict[str, list[str]] | None = None,
    pick_records: list[dict] | None = None,
    random_first: bool = False,
) -> tuple[dict, list[dict]]:
    """在已有 prompt（含全局默认）上追加批量固定与随机片段。"""
    if not batch_prompts:
        return prompt, pick_records or []

    cfg = normalize_batch_prompts(batch_prompts)
    encode = resolve_encode_nodes(load_defaults())
    result = copy.deepcopy(prompt)

    if picks is None:
        frags, pick_records = pick_random_groups(cfg.get("random_groups") or [])
    else:
        frags = picks
        pick_records = pick_records or []

    for side, nid in encode.items():
        if nid not in result:
            continue
        inputs = result[nid].get("inputs", {})
        if "text" not in inputs or isinstance(inputs.get("text"), list):
            continue
        fixed = (cfg.get("fixed") or {}).get(side) or {}
        merged = merge_text_append(
            str(inputs.get("text", "")),
            str(fixed.get("prefix", "")),
            str(fixed.get("suffix", "")),
            frags.get(side) or [],
            extras_before_base=random_first,
        )
        patch_prompt_encode_text(result, encode, side, merged)

    return result, pick_records or []


def build_text_overrides_for_item(
    workflow_id: str,
    base_overrides: dict,
    batch_prompts: dict | None,
    *,
    seed: int | None = None,
    index: int = 0,
    style_enabled: bool | None = None,
    random_first: bool = False,
    frozen_random_frags: dict[str, list[str]] | None = None,
    frozen_pick_records: list[dict] | None = None,
    log_source: str = "",
) -> tuple[dict[str, dict[str, Any]], list[dict]]:
    """生成本条批量项对 CLIPTextEncode 的 text 覆盖（统一 prompt_build_service）。"""
    from prompt_build_service import build_text_overrides_for_queue

    runtime = None
    if batch_prompts:
        runtime = normalize_batch_prompts(batch_prompts)
        if isinstance(batch_prompts, dict):
            for k in ("positive", "negative", "enabled", "merge"):
                if k in batch_prompts:
                    runtime[k] = batch_prompts[k]

    merged, records = build_text_overrides_for_queue(
        workflow_id,
        base_overrides,
        runtime,
        style_enabled=style_enabled,
        seed=seed,
        index=index,
        random_first_override=random_first,
        frozen_random_frags=frozen_random_frags,
        frozen_pick_records=frozen_pick_records,
        log_source=log_source,
    )
    encode = resolve_encode_nodes(load_defaults())
    overrides: dict[str, dict[str, Any]] = {}
    for side, nid in encode.items():
        text = (merged.get(nid) or {}).get("text")
        if text is not None and not isinstance(text, list):
            overrides[nid] = {"text": str(text)}
    return overrides, records
