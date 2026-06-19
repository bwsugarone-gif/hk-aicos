"""Deterministic product formatting for Ask AICOS response display."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from .answer_modes import DEFAULT_ANSWER_MODE, normalize_answer_mode


_HEADING_MAP = {
    "最簡單講": "summary_bullets",
    "答案摘要": "summary_bullets",
    "結論": "summary_bullets",
    "初步判斷": "summary_bullets",
    "現場判斷": "site_judgement_bullets",
    "風險位置": "site_judgement_bullets",
    "主要風險": "site_judgement_bullets",
    "建議": "recommendations_bullets",
    "控制措施": "recommendations_bullets",
    "主要要求": "recommendations_bullets",
    "需要留意": "notes_bullets",
    "跟進紀錄": "notes_bullets",
    "檢查清單": "notes_bullets",
    "合規提醒": "notes_bullets",
    "限制與免責": "notes_bullets",
    "來源摘要": "source_summary",
    "官方來源摘要": "source_summary",
    "相關官方來源": "source_summary",
}
_TECHNICAL_PATTERNS = re.compile(
    r"module(?:not)?founderror|traceback|provider\s*error|ai\s*供應商暫時未能回應|"
    r"provider[^\n]{0,60}(?:error|fail|unavailable)|(?:tavily|brave|gemini|anthropic|deepseek)"
    r"[^\n]{0,60}(?:error|fail|unavailable)|local-fallback\s*\(|exception\s*:|"
    r"no module named|api[_ ]?key",
    re.IGNORECASE,
)


@dataclass
class AnswerDisplayModel:
    title: str = "AICOS 現場建議"
    summary_bullets: list[str] = field(default_factory=list)
    site_judgement_bullets: list[str] = field(default_factory=list)
    recommendations_bullets: list[str] = field(default_factory=list)
    notes_bullets: list[str] = field(default_factory=list)
    source_summary: list[str] = field(default_factory=list)
    confidence_label: str = "需覆核"
    warning_labels: list[str] = field(default_factory=list)
    technical_note: str = ""
    memory_status: str = ""
    answer_mode: str = DEFAULT_ANSWER_MODE


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
) -> AnswerDisplayModel:
    """Sanitize raw model/fallback prose into one bounded display contract."""
    mode = normalize_answer_mode(answer_mode)
    sections = _parse_sections(_sanitize_answer(raw_answer))
    external_sources = _clean_items(source_summary, 3, 220)
    parsed_sources = sections["source_summary"]
    sources = external_sources or parsed_sources
    if not source_available:
        sources = ["本次沒有可核實官方來源；請由安全主任按最新指引覆核。"]

    warning_labels = _clean_items(warnings, 4, 180)
    if fallback_used:
        warning_labels.append("目前使用本機備用回答模式。建議仍須按現場情況及最新官方文件覆核。")
    if str(risk_level or "").lower() in {"high", "critical", "高風險", "極高風險"}:
        warning_labels.append("涉及較高風險，須由管工／安全主任按現場情況覆核。")

    summary = sections["summary_bullets"] or _fallback_summary(raw_answer)
    site_judgement = sections["site_judgement_bullets"]
    if not site_judgement:
        site_judgement = ["需按實際位置、工序及現場狀況確認。"]
    recommendations = sections["recommendations_bullets"]
    if not recommendations:
        recommendations = ["按現場情況補充位置、工序及照片，再由相關負責人確認。"]
    notes = sections["notes_bullets"] or ["安全及合規決定仍由合資格人士及現場管理人員覆核。"]

    return AnswerDisplayModel(
        summary_bullets=summary[:3],
        site_judgement_bullets=site_judgement[:3],
        recommendations_bullets=recommendations[:3],
        notes_bullets=notes[:3],
        source_summary=sources[:3],
        confidence_label=_confidence_label(confidence),
        warning_labels=list(dict.fromkeys(warning_labels))[:4],
        technical_note=("本機備用回答模式" if fallback_used else "AI 回答模式"),
        memory_status=str(memory_save_status or ""),
        answer_mode=mode,
    )


def _parse_sections(text: str) -> dict[str, list[str]]:
    sections = {field: [] for field in (
        "summary_bullets",
        "site_judgement_bullets",
        "recommendations_bullets",
        "notes_bullets",
        "source_summary",
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
