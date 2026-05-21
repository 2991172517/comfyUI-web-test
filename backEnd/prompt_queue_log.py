"""提示词合并与 ComfyUI 入队专用日志（单文件，便于对照随机抽取与最终提交）。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import PROJECT_ROOT

LOG_PATH = PROJECT_ROOT / "logs" / "prompt_queue.log"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fmt_picks(picks: list[dict] | None) -> str:
    if not picks:
        return "(无)"
    lines = []
    for p in picks:
        lines.append(
            f"  - [{p.get('group_name', p.get('group_id', '?'))}] "
            f"{p.get('text', '')} (mode={p.get('mode', '')})"
        )
    return "\n".join(lines)


def _fmt_encode_nodes(prompt: dict, node_ids: dict[str, str]) -> str:
    parts = []
    for side, nid in node_ids.items():
        node = prompt.get(str(nid), prompt.get(nid, {}))
        text = node.get("inputs", {}).get("text", "")
        if isinstance(text, list):
            text = "(链接，非字符串)"
        else:
            text = str(text)
        parts.append(f"--- CLIP #{nid} ({side}) len={len(text)} ---\n{text}")
    return "\n\n".join(parts) if parts else "(无 CLIP 文本节点)"


def append_event(
    event: str,
    *,
    workflow_id: str = "",
    source: str = "",
    extra: dict[str, Any] | None = None,
) -> Path:
    """追加一条结构化记录到 logs/prompt_queue.log。"""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    block = [
        "",
        "=" * 78,
        f"[{_now()}] {event}",
        f"  workflow_id: {workflow_id}",
        f"  source: {source}",
    ]
    if extra:
        for key, val in extra.items():
            if key.startswith("_") and key.endswith("_multiline"):
                label = key[1:].replace("_multiline", "")
                block.append(f"  {label}:")
                block.append(str(val))
            elif isinstance(val, (dict, list)):
                block.append(f"  {key}: {json.dumps(val, ensure_ascii=False)}")
            else:
                block.append(f"  {key}: {val}")
    block.append("")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write("\n".join(block))
    return LOG_PATH


def log_prompt_merge(
    *,
    workflow_id: str,
    source: str,
    index: int = 0,
    seed: int | None = None,
    merged: dict[str, str] | None = None,
    pick_records: list[dict] | None = None,
    debug: dict[str, str] | None = None,
    encode_node_ids: dict[str, str] | None = None,
    should_apply: bool | None = None,
) -> None:
    pos = (merged or {}).get("positive", "")
    neg = (merged or {}).get("negative", "")
    append_event(
        "PROMPT_MERGE",
        workflow_id=workflow_id,
        source=source,
        extra={
            "index": index,
            "seed": seed,
            "should_apply": should_apply,
            "debug": debug or {},
            "encode_nodes": encode_node_ids or {},
            "pick_count": len(pick_records or []),
            "picks_multiline": _fmt_picks(pick_records),
            "positive_len": len(pos),
            "negative_len": len(neg),
            "positive_head": pos[:160],
            "positive_tail": pos[-160:] if pos else "",
            "_positive_full_multiline": pos,
            "_negative_full_multiline": neg,
        },
    )


def log_comfyui_queue(
    *,
    workflow_id: str,
    source: str,
    prompt_id: str = "",
    batch_id: str = "",
    cell_index: int | None = None,
    apply_defaults: bool = True,
    layers_applied: bool = False,
    pick_records: list[dict] | None = None,
    overrides_clip: dict[str, str] | None = None,
    final_prompt: dict | None = None,
    encode_node_ids: dict[str, str] | None = None,
) -> None:
    """记录即将提交 ComfyUI 的 CLIP 文本（overrides 与 build_api_prompt 之后）。"""
    ov = overrides_clip or {}
    append_event(
        "COMFYUI_QUEUE",
        workflow_id=workflow_id,
        source=source,
        extra={
            "prompt_id": prompt_id,
            "batch_id": batch_id,
            "cell_index": cell_index,
            "apply_defaults": apply_defaults,
            "layers_applied": layers_applied,
            "pick_count": len(pick_records or []),
            "picks_multiline": _fmt_picks(pick_records),
            "overrides_clip3_len": len(ov.get("3", ov.get(3, ""))),
            "overrides_clip4_len": len(ov.get("4", ov.get(4, ""))),
            "_overrides_clip_multiline": "\n".join(
                f"#{nid}: {txt[:200]}..." if len(txt) > 200 else f"#{nid}: {txt}"
                for nid, txt in ov.items()
            ),
            "_final_prompt_clip_multiline": _fmt_encode_nodes(
                final_prompt or {},
                encode_node_ids or {},
            ),
        },
    )
