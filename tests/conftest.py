"""公共测试 fixture。"""
import tempfile

import pytest

# HaloRead 沿袭测试集中跳过清单
# 这些测试依赖 src.core / src.agents / src.utils.prompts / src.utils.editor /
# output/ 目录 / 资治通鉴书籍 / scripts/review_plan.py / scripts/check_missing_columns.py
# 等 knowtrace 未迁移的 HaloRead 专属模块或资产，import 即失败或断言不成立。
# knowtrace 自有测试（test_branch_governance / test_check_chapter_order /
# test_check_loop_log / test_regen_loop_log_index / test_web_reader[已 skip]）
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
]


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """启用 Mock 模式，无需 API Key，并将日志重定向到临时目录。"""
    monkeypatch.setenv("DEEP_READING_MOCK", "1")

    # 将日志目录重定向到临时目录，避免污染真实 logs/
    tmpdir = tempfile.mkdtemp()

    def fake_load_config():
        return {
            "output_dir": "output",
            "logs": {"base_dir": tmpdir},
            "quality_check": {
                "required_sections": [
                    "讲事情",
                    "讲人物",
                    "讲背景",
                    "讲道理",
                    "问道悟道",
                    "结语",
                ],
            },
            # 阶段3：section_templates 与 quality_check.required_sections 同步
            "section_templates": {
                "narrative": [
                    "讲事情", "讲人物", "讲背景", "讲道理", "问道悟道", "结语",
                ],
                "modern": ["入戏", "破题", "方法论", "避坑", "践行"],
                "knowledge": ["概念", "原理", "实践", "速查/自测"],
            },
        }

    try:
        import src.core.workflow  # noqa: F401
        monkeypatch.setattr("src.core.workflow.load_config", fake_load_config)
    except ImportError:
        pass  # 环境缺少 langgraph 等依赖时，不阻塞无需 workflow 的测试
    yield
