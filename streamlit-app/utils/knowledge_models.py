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
        fields = cls.__dataclass_fields__
        return cls(**{key: value[key] for key in fields if key in value})
