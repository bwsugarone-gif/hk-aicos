"""AICOS knowledge/source registry with cloud-ready metadata fields."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .analysis_models import KnowledgeSnippet
from .storage_adapters import LocalJsonStorageAdapter, StorageAdapter


STORAGE_PROVIDERS = ("local_json", "local_file", "google_drive", "future_supabase")


@dataclass
class KnowledgeSourceItem:
    source_id: str
    created_at: str
    source_type: str
    title: str
    storage_provider: str
    local_path: str = ""
    google_drive_file_id: str = ""
    google_drive_url: str = ""
    tags: list[str] = field(default_factory=list)
    project_id: str = ""
    summary: str = ""
    extracted_text_path: str = ""
    indexed_status: str = "pending"
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "KnowledgeSourceItem":
        fields = cls.__dataclass_fields__
        return cls(**{key: value[key] for key in fields if key in value})


def save_source_item(
    item: KnowledgeSourceItem | dict[str, Any] | None = None,
    *,
    adapter: StorageAdapter | None = None,
    **values: Any,
) -> KnowledgeSourceItem:
    payload = item.to_dict() if isinstance(item, KnowledgeSourceItem) else dict(item or {})
    payload.update(values)
    provider = str(payload.get("storage_provider") or "local_json")
    if provider not in STORAGE_PROVIDERS:
        raise ValueError(f"Unsupported storage_provider: {provider}")
    normalized = KnowledgeSourceItem(
        source_id=str(payload.get("source_id") or f"src_{uuid.uuid4().hex}"),
        created_at=str(payload.get("created_at") or datetime.now(timezone.utc).isoformat()),
        source_type=str(payload.get("source_type") or "document"),
        title=str(payload.get("title") or "未命名知識來源").strip(),
        storage_provider=provider,
        local_path=str(payload.get("local_path") or ""),
        google_drive_file_id=str(payload.get("google_drive_file_id") or ""),
        google_drive_url=str(payload.get("google_drive_url") or ""),
        tags=_string_list(payload.get("tags")),
        project_id=str(payload.get("project_id") or ""),
        summary=str(payload.get("summary") or "").strip()[:4000],
        extracted_text_path=str(payload.get("extracted_text_path") or ""),
        indexed_status=str(payload.get("indexed_status") or "pending"),
        raw_metadata=dict(payload.get("raw_metadata") or {}),
    )
    (adapter or LocalJsonStorageAdapter()).save_file_metadata(normalized.to_dict())
    return normalized


def list_source_items(
    *,
    source_type: str = "",
    project_id: str | None = None,
    storage_provider: str = "",
    limit: int | None = 100,
    adapter: StorageAdapter | None = None,
) -> list[KnowledgeSourceItem]:
    filters: dict[str, Any] = {"limit": limit}
    if source_type:
        filters["source_type"] = source_type
    if project_id:
        filters["project_id"] = project_id
    if storage_provider:
        filters["storage_provider"] = storage_provider
    rows = (adapter or LocalJsonStorageAdapter()).list_sources(**filters)
    return [KnowledgeSourceItem.from_dict(row) for row in rows]


def search_sources(
    query: str,
    project_id: str | None = None,
    limit: int = 5,
    *,
    adapter: StorageAdapter | None = None,
) -> list[KnowledgeSourceItem]:
    storage = adapter or LocalJsonStorageAdapter()
    filters: dict[str, Any] = {"limit": limit}
    if project_id:
        filters["project_id"] = project_id
    search_method = getattr(storage, "search_sources", None)
    if callable(search_method):
        rows = search_method(query, **filters)
    else:
        rows = _search_rows(storage.list_sources(limit=None, **({"project_id": project_id} if project_id else {})), query, limit)
    return [KnowledgeSourceItem.from_dict(row) for row in rows]


def build_knowledge_context(
    question: str,
    project_id: str | None = None,
    limit: int = 5,
    *,
    adapter: StorageAdapter | None = None,
) -> list[KnowledgeSnippet]:
    snippets = []
    for rank, item in enumerate(search_sources(question, project_id, limit, adapter=adapter)):
        path = item.google_drive_url or item.local_path or f"AICOS Knowledge / {item.source_id}"
        snippets.append(
            KnowledgeSnippet(
                title=item.title,
                path=path,
                snippet=item.summary,
                score=max(1.0, float(limit - rank)),
                source_type=item.source_type,
                source_id=f"knowledge:{item.source_id}",
                trust_level="local_internal",
                provider=f"knowledge_{item.storage_provider}",
            )
        )
    return snippets


def _search_rows(rows: list[dict[str, Any]], query: str, limit: int) -> list[dict[str, Any]]:
    terms = [term.lower() for term in str(query or "").split() if len(term) >= 2]
    if not terms:
        return rows[:limit]
    ranked = []
    for row in rows:
        text = json.dumps(row, ensure_ascii=False).lower()
        score = sum(text.count(term) for term in terms)
        if score:
            ranked.append((score, row))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [row for _, row in ranked[:limit]]


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [value]
    return list(dict.fromkeys(str(item).strip() for item in (value or []) if str(item).strip()))
