"""A×B LoRA 网格批量生成。"""
import json
import logging
import random
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import BATCH_OUTPUT_PREFIX, COMFYUI_ROOT
from logging_config import setup_logging

setup_logging()
log = logging.getLogger("custom_project.batch")
from job_service import OUTPUT_DIR, collect_images_from_outputs

import batch_prompt_service
import global_reference_service
import batch_store
import comfy_client
import job_service
import workflow_service
import ws_tracker
from job_service import build_view_url

RUN_CONFIG_FILENAME = "run_config.json"
DEFAULT_TEMPLATE = (
    "{batch_id}/g{index:02d}_{a_name}_w{a_w}_{a_dir}_x_{b_name}_w{b_w}_{b_dir}_seed{seed}"
)

FILENAME_LEGEND = {
    "g{index:02d}": "本批第几张（00 起）",
    "{a_name}": "A 轴 LoRA 简称（工作流中第一个 LoRA）",
    "w{a_w}": "A 轴 strength_model，如 w0.30",
    "{a_dir}": "A 轴方向：inc=累加，dec=累减",
    "{b_name}": "B 轴 LoRA 简称（工作流中第二个 LoRA）",
    "w{b_w}": "B 轴 strength_model",
    "{b_dir}": "B 轴方向：inc / dec",
    "seed{seed}": "本次 KSampler 使用的 seed",
}


def _format_weight(value: float) -> str:
    """文件名用可读小数，如 0.30。"""
    return f"{value:.2f}"


def _format_weight_legacy(value: float) -> str:
    return f"{value:.2f}".replace(".", "p")


def _dir_tag(direction: str) -> str:
    return "inc" if direction == "up" else "dec"


def _slug_name(name: str, max_len: int = 24) -> str:
    s = re.sub(r"[^\w\-]+", "_", str(name), flags=re.UNICODE).strip("_")
    return (s[:max_len] if s else "lora")


def _axis_summary(meta: dict, rule: dict) -> str:
    direction = rule.get("direction", "up")
    dir_cn = "累加" if direction == "up" else "累减"
    return (
        f"{meta.get('short_name', '?')}(#{meta.get('node_id')}) "
        f"起始{rule.get('start')} {dir_cn} 步进{rule.get('step')} 共{rule.get('count')}档"
    )


def _strength_at(start: float, step: float, direction: str, axis_index: int) -> float:
    sign = 1.0 if direction == "up" else -1.0
    return round(start + sign * step * axis_index, 4)


def _normalize_seed_mode(mode: str | None) -> str:
    m = (mode or "fixed").strip().lower()
    if m in ("random", "rand"):
        return "random"
    if m in ("increment", "inc"):
        return "increment"
    return "fixed"


def _resolve_seed(seed_mode: str, base_seed: int | None, global_index: int) -> int:
    """random 模式不使用 base_seed（可为 None）。"""
    mode = _normalize_seed_mode(seed_mode)
    if mode == "random":
        return random.randint(0, 2**53 - 1)
    base = 0 if base_seed is None else int(base_seed)
    if mode == "increment":
        return base + global_index
    return base


def _render_filename_prefix(
    template: str,
    batch_id: str,
    index: int,
    ia: int,
    ib: int,
    lora_a: dict,
    lora_b: dict,
    wa: float,
    wb: float,
    seed: int,
    direction_a: str = "up",
    direction_b: str = "down",
) -> str:
    a_slug = _slug_name(lora_a.get("short_name", "A"))
    b_slug = _slug_name(lora_b.get("short_name", "B"))
    loras_tag = f"{a_slug}_w{_format_weight(wa)}_{_dir_tag(direction_a)}_x_{b_slug}_w{_format_weight(wb)}_{_dir_tag(direction_b)}"
    mapping = {
        "batch_id": batch_id,
        "index": str(index),
        "ia": str(ia),
        "ib": str(ib),
        "a_w": _format_weight(wa),
        "b_w": _format_weight(wb),
        "wa": _format_weight(wa),
        "wb": _format_weight(wb),
        "a_dir": _dir_tag(direction_a),
        "b_dir": _dir_tag(direction_b),
        "seed": str(seed),
        "loras": loras_tag,
        "a_name": a_slug,
        "b_name": b_slug,
    }

    def repl(match: re.Match) -> str:
        key = match.group(1)
        fmt = match.group(2) or ""
        val = mapping.get(key, "")
        if fmt.startswith(":") and fmt.endswith("d") and val.isdigit():
            width = int(fmt[1:-1])
            return str(val).zfill(width)
        return val

    result = re.sub(r"\{(\w+)((?::\d+d)?)\}", repl, template)
    return result.replace("..", ".").strip("/")


def _validate_axis(rule: dict, label: str) -> None:
    if not rule.get("enabled", True):
        return
    count = int(rule.get("count", 1))
    if count < 1 or count > 20:
        raise ValueError(f"{label} 档位数须在 1~20 之间")
    step = float(rule.get("step", 0))
    if step <= 0:
        raise ValueError(f"{label} 步进必须大于 0")


