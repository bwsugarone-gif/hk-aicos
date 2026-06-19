"""Stable, dependency-light data contracts for AICOS evidence tracing."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


class EvidenceSerializableModel:
    """Minimal JSON-safe mixin kept independent from the wider model module."""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AnalysisBasis(EvidenceSerializableModel):
    text_extraction_basis: list[str] = field(default_factory=list)
    vision_basis: list[str] = field(default_factory=list)
    manual_description_basis: list[str] = field(default_factory=list)
    knowledge_basis: list[str] = field(default_factory=list)
    memory_basis: list[str] = field(default_factory=list)
    rule_basis: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass
class RiskEvidenceTrace(EvidenceSerializableModel):
    risk_level: str = "unknown"
    triggered_by: list[str] = field(default_factory=list)
    evidence_sources: list[str] = field(default_factory=list)
    rules_matched: list[str] = field(default_factory=list)
    missing_confirmations: list[str] = field(default_factory=list)
    confidence_reason: str = ""
    final_reason: str = ""
