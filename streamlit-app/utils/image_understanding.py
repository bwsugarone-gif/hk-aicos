# -*- coding: utf-8 -*-
"""
utils/image_understanding.py
HK-AICOS Phase 3.2B — Image Text Understanding Layer

OCR + Visual Context + Safety Detection
Extracts structured information from images and elevates risk for safety keywords.
"""

import re
from typing import Any

# Safety keywords that trigger risk elevation
SAFETY_KEYWORDS = {
    "danger", "warning", "unsafe", "caution", "prohibited",
    "open edge", "no helmet", "no harness", "stop work",
    "restricted area", "high voltage", "falling hazard",
    "危險", "警告", "不安全", "小心", "禁止",
    "開放邊緣", "無安全帽", "無安全帶", "停工",
    "限制區域", "高壓", "墮下危險", "高空作業",
}

# Location patterns
LOCATION_PATTERNS = [
    r"(?:location|地點|位置)[\s:：]*([^\n]{1,50})",
    r"(?:site|工地|現場)[\s:：]*([^\n]{1,50})",
    r"(?:floor|樓層)[\s:：]*([^\n]{1,30})",
]

# Warning patterns
WARNING_PATTERNS = [
    r"(?:danger|warning|caution|危險|警告|小心)[\s:：]*([^\n]{1,80})",
    r"(?:prohibited|禁止|不准)[\s:：]*([^\n]{1,60})",
]

# Number patterns (project codes, permit numbers, etc.)
NUMBER_PATTERNS = [
    r"\b[A-Z]{2,4}[-/]\d{3,6}[-/]?\d{0,4}\b",  # BW-2025-001, PT/12345
    r"\b(?:permit|許可證|工作證)[\s#:：]*(\d+)\b",
    r"\b(?:ref|編號|參考)[\s#:：]*([A-Z0-9-/]+)\b",
]

# Date patterns
DATE_PATTERNS = [
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",  # DD/MM/YYYY, DD-MM-YY
    r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",    # YYYY-MM-DD
    r"\b(?:20\d{2})年\s*\d{1,2}月\s*\d{1,2}日\b",  # 2025年5月19日
]


def extract_structured_info(ocr_text: str) -> dict[str, Any]:
    """
    Extract structured information from OCR text.
    
    Returns:
        {
            "locations": list[str],
            "warnings": list[str],
            "numbers": list[str],
            "dates": list[str],
            "safety_keywords_found": list[str],
            "has_safety_concern": bool,
        }
    """
    if not ocr_text or not ocr_text.strip():
        return {
            "locations": [],
            "warnings": [],
            "numbers": [],
            "dates": [],
            "safety_keywords_found": [],
            "has_safety_concern": False,
        }
    
    text_lower = ocr_text.lower()
    
    # Extract locations
    locations = []
    for pattern in LOCATION_PATTERNS:
        matches = re.findall(pattern, ocr_text, re.IGNORECASE)
        locations.extend([m.strip() for m in matches if m.strip()])
    locations = list(dict.fromkeys(locations))[:3]  # Dedupe, max 3
    
    # Extract warnings
    warnings = []
    for pattern in WARNING_PATTERNS:
        matches = re.findall(pattern, ocr_text, re.IGNORECASE)
        warnings.extend([m.strip() for m in matches if m.strip()])
    warnings = list(dict.fromkeys(warnings))[:3]
    
    # Extract numbers (project codes, permits)
    numbers = []
    for pattern in NUMBER_PATTERNS:
        matches = re.findall(pattern, ocr_text, re.IGNORECASE)
        if isinstance(matches[0] if matches else None, tuple):
            numbers.extend([m[0].strip() for m in matches if m and m[0].strip()])
        else:
            numbers.extend([m.strip() for m in matches if m.strip()])
    numbers = list(dict.fromkeys(numbers))[:5]
    
    # Extract dates
    dates = []
    for pattern in DATE_PATTERNS:
        matches = re.findall(pattern, ocr_text)
        dates.extend([m.strip() for m in matches if m.strip()])
    dates = list(dict.fromkeys(dates))[:3]
    
    # Detect safety keywords
    safety_keywords_found = []
    for keyword in SAFETY_KEYWORDS:
        if keyword in text_lower:
            safety_keywords_found.append(keyword)
    safety_keywords_found = list(dict.fromkeys(safety_keywords_found))[:5]
    
    has_safety_concern = len(safety_keywords_found) > 0 or len(warnings) > 0
    
    return {
        "locations": locations,
        "warnings": warnings,
        "numbers": numbers,
        "dates": dates,
        "safety_keywords_found": safety_keywords_found,
        "has_safety_concern": has_safety_concern,
    }


