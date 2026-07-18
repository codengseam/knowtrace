"""Pydantic schema · 数据契约定义

定义错题/诊断/试卷/语音五类核心数据结构，
前后端共享，app.py 与 services/ 都依赖这些 schema。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class WrongProblem(BaseModel):
    """错题条目"""

    id: Optional[int] = None
    student_id: str = Field(..., description="学生 ID，如 S001")
    grade: str = Field(default="七年级上册", description="年级学期")
    subject: Literal["数学"] = "数学"
    knowledge_point_id: str = Field(..., description="知识点 ID，对应知识图谱节点 id，如 K7A001")
    problem_text: str = Field(..., description="题面文本（可含 LaTeX）")
    student_answer: Optional[str] = Field(default=None, description="学生作答")
    correct_answer: Optional[str] = Field(default=None, description="正确答案")
    error_type: Optional[str] = Field(default=None, description="错因标签")
    source: Literal["manual", "md_upload", "ocr"] = "manual"
    created_at: Optional[datetime] = None


class DiagnosisResult(BaseModel):
    """认知诊断结果"""

    student_id: str
    weak_points: list[str] = Field(default_factory=list, description="薄弱知识点 ID 列表")
    root_causes: list[str] = Field(default_factory=list, description="溯源到的前置依赖薄弱点")
    recommendation_path: list[str] = Field(default_factory=list, description="推荐补漏路径")
    summary: str = Field(default="", description="一句话诊断摘要")
    raw_llm_output: Optional[str] = Field(default=None, description="LLM 原始输出，便于调试")


class ExamPaper(BaseModel):
    """一键出卷产物"""

    paper_id: str
    title: str
    knowledge_points: list[str]
    difficulty: Literal["基础", "变式", "拓展"]
    problems: list[dict] = Field(default_factory=list, description="题目列表")
    docx_path: Optional[str] = Field(default=None, description="生成的 A4 Word 文件路径")
    pdf_path: Optional[str] = Field(default=None, description="生成的 PDF 文件路径")


class VoiceReport(BaseModel):
    """语音周报产物"""

    student_id: str
    week_range: str
    text_content: str = Field(..., description="周报文字稿")
    audio_path: Optional[str] = Field(default=None, description="生成的音频文件路径")
    dialect: Literal["普通话", "西南官话", "中原官话"] = "普通话"
