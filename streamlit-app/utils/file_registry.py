"""Append-only UTF-8 JSONL registry for uploaded file metadata (Phase 6.1).

One runtime store lives under ``streamlit-app/data`` (git-ignored):

* ``file_registry.jsonl`` — :class:`StoredFileRecord` rows, latest-wins by
  ``file_id``.

Reads tolerate a missing file, blank/corrupt lines, old schemas and missing
fields. Writes are append-only with a process lock + fsync, mirroring the
existing project-memory / drawing stores. No file bytes are ever stored here —
only metadata.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .file_storage_models import StoredFileRecord
from .file_storage import new_file_id


_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_REGISTRY_PATH = _DATA_DIR / "file_registry.jsonl"
_LOCK = threading.Lock()


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


def _read_rows(path: Path) -> list[dict[str, Any]]:
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


def register_file(
    record: StoredFileRecord | dict[str, Any],
    *,
    path: str | Path = DEFAULT_REGISTRY_PATH,
) -> StoredFileRecord:
    """Append a file-metadata record, assigning id/timestamps when missing."""
    normalized = StoredFileRecord.from_dict(record)
    now = _now()
    if not normalized.file_id:
        normalized.file_id = new_file_id()
    if not normalized.created_at:
        normalized.created_at = now
    normalized.updated_at = now
    _append(Path(path), normalized.to_dict())
    return normalized


def list_file_records(
    *,
    project_ref: str | None = None,
    file_type: str | None = None,
    source_module: str | None = None,
    limit: int | None = 200,
    path: str | Path = DEFAULT_REGISTRY_PATH,
) -> list[StoredFileRecord]:
    """Return latest-wins records, newest first, with optional simple filters."""
    latest: dict[str, StoredFileRecord] = {}
    for payload in _read_rows(Path(path)):
        try:
            record = StoredFileRecord.from_dict(payload)
        except (TypeError, ValueError, KeyError):
            continue
        if record.file_id:
            latest[record.file_id] = record
    records = sorted(
        latest.values(),
        key=lambda item: item.updated_at or item.created_at,
        reverse=True,
    )
    if project_ref:
        records = [item for item in records if (item.project_ref or "").lower() == project_ref.lower()]
    if file_type:
        records = [item for item in records if item.file_type == file_type]
    if source_module:
        records = [item for item in records if item.source_module == source_module]
    return records if limit is None else records[: max(0, int(limit))]


def get_file_record(
    file_id: str,
    *,
    path: str | Path = DEFAULT_REGISTRY_PATH,
) -> StoredFileRecord | None:
    wanted = str(file_id or "").strip()
    if not wanted:
        return None
    return next((item for item in list_file_records(limit=None, path=path) if item.file_id == wanted), None)


def search_file_records(
    query: str,
    *,
    project_ref: str | None = None,
    file_type: str | None = None,
    limit: int = 50,
    path: str | Path = DEFAULT_REGISTRY_PATH,
) -> list[StoredFileRecord]:
    """Deterministic local keyword search over file metadata (no embeddings)."""
    records = list_file_records(project_ref=project_ref, file_type=file_type, limit=None, path=path)
    needle = " ".join(str(query or "").split()).lower()
    if not needle:
        return records[: max(0, int(limit))]
    terms = [term for term in needle.split() if term]
    ranked: list[tuple[int, str, StoredFileRecord]] = []
    for record in records:
        name = (record.original_file_name or "").lower()
        blob = " ".join([
            name,
            record.safe_file_name or "",
            record.project_ref or "",
            record.file_type,
            " ".join(record.tags),
        ]).lower()
        score = sum(4 for term in terms if term in name) + sum(1 for term in terms if term in blob)
        if score:
            ranked.append((score, record.updated_at or record.created_at, record))
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [record for _, _, record in ranked[: max(0, int(limit))]]


def update_file_links(
    file_id: str,
    *,
    linked_memory_id: str | None = None,
    linked_drawing_doc_id: str | None = None,
    linked_knowledge_source_id: str | None = None,
    drive_file_id: str | None = None,
    drive_web_url: str | None = None,
    path: str | Path = DEFAULT_REGISTRY_PATH,
) -> StoredFileRecord | None:
    """Re-persist a record with updated cross-links (latest-wins append)."""
    record = get_file_record(file_id, path=path)
    if record is None:
        return None
    if linked_memory_id is not None:
        record.linked_memory_id = linked_memory_id or None
    if linked_drawing_doc_id is not None:
        record.linked_drawing_doc_id = linked_drawing_doc_id or None
    if linked_knowledge_source_id is not None:
        record.linked_knowledge_source_id = linked_knowledge_source_id or None
    if drive_file_id is not None:
        record.drive_file_id = drive_file_id or None
        record.storage_provider = "google_drive_ready" if drive_file_id else record.storage_provider
    if drive_web_url is not None:
        record.drive_web_url = drive_web_url or None
    return register_file(record, path=path)
