"""src/server/services/diagnosis.py 单元测试

覆盖：无错题 / 有错题四色评级 / 前置深度溯源 / 无图谱兜底 / 推荐补漏路径
用 isolated_db fixture 注入独立 SQLite 路径
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from src.server.services import diagnosis
from src.server.services import wrongbook
from src.server.models import DiagnosisResult, NodeRisk


# 简化知识图谱 fixture（用于 monkeypatch GRAPH_PATH）
SIMPLE_GRAPH = {
    "version": "1.0",
    "nodes": [
        {"id": "K7A001", "name": "正数与负数", "chapter": "第1章", "prerequisites": []},
        {"id": "K7A002", "name": "有理数及分类", "chapter": "第1章", "prerequisites": ["K7A001"]},
        {"id": "K7A003", "name": "数轴", "chapter": "第1章", "prerequisites": ["K7A002"]},
        {"id": "K7A007", "name": "有理数加法", "chapter": "第1章", "prerequisites": ["K7A005", "K7A003"]},
        {"id": "K7A008", "name": "有理数减法", "chapter": "第1章", "prerequisites": ["K7A007", "K7A004"]},
        {"id": "K7A004", "name": "相反数", "chapter": "第1章", "prerequisites": ["K7A003"]},
        {"id": "K7A005", "name": "绝对值", "chapter": "第1章", "prerequisites": ["K7A004"]},
    ],
    "edges": [],
}


@pytest.fixture
def graph_path(tmp_path, monkeypatch):
    """monkeypatch diagnosis.GRAPH_PATH 指向临时图谱 JSON"""
    import json
    graph_file = tmp_path / "test_graph.json"
    graph_file.write_text(json.dumps(SIMPLE_GRAPH, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(diagnosis, "GRAPH_PATH", graph_file)
    return graph_file


def test_diagnose_no_problems(isolated_db: Path):
    """无错题时返回 summary '暂无错题记录'，node_risks 为空"""
    result = diagnosis.diagnose_student("S001")
    assert isinstance(result, DiagnosisResult)
    assert "暂无错题记录" in result.summary
    assert result.node_risks == []
    assert result.weak_points == []
    assert result.root_causes == []


def test_diagnose_red_risk(isolated_db: Path, graph_path):
    """错题 ≥4 道的知识点评级为 red"""
    for _ in range(4):
        wrongbook.submit_wrong_problem(
            student_id="S001",
            knowledge_point_id="K7A008",
            problem_text="题面",
            error_type="减法变号错误",
        )
    result = diagnosis.diagnose_student("S001")
    # Phase 1 评审 P1-4：node_risks 现在包含全部图谱节点（含 gray 未做题），
    # 需从 node_risks 中找出 K7A008 进行断言
    risk = next(r for r in result.node_risks if r.knowledge_point_id == "K7A008")
    assert risk.risk_level == "red"
    assert risk.error_count == 4
    assert "减法变号错误" in risk.error_types
    assert "K7A008" in result.weak_points


def test_diagnose_yellow_risk(isolated_db: Path, graph_path):
    """错题 2-3 道的知识点评级为 yellow"""
    for _ in range(3):
        wrongbook.submit_wrong_problem(
            student_id="S001",
            knowledge_point_id="K7A008",
            problem_text="题面",
        )
    result = diagnosis.diagnose_student("S001")
    risk = next(r for r in result.node_risks if r.knowledge_point_id == "K7A008")
    assert risk.risk_level == "yellow"
    assert risk.error_count == 3
    assert "K7A008" in result.weak_points


def test_diagnose_green_risk(isolated_db: Path, graph_path):
    """错题 1 道的知识点评级为 green，不算薄弱"""
    wrongbook.submit_wrong_problem(
        student_id="S001",
        knowledge_point_id="K7A008",
        problem_text="题面",
    )
    result = diagnosis.diagnose_student("S001")
    risk = next(r for r in result.node_risks if r.knowledge_point_id == "K7A008")
    assert risk.risk_level == "green"
    assert risk.error_count == 1
    assert "K7A008" not in result.weak_points  # green 不算薄弱


def test_diagnose_gray_risk_for_unattempted_kp(isolated_db: Path, graph_path):
    """图谱中未做题的知识点评级为 gray（Phase 1 评审 P1-4：守护 gray 评级真实产出）"""
    wrongbook.submit_wrong_problem(
        student_id="S001",
        knowledge_point_id="K7A008",  # 只做 K7A008
        problem_text="题面",
    )
    result = diagnosis.diagnose_student("S001")
    # K7A001 未做题，应为 gray
    gray_risk = next(
        (r for r in result.node_risks if r.knowledge_point_id == "K7A001"), None
    )
    assert gray_risk is not None, "K7A001 应出现在 node_risks 中（gray 评级）"
    assert gray_risk.risk_level == "gray"
    assert gray_risk.error_count == 0
    assert "K7A001" not in result.weak_points  # gray 不算薄弱


def test_diagnose_root_causes_depth_2(isolated_db: Path, graph_path):
    """前置深度溯源：K7A008（减法）→ 第1层 [K7A007, K7A004] → 第2层 [K7A005, K7A003]"""
    for _ in range(4):
        wrongbook.submit_wrong_problem(
            student_id="S001",
            knowledge_point_id="K7A008",
            problem_text="题面",
        )
    result = diagnosis.diagnose_student("S001")
    # 第 1 层前置：K7A007, K7A004
    assert "K7A007" in result.root_causes
    assert "K7A004" in result.root_causes
    # 第 2 层前置：K7A005（来自 K7A007）, K7A003（来自 K7A004）
    assert "K7A005" in result.root_causes
    assert "K7A003" in result.root_causes
    # 起点不应在 root_causes 中
    assert "K7A008" not in result.root_causes


def test_diagnose_root_causes_deduplicated(isolated_db: Path, graph_path):
    """多个薄弱点共享前置依赖时，root_causes 去重保序"""
    # K7A007 和 K7A008 都依赖 K7A003、K7A005
    for _ in range(4):
        wrongbook.submit_wrong_problem(
            student_id="S001", knowledge_point_id="K7A007", problem_text="题",
        )
    for _ in range(4):
        wrongbook.submit_wrong_problem(
            student_id="S001", knowledge_point_id="K7A008", problem_text="题",
        )
    result = diagnosis.diagnose_student("S001")
    # root_causes 不应有重复
    assert len(result.root_causes) == len(set(result.root_causes))


def test_diagnose_recommendation_path_order(isolated_db: Path, graph_path):
    """推荐补漏路径：先补前置，再补薄弱"""
    for _ in range(4):
        wrongbook.submit_wrong_problem(
            student_id="S001", knowledge_point_id="K7A008", problem_text="题",
        )
    result = diagnosis.diagnose_student("S001")
    assert len(result.recommendation_path) > 0
    # 前置应在薄弱之前
    first_weak_idx = next(
        (i for i, s in enumerate(result.recommendation_path) if "补薄弱" in s),
        len(result.recommendation_path),
    )
    first_prereq_idx = next(
        (i for i, s in enumerate(result.recommendation_path) if "补前置" in s),
        len(result.recommendation_path),
    )
    assert first_prereq_idx < first_weak_idx


def test_diagnose_no_graph_path(isolated_db: Path, tmp_path, monkeypatch):
    """GRAPH_PATH 不存在时 diagnose_student 不应崩溃，返回空 root_causes"""
    monkeypatch.setattr(diagnosis, "GRAPH_PATH", tmp_path / "nonexistent.json")
    # 录入 4 道错题让 K7A008 进入 red 等级（≥4 阈值），才能进入 weak_points
    for _ in range(4):
        wrongbook.submit_wrong_problem(
            student_id="S001", knowledge_point_id="K7A008", problem_text="题",
        )
    result = diagnosis.diagnose_student("S001")
    # 图谱缺失时 root_causes 为空（无法查前置依赖）
    assert result.root_causes == []
    # 但 weak_points 仍按错题数评级识别出 K7A008 为 red 薄弱点
    assert "K7A008" in result.weak_points
    # 对应 node_risks 中 K7A008 应为 red 等级
    kp_risk = next(r for r in result.node_risks if r.knowledge_point_id == "K7A008")
    assert kp_risk.risk_level == "red"


def test_diagnose_summary_format(isolated_db: Path, graph_path):
    """summary 应含学生 ID、错题数、知识点数、薄弱点数"""
    for _ in range(4):
        wrongbook.submit_wrong_problem(
            student_id="S001", knowledge_point_id="K7A008", problem_text="题",
        )
    result = diagnosis.diagnose_student("S001")
    assert "S001" in result.summary
    assert "4 道错题" in result.summary
    assert "1 个知识点" in result.summary


def test_diagnose_weak_points_sorted_by_count_desc(isolated_db: Path, graph_path):
    """weak_points 按错题数降序排列"""
    # K7A008 错 5 道，K7A007 错 3 道
    for _ in range(5):
        wrongbook.submit_wrong_problem(
            student_id="S001", knowledge_point_id="K7A008", problem_text="题",
        )
    for _ in range(3):
        wrongbook.submit_wrong_problem(
            student_id="S001", knowledge_point_id="K7A007", problem_text="题",
        )
    result = diagnosis.diagnose_student("S001")
    # K7A008 错 5（red）应排在 K7A007 错 3（yellow）之前
    assert result.weak_points[0] == "K7A008"
    assert result.weak_points[1] == "K7A007"


def test_evaluate_risk_thresholds():
    """_evaluate_risk 阈值边界：4=red / 3=yellow / 2=yellow / 1=green / 0=gray"""
    assert diagnosis._evaluate_risk(4)[0] == "red"
    assert diagnosis._evaluate_risk(10)[0] == "red"
    assert diagnosis._evaluate_risk(3)[0] == "yellow"
    assert diagnosis._evaluate_risk(2)[0] == "yellow"
    assert diagnosis._evaluate_risk(1)[0] == "green"
    assert diagnosis._evaluate_risk(0)[0] == "gray"
