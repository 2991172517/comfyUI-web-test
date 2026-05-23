from pathlib import Path

# ComfyUI 根目录（本仓库）
COMFYUI_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# API 工作流目录（CustomProject/workflows，母版 First_api.json）
WORKFLOWS_REL = "CustomProject/workflows"
WORKFLOWS_DIR = PROJECT_ROOT / "workflows"
WORKFLOW_TEMPLATE_ID = "First_api"
WORKFLOW_VARIANTS_DIR = WORKFLOWS_DIR / "variants"

EDITABLE_CONFIG = Path(__file__).parent / "editable_config.json"

# ComfyUI 官方 Web/API 端口（只读连接，本服务不会 bind 此端口）
COMFYUI_URL = "http://127.0.0.1:8188"
# CustomProject 控制台后端（与 ComfyUI 完全独立）
API_HOST = "127.0.0.1"
API_PORT = 8000

# 批量输出根目录（相对 ComfyUI output）
BATCH_OUTPUT_PREFIX = "custom_batch"
# 单抽历史记录（相对 ComfyUI output）
SINGLE_OUTPUT_PREFIX = "custom_single"

# 模型参考图扩展名（文件放在 ComfyUI/models/{checkpoints|loras}/ 下，与模型同目录）
MODEL_PREVIEW_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif"})

# 提示词词库（manifest → SQLite 索引，供输入补全）
VOCABULARY_MANIFEST_PATH = PROJECT_ROOT / "prompt" / "jsonData" / "manifest.json"
VOCABULARY_DB_PATH = Path(__file__).parent / "data" / "vocabulary.db"
VOCABULARY_USER_PATH = Path(__file__).parent / "data" / "vocabulary_user.json"
