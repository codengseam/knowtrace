"""SQLite 存储层

错题/学情/出卷记录的持久化存储。
设计为文件级 SQLite，魔搭容器重启不丢，零运维。

Phase 0 仅初始化表结构与基础查询；
Phase 1 完善 MD 备份导出与重建索引。
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

# DB_PATH 优先读环境变量（便于单元测试用 tmp_path 注入），否则用项目默认路径
_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "wrongbook.db"
DB_PATH = Path(os.environ.get("KNOWTRACE_DB_PATH", str(_DEFAULT_DB_PATH)))

# WAL 模式 + 30s busy timeout，避免多用户并发录入时 database is locked
# （Phase 0 评审 P1 R4 修复）
_BUSY_TIMEOUT_SEC = 30

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


def init_db(db_path: Path | None = None) -> None:
    """初始化数据库与表结构（幂等）

    启用 WAL 模式提升并发读写；若容器只读挂载导致 PRAGMA 失败，降级为默认模式不阻断。
    注意：默认参数不直接绑 DB_PATH，而是在调用时读取模块级变量，
    避免 monkeypatch store.DB_PATH 后默认参数仍指向旧值（Python 默认参数陷阱）。
    """
    if db_path is None:
        db_path = DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path, timeout=_BUSY_TIMEOUT_SEC) as conn:
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError:
            # 容器只读挂载时 PRAGMA 可能失败，降级为默认 journal_mode 不阻断
            pass
        conn.executescript(_SCHEMA)
        conn.commit()


@contextmanager
def get_conn(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """获取 SQLite 连接（上下文管理器，自动 commit/rollback）

    设置 30s busy timeout，避免多用户并发时立即抛 database is locked。
    注意：默认参数不直接绑 DB_PATH，调用时读取模块级变量（避免默认参数陷阱）。
    """
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path, timeout=_BUSY_TIMEOUT_SEC)
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
    db_path: Path | None = None,
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
    db_path: Path | None = None,
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
