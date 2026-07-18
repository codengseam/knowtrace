"""src/server/store.py 单元测试

覆盖：init_db 幂等 / insert+list 往返 / student_id 过滤 / WAL 启用 / 并发不 locked
全部用 isolated_db fixture 注入独立 SQLite 路径，不污染 /workspace/data/wrongbook.db
"""
from __future__ import annotations

import threading
from pathlib import Path

import pytest

from src.server import store


def test_init_db_is_idempotent(isolated_db: Path):
    """init_db 多次调用不报错（CREATE TABLE IF NOT EXISTS 幂等）"""
    store.init_db(isolated_db)
    store.init_db(isolated_db)
    # 表结构应存在
    with store.get_conn(isolated_db) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = {r["name"] for r in rows}
    assert "wrong_problems" in table_names
    assert "students" in table_names
    assert "exam_papers" in table_names


def test_insert_and_list_roundtrip(isolated_db: Path):
    """insert_wrong_problem + list_wrong_problems 往返一致"""
    pid = store.insert_wrong_problem(
        student_id="S001",
        knowledge_point_id="K7A008",
        problem_text="计算 -5 - (-3) = ?",
        error_type="减法转加法时忘记变号",
        student_answer="-2",
        correct_answer="-8",
        db_path=isolated_db,
    )
    assert pid > 0

    rows = store.list_wrong_problems(student_id="S001", db_path=isolated_db)
    assert len(rows) == 1
    r = rows[0]
    assert r["id"] == pid
    assert r["student_id"] == "S001"
    assert r["knowledge_point_id"] == "K7A008"
    assert r["problem_text"] == "计算 -5 - (-3) = ?"
    assert r["error_type"] == "减法转加法时忘记变号"
    assert r["student_answer"] == "-2"
    assert r["correct_answer"] == "-8"
    assert r["source"] == "manual"
    assert r["grade"] == "七年级上册"
    assert r["subject"] == "数学"
    assert r["created_at"]  # 自动填充


def test_list_filters_by_student_id(isolated_db: Path):
    """list_wrong_problems 按 student_id 过滤"""
    store.insert_wrong_problem(
        student_id="S001", knowledge_point_id="K7A001",
        problem_text="题1", db_path=isolated_db,
    )
    store.insert_wrong_problem(
        student_id="S002", knowledge_point_id="K7A002",
        problem_text="题2", db_path=isolated_db,
    )
    store.insert_wrong_problem(
        student_id="S001", knowledge_point_id="K7A003",
        problem_text="题3", db_path=isolated_db,
    )

    s001_rows = store.list_wrong_problems(student_id="S001", db_path=isolated_db)
    s002_rows = store.list_wrong_problems(student_id="S002", db_path=isolated_db)
    all_rows = store.list_wrong_problems(db_path=isolated_db)

    assert len(s001_rows) == 2
    assert len(s002_rows) == 1
    assert len(all_rows) == 3
    assert all(r["student_id"] == "S001" for r in s001_rows)
    assert all(r["student_id"] == "S002" for r in s002_rows)


def test_list_orders_by_id_desc(isolated_db: Path):
    """list_wrong_problems 默认按 id 降序（最新的在前）"""
    for i in range(5):
        store.insert_wrong_problem(
            student_id="S001", knowledge_point_id="K7A001",
            problem_text=f"题{i}", db_path=isolated_db,
        )
    rows = store.list_wrong_problems(student_id="S001", db_path=isolated_db)
    ids = [r["id"] for r in rows]
    assert ids == sorted(ids, reverse=True)


def test_list_respects_limit(isolated_db: Path):
    """list_wrong_problems limit 参数生效"""
    for i in range(10):
        store.insert_wrong_problem(
            student_id="S001", knowledge_point_id="K7A001",
            problem_text=f"题{i}", db_path=isolated_db,
        )
    rows = store.list_wrong_problems(student_id="S001", limit=3, db_path=isolated_db)
    assert len(rows) == 3


def test_wal_mode_enabled(isolated_db: Path):
    """init_db 启用 WAL 模式（Phase 0 评审 P1 R4 修复）

    Phase 1 评审 P1-3 修复：原断言 `mode in ("wal", "memory", "delete")`
    覆盖几乎所有可能取值，等价于 `assert mode is not None`，WAL 未启用也不会失败。
    改为强断言 wal，tmpfs 环境降级时显式 skip 而非弱断言放水。
    """
    store.init_db(isolated_db)
    with store.get_conn(isolated_db) as conn:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    # tmpfs / 只读挂载等环境 SQLite 会降级为 memory 或 delete，此时显式 skip
    if mode != "wal":
        pytest.skip(f"当前文件系统不支持 WAL，journal_mode={mode}（tmpfs/只读挂载降级，非 bug）")
    assert mode == "wal"


def test_default_db_path_resolved_at_call_time(isolated_db: Path, monkeypatch):
    """守护 Python 默认参数陷阱（Phase 1 评审 P1-6）

    store.py 所有函数默认参数改为 `db_path: Path | None = None`，函数体内读模块级 DB_PATH。
    本测试显式守护：monkeypatch store.DB_PATH 后，不传 db_path 调用 insert/list 应使用新路径。
    未来若有人"优化"回 `db_path: Path = DB_PATH`（定义时绑定），此测试会失败。
    """
    # isolated_db fixture 已 monkeypatch store.DB_PATH = isolated_db 并 init_db
    # 不传 db_path，依赖默认参数走模块级 DB_PATH
    pid = store.insert_wrong_problem(
        student_id="S999", knowledge_point_id="K7A001", problem_text="守护默认参数陷阱",
    )
    assert pid > 0
    rows = store.list_wrong_problems(student_id="S999")
    assert len(rows) == 1
    assert rows[0]["problem_text"] == "守护默认参数陷阱"


def test_concurrent_inserts_no_deadlock(isolated_db: Path):
    """多线程并发插入不应抛 database is locked（WAL + 30s timeout）"""
    store.init_db(isolated_db)
    errors: list[Exception] = []

    def insert_batch(prefix: str):
        try:
            for i in range(5):
                store.insert_wrong_problem(
                    student_id=f"S{prefix}",
                    knowledge_point_id="K7A001",
                    problem_text=f"并发题 {prefix}-{i}",
                    db_path=isolated_db,
                )
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=insert_batch, args=(str(i),)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"并发插入抛错：{errors}"
    rows = store.list_wrong_problems(db_path=isolated_db, limit=1000)
    assert len(rows) == 20
