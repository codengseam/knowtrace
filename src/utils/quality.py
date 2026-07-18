"""质量辅助 · HaloRead 沿袭符号兼容实现

strip_frontmatter 用于剥离 Markdown frontmatter，被 check_char_count.py 复用。
"""

from __future__ import annotations

import re

_FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def strip_frontmatter(text: str) -> str:
    """剥离 Markdown frontmatter，返回正文

    Args:
        text: 含 frontmatter 的 Markdown 文本

    Returns:
        去除 frontmatter 后的正文（若无 frontmatter，原样返回）
    """
    match = _FRONTMATTER_PATTERN.match(text)
    if not match:
        return text
    return text[match.end():]
