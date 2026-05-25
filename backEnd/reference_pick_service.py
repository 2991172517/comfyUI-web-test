"""随机参考词组：从组内解析词条并抽取（逗号分隔，供 batch / 全局参考复用）。"""
from __future__ import annotations

import random
import re
from typing import Any

# 半角/全角逗号
_COMMA_RE = re.compile(r"[,，]\s*")
# 旧配置可能用斜杠；仅在没有逗号时兼容
_SLASH_RE = re.compile(r"\s*/\s*")

# 前端 Tag 编辑器双击屏蔽时写入此前缀；生图合并时跳过
MUTED_TOKEN_PREFIX = "!"


def is_muted_prompt_token(token: str) -> bool:
    return str(token or "").strip().startswith(MUTED_TOKEN_PREFIX)


def strip_muted_prefix(token: str) -> str:
    t = str(token or "").strip()
    if is_muted_prompt_token(t):
        return t[len(MUTED_TOKEN_PREFIX) :].strip()
    return t


def active_prompt_tokens(tokens: list[str]) -> list[str]:
    """去掉屏蔽词条，供随机抽取 / 合并入 CLIP。"""
    out: list[str] = []
    for raw in tokens:
        t = str(raw).strip()
        if not t or is_muted_prompt_token(t):
            continue
        out.append(t)
    return out


def _active_token_indices(tokens: list[str]) -> list[int]:
    return [i for i, raw in enumerate(tokens) if str(raw).strip() and not is_muted_prompt_token(raw)]


def split_prompt_tokens(text: str) -> list[str]:
    """
    将一行提示拆成词条列表。
    优先按逗号（, ，）分隔；若无逗号且含 / 则按斜杠兼容旧数据。
    """
    s = str(text or "").strip()
    if not s:
        return []
    if _COMMA_RE.search(s):
        return [p.strip() for p in _COMMA_RE.split(s) if p.strip()]
    if "/" in s:
        return [p.strip() for p in _SLASH_RE.split(s) if p.strip()]
    return [s]


def join_prompt_tokens(tokens: list[str]) -> str:
    """合并为提交给 CLIP 的逗号分隔片段（与常见 Danbooru 写法一致）。"""
    return ", ".join(t for t in tokens if str(t).strip())


def flatten_prompt_to_tokens(text: str) -> list[str]:
    """多行 + 行内逗号/斜杠 → 有序词条列表（O(n) 扫描）。"""
    tokens: list[str] = []
    for line in str(text or "").replace("\r\n", "\n").split("\n"):
        tokens.extend(split_prompt_tokens(line))
    return tokens


def _token_dedupe_key(token: str) -> str:
    t = strip_muted_prefix(str(token).strip())
    return t.casefold()


def dedupe_prompt_tokens(tokens: list[str]) -> tuple[list[str], int]:
    """保留首次出现顺序；key 为 strip + casefold，O(n)。屏蔽词条（! 前缀）不参与合并。"""
    seen: set[str] = set()
    out: list[str] = []
    removed = 0
    for raw in tokens:
        t = str(raw).strip()
        if not t:
            continue
        if is_muted_prompt_token(t):
            continue
        key = _token_dedupe_key(t)
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        out.append(t)
    return out, removed


def dedupe_prompt_text(text: str) -> tuple[str, int]:
    """合并结果去重后以「, 」提交给 CLIP（与 join_prompt_tokens 一致）。"""
    deduped, removed = dedupe_prompt_tokens(flatten_prompt_to_tokens(text))
    return join_prompt_tokens(deduped), removed


# 底稿过长时，CLIP 对句末 tag 几乎不起作用；自动把随机词前移
_AUTO_PREPEND_RANDOM_MIN_CORE_TOKENS = 48


def merge_deduped_core_with_random(
    core_text: str,
    random_parts: list[str],
    *,
    random_before: bool = False,
) -> tuple[str, int, str]:
    """
    先对底稿/全局/当次全文合并结果去重，再合并随机组抽词。
    返回 (合并文本, 去重移除数, placement: before|after|auto_before)。
    """
    core_tokens, removed = dedupe_prompt_tokens(flatten_prompt_to_tokens(core_text))
    rnd_raw: list[str] = []
    for part in random_parts:
        rnd_raw.extend(split_prompt_tokens(str(part)))
    rnd_tokens, _ = dedupe_prompt_tokens(rnd_raw)
    seen = {_token_dedupe_key(t) for t in core_tokens}
    extra = [t for t in rnd_tokens if _token_dedupe_key(t) not in seen]

    put_random_first = bool(random_before)
    if extra and not put_random_first and len(core_tokens) >= _AUTO_PREPEND_RANDOM_MIN_CORE_TOKENS:
        put_random_first = True
        placement = "auto_before"
    elif put_random_first:
        placement = "before"
    else:
        placement = "after"

    if put_random_first:
        final_tokens = extra + core_tokens
    else:
        final_tokens = core_tokens + extra
    return join_prompt_tokens(final_tokens), removed, placement


