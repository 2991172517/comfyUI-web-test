"""统一提示词合并：全局 / 当次(预设) / 工作流节点 → CLIP #3 #4。"""
from __future__ import annotations

import copy
import logging
from typing import Any

log = logging.getLogger("custom_project.prompt_build")

from batch_prompt_service import normalize_batch_prompts
from global_prompt_config_service import global_as_runtime_layers, load_global_prompt_config
from prompt_defaults_service import load_defaults
from prompt_merge_service import merge_text_append, patch_prompt_encode_text, resolve_encode_nodes
from reference_pick_service import (
    join_prompt_tokens,
    merge_deduped_core_with_random,
    pick_random_bundle_groups,
    pick_random_groups,
)


def normalize_prompt_layers(raw: dict | None) -> dict[str, Any]:
    """当次层（预设 / 抽卡 session / 批量），兼容旧 fixed-only 结构。"""
    base = normalize_batch_prompts(raw)
    if not raw:
        return {
            **base,
            "enabled": True,
            "positive": "",
            "negative": "",
            "merge": {"global_before_workflow": False, "random_before_workflow": False},
        }
    merge = raw.get("merge") or {}
    return {
        **base,
        "enabled": bool(raw.get("enabled", True)),
        "positive": str(raw.get("positive", "")),
        "negative": str(raw.get("negative", "")),
        "merge": {
            "global_before_workflow": bool(merge.get("global_before_workflow", False)),
            "random_before_workflow": bool(merge.get("random_before_workflow", False)),
        },
    }


def _layer_enabled(layer: dict | None) -> bool:
    return bool(layer and layer.get("enabled", True))


def _merge_flags(global_layer: dict, runtime_layer: dict | None, *, random_first_override: bool | None) -> dict:
    g_merge = (global_layer or {}).get("merge") or {}
    r_merge = (runtime_layer or {}).get("merge") or {}
    random_before = bool(r_merge.get("random_before_workflow", g_merge.get("random_before_workflow", False)))
    if random_first_override is not None:
        random_before = bool(random_first_override)
    return {
        "global_before_workflow": bool(
            r_merge.get("global_before_workflow", g_merge.get("global_before_workflow", False))
        ),
        "random_before_workflow": random_before,
    }


def _runtime_fixed_parts(layer: dict, side: str) -> tuple[str, str]:
    fixed = (layer.get("fixed") or {}).get(side) or {}
    return str(fixed.get("prefix", "")).strip(), str(fixed.get("suffix", "")).strip()


def _encode_text_in_overrides(overrides: dict | None, encode: dict[str, str], side: str) -> bool:
    """工作流 overrides 已写入 CLIP 全文时，不再叠当次 positive/negative 或 fixed。"""
    nid = encode.get(side)
    if not nid:
        return False
    return bool(str((overrides or {}).get(str(nid), {}).get("text", "")).strip())


def _enabled_random_groups(layer: dict | None) -> list[dict]:
    """随机组：不依赖全局「启用」总开关（总开关只控制正/负全文块）。"""
    if not layer:
        return []
    return [g for g in (layer.get("random_groups") or []) if g.get("enabled", True)]


def _enabled_random_bundle_groups(layer: dict | None) -> list[dict]:
    if not layer:
        return []
    return [g for g in (layer.get("random_bundle_groups") or []) if g.get("enabled", True)]


def _pick_random_lines(groups: list[dict], *, seed: int | None, index: int) -> dict[str, list[str]]:
    frags, _ = pick_random_groups(groups, seed=seed, index=index)
    out: dict[str, list[str]] = {"positive": [], "negative": []}
    for side in ("positive", "negative"):
        for line in frags.get(side) or []:
            s = str(line).strip()
            if s:
                out[side].append(s)
    return out