def _axis_cfg_by_node(lora_axes: list[dict] | None) -> dict[str, dict]:
    if not lora_axes:
        return {}
    return {str(a.get("node_id")): a for a in lora_axes if a.get("node_id") is not None}


def _apply_fixed_lora_overrides(
    overrides: dict[str, dict[str, Any]],
    loras: list[dict],
    axis_by_node: dict[str, dict],
    sync_clip: bool,
) -> dict[str, dict[str, Any]]:
    """未参与扫参的 LoRA 使用固定权重写入 overrides。"""
    out = dict(overrides)
    for meta in loras:
        nid = meta["node_id"]
        cfg = axis_by_node.get(nid)
        if cfg and cfg.get("enabled"):
            continue
        sm = meta["strength_model"]
        sc = meta["strength_clip"]
        if cfg:
            if cfg.get("fixed_strength_model") is not None:
                sm = float(cfg["fixed_strength_model"])
            if cfg.get("fixed_strength_clip") is not None:
                sc = float(cfg["fixed_strength_clip"])
        patch = {"strength_model": sm, "strength_clip": sc if not sync_clip else sm}
        if cfg and cfg.get("lora_name"):
            patch["lora_name"] = cfg["lora_name"]
        out[nid] = {**out.get(nid, {}), **patch}
    return out


def _resolve_sweep_rules(body: dict, loras: list[dict]) -> tuple[dict, dict, dict, dict]:
    """
    从 lora_axes（新）或 lora_a/lora_b（旧）解析扫参轴。
    返回 rule_a, rule_b, meta_a, meta_b；支持 1 或 2 个扫参轴。
    """
    axis_by_node = _axis_cfg_by_node(body.get("lora_axes"))
    if axis_by_node:
        if not loras:
            raise ValueError("工作流中没有 LoRA 节点")
        enabled = []
        for meta in loras:
            cfg = axis_by_node.get(meta["node_id"], {})
            if cfg.get("enabled"):
                enabled.append((meta, cfg))
        if not enabled:
            raise ValueError("请至少为 1 个 LoRA 开启「参与扫参」")
        if len(enabled) > 2:
            raise ValueError("最多 2 个 LoRA 参与扫参（避免组合数量爆炸）")

        # 按 sweep_role 排序：A 在前，B 在后，未标 role 的按勾选顺序
        def sort_key(item):
            meta, cfg = item
            role = (cfg.get("sweep_role") or "").upper()
            if role == "A":
                return (0, meta["node_id"])
            if role == "B":
                return (1, meta["node_id"])
            return (2, meta["node_id"])

        enabled.sort(key=sort_key)
        meta_a, cfg_a = enabled[0]
        rule_a = {
            "node_id": meta_a["node_id"],
            "alias": cfg_a.get("alias") or "A",
            "enabled": True,
            "start": cfg_a.get("start", meta_a["strength_model"]),
            "step": cfg_a.get("step", 0.1),
            "direction": cfg_a.get("direction", "up"),
            "count": cfg_a.get("count", 4),
        }
        if len(enabled) == 1:
            meta_b = meta_a
            rule_b = {
                "node_id": meta_a["node_id"],
                "alias": "B",
                "enabled": False,
                "start": meta_a["strength_model"],
                "step": 0.1,
                "direction": "down",
                "count": 1,
            }
        else:
            meta_b, cfg_b = enabled[1]
            rule_b = {
                "node_id": meta_b["node_id"],
                "alias": cfg_b.get("alias") or "B",
                "enabled": True,
                "start": cfg_b.get("start", meta_b["strength_model"]),
                "step": cfg_b.get("step", 0.1),
                "direction": cfg_b.get("direction", "down"),
                "count": cfg_b.get("count", 4),
            }
        _validate_axis(rule_a, "LoRA A")
        _validate_axis(rule_b, "LoRA B")
        return rule_a, rule_b, meta_a, meta_b

    if len(loras) < 1:
        raise ValueError("工作流中至少需要 1 个 LoRA 节点")
    rule_a = body.get("lora_a") or {}
    rule_b = body.get("lora_b") or {}
    if not rule_a.get("enabled", True) and not rule_b.get("enabled", True):
        raise ValueError("请至少启用一个扫参轴")
    _validate_axis(rule_a, "LoRA A")
    _validate_axis(rule_b, "LoRA B")
    node_a = str(rule_a.get("node_id") or loras[0]["node_id"])
    node_b = str(rule_b.get("node_id") or (loras[1]["node_id"] if len(loras) > 1 else loras[0]["node_id"]))
    meta_a = next((x for x in loras if x["node_id"] == node_a), loras[0])
    meta_b = next((x for x in loras if x["node_id"] == node_b), loras[min(1, len(loras) - 1)])
    return rule_a, rule_b, meta_a, meta_b


def _prompt_build_kwargs(body: dict) -> dict:
    if "style_enabled" in body:
        return {"style_enabled": bool(body["style_enabled"])}
    return {}


