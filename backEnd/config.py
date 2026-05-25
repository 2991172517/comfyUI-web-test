"""路径与运行时常量。支持源码运行与 PyInstaller 打包后的 exe。"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _bundle_dir() -> Path:
    """PyInstaller 解压/内置资源目录（含 editable_config.json 等）。"""
    if _is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _detect_project_root() -> Path:
    env = os.getenv("CUSTOM_PROJECT_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    if _is_frozen():
        # 默认：ComfyUI/CustomProject/bin/customproject-api.exe → CustomProject
        return Path(sys.executable).resolve().parent.parent
    return Path(__file__).resolve().parents[1]


def _detect_comfyui_root() -> Path:
    env = os.getenv("COMFYUI_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return _detect_project_root().parent


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


BACKEND_DIR = _bundle_dir()
PROJECT_ROOT = _detect_project_root()
COMFYUI_ROOT = _detect_comfyui_root()

# API 工作流目录（CustomProject/workflows）
WORKFLOWS_REL = "CustomProject/workflows"
WORKFLOWS_DIR = PROJECT_ROOT / "workflows"
WORKFLOW_TEMPLATE_ID = "First_api"
WORKFLOW_SEED_ID = "default_api"
WORKFLOW_HIDDEN_IDS = frozenset({WORKFLOW_TEMPLATE_ID, WORKFLOW_SEED_ID})
WORKFLOW_VARIANTS_DIR = WORKFLOWS_DIR / "variants"

EDITABLE_CONFIG = BACKEND_DIR / "editable_config.json"

COMFYUI_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188").strip()
API_HOST = os.getenv("API_HOST", "127.0.0.1").strip() or "127.0.0.1"
API_PORT = _env_int("API_PORT", 8000)

BATCH_OUTPUT_PREFIX = "custom_batch"
SINGLE_OUTPUT_PREFIX = "custom_single"

MODEL_PREVIEW_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif"})

VOCABULARY_MANIFEST_PATH = PROJECT_ROOT / "prompt" / "jsonData" / "manifest.json"

# 源码：backEnd/data；exe：CustomProject/data（可写，与源码目录分离）
if _is_frozen():
    RUNTIME_DATA_DIR = PROJECT_ROOT / "data"
else:
    RUNTIME_DATA_DIR = Path(__file__).resolve().parent / "data"

VOCABULARY_DB_PATH = RUNTIME_DATA_DIR / "vocabulary.db"
VOCABULARY_USER_PATH = RUNTIME_DATA_DIR / "vocabulary_user.json"

FRONTEND_DIST_DIR = PROJECT_ROOT / "frontEnd" / "dist"


def should_serve_frontend() -> bool:
    mode = os.getenv("SERVE_FRONTEND", "auto").strip().lower()
    if mode in ("0", "false", "no", "off"):
        return False
    if mode in ("1", "true", "yes", "on"):
        return FRONTEND_DIST_DIR.is_dir()
    return FRONTEND_DIST_DIR.is_dir()


def ensure_runtime_dirs() -> None:
    RUNTIME_DATA_DIR.mkdir(parents=True, exist_ok=True)
