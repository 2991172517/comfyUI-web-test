"""提示词 tag 权重解析（与前端 promptTagWeight.js 对齐，供词库 resolve 回退匹配）。"""
from __future__ import annotations

import re

WEIGHT_MIN = 0.05
WEIGHT_MAX = 2.0
WEIGHT_STEP = 0.05
PAREN_DEFAULT = 1.1
BRACKET_FACTOR = 0.9


def clamp_weight(w: float) -> float:
    if not isinstance(w, (int, float)) or w != w:
        return 1.0
    w = float(w)
    stepped = round(w / WEIGHT_STEP) * WEIGHT_STEP
    return min(WEIGHT_MAX, max(WEIGHT_MIN, stepped))


def can_adjust_weight(value: str) -> bool:
    t = (value or "").strip()
    if not t or len(t) > 120:
        return False
    return "," not in t and "，" not in t


def parse_tag_weight(value: str) -> tuple[str, float]:
    t = (value or "").strip()
    if not t:
        return "", 1.0

    weight = 1.0

    while t.startswith("[") and t.endswith("]"):
        inner = t[1:-1].strip()
        if not inner or "[" in inner:
            break
        weight *= BRACKET_FACTOR
        t = inner

    while t.startswith("(") and t.endswith(")"):
        inner = t[1:-1].strip()
        if not inner:
            break
        explicit = re.match(r"^(.+):([\d.]+)$", inner)
        if explicit and "(" not in explicit.group(1):
            t = explicit.group(1).strip()
            weight *= float(explicit.group(2))
            break
        weight *= PAREN_DEFAULT
        t = inner

    return t, clamp_weight(weight)


def lookup_key_for_vocabulary(value: str) -> str:
    if not can_adjust_weight(value):
        return (value or "").strip()
    base, _ = parse_tag_weight(value)
    return base or (value or "").strip()
