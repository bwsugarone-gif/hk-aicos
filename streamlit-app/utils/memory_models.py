"""Typed project-memory contracts for AICOS Phase 5.8."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any


MEMORY_SOURCE_TYPES = {
    "upload_analysis", "ask_aicos", "report", "follow_up",
    "knowledge_note", "manual_note", "drawing_analysis",
}
MEMORY_STATUSES = {"open", "in_progress", "resolved", "ignored", "archived"}
MEMORY_PRIORITIES = {"low", "medium", "high", "urgent"}


@dataclass
class ProjectMemoryRecord:
    memory_id: str
    created_at: str
    updated_at: str
    project_ref: str | None
    source_type: str
    title: str
    summary: str
    raw_question: str | None = None
    answer_summary: str | None = None
    analysis_type: str | None = None
    risk_level: str | None = None
    confidence: float | None = None
    evidence_sources: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    trade_tags: list[str] = field(default_factory=list)
    location_hint: str | None = None
    responsible_role: str | None = None
    status: str = "open"
    priority: str = "medium"
    due_hint: str | None = None
    linked_record_ids: list[str] = field(default_factory=list)
    source_file_name: str | None = None
    source_route: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Any) -> "ProjectMemoryRecord":
        if isinstance(value, cls):
            return value
        if is_dataclass(value):
            value = asdict(value)
        elif not isinstance(value, dict):
            value = getattr(value, "__dict__", {})
        payload = dict(value or {})
        created = str(payload.get("created_at") or payload.get("updated_at") or "")
        return cls(
            memory_id=str(payload.get("memory_id") or payload.get("record_id") or ""),
            created_at=created,
            updated_at=str(payload.get("updated_at") or created),
            project_ref=payload.get("project_ref") or payload.get("project_id") or None,
            source_type=str(payload.get("source_type") or payload.get("memory_type") or "manual_note"),
            title=str(payload.get("title") or "未命名工程記憶"),
            summary=str(payload.get("summary") or payload.get("answer_summary") or ""),
            raw_question=payload.get("raw_question"), answer_summary=payload.get("answer_summary"),
            analysis_type=payload.get("analysis_type"), risk_level=payload.get("risk_level"),
            confidence=payload.get("confidence"), evidence_sources=list(payload.get("evidence_sources") or []),
            tags=list(payload.get("tags") or []), trade_tags=list(payload.get("trade_tags") or []),
            location_hint=payload.get("location_hint"), responsible_role=payload.get("responsible_role"),
            status=str(payload.get("status") or "open"), priority=str(payload.get("priority") or "medium"),
            due_hint=payload.get("due_hint"),
            linked_record_ids=list(payload.get("linked_record_ids") or payload.get("related_record_ids") or []),
            source_file_name=payload.get("source_file_name"), source_route=payload.get("source_route"),
            metadata=dict(payload.get("metadata") or payload.get("raw_payload") or {}),
        )


@dataclass
class ProjectMemorySummary:
    project_ref: str | None
    total_records: int = 0
    open_count: int = 0
    high_risk_count: int = 0
    repeated_tags: list[tuple[str, int]] = field(default_factory=list)
    recent_records: list[ProjectMemoryRecord] = field(default_factory=list)
    unresolved_items: list[ProjectMemoryRecord] = field(default_factory=list)
    suggested_next_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
