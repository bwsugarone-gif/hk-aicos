"""Concise, evidence-safe presentation helpers for the AICOS Workspace."""

from __future__ import annotations

import re
from typing import Any

from .image_safety_hardening import build_concise_image_summary


NO_VISION_PREVIEW = "未能確認相片中的具體工序；請補充工序描述或啟用 Vision API。"
_NOISE_TERMS = (
    "pm 工程",
    "delay concern",
    "workflow",
    "repeated issues",
    "project timeline",
    "工序合理性分析",
    "進度追蹤分析",
    "agent 衝突",
)


def build_recent_analysis_preview(data: dict[str, Any]) -> dict[str, Any]:
    """Return a bounded preview without exposing full Agent/PM report prose."""
    image_analysis = data.get("image_analysis") if isinstance(data.get("image_analysis"), dict) else {}
    if image_analysis:
        summary = build_concise_image_summary(image_analysis)
        raw_metadata = image_analysis.get("raw_metadata") if isinstance(image_analysis.get("raw_metadata"), dict) else {}
        evidence_context = raw_metadata.get("evidence_context") if isinstance(raw_metadata.get("evidence_context"), dict) else {}
        visual_confidence = float(image_analysis.get("visual_confidence") or 0.0)
        vision_unavailable = visual_confidence <= 0 or not evidence_context.get("has_visual_analysis")
        if vision_unavailable:
            observations = [NO_VISION_PREVIEW]
            recommendations = ["補充位置、工序及需跟進事項，再由管工／安全主任人工覆核。"]
            confirmations = ["AI 視覺未設定、失敗或未有足夠信心，暫不顯示具體圖片風險。"]
            risk_level = "需人工覆核"
        else:
            observations = summary["observations"][:2]
            recommendations = summary["recommendations"][:2]
            confirmations = summary["confirmations"][:2]
            risk_level = summary["risk_level"]
        return {
            "file_name": str(data.get("file_name") or "最近上載"),
            "analysis_type": str(data.get("analysis_display_name") or data.get("analysis_type") or "圖片分析"),
            "risk_level": risk_level,
            "observations": observations[:2],
            "recommendations": recommendations[:2],
            "confirmations": confirmations[:2],
            "is_image": True,
        }

    lines = _clean_legacy_lines(data.get("analysis_result"))
    recommendations = [line for line in lines if any(term in line for term in ("建議", "跟進", "整改"))][:2]
    confirmations = [line for line in lines if any(term in line for term in ("未能確認", "需確認", "資料不足"))][:2]
    observations = [line for line in lines if line not in recommendations and line not in confirmations][:2]
    return {
        "file_name": str(data.get("file_name") or "最近上載"),
        "analysis_type": str(data.get("analysis_display_name") or data.get("analysis_type") or "分析"),
        "risk_level": str(data.get("risk_level") or "未分類"),
        "observations": observations or ["分析已完成；請開啟完整報告查看詳情。"],
        "recommendations": recommendations,
        "confirmations": confirmations,
        "is_image": False,
    }


def _clean_legacy_lines(value: Any) -> list[str]:
    text = str(value or "")
    segments = re.split(r"\r?\n|(?<=[。！？!?])\s*", text)
    cleaned = []
    for segment in segments:
        line = re.sub(r"^[#>*\-•\d.\s]+", "", segment).strip()
        line = " ".join(line.split())
        if not line or any(term in line.lower() for term in _NOISE_TERMS):
            continue
        if len(line) > 140:
            line = line[:139].rstrip() + "…"
        cleaned.append(line)
    return list(dict.fromkeys(cleaned))[:8]
