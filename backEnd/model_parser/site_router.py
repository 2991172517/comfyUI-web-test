"""站点路由：统一 parse / version 接口。"""
from __future__ import annotations

import logging

from model_parser.civitai.model_service import ModelService as CivitaiModelService
from model_parser.civitai.parser import CivitaiParser
from model_parser.civitai.version_service import VersionService as CivitaiVersionService
from model_parser.shakker.page_extractor import ShakkerMetadataExtractor
from model_parser.shakker.parser import ShakkerParser

log = logging.getLogger("custom_project.model_parser.router")


class SiteRouter:
    def __init__(self) -> None:
        self._civitai_models = CivitaiModelService()
        self._civitai_versions = CivitaiVersionService()

    @staticmethod
    def detect_site(url: str) -> str:
        if CivitaiParser.is_civitai_url(url):
            return "civitai"
        if ShakkerParser.is_shakker_url(url):
            return "shakker"
        raise ValueError("不支持的站点，目前支持 Civitai 与 Shakker")

    def parse_url(self, url: str) -> dict:
        site = self.detect_site(url)
        if site == "civitai":
            ids = CivitaiParser.parse_url(url)
            data = self._civitai_models.fetch_model(int(ids["modelId"]))
            return self._civitai_models.build_parse_response(data, ids.get("modelVersionId"))
        ids = ShakkerParser.parse_url(url)
        return ShakkerMetadataExtractor.parse_model_page(
            ids["modelUuid"], ids.get("versionUuid")
        )

    def get_version_detail(
        self,
        site: str,
        version_id: str | int,
        model_id: str | None = None,
        *,
        model_description_plain: str = "",
    ) -> dict:
        site = (site or "").lower()
        if site == "civitai":
            model_plain = model_description_plain
            if not model_plain and model_id:
                try:
                    mdata = self._civitai_models.fetch_model(int(model_id))
                    from model_parser.html_utils import html_to_plain_text

                    model_plain = html_to_plain_text(mdata.get("description") or "")
                except Exception:
                    pass
            data = self._civitai_versions.fetch_version(int(version_id))
            return self._civitai_versions.build_version_detail(
                data, model_description_plain=model_plain
            )
        if site == "shakker":
            if not model_id:
                raise ValueError("Shakker 版本详情需要 modelUuid（query: modelId）")
            return ShakkerMetadataExtractor.parse_version_detail(str(model_id), str(version_id))
        raise ValueError(f"未知站点: {site}")
