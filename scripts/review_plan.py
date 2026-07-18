#!/usr/bin/env python3
"""计划评审脚本（路径 B：LangGraph 真并行）。

本脚本为可选增强路径，主路径见 .trae/skills/plan-review/SKILL.md v2.0.0——
会话内用 Trae `Task` 工具启动 3 个 subagent 并行评审（架构师/测试/规则）。

路径 B 启用条件（同时满足）：
1. `.env` 存在且 `LLM_API_KEY` 非空
2. `langgraph` 已安装

任一条件不满足时，本脚本退出码 1 并打印友好提示，调用方应降级到路径 C
（会话内 Task 工具并行评审）。

用法：
    python scripts/review_plan.py --plan /tmp/plan_to_review.md
    python scripts/review_plan.py --plan /tmp/plan_to_review.md --output docs/reviews/plan_review_YYYYMMDD.md
    DEEP_READING_MOCK=1 python scripts/review_plan.py --plan /tmp/plan_to_review.md
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

FRIENDLY_HINT = "路径 B（LangGraph 真并行）依赖未就绪：缺 .env/LLM_API_KEY 或 langgraph 未安装，请降级到路径 C（会话内 Task 工具并行评审）"


def _check_env() -> tuple[bool, str]:
    """返回 (env_ok, reason)。env_ok=True 时表示路径 B 可用。"""
    if not os.environ.get("LLM_API_KEY"):
        return False, "缺 .env/LLM_API_KEY"
    try:
        import langgraph  # noqa: F401
    except ImportError:
        return False, "langgraph 未安装（请 pip install langgraph）"
    return True, ""


def main() -> int:
    parser = argparse.ArgumentParser(description="计划评审（路径 B：LangGraph 真并行）")
    parser.add_argument("--plan", required=True, help="待评审计划文件路径")
    parser.add_argument("--output", help="评审报告输出路径（不指定则打印到 stdout）")
    args = parser.parse_args()

    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"错误：计划文件不存在 {plan_path}", file=sys.stderr)
        return 2

    env_ok, reason = _check_env()
    if not env_ok:
        # 友好提示：调用方应降级到路径 C
        print(FRIENDLY_HINT, file=sys.stderr)
        print(f"原因：{reason}", file=sys.stderr)
        return 1

    # 路径 B 已就绪：调用 langgraph 引擎（实现待补，当前仅占位）
    print("路径 B 已就绪，但 LangGraph 引擎实现待补，请暂时使用路径 C（会话内 Task 工具并行评审）。", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
