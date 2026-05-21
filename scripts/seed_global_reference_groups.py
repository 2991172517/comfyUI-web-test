#!/usr/bin/env python3
"""
写入「全局随机参考词组」（config/global_reference_groups.json）。

编辑数据文件（推荐）：
  config/global_reference_groups.seed.json

每组两种写法（二选一）：
  - pool：一行逗号分隔词条 → 词条池模式（每次随机选 1 个 tag）
  - schemes：多行字符串数组 → 多方案模式（每次随机选 1 条方案，整段 tag 全部加入）

用法：
  python scripts/seed_global_reference_groups.py
  python scripts/seed_global_reference_groups.py --file config/global_reference_groups.seed.json
  python scripts/seed_global_reference_groups.py --merge          # 与已有组合并（同名覆盖）
  python scripts/seed_global_reference_groups.py --replace        # 整文件替换为 seed 内容
  python scripts/seed_global_reference_groups.py --dry-run
  python scripts/seed_global_reference_groups.py --list
  python scripts/seed_global_reference_groups.py --api http://127.0.0.1:8000

也可在下方 GROUPS 常量里直接写（会覆盖同名的 --file 默认行为需显式 --from-code）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    requests = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backEnd"
DEFAULT_SEED_FILE = ROOT / "config" / "global_reference_groups.seed.json"
DEFAULT_API = "http://127.0.0.1:8000"
OUTPUT_PATH = ROOT / "config" / "global_reference_groups.json"

sys.path.insert(0, str(BACKEND))

from global_reference_service import (  # noqa: E402
    load_global_reference_groups,
    normalize_groups,
    save_global_reference_groups,
)

# ---------------------------------------------------------------------------
# 也可直接在这里填写（然后: python scripts/seed_global_reference_groups.py --from-code）
# ---------------------------------------------------------------------------
GROUPS: list[dict[str, Any]] = [
    # {
    #     "name": "组名",
    #     "target": "positive",
    #     "enabled": True,
    #     "pool": "tag1, tag2, tag3",
    # },
    # {
    #     "name": "组名-多方案",
    #     "target": "positive",
    #     "schemes": ["tagA, tagB", "tagC, tagD"],
    # },
]


def entry_to_group(entry: dict[str, Any]) -> dict[str, Any]:
    name = str(entry.get("name") or "").strip()
    if not name:
        raise ValueError("每组必须填写 name（组名）")

    target = str(entry.get("target") or "positive").strip().lower()
    if target not in ("positive", "negative"):
        target = "positive"

    enabled = bool(entry.get("enabled", True))

    if "schemes" in entry and entry["schemes"] is not None:
        prompts = [str(s).strip() for s in entry["schemes"] if str(s).strip()]
    elif "pool" in entry and str(entry.get("pool", "")).strip():
        prompts = [str(entry["pool"]).strip()]
    elif "prompts" in entry:
        prompts = [str(p).strip() for p in entry["prompts"] if str(p).strip()]
    else:
        raise ValueError(
            f"组「{name}」需要 pool（逗号分隔词条池）或 schemes（多方案列表）或 prompts"
        )

    if not prompts:
        raise ValueError(f"组「{name}」没有有效词条")

    return {
        "name": name,
        "target": target,
        "enabled": enabled,
        "prompts": prompts,
    }


def load_seed_file(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"数据文件不存在: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    raw = data.get("groups") if isinstance(data, dict) else data
    if not isinstance(raw, list):
        raise ValueError("JSON 需包含 groups 数组")
    return [entry_to_group(g) for g in raw]


def merge_groups(existing: list[dict], incoming: list[dict], *, by_name: bool = True) -> list[dict]:
    """合并：默认按组名覆盖，保留未出现在 seed 中的旧组。"""
    out = normalize_groups(existing)
    incoming_norm = normalize_groups(incoming)
    if by_name:
        by_key = {g["name"]: g for g in out}
        for g in incoming_norm:
            by_key[g["name"]] = g
        return list(by_key.values())
    by_id = {g["id"]: g for g in out}
    for g in incoming_norm:
        by_id[g["id"]] = g
    return list(by_id.values())


def save_via_api(api_base: str, groups: list[dict]) -> None:
    if requests is None:
        raise RuntimeError("需要 requests: pip install requests")
    body = {
        "random_groups": [
            {
                "id": g.get("id", ""),
                "name": g["name"],
                "enabled": g.get("enabled", True),
                "target": g.get("target", "positive"),
                "prompts": g.get("prompts") or [],
            }
            for g in groups
        ]
    }
    r = requests.put(f"{api_base}/api/global-reference-groups", json=body, timeout=30)
    r.raise_for_status()


def describe_group(g: dict) -> str:
    prompts = g.get("prompts") or []
    if len(prompts) <= 1:
        line = prompts[0] if prompts else ""
        n = len([p for p in line.replace("，", ",").split(",") if p.strip()])
        return f"  · {g['name']} [{g.get('target')}] 词条池 · 约 {max(n, 1)} 词"
    return f"  · {g['name']} [{g.get('target')}] 多方案 · {len(prompts)} 条候选"


def print_store(groups: list[dict], title: str) -> None:
    print(title)
    if not groups:
        print("  （空）")
        return
    for g in groups:
        print(describe_group(g))


def main() -> int:
    parser = argparse.ArgumentParser(description="写入全局随机参考词组")
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_SEED_FILE,
        help="种子数据 JSON（默认 config/global_reference_groups.seed.json）",
    )
    parser.add_argument("--from-code", action="store_true", help="使用本脚本内 GROUPS 常量")
    parser.add_argument(
        "--merge",
        action="store_true",
        help="与已有 global_reference_groups.json 合并（同名组覆盖）",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="用本次数据完全替换（默认：merge）",
    )
    parser.add_argument("--dry-run", action="store_true", help="只打印，不写文件")
    parser.add_argument("--list", action="store_true", help="列出当前已保存的全局组")
    parser.add_argument("--api", default=None, help="若指定则 PUT API，否则写本地 JSON")
    args = parser.parse_args()

    if args.list:
        store = load_global_reference_groups()
        print_store(normalize_groups(store.get("groups")), "当前全局参考词组：")
        return 0

    try:
        if args.from_code:
            if not GROUPS:
                print("GROUPS 为空，请在脚本内填写或改用 --file", file=sys.stderr)
                return 1
            incoming = [entry_to_group(g) for g in GROUPS]
        else:
            incoming = load_seed_file(args.file)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"读取失败: {exc}", file=sys.stderr)
        return 1

    if not incoming:
        print("没有可写入的组（groups 为空）", file=sys.stderr)
        print(f"请编辑: {args.file}", file=sys.stderr)
        return 1

    if args.replace:
        final = normalize_groups(incoming)
    else:
        store = load_global_reference_groups()
        existing = store.get("groups") or []
        final = merge_groups(existing, incoming, by_name=True)

    final = normalize_groups(final)
    print_store(incoming, f"\n本次载入 {len(incoming)} 组：")
    print_store(final, f"\n写入后共 {len(final)} 组：")

    if args.dry_run:
        print("\n（dry-run，未写入）")
        return 0

    if args.api:
        save_via_api(args.api, final)
        print(f"\n已通过 API 保存: {args.api}")
    else:
        save_global_reference_groups({"schema_version": 1, "groups": final})
        print(f"\n已写入: {OUTPUT_PATH}")

    print("每次抽卡 / 批量生成时，各启用组会按「词条池 / 多方案」规则自动抽取。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
