"""Typed local knowledge-pack contracts for AICOS."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


KNOWLEDGE_TRUST_LABELS = {
    "official": "官方來源",
    "trusted": "可信來源",
    "internal": "公司內部",
    "unverified": "未核實",
}


@dataclass
class KnowledgeSource:
    source_id: str
    title: str
    source_type: str
    path_or_url: str | None
    trust_level: str
    jurisdiction: str | None
    trade_tags: list[str] = field(default_factory=list)
    topic_tags: list[str] = field(default_factory=list)
    summary: str = ""
    extracted_refs: list[str] = field(default_factory=list)
    last_indexed_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict) -> "KnowledgeSource":
        payload = dict(value or {}) if isinstance(value, dict) else {}
        return cls(
            source_id=str(payload.get("source_id") or ""), title=str(payload.get("title") or "未命名知識來源"),
            source_type=str(payload.get("source_type") or "project_note"),
            path_or_url=payload.get("path_or_url") or payload.get("local_path") or payload.get("google_drive_url"),
            trust_level=str(payload.get("trust_level") or "unverified"), jurisdiction=payload.get("jurisdiction"),
            trade_tags=list(payload.get("trade_tags") or []), topic_tags=list(payload.get("topic_tags") or payload.get("tags") or []),
            summary=str(payload.get("summary") or ""), extracted_refs=list(payload.get("extracted_refs") or []),
            last_indexed_at=str(payload.get("last_indexed_at") or payload.get("created_at") or ""),
        )
