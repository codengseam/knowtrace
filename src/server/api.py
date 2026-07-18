"""UI 事件处理函数（薄包装）

被根目录 app.py 直接调用，每个函数对应一个 Gradio 按钮事件。
内部调用 services/ 完成业务逻辑，返回 UI 所需的数据结构。
"""

from __future__ import annotations

from pathlib import Path

from .store import init_db, list_wrong_problems
from .services.wrongbook import submit_wrong_problem
from .services.diagnosis import diagnose_student
from .services.exam import generate_paper
from .services.ocr import recognize_image
from .services.voice import generate_voice_report

KNOWLEDGE_GRAPH_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "knowledge_graph"
    / "七年级上册.json"
)


def init_store() -> None:
    """初始化 SQLite 数据库（app.py 启动时调用一次）"""
    init_db()


def get_project_info() -> str:
    """返回项目概览 Markdown（用于 Tab 0 展示）"""
    return """# 云脉·智诊伴学 · 认知诊断与补漏中枢

> 夸克解题，钉钉批改，**云脉智诊**——做乡村师生身边的 AI 认知教研员。

## 项目定位

阿里巴巴少年云助学计划 · 乡村课堂 AI 助教赛道（ATH 事业群 + 阿里云百炼）。
不造轮子，不抢入口，做阿里教育生态中缺失的"**认知诊断与补漏中枢**"。

## MVP 范围

初中数学七年级上册，约 50 个核心知识点，覆盖人教版四章：
- 第1章 有理数
- 第2章 整式加减
- 第3章 一元一次方程
- 第4章 几何图形初步

## 五项核心链路

| Tab | 链路 | 阿里能力 | 状态 |
|---|---|---|---|
| 📋 项目概览 | — | — | ✅ 已就绪 |
| 📝 错题录入 | 文本/MD/图片 → SQLite | — | 🟡 Phase 1 |
| 🧠 认知诊断 | 图谱 + LCA 溯源 | Qwen3-Max | 🟡 Phase 1 |
| 📄 智能出卷 | RAG 检索 + A4 Word | 百炼 RAG | 🟡 Phase 2 |
| 📷 拍照识题 | 多模态识别 | Qwen3-Omni | 🟡 Phase 3 |
| 🔊 语音周报 | 方言/普通话播报 | FunASR | 🟡 Phase 3 |

## 主链路图

```
[拍题] → (识题 Qwen3-Omni)
            ↓ 题面JSON
       (诊断 Qwen3-Max + 图谱) ──→ 学情快照 → (语音周报 FunASR) → 家长
            ↓ 薄弱点+前置依赖
       (检索 百炼 RAG)
            ↓ 同源题 Top-K
       (出卷 Qwen3-Max + python-docx) → A4 Word → 教师打印
```

## 部署

魔搭 ModelScope Studio: https://www.modelscope.cn/studios/codengseam/knowtrace
"""


def get_knowledge_points() -> list[str]:
    """返回知识点 ID 列表（供下拉框使用）"""
    import json

    if not KNOWLEDGE_GRAPH_PATH.exists():
        return []
    with KNOWLEDGE_GRAPH_PATH.open(encoding="utf-8") as f:
        graph = json.load(f)
    return [
        f"{n['id']} · {n['name']}（{n.get('chapter', '')}）"
        for n in graph.get("nodes", [])
    ]


def handle_wrongbook_submit(
    student_id: str,
    knowledge_point_choice: str,
    problem_text: str,
    error_type: str,
    student_answer: str,
    correct_answer: str,
) -> str:
    """错题录入按钮事件"""
    if not student_id or not problem_text or not knowledge_point_choice:
        return "⚠️ 请填写学生 ID、选择知识点、输入题面"
    kp_id = knowledge_point_choice.split(" · ")[0]
    result = submit_wrong_problem(
        student_id=student_id,
        knowledge_point_id=kp_id,
        problem_text=problem_text,
        error_type=error_type or None,
        student_answer=student_answer or None,
        correct_answer=correct_answer or None,
        source="manual",
    )
    return f"✅ 已录入错题 #{result['id']}\n📝 MD 备份: {result['md_path']}"


