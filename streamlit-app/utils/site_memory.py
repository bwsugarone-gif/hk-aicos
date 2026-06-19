"""Construction-specific AICOS memory items and retrieval helpers."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from typing import Any

from .analysis_models import KnowledgeSnippet
from .storage_adapters import LocalJsonStorageAdapter, StorageAdapter


MEMORY_TYPES = (
    "project_memory",
    "issue_memory",
    "source_memory",
    "followup_memory",
    "qa_memory",
)


@dataclass
class MemoryItem:
    memory_id: str
    created_at: str
    memory_type: str
    title: str
    summary: str
    updated_at: str = ""
    project_id: str = ""
    tags: list[str] = field(default_factory=list)
    related_record_ids: list[str] = field(default_factory=list)
    related_source_ids: list[str] = field(default_factory=list)
    risk_level: str = ""
    status: str = ""
    raw_payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Any) -> "MemoryItem":
        """Normalize legacy ProjectMemory, dict, and dataclass records safely."""
        if isinstance(value, cls):
            return value
        if is_dataclass(value):
            value = asdict(value)
        elif not isinstance(value, dict):
            value = getattr(value, "__dict__", {})
        payload = dict(value or {})
        created_at = str(payload.get("created_at") or payload.get("updated_at") or "")
        source_type = str(payload.get("memory_type") or payload.get("source_type") or "project_memory")
        if source_type not in MEMORY_TYPES:
            source_type = "project_memory"
        return cls(
            memory_id=str(payload.get("memory_id") or payload.get("record_id") or f"legacy_{uuid.uuid4().hex}"),
            created_at=created_at,
            updated_at=str(payload.get("updated_at") or created_at),
            memory_type=source_type,
            project_id=str(payload.get("project_id") or payload.get("project_ref") or ""),
            title=str(payload.get("title") or "未命名記憶"),
            summary=str(payload.get("summary") or payload.get("answer_summary") or ""),
            tags=_string_list(payload.get("tags")),
            related_record_ids=_string_list(payload.get("related_record_ids") or payload.get("linked_record_ids")),
            related_source_ids=_string_list(payload.get("related_source_ids") or payload.get("evidence_sources")),
            risk_level=str(payload.get("risk_level") or ""),
            status=str(payload.get("status") or "open"),
            raw_payload=dict(payload.get("raw_payload") or payload.get("metadata") or {}),
        )


def save_memory_item(
    item: MemoryItem | dict[str, Any] | None = None,
    *,
    adapter: StorageAdapter | None = None,
    **values: Any,
) -> MemoryItem:
    """Create or update one structured construction memory item."""
    payload = item.to_dict() if isinstance(item, MemoryItem) else dict(item or {})
    payload.update(values)
    now = datetime.now(timezone.utc).isoformat()
    memory_type = str(payload.get("memory_type") or "project_memory")
    if memory_type not in MEMORY_TYPES:
        raise ValueError(f"Unsupported memory_type: {memory_type}")
    normalized = MemoryItem(
        memory_id=str(payload.get("memory_id") or f"mem_{uuid.uuid4().hex}"),
        created_at=str(payload.get("created_at") or now),
        updated_at=str(payload.get("updated_at") or ""),
        memory_type=memory_type,
        project_id=str(payload.get("project_id") or ""),
        title=str(payload.get("title") or "未命名記憶").strip(),
        summary=str(payload.get("summary") or "").strip()[:2000],
        tags=_string_list(payload.get("tags")),
        related_record_ids=_string_list(payload.get("related_record_ids")),
        related_source_ids=_string_list(payload.get("related_source_ids")),
        risk_level=str(payload.get("risk_level") or ""),
        status=str(payload.get("status") or ""),
        raw_payload=dict(payload.get("raw_payload") or {}),
    )
    (adapter or LocalJsonStorageAdapter()).save_record(normalized.to_dict())
    return normalized


def list_memory_items(
    *,
    memory_type: str = "",
    project_id: str | None = None,
    limit: int | None = 100,
    adapter: StorageAdapter | None = None,
) -> list[MemoryItem]:
    rows = (adapter or LocalJsonStorageAdapter()).list_records(limit=None)
    items = []
    for row in rows:
        try:
            item = MemoryItem.from_dict(row)
        except (TypeError, ValueError, AttributeError):
            continue
        if memory_type and item.memory_type != memory_type:
            continue
        if project_id and item.project_id != project_id:
            continue
        items.append(item)
    return items if limit is None else items[: max(0, int(limit))]


def search_memory(
    query: str,
    project_id: str | None = None,
    limit: int = 5,
    *,
    adapter: StorageAdapter | None = None,
) -> list[MemoryItem]:
    rows = (adapter or LocalJsonStorageAdapter()).search_records(query, limit=max(limit * 3, limit))
    items = []
    for row in rows:
        try:
            item = MemoryItem.from_dict(row)
        except (TypeError, ValueError, AttributeError):
            continue
        if not project_id or item.project_id == project_id:
            items.append(item)
    return items[: max(0, int(limit))]


def build_memory_context(
    question: str,
    project_id: str | None = None,
    limit: int = 5,
    *,
    adapter: StorageAdapter | None = None,
) -> list[KnowledgeSnippet]:
    """Return memory matches in the same context shape used by Ask AICOS."""
    snippets = []
    for rank, item in enumerate(search_memory(question, project_id, limit, adapter=adapter)):
        snippets.append(
            KnowledgeSnippet(
                title=item.title,
                path=f"AICOS Memory / {item.memory_id}",
                snippet=item.summary,
                score=max(1.0, float(limit - rank)),
                source_type=item.memory_type,
                source_id=f"memory:{item.memory_id}",
                trust_level="uploaded_record",
                provider="aicos_memory",
            )
        )
    return snippets


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [value]
    return list(dict.fromkeys(str(item).strip() for item in (value or []) if str(item).strip()))
