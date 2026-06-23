"""Append-only UTF-8 JSONL stores for drawing documents and page analyses.

Two runtime stores live under ``streamlit-app/data`` (git-ignored):

* ``drawing_analysis.jsonl`` — :class:`DrawingDocument` records (latest wins).
* ``drawing_pages.jsonl``    — :class:`DrawingPageAnalysis` records.

Reads tolerate missing files, blank/corrupt lines, old schemas and missing
fields. Writes are append-only with a process lock + fsync, mirroring the
existing project-memory / follow-up stores.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .drawing_models import DrawingDocument, DrawingPageAnalysis


_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_DRAWING_DOC_PATH = _DATA_DIR / "drawing_analysis.jsonl"
DEFAULT_DRAWING_PAGE_PATH = _DATA_DIR / "drawing_pages.jsonl"
_LOCK = threading.Lock()


def new_document_id() -> str:
    return f"draw_{uuid.uuid4().hex}"


def new_page_id(document_id: str, page_number: int) -> str:
    return f"{document_id}_p{int(page_number):03d}"


def new_handoff_id() -> str:
    return f"handoff_{uuid.uuid4().hex[:12]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    with _LOCK:
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(encoded + "\n")
            handle.flush()
            os.fsync(handle.fileno())


def _read_lines(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
            if isinstance(payload, dict):
                rows.append(payload)
    except OSError:
        return []
    return rows


# ── Drawing documents ──────────────────────────────────────────────────────
def append_drawing_document(
    document: DrawingDocument | dict[str, Any],
    *,
    path: str | Path = DEFAULT_DRAWING_DOC_PATH,
) -> DrawingDocument:
    record = DrawingDocument.from_dict(document)
    now = _now()
    if not record.document_id or record.document_id == "drawing":
        record.document_id = new_document_id()
    if not record.created_at:
        record.created_at = now
    record.updated_at = now
    _append(Path(path), record.to_dict())
    return record


def read_all_drawing_documents(
    *,
    path: str | Path = DEFAULT_DRAWING_DOC_PATH,
) -> list[DrawingDocument]:
    latest: dict[str, DrawingDocument] = {}
    for payload in _read_lines(Path(path)):
        try:
            record = DrawingDocument.from_dict(payload)
        except (TypeError, ValueError, KeyError):
            continue
        if record.document_id:
            latest[record.document_id] = record
    return sorted(
        latest.values(),
        key=lambda item: item.updated_at or item.created_at,
        reverse=True,
    )


def get_drawing_document(
    document_id: str,
    *,
    path: str | Path = DEFAULT_DRAWING_DOC_PATH,
) -> DrawingDocument | None:
    return next(
        (item for item in read_all_drawing_documents(path=path) if item.document_id == document_id),
        None,
    )


def list_recent_drawing_documents(
    project_ref: str | None = None,
    *,
    limit: int = 10,
    path: str | Path = DEFAULT_DRAWING_DOC_PATH,
) -> list[DrawingDocument]:
    items = read_all_drawing_documents(path=path)
    if project_ref:
        items = [item for item in items if (item.project_ref or "").lower() == project_ref.lower()]
    return items[: max(0, int(limit))] if limit is not None else items


# ── Drawing pages ──────────────────────────────────────────────────────────
def append_drawing_page(
    page: DrawingPageAnalysis | dict[str, Any],
    *,
    path: str | Path = DEFAULT_DRAWING_PAGE_PATH,
) -> DrawingPageAnalysis:
    record = DrawingPageAnalysis.from_dict(page)
    if not record.created_at:
        record.created_at = _now()
    _append(Path(path), record.to_dict())
    return record


def append_drawing_pages(
    pages: list[DrawingPageAnalysis | dict[str, Any]],
    *,
    path: str | Path = DEFAULT_DRAWING_PAGE_PATH,
) -> list[DrawingPageAnalysis]:
    return [append_drawing_page(page, path=path) for page in pages or []]


def read_pages_for_document(
    document_id: str,
    *,
    path: str | Path = DEFAULT_DRAWING_PAGE_PATH,
) -> list[DrawingPageAnalysis]:
    latest: dict[str, DrawingPageAnalysis] = {}
    for payload in _read_lines(Path(path)):
        try:
            record = DrawingPageAnalysis.from_dict(payload)
        except (TypeError, ValueError, KeyError):
            continue
        if record.document_id == document_id and record.page_id:
            latest[record.page_id] = record
    return sorted(latest.values(), key=lambda item: item.page_number)


def list_recent_handoff_items(
    project_ref: str | None = None,
    *,
    limit: int = 20,
    path: str | Path = DEFAULT_DRAWING_DOC_PATH,
) -> list[tuple[DrawingDocument, "CadBimHandoffItemRef"]]:
    """Return recent handoff items paired with their parent document."""
    pairs: list[tuple[DrawingDocument, Any]] = []
    for document in list_recent_drawing_documents(project_ref, limit=None, path=path):
        for item in document.handoff_items:
            pairs.append((document, item))
    return pairs[: max(0, int(limit))] if limit is not None else pairs


# Lightweight alias for typing clarity in callers.
CadBimHandoffItemRef = Any
