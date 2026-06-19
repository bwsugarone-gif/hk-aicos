"""Deterministic product formatting for Ask AICOS response display."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from .analysis_models import AnalysisBasis, RiskEvidenceTrace
from .answer_modes import DEFAULT_ANSWER_MODE, normalize_answer_mode
from .risk_evidence import summarize_analysis_basis


_HEADING_MAP = {
    "最簡單講": "summary_bullets",
    "答案摘要": "summary_bullets",
    "結論": "summary_bullets",
    "初步判斷": "summary_bullets",
    "判斷依據": "judgement_basis_bullets",
    "現場判斷": "judgement_basis_bullets",
    "風險位置": "risk_impact_bullets",
    "主要風險": "risk_impact_bullets",
    "主要風險 / 影響": "risk_impact_bullets",
    "主要風險／影響": "risk_impact_bullets",
    "建議": "recommendations_bullets",
    "控制措施": "recommendations_bullets",
    "主要要求": "recommendations_bullets",
    "需確認事項": "confirmation_bullets",
    "需要留意": "confirmation_bullets",
    "跟進紀錄": "confirmation_bullets",
    "檢查清單": "confirmation_bullets",
    "合規提醒": "confirmation_bullets",
    "來源 / 限制": "source_limitations",
    "來源／限制": "source_limitations",
    "限制與免責": "source_limitations",
    "來源摘要": "source_limitations",
    "官方來源摘要": "source_limitations",
    "相關官方來源": "source_limitations",
}
_TECHNICAL_PATTERNS = re.compile(
    r"module(?:not)?founderror|traceback|provider\s*error|ai\s*供應商暫時未能回應|"
    r"provider[^\n]{0,60}(?:error|fail|unavailable)|(?:tavily|brave|gemini|anthropic|deepseek)"
    r"[^\n]{0,60}(?:error|fail|unavailable)|local-fallback\s*\(|exception\s*:|"
    r"no module named|api[_ ]?key|\b(?:gemini|anthropic|tavily|brave|deepseek|openai|claude)\b",
    re.IGNORECASE,
)


@dataclass
class AnswerDisplayModel:
    title: str = "AICOS 現場建議"
    summary_bullets: list[str] = field(default_factory=list)
    judgement_basis_bullets: list[str] = field(default_factory=list)
    risk_impact_bullets: list[str] = field(default_factory=list)
    confirmation_bullets: list[str] = field(default_factory=list)
    source_limitations: list[str] = field(default_factory=list)
    analysis_basis_labels: list[str] = field(default_factory=list)
    # Compatibility aliases retained for records/tests from earlier phases.
    site_judgement_bullets: list[str] = field(default_factory=list)
    recommendations_bullets: list[str] = field(default_factory=list)
    notes_bullets: list[str] = field(default_factory=list)
    source_summary: list[str] = field(default_factory=list)
    confidence_label: str = "需覆核"
    warning_labels: list[str] = field(default_factory=list)
    technical_note: str = ""
    memory_status: str = ""
    answer_mode: str = DEFAULT_ANSWER_MODE
    technical_status: dict[str, bool] = field(default_factory=dict)


def format_answer_display(
    raw_answer: str,
    *,
    answer_mode: str = DEFAULT_ANSWER_MODE,
    risk_level: str = "unknown",
    confidence: float = 0.0,
    source_summary: Iterable[Any] | None = None,
    warnings: Iterable[Any] | None = None,
    source_available: bool = False,
    memory_save_status: str = "",
    fallback_used: bool = False,
    risk_trace: RiskEvidenceTrace | None = None,
    analysis_basis: AnalysisBasis | None = None,
    technical_status: dict[str, bool] | None = None,
) -> AnswerDisplayModel:
    """Sanitize raw model/fallback prose into one bounded display contract."""
    mode = normalize_answer_mode(answer_mode)
    sections = _parse_sections(_sanitize_answer(raw_answer))
    external_sources = _clean_items(source_summary, 3, 220)
    parsed_sources = sections["source_limitations"]
    sources = external_sources or parsed_sources
    if not source_available:
        sources = ["本次未能核實官方具體章節，請以最新官方文件及安全主任覆核為準。"]
    elif not sources:
        sources = ["已提供來源摘要；作出安全或合規決定前仍須核對官方最新版本。"]

    warning_labels = _clean_items(warnings, 4, 180)
    if fallback_used:
        warning_labels.append("目前使用本機備用回答，請由相關負責人覆核。")
    if str(risk_level or "").lower() in {"high", "critical", "高風險", "極高風險"}:
        warning_labels.append("涉及較高風險，須由管工／安全主任按現場情況覆核。")

    summary = sections["summary_bullets"] or _fallback_summary(raw_answer)
    basis_labels = summarize_analysis_basis(analysis_basis) if analysis_basis else []
    judgement_basis = sections["judgement_basis_bullets"]
    if not judgement_basis and risk_trace:
        judgement_basis = [*risk_trace.triggered_by, *risk_trace.rules_matched]
    if not judgement_basis:
        judgement_basis = basis_labels or ["需按實際位置、工序及可觀察證據確認。"]
    risk_impacts = sections["risk_impact_bullets"]
    if not risk_impacts and risk_trace:
        risk_impacts = [risk_trace.final_reason]
    if not risk_impacts:
        risk_impacts = ["目前資料不足以確定具體危害或影響。"]
    recommendations = sections["recommendations_bullets"]
    if not recommendations:
        recommendations = ["按現場情況補充位置、工序及照片，再由相關負責人確認。"]
    confirmations = sections["confirmation_bullets"]
    if not confirmations and risk_trace:
        confirmations = risk_trace.missing_confirmations
    confirmations = confirmations or ["工序、位置、人員暴露及現有防護措施。"]

    return AnswerDisplayModel(
        summary_bullets=summary[:3],
        judgement_basis_bullets=judgement_basis[:3],
        risk_impact_bullets=risk_impacts[:3],
        confirmation_bullets=confirmations[:3],
        source_limitations=sources[:3],
        analysis_basis_labels=basis_labels[:8],
        site_judgement_bullets=judgement_basis[:3],
        recommendations_bullets=recommendations[:3],
        notes_bullets=confirmations[:3],
        source_summary=sources[:3],
        confidence_label=_confidence_label(confidence),
        warning_labels=list(dict.fromkeys(warning_labels))[:4],
        technical_note=("本機備用回答" if fallback_used else "已使用已設定文字回答"),
        memory_status=str(memory_save_status or ""),
        answer_mode=mode,
        technical_status=dict(technical_status or {}),
    )


def _parse_sections(text: str) -> dict[str, list[str]]:
    sections = {field: [] for field in (
        "summary_bullets",
        "judgement_basis_bullets",
        "risk_impact_bullets",
        "recommendations_bullets",
        "confirmation_bullets",
        "source_limitations",
    )}
    current = "summary_bullets"
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        heading = re.sub(r"^#{1,6}\s*", "", line).strip("*_` ：:")
        if heading in _HEADING_MAP:
            current = _HEADING_MAP[heading]
            continue
        clean = _clean_line(line)
        if clean:
            sections[current].append(clean)
    for key in sections:
        sections[key] = _clean_items(sections[key], 5, 240)
    return sections


def _sanitize_answer(value: Any) -> str:
    lines = []
    for line in str(value or "").replace("即時行動", "建議").splitlines():
        if _TECHNICAL_PATTERNS.search(line):
            continue
        lines.append(line)
    return "\n".join(lines)


def _clean_line(value: Any) -> str:
    line = re.sub(r"^[>*\-•\d.\s]+", "", str(value or "")).strip()
    line = re.sub(r"^#{1,6}\s*", "", line)
    line = line.replace("本機後備判斷：", "")
    line = " ".join(line.replace("即時行動", "建議").split())
    return "" if not line or _TECHNICAL_PATTERNS.search(line) else line


def _clean_items(values: Iterable[Any] | None, limit: int, max_chars: int) -> list[str]:
    cleaned = []
    for value in values or []:
        item = _clean_line(value)
        if not item:
            continue
        if len(item) > max_chars:
            item = item[: max_chars - 1].rstrip() + "…"
        cleaned.append(item)
    return list(dict.fromkeys(cleaned))[:limit]


def _fallback_summary(raw_answer: Any) -> list[str]:
    clean = _sanitize_answer(raw_answer)
    sentences = [
        _clean_line(item)
        for item in re.split(r"(?<=[。！？!?])\s*|\r?\n", clean)
    ]
    return _clean_items(sentences, 3, 220) or ["目前資料不足，請補充現場情況後再作判斷。"]


def _confidence_label(value: Any) -> str:
    try:
        confidence = max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        confidence = 0.0
    if confidence >= 0.75:
        return "較高（仍須現場覆核）"
    if confidence >= 0.5:
        return "中等（建議覆核）"
    return "有限（需要覆核）"
