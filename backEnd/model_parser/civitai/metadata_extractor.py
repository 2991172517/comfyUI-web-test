"""Civitai 版本 metadata / workflow 提取。"""
from __future__ import annotations

import json
from typing import Any

from model_parser.civitai.auth import get_civitai_api_token, is_civitai_download_url
from model_parser.media_utils import (
    classify_image_entry,
    is_static_image_url,
    preview_entry,
)
from model_parser.size_utils import format_size_display, normalize_size_kb


class MetadataExtractor:
    @staticmethod
    def _meta_dict(raw: Any) -> dict:
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {}
        return {}

    @classmethod
    def extract_image_metadata(cls, images: list[dict]) -> tuple[list[dict], Any | None]:
        rows: list[dict] = []
        workflow_json = None
        for img in images or []:
            meta = cls._meta_dict(img.get("meta"))
            url = img.get("url")
            media_type = classify_image_entry(img)
            row = {
                "url": url,
                "mediaType": media_type,
                "prompt": meta.get("prompt") or meta.get("Prompt"),
                "negativePrompt": meta.get("negativePrompt") or meta.get("Negative prompt"),
                "sampler": meta.get("sampler") or meta.get("Sampler"),
                "cfgScale": meta.get("cfgScale") or meta.get("CFG scale"),
                "steps": meta.get("steps") or meta.get("Steps"),
                "seed": meta.get("seed") or meta.get("Seed"),
                "workflow": meta.get("workflow") or meta.get("comfy"),
            }
            rows.append(row)
            if workflow_json is None:
                wf = meta.get("workflow") or meta.get("comfy")
                if wf:
                    if isinstance(wf, str):
                        try:
                            workflow_json = json.loads(wf)
                        except json.JSONDecodeError:
                            workflow_json = {"raw": wf}
                    else:
                        workflow_json = wf
                nodes = meta.get("nodes")
                if nodes and workflow_json is None:
                    workflow_json = {"nodes": nodes, "source": "meta.nodes"}
        return rows, workflow_json

    @staticmethod
    def pick_preview_image(images: list[dict]) -> dict | None:
        """优先静态图；仅有视频时返回视频预览（前端用 video 标签展示）。"""
        if not images:
            return None
        static = [i for i in images if classify_image_entry(i) != "video"]
        pool = static if static else list(images)
        return preview_entry(pool[0])

    @staticmethod
    def list_importable_preview_urls(images: list[dict], *, max_count: int = 3) -> list[str]:
        """导入参考图：仅静态图 URL（跳过 mp4 等）。"""
        urls: list[str] = []
        for img in images or []:
            url = img.get("url")
            if not url or not is_static_image_url(url):
                continue
            if classify_image_entry(img) == "video":
                continue
            if url not in urls:
                urls.append(url)
            if len(urls) >= max_count:
                break
        return urls

    @staticmethod
    def parse_files(files: list[dict]) -> list[dict]:
        out = []
        for f in files or []:
            size_kb = normalize_size_kb(f)
            raw_url = f.get("downloadUrl") or ""
            out.append({
                "name": f.get("name", ""),
                "sizeKB": size_kb,
                "sizeDisplay": format_size_display(size_kb),
                "type": f.get("type", ""),
                "metadata": f.get("metadata") if isinstance(f.get("metadata"), dict) else {},
                "downloadUrl": raw_url,
                "requiresCivitaiToken": bool(raw_url) and is_civitai_download_url(raw_url),
                "civitaiTokenConfigured": bool(get_civitai_api_token()),
                "hashes": f.get("hashes") if isinstance(f.get("hashes"), dict) else {},
            })
        return out
