"""Retriever 抽象与实现

- Retriever: 抽象基类，定义 retrieve 接口
- LocalRetriever: 本地 JSON 题库检索（基于知识点 ID 匹配）
- BailianRetriever: 百炼 RAG 应用检索（Phase 2 实现）

通过环境变量 `RETRIEVER_BACKEND=local|bailian` 切换，默认 local。
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

QUESTION_BANK_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data"
    / "question_bank"
    / "七年级上册_种子题库.json"
)


class Retriever(ABC):
    """检索抽象基类"""

    @abstractmethod
    def retrieve(
        self,
        knowledge_point_id: str,
        difficulty: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """按知识点检索真题，返回题目列表（每题含 stem/options/answer/solution_steps）"""
        raise NotImplementedError


class LocalRetriever(Retriever):
    """本地 JSON 题库检索（Phase 0 占位实现）

    Phase 2 完善为：基于知识点 ID + 难度过滤的精确匹配；
    Phase 2 后期可补 BM25 关键词召回。
    """

    def retrieve(
        self,
        knowledge_point_id: str,
        difficulty: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        if not QUESTION_BANK_PATH.exists():
            return [
                {
                    "problem_id": "STUB-00001",
                    "stem": f"[Phase 2 待实现] 知识点 {knowledge_point_id} 的本地题库尚未生成种子数据",
                    "options": {},
                    "answer": "",
                    "solution_steps": [],
                    "source": "stub",
                }
            ]
        with QUESTION_BANK_PATH.open(encoding="utf-8") as f:
            bank = json.load(f)
        results = [
            p
            for p in bank.get("problems", [])
            if knowledge_point_id in p.get("knowledge_points", [])
            and (difficulty is None or p.get("difficulty") == difficulty)
        ]
        return results[:top_k]


class BailianRetriever(Retriever):
    """百炼 RAG 应用检索（Phase 2 实现）

    Phase 2 搭建百炼 RAG 应用后填充：
    1. 通过 dashscope.RagApplication.retrieve 调用百炼 RAG
    2. 带 chapter + difficulty filter
    3. Rerank 取 Top-K
    """

    def __init__(self, rag_app_id: str, api_key: str) -> None:
        self.rag_app_id = rag_app_id
        self.api_key = api_key

    def retrieve(
        self,
        knowledge_point_id: str,
        difficulty: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError(
            "BailianRetriever 将在 Phase 2 实现。"
            "请先使用 LocalRetriever，或在 .env 配置 DASHSCOPE_RAG_APP_ID 后等待 Phase 2。"
        )


def get_retriever() -> Retriever:
    """根据环境变量选择 retriever 实例"""
    backend = os.getenv("RETRIEVER_BACKEND", "local").lower()
    if backend == "bailian":
        rag_app_id = os.getenv("DASHSCOPE_RAG_APP_ID", "")
        api_key = os.getenv("DASHSCOPE_API_KEY", "")
        if not rag_app_id or not api_key:
            raise RuntimeError(
                "RETRIEVER_BACKEND=bailian 但 DASHSCOPE_RAG_APP_ID 或 DASHSCOPE_API_KEY 未配置"
            )
        return BailianRetriever(rag_app_id=rag_app_id, api_key=api_key)
    return LocalRetriever()
