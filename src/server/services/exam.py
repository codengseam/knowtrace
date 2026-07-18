"""智能出卷服务

调用 Retriever 检索真题 → python-docx 生成 A4 Word 试卷。

Phase 0: 占位（返回 stub 文件路径）
Phase 2: 完整实现 RAG 检索 + A4 排版
"""

from __future__ import annotations

import uuid
from pathlib import Path

from ..models import ExamPaper
from ..rag import get_retriever

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "exam_output"


def generate_paper(
    knowledge_points: list[str],
    difficulty: str = "基础",
    count: int = 5,
    student_id: str | None = None,
) -> ExamPaper:
    """生成 A4 Word 试卷

    Args:
        knowledge_points: 知识点 ID 列表
        difficulty: 基础/变式/拓展
        count: 每个知识点题数
        student_id: 可选，关联学生
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    paper_id = f"P{uuid.uuid4().hex[:8]}"
    title = f"云脉专项试卷 {paper_id}（{difficulty}）"

    retriever = get_retriever()
    problems: list[dict] = []
    for kp in knowledge_points:
        problems.extend(retriever.retrieve(kp, difficulty=difficulty, top_k=count))

    # Phase 2 TODO: 用 python-docx 生成真实 A4 Word（当前 Phase 0 仅写 txt 占位）
    docx_path = OUTPUT_DIR / f"{paper_id}.txt"
    docx_path.write_text(
        f"[Phase 0 占位] 试卷 {paper_id}\n"
        f"知识点: {knowledge_points}\n难度: {difficulty}\n题数: {len(problems)}\n"
        f"Phase 2 将用 python-docx 生成 A4 Word 排版\n",
        encoding="utf-8",
    )

    return ExamPaper(
        paper_id=paper_id,
        title=title,
        knowledge_points=knowledge_points,
        difficulty=difficulty,  # type: ignore
        problems=problems,
        docx_path=str(docx_path),
    )
