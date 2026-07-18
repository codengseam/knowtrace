"""五大业务服务

- wrongbook  错题录入与存储
- diagnosis  认知诊断（图谱 + Qwen3-Max）
- exam       智能出卷（RAG + python-docx）
- ocr        拍照识题（Qwen3-Omni）
- voice      语音周报（FunASR）
"""

from .wrongbook import submit_wrong_problem, list_problems
from .diagnosis import diagnose_student
from .exam import generate_paper
from .ocr import recognize_image
from .voice import generate_voice_report

__all__ = [
    "submit_wrong_problem",
    "list_problems",
    "diagnose_student",
    "generate_paper",
    "recognize_image",
    "generate_voice_report",
]