def merge_side_text(
    *,
    workflow_text: str,
    global_text: str,
    runtime_full: str,
    runtime_prefix: str,
    runtime_suffix: str,
    random_lines: list[str],
    global_enabled: bool,
    global_before_workflow: bool,
    random_before_workflow: bool,
) -> str:
    """
    合并单侧 CLIP 文本。

    顺序（由 merge 标志控制）：
    - global_before_workflow: 全局全文块在 workflow 前或后
    - random_before_workflow: 随机词条在 workflow 前或后
    - runtime fixed prefix/suffix: 包在 workflow 段外层的旧版前后缀
    - runtime_full: 当次整段附加（预设里的正/负全文）
    """
    wf = (workflow_text or "").strip()
    g = (global_text or "").strip() if global_enabled else ""
    rt = (runtime_full or "").strip()
    rnd = [x for x in random_lines if str(x).strip()]
    rnd_block = join_prompt_tokens(rnd) if rnd else ""

    core = wf
    if runtime_prefix or runtime_suffix or core:
        core = merge_text_append(core, runtime_prefix, runtime_suffix, None)

    blocks_before_wf: list[str] = []
    blocks_after_wf: list[str] = []

    if global_before_workflow and g:
        blocks_before_wf.append(g)
    if random_before_workflow and rnd_block:
        blocks_before_wf.append(rnd_block)

    if core:
        if global_before_workflow or random_before_workflow:
            blocks_after_wf.append(core)
        else:
            blocks_before_wf.append(core)

    if not global_before_workflow and g:
        blocks_after_wf.append(g)
    if not random_before_workflow and rnd_block:
        blocks_after_wf.append(rnd_block)
    if rt:
        blocks_after_wf.append(rt)

    parts: list[str] = []
    for b in blocks_before_wf + blocks_after_wf:
        b = str(b).strip()
        if b and (not parts or parts[-1] != b):
            parts.append(b)
    return "\n".join(parts)


def merge_side_preview_segments(
    *,
    workflow_text: str,
    global_text: str,
    runtime_full: str,
    runtime_prefix: str,
    runtime_suffix: str,
    random_lines: list[str],
    global_enabled: bool,
    global_before_workflow: bool,
    random_before_workflow: bool,
) -> list[dict[str, str]]:
    """按最终拼接顺序返回分段（global / random / core），供合并预览着色展示。"""
    wf = (workflow_text or "").strip()
    g = (global_text or "").strip() if global_enabled else ""
    rt = (runtime_full or "").strip()
    rnd = [x for x in random_lines if str(x).strip()]
    rnd_block = join_prompt_tokens(rnd) if rnd else ""

    core_inner = merge_text_append(wf, runtime_prefix, runtime_suffix, None)
    core_body = (core_inner or "").strip()
    if rt:
        core_body = merge_text_append(core_body, "", "", [rt]) if core_body else rt

    segments: list[dict[str, str]] = []

    def push(kind: str, text: str) -> None:
        t = (text or "").strip()
        if t:
            segments.append({"kind": kind, "text": t})

    if global_before_workflow and g:
        push("global", g)
    if random_before_workflow and rnd_block:
        push("random", rnd_block)

    if core_body:
        push("core", core_body)

    if not global_before_workflow and g:
        push("global", g)
    if not random_before_workflow and rnd_block:
        push("random", rnd_block)

    return segments


def layers_have_content(layer: dict | None) -> bool:
    if not layer:
        return False
    # 随机组：不依赖全局/当次「启用」总开关
    if _enabled_random_groups(layer):
        return True
    if not _layer_enabled(layer):
        return False
    if str(layer.get("positive", "")).strip() or str(layer.get("negative", "")).strip():
        return True
    for side in ("positive", "negative"):
        pre, suf = _runtime_fixed_parts(layer, side)
        if pre or suf:
            return True
    return False


