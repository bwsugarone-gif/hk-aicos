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
    # Phase 6.4 ingestion fields (backward compatible; default when absent).
    source_file_name: str | None = None
    page_number: int | None = None
    confidence: float = 1.0

    @property
    def source_title(self) -> str:
        """Alias kept for the Phase 6.4 chunk schema (source_title == title)."""
        return self.title

    @property
    def section_hint(self) -> str | None:
        """Alias kept for the Phase 6.4 chunk schema (section_hint == section_ref)."""
        return self.section_ref

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict) -> "RagChunk":
        payload = dict(value or {}) if isinstance(value, dict) else {}
        page_number = payload.get("page_number")
        if page_number in (None, ""):
            page_number = None
        else:
            try:
                page_number = int(page_number)
            except (TypeError, ValueError):
                page_number = None
        confidence = payload.get("confidence")
        try:
            confidence = float(confidence) if confidence not in (None, "") else 1.0
        except (TypeError, ValueError):
            confidence = 1.0
        return cls(
            chunk_id=str(payload.get("chunk_id") or ""), source_id=str(payload.get("source_id") or ""),
            title=str(payload.get("title") or payload.get("source_title") or "未命名片段"),
            source_type=str(payload.get("source_type") or "project_note"),
            trust_level=str(payload.get("trust_level") or "unverified"), project_ref=payload.get("project_ref") or payload.get("project_id"),
            section_ref=payload.get("section_ref") or payload.get("section_hint"), page_ref=payload.get("page_ref"),
            text=str(payload.get("text") or payload.get("summary") or ""), summary=str(payload.get("summary") or ""),
            tags=list(payload.get("tags") or []), created_at=str(payload.get("created_at") or ""),
            metadata=dict(payload.get("metadata") or {}),
            source_file_name=payload.get("source_file_name") or (payload.get("metadata") or {}).get("source_file_name"),
            page_number=page_number,
            confidence=max(0.0, min(1.0, confidence)),
        )
