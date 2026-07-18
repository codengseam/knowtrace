"""RAG 检索抽象层

定义 Retriever 接口，本地实现与百炼实现可热切换。
Phase 0 仅定义接口与本地占位实现；
Phase 2 搭建百炼 RAG 应用后实现 BailianRetriever。
"""

from .retriever import Retriever, LocalRetriever, BailianRetriever, get_retriever

__all__ = ["Retriever", "LocalRetriever", "BailianRetriever", "get_retriever"]
