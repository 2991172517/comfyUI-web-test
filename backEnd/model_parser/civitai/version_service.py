"""Civitai 版本详情 API。"""
from __future__ import annotations

import logging

from model_parser.civitai.metadata_extractor import MetadataExtractor
from model_parser.html_utils import html_to_plain_text, merge_descriptions
from model_parser.media_utils import classify_image_entry
from model_parser.http_client import CIVITAI_API_BASE, get_json

log = logging.getLogger("custom_project.model_parser.civitai.version")


class VersionService:
    def fetch_version(self, version_id: int) -> dict:
        url = f"{CIVITAI_API_BASE}/model-versions/{version_id}"
        log.info("GET %s", url)
        return get_json(url)

    def build_version_detail(
        self, data: dict, *, model_description_plain: str = ""
    ) -> dict:
        images = data.get("images") or []
        image_meta, workflow_json = MetadataExtractor.extract_image_metadata(images)
        preview = MetadataExtractor.pick_preview_image(images)
        static_preview_urls = MetadataExtractor.list_importable_preview_urls(images)
        files = MetadataExtractor.parse_files(data.get("files") or [])
        ver_html = data.get("description") or ""
        ver_plain = html_to_plain_text(ver_html)
        merged = merge_descriptions(model_description_plain, ver_plain)
        return {
            "site": "civitai",
            "versionId": data.get("id"),
            "name": data.get("name", ""),
            "description": merged,
            "descriptionHtml": ver_html,
            "versionDescription": ver_plain,
            "modelDescription": model_description_plain,
            "trainedWords": data.get("trainedWords") or [],
            "baseModel": data.get("baseModel", ""),
            "previewImage": preview,
            "staticPreviewUrls": static_preview_urls,
            "files": files,
            "images": [
                {
                    "url": i.get("url"),
                    "width": i.get("width"),
                    "height": i.get("height"),
                    "nsfwLevel": i.get("nsfwLevel"),
                    "mediaType": classify_image_entry(i),
                }
                for i in images
            ],
            "imageMetadata": image_meta,
            "workflowJson": workflow_json,
            "recommendedParameters": {},
            "downloadInfo": {"files": files},
        }