def build_grid_plan(workflow_id: str, body: dict) -> dict:
    import prompt_build_service
    import prompt_queue_log

    should_merge = prompt_build_service.should_apply_prompt_layers(body.get("batch_prompts"))
    global_groups = prompt_build_service.collect_all_random_groups(body.get("batch_prompts"))
    prompt_queue_log.append_event(
        "BATCH_PLAN_START",
        workflow_id=workflow_id,
        source="batch",
        extra={
            "should_apply_prompt_layers": should_merge,
            "batch_prompts_in_body": bool(body.get("batch_prompts")),
            "global_random_group_count": len(global_groups),
            "prompt_global_priority": body.get("prompt_global_priority"),
        },
    )

    fmt, _ = workflow_service.load_workflow_file(workflow_id)
    if fmt != "api":
        raise ValueError("批量仅支持 API 格式工作流")

    pkw = _prompt_build_kwargs(body)
    base_overrides = dict(body.get("base_overrides") or {})
    loras = workflow_service.discover_lora_nodes(
        workflow_service.build_api_prompt(workflow_id, base_overrides, **pkw)
    )
    axis_by_node = _axis_cfg_by_node(body.get("lora_axes"))
    sync_clip = body.get("sync_clip", True)
    base_overrides = _apply_fixed_lora_overrides(base_overrides, loras, axis_by_node, sync_clip)
    body = {**body, "base_overrides": base_overrides}

    rule_a, rule_b, meta_a, meta_b = _resolve_sweep_rules(body, loras)
    node_a = str(rule_a.get("node_id") or meta_a["node_id"])
    node_b = str(rule_b.get("node_id") or meta_b["node_id"])

    count_a = int(rule_a.get("count", 4)) if rule_a.get("enabled", True) else 1
    count_b = int(rule_b.get("count", 4)) if rule_b.get("enabled", True) else 1

    if not rule_a.get("enabled", True):
        count_a = 1
    if not rule_b.get("enabled", True):
        count_b = 1

    targets = workflow_service.discover_workflow_targets(
        workflow_service.build_api_prompt(workflow_id, {}, **pkw)
    )
    save_node_id = body.get("save_node_id") or targets.get("save_node_id")
    seed_node_id = body.get("seed_node_id") or targets.get("seed_node_id")
    if not save_node_id:
        raise ValueError("工作流中未找到 SaveImage 节点")

    seed_mode = _normalize_seed_mode(body.get("seed_mode", "fixed"))
    body = {**body, "seed_mode": seed_mode}
    base_seed = body.get("seed")
    if seed_mode in ("fixed", "increment") and base_seed is None:
        if targets.get("seed_nodes"):
            base_seed = targets["seed_nodes"][0].get("seed", 0)
        else:
            base_seed = 0

    template = body.get("filename_template") or DEFAULT_TEMPLATE
    batch_id = body.get("batch_id") or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]

    items = []
    global_index = 0
    for ia in range(count_a):
        wa = _strength_at(
            float(rule_a.get("start", meta_a["strength_model"])),
            float(rule_a.get("step", 0.1)),
            rule_a.get("direction", "up"),
            ia,
        ) if rule_a.get("enabled", True) else meta_a["strength_model"]
        for ib in range(count_b):
            wb = _strength_at(
                float(rule_b.get("start", meta_b["strength_model"])),
                float(rule_b.get("step", 0.1)),
                rule_b.get("direction", "up"),
                ib,
            ) if rule_b.get("enabled", True) else meta_b["strength_model"]

            seed = _resolve_seed(seed_mode, base_seed, global_index)
            dir_a = rule_a.get("direction", "up")
            dir_b = rule_b.get("direction", "down")
            prefix = _render_filename_prefix(
                template,
                batch_id,
                global_index,
                ia,
                ib,
                meta_a,
                meta_b,
                wa,
                wb,
                seed,
                dir_a,
                dir_b,
            )

            overrides: dict[str, dict[str, Any]] = dict(body.get("base_overrides") or {})
            if rule_a.get("enabled", True):
                patch_a = {"strength_model": wa}
                if sync_clip:
                    patch_a["strength_clip"] = wa
                overrides[node_a] = {**overrides.get(node_a, {}), **patch_a}
            if rule_b.get("enabled", True):
                patch_b = {"strength_model": wb}
                if sync_clip:
                    patch_b["strength_clip"] = wb
                overrides[node_b] = {**overrides.get(node_b, {}), **patch_b}
            overrides[save_node_id] = {
                **overrides.get(save_node_id, {}),
                "filename_prefix": prefix,
            }
            seed_nodes = targets.get("seed_nodes") or []
            if seed_nodes:
                for sn in seed_nodes:
                    nid = str(sn["node_id"])
                    overrides[nid] = {
                        **overrides.get(nid, {}),
                        "seed": seed,
                    }
            elif seed_node_id:
                overrides[str(seed_node_id)] = {
                    **overrides.get(str(seed_node_id), {}),
                    "seed": seed,
                }

            prompt_picks: list[dict] = []
            prompt_layers_applied = False
            import prompt_build_service

            should_merge = prompt_build_service.should_apply_prompt_layers(
                body.get("batch_prompts"),
            )
            if should_merge:
                text_ov, prompt_picks = batch_prompt_service.build_text_overrides_for_item(
                    workflow_id,
                    overrides,
                    body.get("batch_prompts"),
                    seed=seed,
                    index=global_index,
                    style_enabled=body.get("style_enabled"),
                    random_first=bool(body.get("prompt_global_priority")),
                    log_source=f"batch_plan:cell={global_index}",
                )
                for nid, patch in text_ov.items():
                    overrides[nid] = {**overrides.get(nid, {}), **patch}
                prompt_layers_applied = True
                clip3 = str(overrides.get("3", overrides.get(3, {})).get("text", ""))
                log.info(
                    "[batch_plan] cell=%s should_merge=True batch_prompts=%s picks=%d clip3_len=%d "
                    "picks_preview=%s",
                    global_index,
                    bool(body.get("batch_prompts")),
                    len(prompt_picks),
                    len(clip3),
                    [p.get("text") for p in prompt_picks[:4]],
                )
            else:
                import prompt_queue_log

                prompt_queue_log.append_event(
                    "BATCH_PLAN_SKIP_MERGE",
                    workflow_id=workflow_id,
                    source=f"batch_plan:cell={global_index}",
                    extra={
                        "reason": "should_apply_prompt_layers=False",
                        "batch_prompts": bool(body.get("batch_prompts")),
                    },
                )
                log.info(
                    "[batch_plan] cell=%s should_merge=False（全局与当次均无提示词层）",
                    global_index,
                )

            workflow_snapshot = {
                "workflow_id": workflow_id,
                "overrides": overrides,
                "batch_prompts": body.get("batch_prompts"),
                "prompt_picks": prompt_picks,
                "style_enabled": body.get("style_enabled"),
                "prompt_global_priority": body.get("prompt_global_priority"),
                "seed": seed,
                "seed_mode": seed_mode,
            }

            items.append({
                "index": global_index,
                "ia": ia,
                "ib": ib,
                "seed": seed,
                "filename_prefix": prefix,
                "overrides": overrides,
                "workflow_snapshot": workflow_snapshot,
                "loras": {
                    "A": {
                        "node_id": node_a,
                        "alias": rule_a.get("alias") or "A",
                        "lora_name": meta_a["lora_name"],
                        "short_name": meta_a["short_name"],
                        "strength_model": wa,
                        "strength_clip": wa if sync_clip else meta_a["strength_clip"],
                    },
                    "B": {
                        "node_id": node_b,
                        "alias": rule_b.get("alias") or "B",
                        "lora_name": meta_b["lora_name"],
                        "short_name": meta_b["short_name"],
                        "strength_model": wb,
                        "strength_clip": wb if sync_clip else meta_b["strength_clip"],
                    },
                },
                "label": (
                    f"{meta_a.get('short_name')}={wa:.2f}{'↑' if dir_a == 'up' else '↓'} · "
                    f"{meta_b.get('short_name')}={wb:.2f}{'↑' if dir_b == 'up' else '↓'}"
                ),
                "filename_hint": prefix.split("/")[-1] if "/" in prefix else prefix,
                "prompt_picks": prompt_picks,
                "prompt_layers_applied": prompt_layers_applied,
            })
            global_index += 1

    return {
        "batch_id": batch_id,
        "workflow_id": workflow_id,
        "grid": {"a_count": count_a, "b_count": count_b, "total": len(items)},
        "lora_a": meta_a,
        "lora_b": meta_b,
        "workflow_loras": loras,
        "lora_axes": body.get("lora_axes"),
        "save_node_id": save_node_id,
        "seed_node_id": seed_node_id,
        "seed_mode": seed_mode,
        "base_seed": base_seed,
        "filename_template": template,
        "filename_legend": FILENAME_LEGEND,
        "strategy_summary": (
            f"A: {_axis_summary(meta_a, rule_a)} | B: {_axis_summary(meta_b, rule_b)}"
        ),
        "output_dir": f"{BATCH_OUTPUT_PREFIX}/{batch_id}",
        "items": items,
        "request_body": {
            k: v
            for k, v in body.items()
            if k not in ("batch_id",)
        },
    }


