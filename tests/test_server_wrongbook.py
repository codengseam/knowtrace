"""src/server/services/wrongbook.py 单元测试

覆盖：submit 空字段 / submit 正常 / MD 备份文件名 sanitize / list_problems
用 isolated_db fixture 注入独立 SQLite 路径
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.server.services import wrongbook
from src.server import store


def test_submit_wrong_problem_basic(isolated_db: Path):
    """submit_wrong_problem 返回 id 和 md_path，SQLite + MD 备份都成功"""
    result = wrongbook.submit_wrong_problem(
        student_id="S001",
        knowledge_point_id="K7A008",
        problem_text="计算 -5 - (-3) = ?",
        error_type="减法转加法时忘记变号",
        student_answer="-2",
        correct_answer="-8",
    )
    assert result["id"] > 0
    md_path = Path(result["md_path"])
    assert md_path.exists()
    # MD 备份内容应含题面
    content = md_path.read_text(encoding="utf-8")
    assert "K7A008" in content
    assert "计算 -5 - (-3) = ?" in content
    assert "减法转加法时忘记变号" in content


def test_submit_writes_to_sqlite(isolated_db: Path):
    """submit_wrong_problem 后 list_wrong_problems 能查到"""
    wrongbook.submit_wrong_problem(
        student_id="S001",
        knowledge_point_id="K7A008",
        problem_text="题面",
    )
    rows = store.list_wrong_problems(student_id="S001")
    assert len(rows) == 1
    assert rows[0]["knowledge_point_id"] == "K7A008"


def test_md_backup_filename_sanitizes_student_id(isolated_db: Path):
    """student_id 含特殊字符时 MD 备份文件名被 sanitize"""
    wrongbook.submit_wrong_problem(
        student_id="S001/evil",  # 含斜杠
        knowledge_point_id="K7A008",
        problem_text="题面",
    )
    # 文件应存在于 sanitize 后的目录名下，不应创建 S001/evil 子目录穿越
    md_files = list(wrongbook.MD_BACKUP_DIR.rglob("*.md"))
    assert len(md_files) == 1
    # sanitize 后 student_id 应为 S001_evil
    assert "S001_evil" in str(md_files[0])
    # 不应出现 /evil/ 路径穿越
    assert "/evil/" not in str(md_files[0])


def test_md_backup_filename_sanitizes_knowledge_point_id(isolated_db: Path):
    """knowledge_point_id 含特殊字符时 MD 备份文件名被 sanitize（Phase 0 评审 R11）"""
    wrongbook.submit_wrong_problem(
        student_id="S001",
        knowledge_point_id="K7A008/../etc/passwd",  # 含路径穿越字符
        problem_text="题面",
    )
    md_files = list(wrongbook.MD_BACKUP_DIR.rglob("*.md"))
    assert len(md_files) == 1
    filename = md_files[0].name
    # 不应含原始的特殊字符
    assert ".." not in filename
    assert "/" not in filename
    # 应被 sanitize 为下划线：K7A008/../etc/passwd → K7A008____etc_passwd
    # （/../ 是 4 个非 word 非 - 字符，全部替换为 _）
    assert "K7A008____etc_passwd" in filename


def test_submit_multiple_problems(isolated_db: Path):
    """多次 submit 应产生多条记录 + 多个 MD 备份"""
    for i in range(3):
        wrongbook.submit_wrong_problem(
            student_id="S001",
            knowledge_point_id=f"K7A00{i}",
            problem_text=f"题{i}",
        )
    rows = store.list_wrong_problems(student_id="S001")
    assert len(rows) == 3
    md_files = list(wrongbook.MD_BACKUP_DIR.rglob("*.md"))
    assert len(md_files) == 3


def test_list_problems(isolated_db: Path):
    """list_problems 委托到 store.list_wrong_problems"""
    wrongbook.submit_wrong_problem(
        student_id="S001",
        knowledge_point_id="K7A001",
        problem_text="题",
    )
    rows = wrongbook.list_problems(student_id="S001")
    assert len(rows) == 1


def test_submit_with_optional_fields_none(isolated_db: Path):
    """submit_wrong_problem 可选字段 None 时不应报错"""
    result = wrongbook.submit_wrong_problem(
        student_id="S001",
        knowledge_point_id="K7A001",
        problem_text="题面",
        error_type=None,
        student_answer=None,
        correct_answer=None,
    )
    assert result["id"] > 0
    # MD 备份应写"未标注"
    md_path = Path(result["md_path"])
    content = md_path.read_text(encoding="utf-8")
    assert "未标注" in content
