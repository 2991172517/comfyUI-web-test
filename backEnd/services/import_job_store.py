"""模型导入任务进度（内存）。"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any

_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}


def create_job() -> str:
    job_id = uuid.uuid4().hex[:12]
    with _lock:
        _jobs[job_id] = {
            "jobId": job_id,
            "status": "pending",
            "phase": "pending",
            "message": "等待开始…",
            "progress": 0,
            "previewIndex": 0,
            "previewTotal": 0,
            "result": None,
            "error": None,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }
    return job_id


def patch_job(job_id: str, **fields: Any) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        job.update(fields)
        job["updatedAt"] = datetime.now(timezone.utc).isoformat()


def get_job(job_id: str) -> dict[str, Any] | None:
    with _lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None
