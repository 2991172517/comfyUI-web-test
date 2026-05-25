"""Checkpoint / LoRA 扫描路径配置（默认 ComfyUI/models 下标准目录）。"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from config import COMFYUI_ROOT, PROJECT_ROOT

log = logging.getLogger("custom_project.model_paths")

VALID_FOLDERS = frozenset({"checkpoints", "loras"})
MODEL_EXTENSIONS = frozenset({".safetensors", ".ckpt", ".pt", ".pth", ".bin"})
SETTINGS_PATH = PROJECT_ROOT / "config" / "model_paths.json"
# 相对配置根目录，最多再向下扫描的子目录层数（不含根目录本身）
MAX_SCAN_SUBDIR_DEPTH = 3


def default_folder_path(folder: str) -> Path:
    if folder not in VALID_FOLDERS:
        raise ValueError(f"不支持的目录: {folder}")
    return (COMFYUI_ROOT / "models" / folder).resolve()


def _empty_settings() -> dict:
    return {
        "checkpoints": "",
        "loras": "",
        "notes": "留空表示使用 ComfyUI 默认路径（COMFYUI_ROOT/models/checkpoints|loras）",
    }


def load_settings() -> dict:
    if not SETTINGS_PATH.is_file():
        return _empty_settings()
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    base = _empty_settings()
    for key in ("checkpoints", "loras"):
        raw = data.get(key)
        base[key] = str(raw).strip() if raw else ""
    return base


def save_settings(payload: dict) -> dict:
    base = _empty_settings()
    for key in ("checkpoints", "loras"):
        raw = payload.get(key)
        base[key] = str(raw).strip() if raw else ""
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(base, f, ensure_ascii=False, indent=2)
    log.info("saved model paths %s", SETTINGS_PATH)
    return get_settings_response()


def resolve_folder_path(folder: str) -> Path:
    """返回用于扫描/读写模型文件的目录。"""
    if folder not in VALID_FOLDERS:
        raise ValueError(f"不支持的目录: {folder}")
    settings = load_settings()
    custom = (settings.get(folder) or "").strip()
    if custom:
        path = Path(custom).expanduser()
        if not path.is_absolute():
            path = (COMFYUI_ROOT / path).resolve()
        else:
            path = path.resolve()
        return path
    return default_folder_path(folder)


def get_settings_response() -> dict:
    settings = load_settings()
    resolved = {
        name: str(resolve_folder_path(name))
        for name in sorted(VALID_FOLDERS)
    }
    defaults = {
        name: str(default_folder_path(name))
        for name in sorted(VALID_FOLDERS)
    }
    return {
        "settings": settings,
        "resolved": resolved,
        "defaults": defaults,
        "comfyui_root": str(COMFYUI_ROOT),
        "config_path": str(SETTINGS_PATH),
        "max_scan_subdir_depth": MAX_SCAN_SUBDIR_DEPTH,
    }


def _is_model_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in MODEL_EXTENSIONS


def _iter_model_files_limited(root: Path, max_subdir_depth: int = MAX_SCAN_SUBDIR_DEPTH):
    """在 root 下遍历模型文件，最多进入 max_subdir_depth 层子目录。"""
    root = root.resolve()
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        rel_dir = Path(dirpath).relative_to(root)
        depth = len(rel_dir.parts)
        if depth >= max_subdir_depth:
            dirnames.clear()
        for fn in filenames:
            path = Path(dirpath) / fn
            if _is_model_file(path):
                yield path


def list_model_filenames(folder: str) -> list[str]:
    """扫描配置目录下权重文件（相对路径，最多 MAX_SCAN_SUBDIR_DEPTH 层子目录）。"""
    root = resolve_folder_path(folder)
    if not root.is_dir():
        return []
    names: list[str] = []
    for path in _iter_model_files_limited(root):
        names.append(str(path.relative_to(root)).replace("\\", "/"))
    return sorted(set(names))
