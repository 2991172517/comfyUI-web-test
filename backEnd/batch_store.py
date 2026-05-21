"""内存中的批量任务状态。"""
import threading
from typing import Any

_lock = threading.Lock()
_batches: dict[str, dict[str, Any]] = {}


def create(batch_id: str, data: dict) -> None:
    with _lock:
        _batches[batch_id] = data


def get(batch_id: str) -> dict | None:
    with _lock:
        entry = _batches.get(batch_id)
        return dict(entry) if entry else None


def update(batch_id: str, **fields: Any) -> None:
    with _lock:
        if batch_id not in _batches:
            return
        _batches[batch_id].update(fields)


def set_cancelled(batch_id: str) -> None:
    update(batch_id, cancel_requested=True)


def is_cancelled(batch_id: str) -> bool:
    with _lock:
        return bool(_batches.get(batch_id, {}).get("cancel_requested"))
