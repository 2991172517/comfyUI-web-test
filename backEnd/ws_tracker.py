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


def mark_cancelled(prompt_id: str) -> None:
    """用户取消单图生成时标记状态，供 get_job_detail 立即返回 cancelled。"""
    _update(
        prompt_id,
        status="cancelled",
        current_node=None,
        progress=None,
        error=None,
    )


def register_prompt_watch(prompt_id: str, node_ids: list[str] | None) -> None:
    """登记本任务中的 CLIPTextEncode 节点，供 WS 捕捉「已执行提示词阶段」。"""
    ids = {str(n).strip() for n in (node_ids or []) if str(n).strip()}
    _update(
        prompt_id,
        prompt_watch_nodes=ids,
        prompt_stage_reached=False,
        prompt_stage_node=None,
    )


def _note_executing_node(prompt_id: str, node: str) -> None:
    with _lock:
        entry = _states.get(prompt_id)
        if not entry:
            return
        watch = entry.get("prompt_watch_nodes") or set()
        if str(node) in watch:
            entry["prompt_stage_reached"] = True
            entry["prompt_stage_node"] = str(node)


def _update(prompt_id: str, **fields: Any) -> None:
    with _lock:
        entry = _states.setdefault(prompt_id, {})
        entry.update(fields)


def start_tracking(
    client_id: str,
    prompt_id: str,
    prompt_node_ids: list[str] | None = None,
) -> None:
    """后台线程监听 ComfyUI WS，更新任务进度。"""
    register_prompt_watch(prompt_id, prompt_node_ids)

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
        if prompt_node_ids:
            register_prompt_watch(prompt_id, prompt_node_ids)

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
                    node_str = str(node)
                    _update(
                        prompt_id,
                        status="in_progress",
                        current_node=node_str,
                    )
                    _note_executing_node(prompt_id, node_str)

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
