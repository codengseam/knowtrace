"""拍照识题服务

调用 Qwen3-Omni 多模态识别，输出结构化题面 JSON。

Phase 0: 占位（返回 stub 题面）
Phase 3: 接入 dashscope.MultiModalConversation
"""

from __future__ import annotations

from pathlib import Path


def recognize_image(image_path: str) -> dict:
    """识别图片中的题面

    Returns: {"stem": str, "options": dict, "image_type": str, "confidence": float}
    """
    p = Path(image_path)
    if not p.exists():
        return {"error": f"图片不存在: {image_path}"}

    # Phase 3 TODO: 调用 dashscope.MultiModalConversation.call(
    #   model="qwen3-omni", messages=[{"role":"user","content":[
    #     {"image": image_path}, {"text": "请识别题面，输出 JSON..."}
    #   ]}]
    # )
    return {
        "stem": f"[Phase 3 待实现] 已收到图片 {p.name}，Qwen3-Omni 识别将在 Phase 3 接入",
        "options": {},
        "image_type": "unknown",
        "confidence": 0.0,
        "image_path": image_path,
    }
