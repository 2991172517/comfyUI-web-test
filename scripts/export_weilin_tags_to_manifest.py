#!/usr/bin/env python3
"""
从 WeiLin-Comfyui-Tools 的 SQLite 词库导出为 CustomProject manifest v2 JSON。

默认输入：
  ComfyUI/custom_nodes/WeiLin-Comfyui-Tools/user_data/userdatas_zh_CN_tags.db
默认输出：
  CustomProject/prompt/jsonData/weilin_tags_manifest.json
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = (
    ROOT.parent
    / "custom_nodes"
    / "WeiLin-Comfyui-Tools"
    / "user_data"
    / "userdatas_zh_CN_tags.db"
)
DEFAULT_OUT = ROOT / "prompt" / "jsonData" / "weilin_tags_manifest.json"
ROOT_CATEGORY_ID = "weilin-root-import"


def _uid(prefix: str, raw: str) -> str:
    return f"{prefix}-{raw}" if raw else str(uuid.uuid4())


def export_manifest(db_path: Path) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    groups = conn.execute(
        "SELECT id_index, name, color, create_time, p_uuid FROM tag_groups ORDER BY create_time ASC"
    ).fetchall()
    subgroups = conn.execute(
        """
        SELECT id_index, group_id, name, color, create_time, p_uuid, g_uuid
        FROM tag_subgroups ORDER BY create_time ASC
        """
    ).fetchall()
    tags = conn.execute(
        """
        SELECT id_index, subgroup_id, text, desc, color, create_time, t_uuid, g_uuid
        FROM tag_tags ORDER BY create_time ASC
        """
    ).fetchall()
    conn.close()

    categories: list[dict] = [
        {
            "id": ROOT_CATEGORY_ID,
            "name": "WeiLin 词库（导入）",
            "parentId": "root",
            "order": 0,
        }
    ]
    order = 1
    group_uuid_by_p: dict[str, str] = {}

    for g in groups:
        p_uuid = (g["p_uuid"] or "").strip() or str(g["id_index"])
        cat_id = _uid("weilin-g", p_uuid)
        group_uuid_by_p[p_uuid] = cat_id
        categories.append(
            {
                "id": cat_id,
                "name": (g["name"] or "未命名组").strip(),
                "parentId": ROOT_CATEGORY_ID,
                "order": order,
            }
        )
        order += 1

    subgroup_uuid_by_g: dict[str, str] = {}
    for sg in subgroups:
        p_uuid = (sg["p_uuid"] or "").strip()
        g_uuid = (sg["g_uuid"] or "").strip() or str(sg["id_index"])
        parent = group_uuid_by_p.get(p_uuid, ROOT_CATEGORY_ID)
        cat_id = _uid("weilin-sg", g_uuid)
        subgroup_uuid_by_g[g_uuid] = cat_id
        categories.append(
            {
                "id": cat_id,
                "name": (sg["name"] or "未命名子组").strip(),
                "parentId": parent,
                "order": order,
            }
        )
        order += 1

    prompts: list[dict] = []
    for t in tags:
        text = (t["text"] or "").strip()
        if not text:
            continue
        g_uuid = (t["g_uuid"] or "").strip()
        cat_id = subgroup_uuid_by_g.get(g_uuid, ROOT_CATEGORY_ID)
        desc = (t["desc"] or "").strip()
        name = desc if desc else text[:80]
        prompts.append(
            {
                "id": _uid("weilin-t", (t["t_uuid"] or "").strip() or str(t["id_index"])),
                "name": name,
                "value": text,
                "categoryId": cat_id,
            }
        )

    return {
        "version": 2,
        "exportedAt": int(time.time() * 1000),
        "rootCategoryId": ROOT_CATEGORY_ID,
        "rootCategoryName": "WeiLin 词库（导入）",
        "source": "WeiLin-Comfyui-Tools",
        "sourceDb": str(db_path),
        "categories": categories,
        "prompts": prompts,
        "stats": {
            "groups": len(groups),
            "subgroups": len(subgroups),
            "prompts": len(prompts),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="导出 WeiLin tags.db 为 manifest v2")
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_DB)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"数据库不存在: {args.input}")
        return 1

    manifest = export_manifest(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    stats = manifest.get("stats", {})
    print(f"已写入: {args.output}")
    print(
        f"组 {stats.get('groups', 0)}，子组 {stats.get('subgroups', 0)}，"
        f"词条 {stats.get('prompts', 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
