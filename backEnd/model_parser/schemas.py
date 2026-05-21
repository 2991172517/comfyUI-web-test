"""统一返回结构（Civitai / Shakker 对齐）。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PreviewImage(BaseModel):
    url: str | None = None
    width: int | None = None
    height: int | None = None
    nsfw_level: str | int | None = Field(None, alias="nsfwLevel")

    model_config = {"populate_by_name": True}


class UnifiedModelSummary(BaseModel):
    id: str | int
    name: str = ""
    creator: str = ""
    description: str = ""
    type: str = ""
    nsfw: bool | None = None
    preview_image: str | None = Field(None, alias="previewImage")
    tags: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class UnifiedVersionSummary(BaseModel):
    version_id: str | int = Field(alias="versionId")
    name: str = ""
    base_model: str = Field("", alias="baseModel")
    created_at: str | None = Field(None, alias="createdAt")
    updated_at: str | None = Field(None, alias="updatedAt")
    description: str = ""
    trained_words: list[str] = Field(default_factory=list, alias="trainedWords")
    download_count: int | None = Field(None, alias="downloadCount")
    images_count: int = Field(0, alias="imagesCount")
    files_count: int = Field(0, alias="filesCount")
    selected: bool = False

    model_config = {"populate_by_name": True}


class ParseUrlIds(BaseModel):
    site: str
    model_id: str | int | None = Field(None, alias="modelId")
    model_version_id: str | int | None = Field(None, alias="modelVersionId")
    model_uuid: str | None = Field(None, alias="modelUuid")
    version_uuid: str | None = Field(None, alias="versionUuid")

    model_config = {"populate_by_name": True}


class ParseResponse(BaseModel):
    site: str
    model: UnifiedModelSummary
    versions: list[UnifiedVersionSummary] = Field(default_factory=list)
    selected_version: str | int | None = Field(None, alias="selectedVersion")
    raw_type: str | None = Field(None, alias="rawType")
    suggested_folder: str | None = Field(None, alias="suggestedFolder")

    model_config = {"populate_by_name": True}


class ModelFileInfo(BaseModel):
    name: str = ""
    size_kb: float | None = Field(None, alias="sizeKB")
    size_display: str = Field("", alias="sizeDisplay")
    type: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    download_url: str | None = Field(None, alias="downloadUrl")
    hashes: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class ImageMetadata(BaseModel):
    url: str | None = None
    prompt: str | None = None
    negative_prompt: str | None = Field(None, alias="negativePrompt")
    sampler: str | None = None
    cfg_scale: float | None = Field(None, alias="cfgScale")
    steps: int | None = None
    seed: int | str | None = None
    workflow: Any | None = None

    model_config = {"populate_by_name": True}


class VersionDetailResponse(BaseModel):
    site: str
    version_id: str | int = Field(alias="versionId")
    name: str = ""
    description: str = ""
    trained_words: list[str] = Field(default_factory=list, alias="trainedWords")
    base_model: str = Field("", alias="baseModel")
    preview_image: PreviewImage | None = Field(None, alias="previewImage")
    files: list[ModelFileInfo] = Field(default_factory=list)
    images: list[PreviewImage] = Field(default_factory=list)
    image_metadata: list[ImageMetadata] = Field(default_factory=list, alias="imageMetadata")
    workflow_json: Any | None = Field(None, alias="workflowJson")
    recommended_parameters: dict[str, Any] = Field(
        default_factory=dict, alias="recommendedParameters"
    )
    download_info: dict[str, Any] = Field(default_factory=dict, alias="downloadInfo")

    model_config = {"populate_by_name": True}
