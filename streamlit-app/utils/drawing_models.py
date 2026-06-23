"""Typed drawing-analysis contracts for AICOS Phase 5.10.

Models cover a drawing document (one uploaded PDF / image set), per-page
analysis, and CAD/BIM handoff items. All ``from_dict`` helpers are defensive so
old schemas, missing fields and corrupt records load without raising.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any


# ── Controlled vocabularies ────────────────────────────────────────────────
DRAWING_PAGE_TYPES = {
    "floor_plan",
    "reflected_ceiling_plan",
    "elevation",
    "section",
    "detail",
    "schedule",
    "specification",
    "title_sheet",
    "legend",
    "diagram",
    "mixed",
    "unknown",
}

DRAWING_DISCIPLINES = {
    "architecture",
    "structural",
    "mep",
    "fire_services",
    "drainage",
    "builder_works",
    "interior",
    "facade",
    "landscape",
    "unknown",
}

CAD_BIM_ACTION_TYPES = {
    "draft_new_sheet",
    "revise_existing_sheet",
    "verify_dimension",
    "verify_level",
    "verify_opening",
    "verify_mep_coordination",
    "issue_rfi",
    "add_annotation",
    "check_fire_protection",
    "check_material",
    "check_code_requirement",
    "update_schedule",
    "site_verify",
}

HANDOFF_TEAMS = {"cad", "bim", "both"}
HANDOFF_PRIORITIES = {"low", "medium", "high", "urgent"}
HANDOFF_STATUSES = {"open", "in_progress", "done", "cancelled"}
ANALYSIS_DEPTHS = {"quick", "standard", "detailed"}

# Traditional-Chinese display labels (UI only; never used as storage keys).
PAGE_TYPE_LABELS_ZH = {
    "floor_plan": "平面圖",
    "reflected_ceiling_plan": "天花反射圖",
    "elevation": "立面圖",
    "section": "剖面圖",
    "detail": "大樣／詳圖",
    "schedule": "明細表／附表",
    "specification": "規格／技術規範",
    "title_sheet": "封面／標題頁",
    "legend": "圖例",
    "diagram": "示意圖",
    "mixed": "混合內容",
    "unknown": "未能分類",
}

DISCIPLINE_LABELS_ZH = {
    "architecture": "建築",
    "structural": "結構",
    "mep": "機電",
    "fire_services": "消防",
    "drainage": "排水",
    "builder_works": "土木／建造",
    "interior": "室內",
    "facade": "幕牆／外牆",
    "landscape": "園境",
    "unknown": "未能分類",
}

ACTION_TYPE_LABELS_ZH = {
    "draft_new_sheet": "繪製新圖紙",
    "revise_existing_sheet": "修改現有圖紙",
    "verify_dimension": "核對尺寸",
    "verify_level": "核對水平／標高",
    "verify_opening": "核對開口位",
    "verify_mep_coordination": "核對機電協調",
    "issue_rfi": "發出 RFI 查詢",
    "add_annotation": "補充標註",
    "check_fire_protection": "檢查消防保護",
    "check_material": "檢查物料",
    "check_code_requirement": "檢查規範要求",
    "update_schedule": "更新明細表",
    "site_verify": "現場核實",
}


def _clean(value: Any, limit: int = 600) -> str:
    return " ".join(str(value or "").split())[:limit]


def _optional(value: Any, limit: int = 600) -> str | None:
    text = _clean(value, limit)
    return text or None


def _strings(value: Any, limit: int = 400) -> list[str]:
    if isinstance(value, str):
        value = [value]
    seen: list[str] = []
    for item in value or []:
        cleaned = _clean(item, limit)
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return seen


def _choice(value: Any, choices: set[str], default: str) -> str:
    text = str(value or "").strip().lower()
    return text if text in choices else default


def _confidence(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_payload(value: Any) -> dict:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return dict(value)
    return dict(getattr(value, "__dict__", {}) or {})


@dataclass
class CadBimHandoffItem:
    """One practical, task-oriented action handed to the CAD or BIM team.

    Phase 5.11 enriches each item so it reads like a real work order: besides the
    title/description it carries the concrete ``required_output``, the
    ``evidence`` (why the task exists) and ``verify_by`` (who should sign it off).
    """

    item_id: str
    action_type: str
    target_team: str
    title: str
    description: str = ""
    priority: str = "medium"
    page_number: int | None = None
    sheet_number: str | None = None
    discipline: str | None = None
    references: list[str] = field(default_factory=list)
    status: str = "open"
    required_output: str = ""
    evidence: str = ""
    verify_by: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Any) -> "CadBimHandoffItem":
        if isinstance(value, cls):
            return value
        payload = _as_payload(value)
        return cls(
            item_id=_clean(payload.get("item_id") or payload.get("id"), 80) or "handoff",
            action_type=_choice(payload.get("action_type"), CAD_BIM_ACTION_TYPES, "add_annotation"),
            target_team=_choice(payload.get("target_team") or payload.get("team"), HANDOFF_TEAMS, "cad"),
            title=_clean(payload.get("title") or "CAD/BIM 交接事項", 200),
            description=_clean(payload.get("description"), 1200),
            priority=_choice(payload.get("priority"), HANDOFF_PRIORITIES, "medium"),
            page_number=(_int(payload.get("page_number")) if payload.get("page_number") not in (None, "") else None),
            sheet_number=_optional(payload.get("sheet_number"), 80),
            discipline=_choice(payload.get("discipline"), DRAWING_DISCIPLINES, "unknown")
            if payload.get("discipline") else None,
            references=_strings(payload.get("references"), 200),
            status=_choice(payload.get("status"), HANDOFF_STATUSES, "open"),
            required_output=_clean(payload.get("required_output"), 600),
            evidence=_clean(payload.get("evidence") or payload.get("reason"), 600),
            verify_by=_clean(payload.get("verify_by") or payload.get("verifier"), 200),
        )


@dataclass
class DrawingPageAnalysis:
    """Analysis result for a single drawing page."""

    page_id: str
    document_id: str
    page_number: int
    created_at: str = ""
    page_type: str = "unknown"
    discipline: str = "unknown"
    sheet_number: str | None = None
    sheet_title: str | None = None
    drawing_number: str | None = None
    revision: str | None = None
    scale: str | None = None
    drawing_date: str | None = None
    project_number: str | None = None
    level_hint: str | None = None
    classification_confidence: float = 0.0
    classification_basis: list[str] = field(default_factory=list)
    title_block_fields: dict[str, Any] = field(default_factory=dict)
    extracted_text_excerpt: str = ""
    drawing_issues: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    coordination_flags: list[str] = field(default_factory=list)
    ocr_status: str = "NOT_ATTEMPTED"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Any) -> "DrawingPageAnalysis":
        if isinstance(value, cls):
            return value
        payload = _as_payload(value)
        title_block = payload.get("title_block_fields")
        return cls(
            page_id=_clean(payload.get("page_id") or payload.get("id"), 120) or "page",
            document_id=_clean(payload.get("document_id"), 120),
            page_number=_int(payload.get("page_number"), 1),
            created_at=_clean(payload.get("created_at"), 60),
            page_type=_choice(payload.get("page_type"), DRAWING_PAGE_TYPES, "unknown"),
            discipline=_choice(payload.get("discipline"), DRAWING_DISCIPLINES, "unknown"),
            sheet_number=_optional(payload.get("sheet_number"), 80),
            sheet_title=_optional(payload.get("sheet_title"), 300),
            drawing_number=_optional(payload.get("drawing_number"), 120),
            revision=_optional(payload.get("revision"), 40),
            scale=_optional(payload.get("scale"), 80),
            drawing_date=_optional(payload.get("drawing_date"), 60),
            project_number=_optional(payload.get("project_number"), 120),
            level_hint=_optional(payload.get("level_hint"), 80),
            classification_confidence=_confidence(payload.get("classification_confidence")),
            classification_basis=_strings(payload.get("classification_basis"), 200),
            title_block_fields=dict(title_block) if isinstance(title_block, dict) else {},
            extracted_text_excerpt=_clean(payload.get("extracted_text_excerpt"), 2000),
            drawing_issues=_strings(payload.get("drawing_issues"), 400),
            missing_information=_strings(payload.get("missing_information"), 400),
            coordination_flags=_strings(payload.get("coordination_flags"), 400),
            ocr_status=_clean(payload.get("ocr_status") or "NOT_ATTEMPTED", 60),
        )


@dataclass
class DrawingDocument:
    """A complete drawing upload and its aggregated analysis."""

    document_id: str
    created_at: str
    updated_at: str
    project_ref: str | None = None
    source_file_name: str | None = None
    description: str | None = None
    discipline_hint: str | None = None
    analysis_depth: str = "standard"
    page_count: int = 0
    analyzed_page_count: int = 0
    disciplines: list[str] = field(default_factory=list)
    page_types: list[str] = field(default_factory=list)
    summary: str = ""
    drawing_issues: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    coordination_flags: list[str] = field(default_factory=list)
    cad_bim_actions: list[str] = field(default_factory=list)
    handoff_items: list[CadBimHandoffItem] = field(default_factory=list)
    page_ids: list[str] = field(default_factory=list)
    ingestion_status: str = "unknown"
    vision_used: bool = False
    technical_notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["handoff_items"] = [item.to_dict() for item in self.handoff_items]
        return data

    @classmethod
    def from_dict(cls, value: Any) -> "DrawingDocument":
        if isinstance(value, cls):
            return value
        payload = _as_payload(value)
        created = _clean(payload.get("created_at") or payload.get("updated_at"), 60)
        metadata = payload.get("metadata")
        return cls(
            document_id=_clean(payload.get("document_id") or payload.get("id"), 120) or "drawing",
            created_at=created,
            updated_at=_clean(payload.get("updated_at") or created, 60),
            project_ref=_optional(payload.get("project_ref") or payload.get("project_id"), 120),
            source_file_name=_optional(payload.get("source_file_name") or payload.get("file_name"), 240),
            description=_optional(payload.get("description"), 1200),
            discipline_hint=_optional(payload.get("discipline_hint"), 120),
            analysis_depth=_choice(payload.get("analysis_depth"), ANALYSIS_DEPTHS, "standard"),
            page_count=_int(payload.get("page_count")),
            analyzed_page_count=_int(payload.get("analyzed_page_count")),
            disciplines=_strings(payload.get("disciplines"), 80),
            page_types=_strings(payload.get("page_types"), 80),
            summary=_clean(payload.get("summary"), 3000),
            drawing_issues=_strings(payload.get("drawing_issues"), 400),
            missing_information=_strings(payload.get("missing_information"), 400),
            coordination_flags=_strings(payload.get("coordination_flags"), 400),
            cad_bim_actions=_strings(payload.get("cad_bim_actions"), 400),
            handoff_items=[CadBimHandoffItem.from_dict(item) for item in (payload.get("handoff_items") or [])],
            page_ids=_strings(payload.get("page_ids"), 120),
            ingestion_status=_clean(payload.get("ingestion_status") or "unknown", 60),
            vision_used=bool(payload.get("vision_used")),
            technical_notes=_strings(payload.get("technical_notes"), 400),
            metadata=dict(metadata) if isinstance(metadata, dict) else {},
        )
