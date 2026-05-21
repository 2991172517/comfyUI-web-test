"""Civitai 模型 API。"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from model_parser.civitai.metadata_extractor import MetadataExtractor
from model_parser.html_utils import html_to_plain_text
from model_parser.http_client import CIVITAI_API_BASE, get_json

log = logging.getLogger("custom_project.model_parser.civitai.model")


class ModelService:
    def fetch_model(self, model_id: int) -> dict:
        url = f"{CIVITAI_API_BASE}/models/{model_id}"
        log.info("GET %s", url)
        return get_json(url)

    @staticmethod
    def _iso_date(val: Any) -> str | None:
        if not val:
            return None
        if isinstance(val, str):
            return val[:10] if len(val) >= 10 else val
        if isinstance(val, datetime):
            return val.date().isoformat()
        return str(val)

    def build_parse_response(self, data: dict, selected_version_id: int | None) -> dict:
        creator = data.get("creator") or {}
        creator_name = creator.get("username") or creator.get("name") or ""
        versions_raw = data.get("modelVersions") or []
        versions = []
        preview_url = None
        preview_media = None

        for v in versions_raw:
            vid = v.get("id")
            images = v.get("images") or []
            files = v.get("files") or []
            selected = selected_version_id is not None and int(vid) == int(selected_version_id)
            if selected and images and not preview_url:
                preview_media = MetadataExtractor.pick_preview_image(images)
                preview_url = preview_media.get("url") if preview_media else None
            versions.append({
                "versionId": vid,
                "name": v.get("name", ""),
                "baseModel": v.get("baseModel", ""),
                "createdAt": self._iso_date(v.get("createdAt")),
                "updatedAt": self._iso_date(v.get("updatedAt")),
                "description": html_to_plain_text(v.get("description") or ""),
                "descriptionHtml": v.get("description") or "",
                "trainedWords": v.get("trainedWords") or [],
                "downloadCount": v.get("downloadCount"),
                "imagesCount": len(images),
                "filesCount": len(files),
                "selected": selected,
            })

        if not preview_url and versions_raw:
            preview_media = MetadataExtractor.pick_preview_image(
                versions_raw[0].get("images") or []
            )
            preview_url = preview_media.get("url") if preview_media else None

        if selected_version_id is None and versions:
            versions[0]["selected"] = True
            selected_version_id = versions[0]["versionId"]

        model_type = data.get("type") or ""
        model_desc_html = data.get("description") or ""
        model_desc_plain = html_to_plain_text(model_desc_html)
        return {
            "site": "civitai",
            "model": {
                "id": data.get("id"),
                "name": data.get("name", ""),
                "creator": creator_name,
                "description": model_desc_plain,
                "descriptionHtml": model_desc_html,
                "descriptionPlain": model_desc_plain,
                "type": model_type,
                "nsfw": data.get("nsfw"),
                "previewImage": preview_url,
                "previewMedia": preview_media,
                "tags": [t if isinstance(t, str) else t.get("name", "") for t in (data.get("tags") or [])],
            },
            "versions": versions,
            "selectedVersion": selected_version_id,
            "rawType": model_type,
            "suggestedFolder": self.suggest_folder(model_type),
        }

    @staticmethod
    def suggest_folder(model_type: str) -> str:
        t = (model_type or "").lower()
        if "checkpoint" in t:
            return "checkpoints"
        if any(x in t for x in ("lora", "locon", "lycoris", "dora")):
            return "loras"
        return "checkpoints"
