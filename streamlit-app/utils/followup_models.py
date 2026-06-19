"""Typed follow-up workflow model for AICOS Phase 5.8."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass


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
    def from_dict(cls, value) -> "FollowUpItem":
        if isinstance(value, cls):
            return value
        if is_dataclass(value):
            value = asdict(value)
        elif not isinstance(value, dict):
            value = getattr(value, "__dict__", {})
        payload = dict(value or {})
        created = str(payload.get("created_at") or payload.get("updated_at") or "")
        return cls(
            followup_id=str(payload.get("followup_id") or payload.get("record_id") or ""),
            created_at=created, updated_at=str(payload.get("updated_at") or created),
            project_ref=payload.get("project_ref") or payload.get("project_id") or None,
            title=str(payload.get("title") or "需跟進事項"),
            description=str(payload.get("description") or payload.get("summary") or ""),
            source_memory_id=payload.get("source_memory_id"), source_record_id=payload.get("source_record_id"),
            risk_level=payload.get("risk_level"), priority=str(payload.get("priority") or "medium"),
            status=str(payload.get("status") or "open"), responsible_role=payload.get("responsible_role"),
            due_hint=payload.get("due_hint"), evidence_required=list(payload.get("evidence_required") or []),
            suggested_actions=list(payload.get("suggested_actions") or []),
            closeout_notes=payload.get("closeout_notes"), history=list(payload.get("history") or []),
        )
