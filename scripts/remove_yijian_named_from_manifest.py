#!/usr/bin/env python3
"""从 manifest.json 中删除 name 以「一键」开头的项。

默认处理 prompt/jsonData/manifest.json。
会处理 categories / prompts / combinations / images 四个数组（若存在且元素含 name 字段）。

用法:
  python remove_yijian_named_from_manifest.py              # 预览（dry-run）
  python remove_yijian_named_from_manifest.py --apply      # 写入（先备份 .bak）
  python remove_yijian_named_from_manifest.py -f 其它路径/manifest.json --apply
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

NAME_PREFIX = "一键"
LIST_KEYS = ("categories", "prompts", "combinations", "images")

DEFAULT_FILE = (
    Path(__file__).resolve().parent.parent / "prompt" / "jsonData" / "manifest.json"
)


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
        data[key] = [
            x for x in arr if not (isinstance(x, dict) and should_remove(x, prefix))
        ]
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="删除 manifest 中 name 以「一键」开头的项"
    )
    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        default=DEFAULT_FILE,
        help=f"manifest.json 路径（默认: {DEFAULT_FILE.as_posix()}）",
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

    path = args.file.resolve()
    if not path.is_file():
        print(f"错误: 文件不存在: {path}", file=sys.stderr)
        return 1

    mode = "写入" if args.apply else "预览（加 --apply 执行）"
    print(f"文件: {path}")
    print(f"模式: {mode} | 前缀: {args.prefix!r}\n")

    try:
        removed = process_file(path, args.prefix, args.apply)
    except json.JSONDecodeError as e:
        print(f"JSON 解析失败: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    if removed is None:
        print("无变更")
        return 0

    grand_total = sum(removed.values())
    for key in LIST_KEYS:
        n = removed.get(key, 0)
        if n:
            print(f"  {key}: -{n}")
    if grand_total == 0:
        print("无匹配项")
    else:
        print(f"\n合计删除: {grand_total} 项")
        if not args.apply:
            print("使用 --apply 写入修改。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