PICK_MODES = frozenset({"random", "sequential"})


def _normalize_weight(value: Any, default: float = 1.0) -> float:
    try:
        w = float(value)
    except (TypeError, ValueError):
        w = default
    return max(0.0, w)


def _weights_for_pool(group: dict, pool_len: int) -> list[float]:
    raw = group.get("weights") or []
    weights = [_normalize_weight(raw[i] if i < len(raw) else 1.0) for i in range(pool_len)]
    if not any(w > 0 for w in weights):
        return [1.0] * pool_len
    return weights


def _weights_for_tokens(group: dict, token_count: int) -> list[float]:
    raw = group.get("weights") or []
    if len(raw) == token_count:
        weights = [_normalize_weight(x) for x in raw]
    else:
        weights = [1.0] * token_count
    if not any(w > 0 for w in weights):
        return [1.0] * token_count
    return weights


def _weighted_index(weights: list[float], rng: random.Random) -> int:
    total = sum(weights)
    if total <= 0:
        return rng.randrange(len(weights))
    r = rng.random() * total
    acc = 0.0
    for i, w in enumerate(weights):
        acc += w
        if r <= acc:
            return i
    return len(weights) - 1


def resolve_sequential_group_pick(
    group: dict,
    index: int,
) -> tuple[str, list[str], dict[str, Any]]:
    """按批量序号顺序取词：index 对候选数/词条数取模，超出后从头循环。"""
    pool = [str(p).strip() for p in (group.get("prompts") or []) if str(p).strip()]
    if not pool:
        return "", [], {}

    target = group.get("target", "positive")
    seq_index = int(index or 0)
    base_rec: dict[str, Any] = {
        "group_id": group.get("id"),
        "group_name": group.get("name"),
        "target": target,
        "pick_mode": "sequential",
        "sequence_index": seq_index,
    }

    if len(pool) == 1:
        tokens = active_prompt_tokens(split_prompt_tokens(pool[0]))
        if not tokens:
            return "", [], base_rec
        idx = seq_index % len(tokens)
        chosen = tokens[idx]
        record = {
            **base_rec,
            "mode": "sequential_one_of_tokens",
            "candidate_count": 1,
            "token_index": idx,
            "token_count": len(tokens),
            "tokens": [chosen],
            "text": chosen,
        }
        return chosen, [chosen], record

    idx = seq_index % len(pool)
    line = pool[idx]
    tokens = active_prompt_tokens(split_prompt_tokens(line))
    merged = join_prompt_tokens(tokens)
    record = {
        **base_rec,
        "mode": "sequential_all_tokens_from_candidate",
        "candidate_count": len(pool),
        "candidate_index": idx,
        "candidate_preview": line[:120] + ("…" if len(line) > 120 else ""),
        "tokens": tokens,
        "text": merged,
    }
    return merged, tokens, record


def resolve_random_group_pick(
    group: dict,
    rng: random.Random,
) -> tuple[str, list[str], dict[str, Any]]:
    """
    解析一个随机组的本次抽取。

    - **仅 1 条候选**：在该行的逗号分隔词条中 **随机选 1 个** 加入提示词。
    - **多条候选**：先 **随机选 1 条候选方案**，再将该方案内 **全部** 逗号分隔词条加入提示词。

    返回 (merged_text, token_list, pick_record)。
    """
    pool = [str(p).strip() for p in (group.get("prompts") or []) if str(p).strip()]
    if not pool:
        return "", [], {}

    target = group.get("target", "positive")
    base_rec: dict[str, Any] = {
        "group_id": group.get("id"),
        "group_name": group.get("name"),
        "target": target,
        "pick_mode": "random",
    }

    if len(pool) == 1:
        all_tokens = split_prompt_tokens(pool[0])
        active_idx = _active_token_indices(all_tokens)
        tokens = [all_tokens[i] for i in active_idx]
        if not tokens:
            return "", [], base_rec
        weights = _weights_for_tokens(group, len(all_tokens))
        pick_weights = [weights[i] for i in active_idx]
        idx = _weighted_index(pick_weights, rng)
        chosen = tokens[idx]
        merged = chosen
        record = {
            **base_rec,
            "mode": "one_of_tokens",
            "candidate_count": 1,
            "token_index": idx,
            "token_count": len(tokens),
            "token_weight": pick_weights[idx],
            "tokens": [chosen],
            "text": merged,
        }
        return merged, [chosen], record

    weights = _weights_for_pool(group, len(pool))
    idx = _weighted_index(weights, rng)
    line = pool[idx]
    tokens = active_prompt_tokens(split_prompt_tokens(line))
    merged = join_prompt_tokens(tokens)
    record = {
        **base_rec,
        "mode": "all_tokens_from_candidate",
        "candidate_count": len(pool),
        "candidate_index": idx,
        "candidate_weight": weights[idx],
        "candidate_preview": line[:120] + ("…" if len(line) > 120 else ""),
        "tokens": tokens,
        "text": merged,
    }
    return merged, tokens, record


