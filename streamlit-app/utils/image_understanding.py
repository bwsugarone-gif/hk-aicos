"""Reusable OCR, vision, classification, and site follow-up pipeline."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .analysis_models import ImageAnalysisResult, OCRResult
from .followup_generator import generate_followups
from .image_classifier import classify_image
from .ocr_engine import run_ocr, to_ocr_result
from .vision_client import SUPPORTED_IMAGE_TYPES, analyze_image_with_vision


SAFETY_KEYWORDS = {
    "danger", "warning", "unsafe", "caution", "prohibited", "open edge",
    "no helmet", "no harness", "stop work", "restricted area", "high voltage",
    "falling hazard", "危險", "警告", "不安全", "小心", "禁止", "臨邊",
    "沒有安全帽", "沒有安全帶", "停工", "限制區域", "高壓電", "高空工作",
}

LOCATION_PATTERNS = [
    r"(?:location|位置|地點)\s*[:：]\s*([^\n]{1,50})",
    r"(?:site|地盤|工地)\s*[:：]\s*([^\n]{1,50})",
    r"(?:floor|樓層)\s*[:：]\s*([^\n]{1,30})",
]
WARNING_PATTERNS = [
    r"(?:danger|warning|caution|危險|警告|小心)\s*[:：]?\s*([^\n]{1,80})",
    r"(?:prohibited|禁止)\s*[:：]?\s*([^\n]{1,60})",
]
NUMBER_PATTERNS = [
    r"\b[A-Z]{2,4}[-/]\d{3,6}[-/]?\d{0,4}\b",
    r"(?:permit|許可證|牌照)\s*[#:：]?\s*([A-Z0-9-/]+)",
    r"(?:ref|編號|參考)\s*[#:：]?\s*([A-Z0-9-/]+)",
]
DATE_PATTERNS = [
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",
    r"\b20\d{2}年\s*\d{1,2}月\s*\d{1,2}日\b",
]


def extract_structured_info(ocr_text: str) -> dict[str, Any]:
    text = str(ocr_text or "").strip()
    if not text:
        return _empty_structured_info()

    locations = _pattern_values(LOCATION_PATTERNS, text, 3)
    warnings = _pattern_values(WARNING_PATTERNS, text, 3)
    numbers = _pattern_values(NUMBER_PATTERNS, text, 5)
    dates = _pattern_values(DATE_PATTERNS, text, 3)
    lowered = text.lower()
    safety_keywords = [keyword for keyword in sorted(SAFETY_KEYWORDS) if keyword.lower() in lowered][:8]
    return {
        "locations": locations,
        "warnings": warnings,
        "numbers": numbers,
        "dates": dates,
        "safety_keywords_found": safety_keywords,
        "has_safety_concern": bool(safety_keywords or warnings),
    }


def analyze_image(
    file_path: str | Path | None = None,
    *,
    ocr_data: dict[str, Any] | OCRResult | None = None,
    use_vision: bool = True,
    anthropic_api_key: str | None = None,
) -> ImageAnalysisResult:
    """Analyse an image with local OCR first and optional vision enrichment."""
    path = Path(file_path) if file_path else None
    supported_image = bool(path and path.suffix.lower() in SUPPORTED_IMAGE_TYPES)

    if ocr_data is not None:
        ocr_result = to_ocr_result(ocr_data)
    elif path is not None:
        ocr_result = run_ocr(path)
    else:
        ocr_result = OCRResult(metadata={"ocr_status": "NO_IMAGE"})

    vision = (
        analyze_image_with_vision(path, api_key=anthropic_api_key)
        if use_vision and path is not None
        else {
            "configured": False,
            "performed": False,
            "status": "disabled",
            "category": "unknown",
            "confidence": 0.0,
            "extracted_text": "",
            "observations": [],
            "risks": [],
        }
    )
    extracted_text = ocr_result.text or str(vision.get("extracted_text") or "").strip()
    structured = extract_structured_info(extracted_text)
    category, category_confidence = classify_image(
        extracted_text,
        vision,
        has_supported_image=supported_image or ocr_data is not None,
    )

    observations = _local_observations(structured, extracted_text)
    observations = _dedupe(observations + _string_list(vision.get("observations")))[:8]
    risks = _local_risks(structured)
    risks = _dedupe(risks + _string_list(vision.get("risks")))[:8]
    followups = generate_followups(category, observations, risks)

    engines = [ocr_result.engine]
    if vision.get("performed") and vision.get("status") == "success":
        engines.append("anthropic_vision")
    confidence = max(category_confidence, ocr_result.confidence * 0.8)
    return ImageAnalysisResult(
        extracted_text=extracted_text,
        detected_category=category,
        confidence=round(min(1.0, confidence), 2),
        key_observations=observations,
        risks=risks,
        recommended_followups=followups,
        source_engine="+".join(dict.fromkeys(engines)),
        raw_metadata={
            "ocr": ocr_result.to_dict(),
            "vision": vision,
            "structured_info": structured,
            "fallback_used": not bool(vision.get("performed") and vision.get("status") == "success"),
        },
    )


def process_image_with_understanding(
    ocr_result: dict[str, Any],
    *,
    anthropic_api_key: str | None = None,
) -> dict[str, Any]:
    """Compatibility wrapper used by the existing Upload/report pipeline."""
    analysis = analyze_image(
        ocr_result.get("path"),
        ocr_data=ocr_result,
        anthropic_api_key=anthropic_api_key,
    )
    structured = analysis.raw_metadata.get("structured_info", _empty_structured_info())
    context = build_image_text_context(ocr_result, structured)
    should_elevate, reason = should_elevate_risk(structured)
    return {
        "ocr_result": ocr_result,
        "structured_info": structured,
        "image_text_context": context,
        "should_elevate_risk": should_elevate,
        "risk_elevation_reason": reason,
        "analysis_result": analysis.to_dict(),
    }


def build_image_text_context(ocr_result: dict[str, Any], structured_info: dict[str, Any]) -> str:
    extracted_text = str(ocr_result.get("extracted_text") or "").strip()
    if not extracted_text:
        return ""
    lines = ["[IMAGE OCR]", f"OCR 狀態：{ocr_result.get('ocr_status', 'UNKNOWN')}"]
    lines.append("\n擷取文字：\n" + extracted_text[:500] + ("..." if len(extracted_text) > 500 else ""))
    labels = {
        "locations": "位置",
        "warnings": "警告",
        "numbers": "編號／參考",
        "dates": "日期",
        "safety_keywords_found": "安全關鍵字",
    }
    for key, label in labels.items():
        values = structured_info.get(key, [])
        if values:
            lines.append(f"\n{label}：{', '.join(values)}")
    if structured_info.get("has_safety_concern"):
        lines.append("\n⚠️ 圖片文字可能涉及安全風險，須由現場合資格人員核實。")
    return "\n".join(lines)


def should_elevate_risk(structured_info: dict[str, Any]) -> tuple[bool, str]:
    if not structured_info.get("has_safety_concern"):
        return False, ""
    keywords = structured_info.get("safety_keywords_found", [])
    warnings = structured_info.get("warnings", [])
    reasons = []
    if keywords:
        reasons.append("偵測到安全關鍵字：" + ", ".join(keywords[:3]))
    if warnings:
        reasons.append("偵測到警告內容：" + ", ".join(warnings[:2]))
    return True, "；".join(reasons) or "圖片可能涉及安全風險"


def _empty_structured_info() -> dict[str, Any]:
    return {
        "locations": [],
        "warnings": [],
        "numbers": [],
        "dates": [],
        "safety_keywords_found": [],
        "has_safety_concern": False,
    }


def _pattern_values(patterns: list[str], text: str, limit: int) -> list[str]:
    values: list[str] = []
    for pattern in patterns:
        for match in re.findall(pattern, text, re.IGNORECASE):
            value = match[0] if isinstance(match, tuple) else match
            value = str(value).strip()
            if value:
                values.append(value)
    return _dedupe(values)[:limit]


def _local_observations(structured: dict[str, Any], text: str) -> list[str]:
    observations = []
    if structured.get("locations"):
        observations.append("識別位置：" + ", ".join(structured["locations"]))
    if structured.get("dates"):
        observations.append("識別日期：" + ", ".join(structured["dates"]))
    if structured.get("numbers"):
        observations.append("識別編號：" + ", ".join(structured["numbers"]))
    if text and not observations:
        observations.append("已從圖片抽取文字，建議人工核對原圖。")
    if not text:
        observations.append("未能抽取可用文字；已保留圖片作人工覆核。")
    return observations


def _local_risks(structured: dict[str, Any]) -> list[str]:
    risks = []
    if structured.get("warnings"):
        risks.extend("警告內容：" + item for item in structured["warnings"][:3])
    if structured.get("safety_keywords_found"):
        risks.append("可能涉及安全事項：" + ", ".join(structured["safety_keywords_found"][:5]))
    return risks


def _string_list(value: Any) -> list[str]:
    return [str(item).strip() for item in value or [] if str(item).strip()] if isinstance(value, list) else []


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
