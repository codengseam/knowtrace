"""分类映射完整性回归测试。

防止「新增专栏的 category 未在 DISPLAY_CATEGORY_MAP 定义，导致专栏
掉入 other 黑洞、首页 4 大栏不显示」问题复发。
参见 tests/bug_regression_list.md BUG-051。
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def _read_all_categories():
    """读取 output/ 下所有专栏 _meta.yaml 的 category。"""
    base = os.path.join(os.path.dirname(__file__), '..', 'output')
    cats = set()
    for col in sorted(os.listdir(base)):
        meta = os.path.join(base, col, '_meta.yaml')
        if not os.path.isfile(meta):
            continue
        with open(meta, encoding='utf-8') as f:
            content = f.read()
        m = re.search(r'^category:\s*(.+)$', content, re.MULTILINE)
        if m:
            cats.add(m.group(1).strip())
    return cats


def test_all_categories_have_display_mapping():
    """每个专栏的 category 必须在 DISPLAY_CATEGORY_MAP 中有定义。

    若此测试失败，说明有专栏的 category 没有被映射到首页 4 大栏，
    会在首页「其他」黑洞里消失。需在 build_site.py 的
    DISPLAY_CATEGORY_MAP 补上映射。
    """
    from scripts.build_site import DISPLAY_CATEGORY_MAP

    used_cats = _read_all_categories()
    unmapped = used_cats - set(DISPLAY_CATEGORY_MAP.keys())
    assert not unmapped, (
        f"以下 category 未在 DISPLAY_CATEGORY_MAP 定义，对应专栏会在首页消失:\n"
        f"  {unmapped}\n"
        f"请在 scripts/build_site.py 的 DISPLAY_CATEGORY_MAP 补上映射。"
    )


def test_no_book_in_other_after_build():
    """build_site 后不应有专栏落在 other 分类。

    other 是兜底分类，首页 4 大栏不展示。任何专栏落入 other 都意味着
    用户在首页看不到它——这正是 BUG-051 的现象。
    """
    base = os.path.join(os.path.dirname(__file__), '..')
    result = subprocess.run(
        [sys.executable, 'scripts/build_site.py'],
        capture_output=True, text=True, cwd=base, timeout=120,
    )
    assert result.returncode == 0, f"build_site 失败:\n{result.stderr}"

    index_path = os.path.join(base, 'site', 'data', 'index.json')
    with open(index_path, encoding='utf-8') as f:
        data = json.load(f)
    # index.json 可能是 list 或 dict（含 books 键）
    if isinstance(data, dict):
        books = data.get('books', data.get('data', []))
    else:
        books = data

    others = [b.get('title', '?') for b in books if b.get('display_category') == 'other']
    assert not others, (
        f"以下专栏落入 other 黑洞，首页 4 大栏不显示:\n  {others}\n"
        f"请在 DISPLAY_CATEGORY_MAP 补上对应 category 的映射。"
    )
