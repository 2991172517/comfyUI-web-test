"""向前端推送 ComfyUI 任务进度（WebSocket）。"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

log = logging.getLogger("custom_project.job_events")

_connections: set[Any] = set()
_main_loop: asyncio.AbstractEventLoop | None = None


def attach_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


def register(ws: Any) -> None:
    _connections.add(ws)
    if _main_loop is None:
        try:
            attach_loop(asyncio.get_running_loop())
        except RuntimeError:
            pass


def unregister(ws: Any) -> None:
    _connections.discard(ws)


def _serialize_job(prompt_id: str, state: dict[str, Any]) -> dict[str, Any]:
    progress = state.get("progress")
    if isinstance(progress, dict):
        pct = progress.get("value")
        if progress.get("max"):
            pct = int(round(100 * (progress.get("value") or 0) / progress["max"]))
    elif progress is not None:
        pct = int(progress)
    else:
        pct = None
    return {
        "type": "job",
        "prompt_id": prompt_id,
        "status": state.get("status"),
        "current_node": state.get("current_node"),
        "progress": pct,
        "completed_nodes": list(state.get("completed_nodes") or []),
        "execution_track_nodes": list(state.get("execution_track_nodes") or []),
        "error": state.get("error"),
    }


def _serialize_batch(batch_id: str, entry: dict[str, Any]) -> dict[str, Any]:
    total = int(entry.get("total") or 0)
    completed = int(entry.get("completed") or 0)
    pct = int(round(100 * completed / total)) if total > 0 else 0
    return {
        "type": "batch",
        "batch_id": batch_id,
        "status": entry.get("status"),
        "completed": completed,
        "total": total,
        "progress": pct,
        "current_index": entry.get("current_index"),
        "current_label": entry.get("current_label"),
        "current_prompt_id": entry.get("current_prompt_id"),
        "message": entry.get("message"),
        "error": entry.get("error"),
    }


async def _send_json(ws: Any, payload: dict[str, Any]) -> None:
    await ws.send_text(json.dumps(payload, ensure_ascii=False))


async def send_snapshot(ws: Any) -> None:
    """新连接时推送当前在跑任务快照。"""
    import batch_store
    import ws_tracker

    jobs = ws_tracker.list_tracker_states()
    for pid, st in jobs.items():
        if st.get("status") in ("pending", "in_progress", "finalizing"):
            await _send_json(ws, _serialize_job(pid, st))

    import batch_service

    for summary in batch_service.list_batches(limit=20):
        bid = summary.get("batch_id")
        if not bid:
            continue
        entry = batch_store.get(bid)
        if entry and entry.get("status") in ("running", "cancelling"):
            await _send_json(ws, _serialize_batch(bid, entry))


async def broadcast_async(payload: dict[str, Any]) -> None:
    if not _connections:
        return
    dead: list[Any] = []
    for ws in list(_connections):
        try:
            await _send_json(ws, payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        unregister(ws)


def _schedule_broadcast(payload: dict[str, Any]) -> None:
    loop = _main_loop
    if loop is None or not _connections:
        return
    try:
        asyncio.run_coroutine_threadsafe(broadcast_async(payload), loop)
    except Exception as exc:
        log.debug("broadcast schedule failed: %s", exc)


def broadcast_job_sync(prompt_id: str, state: dict[str, Any] | None = None) -> None:
    import ws_tracker

    st = state if state is not None else ws_tracker.get_tracker_state(prompt_id)
    _schedule_broadcast(_serialize_job(prompt_id, st))


def broadcast_batch_sync(batch_id: str, entry: dict[str, Any] | None = None) -> None:
    import batch_store

    ent = entry if entry is not None else batch_store.get(batch_id)
    if not ent:
        return
    _schedule_broadcast(_serialize_batch(batch_id, ent))
