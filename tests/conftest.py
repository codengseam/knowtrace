"""公共测试 fixture。"""
import os
import tempfile
from pathlib import Path

import pytest

# HaloRead 沿袭测试集中跳过清单
# 这些测试依赖 src.core / src.agents / src.utils.prompts / src.utils.editor /
# output/ 目录 / 资治通鉴书籍 / scripts/review_plan.py / scripts/check_missing_columns.py
# 等 knowtrace 未迁移的 HaloRead 专属模块或资产，import 即失败或断言不成立。
# knowtrace 自有测试（test_branch_governance / test_check_chapter_order /
# test_check_loop_log / test_regen_loop_log_index / test_server_* / test_web_reader[已 skip]）
# 不在此列，仍正常跑。
collect_ignore = [
    # 依赖 src.core / src.agents / src.utils.prompts / src.utils.editor 等 HaloRead 专属模块
    "test_archetype.py",
    "test_char_count.py",
    "test_check_consistency_cli.py",
    "test_consistency.py",
    "test_content_quality_archetype.py",
    "test_content_quality_soul.py",
    "test_editor.py",
    "test_markdown.py",
    "test_migrate_wellness_books.py",
    "test_orchestrator.py",
    "test_prompt_archetype.py",
    "test_quality.py",
    "test_score_aggregate.py",
    "test_sorting.py",
    "test_sources_references.py",
    "test_specialist_archetype.py",
    "test_track_02.py",
    "test_workflow_archetype.py",
    "test_workflow_output_dir.py",
    # 依赖 output/ 目录与 HaloRead 书籍（资治通鉴/明纪/易经课），knowtrace 用 content/初中数学教研
    "test_book_structure.py",
    "test_category_mapping.py",
    "test_skill_archetype_routing.py",
    # 依赖 src/main.py 生成「资治通鉴/周纪二_商鞅变法.md」，knowtrace main.py 是骨架不生成文件
    "test_main.py",
    # 依赖 scripts/check_missing_columns.py（HaloRead 专栏校验，knowtrace 无专栏）
    "test_check_missing_columns.py",
    # 依赖 scripts/review_plan.py（路径 B langgraph，knowtrace 走路径 C Task 工具）
    "test_plan_review_skill.py",
    # 依赖 site/css/style.css（HaloRead 静态前端资产，knowtrace 改用根目录 app.py 入口）
    "test_build_site.py",
    # 依赖 src.core.workflow / src.core.plan_review_workflow（HaloRead 专属），
    # 当前靠 pytest.importorskip("langgraph") 间接跳过，但 requirements-dev.txt
    # 装 langgraph 后会收集期崩溃，故显式加入 collect_ignore
    "test_workflow.py",
    "test_workflow_e2e.py",
    "test_plan_review.py",
]


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """src/server 单元测试专用：注入独立 SQLite 路径 + 输出目录，避免污染 /workspace/data/。

    用法：在测试函数签名加 `isolated_db` 参数即可，fixture 会自动：
    1. 创建 tmp_path/wrongbook.db
    2. monkeypatch KNOWTRACE_DB_PATH 环境变量
    3. 同步重置 store.DB_PATH / wrongbook.MD_BACKUP_DIR / exam.OUTPUT_DIR / voice.VOICE_OUTPUT_DIR
    4. 调用 init_db() 初始化表结构

    注意：本 fixture 不 patch diagnosis.GRAPH_PATH / retriever.QUESTION_BANK_PATH，
    需要图谱/题库隔离的测试请额外用 graph_path / question_bank fixture。
    """
    db_path = tmp_path / "wrongbook.db"
    monkeypatch.setenv("KNOWTRACE_DB_PATH", str(db_path))
    # 同步重置 store 模块的 DB_PATH 常量（模块加载时已读旧值）
    import src.server.store as store
    monkeypatch.setattr(store, "DB_PATH", db_path)
    # 同步重置 wrongbook 的 MD_BACKUP_DIR（派生自 DB_PATH.parent）
    import src.server.services.wrongbook as wrongbook
    monkeypatch.setattr(wrongbook, "MD_BACKUP_DIR", db_path.parent / "wrongbook_md")
    # 同步重置 exam / voice 输出目录（避免向真实 data/exam_output 写文件）
    import src.server.services.exam as exam
    monkeypatch.setattr(exam, "OUTPUT_DIR", tmp_path / "exam_output")
    import src.server.services.voice as voice
    monkeypatch.setattr(voice, "VOICE_OUTPUT_DIR", tmp_path / "voice_output")
    # 初始化表结构
    store.init_db(db_path)
    yield db_path


@pytest.fixture(autouse=True)
def _mock_llm_env(monkeypatch):
    """启用 LLM Mock 模式，无需 API Key。

    与 .env.example 的 LLM_MOCK= 对齐（Phase 0 评审 P1 R7：原 conftest 用
    DEEP_READING_MOCK 是 HaloRead 沿袭死变量，knowtrace 用 LLM_MOCK）。
    autouse=True 但只设置环境变量，不影响测试逻辑。
    """
    monkeypatch.setenv("LLM_MOCK", "1")
    # 将日志目录重定向到临时目录，避免污染真实 logs/
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setenv("LOG_DIR", tmpdir)
    yield
