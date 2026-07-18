"""云脉·智诊伴学 · 魔搭 ModelScope Studio 入口

Gradio Blocks + 5 Tab，每个 Tab 的按钮真实调用 src/server/ 后端业务函数。
魔搭 Studio 默认查找根目录 app.py，本文件即入口。

架构分层（前后端分离）：
- UI 层（本文件）         gr.Blocks / gr.Button / gr.Textbox 等组件
- API 层（src/server/api.py）   事件处理函数薄包装
- Service 层（src/server/services/）  五大业务逻辑
- Store 层（src/server/store.py）  SQLite 持久化
"""

from __future__ import annotations

import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中，让 `from src.server...` 可用
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import gradio as gr  # noqa: E402

from src.server import (  # noqa: E402
    get_project_info,
    get_wrongbook_list,
    handle_wrongbook_submit,
    handle_diagnosis_run,
    handle_exam_generate,
    handle_ocr_upload,
    handle_voice_generate,
    init_store,
)
from src.server.api import get_knowledge_points  # noqa: E402


def build_ui() -> gr.Blocks:
    """构建 Gradio Blocks UI"""
    knowledge_points = get_knowledge_points()

    with gr.Blocks(
        title="云脉·智诊伴学",
        theme=gr.themes.Soft(),
        css="""
        .main-title { text-align: center; padding: 16px 0 8px; }
        .subtitle { text-align: center; color: #666; padding-bottom: 16px; }
        """,
    ) as demo:
        gr.Markdown(
            "# 云脉·智诊伴学 · 认知诊断与补漏中枢\n"
            "> 夸克解题，钉钉批改，**云脉智诊**——做乡村师生身边的 AI 认知教研员",
            elem_classes="main-title",
        )

        with gr.Tab("📋 项目概览"):
            gr.Markdown(get_project_info())

        with gr.Tab("📝 错题录入"):
            gr.Markdown(
                "### 录入错题到 SQLite + MD 备份\n"
                "支持文本输入；Phase 1 已支持学生 ID / 知识点 ID 安全 sanitize；"
                "Phase 1.5 将补 MD 上传与图片录入"
            )
            with gr.Row():
                student_id_wb = gr.Textbox(
                    label="学生 ID", placeholder="如 S001", value="S001"
                )
                kp_choice_wb = gr.Dropdown(
                    label="知识点",
                    choices=knowledge_points,
                    value=knowledge_points[0] if knowledge_points else None,
                    allow_custom_value=False,
                )
            problem_text_wb = gr.Textbox(
                label="题面（可含 LaTeX）",
                placeholder="如：下列式子中是一元一次方程的是（  ）...",
                lines=4,
            )
            with gr.Row():
                error_type_wb = gr.Textbox(label="错因", placeholder="如 概念混淆")
                student_answer_wb = gr.Textbox(label="学生作答", placeholder="如 B")
                correct_answer_wb = gr.Textbox(label="正确答案", placeholder="如 D")
            with gr.Row():
                fill_example_btn_wb = gr.Button("📝 填入示例题面", size="sm")
                submit_btn_wb = gr.Button("📝 提交错题", variant="primary")
            output_wb = gr.Markdown(label="录入结果")

            # 示例填充：一键填入真实错题，方便演示
            # （K7A008 有理数减法：典型错因"减法变号错误"）
            fill_example_btn_wb.click(
                fn=lambda: (
                    "计算 -5 - (-3) = ?",
                    "减法变号错误",
                    "-2",
                    "-8",
                ),
                inputs=[],
                outputs=[problem_text_wb, error_type_wb, student_answer_wb, correct_answer_wb],
            )
            # 知识点同步切到 K7A008（有理数减法），让示例链路完整
            kp_choice_wb.value = next(
                (kp for kp in knowledge_points if kp.startswith("K7A008")),
                knowledge_points[0] if knowledge_points else None,
            )

            submit_btn_wb.click(
                fn=handle_wrongbook_submit,
                inputs=[
                    student_id_wb, kp_choice_wb, problem_text_wb,
                    error_type_wb, student_answer_wb, correct_answer_wb,
                ],
                outputs=output_wb,
            )

            gr.Markdown(
                "---\n### 错题列表查询\n"
                "> 演示提示：连续录入 4 次同一知识点后，前往「认知诊断」Tab 可看到 🔴 red 评级 + 前置溯源"
            )
            query_student_wb = gr.Textbox(label="学生 ID（留空查全部）", value="")
            query_btn_wb = gr.Button("🔍 查询错题")
            query_output_wb = gr.Markdown(label="错题列表")
            query_btn_wb.click(
                fn=get_wrongbook_list,
                inputs=query_student_wb,
                outputs=query_output_wb,
            )

        with gr.Tab("🧠 认知诊断"):
            gr.Markdown(
                "### 基于知识图谱 + Qwen3-Max 的认知诊断\n"
                "**Phase 1 已上线**：规则引擎版（四色风险等级 + 错因聚合 + 前置深度溯源）\n"
                "- 🔴 red 直接薄弱（错 ≥4 道）｜ 🟡 yellow 前置薄弱（2-3 道）\n"
                "- 🟢 green 已掌握（≤1 道）｜ ⚪ gray 未做题\n"
                "- 递归查 2 层 prerequisites 溯源根因，生成「先补前置 → 再补薄弱」补漏路径\n\n"
                "Phase 1.5：接入 Qwen3-Max 做语义级 LCA 溯源（schema 不变）"
            )
            student_id_diag = gr.Textbox(
                label="学生 ID", placeholder="如 S001", value="S001"
            )
            diagnose_btn = gr.Button("🧠 开始诊断", variant="primary")
            diagnosis_output = gr.Markdown(label="诊断报告")
            diagnose_btn.click(
                fn=handle_diagnosis_run,
                inputs=student_id_diag,
                outputs=diagnosis_output,
            )

        with gr.Tab("📄 智能出卷"):
            gr.Markdown(
                "### RAG 检索真题 + python-docx A4 Word 排版\n"
                "Phase 0：LocalRetriever 占位\n"
                "Phase 2：接入百炼 RAG + python-docx 完整 A4 排版"
            )
            kp_choices_exam = gr.CheckboxGroup(
                label="选择知识点（可多选）",
                choices=knowledge_points,
                value=knowledge_points[:3] if len(knowledge_points) >= 3 else knowledge_points,
            )
            with gr.Row():
                difficulty_exam = gr.Radio(
                    label="难度",
                    choices=["基础", "变式", "拓展"],
                    value="基础",
                )
                count_exam = gr.Slider(
                    label="每知识点题数", minimum=1, maximum=10, step=1, value=3
                )
            generate_exam_btn = gr.Button("📄 生成试卷", variant="primary")
            exam_output = gr.Markdown(label="出卷结果")
            generate_exam_btn.click(
                fn=handle_exam_generate,
                inputs=[kp_choices_exam, difficulty_exam, count_exam],
                outputs=exam_output,
            )

        with gr.Tab("📷 拍照识题"):
            gr.Markdown(
                "### Qwen3-Omni 多模态识别\n"
                "Phase 0：占位（仅校验图片存在）\n"
                "Phase 3：接入 Qwen3-Omni 真实识别"
            )
            image_input = gr.Image(label="上传题目图片", type="filepath")
            ocr_btn = gr.Button("📷 识别题面", variant="primary")
            ocr_output = gr.Markdown(label="识别结果")
            ocr_btn.click(
                fn=handle_ocr_upload,
                inputs=image_input,
                outputs=ocr_output,
            )

        with gr.Tab("🔊 语音周报"):
            gr.Markdown(
                "### FunASR 方言/普通话语音周报\n"
                "Phase 0：占位（仅生成文字稿）\n"
                "Phase 3：接入 FunASR 生成 MP3 音频"
            )
            with gr.Row():
                student_id_voice = gr.Textbox(
                    label="学生 ID", placeholder="如 S001", value="S001"
                )
                dialect_voice = gr.Radio(
                    label="方言",
                    choices=["普通话", "西南官话", "中原官话"],
                    value="普通话",
                )
            voice_btn = gr.Button("🔊 生成周报", variant="primary")
            voice_output = gr.Markdown(label="周报内容")
            voice_btn.click(
                fn=handle_voice_generate,
                inputs=[student_id_voice, dialect_voice],
                outputs=voice_output,
            )

        gr.Markdown(
            "---\n"
            "**项目仓库**: GitHub `knowtrace`  ·  "
            "**魔搭部署**: https://www.modelscope.cn/studios/codengseam/knowtrace  ·  "
            "**MVP 范围**: 初中数学七年级上册 50 知识点"
        )

    return demo


# 模块加载时初始化数据库
# 用 try/except 包住，避免魔搭 Studio 容器只读挂载时 import 失败导致页面白屏
try:
    init_store()
except Exception as exc:  # noqa: BLE001
    print(f"[app.py] init_store 失败，魔搭 Studio 入口仍可加载（仅持久化不可用）：{exc}")

demo = build_ui()

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=8080, show_error=True)
