"""认知诊断服务

基于知识图谱 JSON + Qwen3-Max 推理，输出薄弱点 + LCA 溯源 + 推荐补漏路径。

Phase 0: 规则引擎兜底（按错题数 TOP3 找薄弱点）
Phase 1: 接入 Qwen3-Max，基于图谱做 LCA 溯源
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..store import list_wrong_problems
from ..models import DiagnosisResult

GRAPH_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data"
    / "knowledge_graph"
    / "七年级上册.json"
)


def diagnose_student(student_id: str) -> DiagnosisResult:
    """对学生做认知诊断

    Phase 0: 规则引擎兜底——按知识点错题数 TOP3 + 图谱查前置依赖
    Phase 1: 接入 Qwen3-Max 做语义级 LCA 溯源
    """
    problems = list_wrong_problems(student_id=student_id, limit=500)
    if not problems:
        return DiagnosisResult(
            student_id=student_id,
            summary=f"学生 {student_id} 暂无错题记录，无法诊断。",
        )

    # Phase 0 规则引擎：按知识点统计错题数
    kp_count: dict[str, int] = {}
    for p in problems:
        kp = p["knowledge_point_id"]
        kp_count[kp] = kp_count.get(kp, 0) + 1
    weak_points = sorted(kp_count, key=lambda k: kp_count[k], reverse=True)[:3]

    # 从图谱查前置依赖
    graph = _load_graph()
    root_causes = _find_root_causes(weak_points, graph)
    recommendation_path = _build_recommendation(weak_points, root_causes, graph)

    summary = (
        f"学生 {student_id} 共 {len(problems)} 道错题，"
        f"薄弱知识点 TOP3: {', '.join(weak_points)}；"
        f"溯源前置薄弱点: {', '.join(root_causes) if root_causes else '无'}。"
    )

    return DiagnosisResult(
        student_id=student_id,
        weak_points=weak_points,
        root_causes=root_causes,
        recommendation_path=recommendation_path,
        summary=summary,
    )


def _load_graph() -> dict[str, Any]:
    if not GRAPH_PATH.exists():
        return {"nodes": [], "edges": []}
    with GRAPH_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _find_root_causes(weak_points: list[str], graph: dict[str, Any]) -> list[str]:
    """从图谱查薄弱点的前置依赖，作为溯源根因"""
    nodes_by_id = {n["id"]: n for n in graph.get("nodes", [])}
    root_causes: list[str] = []
    for kp in weak_points:
        node = nodes_by_id.get(kp)
        if not node:
            continue
        for prereq in node.get("prerequisites", []):
            if prereq not in weak_points and prereq not in root_causes:
                root_causes.append(prereq)
    return root_causes


def _build_recommendation(
    weak_points: list[str],
    root_causes: list[str],
    graph: dict[str, Any],
) -> list[str]:
    """构建推荐补漏路径：先补前置，再补薄弱"""
    path: list[str] = []
    path.extend(f"补前置: {kp}" for kp in root_causes)
    path.extend(f"补薄弱: {kp}" for kp in weak_points)
    return path
