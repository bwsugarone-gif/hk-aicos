"""Typed follow-up workflow model for AICOS Phase 5.8."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


FOLLOWUP_STATUSES = {"open", "in_progress", "waiting", "resolved", "cancelled"}
FOLLOWUP_PRIORITIES = {"low", "medium", "high", "urgent"}


@dataclass
class FollowUpItem:
    followup_id: str
    created_at: str
    updated_at: str
    project_ref: str | None
    title: str
    description: str
    source_memory_id: str | None = None
    source_record_id: str | None = None
    risk_level: str | None = None
    priority: str = "medium"
    status: str = "open"
    responsible_role: str | None = None
    due_hint: str | None = None
    evidence_required: list[str] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)
    closeout_notes: str | None = None
    history: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict) -> "FollowUpItem":
        fields = cls.__dataclass_fields__
        return cls(**{key: value[key] for key in fields if key in value})
