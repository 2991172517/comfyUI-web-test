"""提示词合并：全局 / 批量固定 / 随机组片段。"""
from __future__ import annotations

from typing import Any


def merge_text_append(
    base: str,
    prefix: str = "",
    suffix: str = "",
    extra_lines: list[str] | None = None,
    *,
    extras_before_base: bool = False,
) -> str:
    """合并提示词。extras_before_base=True 时随机片段插在 base 之前（便于全局参考优先生效）。"""
    parts: list[str] = []
    if prefix.strip():
        parts.append(prefix.strip())
    extras = [str(line).strip() for line in (extra_lines or []) if str(line).strip()]
    base = (base or "").strip()
    if extras_before_base:
        parts.extend(extras)
        if base:
            parts.append(base)
    else:
        if base:
            parts.append(base)
        parts.extend(extras)
    if suffix.strip():
        parts.append(suffix.strip())
    return "\n".join(parts)


def resolve_encode_nodes(cfg: dict) -> dict[str, str]:
    """side -> node_id"""
    out: dict[str, str] = {}
    for side in ("positive", "negative"):
        spec = cfg.get(side) or {}
        nid = str(spec.get("node_id", ""))
        if nid:
            out[side] = nid
    return out


def patch_prompt_encode_text(
    prompt: dict,
    encode_nodes: dict[str, str],
    side: str,
    text: str,
    field: str = "text",
) -> None:
    nid = encode_nodes.get(side)
    if not nid or nid not in prompt:
        return
    inputs = prompt[nid].setdefault("inputs", {})
    if field in inputs and isinstance(inputs[field], list):
        return
    inputs[field] = text
