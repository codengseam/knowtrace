"""云脉·智诊伴学 · 主入口（骨架占位）

比赛 MVP 实现将在后续迭代中补全：
- 拍照录题（Qwen3-Omni 多模态识别）
- 认知诊断（轻量图谱 + Qwen3-Max 推理）
- RAG 题库检索（阿里云百炼）
- 一键出卷（python-docx A4 Word）
- FunASR 语音周报

当前版本仅提供知识图谱基座加载与校验入口。
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_GRAPH_PATH = PROJECT_ROOT / "data" / "knowledge_graph" / "七年级上册.json"


def load_knowledge_graph():
    """加载七年级上册知识图谱基座。"""
    with open(KNOWLEDGE_GRAPH_PATH, encoding="utf-8") as f:
        return json.load(f)


def main():
    kg = load_knowledge_graph()
    print(f"学科: {kg['subject']} · 年级: {kg['grade']} · 教材: {kg['textbook']}")
    print(f"节点数: {kg['node_count']} / 实际: {len(kg['nodes'])}")
    print(f"依赖边数: {len(kg['edges'])}")
    print("骨架就绪，等待 MVP 链路实现。")


if __name__ == "__main__":
    main()
