#!/usr/bin/env python3
"""按 models_manifest.json 批量下载模型（本地已有则跳过）。"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backEnd"
sys.path.insert(0, str(BACKEND))

import model_manifest_service as svc  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="按清单批量下载模型")
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=svc.DEFAULT_MANIFEST_PATH,
        help="清单 JSON 路径",
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="不跳过本地已存在的模型（可能冲突）",
    )
    parser.add_argument(
        "--metadata-only-if-exists",
        action="store_true",
        help="已存在时仅导入说明与预览图",
    )
    parser.add_argument(
        "--civitai-token",
        default=os.environ.get("CIVITAI_API_TOKEN", ""),
        help="Civitai API Token（或环境变量 CIVITAI_API_TOKEN）",
    )
    args = parser.parse_args()

    manifest = svc.load_manifest(args.input)

    def on_progress(evt: dict) -> None:
        msg = evt.get("message", "")
        if msg:
            print(msg, flush=True)

    summary = svc.import_all_from_manifest(
        manifest,
        civitai_api_token=args.civitai_token.strip(),
        skip_existing=not args.no_skip,
        import_metadata_when_exists=args.metadata_only_if_exists,
        on_progress=on_progress,
    )
    c = summary.get("counts", {})
    print(
        f"\n完成: 下载 {c.get('downloaded', 0)}, "
        f"跳过 {c.get('skipped', 0)}, "
        f"无链接 {c.get('no_source', 0)}, "
        f"失败 {c.get('failed', 0)}"
    )
    return 1 if c.get("failed") else 0


if __name__ == "__main__":
    raise SystemExit(main())
