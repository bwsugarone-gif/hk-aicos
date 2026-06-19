"""Deterministic construction-image category classification."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .analysis_models import ImageCategory


_ALIASES = {
    "safety": ImageCategory.SAFETY_ISSUE,
    "hazard": ImageCategory.SAFETY_ISSUE,
    "unsafe": ImageCategory.SAFETY_ISSUE,
    "hotwork": ImageCategory.HOT_WORK,
    "hot_work": ImageCategory.HOT_WORK,
    "welding": ImageCategory.HOT_WORK,
    "cutting": ImageCategory.CUTTING_GRINDING,
    "grinding": ImageCategory.CUTTING_GRINDING,
    "grinder": ImageCategory.CUTTING_GRINDING,
    "fire": ImageCategory.FIRE_RISK,
    "ppe": ImageCategory.PPE_ISSUE,
    "defect": ImageCategory.CONSTRUCTION_DEFECT,
    "construction_issue": ImageCategory.CONSTRUCTION_DEFECT,
    "delivery": ImageCategory.MATERIAL_DELIVERY,
    "material": ImageCategory.MATERIAL_DELIVERY,
    "handwritten": ImageCategory.HANDWRITTEN_RECORD,
    "site_diary": ImageCategory.HANDWRITTEN_RECORD,
    "attendance": ImageCategory.ATTENDANCE_OR_TIMESHEET,
    "timesheet": ImageCategory.ATTENDANCE_OR_TIMESHEET,
    "site_photo": ImageCategory.GENERAL_SITE_PHOTO,
    "general": ImageCategory.GENERAL_SITE_PHOTO,
}

_CATEGORY_KEYWORDS = {
    ImageCategory.CUTTING_GRINDING: {
        "grinder", "grinding", "angle grinder", "cutting tool", "metal cutting",
        "磨機", "角磨機", "砂輪機", "切割機", "切割工具", "金屬切割",
    },
    ImageCategory.HOT_WORK: {
        "hot work", "sparks", "spark", "welding", "flame", "torch cutting",
        "熱工", "火花", "燒焊", "焊接", "明火", "氣割",
    },
    ImageCategory.FIRE_RISK: {
        "fire risk", "combustible", "flammable", "fire blanket", "fire extinguisher",
        "火災風險", "可燃物", "易燃物", "防火氈", "滅火筒", "滅火器",
    },
    ImageCategory.PPE_ISSUE: {
        "ppe issue", "face shield", "eye protection", "safety glasses", "gloves",
        "個人防護", "面罩", "眼罩", "護目鏡", "手套",
    },
    ImageCategory.SAFETY_ISSUE: {
        "danger", "warning", "unsafe", "hazard", "stop work", "no helmet",
        "no harness", "open edge", "fall protection", "危險", "警告", "不安全",
        "安全帶", "安全帽", "高空工作", "臨邊", "停工", "觸電", "棚架",
    },
    ImageCategory.CONSTRUCTION_DEFECT: {
        "defect", "crack", "leak", "spalling", "honeycomb", "misalignment",
        "damaged", "裂縫", "滲水", "漏水", "剝落", "蜂巢", "空鼓", "缺陷",
        "損壞", "不平", "維修",
    },
    ImageCategory.MATERIAL_DELIVERY: {
        "delivery", "delivered", "material", "batch", "quantity", "supplier",
        "purchase order", "packing list", "送貨", "材料", "批次", "數量", "供應商",
        "收貨", "水泥", "鋼筋",
    },
    ImageCategory.ATTENDANCE_OR_TIMESHEET: {
        "attendance", "timesheet", "clock in", "clock out", "man-hours", "worker name",
        "出勤", "考勤", "工時", "上班", "下班", "簽到", "人名", "出席",
    },
    ImageCategory.HANDWRITTEN_RECORD: {
        "handwritten", "site diary", "daily record", "inspection note", "signature",
        "手寫", "地盤日誌", "施工日誌", "巡查記錄", "簽名", "備忘",
    },
}


def normalize_image_category(value: ImageCategory | str | None) -> ImageCategory:
    if isinstance(value, ImageCategory):
        return value
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    try:
        return ImageCategory(normalized)
    except ValueError:
        return _ALIASES.get(normalized, ImageCategory.UNKNOWN)


def classify_image(
    text: str = "",
    vision_data: Mapping[str, Any] | None = None,
    *,
    has_supported_image: bool = True,
    manual_context: str = "",
) -> tuple[ImageCategory, float]:
    """Return the best category and a conservative deterministic confidence."""
    vision_data = vision_data or {}
    vision_category = normalize_image_category(vision_data.get("category"))
    vision_confidence = _safe_confidence(vision_data.get("confidence"))
    haystack = " ".join(
        [
            str(text or ""),
            str(manual_context or ""),
            " ".join(str(item) for item in vision_data.get("observations", []) or []),
            " ".join(str(item) for item in vision_data.get("risks", []) or []),
            " ".join(str(item) for item in vision_data.get("evidence_items", []) or []),
        ]
    ).lower()
    scores: dict[ImageCategory, int] = {}
    for category, keywords in _CATEGORY_KEYWORDS.items():
        scores[category] = sum(2 if " " in keyword else 1 for keyword in keywords if keyword in haystack)

    # Visible/explicit hot-work signals override a generic site-photo label.
    # A filename or user context may provide a conservative fallback when the
    # vision provider is unavailable, but never with high confidence.
    if scores.get(ImageCategory.CUTTING_GRINDING, 0):
        base = 0.72 if vision_data.get("performed") else 0.55
        return ImageCategory.CUTTING_GRINDING, min(0.92, max(base, vision_confidence))
    if scores.get(ImageCategory.HOT_WORK, 0):
        base = 0.72 if vision_data.get("performed") else 0.55
        return ImageCategory.HOT_WORK, min(0.92, max(base, vision_confidence))

    if vision_category is not ImageCategory.UNKNOWN and vision_confidence >= 0.45:
        return vision_category, vision_confidence

    best_category = max(scores, key=scores.get) if scores else ImageCategory.UNKNOWN
    best_score = scores.get(best_category, 0)
    if best_score:
        confidence = min(0.92, 0.5 + best_score * 0.08)
        return best_category, confidence
    if has_supported_image:
        # A supported file is not evidence that its visual contents were
        # actually inspected.  The caller keeps visual confidence at zero.
        return ImageCategory.GENERAL_SITE_PHOTO, 0.0
    return ImageCategory.UNKNOWN, 0.0


def _safe_confidence(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0
