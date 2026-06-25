"""Typed metadata contract for uploaded files, drawings, PDFs and knowledge sources.

Phase 6.1 storage foundation. A :class:`StoredFileRecord` only ever holds
*metadata* about an uploaded artefact — never the file bytes. The actual bytes
live in the git-ignored runtime ``uploads`` directory (``local_runtime``) or, in
a future phase, in Google Drive (``google_drive_ready``).

``from_dict`` is deliberately defensive so missing fields, old schemas and
corrupt records load without raising. ``local_runtime_path`` is stored for
internal lookups but must never be surfaced in the normal UI.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any


# ── Controlled vocabularies ────────────────────────────────────────────────
FILE_TYPES = {
    "site_photo",
    "drawing_pdf",
    "drawing_image",
    "knowledge_pdf",
    "knowledge_doc",
    "report",
    "unknown",
}

SOURCE_MODULES = {
    "upload_analysis",
    "drawing_analysis",
    "knowledge_ingestion",
    "report_generation",
    "unknown",
}

STORAGE_PROVIDERS = {
    "local_runtime",
    "google_drive_ready",
    "google_drive",
    "external_reference",
}

# Traditional-Chinese display labels (UI only; never used as storage keys).
FILE_TYPE_LABELS_ZH = {
    "site_photo": "地盤相片",
    "drawing_pdf": "圖紙 PDF",
    "drawing_image": "圖紙圖片",
    "knowledge_pdf": "知識 PDF",
    "knowledge_doc": "知識文件",
    "report": "報告",
    "unknown": "未分類檔案",
}

STORAGE_PROVIDER_LABELS_ZH = {
    "local_runtime": "本機暫存",
    "google_drive_ready": "Drive-ready",
    "google_drive": "Google Drive",
    "external_reference": "外部連結",
}


def _clean(value: Any, limit: int = 600) -> str:
    return " ".join(str(value or "").split())[:limit]


def _optional(value: Any, limit: int = 600) -> str | None:
    text = _clean(value, limit)
    return text or None


def _strings(value: Any, limit: int = 200) -> list[str]:
    if isinstance(value, str):
        value = [value]
    seen: list[str] = []
    for item in value or []:
        cleaned = _clean(item, limit)
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return seen


def _choice(value: Any, choices: set[str], default: str) -> str:
    text = str(value or "").strip().lower()
    return text if text in choices else default


def _int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_payload(value: Any) -> dict:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return dict(value)
    return dict(getattr(value, "__dict__", {}) or {})


@dataclass
class StoredFileRecord:
    """Metadata about one uploaded artefact (no binary content)."""

    file_id: str
    created_at: str
    updated_at: str
    original_file_name: str
    project_ref: str | None = None
    safe_file_name: str | None = None
    file_type: str = "unknown"
    mime_type: str | None = None
    size_bytes: int | None = None
    checksum: str | None = None
    source_module: str = "unknown"
    storage_provider: str = "local_runtime"
    local_runtime_path: str | None = None  # internal only — never shown in normal UI
    drive_file_id: str | None = None
    drive_web_url: str | None = None
    linked_memory_id: str | None = None
    linked_drawing_doc_id: str | None = None
    linked_knowledge_source_id: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_safe_public_dict(self) -> dict[str, Any]:
        """A view safe for normal UI: no local filesystem path, no raw metadata."""
        data = self.to_dict()
        data.pop("local_runtime_path", None)
        data.pop("metadata", None)
        return data

    @classmethod
    def from_dict(cls, value: Any) -> "StoredFileRecord":
        if isinstance(value, cls):
            return value
        payload = _as_payload(value)
        created = _clean(payload.get("created_at") or payload.get("updated_at"), 60)
        metadata = payload.get("metadata")
        return cls(
            file_id=_clean(payload.get("file_id") or payload.get("id"), 120) or "",
            created_at=created,
            updated_at=_clean(payload.get("updated_at") or created, 60),
            original_file_name=_clean(
                payload.get("original_file_name") or payload.get("file_name") or "未命名檔案", 300
            ),
            project_ref=_optional(payload.get("project_ref") or payload.get("project_id"), 120),
            safe_file_name=_optional(payload.get("safe_file_name"), 300),
            file_type=_choice(payload.get("file_type"), FILE_TYPES, "unknown"),
            mime_type=_optional(payload.get("mime_type"), 120),
            size_bytes=_int_or_none(payload.get("size_bytes")),
            checksum=_optional(payload.get("checksum"), 128),
            source_module=_choice(payload.get("source_module"), SOURCE_MODULES, "unknown"),
            storage_provider=_choice(payload.get("storage_provider"), STORAGE_PROVIDERS, "local_runtime"),
            local_runtime_path=_optional(payload.get("local_runtime_path") or payload.get("local_path"), 600),
            drive_file_id=_optional(payload.get("drive_file_id"), 200),
            drive_web_url=_optional(payload.get("drive_web_url") or payload.get("drive_url"), 600),
            linked_memory_id=_optional(payload.get("linked_memory_id"), 120),
            linked_drawing_doc_id=_optional(payload.get("linked_drawing_doc_id") or payload.get("document_id"), 120),
            linked_knowledge_source_id=_optional(payload.get("linked_knowledge_source_id") or payload.get("source_id"), 120),
            tags=_strings(payload.get("tags")),
            metadata=dict(metadata) if isinstance(metadata, dict) else {},
        )
