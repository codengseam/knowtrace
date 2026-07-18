"""SQLite 存储层

错题/学情/出卷记录的持久化存储。
设计为文件级 SQLite，魔搭容器重启不丢，零运维。

Phase 0 仅初始化表结构与基础查询；
Phase 1 完善 MD 备份导出与重建索引。
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "wrongbook.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS wrong_problems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    grade TEXT NOT NULL,
    subject TEXT NOT NULL,
    knowledge_point_id TEXT NOT NULL,
    problem_text TEXT NOT NULL,
    student_answer TEXT,
    correct_answer TEXT,
    error_type TEXT,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_wrong_problems_student
    ON wrong_problems(student_id);

CREATE INDEX IF NOT EXISTS idx_wrong_problems_kp
    ON wrong_problems(knowledge_point_id);

CREATE TABLE IF NOT EXISTS students (
    student_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    grade TEXT NOT NULL,
    class TEXT,
    guardian_relation TEXT,
    preferred_dialect TEXT DEFAULT '普通话'
);

CREATE TABLE IF NOT EXISTS exam_papers (
    paper_id TEXT PRIMARY KEY,
    student_id TEXT,
    title TEXT NOT NULL,
    knowledge_points TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    docx_path TEXT,
    pdf_path TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""


def init_db(db_path: Path = DB_PATH) -> None:
    """初始化数据库与表结构（幂等）"""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(_SCHEMA)
        conn.commit()


@contextmanager
def get_conn(db_path: Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    """获取 SQLite 连接（上下文管理器，自动 commit/rollback）"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def insert_wrong_problem(
    student_id: str,
    knowledge_point_id: str,
    problem_text: str,
    error_type: str | None = None,
    student_answer: str | None = None,
    correct_answer: str | None = None,
    source: str = "manual",
    grade: str = "七年级上册",
    subject: str = "数学",
    db_path: Path = DB_PATH,
) -> int:
    """插入一条错题，返回自增 id"""
    with get_conn(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO wrong_problems
                (student_id, grade, subject, knowledge_point_id, problem_text,
                 student_answer, correct_answer, error_type, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                student_id, grade, subject, knowledge_point_id, problem_text,
                student_answer, correct_answer, error_type, source,
            ),
        )
        return cur.lastrowid or 0


def list_wrong_problems(
    student_id: str | None = None,
    limit: int = 100,
    db_path: Path = DB_PATH,
) -> list[dict]:
    """列出错题（可按学生过滤）"""
    with get_conn(db_path) as conn:
        if student_id:
            rows = conn.execute(
                "SELECT * FROM wrong_problems WHERE student_id = ? ORDER BY id DESC LIMIT ?",
                (student_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM wrong_problems ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
