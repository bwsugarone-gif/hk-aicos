"""Pure, dependency-light helpers for the Phase 6.1 file storage layer.

Nothing here writes the registry (see :mod:`utils.file_registry`); these are
small building blocks for deriving safe file names, mime types, checksums and a
sensible ``file_type`` from an upload. They never raise on bad input and never
expose secrets.

A Google Drive "ready" compatibility hook is provided so a future adapter can
attach ``drive_file_id`` / ``drive_web_url`` without changing call sites.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from pathlib import Path
from typing import Any


# Extension → coarse file_type, scoped by the calling module's intent.
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp"}
_DOC_EXTS = {".txt", ".md", ".rst", ".doc", ".docx", ".rtf", ".odt"}
_SHEET_EXTS = {".xls", ".xlsx", ".csv", ".tsv"}

_MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".webp": "image/webp",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".rst": "text/x-rst",
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._㐀-鿿-]+")


def new_file_id() -> str:
    return f"file_{uuid.uuid4().hex}"


def guess_mime_type(file_name: str | None) -> str | None:
    if not file_name:
        return None
    return _MIME_BY_EXT.get(Path(str(file_name)).suffix.lower())


def safe_file_name(file_name: str | None, *, fallback: str = "upload") -> str:
    """A filesystem/URL-safe rendering of the original name (extension kept)."""
    name = Path(str(file_name or "")).name
    if not name:
        return fallback
    stem = Path(name).stem or fallback
    suffix = Path(name).suffix.lower()
    cleaned = _SAFE_NAME.sub("_", stem).strip("._") or fallback
    return f"{cleaned[:120]}{suffix}"


def guess_file_type(file_name: str | None, *, source_module: str = "unknown") -> str:
    """Best-effort ``file_type`` from the extension and the calling module.

    The module hint disambiguates a PDF that is a drawing from one that is a
    knowledge source, and an image that is a site photo from a drawing image.
    """
    ext = Path(str(file_name or "")).suffix.lower()
    module = str(source_module or "").lower()
    if ext == ".pdf":
        if module == "drawing_analysis":
            return "drawing_pdf"
        if module == "report_generation":
            return "report"
        return "knowledge_pdf"
    if ext in _IMAGE_EXTS:
        if module == "drawing_analysis":
            return "drawing_image"
        return "site_photo"
    if ext in _DOC_EXTS:
        return "knowledge_doc"
    if ext in _SHEET_EXTS:
        return "knowledge_doc"
    return "unknown"


def compute_checksum(path: str | Path | None) -> str | None:
    """SHA-256 of a file on disk, or ``None`` if unreadable/missing."""
    if not path:
        return None
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return None
    digest = hashlib.sha256()
    try:
        with file_path.open("rb") as handle:
            for block in iter(lambda: handle.read(65536), b""):
                digest.update(block)
    except OSError:
        return None
    return digest.hexdigest()


def checksum_bytes(data: bytes | None) -> str | None:
    if data is None:
        return None
    try:
        return hashlib.sha256(bytes(data)).hexdigest()
    except (TypeError, ValueError):
        return None


def file_size_bytes(path: str | Path | None) -> int | None:
    if not path:
        return None
    try:
        stat = Path(path).stat()
    except OSError:
        return None
    return int(stat.st_size)


def build_file_metadata(
    *,
    original_file_name: str,
    source_module: str,
    project_ref: str | None = None,
    local_runtime_path: str | Path | None = None,
    size_bytes: int | None = None,
    checksum: str | None = None,
    file_type: str | None = None,
    tags: list[str] | None = None,
    linked_memory_id: str | None = None,
    linked_drawing_doc_id: str | None = None,
    linked_knowledge_source_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble a ``StoredFileRecord``-shaped dict from an upload.

    Size and checksum are derived from ``local_runtime_path`` when present and
    not supplied explicitly. Returns a plain dict so the registry layer owns the
    id / timestamps.
    """
    path_str = str(local_runtime_path) if local_runtime_path else None
    if size_bytes is None and path_str:
        size_bytes = file_size_bytes(path_str)
    if checksum is None and path_str:
        checksum = compute_checksum(path_str)
    return {
        "original_file_name": original_file_name,
        "safe_file_name": safe_file_name(original_file_name),
        "project_ref": project_ref,
        "file_type": file_type or guess_file_type(original_file_name, source_module=source_module),
        "mime_type": guess_mime_type(original_file_name),
        "size_bytes": size_bytes,
        "checksum": checksum,
        "source_module": source_module,
        "storage_provider": "local_runtime",
        "local_runtime_path": path_str,
        "tags": list(tags or []),
        "linked_memory_id": linked_memory_id,
        "linked_drawing_doc_id": linked_drawing_doc_id,
        "linked_knowledge_source_id": linked_knowledge_source_id,
        "metadata": dict(metadata or {}),
    }


def attach_drive_reference(
    payload: dict[str, Any],
    *,
    drive_file_id: str | None,
    drive_web_url: str | None = None,
) -> dict[str, Any]:
    """Google-Drive-ready compatibility hook (no live OAuth in this phase).

    Marks a record as ``google_drive_ready`` and records the Drive identifiers so
    a future adapter can promote it without changing the metadata shape.
    """
    updated = dict(payload or {})
    if drive_file_id:
        updated["drive_file_id"] = str(drive_file_id)
        updated["drive_web_url"] = drive_web_url or updated.get("drive_web_url")
        updated["storage_provider"] = "google_drive_ready"
    return updated
