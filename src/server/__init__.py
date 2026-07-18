"""云脉·智诊伴学 · 后端业务层

分四层：
- api.py          UI 事件处理（薄包装，被 app.py 调用）
- services/       业务逻辑（错题/诊断/出卷/识题/语音 五大服务）
- rag/            检索抽象（本地实现 + 百炼实现可热切换）
- models.py       Pydantic schema
- store.py        SQLite 存储层

Phase 0 阶段所有 service 函数为 stub，返回占位结构；
Phase 1-4 逐步填充真实业务逻辑（百炼 API / python-docx / FunASR 等）。
"""

from .api import (
    handle_wrongbook_submit,
    handle_diagnosis_run,
    handle_exam_generate,
    handle_ocr_upload,
    handle_voice_generate,
    get_project_info,
    get_wrongbook_list,
    init_store,
)

__all__ = [
    "handle_wrongbook_submit",
    "handle_diagnosis_run",
    "handle_exam_generate",
    "handle_ocr_upload",
    "handle_voice_generate",
    "get_project_info",
    "get_wrongbook_list",
    "init_store",
]
