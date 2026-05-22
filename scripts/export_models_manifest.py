#!/usr/bin/env python3
"""导出本地 ComfyUI 模型清单到 JSON。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backEnd"
sys.path.insert(0, str(BACKEND))

import model_manifest_service as svc  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="导出 checkpoints/loras 清单")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=svc.DEFAULT_MANIFEST_PATH,
        help="输出 JSON 路径",
    )
    parser.add_argument(
        "--no-catalog",
        action="store_true",
        help="不附带 model_node_defaults.json 摘要",
    )
    args = parser.parse_args()
    manifest = svc.export_manifest(include_catalog=not args.no_catalog)
    out = svc.save_manifest(manifest, args.output)
    stats = manifest.get("stats", {})
    print(f"已写入: {out}")
    print(
        f"Checkpoint {stats.get('checkpoints_total', 0)}，"
        f"LoRA {stats.get('loras_total', 0)}，"
        f"含链接 {stats.get('with_source_url', 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
