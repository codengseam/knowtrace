"""src/server/rag/retriever.py 单元测试

覆盖：LocalRetriever stub / 真题库 / 难度过滤 / BailianRetriever 占位 / get_retriever 工厂切换
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from src.server.rag import retriever
from src.server.rag.retriever import (
    BailianRetriever,
    LocalRetriever,
    Retriever,
    get_retriever,
)


@pytest.fixture
def question_bank(tmp_path, monkeypatch):
    """monkeypatch QUESTION_BANK_PATH 指向临时题库 JSON"""
    bank_data = {
        "problems": [
            {
                "problem_id": "JUNIOR-MATH-00001",
                "stem": "计算 -5 - (-3) = ?",
                "options": {"A": "-8", "B": "-2", "C": "2", "D": "8"},
                "answer": "A",
                "solution_steps": ["减去一个数等于加上它的相反数", "-5 + 3 = -2 → 错，应为 -5 + (-3) = -8"],
                "knowledge_points": ["K7A008"],
                "difficulty": "基础",
            },
            {
                "problem_id": "JUNIOR-MATH-00002",
                "stem": "下列各组数中互为相反数的是（  ）",
                "options": {"A": "+3 和 -3", "B": "0 和 0", "C": "-1/2 和 0.5", "D": "以上都对"},
                "answer": "A",
                "solution_steps": ["相反数定义：只有符号不同的两个数"],
                "knowledge_points": ["K7A004"],
                "difficulty": "基础",
            },
            {
                "problem_id": "JUNIOR-MATH-00003",
                "stem": "已知 |a|=3，求 a 的值",
                "options": {},
                "answer": "a = ±3",
                "solution_steps": ["绝对值定义：|a| 表示 a 到原点的距离", "|a|=3 → a=3 或 a=-3"],
                "knowledge_points": ["K7A005"],
                "difficulty": "变式",
            },
        ]
    }
    bank_file = tmp_path / "test_bank.json"
    bank_file.write_text(json.dumps(bank_data, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(retriever, "QUESTION_BANK_PATH", bank_file)
    return bank_file


def test_local_retriever_returns_stub_when_bank_missing(tmp_path, monkeypatch):
    """题库文件不存在时 LocalRetriever 返回 stub（Phase 0 占位行为）"""
    monkeypatch.setattr(retriever, "QUESTION_BANK_PATH", tmp_path / "nonexistent.json")
    r = LocalRetriever()
    results = r.retrieve("K7A008")
    assert len(results) == 1
    assert results[0]["problem_id"] == "STUB-00001"
    assert "K7A008" in results[0]["stem"]


def test_local_retriever_retrieves_by_kp(question_bank):
    """LocalRetriever 按知识点 ID 精确匹配检索"""
    r = LocalRetriever()
    results = r.retrieve("K7A008")
    assert len(results) == 1
    assert results[0]["problem_id"] == "JUNIOR-MATH-00001"
    assert "K7A008" in results[0]["knowledge_points"]


def test_local_retriever_filters_by_difficulty(question_bank):
    """LocalRetriever difficulty 参数过滤生效"""
    r = LocalRetriever()
    # K7A005 只有 1 道「变式」题
    results_all = r.retrieve("K7A005", difficulty=None)
    results_basic = r.retrieve("K7A005", difficulty="基础")
    results_variant = r.retrieve("K7A005", difficulty="变式")

    assert len(results_all) == 1
    assert len(results_basic) == 0  # K7A005 没有「基础」题
    assert len(results_variant) == 1


def test_local_retriever_respects_top_k(question_bank):
    """LocalRetriever top_k 参数限制返回数量"""
    r = LocalRetriever()
    # 构造多道命中题：用 K7A008 多次出现
    # 当前题库 K7A008 只有 1 道，top_k=0 测边界
    results = r.retrieve("K7A008", top_k=0)
    assert len(results) == 0


def test_local_retriever_returns_empty_for_unknown_kp(question_bank):
    """LocalRetriever 查不到知识点时返回空列表（不是 stub）"""
    r = LocalRetriever()
    results = r.retrieve("K7A999")  # 不存在的知识点
    assert results == []


def test_bailian_retriever_not_implemented():
    """BailianRetriever.retrieve 抛 NotImplementedError（Phase 2 占位）"""
    r = BailianRetriever(rag_app_id="test-app", api_key="test-key")
    with pytest.raises(NotImplementedError, match="Phase 2"):
        r.retrieve("K7A008")


def test_get_retriever_default_local(monkeypatch):
    """默认 RETRIEVER_BACKEND 未设置时返回 LocalRetriever"""
    monkeypatch.delenv("RETRIEVER_BACKEND", raising=False)
    r = get_retriever()
    assert isinstance(r, LocalRetriever)


def test_get_retriever_explicit_local(monkeypatch):
    """RETRIEVER_BACKEND=local 显式指定返回 LocalRetriever"""
    monkeypatch.setenv("RETRIEVER_BACKEND", "local")
    r = get_retriever()
    assert isinstance(r, LocalRetriever)


def test_get_retriever_bailian_missing_key_raises(monkeypatch):
    """RETRIEVER_BACKEND=bailian 但缺 KEY 时抛 RuntimeError"""
    monkeypatch.setenv("RETRIEVER_BACKEND", "bailian")
    monkeypatch.delenv("DASHSCOPE_RAG_APP_ID", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="DASHSCOPE_RAG_APP_ID"):
        get_retriever()


def test_get_retriever_bailian_with_key_returns_bailian(monkeypatch):
    """RETRIEVER_BACKEND=bailian 且 KEY 齐全时返回 BailianRetriever"""
    monkeypatch.setenv("RETRIEVER_BACKEND", "bailian")
    monkeypatch.setenv("DASHSCOPE_RAG_APP_ID", "test-app-id")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-api-key")
    r = get_retriever()
    assert isinstance(r, BailianRetriever)
    assert r.rag_app_id == "test-app-id"
    assert r.api_key == "test-api-key"


def test_retriever_is_abstract():
    """Retriever 是 ABC，不能直接实例化"""
    with pytest.raises(TypeError):
        Retriever()  # type: ignore[abstract]
