"""Unified, deterministic record search across AICOS data stores (Phase 6.3).

Normalizes records from eight sources — project memory, follow-up items,
knowledge sources, RAG chunks, drawing documents, drawing page analyses,
CAD/BIM handoff items and the file registry — into a single
:class:`UnifiedRecord` shape, then offers local keyword + field filtering.

No embeddings, no network. All store reads are best-effort and wrapped so a
missing file, corrupt JSONL line or absent module never crashes the page.
Local filesystem paths are never carried into a unified record.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .records_filters import (
    filter_records_by_field,
    filter_records_by_keyword,
    filter_records_by_project,
)


RECORD_TYPE_LABELS_ZH = {
    "project_memory": "工程記憶",
    "follow_up": "跟進事項",
    "knowledge_source": "知識來源",
    "rag_chunk": "RAG 片段",
    "drawing_document": "圖紙文件",
    "drawing_page": "圖紙頁面",
    "cad_bim_handoff": "CAD/BIM 交接",
    "file_record": "檔案登記",
}


@dataclass
class UnifiedRecord:
    record_type: str
    record_id: str
    title: str
    summary: str = ""
    project_ref: str | None = None
    source_file_name: str | None = None
    sheet_number: str | None = None
    page_type: str | None = None
    discipline: str | None = None
    status: str | None = None
    priority: str | None = None
    risk_level: str | None = None
    responsible_team: str | None = None
    created_at: str = ""
    linked_ids: dict[str, Any] = field(default_factory=dict)

    @property
    def type_label(self) -> str:
        return RECORD_TYPE_LABELS_ZH.get(self.record_type, self.record_type)

    @property
    def blob(self) -> str:
        parts = [
            self.title, self.summary, self.project_ref, self.source_file_name,
            self.sheet_number, self.page_type, self.discipline, self.status,
            self.priority, self.risk_level, self.responsible_team, self.record_type,
        ]
        return " ".join(str(p) for p in parts if p).lower()

    def to_card_dict(self) -> dict[str, Any]:
        """Compact, UI-safe card (no raw JSON, no paths)."""
        return {
            "type_label": self.type_label,
            "record_type": self.record_type,
            "title": self.title,
            "project_ref": self.project_ref,
            "source_file_name": self.source_file_name,
            "sheet_number": self.sheet_number,
            "status": self.status,
            "priority": self.priority,
            "risk_level": self.risk_level,
            "summary": (self.summary or "")[:280],
            "created_at": self.created_at,
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _s(value: Any, limit: int = 600) -> str:
    return " ".join(str(value or "").split())[:limit]


def _opt(value: Any, limit: int = 600) -> str | None:
    text = _s(value, limit)
    return text or None


# ── Per-source normalizers ─────────────────────────────────────────────────
def _from_memory(item: Any) -> UnifiedRecord:
    return UnifiedRecord(
        record_type="project_memory",
        record_id=_s(getattr(item, "memory_id", ""), 120),
        title=_s(getattr(item, "title", "") or "工程記憶", 200),
        summary=_s(getattr(item, "summary", ""), 280),
        project_ref=_opt(getattr(item, "project_ref", None), 120),
        source_file_name=_opt(getattr(item, "source_file_name", None), 240),
        status=_opt(getattr(item, "status", None), 40),
        priority=_opt(getattr(item, "priority", None), 40),
        risk_level=_opt(getattr(item, "risk_level", None), 40),
        responsible_team=_opt(getattr(item, "responsible_role", None), 120),
        created_at=_s(getattr(item, "created_at", ""), 60),
        linked_ids={"memory_id": getattr(item, "memory_id", None),
                    "linked_record_ids": list(getattr(item, "linked_record_ids", []) or [])},
    )


def _from_followup(item: Any) -> UnifiedRecord:
    return UnifiedRecord(
        record_type="follow_up",
        record_id=_s(getattr(item, "followup_id", ""), 120),
        title=_s(getattr(item, "title", "") or "跟進事項", 200),
        summary=_s(getattr(item, "description", ""), 280),
        project_ref=_opt(getattr(item, "project_ref", None), 120),
        status=_opt(getattr(item, "status", None), 40),
        priority=_opt(getattr(item, "priority", None), 40),
        risk_level=_opt(getattr(item, "risk_level", None), 40),
        responsible_team=_opt(getattr(item, "responsible_role", None), 120),
        created_at=_s(getattr(item, "created_at", ""), 60),
        linked_ids={"source_memory_id": getattr(item, "source_memory_id", None),
                    "source_record_id": getattr(item, "source_record_id", None)},
    )


def _from_knowledge_source(item: Any) -> UnifiedRecord:
    return UnifiedRecord(
        record_type="knowledge_source",
        record_id=_s(getattr(item, "source_id", ""), 120),
        title=_s(getattr(item, "title", "") or "知識來源", 200),
        summary=_s(getattr(item, "summary", ""), 280),
        source_file_name=_opt(getattr(item, "title", None), 240),
        status=_opt(getattr(item, "trust_level", None), 40),
        created_at=_s(getattr(item, "last_indexed_at", ""), 60),
        linked_ids={"source_id": getattr(item, "source_id", None)},
    )


def _from_rag_chunk(item: Any) -> UnifiedRecord:
    page_number = getattr(item, "page_number", None)
    return UnifiedRecord(
        record_type="rag_chunk",
        record_id=_s(getattr(item, "chunk_id", ""), 120),
        title=_s(getattr(item, "title", "") or "RAG 片段", 200),
        summary=_s(getattr(item, "text", "") or getattr(item, "summary", ""), 280),
        project_ref=_opt(getattr(item, "project_ref", None), 120),
        source_file_name=_opt(getattr(item, "source_file_name", None), 240),
        sheet_number=_opt(f"p.{page_number}" if page_number else None, 40),
        created_at=_s(getattr(item, "created_at", ""), 60),
        linked_ids={"source_id": getattr(item, "source_id", None),
                    "page_number": page_number},
    )


def _from_drawing_document(item: Any) -> UnifiedRecord:
    disciplines = list(getattr(item, "disciplines", []) or [])
    return UnifiedRecord(
        record_type="drawing_document",
        record_id=_s(getattr(item, "document_id", ""), 120),
        title=_s(getattr(item, "source_file_name", None) or getattr(item, "document_id", "") or "圖紙文件", 240),
        summary=_s(getattr(item, "summary", ""), 280),
        project_ref=_opt(getattr(item, "project_ref", None), 120),
        source_file_name=_opt(getattr(item, "source_file_name", None), 240),
        discipline=_opt(disciplines[0] if disciplines else None, 40),
        status=_opt(getattr(item, "ingestion_status", None), 40),
        created_at=_s(getattr(item, "created_at", ""), 60),
        linked_ids={"document_id": getattr(item, "document_id", None)},
    )


def _from_drawing_page(page: Any, *, document: Any = None) -> UnifiedRecord:
    doc_project = getattr(document, "project_ref", None) if document is not None else None
    doc_file = getattr(document, "source_file_name", None) if document is not None else None
    doc_id = getattr(document, "document_id", None) if document is not None else getattr(page, "document_id", None)
    title = (
        getattr(page, "sheet_title", None)
        or getattr(page, "sheet_number", None)
        or getattr(page, "drawing_number", None)
        or f"第 {getattr(page, 'page_number', '')} 頁"
    )
    return UnifiedRecord(
        record_type="drawing_page",
        record_id=_s(getattr(page, "page_id", ""), 120),
        title=_s(title, 200),
        summary=_s(getattr(page, "extracted_text_excerpt", ""), 280),
        project_ref=_opt(doc_project, 120),
        source_file_name=_opt(doc_file, 240),
        sheet_number=_opt(getattr(page, "sheet_number", None) or getattr(page, "drawing_number", None), 80),
        page_type=_opt(getattr(page, "page_type", None), 60),
        discipline=_opt(getattr(page, "discipline", None), 40),
        created_at=_s(getattr(page, "created_at", ""), 60),
        linked_ids={"document_id": doc_id, "page_id": getattr(page, "page_id", None)},
    )


def _from_handoff(item: Any, *, document: Any = None) -> UnifiedRecord:
    doc_project = getattr(document, "project_ref", None) if document is not None else None
    doc_file = getattr(document, "source_file_name", None) if document is not None else None
    doc_id = getattr(document, "document_id", None) if document is not None else None
    return UnifiedRecord(
        record_type="cad_bim_handoff",
        record_id=_s(getattr(item, "item_id", ""), 120),
        title=_s(getattr(item, "title", "") or "CAD/BIM 交接事項", 200),
        summary=_s(getattr(item, "description", "") or getattr(item, "required_output", ""), 280),
        project_ref=_opt(doc_project, 120),
        source_file_name=_opt(doc_file, 240),
        sheet_number=_opt(getattr(item, "sheet_number", None), 80),
        discipline=_opt(getattr(item, "discipline", None), 40),
        status=_opt(getattr(item, "status", None), 40),
        priority=_opt(getattr(item, "priority", None), 40),
        responsible_team=_opt(getattr(item, "target_team", None), 40),
        linked_ids={"document_id": doc_id, "item_id": getattr(item, "item_id", None)},
    )


def _from_file_record(item: Any) -> UnifiedRecord:
    from .file_storage_models import FILE_TYPE_LABELS_ZH

    file_type = getattr(item, "file_type", "unknown")
    size = getattr(item, "size_bytes", None)
    summary_bits = [FILE_TYPE_LABELS_ZH.get(file_type, file_type)]
    if size:
        summary_bits.append(f"{int(size) // 1024} KB" if int(size) >= 1024 else f"{int(size)} bytes")
    return UnifiedRecord(
        record_type="file_record",
        record_id=_s(getattr(item, "file_id", ""), 120),
        title=_s(getattr(item, "original_file_name", None) or "未命名檔案", 240),
        summary=_s(" · ".join(summary_bits), 280),
        project_ref=_opt(getattr(item, "project_ref", None), 120),
        source_file_name=_opt(getattr(item, "original_file_name", None), 240),
        status=_opt(getattr(item, "storage_provider", None), 40),
        created_at=_s(getattr(item, "created_at", ""), 60),
        linked_ids={
            "linked_memory_id": getattr(item, "linked_memory_id", None),
            "linked_drawing_doc_id": getattr(item, "linked_drawing_doc_id", None),
            "linked_knowledge_source_id": getattr(item, "linked_knowledge_source_id", None),
        },
    )


# ── Index construction ─────────────────────────────────────────────────────
def build_unified_record_index(
    *,
    memories: list[Any] | None = None,
    followups: list[Any] | None = None,
    knowledge_sources: list[Any] | None = None,
    rag_chunks: list[Any] | None = None,
    drawing_documents: list[Any] | None = None,
    drawing_pages_by_doc: dict[str, list[Any]] | None = None,
    file_records: list[Any] | None = None,
    load_defaults: bool = True,
) -> list[UnifiedRecord]:
    """Build a unified record index from supplied collections or default stores.

    When a collection argument is ``None`` and ``load_defaults`` is true, it is
    loaded from its default JSONL store (best-effort). Pass ``load_defaults=False``
    to build purely from in-memory inputs (used by tests).
    """
    records: list[UnifiedRecord] = []

    memories = _resolve(memories, load_defaults, _load_memories)
    followups = _resolve(followups, load_defaults, _load_followups)
    knowledge_sources = _resolve(knowledge_sources, load_defaults, _load_knowledge_sources)
    rag_chunks = _resolve(rag_chunks, load_defaults, _load_rag_chunks)
    drawing_documents = _resolve(drawing_documents, load_defaults, _load_drawing_documents)
    file_records = _resolve(file_records, load_defaults, _load_file_records)
    if drawing_pages_by_doc is None and load_defaults:
        drawing_pages_by_doc = _load_pages_by_doc(drawing_documents)
    drawing_pages_by_doc = drawing_pages_by_doc or {}

    for item in memories or []:
        records.append(_from_memory(item))
    for item in followups or []:
        records.append(_from_followup(item))
    for item in knowledge_sources or []:
        records.append(_from_knowledge_source(item))
    for item in rag_chunks or []:
        records.append(_from_rag_chunk(item))
    doc_by_id: dict[str, Any] = {}
    for document in drawing_documents or []:
        records.append(_from_drawing_document(document))
        doc_by_id[getattr(document, "document_id", "")] = document
        for handoff in getattr(document, "handoff_items", []) or []:
            records.append(_from_handoff(handoff, document=document))
    for doc_id, pages in (drawing_pages_by_doc or {}).items():
        document = doc_by_id.get(doc_id)
        for page in pages or []:
            records.append(_from_drawing_page(page, document=document))
    for item in file_records or []:
        records.append(_from_file_record(item))

    return records


def search_unified_records(
    index: list[UnifiedRecord],
    *,
    keyword: str = "",
    project_ref: str = "",
    record_type: str = "",
    status: str = "",
    priority: str = "",
    risk_level: str = "",
    responsible_team: str = "",
    discipline: str = "",
    page_type: str = "",
    sheet_number: str = "",
    source_file_name: str = "",
    limit: int | None = 300,
) -> list[UnifiedRecord]:
    """Filter + keyword-rank a unified index. Deterministic and local."""
    results = list(index or [])
    results = filter_records_by_project(results, project_ref)
    if record_type:
        results = filter_records_by_field(results, "record_type", record_type)
    if status:
        results = filter_records_by_field(results, "status", status)
    if priority:
        results = filter_records_by_field(results, "priority", priority)
    if risk_level:
        results = filter_records_by_field(results, "risk_level", risk_level)
    if responsible_team:
        results = filter_records_by_field(results, "responsible_team", responsible_team)
    if discipline:
        results = filter_records_by_field(results, "discipline", discipline)
    if page_type:
        results = filter_records_by_field(results, "page_type", page_type)
    if source_file_name:
        needle = source_file_name.strip().lower()
        results = [r for r in results if needle in str(r.source_file_name or "").lower()]
    if sheet_number:
        needle = sheet_number.strip().lower()
        results = [r for r in results if needle in str(r.sheet_number or "").lower()]
    if keyword:
        results = filter_records_by_keyword(results, keyword)
    results.sort(key=lambda r: r.created_at or "", reverse=True)
    return results if limit is None else results[: max(0, int(limit))]


# Expose `_blob` for the keyword filter, which reads it via getattr.
UnifiedRecord._blob = property(lambda self: self.blob)  # type: ignore[attr-defined]


# ── Best-effort default store loaders ──────────────────────────────────────
def _resolve(value: list[Any] | None, load_defaults: bool, loader) -> list[Any]:
    if value is not None:
        return value
    if not load_defaults:
        return []
    try:
        return loader()
    except Exception:
        return []


def _load_memories() -> list[Any]:
    from .project_memory_store import read_all_memory

    return read_all_memory()


def _load_followups() -> list[Any]:
    from .followup_store import list_followups

    return list_followups(limit=None)


def _load_knowledge_sources() -> list[Any]:
    sources: list[Any] = []
    try:
        from .knowledge_pack_store import read_knowledge_index

        sources.extend(read_knowledge_index())
    except Exception:
        pass
    try:
        from .knowledge_ingestion import read_ingested_knowledge_sources

        sources.extend(read_ingested_knowledge_sources())
    except Exception:
        pass
    return sources


def _load_rag_chunks() -> list[Any]:
    chunks: list[Any] = []
    try:
        from .rag_indexer import read_rag_index

        chunks.extend(read_rag_index())
    except Exception:
        pass
    try:
        from .rag_persistence import read_ingested_chunks

        chunks.extend(read_ingested_chunks())
    except Exception:
        pass
    return chunks


def _load_drawing_documents() -> list[Any]:
    from .drawing_store import list_recent_drawing_documents

    return list_recent_drawing_documents(limit=200)


def _load_pages_by_doc(documents: list[Any] | None) -> dict[str, list[Any]]:
    pages_by_doc: dict[str, list[Any]] = {}
    try:
        from .drawing_store import read_pages_for_document

        for document in documents or []:
            doc_id = getattr(document, "document_id", "")
            if doc_id:
                pages_by_doc[doc_id] = read_pages_for_document(doc_id)
    except Exception:
        return {}
    return pages_by_doc


def _load_file_records() -> list[Any]:
    from .file_registry import list_file_records

    return list_file_records(limit=None)
