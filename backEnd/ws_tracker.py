"""
在服务端连接 ComfyUI WebSocket（与 script_examples/websockets_api_example.py 相同方式），
避免浏览器 Origin 与 127.0.0.1:8188 不一致导致 403。
"""
import json
import logging
import threading
from typing import Any

from config import COMFYUI_URL

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_states: dict[str, dict[str, Any]] = {}


def _ws_url() -> str:
    base = COMFYUI_URL.rstrip("/")
    if base.startswith("https://"):
        return base.replace("https://", "wss://", 1) + "/ws"
    return base.replace("http://", "ws://", 1) + "/ws"


def get_tracker_state(prompt_id: str) -> dict[str, Any]:
    with _lock:
        return dict(_states.get(prompt_id, {}))


def clear_tracker_state(prompt_id: str) -> None:
    with _lock:
        _states.pop(prompt_id, None)


def _update(prompt_id: str, **fields: Any) -> None:
    with _lock:
        entry = _states.setdefault(prompt_id, {})
        entry.update(fields)


def start_tracking(client_id: str, prompt_id: str) -> None:
    """后台线程监听 ComfyUI WS，更新任务进度。"""

    def run() -> None:
        try:
            import websocket
        except ImportError:
            logger.warning("websocket-client 未安装，进度追踪不可用")
            return

        _update(
            prompt_id,
            status="pending",
            current_node=None,
            progress=None,
            error=None,
        )

        ws = websocket.WebSocket()
        try:
            ws.connect(f"{_ws_url()}?clientId={client_id}")
            ws.settimeout(1.0)
        except Exception as exc:
            logger.warning("连接 ComfyUI WebSocket 失败: %s", exc)
            _update(prompt_id, status="unknown", error=str(exc))
            return

        try:
            while True:
                try:
                    raw = ws.recv()
                except Exception:
                    continue

                if isinstance(raw, bytes):
                    continue

                try:
                    message = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                msg_type = message.get("type")
                data = message.get("data") or {}

                if msg_type == "executing":
                    if data.get("prompt_id") not in (None, prompt_id):
                        continue
                    node = data.get("node")
                    if node is None:
                        _update(
                            prompt_id,
                            status="finalizing",
                            current_node=None,
                        )
                        break
                    _update(
                        prompt_id,
                        status="in_progress",
                        current_node=str(node),
                    )

                elif msg_type == "progress":
                    if data.get("prompt_id") not in (None, prompt_id):
                        continue
                    max_val = data.get("max") or 0
                    value = data.get("value") or 0
                    if max_val > 0:
                        _update(
                            prompt_id,
                            status="in_progress",
                            progress=int(round(100 * value / max_val)),
                        )

                elif msg_type == "execution_error":
                    if data.get("prompt_id") not in (None, prompt_id):
                        continue
                    _update(
                        prompt_id,
                        status="failed",
                        error=data.get("exception_message") or "执行出错",
                    )
                    break

        finally:
            try:
                ws.close()
            except Exception:
                pass

    thread = threading.Thread(target=run, daemon=True, name=f"ws-track-{prompt_id[:8]}")
    thread.start()
