"""Shakker 页面 JSON 提取（无 Selenium）。"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from bs4 import BeautifulSoup

from model_parser.http_client import DEFAULT_HEADERS, _request_sync
from model_parser.size_utils import format_size_display, normalize_size_kb

log = logging.getLogger("custom_project.model_parser.shakker")

SHAKKER_PAGE = "https://www.shakker.ai/modelinfo/{model_uuid}"


class ShakkerMetadataExtractor:
    """从 HTML 中解析 __NEXT_DATA__ / application/json script。"""

    @classmethod
    def fetch_page_html(cls, model_uuid: str) -> str:
        url = SHAKKER_PAGE.format(model_uuid=model_uuid)
        content = _request_sync("GET", url, headers={**DEFAULT_HEADERS, "Accept": "text/html"})
        if isinstance(content, bytes):
            return content.decode("utf-8", errors="replace")
        return str(content)

    @classmethod
    def extract_json_blobs(cls, html: str) -> list[Any]:
        soup = BeautifulSoup(html, "html.parser")
        blobs: list[Any] = []

        script = soup.find("script", id="__NEXT_DATA__")
        if script and script.string:
            try:
                blobs.append(json.loads(script.string))
            except json.JSONDecodeError as e:
                log.warning("__NEXT_DATA__ JSON 解析失败: %s", e)

        for tag in soup.find_all("script", type="application/json"):
            if tag.string:
                try:
                    blobs.append(json.loads(tag.string))
                except json.JSONDecodeError:
                    pass

        for m in re.finditer(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;", html, re.S):
            try:
                blobs.append(json.loads(m.group(1)))
            except json.JSONDecodeError:
                pass

        return blobs

    @classmethod
    def _walk(cls, node: Any, hits: list[dict]) -> None:
        if isinstance(node, dict):
            keys = set(node.keys())
            if {"name", "versions"} <= keys or {"modelName", "versionList"} <= keys:
                hits.append(node)
            if "model" in node and isinstance(node["model"], dict):
                hits.append(node["model"])
            if "modelInfo" in node and isinstance(node["modelInfo"], dict):
                hits.append(node["modelInfo"])
            for v in node.values():
                cls._walk(v, hits)
        elif isinstance(node, list):
            for item in node:
                cls._walk(item, hits)

    @classmethod
    def normalize_model_payload(cls, raw: dict) -> dict:
        name = raw.get("name") or raw.get("modelName") or raw.get("title") or ""
        author = (
            raw.get("author")
            or raw.get("creator")
            or (raw.get("user") or {}).get("name")
            or (raw.get("authorInfo") or {}).get("name")
            or ""
        )
        if isinstance(author, dict):
            author = author.get("name", "")

        versions_in = (
            raw.get("versions")
            or raw.get("versionList")
            or raw.get("modelVersions")
            or []
        )
        versions = []
        for v in versions_in:
            if not isinstance(v, dict):
                continue
            vid = (
                v.get("versionUuid")
                or v.get("uuid")
                or v.get("id")
                or v.get("versionId")
            )
            versions.append({
                "versionUuid": str(vid) if vid else "",
                "name": v.get("name") or v.get("versionName") or "Version",
                "baseModel": v.get("baseModel") or v.get("base_model") or "",
                "description": v.get("description") or "",
                "imagesCount": len(v.get("images") or v.get("imageList") or []),
                "filesCount": len(v.get("files") or v.get("fileList") or []),
                "selected": False,
            })

        preview = (
            raw.get("cover")
            or raw.get("coverUrl")
            or raw.get("previewImage")
            or raw.get("thumbnail")
        )
        if not preview and versions_in:
            imgs = (versions_in[0] or {}).get("images") or (versions_in[0] or {}).get("imageList") or []
            if imgs:
                preview = imgs[0].get("url") if isinstance(imgs[0], dict) else imgs[0]

        return {
            "id": raw.get("id") or raw.get("modelUuid") or raw.get("uuid") or "",
            "name": name,
            "author": str(author),
            "description": raw.get("description") or raw.get("intro") or "",
            "previewImage": preview,
            "versions": versions,
            "tags": raw.get("tags") or [],
        }

    @classmethod
    def parse_model_page(cls, model_uuid: str, version_uuid: str | None = None) -> dict:
        html = cls.fetch_page_html(model_uuid)
        blobs = cls.extract_json_blobs(html)
        hits: list[dict] = []
        for blob in blobs:
            cls._walk(blob, hits)

        if not hits:
            raise RuntimeError("无法从 Shakker 页面提取模型 JSON，页面结构可能已变更")

        raw = hits[0]
        norm = cls.normalize_model_payload({**raw, "modelUuid": model_uuid})
        versions = norm.pop("versions", [])
        selected = version_uuid
        for v in versions:
            v["versionId"] = v.get("versionUuid")
            if version_uuid and str(v.get("versionUuid")) == str(version_uuid):
                v["selected"] = True
                selected = version_uuid
        if not selected and versions:
            versions[0]["selected"] = True
            selected = versions[0].get("versionUuid")

        return {
            "site": "shakker",
            "model": {
                "id": model_uuid,
                "name": norm.get("name", ""),
                "creator": norm.get("author", ""),
                "description": norm.get("description", ""),
                "type": "Unknown",
                "previewImage": norm.get("previewImage"),
                "tags": norm.get("tags") or [],
            },
            "versions": versions,
            "selectedVersion": selected,
            "rawType": "Unknown",
            "suggestedFolder": "loras",
        }

    @classmethod
    def parse_version_detail(cls, model_uuid: str, version_uuid: str) -> dict:
        html = cls.fetch_page_html(model_uuid)
        blobs = cls.extract_json_blobs(html)
        version_data = None
        for blob in blobs:
            stack = [blob]
            while stack:
                n = stack.pop()
                if isinstance(n, dict):
                    vid = n.get("versionUuid") or n.get("uuid") or n.get("id")
                    if str(vid) == str(version_uuid):
                        version_data = n
                        break
                    stack.extend(n.values())
                elif isinstance(n, list):
                    stack.extend(n)
            if version_data:
                break

        if not version_data:
            raise RuntimeError(f"未找到 Shakker 版本 {version_uuid}")

        images = version_data.get("images") or version_data.get("imageList") or []
        files = version_data.get("files") or version_data.get("fileList") or []
        image_meta = []
        workflow_json = None
        for img in images:
            if not isinstance(img, dict):
                continue
            meta = img.get("meta") or img.get("metadata") or {}
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except json.JSONDecodeError:
                    meta = {}
            image_meta.append({
                "url": img.get("url"),
                "prompt": meta.get("prompt"),
                "negativePrompt": meta.get("negativePrompt"),
                "sampler": meta.get("sampler"),
                "cfgScale": meta.get("cfgScale"),
                "steps": meta.get("steps"),
                "seed": meta.get("seed"),
                "workflow": meta.get("workflow"),
            })
            if not workflow_json and meta.get("workflow"):
                workflow_json = meta.get("workflow")

        parsed_files = []
        for f in files:
            if not isinstance(f, dict):
                continue
            size_kb = normalize_size_kb(f)
            parsed_files.append({
                "name": f.get("name", ""),
                "sizeKB": size_kb,
                "sizeDisplay": format_size_display(size_kb),
                "type": f.get("type", ""),
                "metadata": f,
                "downloadUrl": f.get("downloadUrl") or f.get("url"),
                "hashes": f.get("hashes") or {},
            })

        preview = None
        if images:
            im = images[0]
            preview = {
                "url": im.get("url") if isinstance(im, dict) else im,
                "width": im.get("width") if isinstance(im, dict) else None,
                "height": im.get("height") if isinstance(im, dict) else None,
            }

        return {
            "site": "shakker",
            "versionId": version_uuid,
            "name": version_data.get("name") or version_data.get("versionName") or "",
            "description": version_data.get("description") or "",
            "trainedWords": version_data.get("trainedWords") or version_data.get("triggerWords") or [],
            "baseModel": version_data.get("baseModel") or "",
            "previewImage": preview,
            "files": parsed_files,
            "images": [
                {"url": i.get("url") if isinstance(i, dict) else i}
                for i in images
            ],
            "imageMetadata": image_meta,
            "workflowJson": workflow_json,
            "recommendedParameters": version_data.get("recommendedParameters")
            or version_data.get("params")
            or {},
            "downloadInfo": version_data.get("downloadInfo") or {"files": parsed_files},
        }
