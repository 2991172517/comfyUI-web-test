"""从 Prompt Gallery manifest v2 读取词条与分类。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator


def load_manifest(manifest_path: Path) -> dict:
    with open(manifest_path, encoding="utf-8") as f:
        return json.load(f)


def iter_manifest_prompts(manifest_path: Path) -> Iterator[dict]:
    """
    产出归一化词条。
    字段：insert_text, label, category, category_id, source_id
    """
    data = load_manifest(manifest_path)
    categories = {
        c.get("id"): c.get("name", "")
        for c in data.get("categories", [])
        if c.get("id")
    }

    for item in data.get("prompts", []):
        value = (item.get("value") or "").strip()
        if not value:
            continue
        name = (item.get("name") or value).strip()
        cat_id = (item.get("categoryId") or "").strip()
        yield {
            "insert_text": value,
            "label": name,
            "category": categories.get(cat_id, ""),
            "category_id": cat_id,
            "source_id": "manifest",
        }


def iter_user_prompts(user_prompts: list[dict]) -> Iterator[dict]:
    for item in user_prompts:
        value = (item.get("value") or "").strip()
        if not value:
            continue
        name = (item.get("name") or value).strip()
        cat_id = (item.get("categoryId") or "").strip()
        yield {
            "insert_text": value,
            "label": name,
            "category": "",
            "category_id": cat_id,
            "source_id": "user",
        }
