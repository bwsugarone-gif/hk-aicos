"""Pure, UI-free filter helpers for the Records drawing / CAD-BIM views (Phase 5.11E).

Kept out of the Streamlit page so the search/filter behaviour can be unit-tested
without a running app. All inputs are plain objects (``DrawingDocument`` /
``DrawingPageAnalysis`` / ``CadBimHandoffItem``); nothing here touches the disk.
"""

from __future__ import annotations

from typing import Any


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def drawing_search_blobs(document: Any, pages: list[Any]) -> tuple[str, str]:
    """Return ``(full_blob, sheet_blob)`` lowercased search text for a document."""
    sheet_blob = " ".join(
        f"{getattr(page, 'sheet_number', '') or ''} {getattr(page, 'drawing_number', '') or ''}"
        for page in pages
    )
    full = " ".join([
        document.summary or "",
        " ".join(document.drawing_issues),
        " ".join(document.missing_information),
        document.source_file_name or "",
        " ".join(item.title for item in document.handoff_items),
        sheet_blob,
    ])
    return full.lower(), sheet_blob.lower()


def filter_drawing_documents(
    documents: list[Any],
    pages_by_doc: dict[str, list[Any]],
    *,
    project_ref: str = "",
    discipline: str = "",
    page_type: str = "",
    sheet_number: str = "",
    keyword: str = "",
) -> list[Any]:
    """Filter drawing documents by project / discipline / page type / sheet / keyword."""
    keyword_needle = _norm(keyword)
    sheet_needle = _norm(sheet_number)
    output: list[Any] = []
    for document in documents:
        pages = pages_by_doc.get(document.document_id, [])
        if project_ref and (document.project_ref or "") != project_ref:
            continue
        if discipline and discipline not in document.disciplines:
            continue
        if page_type and page_type not in document.page_types:
            continue
        full_blob, sheet_blob = drawing_search_blobs(document, pages)
        if sheet_needle and sheet_needle not in sheet_blob:
            continue
        if keyword_needle and keyword_needle not in full_blob:
            continue
        output.append(document)
    return output


def filter_handoff_rows(
    rows: list[tuple[Any, Any]],
    *,
    team: str = "",
    priority: str = "",
    status: str = "",
    discipline: str = "",
    keyword: str = "",
) -> list[tuple[Any, Any]]:
    """Filter ``(document, handoff_item)`` rows by team / priority / status / discipline / keyword."""
    keyword_needle = _norm(keyword)
    output: list[tuple[Any, Any]] = []
    for document, item in rows:
        if team and item.target_team != team:
            continue
        if priority and item.priority != priority:
            continue
        if status and item.status != status:
            continue
        if discipline and (item.discipline or "") != discipline:
            continue
        blob = " ".join([
            item.title, item.description, item.required_output, item.evidence,
            item.sheet_number or "", document.source_file_name or "",
        ]).lower()
        if keyword_needle and keyword_needle not in blob:
            continue
        output.append((document, item))
    return output
