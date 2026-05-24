"""模型参考图与说明：ComfyUI/models/{checkpoints|loras} 下与模型同名的文件夹或侧挂文件。"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from config import COMFYUI_ROOT, MODEL_PREVIEW_EXTENSIONS
from model_parser.source_url_utils import split_source_url_from_text

log = logging.getLogger("custom_project.model_preview")

VALID_FOLDERS = frozenset({"checkpoints", "loras"})
MODELS_ROOT = COMFYUI_ROOT / "models"
TXT_MAX_CHARS = 12_000
MAX_UPLOAD_PREVIEW_BYTES = 15 * 1024 * 1024
MAX_UPLOAD_FILES_PER_REQUEST = 10

_MIME_TO_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


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


def _pick_summary_txt(txts: list[Path]) -> Path | None:
    """优先读取导入时写入的 模型说明.txt。"""
    if not txts:
        return None
    prefer_names = ("模型说明.txt", "readme.txt", "README.txt")
    lower_map = {p.name.lower(): p for p in txts}
    for name in prefer_names:
        hit = lower_map.get(name.lower())
        if hit:
            return hit
    return txts[0]


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
        path = _pick_summary_txt(txts)
        if not path:
            continue
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


def ensure_asset_dir_for_model(folder: str, model_name: str) -> Path:
    """确保存在与模型 stem 同名的资源目录（用于写入说明与参考图）。"""
    model_path = _model_file_path(folder, model_name)
    if not model_path.is_file():
        raise FileNotFoundError(f"模型文件不存在: {model_name}")
    parent = model_path.parent
    filename = _filename_from_key(_model_key(model_name))
    dirs = _asset_dirs_for_model(parent, filename)
    if dirs:
        return dirs[0]
    stem = Path(filename).stem
    asset_dir = parent / stem
    asset_dir.mkdir(parents=True, exist_ok=True)
    return asset_dir


def write_summary_txt_for_model(
    folder: str,
    model_name: str,
    content: str,
    *,
    source_url: str = "",
) -> dict:
    """写入或覆盖 模型说明.txt。"""
    from model_parser.source_url_utils import format_with_source_url

    asset_dir = ensure_asset_dir_for_model(folder, model_name)
    full = format_with_source_url(source_url, (content or "").strip())
    path = asset_dir / "模型说明.txt"
    path.write_text(full, encoding="utf-8")
    log.info("wrote model summary %s/%s -> %s", folder, model_name, path)
    summary = read_summary_txt_for_model(folder, model_name)
    return {
        "ok": True,
        "summary": summary,
        "has_summary": summary is not None,
        "asset_dir": asset_dir.name,
    }


def delete_model_from_disk(
    folder: str,
    model_name: str,
    *,
    delete_asset_dirs: bool = True,
) -> dict:
    """删除模型权重文件；可选删除同名资源目录与侧挂预览图。"""
    model_path = _model_file_path(folder, model_name)
    if not model_path.is_file():
        raise FileNotFoundError(f"模型文件不存在: {model_name}")

    parent = model_path.parent
    filename = _filename_from_key(_model_key(model_name))
    removed_dirs: list[str] = []
    removed_files: list[str] = []

    if delete_asset_dirs:
        for asset_dir in _asset_dirs_for_model(parent, filename):
            rel = asset_dir.name
            shutil.rmtree(asset_dir, ignore_errors=False)
            removed_dirs.append(rel)

    for path in _sidecar_image_paths(parent, filename):
        try:
            path.unlink()
            removed_files.append(path.name)
        except OSError as e:
            log.warning("删除侧挂预览失败 %s: %s", path, e)

    model_path.unlink()
    removed_files.append(model_path.name)
    log.info("deleted model %s/%s dirs=%s", folder, model_name, removed_dirs)
    return {
        "ok": True,
        "folder": folder,
        "name": model_name,
        "removed_dirs": removed_dirs,
        "removed_files": removed_files,
    }


def _ext_from_upload(filename: str, content_type: str | None) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix in MODEL_PREVIEW_EXTENSIONS:
        return suffix
    if content_type:
        ct = content_type.split(";", 1)[0].strip().lower()
        hit = _MIME_TO_EXT.get(ct)
        if hit:
            return hit
    raise ValueError(
        f"不支持的图片格式，请使用: {', '.join(sorted(MODEL_PREVIEW_EXTENSIONS))}"
    )


def _allocate_preview_path(asset_dir: Path, ext: str) -> Path:
    ext = ext.lower()
    if ext not in MODEL_PREVIEW_EXTENSIONS:
        raise ValueError(f"不支持的图片格式: {ext}")
    used = {p.name.lower() for p in _sorted_images_in_dir(asset_dir)}
    for n in range(1, 1000):
        candidate = asset_dir / f"preview_{n:02d}{ext}"
        if candidate.name.lower() not in used:
            return candidate
    raise ValueError("参考图数量过多，请清理后再上传")


def save_uploaded_previews(
    folder: str,
    model_name: str,
    uploads: list[tuple[bytes, str, str | None]],
) -> dict:
    """将本地上传的图片写入模型同名资源目录（preview_01.png 等）。"""
    if not uploads:
        raise ValueError("未选择图片文件")
    if len(uploads) > MAX_UPLOAD_FILES_PER_REQUEST:
        raise ValueError(f"单次最多上传 {MAX_UPLOAD_FILES_PER_REQUEST} 张图片")

    asset_dir = ensure_asset_dir_for_model(folder, model_name)
    saved: list[str] = []

    for data, filename, content_type in uploads:
        if not data:
            raise ValueError(f"文件为空: {filename or '未命名'}")
        if len(data) > MAX_UPLOAD_PREVIEW_BYTES:
            raise ValueError(
                f"文件过大: {filename or '未命名'}（上限 {MAX_UPLOAD_PREVIEW_BYTES // (1024 * 1024)}MB）"
            )
        ext = _ext_from_upload(filename, content_type)
        dest = _allocate_preview_path(asset_dir, ext)
        dest.write_bytes(data)
        saved.append(dest.name)
        log.info("saved model preview upload %s/%s -> %s", folder, model_name, dest)

    assets = get_model_assets(folder, model_name)
    return {
        "ok": True,
        "folder": folder,
        "name": model_name,
        "saved": saved,
        "asset_dir": asset_dir.name,
        "previews": assets["previews"],
        "has_preview": assets["has_preview"],
        "summary": assets["summary"],
        "has_summary": assets["has_summary"],
    }


def _preview_belongs_to_model(folder: str, model_name: str, path: Path) -> bool:
    key = _model_key(model_name)
    parent = _model_file_path(folder, model_name).parent
    filename = _filename_from_key(key)
    resolved = path.resolve()

    for asset_dir in _asset_dirs_for_model(parent, filename):
        try:
            resolved.relative_to(asset_dir.resolve())
            return True
        except ValueError:
            continue

    for side in _sidecar_image_paths(parent, filename):
        if side.resolve() == resolved:
            return True
    return False


def delete_preview_for_model(folder: str, model_name: str, relative_path: str) -> dict:
    """删除指定模型的单张参考图（资源目录内或侧挂图）。"""
    rel = str(relative_path or "").replace("\\", "/").strip()
    if not rel:
        raise ValueError("缺少 relative_path")

    path = resolve_preview_file(folder, rel)
    if not path:
        raise FileNotFoundError("预览图不存在")

    if not _model_file_path(folder, model_name).is_file():
        raise FileNotFoundError(f"模型文件不存在: {model_name}")

    if not _preview_belongs_to_model(folder, model_name, path):
        raise ValueError("该预览图不属于此模型")

    removed_name = path.name
    path.unlink()
    log.info("deleted model preview %s/%s -> %s", folder, model_name, path)

    assets = get_model_assets(folder, model_name)
    return {
        "ok": True,
        "folder": folder,
        "name": model_name,
        "removed": removed_name,
        "relative_path": rel,
        "previews": assets["previews"],
        "has_preview": assets["has_preview"],
        "summary": assets["summary"],
        "has_summary": assets["has_summary"],
    }


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