def resolve_effective_layers(
    runtime_raw: dict | None,
    *,
    include_global: bool = True,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """返回 (global_layer, runtime_layer)。"""
    global_layer = global_as_runtime_layers() if include_global else _disabled_global()
    runtime_layer = normalize_prompt_layers(runtime_raw) if runtime_raw else None
    if runtime_layer and not _layer_enabled(runtime_layer):
        runtime_layer = None
    return global_layer, runtime_layer


def _disabled_global() -> dict[str, Any]:
    g = global_as_runtime_layers()
    g["enabled"] = False
    return g


def collect_all_random_groups(runtime_raw: dict | None) -> list[dict]:
    """全局 + 当次批量配置中的已启用随机组。"""
    global_layer, runtime_layer = resolve_effective_layers(runtime_raw, include_global=True)
    groups: list[dict] = []
    groups.extend(_enabled_random_groups(global_layer))
    if runtime_layer:
        groups.extend(_enabled_random_groups(runtime_layer))
    return groups


def collect_all_random_bundle_groups(runtime_raw: dict | None) -> list[dict]:
    global_layer, runtime_layer = resolve_effective_layers(runtime_raw, include_global=True)
    groups: list[dict] = []
    groups.extend(_enabled_random_bundle_groups(global_layer))
    if runtime_layer:
        groups.extend(_enabled_random_bundle_groups(runtime_layer))
    return groups


def build_merged_encode_texts(
    workflow_id: str,
    overrides: dict[str, dict[str, Any]] | None,
    *,
    runtime_raw: dict | None = None,
    style_enabled: bool | None = None,
    seed: int | None = None,
    index: int = 0,
    random_first_override: bool | None = None,
    include_global: bool = True,
    frozen_random_frags: dict[str, list[str]] | None = None,
    frozen_pick_records: list[dict] | None = None,
    log_source: str = "",
    include_segments: bool = False,
) -> tuple[dict[str, str], list[dict], dict[str, str]] | tuple[
    dict[str, str], list[dict], dict[str, str], dict[str, list[dict[str, str]]]
]:
    """
    生成节点正/负最终 text 与 pick 记录。
    返回 ({"positive": "...", "negative": "..."}, pick_records, debug_info)
    """
    import workflow_service

    overrides = copy.deepcopy(overrides or {})
    global_layer, runtime_layer = resolve_effective_layers(runtime_raw, include_global=include_global)

    prompt = workflow_service.build_api_prompt(
        workflow_id,
        overrides,
        style_enabled=style_enabled,
        apply_defaults=False,
    )
    encode = resolve_encode_nodes(load_defaults())
    workflow_texts: dict[str, str] = {}
    for side, nid in encode.items():
        if nid in prompt:
            raw = prompt[nid].get("inputs", {}).get("text", "")
            if not isinstance(raw, list):
                workflow_texts[side] = str(raw)

    flags = _merge_flags(global_layer, runtime_layer, random_first_override=random_first_override)

    all_groups: list[dict] = []
    all_groups.extend(_enabled_random_groups(global_layer))
    if runtime_layer:
        all_groups.extend(_enabled_random_groups(runtime_layer))

    all_bundle_groups: list[dict] = []
    all_bundle_groups.extend(_enabled_random_bundle_groups(global_layer))
    if runtime_layer:
        all_bundle_groups.extend(_enabled_random_bundle_groups(runtime_layer))

    debug: dict[str, str] = {}
    if frozen_random_frags is not None:
        random_lines = {
            side: [str(x) for x in (frozen_random_frags.get(side) or []) if str(x).strip()]
            for side in ("positive", "negative")
        }
        pick_records = list(frozen_pick_records or [])
        debug["random_mode"] = "shared"
    else:
        random_lines = _pick_random_lines(all_groups, seed=seed, index=index)
        _, pick_records = pick_random_groups(all_groups, seed=seed, index=index)
        bundle_frags, bundle_records = pick_random_bundle_groups(
            all_bundle_groups, seed=seed, index=index
        )
        for side in ("positive", "negative"):
            for line in bundle_frags.get(side) or []:
                s = str(line).strip()
                if s:
                    random_lines.setdefault(side, []).append(s)
        pick_records = list(pick_records) + list(bundle_records)
        debug["random_mode"] = "per_pick"
        debug["random_bundle_groups"] = str(len(all_bundle_groups))

    preview_segments: dict[str, list[dict[str, str]]] | None = (
        {"positive": [], "negative": []} if include_segments else None
    )
    merged: dict[str, str] = {}
    for side in ("positive", "negative"):
        g_text = str(global_layer.get(side, "")) if _layer_enabled(global_layer) else ""
        encode_has_text = _encode_text_in_overrides(overrides, encode, side)
        r_text = (
            ""
            if encode_has_text
            else (str(runtime_layer.get(side, "")) if runtime_layer else "")
        )
        pre, suf = _runtime_fixed_parts(runtime_layer or {}, side)
        if encode_has_text:
            pre, suf = "", ""
        core_text = merge_side_text(
            workflow_text=workflow_texts.get(side, ""),
            global_text=g_text,
            runtime_full=r_text,
            runtime_prefix=pre,
            runtime_suffix=suf,
            random_lines=[],
            global_enabled=_layer_enabled(global_layer),
            global_before_workflow=flags["global_before_workflow"],
            random_before_workflow=flags["random_before_workflow"],
        )
        merged[side], removed, rnd_place = merge_deduped_core_with_random(
            core_text,
            random_lines.get(side, []),
            random_before=flags["random_before_workflow"],
        )
        if removed:
            debug_key = f"dedupe_removed_{side}"
            debug[debug_key] = str(removed)
        rnd_n = len(random_lines.get(side, []))
        if rnd_n:
            debug[f"random_fragments_{side}"] = str(rnd_n)
            debug[f"random_placement_{side}"] = rnd_place
        if preview_segments is not None:
            preview_segments[side] = merge_side_preview_segments(
                workflow_text=workflow_texts.get(side, ""),
                global_text=g_text,
                runtime_full=r_text,
                runtime_prefix=pre,
                runtime_suffix=suf,
                random_lines=random_lines.get(side, []),
                global_enabled=_layer_enabled(global_layer),
                global_before_workflow=flags["global_before_workflow"],
                random_before_workflow=flags["random_before_workflow"],
            )

    debug = {
        **debug,
        "global_enabled": str(_layer_enabled(global_layer)),
        "global_random_groups": str(len(_enabled_random_groups(global_layer))),
        "runtime_random_groups": str(len(_enabled_random_groups(runtime_layer))),
        "random_groups_total": str(len(all_groups)),
        "random_picks_count": str(len(pick_records)),
        "global_before_workflow": str(flags["global_before_workflow"]),
        "random_before_workflow": str(flags["random_before_workflow"]),
        "has_runtime_layer": str(bool(runtime_layer)),
        "dedupe_tokens": "true",
    }
    pos = merged.get("positive", "")
    log.info(
        "[prompt_merge] workflow=%s index=%s global_on=%s groups=%d picks=%d pos_len=%d "
        "random_frags=%s placement=%s picks=%s head=%r tail=%r",
        workflow_id,
        index,
        _layer_enabled(global_layer),
        len(all_groups),
        len(pick_records),
        len(pos),
        debug.get("random_fragments_positive", "0"),
        debug.get("random_placement_positive", "-"),
        [p.get("text") for p in pick_records[:4]],
        pos[:100],
        pos[-100:] if pos else "",
    )
    if all_groups and not pick_records:
        log.warning(
            "[prompt_merge] 有随机组但未抽到词 groups=%d enabled_global=%s",
            len(all_groups),
            _layer_enabled(global_layer),
        )
    if log_source:
        import prompt_queue_log

        prompt_queue_log.log_prompt_merge(
            workflow_id=workflow_id,
            source=log_source,
            index=index,
            seed=seed,
            merged=merged,
            pick_records=pick_records,
            debug=debug,
            encode_node_ids=encode,
        )
    if preview_segments is not None:
        return merged, pick_records, debug, preview_segments
    return merged, pick_records, debug


def apply_merged_texts_to_overrides(
    overrides: dict[str, dict[str, Any]],
    texts: dict[str, str],
) -> dict[str, dict[str, Any]]:
    encode = resolve_encode_nodes(load_defaults())
    out = copy.deepcopy(overrides)
    for side, nid in encode.items():
        if texts.get(side) is not None:
            out[nid] = {**out.get(nid, {}), "text": texts[side]}
    return out


def build_text_overrides_for_queue(
    workflow_id: str,
    base_overrides: dict[str, dict[str, Any]] | None,
    runtime_raw: dict | None = None,
    *,
    style_enabled: bool | None = None,
    seed: int | None = None,
    index: int = 0,
    random_first_override: bool | None = None,
    frozen_random_frags: dict[str, list[str]] | None = None,
    frozen_pick_records: list[dict] | None = None,
    log_source: str = "",
) -> tuple[dict[str, dict[str, Any]], list[dict]]:
    """单抽/批量统一入口：写出 CLIP 节点 text 覆盖。"""
    texts, picks, _ = build_merged_encode_texts(
        workflow_id,
        base_overrides,
        runtime_raw=runtime_raw,
        style_enabled=style_enabled,
        seed=seed,
        index=index,
        random_first_override=random_first_override,
        include_global=True,
        frozen_random_frags=frozen_random_frags,
        frozen_pick_records=frozen_pick_records,
        log_source=log_source,
    )
    merged = apply_merged_texts_to_overrides(base_overrides or {}, texts)
    return merged, picks


def should_apply_prompt_layers(
    runtime_raw: dict | None,
    *,
    include_global: bool = True,
) -> bool:
    g, r = resolve_effective_layers(runtime_raw, include_global=include_global)
    return layers_have_content(g) or layers_have_content(r)


def build_queued_api_prompt(
    workflow_id: str,
    overrides: dict[str, dict[str, Any]] | None,
    runtime_raw: dict | None = None,
    *,
    style_enabled: bool | None = None,
    seed: int | None = None,
    index: int = 0,
    random_first_override: bool | None = None,
) -> tuple[dict, list[dict]]:
    """构建提交 ComfyUI 的完整 prompt dict。"""
    import workflow_service

    if should_apply_prompt_layers(runtime_raw):
        merged_ov, picks = build_text_overrides_for_queue(
            workflow_id,
            overrides,
            runtime_raw,
            style_enabled=style_enabled,
            seed=seed,
            index=index,
            random_first_override=random_first_override,
        )
        prompt = workflow_service.build_api_prompt(
            workflow_id,
            merged_ov,
            style_enabled=style_enabled,
            apply_defaults=False,
        )
        return prompt, picks

    prompt = workflow_service.build_api_prompt(
        workflow_id,
        overrides or {},
        style_enabled=style_enabled,
        apply_defaults=False,
    )
    return prompt, []
