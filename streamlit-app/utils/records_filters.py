"""Pure, UI-free filter helpers for the Records record center (Phase 6.3).

Everything here is deterministic, local and dependency-free so the Records
search/filter behaviour can be unit-tested without a running Streamlit app.
Helpers accept either dataclass instances or plain dicts, and tolerate missing
fields without raising. Nothing here touches disk or exposes local paths.
"""

from __future__ import annotations

from typing import Any


def _get(item: Any, key: str, default: Any = None) -> Any:
    """Field access that works for dataclasses, objects and dicts."""
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _keywords(value: Any) -> list[str]:
    return [term for term in _norm(value).split() if term]


# ── Unified normalized records ─────────────────────────────────────────────
def filter_records_by_project(records: list[Any], project_ref: str | None) -> list[Any]:
    """Keep records matching ``project_ref`` (case-insensitive). Empty → all."""
    needle = _norm(project_ref)
    if not needle:
        return list(records or [])
    return [item for item in (records or []) if _norm(_get(item, "project_ref")) == needle]


def filter_records_by_keyword(records: list[Any], keyword: str | None) -> list[Any]:
    """Keep records whose searchable blob contains every keyword token."""
    terms = _keywords(keyword)
    if not terms:
        return list(records or [])
    output: list[Any] = []
    for item in records or []:
        blob = _record_blob(item)
        if all(term in blob for term in terms):
            output.append(item)
    return output


def filter_records_by_field(records: list[Any], field: str, value: Any) -> list[Any]:
    """Generic equality filter on one field (case-insensitive). Empty → all."""
    needle = _norm(value)
    if not needle:
        return list(records or [])
    return [item for item in (records or []) if _norm(_get(item, field)) == needle]


def _record_blob(item: Any) -> str:
    explicit = _get(item, "_blob")
    if explicit:
        return _norm(explicit)
    parts = [
        _get(item, "title"),
        _get(item, "summary"),
        _get(item, "project_ref"),
        _get(item, "source_file_name"),
        _get(item, "sheet_number"),
        _get(item, "record_type"),
        _get(item, "status"),
        _get(item, "priority"),
        _get(item, "risk_level"),
        _get(item, "responsible_team"),
    ]
    return " ".join(_norm(part) for part in parts if part)


# ── Drawing pages ──────────────────────────────────────────────────────────
def filter_drawing_pages(
    pages: list[Any],
    *,
    project_ref: str = "",
    discipline: str = "",
    page_type: str = "",
    sheet_number: str = "",
    keyword: str = "",
) -> list[Any]:
    """Filter ``DrawingPageAnalysis`` items by discipline / type / sheet / keyword."""
    project_needle = _norm(project_ref)
    sheet_needle = _norm(sheet_number)
    keyword_terms = _keywords(keyword)
    output: list[Any] = []
    for page in pages or []:
        if project_needle and _norm(_get(page, "project_ref")) != project_needle:
            continue
        if discipline and _norm(_get(page, "discipline")) != _norm(discipline):
            continue
        if page_type and _norm(_get(page, "page_type")) != _norm(page_type):
            continue
        sheet_blob = " ".join([
            _norm(_get(page, "sheet_number")),
            _norm(_get(page, "drawing_number")),
        ])
        if sheet_needle and sheet_needle not in sheet_blob:
            continue
        if keyword_terms:
            blob = " ".join([
                _norm(_get(page, "sheet_title")),
                _norm(_get(page, "extracted_text_excerpt")),
                sheet_blob,
                " ".join(_norm(x) for x in (_get(page, "drawing_issues") or [])),
            ])
            if not all(term in blob for term in keyword_terms):
                continue
        output.append(page)
    return output


# ── CAD/BIM handoff items ──────────────────────────────────────────────────
def filter_handoff_items(
    items: list[Any],
    *,
    team: str = "",
    priority: str = "",
    status: str = "",
    discipline: str = "",
    keyword: str = "",
) -> list[Any]:
    """Filter ``CadBimHandoffItem`` objects/dicts by team / priority / status / kw."""
    team_needle = _norm(team)
    priority_needle = _norm(priority)
    status_needle = _norm(status)
    discipline_needle = _norm(discipline)
    keyword_terms = _keywords(keyword)
    output: list[Any] = []
    for item in items or []:
        if team_needle and _norm(_get(item, "target_team")) != team_needle:
            continue
        if priority_needle and _norm(_get(item, "priority")) != priority_needle:
            continue
        if status_needle and _norm(_get(item, "status")) != status_needle:
            continue
        if discipline_needle and _norm(_get(item, "discipline")) != discipline_needle:
            continue
        if keyword_terms:
            blob = " ".join([
                _norm(_get(item, "title")),
                _norm(_get(item, "description")),
                _norm(_get(item, "required_output")),
                _norm(_get(item, "evidence")),
                _norm(_get(item, "sheet_number")),
            ])
            if not all(term in blob for term in keyword_terms):
                continue
        output.append(item)
    return output


# ── File registry records ──────────────────────────────────────────────────
def filter_file_records(
    records: list[Any],
    *,
    project_ref: str = "",
    file_type: str = "",
    source_module: str = "",
    keyword: str = "",
) -> list[Any]:
    """Filter ``StoredFileRecord`` items by project / type / module / keyword.

    Never reads or exposes ``local_runtime_path``; keyword search is over the
    original file name, tags and project only.
    """
    project_needle = _norm(project_ref)
    type_needle = _norm(file_type)
    module_needle = _norm(source_module)
    keyword_terms = _keywords(keyword)
    output: list[Any] = []
    for record in records or []:
        if project_needle and _norm(_get(record, "project_ref")) != project_needle:
            continue
        if type_needle and _norm(_get(record, "file_type")) != type_needle:
            continue
        if module_needle and _norm(_get(record, "source_module")) != module_needle:
            continue
        if keyword_terms:
            blob = " ".join([
                _norm(_get(record, "original_file_name")),
                _norm(_get(record, "safe_file_name")),
                _norm(_get(record, "project_ref")),
                _norm(_get(record, "file_type")),
                " ".join(_norm(x) for x in (_get(record, "tags") or [])),
            ])
            if not all(term in blob for term in keyword_terms):
                continue
        output.append(record)
    return output