def wait_for_prompt(prompt_id: str, client_id: str, batch_id: str, timeout: float = 7200) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if batch_store.is_cancelled(batch_id):
            raise RuntimeError("批量任务已取消")
        detail = job_service.get_job_detail(prompt_id)
        if detail["status"] in ("completed", "failed", "cancelled"):
            return detail
        time.sleep(1.0)
    raise RuntimeError(f"等待超时: {prompt_id}")


def run_batch(workflow_id: str, body: dict) -> None:
    plan = build_grid_plan(workflow_id, body)
    batch_id = plan["batch_id"]
    items = plan["items"]

    if batch_store.get(batch_id):
        batch_store.update(
            batch_id,
            status="running",
            plan=plan,
            total=len(items),
            message="批量执行中…",
        )
    else:
        batch_store.create(batch_id, {
            "batch_id": batch_id,
            "workflow_id": workflow_id,
            "status": "running",
            "plan": plan,
            "completed": 0,
            "total": len(items),
            "items": [],
            "error": None,
            "cancel_requested": False,
            "started_at": datetime.now(timezone.utc).isoformat(),
        })

    log.info(
        "批量开始 batch_id=%s workflow=%s total=%d output=%s",
        batch_id,
        workflow_id,
        len(items),
        plan.get("output_dir"),
    )

    manifest_items = []
    stop_on_error = body.get("stop_on_error", True)

    try:
        for item in items:
            if batch_store.is_cancelled(batch_id):
                batch_store.update(batch_id, status="cancelled")
                return

            batch_store.update(
                batch_id,
                current_index=item["index"],
                current_label=item["label"],
                message=f"正在生成 {item['index'] + 1}/{len(items)}: {item['label']}",
            )
            log.info(
                "批量进度 batch_id=%s %d/%d %s",
                batch_id,
                item["index"] + 1,
                len(items),
                item["label"],
            )

            kw = _prompt_build_kwargs(body)
            if item.get("prompt_layers_applied"):
                kw["apply_defaults"] = False
            clip3 = str(item.get("overrides", {}).get("3", item.get("overrides", {}).get(3, {})).get("text", ""))
            clip4 = str(item.get("overrides", {}).get("4", item.get("overrides", {}).get(4, {})).get("text", ""))
            log.info(
                "[batch_queue] cell=%s apply_defaults=%s layers_applied=%s picks=%d clip3_len=%d "
                "head=%r tail=%r",
                item["index"],
                kw.get("apply_defaults", True),
                bool(item.get("prompt_layers_applied")),
                len(item.get("prompt_picks") or []),
                len(clip3),
                clip3[:100] if clip3 else "",
                clip3[-100:] if clip3 else "",
            )
            prompt = workflow_service.build_api_prompt(
                workflow_id, item["overrides"], **kw
            )
            final3 = str(prompt.get("3", prompt.get(3, {})).get("inputs", {}).get("text", ""))
            log.info(
                "[batch_queue] cell=%s final_clip3_len=%d random_in_final=%s",
                item["index"],
                len(final3),
                any(
                    (p.get("text") or "") in final3
                    for p in (item.get("prompt_picks") or [])[:6]
                ),
            )
            import prompt_defaults_service as pds
            import prompt_queue_log

            encode_ids = pds.load_defaults()
            encode_map = {
                "positive": str((encode_ids.get("positive") or {}).get("node_id", "3")),
                "negative": str((encode_ids.get("negative") or {}).get("node_id", "4")),
            }
            prompt_queue_log.log_comfyui_queue(
                workflow_id=workflow_id,
                source="batch_queue",
                batch_id=batch_id,
                cell_index=item["index"],
                apply_defaults=kw.get("apply_defaults", True),
                layers_applied=bool(item.get("prompt_layers_applied")),
                pick_records=item.get("prompt_picks") or [],
                overrides_clip={"3": clip3, "4": clip4},
                final_prompt=prompt,
                encode_node_ids=encode_map,
            )
            client_id = str(uuid.uuid4())
            prompt_id = str(uuid.uuid4())
            result = comfy_client.queue_prompt(prompt, client_id=client_id, prompt_id=prompt_id)
            pid = result.get("prompt_id", prompt_id)
            ws_tracker.start_tracking(client_id, pid)

            try:
                detail = wait_for_prompt(pid, client_id, batch_id)
            except RuntimeError as exc:
                if "取消" in str(exc):
                    batch_store.update(batch_id, status="cancelled")
                    return
                entry = {
                    **item,
                    "prompt_id": pid,
                    "status": "failed",
                    "error": str(exc),
                    "images": [],
                }
                manifest_items.append(entry)
                batch_store.update(batch_id, items=manifest_items, completed=len(manifest_items))
                if stop_on_error:
                    batch_store.update(batch_id, status="failed", error=str(exc))
                    _write_manifest(batch_id, plan, manifest_items)
                    return
                continue

            images = collect_images_from_outputs(
                comfy_client.get_job(pid).get("outputs", {}) if detail["status"] == "completed" else {}
            )
            if not images and detail["status"] == "completed":
                hist = comfy_client.get_history(pid)
                if pid in hist:
                    images = collect_images_from_outputs(hist[pid].get("outputs", {}))

            for img in images:
                img["label"] = item["label"]
                img["grid_ia"] = item["ia"]
                img["grid_ib"] = item["ib"]
                img["loras"] = item["loras"]

            entry = {
                **item,
                "prompt_id": pid,
                "status": detail["status"],
                "images": images,
                "error": detail.get("message") if detail["status"] != "completed" else None,
            }
            manifest_items.append(entry)
            batch_store.update(
                batch_id,
                items=manifest_items,
                completed=len(manifest_items),
            )
            _write_manifest(
                batch_id,
                plan,
                manifest_items,
                status="running",
                message=f"已完成 {len(manifest_items)}/{len(items)}",
            )

            if detail["status"] != "completed" and stop_on_error:
                err = entry.get("error") or "生成失败"
                batch_store.update(batch_id, status="failed", error=err)
                _write_manifest(
                    batch_id, plan, manifest_items, status="failed", error=err
                )
                _write_run_config(batch_id, {"status": "failed", "error": err})
                return

        finished = datetime.now(timezone.utc).isoformat()
        _write_manifest(
            batch_id, plan, manifest_items, status="completed", message="批量生成完成"
        )
        _write_run_config(
            batch_id,
            {"status": "completed", "completed_count": len(manifest_items)},
            finished_at=finished,
        )
        batch_store.update(batch_id, status="completed", message="批量生成完成")
        log.info("批量完成 batch_id=%s completed=%d", batch_id, len(manifest_items))

    except Exception as exc:
        log.exception("批量失败 batch_id=%s", batch_id)
        batch_store.update(batch_id, status="failed", error=str(exc))
        _write_manifest(
            batch_id, plan, manifest_items, status="failed", error=str(exc)
        )
        _write_run_config(batch_id, {"status": "failed", "error": str(exc)})


