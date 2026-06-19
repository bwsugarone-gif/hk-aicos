"""Reusable OCR, vision, classification, and site follow-up pipeline."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .analysis_models import EvidenceContext, ImageAnalysisResult, ImageCategory, OCRResult
from .followup_generator import generate_followups
from .image_classifier import classify_image
from .image_safety_hardening import HOT_WORK_CATEGORIES, filter_unsupported_assumptions
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
    gemini_api_key: str | None = None,
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
        analyze_image_with_vision(
            path,
            api_key=anthropic_api_key,
            gemini_api_key=gemini_api_key,
        )
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
    user_description = (
        str((ocr_data or {}).get("manual_context") or "").strip()
        if isinstance(ocr_data, dict)
        else ""
    )
    selected_analysis_type = (
        str((ocr_data or {}).get("selected_analysis_type") or "").strip()
        if isinstance(ocr_data, dict)
        else ""
    )
    filename_context = " ".join(
        str(value or "")
        for value in (
            getattr(path, "name", ""),
            (ocr_data or {}).get("filename") if isinstance(ocr_data, dict) else "",
        )
    )
    manual_context = " ".join((filename_context, user_description))
    category, category_confidence = classify_image(
        extracted_text,
        vision,
        has_supported_image=supported_image or ocr_data is not None,
        manual_context=manual_context,
    )

    has_visual_analysis = bool(
        vision.get("performed")
        and vision.get("status") == "success"
        and float(vision.get("confidence") or 0) > 0
    )
    evidence_items = _string_list(vision.get("evidence_items")) if has_visual_analysis else []
    raw_observations = _dedupe(_local_observations(structured, extracted_text) + _string_list(vision.get("observations")))
    raw_risks = _dedupe(_local_risks(structured) + _string_list(vision.get("risks")))
    explicit_context = " ".join((extracted_text, manual_context))
    observations, unsupported_observations = filter_unsupported_assumptions(
        raw_observations,
        evidence_items,
        explicit_context,
    )
    risks, unsupported_risks = filter_unsupported_assumptions(raw_risks, evidence_items, explicit_context)
    unsupported = _dedupe(
        _string_list(vision.get("unsupported_assumptions"))
        + unsupported_observations
        + unsupported_risks
    )

    if category.value in HOT_WORK_CATEGORIES:
        signal_text = " ".join([*evidence_items, *observations, *risks, explicit_context]).lower()
        hot_observations, hot_risks = _hot_work_findings(signal_text, has_visual_analysis)
        observations = _dedupe(hot_observations + observations)[:8]
        risks = _dedupe(hot_risks + risks)[:8]

    has_user_or_text_evidence = bool(extracted_text.strip() or user_description or _hot_work_terms(filename_context))
    if not has_visual_analysis and not has_user_or_text_evidence:
        category = ImageCategory.GENERAL_SITE_PHOTO
        category_confidence = 0.0
        observations = []
        risks = []
        unsupported = []

    if not evidence_items:
        evidence_items = _confirmed_evidence(observations)
    followups = generate_followups(category, observations, risks)

    engines = [ocr_result.engine]
    if has_visual_analysis:
        engines.append(f"{vision.get('provider') or 'ai'}_vision")
    visual_confidence = round(min(1.0, category_confidence), 2) if has_visual_analysis else 0.0
    evidence_context = EvidenceContext(
        has_ocr_text=bool(ocr_result.text.strip()),
        ocr_confidence=round(min(1.0, ocr_result.confidence), 2),
        has_visual_analysis=has_visual_analysis,
        visual_confidence=visual_confidence,
        visual_observations=_string_list(vision.get("observations")) if has_visual_analysis else [],
        user_description=user_description,
        selected_analysis_type=selected_analysis_type,
        evidenced_terms=_evidenced_terms(" ".join([*evidence_items, extracted_text, user_description, filename_context])),
        unsupported_terms=unsupported,
    )
    needs_manual_review = bool(
        vision.get("needs_manual_review")
        or not has_visual_analysis
        or visual_confidence < 0.65
        or unsupported
    )
    return ImageAnalysisResult(
        extracted_text=extracted_text,
        detected_category=category,
        confidence=visual_confidence,
        key_observations=observations,
        risks=risks,
        recommended_followups=followups,
        source_engine="+".join(dict.fromkeys(engines)),
        raw_metadata={
            "ocr": ocr_result.to_dict(),
            "vision": vision,
            "structured_info": structured,
            "evidence_context": evidence_context.to_dict(),
            "fallback_used": not bool(vision.get("performed") and vision.get("status") == "success"),
        },
        ocr_text=ocr_result.text,
        ocr_confidence=round(min(1.0, ocr_result.confidence), 2),
        visual_confidence=visual_confidence,
        image_category=category,
        visual_observations=(observations if has_visual_analysis else []),
        evidence_items=evidence_items,
        unsupported_assumptions=unsupported,
        needs_manual_review=needs_manual_review,
    )


def process_image_with_understanding(
    ocr_result: dict[str, Any],
    *,
    anthropic_api_key: str | None = None,
    gemini_api_key: str | None = None,
) -> dict[str, Any]:
    """Compatibility wrapper used by the existing Upload/report pipeline."""
    analysis = analyze_image(
        ocr_result.get("path"),
        ocr_data=ocr_result,
        anthropic_api_key=anthropic_api_key,
        gemini_api_key=gemini_api_key,
    )
    structured = analysis.raw_metadata.get("structured_info", _empty_structured_info())
    text_context = build_image_text_context(ocr_result, structured)
    visual_context = build_visual_evidence_context(analysis.to_dict())
    context = "\n\n".join(part for part in (text_context, visual_context) if part)
    should_elevate, reason = should_elevate_risk(structured, analysis.to_dict())
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


def build_visual_evidence_context(analysis: dict[str, Any]) -> str:
    category = str(analysis.get("image_category") or analysis.get("detected_category") or "unknown")
    observations = _string_list(analysis.get("visual_observations") or analysis.get("key_observations"))
    evidence_items = _string_list(analysis.get("evidence_items"))
    unsupported = _string_list(analysis.get("unsupported_assumptions"))
    evidence_context = (
        analysis.get("raw_metadata", {}).get("evidence_context", {})
        if isinstance(analysis.get("raw_metadata"), dict)
        else {}
    )
    lines = [
        "[IMAGE VISUAL EVIDENCE]",
        f"圖片分類：{category}",
        f"視覺分析信心：{float(analysis.get('visual_confidence') or 0):.0%}",
        "只可把以下可見或明確提供內容寫成已確認事項。",
    ]
    if evidence_context.get("user_description"):
        lines.append("使用者提供的工序描述：" + str(evidence_context["user_description"]))
    if not evidence_context.get("has_visual_analysis"):
        lines.append("未能進行 AI 視覺辨識；不得根據安全分析類型推測任何具體危害。")
    lines.extend(f"- {item}" for item in (evidence_items or observations)[:8])
    if unsupported:
        lines.append("需確認／不可當作已確認風險：")
        lines.extend(f"- {item}" for item in unsupported[:8])
    lines.append("除非上述證據明確支持，禁止加入棚架、高空工作、氣樽、安全帶、護欄或踢腳板。")
    return "\n".join(lines)


def should_elevate_risk(
    structured_info: dict[str, Any],
    image_analysis: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    image_analysis = image_analysis or {}
    category = str(image_analysis.get("image_category") or image_analysis.get("detected_category") or "")
    if category in HOT_WORK_CATEGORIES:
        return True, f"視覺分析識別為 {category}，最終風險不得低於中風險。"
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


def _confirmed_evidence(observations: list[str]) -> list[str]:
    positive_markers = ("已確認", "清晰可見", "相片可見", "正在", "產生明顯")
    uncertain_markers = ("未能確認", "可能", "疑似", "需要確認")
    return [
        item
        for item in observations
        if any(marker in item for marker in positive_markers)
        and not any(marker in item for marker in uncertain_markers)
    ][:8]


def _hot_work_findings(signal_text: str, vision_performed: bool) -> tuple[list[str], list[str]]:
    observations = []
    if any(term in signal_text for term in ("磨機", "角磨", "砂輪", "grinder", "grinding", "切割", "cutting")):
        prefix = "已確認" if vision_performed else "根據檔名或提供資料判斷"
        observations.append(f"{prefix}：工人正在使用磨機或切割工具。")
    if any(term in signal_text for term in ("火花", "sparks", "spark")):
        prefix = "已確認" if vision_performed else "根據提供資料判斷"
        observations.append(f"{prefix}：工序產生明顯火花。")
    if any(term in signal_text for term in ("安全帽", "手套", "長袖", "helmet", "gloves", "long sleeve")):
        observations.append("已確認：相片可見部分 PPE；眼部及面部保護仍需現場確認。")
    risks = [
        "火花可能引燃附近物料或裝修材料。",
        "火花可能損壞門框、牆身或已完成飾面。",
        "金屬碎屑或火花可能造成眼部及面部受傷。",
        "電動工具操作有割傷或反彈風險。",
        "室內位置的通風及走火通道需要確認。",
    ]
    return observations, risks


def _hot_work_terms(text: str) -> list[str]:
    lowered = str(text or "").lower()
    terms = ("grinder", "grinding", "cutting", "sparks", "火花", "磨機", "切割", "熱工")
    return [term for term in terms if term in lowered]


def _evidenced_terms(text: str) -> list[str]:
    lowered = str(text or "").lower()
    groups = (
        "grinder", "grinding", "cutting", "sparks", "火花", "磨機", "切割", "熱工",
        "working at height", "高空工作", "scaffold", "棚架", "gas cylinder", "氣樽",
        "safety harness", "安全帶", "guardrail", "護欄", "toe board", "踢腳板",
    )
    return list(dict.fromkeys(term for term in groups if term in lowered))
