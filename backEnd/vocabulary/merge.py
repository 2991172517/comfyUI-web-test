"""将上传的 manifest v2 JSON 合并入主 manifest（分类与词条去重）。"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any

from .manifest_source import load_manifest

MANIFEST_SCHEMA_VERSION = 2


def empty_manifest(*, root_name: str = "标签库") -> dict:
    import uuid

    root_id = str(uuid.uuid4())
    return {
        "version": MANIFEST_SCHEMA_VERSION,
        "exportedAt": int(time.time() * 1000),
        "rootCategoryId": root_id,
        "rootCategoryName": root_name,
        "categories": [
            {
                "id": root_id,
                "name": root_name,
                "parentId": "root",
                "order": 0,
            }
        ],
        "prompts": [],
    }


def validate_manifest_payload(data: Any) -> dict:
    """校验并归一化 manifest v2 结构。"""
    if not isinstance(data, dict):
        raise ValueError("根对象必须是 JSON 对象（manifest v2）")
    version = data.get("version")
    if version not in (2, "2", None):
        raise ValueError("仅支持 version: 2 的 manifest")
    categories_in = data.get("categories")
    prompts_in = data.get("prompts")
    if categories_in is not None and not isinstance(categories_in, list):
        raise ValueError("categories 必须是数组")
    if prompts_in is not None and not isinstance(prompts_in, list):
        raise ValueError("prompts 必须是数组")

    categories: list[dict] = []
    seen_cat_ids: set[str] = set()
    for raw in categories_in or []:
        if not isinstance(raw, dict):
            continue
        cid = str(raw.get("id") or "").strip()
        if not cid or cid in seen_cat_ids:
            continue
        seen_cat_ids.add(cid)
        categories.append(
            {
                "id": cid,
                "name": str(raw.get("name") or cid).strip(),
                "parentId": str(raw.get("parentId") or "root").strip() or "root",
                "order": int(raw.get("order") or 0),
            }
        )

    prompts: list[dict] = []
    for raw in prompts_in or []:
        if not isinstance(raw, dict):
            continue
        value = str(raw.get("value") or "").strip()
        if not value:
            continue
        cat_id = str(raw.get("categoryId") or raw.get("category_id") or "").strip()
        if not cat_id:
            continue
        name = str(raw.get("name") or value).strip()[:256]
        pid = str(raw.get("id") or "").strip()
        row: dict[str, Any] = {
            "name": name,
            "value": value,
            "categoryId": cat_id,
        }
        if pid:
            row["id"] = pid
        prompts.append(row)

    root_id = str(data.get("rootCategoryId") or "").strip()
    root_name = str(data.get("rootCategoryName") or "标签库").strip() or "标签库"
    if not root_id and categories:
        # 取 parentId=root 的第一个作为根
        for c in categories:
            if c.get("parentId") in ("root", ""):
                root_id = c["id"]
                root_name = c.get("name") or root_name
                break
    if not root_id:
        root_id = categories[0]["id"] if categories else ""
    if root_id and not any(c["id"] == root_id for c in categories):
        categories.insert(
            0,
            {
                "id": root_id,
                "name": root_name,
                "parentId": "root",
                "order": 0,
            },
        )

    return {
        "version": MANIFEST_SCHEMA_VERSION,
        "exportedAt": int(data.get("exportedAt") or time.time() * 1000),
        "rootCategoryId": root_id,
        "rootCategoryName": root_name,
        "categories": categories,
        "prompts": prompts,
        **{
            k: data[k]
            for k in ("source", "sourceDb", "stats")
            if k in data
        },
    }


def _prompt_dedup_key(category_id: str, value: str) -> tuple[str, str]:
    return ((category_id or "").strip(), (value or "").strip().lower())


def merge_manifests(base: dict, incoming: dict) -> tuple[dict, dict[str, int]]:
    """
    合并 incoming → base，返回 (merged_manifest, stats)。
    去重规则：
    - 分类：相同 id 保留 base，不覆盖
    - 词条：相同 (categoryId, value 忽略大小写) 只保留一条
    """
    base = validate_manifest_payload(base)
    incoming = validate_manifest_payload(incoming)

    stats = {
        "base_categories": len(base.get("categories") or []),
        "base_prompts": len(base.get("prompts") or []),
        "incoming_categories": len(incoming.get("categories") or []),
        "incoming_prompts": len(incoming.get("prompts") or []),
        "added_categories": 0,
        "skipped_categories_duplicate_id": 0,
        "added_prompts": 0,
        "skipped_prompts_duplicate": 0,
    }

    cat_by_id = {
        str(c["id"]).strip(): dict(c)
        for c in base.get("categories") or []
        if c.get("id")
    }
    max_order = max((int(c.get("order") or 0) for c in cat_by_id.values()), default=0)

    for c in incoming.get("categories") or []:
        cid = str(c.get("id") or "").strip()
        if not cid:
            continue
        if cid in cat_by_id:
            stats["skipped_categories_duplicate_id"] += 1
            continue
        max_order += 1
        row = dict(c)
        row["order"] = int(row.get("order") or max_order)
        cat_by_id[cid] = row
        stats["added_categories"] += 1

    seen_prompts: set[tuple[str, str]] = set()
    merged_prompts: list[dict] = []
    for p in base.get("prompts") or []:
        value = str(p.get("value") or "").strip()
        cat_id = str(p.get("categoryId") or "").strip()
        if not value or not cat_id:
            continue
        key = _prompt_dedup_key(cat_id, value)
        if key in seen_prompts:
            continue
        seen_prompts.add(key)
        merged_prompts.append(dict(p))

    for p in incoming.get("prompts") or []:
        value = str(p.get("value") or "").strip()
        cat_id = str(p.get("categoryId") or "").strip()
        if not value or not cat_id:
            continue
        key = _prompt_dedup_key(cat_id, value)
        if key in seen_prompts:
            stats["skipped_prompts_duplicate"] += 1
            continue
        seen_prompts.add(key)
        merged_prompts.append(dict(p))
        stats["added_prompts"] += 1

    merged = {
        **base,
        "version": MANIFEST_SCHEMA_VERSION,
        "exportedAt": int(time.time() * 1000),
        "categories": list(cat_by_id.values()),
        "prompts": merged_prompts,
    }
    stats["merged_categories"] = len(merged["categories"])
    stats["merged_prompts"] = len(merged["prompts"])
    return merged, stats


def save_manifest(path: Path, manifest: dict, *, backup: bool = True) -> str | None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    backup_path: str | None = None
    if backup and path.is_file():
        ts = time.strftime("%Y%m%d_%H%M%S")
        bak = path.with_suffix(f".{ts}.bak.json")
        shutil.copy2(path, bak)
        backup_path = str(bak)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return backup_path


def parse_upload_bytes(raw: bytes) -> dict:
    if not raw:
        raise ValueError("文件为空")
    try:
        data = json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError as e:
        raise ValueError("请上传 UTF-8 编码的 JSON 文件") from e
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 解析失败: {e}") from e
    return validate_manifest_payload(data)


def merge_into_main_manifest(
    incoming: dict,
    manifest_path: Path,
    *,
    backup: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    if manifest_path.is_file():
        base = load_manifest(manifest_path)
    else:
        base = empty_manifest()

    merged, stats = merge_manifests(base, incoming)
    result: dict[str, Any] = {
        "ok": True,
        "dryRun": dry_run,
        "stats": stats,
        "manifestPath": str(manifest_path),
        "rebuilt": False,
        "backupPath": None,
    }
    if not dry_run:
        result["backupPath"] = save_manifest(manifest_path, merged, backup=backup)
    return result, merged
