#!/usr/bin/env python3
"""从指定目录下所有 manifest.json 中删除 name 以「随机」开头的项。

默认处理 scripts/category_标签库_20260513_004841/ 及其子目录中的 manifest.json。
会处理 categories / prompts / combinations / images 四个数组（若存在且元素含 name 字段）。

用法:
  python remove_random_named_from_manifests.py              # 预览（dry-run）
  python remove_random_named_from_manifests.py --apply      # 写入（先备份 .bak）
  python remove_random_named_from_manifests.py -d 其它目录 --apply
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

NAME_PREFIX = "随机"
LIST_KEYS = ("categories", "prompts", "combinations", "images")

DEFAULT_DIR = Path(__file__).resolve().parent / "category_标签库_20260513_004841"


def should_remove(item: dict, prefix: str) -> bool:
    name = item.get("name")
    if name is None:
        return False
    return str(name).startswith(prefix)


def filter_manifest(data: dict, prefix: str) -> dict[str, int]:
    """原地过滤，返回各 key 删除数量。"""
    removed: dict[str, int] = {}
    for key in LIST_KEYS:
        arr = data.get(key)
        if not isinstance(arr, list):
            continue
        before = len(arr)
        data[key] = [x for x in arr if not (isinstance(x, dict) and should_remove(x, prefix))]
        removed[key] = before - len(data[key])
    return removed


def process_file(path: Path, prefix: str, apply: bool) -> dict[str, int] | None:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    removed = filter_manifest(data, prefix)
    total_removed = sum(removed.values())
    if total_removed == 0:
        return removed

    if apply:
        backup = path.with_suffix(path.suffix + ".bak")
        if not backup.exists():
            shutil.copy2(path, backup)
            print(f"  备份 -> {backup.name}")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")

    return removed


def find_manifests(root: Path) -> list[Path]:
    return sorted(root.rglob("manifest.json"))


def main() -> int:
    parser = argparse.ArgumentParser(description="删除 manifest 中 name 以「随机」开头的项")
    parser.add_argument(
        "-d",
        "--dir",
        type=Path,
        default=DEFAULT_DIR,
        help=f"扫描目录（默认: {DEFAULT_DIR.name}）",
    )
    parser.add_argument(
        "--prefix",
        default=NAME_PREFIX,
        help=f"name 前缀（默认: {NAME_PREFIX}）",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="实际写入文件（否则仅预览）",
    )
    args = parser.parse_args()

    root = args.dir.resolve()
    if not root.is_dir():
        print(f"错误: 目录不存在: {root}", file=sys.stderr)
        return 1

    manifests = find_manifests(root)
    if not manifests:
        print(f"未找到 manifest.json: {root}")
        return 0

    mode = "写入" if args.apply else "预览（加 --apply 执行）"
    print(f"目录: {root}")
    print(f"模式: {mode} | 前缀: {args.prefix!r} | 文件数: {len(manifests)}\n")

    grand_total = 0
    for path in manifests:
        rel = path.relative_to(root)
        print(f"[{rel}]")
        try:
            removed = process_file(path, args.prefix, args.apply)
        except json.JSONDecodeError as e:
            print(f"  跳过（JSON 解析失败）: {e}", file=sys.stderr)
            continue
        except OSError as e:
            print(f"  错误: {e}", file=sys.stderr)
            return 1

        if removed is None:
            print("  无变更")
            continue

        file_total = sum(removed.values())
        grand_total += file_total
        for key in LIST_KEYS:
            n = removed.get(key, 0)
            if n:
                print(f"  {key}: -{n}")
        if file_total == 0:
            print("  无匹配项")
        print()

    print(f"合计删除: {grand_total} 项")
    if not args.apply and grand_total > 0:
        print("使用 --apply 写入修改。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
