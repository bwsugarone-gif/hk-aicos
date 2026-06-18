"""Extract specific, non-invented document references from supplied sources."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any, Iterable
from urllib.parse import unquote, urlsplit

from .analysis_models import SourceReference


_REFERENCE_PATTERNS = {
    "chapter": (
        re.compile(r"第\s*([0-9]+(?:\.[0-9]+)*)\s*章"),
        re.compile(r"\bChapter\s+([0-9]+(?:\.[0-9]+)*)", re.IGNORECASE),
    ),
    "section": (
        re.compile(r"第\s*([0-9]+(?:\.[0-9]+)*)\s*節"),
        re.compile(r"\bSection\s+([0-9]+(?:\.[0-9]+)*)", re.IGNORECASE),
    ),
    "clause": (
        re.compile(r"第\s*([0-9]+(?:\.[0-9]+)*)\s*條"),
        re.compile(r"\bClause\s+([0-9]+(?:\.[0-9]+)*)", re.IGNORECASE),
    ),
    "paragraph": (
        re.compile(r"第\s*([0-9]+(?:\.[0-9]+)*)\s*段"),
        re.compile(r"\b(?:Paragraph|Para\.?)\s+([0-9]+(?:\.[0-9]+)*)", re.IGNORECASE),
    ),
    "page": (
        re.compile(r"(?:第\s*)?([0-9]{1,4})\s*頁"),
        re.compile(r"\b(?:page|p\.)\s*([0-9]{1,4})\b", re.IGNORECASE),
    ),
}

_GENERIC_NUMBER = re.compile(r"(?<![\d.])([0-9]{1,2}\.[0-9]{1,2}(?:\.[0-9]{1,2}){0,2})(?![\d.])")
_DOCUMENT_TITLE = re.compile(r"《([^》]{2,120})》")
_RELEVANCE_TERMS = (
    "高空",
    "防墮",
    "墮下",
    "護欄",
    "踢腳板",
    "工作平台",
    "安全帶",
    "吊船",
    "棚架",
    "法例",
    "守則",
    "指引",
    "working at height",
    "fall",
    "guardrail",
    "harness",
)


def extract_source_reference(source: Any, question: str = "") -> SourceReference:
    data = _as_dict(source)
    title = str(data.get("source_title") or data.get("title") or "未命名來源").strip()
    url = str(data.get("source_url") or data.get("url") or "").strip()
    snippet = " ".join(str(data.get("snippet") or data.get("content_summary") or "").split())
    document_title = _find_document_title(data, title, snippet, url)
    searchable = " ".join(part for part in (title, document_title, snippet) if part)

    values: dict[str, str] = {name: "" for name in _REFERENCE_PATTERNS}
    selected_spans: list[tuple[int, int]] = []
    explicit_found = False
    for name, patterns in _REFERENCE_PATTERNS.items():
        match = _best_match(patterns, searchable, question)
        if match:
            values[name] = match.group(1)
            selected_spans.append(match.span())
            explicit_found = True

    generic_found = False
    if not values["section"] and not values["clause"]:
        # Bare numbers are only accepted from the supplied snippet, avoiding
        # accidental extraction of version numbers from a page title.
        generic_match = _best_match((_GENERIC_NUMBER,), snippet, question)
        if generic_match:
            number = generic_match.group(1)
            if number.count(".") >= 2:
                values["clause"] = number
            else:
                values["section"] = number
            snippet_offset = searchable.find(snippet)
            selected_spans.append(
                (
                    max(0, snippet_offset) + generic_match.start(),
                    max(0, snippet_offset) + generic_match.end(),
                )
            )
            generic_found = True

    if explicit_found:
        confidence = 0.95
    elif generic_found:
        confidence = 0.72
    elif document_title:
        confidence = 0.45
    else:
        confidence = 0.2

    return SourceReference(
        source_id=str(data.get("source_id") or ""),
        title=title,
        trust_level=str(data.get("trust_level") or "unknown"),
        url=url,
        document_title=document_title,
        chapter=values["chapter"],
        section=values["section"],
        clause=values["clause"],
        paragraph=values["paragraph"],
        page=values["page"],
        excerpt=_reference_excerpt(searchable, selected_spans),
        reference_confidence=confidence,
    )


def extract_source_references(sources: Iterable[Any], question: str = "") -> list[SourceReference]:
    references: list[SourceReference] = []
    seen: set[str] = set()
    for source in sources:
        reference = extract_source_reference(source, question)
        identity = reference.source_id or reference.url or reference.title
        if identity not in seen:
            references.append(reference)
            seen.add(identity)
    return references


def has_specific_reference(reference: SourceReference) -> bool:
    return any((reference.chapter, reference.section, reference.clause, reference.paragraph, reference.page))


def format_source_reference(reference: SourceReference) -> str:
    publisher = _publisher_name(reference.url, reference.title)
    document_title = reference.document_title or reference.title
    named_document = f"《{document_title}》" if document_title else "相關文件"
    prefix = f"來源：{publisher}{named_document}" if publisher else f"來源：{named_document}"
    details = []
    if reference.chapter:
        details.append(f"第 {reference.chapter} 章")
    if reference.section:
        details.append(f"第 {reference.section} 節")
    if reference.clause:
        details.append(f"第 {reference.clause} 條")
    if reference.paragraph:
        details.append(f"第 {reference.paragraph} 段")
    if reference.page:
        details.append(f"第 {reference.page} 頁")
    return prefix + ("，" + "、".join(details) if details else "（未能確認具體章節）")


def _best_match(patterns: Iterable[re.Pattern[str]], text: str, question: str) -> re.Match[str] | None:
    matches = [match for pattern in patterns for match in pattern.finditer(text)]
    if not matches:
        return None
    return max(matches, key=lambda match: _match_score(match, text, question))


def _match_score(match: re.Match[str], text: str, question: str) -> tuple[int, int]:
    start = max(0, match.start() - 100)
    end = min(len(text), match.end() + 100)
    context = text[start:end].lower()
    question_lower = str(question or "").lower()
    relevant_terms = [term for term in _RELEVANCE_TERMS if term in question_lower]
    overlap = sum(term in context for term in relevant_terms)
    return overlap, -match.start()


def _find_document_title(data: dict[str, Any], title: str, snippet: str, url: str) -> str:
    for key in ("document_title", "pdf_title"):
        value = str(data.get(key) or "").strip()
        if value:
            return value
    title_match = _DOCUMENT_TITLE.search(" ".join((title, snippet)))
    if title_match:
        return title_match.group(1).strip()
    if title and title not in {"未命名來源", "Untitled result"}:
        return title
    path_name = unquote(PurePosixPath(urlsplit(url).path).name)
    return path_name.rsplit(".", 1)[0] if path_name.lower().endswith(".pdf") else ""


def _reference_excerpt(text: str, spans: list[tuple[int, int]], limit: int = 280) -> str:
    if not text:
        return ""
    if spans:
        start = max(0, min(span[0] for span in spans) - 90)
        end = min(len(text), max(span[1] for span in spans) + 140)
        excerpt = text[start:end]
    else:
        excerpt = text[:limit]
    excerpt = " ".join(excerpt.split())
    return excerpt if len(excerpt) <= limit else excerpt[: limit - 1].rstrip() + "…"


def _publisher_name(url: str, title: str) -> str:
    value = f"{url} {title}".lower()
    publishers = (
        (("labour.gov.hk", "勞工處"), "勞工處"),
        (("bd.gov.hk", "屋宇署"), "屋宇署"),
        (("emsd.gov.hk", "機電工程署"), "機電工程署"),
        (("devb.gov.hk", "發展局"), "發展局"),
        (("elegislation.gov.hk", "e-legislation.gov.hk", "香港法例"), "香港法例電子版"),
        (("cic.hk", "建造業議會"), "建造業議會"),
    )
    for needles, label in publishers:
        if any(needle in value for needle in needles):
            return label
    return ""


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return {
        key: getattr(value, key)
        for key in (
            "source_id",
            "source_title",
            "title",
            "source_url",
            "url",
            "trust_level",
            "snippet",
            "document_title",
            "pdf_title",
        )
        if hasattr(value, key)
    }