def _batch_output_dir(batch_id: str) -> Path:
    return OUTPUT_DIR / BATCH_OUTPUT_PREFIX / batch_id


def _enrich_items_images(items: list[dict]) -> list[dict]:
    for item in items:
        for img in item.get("images") or []:
            if not img.get("url") and img.get("filename"):
                img["url"] = build_view_url(
                    img["filename"],
                    img.get("subfolder", ""),
                    img.get("type", "output"),
                )
    return items


def _infer_status(manifest: dict) -> str:
    explicit = manifest.get("status")
    if explicit and explicit != "unknown":
        return explicit
    items = manifest.get("items") or []
    grid_total = (manifest.get("grid") or {}).get("total") or len(items)
    completed = sum(1 for it in items if it.get("status") == "completed")
    if completed and completed >= grid_total:
        return "completed"
    if items:
        return "running"
    return "unknown"


def _manifest_to_entry(manifest: dict, batch_id: str, *, recovered: bool = False) -> dict:
    items = _enrich_items_images(list(manifest.get("items") or []))
    grid = manifest.get("grid") or {}
    total = grid.get("total") or len(items)
    completed = sum(1 for it in items if it.get("status") == "completed")
    status = _infer_status({**manifest, "items": items})
    return {
        "batch_id": batch_id,
        "workflow_id": manifest.get("workflow_id"),
        "status": status,
        "plan": {
            "grid": grid,
            "seed_mode": manifest.get("seed_mode"),
            "output_dir": manifest.get("output_dir"),
        },
        "completed": completed,
        "total": total,
        "items": items,
        "started_at": manifest.get("started_at"),
        "finished_at": manifest.get("finished_at"),
        "message": manifest.get("message") or (
            "从 manifest.json 恢复" if recovered else ""
        ),
        "recovered_from_disk": recovered,
        "error": manifest.get("error"),
    }