def get_wrongbook_list(student_id: str) -> str:
    """查询错题列表"""
    if not student_id:
        rows = list_wrong_problems(limit=50)
    else:
        rows = list_wrong_problems(student_id=student_id, limit=50)
    if not rows:
        return f"学生 {student_id or '(所有)'} 暂无错题记录"
    lines = [f"**学生 {student_id or '(所有)'} 错题列表（共 {len(rows)} 条）**\n"]
    lines.append("| # | 学生 | 知识点 | 错因 | 录入时间 |")
    lines.append("|---|---|---|---|---|")
    for r in rows:
        lines.append(
            f"| {r['id']} | {r['student_id']} | {r['knowledge_point_id']} | "
            f"{r['error_type'] or '-'} | {r['created_at']} |"
        )
    return "\n".join(lines)


def handle_diagnosis_run(student_id: str) -> str:
    """认知诊断按钮事件"""
    if not student_id:
        return "⚠️ 请填写学生 ID"
    result = diagnose_student(student_id=student_id)
    lines = [
        f"## 认知诊断报告 · 学生 {student_id}\n",
        f"**摘要**: {result.summary}\n",
        f"**薄弱知识点 TOP3**: {', '.join(result.weak_points) or '无'}",
        f"**溯源前置薄弱点**: {', '.join(result.root_causes) or '无'}",
        f"**推荐补漏路径**:",
    ]
    for step in result.recommendation_path:
        lines.append(f"  - {step}")
    return "\n".join(lines)


def handle_exam_generate(
    knowledge_point_choices: list[str],
    difficulty: str,
    count: int,
) -> str:
    """智能出卷按钮事件"""
    if not knowledge_point_choices:
        return "⚠️ 请至少选择一个知识点"
    kp_ids = [c.split(" · ")[0] for c in knowledge_point_choices]
    paper = generate_paper(
        knowledge_points=kp_ids,
        difficulty=difficulty,
        count=int(count),
    )
    return (
        f"✅ 已生成试卷 {paper.paper_id}\n\n"
        f"**标题**: {paper.title}\n"
        f"**知识点**: {', '.join(paper.knowledge_points)}\n"
        f"**难度**: {paper.difficulty}\n"
        f"**题目数**: {len(paper.problems)}\n"
        f"**Word 路径**: {paper.docx_path}\n\n"
        f"> Phase 2 将完整实现 python-docx A4 排版，当前为占位文件。"
    )


def handle_ocr_upload(image_path) -> str:
    """拍照识题按钮事件"""
    if image_path is None:
        return "⚠️ 请上传题目图片"
    # Gradio 传入的是文件路径字符串
    image_path_str = str(image_path) if not isinstance(image_path, str) else image_path
    result = recognize_image(image_path_str)
    if "error" in result:
        return f"❌ {result['error']}"
    return (
        f"## 拍照识题结果\n\n"
        f"**题面**: {result['stem']}\n\n"
        f"**图片类型**: {result['image_type']}\n"
        f"**置信度**: {result['confidence']}\n\n"
        f"> Phase 3 将接入 Qwen3-Omni 真实识别"
    )


def handle_voice_generate(student_id: str, dialect: str) -> str:
    """语音周报按钮事件"""
    if not student_id:
        return "⚠️ 请填写学生 ID"
    report = generate_voice_report(
        student_id=student_id,
        week_range="本周",
        dialect=dialect,
    )
    return (
        f"✅ 已生成语音周报\n\n"
        f"**学生**: {report.student_id}\n"
        f"**周期**: {report.week_range}\n"
        f"**方言**: {report.dialect}\n\n"
        f"**文字稿**:\n\n{report.text_content}\n\n"
        f"**音频路径**: {report.audio_path}\n\n"
        f"> Phase 3 将接入 FunASR 生成真实 MP3 音频"
    )
