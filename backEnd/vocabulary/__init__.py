"""提示词词库索引与补全建议。"""

from .service import (
    ensure_index,
    index_stats,
    merge_manifest_json,
    merge_manifest_upload,
    resolve,
    suggest,
)

__all__ = [
    "ensure_index",
    "index_stats",
    "merge_manifest_json",
    "merge_manifest_upload",
    "resolve",
    "suggest",
]
