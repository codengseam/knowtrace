"""认知诊断服务

基于知识图谱 JSON + Qwen3-Max 推理，输出薄弱点 + LCA 溯源 + 推荐补漏路径。

Phase 0: 规则引擎兜底（按错题数 TOP3 找薄弱点）
Phase 1: 规则引擎升级——四色风险等级 + 错因聚合 + 前置深度溯源（递归查 2 层）
Phase 1.5: 接入 Qwen3-Max，基于图谱做语义级 LCA 溯源（schema 不变，只换内部实现）

四色风险等级阈值（保守估计，后续可调）：
- red    直接薄弱：该知识点错题 ≥4 道
- yellow 前置薄弱：该知识点错题 2-3 道
- green  已掌握：该知识点错题 ≤1 道
- gray   未做题：该知识点错题 0 道（且无前置依赖被牵连）
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from ..models import DiagnosisResult, NodeRisk
from ..store import list_wrong_problems

GRAPH_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data"
    / "knowledge_graph"
    / "七年级上册.json"
)

# 四色风险等级阈值（Phase 1 评审确认）
RED_THRESHOLD = 4      # ≥4 道 = 直接薄弱
YELLOW_THRESHOLD = 2   # 2-3 道 = 前置薄弱
# 1 道 = green（已掌握），0 道 = gray（未做题）

# 前置依赖溯源深度（递归查 2 层：薄弱点 → 前置 → 前置的前置）
PREREQUISITE_DEPTH = 2


def diagnose_student(student_id: str) -> DiagnosisResult:
    """对学生做认知诊断

    Phase 1: 规则引擎——四色风险等级 + 错因聚合 + 前置深度溯源
    Phase 1.5: 接入 Qwen3-Max 做语义级 LCA 溯源（保持 schema 不变）
    """
    problems = list_wrong_problems(student_id=student_id, limit=500)
    graph = _load_graph()
    nodes_by_id = {n["id"]: n for n in graph.get("nodes", [])}

    if not problems:
        return DiagnosisResult(
            student_id=student_id,
            summary=f"学生 {student_id} 暂无错题记录，无法诊断。",
        )

    # 按知识点聚合错题数 + 错因类型
    kp_count: dict[str, int] = Counter(p["knowledge_point_id"] for p in problems)
    kp_error_types: dict[str, list[str]] = {}
    for p in problems:
        kp = p["knowledge_point_id"]
        if p.get("error_type"):
            kp_error_types.setdefault(kp, []).append(p["error_type"])

    # 四色风险评级：对所有错过的知识点评级
    node_risks: list[NodeRisk] = []
    weak_points: list[str] = []  # red + yellow
    for kp_id, count in kp_count.items():
        node = nodes_by_id.get(kp_id, {})
        risk_level, risk_reason = _evaluate_risk(count)
        if risk_level in ("red", "yellow"):
            weak_points.append(kp_id)
        node_risks.append(
            NodeRisk(
                knowledge_point_id=kp_id,
                name=node.get("name", ""),
                chapter=node.get("chapter", ""),
                error_count=count,
                error_types=kp_error_types.get(kp_id, []),
                risk_level=risk_level,
                risk_reason=risk_reason,
            )
        )

    # weak_points 按错题数降序
    weak_points.sort(key=lambda k: kp_count[k], reverse=True)

    # 前置深度溯源（递归查 PREREQUISITE_DEPTH 层）
    root_causes = _find_root_causes_deep(weak_points, nodes_by_id, depth=PREREQUISITE_DEPTH)

    # 推荐补漏路径：先补前置（去重保序），再补薄弱
    recommendation_path = _build_recommendation(weak_points, root_causes)

    summary = (
        f"学生 {student_id} 共 {len(problems)} 道错题，"
        f"覆盖 {len(kp_count)} 个知识点；"
        f"薄弱知识点（red+yellow）{len(weak_points)} 个：{', '.join(weak_points[:3])}{'...' if len(weak_points) > 3 else ''}；"
        f"溯源前置薄弱点 {len(root_causes)} 个。"
    )

    return DiagnosisResult(
        student_id=student_id,
        weak_points=weak_points,
        root_causes=root_causes,
        recommendation_path=recommendation_path,
        summary=summary,
        node_risks=node_risks,
    )


def _evaluate_risk(error_count: int) -> tuple[str, str]:
    """根据错题数评级四色风险等级，返回 (level, reason)"""
    if error_count >= RED_THRESHOLD:
        return "red", f"直接薄弱（错 {error_count} 道，≥{RED_THRESHOLD} 阈值）"
    if error_count >= YELLOW_THRESHOLD:
        return "yellow", f"前置薄弱（错 {error_count} 道，{YELLOW_THRESHOLD}-{RED_THRESHOLD - 1} 阈值）"
    if error_count >= 1:
        return "green", f"已掌握（错 {error_count} 道，≤1 阈值，偶发失误）"
    return "gray", "未做题（无错题记录）"


def _load_graph() -> dict[str, Any]:
    """加载知识图谱 JSON，缺失时返回空图谱（不阻断诊断）"""
    if not GRAPH_PATH.exists():
        return {"nodes": [], "edges": []}
    with GRAPH_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _find_root_causes_deep(
    weak_points: list[str],
    nodes_by_id: dict[str, dict[str, Any]],
    depth: int = PREREQUISITE_DEPTH,
) -> list[str]:
    """递归查前置依赖，深度 depth 层，返回去重保序的根因列表

    例：weak=K7A008（减法），depth=2 时查：
    - 第 1 层：K7A008.prerequisites = [K7A007, K7A004]
    - 第 2 层：K7A007.prerequisites = [K7A005, K7A003]
    返回：[K7A007, K7A004, K7A005, K7A003]（去重保序，排除已在 weak_points 中的）
    """
    root_causes: list[str] = []
    visited: set[str] = set(weak_points)  # 起点不入根因
    queue = list(weak_points)

    for _ in range(depth):
        next_layer: list[str] = []
        for kp in queue:
            node = nodes_by_id.get(kp)
            if not node:
                continue
            for prereq in node.get("prerequisites", []):
                if prereq in visited:
                    continue
                visited.add(prereq)
                root_causes.append(prereq)
                next_layer.append(prereq)
        queue = next_layer
        if not queue:
            break

    return root_causes


def _build_recommendation(
    weak_points: list[str],
    root_causes: list[str],
) -> list[str]:
    """构建推荐补漏路径：先补前置（去重保序），再补薄弱"""
    path: list[str] = []
    path.extend(f"补前置: {kp}" for kp in root_causes)
    path.extend(f"补薄弱: {kp}" for kp in weak_points)
    return path
