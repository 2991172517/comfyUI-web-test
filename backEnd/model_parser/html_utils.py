"""Civitai 等返回的 HTML 说明转为可读纯文本。"""
from __future__ import annotations

import re
from html import unescape


def html_to_plain_text(html: str) -> str:
    if not html or not str(html).strip():
        return ""
    text = str(html)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.I | re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.I | re.S)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p>", "\n", text, flags=re.I)
    text = re.sub(r"</li>", "\n", text, flags=re.I)
    text = re.sub(r"</h[1-6]>", "\n", text, flags=re.I)
    text = re.sub(r"</pre>", "\n", text, flags=re.I)
    text = re.sub(r"<pre[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def merge_descriptions(model_plain: str, version_plain: str) -> str:
    """模型页完整说明 + 版本补充（避免版本短说明覆盖模型页）。"""
    model_plain = (model_plain or "").strip()
    version_plain = (version_plain or "").strip()
    if not model_plain:
        return version_plain
    if not version_plain:
        return model_plain
    if version_plain in model_plain:
        return model_plain
    if len(version_plain) < 80:
        return model_plain
    return f"{model_plain}\n\n--- 当前版本补充 ---\n\n{version_plain}"
