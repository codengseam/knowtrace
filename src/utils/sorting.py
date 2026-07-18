"""排序辅助 · HaloRead 沿袭符号兼容实现

knowtrace 的 content/ 只有"初中数学教研"一本书，无阶段模式，
BOOK_CATEGORY_ORDER 与 STAGE_MODE_BOOKS 均为空容器；
sort_notes_tree 为最小可用实现（按 sort/chapter_sort 字段递归排序）。
"""

from __future__ import annotations

from typing import Any

# knowtrace 无阶段模式书籍，BOOK_CATEGORY_ORDER 与 STAGE_MODE_BOOKS 留空
# HaloRead 沿袭脚本通过 `if book not in STAGE_MODE_BOOKS` 判断走默认分支
BOOK_CATEGORY_ORDER: dict[str, dict[str, int]] = {}
STAGE_MODE_BOOKS: set[str] = set()

# 中文数字 → 阿拉伯数字映射（支持 0-99 常用范围）
_CHINESE_DIGITS = {
    "零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}
_CHINESE_UNITS = {"十": 10, "百": 100, "千": 1000}


def parse_chinese_number(s: str) -> int:
    """中文数字转 int

    支持 "一"→1, "十"→10, "十五"→15, "二十"→20, "二十三"→23, "一百"→100。
    空串或非中文数字返回 0。

    Args:
        s: 中文数字字符串（如 "二十三"）

    Returns:
        对应整数
    """
    if not s:
        return 0
    s = s.strip()
    if not s:
        return 0

    # 纯阿拉伯数字直接返回
    if s.isdigit():
        return int(s)

    total = 0
    current = 0
    for ch in s:
        if ch in _CHINESE_DIGITS:
            current = _CHINESE_DIGITS[ch]
        elif ch in _CHINESE_UNITS:
            unit = _CHINESE_UNITS[ch]
            if current == 0:
                current = 1  # "十" 单独出现视为 10
            total += current * unit
            current = 0
        else:
            # 非法字符，返回已累计值
            return total + current
    return total + current


def sort_notes_tree(tree: list[dict[str, Any]]) -> None:
    """对笔记树原地排序（按 sort/chapter_sort 字段递归）

    HaloRead 沿袭符号，被 build_site.py 调用。
    knowtrace 阶段实现最小可用版本：按 sort 字段升序排序，
    递归处理 children。

    Args:
        tree: 笔记树，每个节点是 dict，可能含 "sort"（int）与 "children"（list）
    """
    if not tree:
        return
    tree.sort(key=lambda n: _safe_sort_key(n))
    for node in tree:
        children = node.get("children")
        if isinstance(children, list):
            sort_notes_tree(children)


def _safe_sort_key(node: dict[str, Any]) -> tuple[int, str]:
    """排序键：优先 sort 字段，其次 chapter_sort，最后 name 兜底"""
    s = node.get("sort")
    if isinstance(s, (int, float)):
        return (int(s), "")
    cs = node.get("chapter_sort")
    if isinstance(cs, (int, float)):
        return (int(cs), "")
    if isinstance(cs, str) and cs.isdigit():
        return (int(cs), "")
    return (0, str(node.get("name", node.get("title", ""))))
