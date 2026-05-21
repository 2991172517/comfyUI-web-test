"""模型参考图与说明：ComfyUI/models/{checkpoints|loras} 下与模型同名的文件夹或侧挂文件。"""
from __future__ import annotations

import logging
from pathlib import Path

from config import COMFYUI_ROOT, MODEL_PREVIEW_EXTENSIONS
from model_parser.source_url_utils import split_source_url_from_text

log = logging.getLogger("custom_project.model_preview")

VALID_FOLDERS = frozenset({"checkpoints", "loras"})
MODELS_ROOT = COMFYUI_ROOT / "models"
TXT_MAX_CHARS = 12_000


def models_folder_dir(folder: str) -> Path:
    if folder not in VALID_FOLDERS:
        raise ValueError(f"不支持的模型目录: {folder}")
    return MODELS_ROOT / folder


def _model_key(model_name: str) -> str:
    return model_name.replace("\\", "/")


def _model_file_path(folder: str, model_name: str) -> Path:
    return models_folder_dir(folder) / _model_key(model_name)


def _rel_in_folder(folder: str, path: Path) -> str:
    return str(path.relative_to(models_folder_dir(folder))).replace("\\", "/")


def _preview_url(folder: str, relative_path: str) -> str:
    from urllib.parse import quote

    parts = relative_path.replace("\\", "/").split("/")
    encoded = "/".join(quote(p, safe="") for p in parts)
    return f"/api/model-previews/{folder}/{encoded}"


def _filename_from_key(key: str) -> str:
    return Path(key).name


def _asset_dirs_for_model(parent: Path, filename: str) -> list[Path]:
    """与模型同名的资源目录：优先 stem（如 foo.safetensors → foo/），再尝试完整文件名目录。"""
    stem = Path(filename).stem
    seen: set[str] = set()
    dirs: list[Path] = []
    for name in (stem, filename):
        if not name or name in seen:
            continue
        seen.add(name)
        d = parent / name
        if d.is_dir():
            dirs.append(d)
    return dirs


def _sorted_images_in_dir(directory: Path) -> list[Path]:
    return sorted(
        f
        for f in directory.iterdir()
        if f.is_file() and f.suffix.lower() in MODEL_PREVIEW_EXTENSIONS
    )


def _sorted_txts_in_dir(directory: Path) -> list[Path]:
    return sorted(
        f for f in directory.iterdir() if f.is_file() and f.suffix.lower() == ".txt"
    )


def _collect_images_at(paths: list[Path], folder: str) -> list[dict]:
    items: list[dict] = []
    seen_rel: set[str] = set()
    for path in paths:
        if not path.is_file() or path.suffix.lower() not in MODEL_PREVIEW_EXTENSIONS:
            continue
        rel = _rel_in_folder(folder, path)
        if rel in seen_rel:
            continue
        seen_rel.add(rel)
        items.append({
            "index": len(items),
            "filename": path.name,
            "relative_path": rel,
            "url": _preview_url(folder, rel),
        })
    return items


def _sidecar_image_paths(parent: Path, filename: str) -> list[Path]:
    paths: list[Path] = []
    for ext in MODEL_PREVIEW_EXTENSIONS:
        sidecar = parent / f"{filename}{ext}"
        if sidecar.is_file():
            paths.append(sidecar)
    stem = Path(filename).stem
    if stem != filename:
        for ext in MODEL_PREVIEW_EXTENSIONS:
            alt = parent / f"{stem}{ext}"
            if alt.is_file():
                paths.append(alt)
    return paths


def list_previews_for_model(folder: str, model_name: str) -> list[dict]:
    """
    参考图查找顺序：
    1) 与模型 stem 或完整文件名同名的文件夹内全部图片（如 waiIllustriousSDXL_v170/*.png）
    2) 模型文件旁的侧挂图（model.safetensors.png、stem.png）
    """
    root = models_folder_dir(folder)
    if not root.is_dir():
        return []

    key = _model_key(model_name)
    model_path = _model_file_path(folder, model_name)
    parent = model_path.parent
    filename = _filename_from_key(key)

    image_paths: list[Path] = []
    seen: set[str] = set()

    def _add(path: Path) -> None:
        s = str(path.resolve())
        if s not in seen:
            seen.add(s)
            image_paths.append(path)

    for asset_dir in _asset_dirs_for_model(parent, filename):
        for img in _sorted_images_in_dir(asset_dir):
            _add(img)

    if image_paths:
        return _collect_images_at(image_paths, folder)

    for path in _sidecar_image_paths(parent, filename):
        _add(path)
    return _collect_images_at(image_paths, folder)


def read_summary_txt_for_model(folder: str, model_name: str) -> dict | None:
    """同名文件夹内按文件名排序的第一个 .txt（如 WAI_Illustrious_SDXL_总结.txt）。"""
    root = models_folder_dir(folder)
    if not root.is_dir():
        return None

    key = _model_key(model_name)
    parent = _model_file_path(folder, model_name).parent
    filename = _filename_from_key(key)

    for asset_dir in _asset_dirs_for_model(parent, filename):
        txts = _sorted_txts_in_dir(asset_dir)
        if not txts:
            continue
        path = txts[0]
        try:
            raw = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            log.warning("读取模型说明 txt 失败 %s: %s", path, e)
            continue
        source_url, body = split_source_url_from_text(raw)
        truncated = len(body) > TXT_MAX_CHARS
        content = body[:TXT_MAX_CHARS] if truncated else body
        return {
            "filename": path.name,
            "relative_path": _rel_in_folder(folder, path),
            "asset_dir": asset_dir.name,
            "content": content,
            "sourceUrl": source_url,
            "truncated": truncated,
        }
    return None


def get_model_assets(folder: str, model_name: str) -> dict:
    previews = list_previews_for_model(folder, model_name)
    summary = read_summary_txt_for_model(folder, model_name)
    return {
        "previews": previews,
        "has_preview": len(previews) > 0,
        "summary": summary,
        "has_summary": summary is not None,
    }


def enrich_model_files(folder: str, files: list[str]) -> list[dict]:
    result = []
    for name in files:
        assets = get_model_assets(folder, name)
        previews = assets["previews"]
        result.append({
            "name": name,
            "preview_count": len(previews),
            "previews": previews,
            "has_preview": len(previews) > 0,
            "has_summary": assets["has_summary"],
        })
    return result


def resolve_preview_file(folder: str, relative_path: str) -> Path | None:
    """relative_path 相对 models/{folder}/，防止路径穿越。"""
    base = models_folder_dir(folder).resolve()
    target = (base / relative_path).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        return None
    if target.is_file() and target.suffix.lower() in MODEL_PREVIEW_EXTENSIONS:
        if target.suffix.lower() in {".safetensors", ".ckpt", ".pt", ".pth", ".bin"}:
            return None
        return target
    return None


def models_root_for_folder(folder: str) -> str:
    return str(models_folder_dir(folder))
