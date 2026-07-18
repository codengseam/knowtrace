"""knowtrace · 通用工具模块

提供 sorting/quality 等通用辅助函数，被 scripts/ 与 tests/ 复用。
Phase 0 阶段为 HaloRead 沿袭脚本提供最小兼容实现；
后续按 knowtrace 实际需求扩展。
"""

from .sorting import (
    BOOK_CATEGORY_ORDER,
    STAGE_MODE_BOOKS,
    parse_chinese_number,
    sort_notes_tree,
)
from .quality import strip_frontmatter

__all__ = [
    "BOOK_CATEGORY_ORDER",
    "STAGE_MODE_BOOKS",
    "parse_chinese_number",
    "sort_notes_tree",
    "strip_frontmatter",
]
