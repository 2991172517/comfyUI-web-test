"""已保存的 LoRA 批量任务配置（任务计划库）。"""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import PROJECT_ROOT

import batch_service
import logging

log = logging.getLogger("custom_project.batch_task")

TASKS_PATH = PROJECT_ROOT / "config" / "batch_tasks.json"
_run_lock = threading.Lock()


def _empty_store() -> dict:
    return {"schema_version": 1, "tasks": []}


def load_store() -> dict:
    if not TASKS_PATH.is_file():
        return _empty_store()
    with open(TASKS_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_store(data: dict) -> dict:
    TASKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TASKS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data


def _execution_summary(t: dict) -> dict:
    ex = t.get("execution") or {}
    return {
        "status": ex.get("status", "pending"),
        "batch_ids": list(ex.get("batch_ids") or []),
        "last_batch_id": ex.get("last_batch_id"),
        "executed_at": ex.get("executed_at"),
        "last_error": ex.get("last_error"),
    }


def list_tasks() -> list[dict]:
    store = load_store()
    items = []
    for t in store.get("tasks") or []:
        payload = t.get("batch_payload") or {}
        ex = _execution_summary(t)
        items.append({
            "task_id": t.get("task_id"),
            "name": t.get("name", ""),
            "description": t.get("description", ""),
            "workflow_id": t.get("workflow_id", ""),
            "workflow_display_name": t.get("workflow_display_name", ""),
            "planned_total": t.get("planned_total", 0),
            "created_at": t.get("created_at"),
            "updated_at": t.get("updated_at"),
            "has_batch_prompts": bool(payload.get("batch_prompts")),
            **ex,
        })
    return items


def get_task(task_id: str) -> dict | None:
    for t in load_store().get("tasks") or []:
        if str(t.get("task_id")) == str(task_id):
            return t
    return None


def _update_task_execution(task_id: str, **fields: Any) -> None:
    store = load_store()
    now = datetime.now(timezone.utc).isoformat()
    for t in store.get("tasks") or []:
        if str(t.get("task_id")) != str(task_id):
            continue
        ex = dict(t.get("execution") or {})
        ex.update(fields)
        t["execution"] = ex
        t["updated_at"] = now
        save_store(store)
        return


def mark_task_running(task_id: str, batch_id: str) -> None:
    task = get_task(task_id)
    ex = (task or {}).get("execution") or {}
    batch_ids = list(ex.get("batch_ids") or [])
    if batch_id not in batch_ids:
        batch_ids.append(batch_id)
    _update_task_execution(
        task_id,
        status="running",
        last_batch_id=batch_id,
        batch_ids=batch_ids,
        last_error=None,
    )


def mark_task_completed(task_id: str, batch_id: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    task = get_task(task_id)
    ex = (task or {}).get("execution") or {}
    batch_ids = list(ex.get("batch_ids") or [])
    if batch_id not in batch_ids:
        batch_ids.append(batch_id)
    _update_task_execution(
        task_id,
        status="completed",
        last_batch_id=batch_id,
        batch_ids=batch_ids,
        executed_at=now,
        last_error=None,
    )


def mark_task_failed(task_id: str, batch_id: str | None, error: str) -> None:
    fields: dict[str, Any] = {"status": "failed", "last_error": str(error)[:500]}
    if batch_id:
        fields["last_batch_id"] = batch_id
    _update_task_execution(task_id, **fields)


def save_task(
    name: str,
    workflow_id: str,
    batch_payload: dict,
    *,
    workflow_display_name: str = "",
    description: str = "",
    planned_total: int = 0,
    task_id: str | None = None,
) -> dict:
    store = load_store()
    tasks = store.setdefault("tasks", [])
    now = datetime.now(timezone.utc).isoformat()
    tid = task_id or uuid.uuid4().hex[:10]
    entry = {
        "task_id": tid,
        "name": (name or workflow_id).strip(),
        "description": (description or "").strip(),
        "workflow_id": workflow_id,
        "workflow_display_name": workflow_display_name or workflow_id,
        "batch_payload": batch_payload,
        "planned_total": int(planned_total or 0),
        "created_at": now,
        "updated_at": now,
        "execution": {"status": "pending", "batch_ids": [], "last_batch_id": None, "executed_at": None},
    }
    replaced = False
    for i, t in enumerate(tasks):
        if str(t.get("task_id")) == tid:
            entry["created_at"] = t.get("created_at", now)
            entry["execution"] = t.get("execution") or entry["execution"]
            tasks[i] = entry
            replaced = True
            break
    if not replaced:
        tasks.append(entry)
    save_store(store)
    return entry


def delete_task(task_id: str) -> bool:
    store = load_store()
    tasks = store.get("tasks") or []
    new_tasks = [t for t in tasks if str(t.get("task_id")) != str(task_id)]
    if len(new_tasks) == len(tasks):
        raise ValueError(f"任务不存在: {task_id}")
    store["tasks"] = new_tasks
    save_store(store)
    return True


def _run_tasks_worker(task_ids: list[str]) -> None:
    import batch_store

    with _run_lock:
        for tid in task_ids:
            task = get_task(tid)
            if not task:
                continue
            wid = task.get("workflow_id")
            payload = dict(task.get("batch_payload") or {})
            batch_id: str | None = None
            try:
                plan = batch_service.build_grid_plan(wid, payload)
                batch_id = plan["batch_id"]
                payload["batch_id"] = batch_id
                payload["task_id"] = tid
                payload["task_name"] = task.get("name")
                mark_task_running(tid, batch_id)
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
                    "task_id": tid,
                    "task_name": task.get("name"),
                })
                batch_service.persist_batch_start(plan, payload)
                batch_service.run_batch(wid, payload)
                final = batch_store.get(batch_id) or {}
                if final.get("status") == "completed":
                    mark_task_completed(tid, batch_id)
                elif final.get("status") in ("failed", "cancelled"):
                    mark_task_failed(
                        tid,
                        batch_id,
                        final.get("error") or final.get("status") or "批量未完成",
                    )
                else:
                    mark_task_completed(tid, batch_id)
            except Exception as exc:
                log.exception("batch task failed task_id=%s", tid)
                mark_task_failed(tid, batch_id, str(exc))


def run_tasks_async(task_ids: list[str]) -> dict:
    if not task_ids:
        raise ValueError("请至少选择一个任务")
    thread = threading.Thread(
        target=_run_tasks_worker,
        args=(list(task_ids),),
        daemon=True,
        name=f"batch-tasks-{len(task_ids)}",
    )
    thread.start()
    return {
        "ok": True,
        "task_ids": list(task_ids),
        "count": len(task_ids),
        "message": f"已开始串行执行 {len(task_ids)} 个批量任务",
    }
