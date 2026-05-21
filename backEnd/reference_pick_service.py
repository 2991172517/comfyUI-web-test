"""随机参考词组：从组内解析词条并抽取（逗号分隔，供 batch / 全局参考复用）。"""
from __future__ import annotations

import random
import re
from typing import Any

# 半角/全角逗号
_COMMA_RE = re.compile(r"[,，]\s*")
# 旧配置可能用斜杠；仅在没有逗号时兼容
_SLASH_RE = re.compile(r"\s*/\s*")


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
    return str(token).strip().casefold()


def dedupe_prompt_tokens(tokens: list[str]) -> tuple[list[str], int]:
    """保留首次出现顺序；key 为 strip + casefold，O(n)。"""
    seen: set[str] = set()
    out: list[str] = []
    removed = 0
    for raw in tokens:
        t = str(raw).strip()
        if not t:
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
    }

    if len(pool) == 1:
        tokens = split_prompt_tokens(pool[0])
        if not tokens:
            return "", [], base_rec
        chosen = rng.choice(tokens)
        merged = chosen
        record = {
            **base_rec,
            "mode": "one_of_tokens",
            "candidate_count": 1,
            "tokens": [chosen],
            "text": merged,
        }
        return merged, [chosen], record

    idx = rng.randrange(len(pool))
    line = pool[idx]
    tokens = split_prompt_tokens(line)
    merged = join_prompt_tokens(tokens)
    record = {
        **base_rec,
        "mode": "all_tokens_from_candidate",
        "candidate_count": len(pool),
        "candidate_index": idx,
        "candidate_preview": line[:120] + ("…" if len(line) > 120 else ""),
        "tokens": tokens,
        "text": merged,
    }
    return merged, tokens, record


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
        merged, _tokens, rec = resolve_random_group_pick(g, rng)
        if not merged:
            continue
        target = rec.get("target", "positive")
        if target not in frags:
            target = "positive"
        frags[target].append(merged)
        records.append(rec)
    return frags, records
