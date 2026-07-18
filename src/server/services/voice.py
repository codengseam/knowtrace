"""语音周报服务

调用 FunASR TTS 生成方言/普通话语音周报。

Phase 0: 占位（仅生成文字稿）
Phase 3: 接入 FunASR 生成音频
"""

from __future__ import annotations

import uuid
from pathlib import Path

from ..models import VoiceReport
from .diagnosis import diagnose_student

VOICE_OUTPUT_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent / "data" / "voice_output"
)


def generate_voice_report(
    student_id: str,
    week_range: str = "本周",
    dialect: str = "普通话",
) -> VoiceReport:
    """生成语音周报

    Args:
        student_id: 学生 ID
        week_range: 周报周期，如 "2026-07-12 至 2026-07-18"
        dialect: 普通话/西南官话/中原官话
    """
    VOICE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    diagnosis = diagnose_student(student_id=student_id)
    text_content = _compose_text(
        student_id=student_id,
        week_range=week_range,
        diagnosis_summary=diagnosis.summary,
        weak_points=diagnosis.weak_points,
    )

    # Phase 3 TODO: 调用 FunASR TTS 生成音频
    audio_id = f"V{uuid.uuid4().hex[:8]}"
    audio_path = VOICE_OUTPUT_DIR / f"{audio_id}.mp3"
    audio_path.write_text(
        f"[Phase 3 待实现] 语音周报 {audio_id}\n{text_content}",
        encoding="utf-8",
    )

    return VoiceReport(
        student_id=student_id,
        week_range=week_range,
        text_content=text_content,
        audio_path=str(audio_path),
        dialect=dialect,  # type: ignore
    )


def _compose_text(
    student_id: str,
    week_range: str,
    diagnosis_summary: str,
    weak_points: list[str],
) -> str:
    """组装周报文字稿（仿 docs/04 §6.4 模板）"""
    return (
        f"家长您好，我是云脉伴学。学生 {student_id} 本周（{week_range}）"
        f"学情如下：{diagnosis_summary}"
        f"建议本周重点辅导知识点：{'、'.join(weak_points) if weak_points else '暂无'}。"
        f"请您多鼓励孩子，我们一起加油。"
    )
