"""统一生成历史：单抽 + 批量，按时间排序，支持筛选。"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import BATCH_OUTPUT_PREFIX, COMFYUI_ROOT, SINGLE_OUTPUT_PREFIX
from job_service import OUTPUT_DIR, build_view_url, collect_images_from_outputs

import batch_service
import comfy_client

log = logging.getLogger(__name__)

RECORD_FILENAME = "record.json"


def _single_dir(prompt_id: str) -> Path:
    return OUTPUT_DIR / SINGLE_OUTPUT_PREFIX / prompt_id


def _record_path(prompt_id: str) -> Path:
    return _single_dir(prompt_id) / RECORD_FILENAME


def _parse_iso(ts: str | None) -> float:
    if not ts:
        return 0.0
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _prompt_to_comma(text: str) -> str:
    """多行合并结果 → 单行逗号 tag（按词条拆，与 merge 预览原文一致，避免行末逗号产生 ,,）。"""
    from reference_pick_service import split_prompt_tokens

    tokens: list[str] = []
    for line in str(text or "").replace("\r\n", "\n").split("\n"):
        tokens.extend(split_prompt_tokens(line))
    return ", ".join(tokens)


def _build_queued_prompt(
    workflow_id: str,
    overrides: dict[str, dict[str, Any]] | None,
    snap: dict[str, Any],
) -> dict:
    """与提交 ComfyUI 队列时一致的 prompt 构建。"""
    from prompt_build_service import build_queued_api_prompt

    seed = snap.get("item_seed")
    if seed is None and overrides:
        for nid in ("5", "14"):
            s = (overrides.get(nid) or overrides.get(str(nid)) or {}).get("seed")
            if s is not None:
                seed = s
                break
    prio = snap.get("prompt_global_priority")
    prompt, _ = build_queued_api_prompt(
        workflow_id or "First_api",
        overrides,
        snap.get("batch_prompts"),
        style_enabled=snap.get("style_enabled"),
        seed=seed,
        index=int(snap.get("item_index") or 0),
        random_first_override=bool(prio) if prio is not None else None,
    )
    return prompt


def _attach_final_prompts(meta: dict[str, Any], prompt: dict) -> None:
    from prompt_defaults_service import load_defaults
    from prompt_merge_service import resolve_encode_nodes

    encode = resolve_encode_nodes(load_defaults())
    pos = neg = ""
    for side, nid in encode.items():
        if nid not in prompt:
            continue
        raw = prompt[nid].get("inputs", {}).get("text")
        if isinstance(raw, list):
            continue
        text = str(raw)
        if side == "positive":
            pos = text
        elif side == "negative":
            neg = text
    meta["prompt_positive"] = pos
    meta["prompt_negative"] = neg
    meta["prompt_positive_comma"] = _prompt_to_comma(pos)
    meta["prompt_negative_comma"] = _prompt_to_comma(neg)


def extract_meta_from_overrides(
    workflow_id: str,
    overrides: dict[str, dict[str, Any]] | None,
    *,
    workflow_snapshot: dict | None = None,
) -> dict[str, Any]:
    """从 overrides 提取筛选/展示用元数据。"""
    import workflow_service

    overrides = overrides or {}
    meta: dict[str, Any] = {
        "checkpoint": None,
        "loras": [],
        "sampler": {},
        "prompt_positive": "",
        "prompt_negative": "",
    }
    snap = workflow_snapshot or {}
    picks = snap.get("prompt_picks") or []
    if picks:
        meta["prompt_picks"] = picks

    try:
        prompt = _build_queued_prompt(workflow_id, overrides, snap)
    except (FileNotFoundError, ValueError):
        prompt = {}

    for node_id, node in prompt.items():
        ct = node.get("class_type", "")
        inp = node.get("inputs", {})
        patch = overrides.get(str(node_id), {})
        if ct == "CheckpointLoaderSimple":
            meta["checkpoint"] = patch.get("ckpt_name") or inp.get("ckpt_name")
        elif ct in workflow_service.LORA_CLASS_TYPES:
            meta["loras"].append({
                "node_id": str(node_id),
                "lora_name": patch.get("lora_name") or inp.get("lora_name"),
                "short_name": _short_lora(patch.get("lora_name") or inp.get("lora_name", "")),
                "strength_model": float(
                    patch.get("strength_model", inp.get("strength_model", 1))
                ),
                "strength_clip": float(
                    patch.get("strength_clip", inp.get("strength_clip", 1))
                ),
            })
        elif ct == "KSampler":
            samp = {
                k: patch.get(k, inp.get(k))
                for k in ("seed", "steps", "cfg", "sampler_name", "scheduler", "denoise")
                if k in inp or k in patch
            }
            try:
                import workflow_meta_service as wms

                topo = (wms.load_meta(workflow_id or "First_api") or {}).get("topology") or {}
            except Exception:
                topo = {}
            primary = str(topo.get("ksampler_pass1") or "5")
            secondary = str(topo.get("ksampler_pass2") or "14")
            nid = str(node_id)
            if nid == primary:
                meta["sampler"] = samp
            elif nid == secondary:
                meta["sampler_pass2"] = samp
            elif not meta.get("sampler"):
                meta["sampler"] = samp
    _attach_final_prompts(meta, prompt)

    if not meta["checkpoint"]:
        for patch in overrides.values():
            if isinstance(patch, dict) and patch.get("ckpt_name"):
                meta["checkpoint"] = patch["ckpt_name"]
                break

    meta["loras"].sort(key=lambda x: x.get("node_id", ""))
    return meta


def _short_lora(name: str) -> str:
    import re
    s = str(name or "")
    return re.sub(r"\.(safetensors|ckpt|pt)$", "", s, flags=re.I) or s


def persist_single_queued(
    *,
    prompt_id: str,
    workflow_id: str,
    overrides: dict[str, dict[str, Any]],
    style_enabled: bool | None = None,
    batch_prompts: dict | None = None,
    prompt_picks: list[dict] | None = None,
) -> dict:
    """单抽提交后立即写入记录（图片完成后更新）。"""
    now = datetime.now(timezone.utc).isoformat()
    snapshot = {
        "workflow_id": workflow_id,
        "overrides": overrides,
        "batch_prompts": batch_prompts,
        "prompt_picks": prompt_picks or [],
        "style_enabled": style_enabled,
    }
    meta = extract_meta_from_overrides(workflow_id, overrides, workflow_snapshot=snapshot)
    record = {
        "id": prompt_id,
        "type": "single",
        "prompt_id": prompt_id,
        "workflow_id": workflow_id,
        "started_at": now,
        "finished_at": None,
        "status": "pending",
        "workflow_snapshot": snapshot,
        "meta": meta,
        "images": [],
    }
    out = _single_dir(prompt_id)
    out.mkdir(parents=True, exist_ok=True)
    with open(_record_path(prompt_id), "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    log.info("已写入单抽历史 record prompt_id=%s", prompt_id)
    return record


def try_finish_single_record(prompt_id: str) -> None:
    """任务完成时补全图片与状态。"""
    path = _record_path(prompt_id)
    if not path.is_file():
        return
    try:
        with open(path, encoding="utf-8") as f:
            record = json.load(f)
    except (OSError, json.JSONDecodeError):
        return
    if record.get("status") == "completed" and record.get("images"):
        return
    try:
        hist = comfy_client.get_history(prompt_id)
        if prompt_id not in hist:
            return
        entry = hist[prompt_id]
        status = entry.get("status", {})
        if isinstance(status, dict) and status.get("status_str") == "error":
            record["status"] = "failed"
            record["finished_at"] = datetime.now(timezone.utc).isoformat()
        else:
            images = collect_images_from_outputs(entry.get("outputs", {}))
            if images:
                record["images"] = images
                record["status"] = "completed"
                record["finished_at"] = datetime.now(timezone.utc).isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
    except RuntimeError as exc:
        log.debug("finish single record %s: %s", prompt_id, exc)


def _load_single_record(prompt_id: str) -> dict | None:
    path = _record_path(prompt_id)
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            rec = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if rec.get("status") != "completed" or not rec.get("images"):
        try_finish_single_record(prompt_id)
        try:
            with open(path, encoding="utf-8") as f:
                rec = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    return _single_to_timeline(rec)


def _single_to_timeline(rec: dict | None) -> dict | None:
    if not rec:
        return None
    images = rec.get("images") or []
    thumb = images[0].get("url") if images else None
    meta = rec.get("meta") or {}
    return {
        "id": rec.get("id") or rec.get("prompt_id"),
        "type": "single",
        "prompt_id": rec.get("prompt_id"),
        "workflow_id": rec.get("workflow_id"),
        "started_at": rec.get("started_at"),
        "finished_at": rec.get("finished_at"),
        "status": rec.get("status", "unknown"),
        "thumbnail_url": thumb,
        "meta": meta,
        "images": images,
        "workflow_snapshot": rec.get("workflow_snapshot"),
    }


def _batch_to_timeline(summary: dict) -> dict:
    rc = batch_service._read_run_config(summary["batch_id"]) or {}
    overrides = rc.get("base_overrides") or {}
    meta = extract_meta_from_overrides(
        summary.get("workflow_id") or "",
        overrides,
        workflow_snapshot={
            "batch_prompts": rc.get("batch_prompts"),
            "style_enabled": rc.get("style_enabled"),
            "prompt_global_priority": rc.get("prompt_global_priority"),
            "item_index": 0,
        },
    )
    la = rc.get("lora_a") or {}
    lb = rc.get("lora_b") or {}
    if la.get("lora_name"):
        found = any(x.get("node_id") == str(la.get("node_id")) for x in meta["loras"])
        if not found:
            meta["loras"].insert(0, {
                "node_id": str(la.get("node_id", "15")),
                "lora_name": la.get("lora_name"),
                "short_name": la.get("short_name") or _short_lora(la.get("lora_name", "")),
                "strength_model": float(la.get("start", 0)),
                "strength_clip": float(la.get("start", 0)),
            })
    if lb.get("lora_name"):
        found = any(x.get("node_id") == str(lb.get("node_id")) for x in meta["loras"])
        if not found:
            meta["loras"].append({
                "node_id": str(lb.get("node_id", "16")),
                "lora_name": lb.get("lora_name"),
                "short_name": lb.get("short_name") or _short_lora(lb.get("lora_name", "")),
                "strength_model": float(lb.get("start", 0)),
                "strength_clip": float(lb.get("start", 0)),
            })
    return {
        **summary,
        "type": "batch",
        "id": summary.get("batch_id"),
        "meta": meta,
        "task_name": rc.get("task_name"),
        "strategy_summary": rc.get("strategy_summary"),
    }


def _list_single_summaries(limit: int) -> list[dict]:
    root = OUTPUT_DIR / SINGLE_OUTPUT_PREFIX
    if not root.is_dir():
        return []
    dirs = sorted(
        [p for p in root.iterdir() if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    out = []
    for d in dirs[: limit * 2]:
        item = _load_single_record(d.name)
        if item:
            out.append(item)
        if len(out) >= limit:
            break
    return out


def _matches_filters(
    entry: dict,
    *,
    checkpoint: str | None,
    lora_name: str | None,
    lora_weight: float | None,
    lora_node: str | None,
) -> bool:
    meta = entry.get("meta") or {}
    if checkpoint and (meta.get("checkpoint") or "") != checkpoint:
        return False
    loras = meta.get("loras") or []
    if lora_name or lora_weight is not None or lora_node:
        matched = False
        for l in loras:
            if lora_node and str(l.get("node_id")) != str(lora_node):
                continue
            if lora_name and lora_name not in str(l.get("lora_name", "")):
                continue
            if lora_weight is not None:
                sm = float(l.get("strength_model", -1))
                if abs(sm - lora_weight) > 0.051:
                    continue
            matched = True
            break
        if not matched and (lora_name or lora_weight is not None or lora_node):
            return False
    return True


def list_history(
    limit: int = 80,
    *,
    checkpoint: str | None = None,
    lora_name: str | None = None,
    lora_weight: float | None = None,
    lora_node: str | None = None,
    record_type: str | None = None,
) -> list[dict]:
    """合并单抽与批量摘要，按时间倒序。"""
    pool: list[dict] = []
    if record_type != "batch":
        pool.extend(_list_single_summaries(limit))
    if record_type != "single":
        for s in batch_service.list_batches(limit=limit * 2):
            pool.append(_batch_to_timeline(s))

    pool = [
        e
        for e in pool
        if _matches_filters(
            e,
            checkpoint=checkpoint or None,
            lora_name=lora_name or None,
            lora_weight=lora_weight,
            lora_node=lora_node or None,
        )
    ]
    pool.sort(key=lambda e: _parse_iso(e.get("started_at")), reverse=True)
    return pool[:limit]


def get_filter_options(limit: int = 200) -> dict:
    """汇总可筛选的 Checkpoint / LoRA / 权重。"""
    checkpoints: set[str] = set()
    lora_map: dict[str, set[float]] = {}

    for entry in list_history(limit=limit, record_type=None):
        meta = entry.get("meta") or {}
        ck = meta.get("checkpoint")
        if ck:
            checkpoints.add(str(ck))
        for l in meta.get("loras") or []:
            name = str(l.get("lora_name") or "")
            if not name:
                continue
            lora_map.setdefault(name, set()).add(round(float(l.get("strength_model", 0)), 2))

    loras = [
        {
            "lora_name": name,
            "short_name": _short_lora(name),
            "weights": sorted(weights),
        }
        for name, weights in sorted(lora_map.items(), key=lambda x: x[0].lower())
    ]
    return {
        "checkpoints": sorted(checkpoints),
        "loras": loras,
    }


def get_batch_detail(batch_id: str) -> dict | None:
    entry = batch_service.get_batch(batch_id)
    if not entry:
        return None
    rc = batch_service._read_run_config(batch_id) or {}
    summary = {
        "batch_id": batch_id,
        "workflow_id": entry.get("workflow_id"),
        "status": entry.get("status"),
        "started_at": entry.get("started_at"),
        "finished_at": entry.get("finished_at"),
        "grid": entry.get("plan", {}).get("grid"),
        "completed": entry.get("completed"),
        "total": entry.get("total"),
    }
    batch_meta = _batch_to_timeline(summary).get("meta")
    items = entry.get("items") or []
    wid = entry.get("workflow_id") or ""
    for item in items:
        snap = dict(item.get("workflow_snapshot") or {})
        snap["item_index"] = item.get("index")
        snap["item_seed"] = item.get("seed")
        item["meta"] = extract_meta_from_overrides(
            wid,
            item.get("overrides") or {},
            workflow_snapshot=snap,
        )
    return {
        **entry,
        "items": items,
        "type": "batch",
        "run_config": rc,
        "meta": batch_meta,
        "task_name": rc.get("task_name"),
        "strategy_summary": rc.get("strategy_summary"),
    }


def get_single_detail(prompt_id: str) -> dict | None:
    path = _record_path(prompt_id)
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            rec = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    try_finish_single_record(prompt_id)
    try:
        with open(path, encoding="utf-8") as f:
            rec = json.load(f)
    except (OSError, json.JSONDecodeError):
        pass
    item = _single_to_timeline(rec)
    if not item:
        return None
    snap = rec.get("workflow_snapshot") or {}
    meta = extract_meta_from_overrides(
        rec.get("workflow_id") or item.get("workflow_id") or "",
        rec.get("overrides") or snap.get("overrides") or {},
        workflow_snapshot=snap,
    )
    return {**rec, **item, "meta": meta}


def delete_single_record(prompt_id: str) -> dict:
    """删除单抽历史目录与输出图。"""
    import shutil

    from job_service import safe_delete_image_file

    path = _record_path(prompt_id)
    rec: dict | None = None
    if path.is_file():
        try:
            with open(path, encoding="utf-8") as f:
                rec = json.load(f)
        except (OSError, json.JSONDecodeError):
            rec = None
    deleted_files: list[str] = []
    for img in (rec or {}).get("images") or []:
        try:
            if safe_delete_image_file(
                img.get("filename", ""),
                img.get("subfolder", ""),
                img.get("type", "output"),
            ):
                deleted_files.append(img["filename"])
        except (OSError, ValueError):
            pass
    try:
        comfy_client.delete_history(prompt_id)
    except RuntimeError:
        pass
    out_dir = _single_dir(prompt_id)
    if out_dir.is_dir():
        shutil.rmtree(out_dir, ignore_errors=True)
    log.info("已删除单抽历史 prompt_id=%s files=%d", prompt_id, len(deleted_files))
    return {"ok": True, "prompt_id": prompt_id, "deleted_files": deleted_files}


def delete_batch_record(batch_id: str) -> dict:
    """删除整批历史（含 manifest 目录）。"""
    return batch_service.delete_batch(batch_id)


def delete_batch_items(batch_id: str, indices: list[int]) -> dict:
    """删除批量中的指定格子。"""
    return batch_service.delete_batch_items(batch_id, indices)
