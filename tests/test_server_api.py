"""src/server/api.py 单元测试

覆盖：5 个 handle_xxx 空输入返回 ⚠️ / 正常输入返回 ✅ / get_knowledge_points /
get_project_info / init_store / get_wrongbook_list
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.server import api
from src.server import store


@pytest.fixture
def graph_path(tmp_path, monkeypatch):
    """monkeypatch api.KNOWLEDGE_GRAPH_PATH 指向临时图谱 JSON"""
    import json
    graph_data = {
        "version": "1.0",
        "nodes": [
            {"id": "K7A001", "name": "正数与负数", "chapter": "第1章 有理数", "section": "1.1"},
            {"id": "K7A008", "name": "有理数减法", "chapter": "第1章 有理数", "section": "1.3"},
        ],
        "edges": [],
    }
    graph_file = tmp_path / "test_graph.json"
    graph_file.write_text(json.dumps(graph_data, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(api, "KNOWLEDGE_GRAPH_PATH", graph_file)
    return graph_file


def test_init_store_calls_init_db(isolated_db: Path, monkeypatch):
    """init_store 委托到 init_db（api 模块已 from .store import init_db 绑定引用）"""
    called = {"init_db": False}

    def fake_init_db(db_path=None):
        called["init_db"] = True

    # api.py 顶部 `from .store import init_db` 已绑定引用，
    # 必须 patch api 模块的 init_db 才能拦截调用（patch store.init_db 不生效）
    monkeypatch.setattr(api, "init_db", fake_init_db)
    api.init_store()
    assert called["init_db"] is True


def test_get_project_info_returns_markdown():
    """get_project_info 返回非空 Markdown，含项目核心信息"""
    info = api.get_project_info()
    assert isinstance(info, str)
    assert len(info) > 100
    assert "云脉" in info
    assert "MVP" in info
    assert "魔搭" in info


def test_get_knowledge_points_returns_list(graph_path):
    """get_knowledge_points 返回知识点 ID 列表"""
    kps = api.get_knowledge_points()
    assert isinstance(kps, list)
    assert len(kps) == 2
    # 每项格式："K7A001 · 正数与负数（第1章 有理数）"
    assert any("K7A001" in kp for kp in kps)
    assert any("K7A008" in kp for kp in kps)


def test_get_knowledge_points_empty_when_graph_missing(tmp_path, monkeypatch):
    """GRAPH_PATH 不存在时返回空列表"""
    monkeypatch.setattr(api, "KNOWLEDGE_GRAPH_PATH", tmp_path / "nonexistent.json")
    kps = api.get_knowledge_points()
    assert kps == []


def test_handle_wrongbook_submit_empty_fields(isolated_db: Path):
    """handle_wrongbook_submit 空字段返回 ⚠️"""
    # 空 student_id
    assert "⚠️" in api.handle_wrongbook_submit("", "K7A001 · x", "题面", "", "", "")
    # 空 problem_text
    assert "⚠️" in api.handle_wrongbook_submit("S001", "K7A001 · x", "", "", "", "")
    # 空 knowledge_point_choice
    assert "⚠️" in api.handle_wrongbook_submit("S001", "", "题面", "", "", "")


def test_handle_wrongbook_submit_success(isolated_db: Path, graph_path):
    """handle_wrongbook_submit 正常录入返回 ✅"""
    result = api.handle_wrongbook_submit(
        student_id="S001",
        knowledge_point_choice="K7A008 · 有理数减法（第1章 有理数）",
        problem_text="计算 -5 - (-3) = ?",
        error_type="减法变号错误",
        student_answer="-2",
        correct_answer="-8",
    )
    assert "✅" in result
    assert "已录入错题" in result
    assert "MD 备份" in result


def test_get_wrongbook_list_empty(isolated_db: Path):
    """get_wrongbook_list 无错题时返回提示"""
    result = api.get_wrongbook_list("S001")
    assert "暂无错题记录" in result


def test_get_wrongbook_list_with_data(isolated_db: Path):
    """get_wrongbook_list 有错题时返回 Markdown 表格"""
    api.handle_wrongbook_submit(
        student_id="S001",
        knowledge_point_choice="K7A008 · 有理数减法（第1章 有理数）",
        problem_text="题面",
        error_type="错因",
        student_answer="答",
        correct_answer="正解",
    )
    result = api.get_wrongbook_list("S001")
    assert "S001" in result
    assert "K7A008" in result
    assert "| # |" in result  # Markdown 表格头


def test_handle_diagnosis_run_empty_student_id(isolated_db: Path):
    """handle_diagnosis_run 空 student_id 返回 ⚠️"""
    assert "⚠️" in api.handle_diagnosis_run("")


def test_handle_diagnosis_run_no_problems(isolated_db: Path, graph_path):
    """handle_diagnosis_run 无错题时返回提示，不崩溃"""
    result = api.handle_diagnosis_run("S001")
    assert "暂无错题记录" in result


def test_handle_diagnosis_run_with_red_risk(isolated_db: Path, graph_path):
    """handle_diagnosis_run 错题 ≥4 道时显示 red 评级"""
    for _ in range(4):
        api.handle_wrongbook_submit(
            student_id="S001",
            knowledge_point_choice="K7A008 · 有理数减法（第1章 有理数）",
            problem_text="题面",
            error_type="减法变号错误",
            student_answer="",
            correct_answer="",
        )
    result = api.handle_diagnosis_run("S001")
    assert "认知诊断报告" in result
    assert "🔴" in result  # red 标记
    assert "K7A008" in result
    assert "Phase 1 规则引擎" in result


def test_handle_exam_generate_empty_kp(isolated_db: Path):
    """handle_exam_generate 空知识点列表返回 ⚠️"""
    assert "⚠️" in api.handle_exam_generate([], "基础", 5)


def test_handle_exam_generate_success(isolated_db: Path, graph_path):
    """handle_exam_generate 正常生成返回 ✅"""
    result = api.handle_exam_generate(
        knowledge_point_choices=["K7A008 · 有理数减法（第1章 有理数）"],
        difficulty="基础",
        count=3,
    )
    assert "✅" in result
    assert "已生成试卷" in result


def test_handle_ocr_upload_none():
    """handle_ocr_upload 传 None 返回 ⚠️"""
    assert "⚠️" in api.handle_ocr_upload(None)


def test_handle_ocr_upload_nonexistent_path(tmp_path):
    """handle_ocr_upload 传不存在的图片路径返回 ❌"""
    result = api.handle_ocr_upload(str(tmp_path / "nonexistent.png"))
    assert "❌" in result


def test_handle_voice_generate_empty_student_id():
    """handle_voice_generate 空 student_id 返回 ⚠️"""
    assert "⚠️" in api.handle_voice_generate("", "普通话")


def test_handle_voice_generate_success(isolated_db: Path, graph_path):
    """handle_voice_generate 正常生成返回 ✅"""
    # 先录入错题，让周报有内容可生成
    api.handle_wrongbook_submit(
        student_id="S001",
        knowledge_point_choice="K7A008 · 有理数减法（第1章 有理数）",
        problem_text="题面",
        error_type="错因",
        student_answer="答",
        correct_answer="正解",
    )
    result = api.handle_voice_generate("S001", "普通话")
    assert "✅" in result
    assert "已生成语音周报" in result
    assert "普通话" in result
