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
        fields = cls.__dataclass_fields__
        return cls(**{key: value[key] for key in fields if key in value})
