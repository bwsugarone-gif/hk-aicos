"""Typed project-memory contracts for AICOS Phase 5.8."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


MEMORY_SOURCE_TYPES = {
    "upload_analysis", "ask_aicos", "report", "follow_up",
    "knowledge_note", "manual_note",
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
    def from_dict(cls, value: dict[str, Any]) -> "ProjectMemoryRecord":
        fields = cls.__dataclass_fields__
        return cls(**{key: value[key] for key in fields if key in value})


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
