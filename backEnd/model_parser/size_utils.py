"""模型文件大小：Civitai API 的 sizeKB 字段实际为 KB（非字节）。"""
from __future__ import annotations


def normalize_size_kb(file_obj: dict) -> float | None:
    """
    Civitai: sizeKB 已是 KB（如 6775430 ≈ 6.46GB）。
    部分源仅有 size：若 > 10MB 量级则按字节转 KB，否则按 KB。
    """
    if file_obj.get("sizeKB") is not None:
        try:
            return float(file_obj["sizeKB"])
        except (TypeError, ValueError):
            pass
    raw = file_obj.get("size")
    if raw is None:
        return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    # 无 sizeKB 时：大于 1e7 多为字节（GB 级模型）
    if val >= 10_000_000:
        return val / 1024
    return val


def format_size_display(size_kb: float | None) -> str:
    if size_kb is None or size_kb <= 0:
        return ""
    if size_kb >= 1024 * 1024:
        return f"{size_kb / 1024 / 1024:.2f} GB"
    if size_kb >= 1024:
        return f"{size_kb / 1024:.2f} MB"
    if size_kb >= 1:
        return f"{size_kb:.0f} KB"
    return f"{size_kb:.2f} KB"