def _write_manifest(
    batch_id: str,
    plan: dict,
    items: list[dict],
    *,
    status: str | None = None,
    started_at: str | None = None,
    message: str | None = None,
    error: str | None = None,
) -> None:
    """每批一条 manifest.json，作为持久化记录（无需数据库）。"""
    out_dir = _batch_output_dir(batch_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"
    existing: dict = {}
    if manifest_path.is_file():
        try:
            with open(manifest_path, encoding="utf-8") as f:
                existing = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass

    grid_total = plan["grid"]["total"]
    completed = sum(1 for it in items if it.get("status") == "completed")
    if status is None:
        if completed >= grid_total and completed > 0:
            status = "completed"
        elif items:
            status = "running"
        else:
            status = existing.get("status") or "running"

    now = datetime.now(timezone.utc).isoformat()
    manifest = {
        "batch_id": batch_id,
        "workflow_id": plan["workflow_id"],
        "grid": plan["grid"],
        "seed_mode": plan.get("seed_mode"),
        "output_dir": str(out_dir.relative_to(COMFYUI_ROOT / "output")).replace("\\", "/"),
        "status": status,
        "started_at": started_at or existing.get("started_at") or now,
        "finished_at": now if status in ("completed", "failed", "cancelled") else existing.get("finished_at"),
        "items": items,
        "message": message if message is not None else existing.get("message"),
        "error": error if error is not None else existing.get("error"),
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def _build_run_config(plan: dict, body: dict) -> dict:
    rule_a = body.get("lora_a") or {}
    rule_b = body.get("lora_b") or {}
    meta_a = plan.get("lora_a") or {}
    meta_b = plan.get("lora_b") or {}
    example = ""
    if plan.get("items"):
        example = plan["items"][0].get("filename_hint") or plan["items"][0].get("filename_prefix", "")
    return {
        "batch_id": plan["batch_id"],
        "workflow_id": plan["workflow_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "output_dir": plan.get("output_dir"),
        "strategy_summary": plan.get("strategy_summary"),
        "grid": plan.get("grid"),
        "seed_mode": plan.get("seed_mode"),
        "base_seed": plan.get("base_seed"),
        "sync_clip": body.get("sync_clip", True),
        "filename_template": plan.get("filename_template"),
        "filename_legend": plan.get("filename_legend") or FILENAME_LEGEND,
        "filename_example": example,
        "lora_a": {
            **rule_a,
            "node_id": meta_a.get("node_id"),
            "lora_name": meta_a.get("lora_name"),
            "short_name": meta_a.get("short_name"),
        },
        "lora_b": {
            **rule_b,
            "node_id": meta_b.get("node_id"),
            "lora_name": meta_b.get("lora_name"),
            "short_name": meta_b.get("short_name"),
        },
        "save_node_id": plan.get("save_node_id"),
        "seed_node_id": plan.get("seed_node_id"),
        "base_overrides": body.get("base_overrides") or {},
        "batch_prompts": body.get("batch_prompts"),
        "style_enabled": body.get("style_enabled"),
        "lora_axes": body.get("lora_axes"),
        "seed_mode": body.get("seed_mode"),
        "prompt_global_priority": body.get("prompt_global_priority"),
        "request_body": {
            k: v
            for k, v in (plan.get("request_body") or body).items()
            if k not in ("batch_id", "task_id", "task_name")
        },
        "task_id": body.get("task_id"),
        "task_name": body.get("task_name"),
        "workflow_params_note": "base_overrides 为控制台表单中的节点参数；与本次 A×B 扫参叠加后提交 ComfyUI。",
    }


def _write_run_config(batch_id: str, config: dict, *, finished_at: str | None = None) -> None:
    out_dir = _batch_output_dir(batch_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / RUN_CONFIG_FILENAME
    existing: dict = {}
    if path.is_file():
        try:
            with open(path, encoding="utf-8") as f:
                existing = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    merged = {**existing, **config}
    if finished_at:
        merged["finished_at"] = finished_at
    with open(path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    log.info("已写入 %s batch_id=%s", RUN_CONFIG_FILENAME, batch_id)


def persist_batch_start(plan: dict, body: dict | None = None) -> None:
    """批量开始时写入 manifest + run_config.json。"""
    batch_id = plan["batch_id"]
    _write_manifest(
        batch_id,
        plan,
        [],
        status="running",
        started_at=datetime.now(timezone.utc).isoformat(),
        message="批量已排队…",
    )
    if body is not None:
        _write_run_config(batch_id, _build_run_config(plan, body))
    log.info("已写入批量记录 manifest + run_config batch_id=%s", batch_id)


def _read_manifest(batch_id: str) -> dict | None:
    manifest_path = _batch_output_dir(batch_id) / "manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        with open(manifest_path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("读取 manifest 失败 batch_id=%s: %s", batch_id, exc)
        return None


def _summary_from_manifest(manifest: dict, batch_id: str) -> dict:
    entry = _manifest_to_entry(manifest, batch_id)
    thumb = None
    for it in entry.get("items") or []:
        if it.get("status") == "completed" and it.get("images"):
            thumb = it["images"][0].get("url")
            break
    rc = _read_run_config(batch_id) or {}
    return {
        "batch_id": batch_id,
        "workflow_id": entry.get("workflow_id"),
        "status": entry.get("status"),
        "started_at": entry.get("started_at"),
        "finished_at": entry.get("finished_at"),
        "grid": entry.get("plan", {}).get("grid"),
        "completed": entry.get("completed"),
        "total": entry.get("total"),
        "thumbnail_url": thumb,
        "output_dir": entry.get("plan", {}).get("output_dir"),
        "task_id": rc.get("task_id"),
        "task_name": rc.get("task_name"),
    }


def list_batches(limit: int = 50, *, task_id: str | None = None) -> list[dict]:
    root = OUTPUT_DIR / BATCH_OUTPUT_PREFIX
    if not root.is_dir():
        return []
    dirs = [p for p in root.iterdir() if p.is_dir()]
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    records = []
    for d in dirs[: limit * 4]:
        if task_id:
            rc = _read_run_config(d.name)
            if not rc or str(rc.get("task_id")) != str(task_id):
                continue
        manifest = _read_manifest(d.name)
        if manifest:
            rec = _summary_from_manifest(manifest, d.name)
            if task_id:
                rc = _read_run_config(d.name) or {}
                rec["task_id"] = rc.get("task_id")
                rec["task_name"] = rc.get("task_name")
            records.append(rec)
        else:
            records.append({
                "batch_id": d.name,
                "workflow_id": None,
                "status": "unknown",
                "started_at": datetime.fromtimestamp(
                    d.stat().st_mtime, tz=timezone.utc
                ).isoformat(),
                "finished_at": None,
                "grid": None,
                "completed": 0,
                "total": 0,
                "thumbnail_url": None,
                "output_dir": f"{BATCH_OUTPUT_PREFIX}/{d.name}",
            })
        if len(records) >= limit:
            break
    return records


def _read_run_config(batch_id: str) -> dict | None:
    path = _batch_output_dir(batch_id) / RUN_CONFIG_FILENAME
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def get_batch(batch_id: str) -> dict | None:
    entry = batch_store.get(batch_id)
    if entry:
        entry = dict(entry)
        entry["items"] = _enrich_items_images(entry.get("items") or [])
        rc = _read_run_config(batch_id)
        if rc:
            entry["run_config"] = rc
        return entry
    manifest = _read_manifest(batch_id)
    if manifest:
        out = _manifest_to_entry(manifest, batch_id, recovered=True)
        rc = _read_run_config(batch_id)
        if rc:
            out["run_config"] = rc
        return out
    return None


def _delete_item_outputs(item: dict) -> list[str]:
    from job_service import safe_delete_image_file

    deleted_files: list[str] = []
    for img in item.get("images") or []:
        try:
            if safe_delete_image_file(
                img["filename"], img.get("subfolder", ""), img.get("type", "output")
            ):
                deleted_files.append(img["filename"])
        except (OSError, ValueError):
            pass
    pid = item.get("prompt_id")
    if pid:
        try:
            comfy_client.delete_history(pid)
        except RuntimeError:
            pass
    return deleted_files


def delete_batch_items(batch_id: str, indices: list[int]) -> dict:
    """删除批量中的指定格子（按 item.index）。"""
    idx_set = {int(i) for i in indices}
    if not idx_set:
        return {"ok": True, "batch_id": batch_id, "removed": 0}

    manifest = _read_manifest(batch_id)
    entry = batch_store.get(batch_id)
    if manifest:
        items = list(manifest.get("items") or [])
        workflow_id = manifest.get("workflow_id")
        grid = dict(manifest.get("grid") or {})
        seed_mode = manifest.get("seed_mode")
    elif entry:
        items = list(entry.get("items") or [])
        workflow_id = entry.get("workflow_id")
        grid = dict((entry.get("plan") or {}).get("grid") or {})
        seed_mode = (entry.get("plan") or {}).get("seed_mode")
    else:
        raise FileNotFoundError(f"批量不存在: {batch_id}")

    to_remove = [it for it in items if int(it.get("index", -1)) in idx_set]
    if not to_remove:
        return {"ok": True, "batch_id": batch_id, "removed": 0}

    deleted_files: list[str] = []
    for it in to_remove:
        deleted_files.extend(_delete_item_outputs(it))

    remaining = [it for it in items if int(it.get("index", -1)) not in idx_set]
    if not remaining:
        return delete_batch(batch_id)

    plan = {
        "workflow_id": workflow_id,
        "grid": {**grid, "total": len(remaining)},
        "seed_mode": seed_mode,
    }
    completed = sum(
        1 for it in remaining if it.get("status") == "completed" and (it.get("images") or [])
    )
    status = _infer_status({**manifest, "items": remaining, "grid": plan["grid"]} if manifest else {"items": remaining, "grid": plan["grid"]})
    _write_manifest(batch_id, plan, remaining, status=status, message=f"已删除 {len(to_remove)} 格")
    if entry:
        batch_store.update(
            batch_id,
            items=remaining,
            completed=completed,
            total=len(remaining),
            status=status,
        )
    return {
        "ok": True,
        "batch_id": batch_id,
        "removed": len(to_remove),
        "remaining": len(remaining),
        "deleted_files": deleted_files,
    }


def delete_batch(batch_id: str) -> dict:
    import shutil

    entry = batch_store.get(batch_id)
    deleted_files = []
    out_dir = OUTPUT_DIR / BATCH_OUTPUT_PREFIX / batch_id
    if entry:
        for item in entry.get("items", []):
            deleted_files.extend(_delete_item_outputs(item))
    manifest = _read_manifest(batch_id)
    if manifest and not entry:
        for item in manifest.get("items") or []:
            deleted_files.extend(_delete_item_outputs(item))
    if out_dir.is_dir():
        shutil.rmtree(out_dir, ignore_errors=True)
    if entry:
        batch_store.update(batch_id, status="deleted")
    return {"ok": True, "batch_id": batch_id, "deleted_files": deleted_files}


def cancel_batch(batch_id: str) -> dict:
    batch_store.set_cancelled(batch_id)
    try:
        comfy_client.interrupt()
    except RuntimeError:
        pass
    batch_store.update(batch_id, status="cancelling", message="正在取消…")
    return {"ok": True, "batch_id": batch_id}
