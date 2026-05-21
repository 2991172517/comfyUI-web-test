#!/usr/bin/env python3
"""
按 LoRA 两两组合生成批量任务（优先未出现在任务计划 / 批量记录中的配对）。

- 工作流：First_api
- Checkpoint：waiIllustriousSDXL_v170.safetensors
- A 轴 0.3→+0.1×5，B 轴 0.8→-0.1×5（5×5=25 张/任务）
- 组合空间：C(n,2)；请求条数超过剩余未测组合时，只生成剩余数量并提示
- **不写 batch_prompts**：运行时由后端并入全局随机组；payload 清空母版 CLIP 并设 prompt_global_priority（随机词排在角色底稿前）
- **style_enabled: true**：#15 角色 + #16 Style 两路 LoRA 均接入 K 采样器（若为 false 则 B 轴扫参无效）

用法：
  python scripts/seed_lora_batch_tasks.py
  python scripts/seed_lora_batch_tasks.py --count 20
  python scripts/seed_lora_batch_tasks.py --count 10000   # 至多占满全部未测组合
  python scripts/seed_lora_batch_tasks.py --dry-run
  python scripts/seed_lora_batch_tasks.py --list          # 仅统计组合占用情况
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import uuid
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

try:
    import requests
except ImportError:
    print("需要 requests: pip install requests", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backEnd"
sys.path.insert(0, str(BACKEND))

from config import BATCH_OUTPUT_PREFIX, COMFYUI_ROOT  # noqa: E402

WORKFLOW_ID = "First_api"
# 清空母版 CLIP 长文案，生成时仅用「全局默认底稿 + 全局随机参考词组」
PROMPT_NODE_POSITIVE = "3"
PROMPT_NODE_NEGATIVE = "4"
PROMPT_GLOBAL_PRIORITY = True
CKPT = "waiIllustriousSDXL_v170.safetensors"
NODE_CKPT = "1"
NODE_LORA_A = "15"
NODE_LORA_B = "16"
DEFAULT_COUNT = 10
DEFAULT_API = "http://127.0.0.1:8000"
RUN_CONFIG_NAME = "run_config.json"

FILENAME_TEMPLATE = (
    "{batch_id}/g{index:02d}_{a_name}_w{a_w}_{a_dir}_x_{b_name}_w{b_w}_{b_dir}_seed{seed}"
)

# 任务 payload 不包含 batch_prompts（批量页/预设提示词），便于纯 LoRA 扫参测试
INCLUDE_BATCH_PROMPTS = False
TASK_DESCRIPTION = (
    f"LoRA 配对 · 工作流 {WORKFLOW_ID} · 5×5 扫参 · "
    "提示词=全局默认底稿+全局随机组（已清空母版 CLIP 长文案）"
)

TASKS_PATH = ROOT / "config" / "batch_tasks.json"
BATCH_OUTPUT_ROOT = COMFYUI_ROOT / "output" / BATCH_OUTPUT_PREFIX


def pair_key(lora_a: str, lora_b: str) -> tuple[str, str]:
    return tuple(sorted((lora_a, lora_b)))


def list_loras_local() -> list[str]:
    loras_dir = COMFYUI_ROOT / "models" / "loras"
    if not loras_dir.is_dir():
        return []
    return sorted(
        p.name for p in loras_dir.iterdir()
        if p.is_file() and p.suffix.lower() in (".safetensors", ".ckpt", ".pt")
    )


def list_loras(api_base: str) -> list[str]:
    try:
        r = requests.get(f"{api_base}/api/models/loras", timeout=60)
        r.raise_for_status()
        data = r.json()
        files = sorted(set(data.get("files") or []))
        if files:
            return files
    except requests.RequestException as exc:
        print(f"API 不可用 ({exc})，改从本地读取 LoRA 列表", file=sys.stderr)
    local = list_loras_local()
    if not local:
        raise RuntimeError(
            "无法获取 LoRA 列表：请先启动 backEnd 的 python main.py，"
            f"或确认目录存在: {COMFYUI_ROOT / 'models' / 'loras'}"
        )
    return local


def extract_pair_from_payload(payload: dict | None) -> tuple[str, str] | None:
    if not payload:
        return None
    base = payload.get("base_overrides") or {}
    la = (base.get(NODE_LORA_A) or {}).get("lora_name")
    lb = (base.get(NODE_LORA_B) or {}).get("lora_name")
    if la and lb:
        return pair_key(str(la), str(lb))

    enabled_names: list[str] = []
    for ax in payload.get("lora_axes") or []:
        if not ax.get("enabled"):
            continue
        name = ax.get("lora_name")
        if name:
            enabled_names.append(str(name))
    if len(enabled_names) >= 2:
        return pair_key(enabled_names[0], enabled_names[1])
    return None


def extract_pair_from_run_config(rc: dict) -> tuple[str, str] | None:
    la = (rc.get("lora_a") or {}).get("lora_name")
    lb = (rc.get("lora_b") or {}).get("lora_name")
    if la and lb:
        return pair_key(str(la), str(lb))
    base = rc.get("base_overrides") or {}
    la = (base.get(NODE_LORA_A) or {}).get("lora_name")
    lb = (base.get(NODE_LORA_B) or {}).get("lora_name")
    if la and lb:
        return pair_key(str(la), str(lb))
    return None


def collect_used_pairs() -> tuple[set[tuple[str, str]], dict[str, list[str]]]:
    """返回 (已占用配对, 来源说明)。"""
    used: set[tuple[str, str]] = set()
    sources: dict[str, list[str]] = {"batch_tasks": [], "batch_records": []}

    if TASKS_PATH.is_file():
        try:
            with open(TASKS_PATH, encoding="utf-8") as f:
                store = json.load(f)
            for t in store.get("tasks") or []:
                pk = extract_pair_from_payload(t.get("batch_payload"))
                if pk and pk not in used:
                    used.add(pk)
                    sources["batch_tasks"].append(f"{t.get('name', t.get('task_id'))}: {pk[0]} × {pk[1]}")
        except (OSError, json.JSONDecodeError) as exc:
            print(f"读取 batch_tasks.json 失败: {exc}", file=sys.stderr)

    if BATCH_OUTPUT_ROOT.is_dir():
        for batch_dir in BATCH_OUTPUT_ROOT.iterdir():
            if not batch_dir.is_dir():
                continue
            rc_path = batch_dir / RUN_CONFIG_NAME
            if not rc_path.is_file():
                continue
            try:
                with open(rc_path, encoding="utf-8") as f:
                    rc = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            pk = extract_pair_from_run_config(rc)
            if pk and pk not in used:
                used.add(pk)
                sources["batch_records"].append(f"{batch_dir.name}: {pk[0]} × {pk[1]}")

    return used, sources


def all_pairs(loras: list[str]) -> list[tuple[str, str]]:
    return [pair_key(a, b) for a, b in combinations(loras, 2)]


def pick_unused_pairs(
    loras: list[str],
    n: int,
    used: set[tuple[str, str]],
    *,
    diversify: bool = True,
) -> tuple[list[tuple[str, str]], dict[str, int]]:
    """
    从 C(n,2) 中选取未占用配对。
    同一轮生成内优先让不同任务覆盖更多不同 LoRA（例如 2 条任务尽量用满 4 个不同 LoRA）。
    """
    pool = [p for p in all_pairs(loras) if p not in used]
    stats = {
        "lora_count": len(loras),
        "total_combinations": len(all_pairs(loras)),
        "already_used": len(used),
        "remaining_unused": len(pool),
        "requested": n,
    }
    if not pool:
        return [], stats

    selected: list[tuple[str, str]] = []
    remaining = set(pool)
    loras_in_this_run: set[str] = set()

    while len(selected) < n and remaining:
        candidates = list(remaining)
        random.shuffle(candidates)
        if diversify:
            candidates.sort(
                key=lambda p: (p[0] in loras_in_this_run) + (p[1] in loras_in_this_run),
            )
        pick = candidates[0]
        selected.append(pick)
        remaining.remove(pick)
        loras_in_this_run.add(pick[0])
        loras_in_this_run.add(pick[1])

    stats["selected"] = len(selected)
    stats["loras_in_new_tasks"] = len(loras_in_this_run)
    return selected, stats


def build_payload(lora_a: str, lora_b: str, short_a: str, short_b: str) -> dict:
    """LoRA 扫参测试：工作流 First_api；提示词由全局随机组驱动（见 PROMPT_GLOBAL_PRIORITY）。"""
    base_overrides: dict = {
        NODE_CKPT: {"ckpt_name": CKPT},
        NODE_LORA_A: {"lora_name": lora_a},
        NODE_LORA_B: {"lora_name": lora_b},
    }
    if PROMPT_GLOBAL_PRIORITY:
        base_overrides[PROMPT_NODE_POSITIVE] = {"text": ""}
        base_overrides[PROMPT_NODE_NEGATIVE] = {"text": ""}

    payload: dict = {
        "base_overrides": base_overrides,
        "prompt_global_priority": PROMPT_GLOBAL_PRIORITY,
        # 双 LoRA 扫参须启用 Style，否则 #16 被拓扑绕过，B 轴权重不生效
        "style_enabled": True,
        "seed_mode": "random",
        "sync_clip": True,
        "filename_template": FILENAME_TEMPLATE,
        "save_node_id": "8",
        "seed_node_id": "5",
        "lora_axes": [
            {
                "node_id": NODE_LORA_A,
                "enabled": True,
                "alias": short_a,
                "sweep_role": "A",
                "start": 0.3,
                "step": 0.1,
                "direction": "up",
                "count": 5,
                "lora_name": lora_a,
            },
            {
                "node_id": NODE_LORA_B,
                "enabled": True,
                "alias": short_b,
                "sweep_role": "B",
                "start": 0.8,
                "step": 0.1,
                "direction": "down",
                "count": 5,
                "lora_name": lora_b,
            },
        ],
    }
    if INCLUDE_BATCH_PROMPTS:
        payload["batch_prompts"] = {"fixed": {}, "random_groups": []}
    return payload


def short_name(filename: str) -> str:
    return Path(filename).stem[:24]


def save_via_api(api_base: str, name: str, payload: dict, planned: int) -> dict:
    body = {
        "name": name,
        "description": TASK_DESCRIPTION,
        "workflow_id": WORKFLOW_ID,
        "workflow_display_name": "母版（LoRA 链 + 放大）",
        "planned_total": planned,
        "batch_payload": payload,
    }
    r = requests.post(f"{api_base}/api/batch-tasks", json=body, timeout=30)
    r.raise_for_status()
    return r.json().get("task") or {}


def upgrade_prompt_priority_in_store() -> int:
    """为已有 LoRA 配对任务补上「清空 CLIP + 全局随机优先」字段。"""
    if not TASKS_PATH.is_file():
        return 0
    with open(TASKS_PATH, encoding="utf-8") as f:
        store = json.load(f)
    n = 0
    for t in store.get("tasks") or []:
        payload = t.get("batch_payload")
        if not isinstance(payload, dict):
            continue
        wid = str(t.get("workflow_id") or "")
        if wid and wid != WORKFLOW_ID:
            continue
        base = payload.setdefault("base_overrides", {})
        base[PROMPT_NODE_POSITIVE] = {**(base.get(PROMPT_NODE_POSITIVE) or {}), "text": ""}
        base[PROMPT_NODE_NEGATIVE] = {**(base.get(PROMPT_NODE_NEGATIVE) or {}), "text": ""}
        payload["prompt_global_priority"] = True
        if "batch_prompts" in payload:
            del payload["batch_prompts"]
        n += 1
    if n:
        with open(TASKS_PATH, "w", encoding="utf-8") as f:
            json.dump(store, f, indent=2, ensure_ascii=False)
    return n


def strip_batch_prompts_in_store() -> int:
    """从已有任务计划里删除 batch_prompts，避免与全局参考词组重复或冲突。"""
    if not TASKS_PATH.is_file():
        return 0
    with open(TASKS_PATH, encoding="utf-8") as f:
        store = json.load(f)
    n = 0
    for t in store.get("tasks") or []:
        payload = t.get("batch_payload")
        if isinstance(payload, dict) and "batch_prompts" in payload:
            del payload["batch_prompts"]
            n += 1
    if n:
        with open(TASKS_PATH, "w", encoding="utf-8") as f:
            json.dump(store, f, indent=2, ensure_ascii=False)
    return n


def save_via_file(entry: dict) -> None:
    path = TASKS_PATH
    store = {"schema_version": 1, "tasks": []}
    if path.is_file():
        with open(path, encoding="utf-8") as f:
            store = json.load(f)
    existing = {str(t.get("task_id")) for t in store.get("tasks") or []}
    if entry["task_id"] not in existing:
        store.setdefault("tasks", []).append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)


def print_stats(loras: list[str], used: set[tuple[str, str]], sources: dict[str, list[str]]) -> None:
    total = len(all_pairs(loras))
    unused = len([p for p in all_pairs(loras) if p not in used])
    print(f"LoRA 数量: {len(loras)}")
    print(f"两两组合总数 C({len(loras)},2) = {total}")
    print(f"已占用（任务计划 + 批量 run_config）: {len(used)}")
    print(f"剩余未测: {unused}")
    if sources["batch_tasks"]:
        print(f"  来自任务计划: {len(sources['batch_tasks'])} 条")
    if sources["batch_records"]:
        print(f"  来自批量记录: {len(sources['batch_records'])} 条")


def main() -> int:
    parser = argparse.ArgumentParser(description="种子 LoRA 两两配对批量任务")
    parser.add_argument("--api", default=DEFAULT_API, help="CustomProject API 地址")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help="生成任务条数（上限=剩余未测组合数）")
    parser.add_argument("--dry-run", action="store_true", help="仅打印，不写入")
    parser.add_argument("--list", action="store_true", help="只查看组合占用统计")
    parser.add_argument("--seed", type=int, default=None, help="随机种子")
    parser.add_argument(
        "--no-diversify",
        action="store_true",
        help="不在本轮生成内优先摊开到更多不同 LoRA",
    )
    parser.add_argument(
        "--strip-prompts-in-tasks",
        action="store_true",
        help="保存新任务前，从 batch_tasks.json 里移除所有任务的 batch_prompts 字段",
    )
    parser.add_argument(
        "--upgrade-prompt-priority",
        action="store_true",
        help="为 batch_tasks.json 中已有任务补上清空 CLIP + prompt_global_priority（不新建任务）",
    )
    args = parser.parse_args()
    if args.seed is not None:
        random.seed(args.seed)
    if args.count < 1:
        print("--count 至少为 1", file=sys.stderr)
        return 1

    loras = list_loras(args.api)
    used, sources = collect_used_pairs()

    if args.list:
        print_stats(loras, used, sources)
        return 0

    if args.upgrade_prompt_priority:
        n = upgrade_prompt_priority_in_store()
        print(f"已升级 {n} 个任务的提示词策略（清空母版 CLIP + 全局随机优先）")
        print("请重启 backEnd 后重新执行任务计划。")
        return 0

    if args.strip_prompts_in_tasks:
        removed = strip_batch_prompts_in_store()
        print(f"已从 {removed} 个已有任务中移除 batch_prompts")

    if len(loras) < 2:
        print(f"至少需要 2 个 LoRA，当前 {len(loras)} 个", file=sys.stderr)
        return 1

    pairs, stats = pick_unused_pairs(
        loras,
        args.count,
        used,
        diversify=not args.no_diversify,
    )

    print_stats(loras, used, sources)
    print(
        f"\n本次将生成 {stats.get('selected', 0)} 条任务"
        f"（请求 {args.count}，剩余未测 {stats['remaining_unused']}）"
    )
    if stats.get("loras_in_new_tasks"):
        print(f"本轮覆盖 {stats['loras_in_new_tasks']} 个不同 LoRA 文件")

    if not pairs:
        print("没有可生成的新配对；所有组合均已在任务或批量记录中出现。", file=sys.stderr)
        return 1

    if stats.get("selected", 0) < args.count:
        print(
            f"提示：仅 {stats['remaining_unused']} 个未测组合，"
            f"无法凑满 {args.count} 条；已全部写入剩余组合。",
            file=sys.stderr,
        )

    created = []
    total = len(pairs)
    for i, (la, lb) in enumerate(pairs, 1):
        sa, sb = short_name(la), short_name(lb)
        payload = build_payload(la, lb, sa, sb)
        name = f"配对 #{i:04d} · {sa} × {sb}"
        planned = 25
        print(f"  [{i}/{total}] {name} ({planned} 张)")
        if args.dry_run:
            created.append({"name": name, "pair": (la, lb)})
            continue
        try:
            task = save_via_api(args.api, name, payload, planned)
            created.append(task)
            print(f"       -> task_id={task.get('task_id')}")
        except requests.RequestException as exc:
            print(f"API 保存失败，改写入本地文件: {exc}", file=sys.stderr)
            tid = uuid.uuid4().hex[:10]
            now = datetime.now(timezone.utc).isoformat()
            entry = {
                "task_id": tid,
                "name": name,
                "description": TASK_DESCRIPTION,
                "workflow_id": WORKFLOW_ID,
                "workflow_display_name": "母版（LoRA 链 + 放大）",
                "batch_payload": payload,
                "planned_total": planned,
                "created_at": now,
                "updated_at": now,
                "execution": {"status": "pending", "batch_ids": [], "last_batch_id": None},
            }
            save_via_file(entry)
            created.append(entry)

    print(
        "\n完成：共 {0} 条任务。请在「任务计划」页勾选后手动执行。".format(len(created))
    )
    if PROMPT_GLOBAL_PRIORITY:
        print(
            "提示：prompt_global_priority 已开启，全局随机组排在角色底稿前；"
            "旧任务请运行: python scripts/seed_lora_batch_tasks.py --upgrade-prompt-priority"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