def build_image_text_context(ocr_result: dict[str, Any], structured_info: dict[str, Any]) -> str:
    """
    Build IMAGE_TEXT_CONTEXT string for agent prompt injection.
    
    Args:
        ocr_result: Result from ocr_engine.extract_text_with_ocr()
        structured_info: Result from extract_structured_info()
    
    Returns:
        Formatted context string for AI prompt injection.
    """
    if not ocr_result.get("ocr_used") or not ocr_result.get("extracted_text"):
        return ""
    
    lines = ["[IMAGE OCR]"]
    
    # OCR status
    ocr_status = ocr_result.get("ocr_status", "")
    if ocr_status == "OCR_SUCCESS":
        lines.append(f"OCR 狀態：成功（{ocr_result.get('ocr_page_count', 0)} 頁）")
    else:
        lines.append(f"OCR 狀態：{ocr_status}")
    
    # Extracted text preview (first 500 chars)
    extracted_text = ocr_result.get("extracted_text", "")
    text_preview = extracted_text[:500] + ("..." if len(extracted_text) > 500 else "")
    lines.append(f"\n辨識到文字：\n{text_preview}")
    
    # Structured info
    if structured_info.get("locations"):
        lines.append(f"\n位置：{', '.join(structured_info['locations'])}")
    
    if structured_info.get("warnings"):
        lines.append(f"\n警告內容：{', '.join(structured_info['warnings'])}")
    
    if structured_info.get("numbers"):
        lines.append(f"\n編號/數字：{', '.join(structured_info['numbers'])}")
    
    if structured_info.get("dates"):
        lines.append(f"\n日期：{', '.join(structured_info['dates'])}")
    
    if structured_info.get("safety_keywords_found"):
        keywords_str = ', '.join(structured_info['safety_keywords_found'])
        lines.append(f"\n⚠️ 安全關鍵字：{keywords_str}")
    
    if structured_info.get("has_safety_concern"):
        lines.append("\n⚠️ 此圖片包含安全警告或風險關鍵字，請特別注意。")
    
    return "\n".join(lines)


def should_elevate_risk(structured_info: dict[str, Any]) -> tuple[bool, str]:
    """
    Determine if risk level should be elevated based on OCR findings.
    
    Returns:
        (should_elevate: bool, reason: str)
    """
    if not structured_info.get("has_safety_concern"):
        return False, ""
    
    keywords = structured_info.get("safety_keywords_found", [])
    warnings = structured_info.get("warnings", [])
    
    reasons = []
    if keywords:
        reasons.append(f"圖片包含安全關鍵字：{', '.join(keywords[:3])}")
    if warnings:
        reasons.append(f"圖片包含警告內容：{', '.join(warnings[:2])}")
    
    if reasons:
        return True, "；".join(reasons)
    
    return False, ""


def process_image_with_understanding(ocr_result: dict[str, Any]) -> dict[str, Any]:
    """
    Full pipeline: OCR result → structured extraction → context building → risk assessment.
    
    Args:
        ocr_result: Result from ocr_engine.extract_text_with_ocr()
    
    Returns:
        {
            "ocr_result": dict,           # Original OCR result
            "structured_info": dict,      # Extracted structured info
            "image_text_context": str,    # Formatted context for prompt injection
            "should_elevate_risk": bool,  # Whether to elevate risk level
            "risk_elevation_reason": str, # Reason for risk elevation
        }
    """
    extracted_text = ocr_result.get("extracted_text", "")
    structured_info = extract_structured_info(extracted_text)
    image_text_context = build_image_text_context(ocr_result, structured_info)
    should_elevate, reason = should_elevate_risk(structured_info)
    
    return {
        "ocr_result": ocr_result,
        "structured_info": structured_info,
        "image_text_context": image_text_context,
        "should_elevate_risk": should_elevate,
        "risk_elevation_reason": reason,
    }
