"""Shared typed models for AICOS image analysis, search, Q&A, and records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ImageCategory(str, Enum):
    SAFETY_ISSUE = "safety_issue"
    HOT_WORK = "hot_work"
    CUTTING_GRINDING = "cutting_grinding"
    FIRE_RISK = "fire_risk"
    PPE_ISSUE = "ppe_issue"
    CONSTRUCTION_DEFECT = "construction_defect"
    MATERIAL_DELIVERY = "material_delivery"
    HANDWRITTEN_RECORD = "handwritten_record"
    ATTENDANCE_OR_TIMESHEET = "attendance_or_timesheet"
    GENERAL_SITE_PHOTO = "general_site_photo"
    UNKNOWN = "unknown"


class SerializableModel:
    """Small dataclass mixin that converts enums into JSON-safe values."""

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


def _json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


@dataclass
class OCRResult(SerializableModel):
    text: str = ""
    confidence: float = 0.0
    engine: str = "local_ocr"
    language: str = "eng+chi_tra"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidenceContext(SerializableModel):
    """Evidence gate shared by image classification, risks, and reporting."""

    has_ocr_text: bool = False
    ocr_confidence: float = 0.0
    has_visual_analysis: bool = False
    visual_confidence: float = 0.0
    visual_observations: list[str] = field(default_factory=list)
    user_description: str = ""
    selected_analysis_type: str = ""
    evidenced_terms: list[str] = field(default_factory=list)
    unsupported_terms: list[str] = field(default_factory=list)


@dataclass
class FollowUpSuggestion(SerializableModel):
    title: str
    action: str
    priority: str
    responsible_role: str
    due_hint: str
    reason: str


@dataclass
class ImageAnalysisResult(SerializableModel):
    extracted_text: str = ""
    detected_category: ImageCategory = ImageCategory.UNKNOWN
    # ``confidence`` remains as a compatibility alias for visual confidence.
    # OCR confidence must never be used as overall image/risk confidence.
    confidence: float = 0.0
    key_observations: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    recommended_followups: list[FollowUpSuggestion] = field(default_factory=list)
    source_engine: str = "local_heuristic"
    raw_metadata: dict[str, Any] = field(default_factory=dict)
    ocr_text: str = ""
    ocr_confidence: float = 0.0
    visual_confidence: float = 0.0
    image_category: ImageCategory = ImageCategory.UNKNOWN
    visual_observations: list[str] = field(default_factory=list)
    evidence_items: list[str] = field(default_factory=list)
    unsupported_assumptions: list[str] = field(default_factory=list)
    needs_manual_review: bool = False


@dataclass
class KnowledgeSnippet(SerializableModel):
    title: str
    path: str
    snippet: str
    score: float
    source_type: str
    source_id: str = ""
    trust_level: str = "local_internal"
    provider: str = "local_keyword"
    retrieved_at: str | None = None
    used_in_answer: bool = False


@dataclass
class SearchResult(SerializableModel):
    title: str
    url: str
    snippet: str
    source: str
    published_date: str | None = None
    confidence: float | None = None
    source_id: str = ""
    source_type: str = "general_web"
    trust_level: str = "unknown"
    provider: str = ""
    retrieved_at: str | None = None
    used_in_answer: bool = False


@dataclass
class SourceCitation(SerializableModel):
    source_id: str
    source_title: str
    source_url: str = ""
    source_path: str = ""
    source_type: str = "unknown"
    trust_level: str = "unknown"
    snippet: str = ""
    used_in_answer: bool = False
    provider: str = ""
    retrieved_at: str | None = None


@dataclass
class SourceReference(SerializableModel):
    source_id: str
    title: str
    trust_level: str = "unknown"
    url: str = ""
    document_title: str = ""
    chapter: str = ""
    section: str = ""
    clause: str = ""
    paragraph: str = ""
    page: str = ""
    excerpt: str = ""
    reference_confidence: float = 0.0


@dataclass
class QAResponse(SerializableModel):
    answer: str
    practical_recommendations: list[str] = field(default_factory=list)
    risk_level: str = "unknown"
    sources: list[SourceCitation | dict[str, Any]] = field(default_factory=list)
    followup_actions: list[str] = field(default_factory=list)
    confidence: float = 0.0
    used_search_scope: str = "local_knowledge"
    model_name: str = "local-fallback"
    fallback_used: bool = True


@dataclass
class SiteRecord(SerializableModel):
    record_id: str
    created_at: str
    record_type: str
    title: str
    content_summary: str
    source: str
    category: str = "general"
    risk_level: str = ""
    priority: str = ""
    status: str = "open"
    responsible_role: str = ""
    due_hint: str = ""
    remarks: str = ""
    updated_at: str = ""
    history: list[dict[str, Any]] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SiteRecord":
        values = {
            key: data[key]
            for key in cls.__dataclass_fields__
            if key in data and data[key] is not None
        }
        values.setdefault("history", [])
        values.setdefault("raw_payload", {})
        return cls(**values)
