"""Local keyword-RAG data contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class RagChunk:
    chunk_id: str
    source_id: str
    title: str
    source_type: str
    trust_level: str
    project_ref: str | None
    section_ref: str | None
    page_ref: str | None
    text: str
    summary: str
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict) -> "RagChunk":
        payload = dict(value or {}) if isinstance(value, dict) else {}
        return cls(
            chunk_id=str(payload.get("chunk_id") or ""), source_id=str(payload.get("source_id") or ""),
            title=str(payload.get("title") or "未命名片段"), source_type=str(payload.get("source_type") or "project_note"),
            trust_level=str(payload.get("trust_level") or "unverified"), project_ref=payload.get("project_ref") or payload.get("project_id"),
            section_ref=payload.get("section_ref"), page_ref=payload.get("page_ref"),
            text=str(payload.get("text") or payload.get("summary") or ""), summary=str(payload.get("summary") or ""),
            tags=list(payload.get("tags") or []), created_at=str(payload.get("created_at") or ""),
            metadata=dict(payload.get("metadata") or {}),
        )
