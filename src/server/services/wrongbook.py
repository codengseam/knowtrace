"""错题录入服务

支持文本/MD/图片三种录入方式，写入 SQLite + MD 备份。
"""

from __future__ import annotations

import re
from pathlib import Path

from ..store import insert_wrong_problem, list_wrong_problems, DB_PATH

MD_BACKUP_DIR = DB_PATH.parent / "wrongbook_md"

# 文件名 sanitize：仅允许字母数字下划线连字符，其余替换为下划线
_SANITIZE_RE = re.compile(r"[^\w\-]", re.UNICODE)


def _sanitize_filename(value: str) -> str:
    """把字符串 sanitize 成文件名安全形式"""
    return _SANITIZE_RE.sub("_", value)


def submit_wrong_problem(
    student_id: str,
    knowledge_point_id: str,
    problem_text: str,
    error_type: str | None = None,
    student_answer: str | None = None,
    correct_answer: str | None = None,
    source: str = "manual",
    grade: str = "七年级上册",
) -> dict:
    """提交错题 → SQLite + MD 备份

    Returns: {"id": int, "md_path": str}
    """
    problem_id = insert_wrong_problem(
        student_id=student_id,
        knowledge_point_id=knowledge_point_id,
        problem_text=problem_text,
        error_type=error_type,
        student_answer=student_answer,
        correct_answer=correct_answer,
        source=source,
        grade=grade,
    )

    md_path = _write_md_backup(
        student_id=student_id,
        problem_id=problem_id,
        knowledge_point_id=knowledge_point_id,
        problem_text=problem_text,
        error_type=error_type,
    )

    return {"id": problem_id, "md_path": str(md_path)}


def list_problems(student_id: str | None = None, limit: int = 100) -> list[dict]:
    """列出错题"""
    return list_wrong_problems(student_id=student_id, limit=limit)


def _write_md_backup(
    student_id: str,
    problem_id: int,
    knowledge_point_id: str,
    problem_text: str,
    error_type: str | None,
) -> Path:
    """写 MD 备份文件（人可读，Git 友好）

    文件名 sanitize：student_id 和 knowledge_point_id 都做安全处理，
    防止 ../ 或特殊字符导致异常路径（Phase 0 评审 R11 修复）。
    """
    MD_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    safe_student = _sanitize_filename(student_id)
    safe_kp = _sanitize_filename(knowledge_point_id)
    md_path = MD_BACKUP_DIR / safe_student / f"{problem_id:06d}_{safe_kp}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    content = f"""# 错题 #{problem_id}

- 学生 ID: {student_id}
- 知识点 ID: {knowledge_point_id}
- 错因: {error_type or "未标注"}

## 题面

{problem_text}
"""
    md_path.write_text(content, encoding="utf-8")
    return md_path
