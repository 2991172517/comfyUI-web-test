"""任务计划：串行执行多个批量任务（每步一份 batch 配置）。"""
from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import COMFYUI_ROOT, PROJECT_ROOT

import batch_service
import batch_store

log = logging.getLogger("custom_project.campaign")

CAMPAIGNS_DIR = PROJECT_ROOT / "output" / "campaigns"
_campaigns: dict[str, dict] = {}
_lock = threading.Lock()


def _campaign_path(campaign_id: str) -> Path:
    return CAMPAIGNS_DIR / campaign_id


def _save_campaign(entry: dict) -> None:
    path = _campaign_path(entry["campaign_id"])
    path.mkdir(parents=True, exist_ok=True)
    with open(path / "campaign.json", "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=2, ensure_ascii=False)


def _load_campaign(campaign_id: str) -> dict | None:
    p = _campaign_path(campaign_id) / "campaign.json"
    if not p.is_file():
        return _campaigns.get(campaign_id)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def list_campaigns(limit: int = 50) -> list[dict]:
    items = []
    if CAMPAIGNS_DIR.is_dir():
        for d in sorted(CAMPAIGNS_DIR.iterdir(), reverse=True):
            if not d.is_dir():
                continue
            meta = d / "campaign.json"
            if meta.is_file():
                with open(meta, encoding="utf-8") as f:
                    c = json.load(f)
                items.append(_summary(c))
            if len(items) >= limit:
                break
    with _lock:
        for c in _campaigns.values():
            if not any(x["campaign_id"] == c["campaign_id"] for x in items):
                items.append(_summary(c))
    return items[:limit]


def _summary(c: dict) -> dict:
    tasks = c.get("tasks") or []
    done = sum(1 for t in tasks if t.get("status") == "completed")
    return {
        "campaign_id": c.get("campaign_id"),
        "name": c.get("name"),
        "status": c.get("status"),
        "task_count": len(tasks),
        "completed_tasks": done,
        "created_at": c.get("created_at"),
        "message": c.get("message"),
    }


def get_campaign(campaign_id: str) -> dict | None:
    with _lock:
        if campaign_id in _campaigns:
            return _campaigns[campaign_id]
    return _load_campaign(campaign_id)


def create_campaign(name: str, tasks: list[dict] | None = None) -> dict:
    cid = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    normalized = []
    for i, t in enumerate(tasks or []):
        normalized.append({
            "task_id": t.get("task_id") or f"t{i + 1:02d}",
            "label": t.get("label") or f"任务 {i + 1}",
            "workflow_id": t.get("workflow_id", ""),
            "batch_payload": t.get("batch_payload") or {},
            "status": "pending",
            "batch_id": None,
            "error": None,
        })
    entry = {
        "campaign_id": cid,
        "name": name or cid,
        "status": "idle",
        "tasks": normalized,
        "current_task_index": 0,
        "message": "已创建",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cancel_requested": False,
    }
    with _lock:
        _campaigns[cid] = entry
    _save_campaign(entry)
    return entry


def _update_campaign(campaign_id: str, **patch) -> dict | None:
    entry = get_campaign(campaign_id)
    if not entry:
        return None
    entry.update(patch)
    with _lock:
        _campaigns[campaign_id] = entry
    _save_campaign(entry)
    return entry


def cancel_campaign(campaign_id: str) -> dict:
    entry = _update_campaign(campaign_id, cancel_requested=True, status="cancelling", message="取消中…")
    if not entry:
        return {"ok": False, "error": "任务计划不存在"}
    for t in entry.get("tasks") or []:
        bid = t.get("batch_id")
        if bid and t.get("status") == "running":
            batch_store.set_cancelled(bid)
    return {"ok": True, "campaign_id": campaign_id}


def run_campaign(campaign_id: str) -> None:
    entry = get_campaign(campaign_id)
    if not entry:
        return
    _update_campaign(
        campaign_id,
        status="running",
        message="任务计划执行中…",
        cancel_requested=False,
    )
    tasks = entry.get("tasks") or []
    for idx, task in enumerate(tasks):
        if entry.get("cancel_requested"):
            _update_campaign(campaign_id, status="cancelled", message="已取消")
            return
        entry = get_campaign(campaign_id) or entry
        if entry.get("cancel_requested"):
            _update_campaign(campaign_id, status="cancelled", message="已取消")
            return

        wid = task.get("workflow_id")
        payload = dict(task.get("batch_payload") or {})
        if not wid:
            task["status"] = "failed"
            task["error"] = "缺少 workflow_id"
            continue

        _update_campaign(
            campaign_id,
            current_task_index=idx,
            message=f"执行 {task.get('label')} ({idx + 1}/{len(tasks)})…",
        )
        task["status"] = "running"
        entry["tasks"][idx] = task
        _save_campaign(entry)

        try:
            plan = batch_service.build_grid_plan(wid, payload)
            batch_id = plan["batch_id"]
            payload["batch_id"] = batch_id
            task["batch_id"] = batch_id
            batch_store.create(batch_id, {
                "batch_id": batch_id,
                "workflow_id": wid,
                "status": "running",
                "plan": plan,
                "completed": 0,
                "total": plan["grid"]["total"],
                "items": [],
                "error": None,
                "cancel_requested": False,
                "campaign_id": campaign_id,
            })
            batch_service.persist_batch_start(plan, payload)
            batch_service.run_batch(wid, payload)
            final = batch_store.get(batch_id) or {}
            task["status"] = final.get("status", "completed")
            task["error"] = final.get("error")
        except Exception as exc:
            log.exception("campaign task failed %s", campaign_id)
            task["status"] = "failed"
            task["error"] = str(exc)

        entry = get_campaign(campaign_id) or entry
        entry["tasks"][idx] = task
        _save_campaign(entry)

        if task["status"] == "failed" and payload.get("stop_on_error", True):
            _update_campaign(campaign_id, status="failed", message=task.get("error") or "任务失败")
            return

    _update_campaign(campaign_id, status="completed", message="任务计划已完成")


def start_campaign_async(campaign_id: str) -> None:
    thread = threading.Thread(
        target=run_campaign,
        args=(campaign_id,),
        daemon=True,
        name=f"campaign-{campaign_id}",
    )
    thread.start()