def resolve_group_pick(
    group: dict,
    *,
    rng: random.Random,
    index: int = 0,
) -> tuple[str, list[str], dict[str, Any]]:
    mode = str(group.get("pick_mode") or "random").strip().lower()
    if mode not in PICK_MODES:
        mode = "random"
    if mode == "sequential":
        return resolve_sequential_group_pick(group, index)
    return resolve_random_group_pick(group, rng)


def resolve_random_bundle_pick(
    group: dict,
    rng: random.Random,
) -> tuple[str, list[str], dict[str, Any]]:
    """随机词串组：每次抽取一整组（组内全部逗号分隔词条加入提示词）。"""
    bundles = list(group.get("bundles") or [])
    if not bundles:
        return "", [], {}

    target = group.get("target", "positive")
    base_rec: dict[str, Any] = {
        "pick_type": "bundle_group",
        "group_id": group.get("id"),
        "group_name": group.get("name"),
        "target": target,
        "pick_mode": "random",
    }

    weights = _weights_for_pool(group, len(bundles))
    idx = _weighted_index(weights, rng)
    bundle = bundles[idx]
    tokens = active_prompt_tokens(split_prompt_tokens(str(bundle.get("text") or "")))
    merged = join_prompt_tokens(tokens)
    record = {
        **base_rec,
        "mode": "one_bundle_all_tokens",
        "bundle_id": bundle.get("id"),
        "bundle_alias": bundle.get("alias") or bundle.get("name") or "",
        "bundle_index": idx,
        "bundle_weight": weights[idx],
        "bundle_count": len(bundles),
        "tokens": tokens,
        "text": merged,
    }
    return merged, tokens, record


def resolve_sequential_bundle_pick(
    group: dict,
    index: int,
) -> tuple[str, list[str], dict[str, Any]]:
    bundles = list(group.get("bundles") or [])
    if not bundles:
        return "", [], {}

    target = group.get("target", "positive")
    seq_index = int(index or 0)
    idx = seq_index % len(bundles)
    bundle = bundles[idx]
    tokens = active_prompt_tokens(split_prompt_tokens(str(bundle.get("text") or "")))
    merged = join_prompt_tokens(tokens)
    record: dict[str, Any] = {
        "pick_type": "bundle_group",
        "group_id": group.get("id"),
        "group_name": group.get("name"),
        "target": target,
        "pick_mode": "sequential",
        "mode": "sequential_one_bundle",
        "sequence_index": seq_index,
        "bundle_id": bundle.get("id"),
        "bundle_alias": bundle.get("alias") or "",
        "bundle_index": idx,
        "bundle_count": len(bundles),
        "tokens": tokens,
        "text": merged,
    }
    return merged, tokens, record


def resolve_bundle_group_pick(
    group: dict,
    *,
    rng: random.Random,
    index: int = 0,
) -> tuple[str, list[str], dict[str, Any]]:
    mode = str(group.get("pick_mode") or "random").strip().lower()
    if mode not in PICK_MODES:
        mode = "random"
    if mode == "sequential":
        return resolve_sequential_bundle_pick(group, index)
    return resolve_random_bundle_pick(group, rng)


def pick_random_bundle_groups(
    groups: list[dict],
    *,
    seed: int | None = None,
    index: int = 0,
) -> tuple[dict[str, list[str]], list[dict]]:
    frags: dict[str, list[str]] = {"positive": [], "negative": []}
    records: list[dict] = []
    rng = random.Random((seed or 0) + index * 7919) if seed is not None else random

    for g in groups:
        if not g.get("enabled", True):
            continue
        merged, _tokens, rec = resolve_bundle_group_pick(g, rng=rng, index=index)
        if not merged:
            continue
        target = rec.get("target", "positive")
        if target not in frags:
            target = "positive"
        frags[target].append(merged)
        records.append(rec)
    return frags, records


def pick_random_groups(
    groups: list[dict],
    *,
    seed: int | None = None,
    index: int = 0,
) -> tuple[dict[str, list[str]], list[dict]]:
    """
    每个启用的组抽取一次，返回 (side -> [追加片段], pick_records)。
    每组通常贡献一个逗号拼接的字符串片段。
    """
    frags: dict[str, list[str]] = {"positive": [], "negative": []}
    records: list[dict] = []
    rng = random.Random((seed or 0) + index * 9973) if seed is not None else random

    for g in groups:
        if not g.get("enabled", True):
            continue
        merged, _tokens, rec = resolve_group_pick(g, rng=rng, index=index)
        if not merged:
            continue
        rec.setdefault("pick_type", "token_group")
        target = rec.get("target", "positive")
        if target not in frags:
            target = "positive"
        frags[target].append(merged)
        records.append(rec)
    return frags, records
