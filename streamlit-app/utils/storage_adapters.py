"""Storage adapter contracts for AICOS memory and knowledge metadata.

The local implementation is deliberately small and dependency-free.  A future
Google Drive adapter can store file bytes in Drive while preserving the same
record/source interface for AICOS, CRM, SOP, and RAG projects.
"""

from __future__ import annotations

import json
import os
import re
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


APP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MEMORY_PATH = APP_ROOT / "data" / "aicos_memory.jsonl"
DEFAULT_SOURCE_PATH = APP_ROOT / "data" / "aicos_sources.jsonl"
_write_lock = threading.Lock()


class StorageAdapter(ABC):
    """Persistence boundary shared by AICOS memory and knowledge services."""

    @abstractmethod
    def save_record(self, record: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def list_records(self, **filters: Any) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def search_records(self, query: str, **filters: Any) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def save_file_metadata(self, source: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def list_sources(self, **filters: Any) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_source(self, source_id: str) -> dict[str, Any] | None:
        raise NotImplementedError


class LocalJsonStorageAdapter(StorageAdapter):
    """Append-only JSONL storage with latest-value reads by stable ID."""

    def __init__(
        self,
        memory_path: str | Path = DEFAULT_MEMORY_PATH,
        source_path: str | Path = DEFAULT_SOURCE_PATH,
    ) -> None:
        self.memory_path = Path(memory_path)
        self.source_path = Path(source_path)

    def save_record(self, record: dict[str, Any]) -> dict[str, Any]:
        payload = _json_safe(record)
        if not str(payload.get("memory_id") or "").strip():
            raise ValueError("memory_id is required")
        self._append(self.memory_path, payload)
        return payload

    def list_records(self, **filters: Any) -> list[dict[str, Any]]:
        limit = filters.pop("limit", 100)
        records = self._read_latest(self.memory_path, "memory_id")
        records = _apply_filters(records, filters)
        records.sort(key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""), reverse=True)
        return records if limit is None else records[: max(0, int(limit))]

    def search_records(self, query: str, **filters: Any) -> list[dict[str, Any]]:
        limit = int(filters.pop("limit", 5))
        records = self.list_records(limit=None, **filters)
        return _rank_matches(records, query, limit)

    def save_file_metadata(self, source: dict[str, Any]) -> dict[str, Any]:
        payload = _json_safe(source)
        if not str(payload.get("source_id") or "").strip():
            raise ValueError("source_id is required")
        self._append(self.source_path, payload)
        return payload

    def list_sources(self, **filters: Any) -> list[dict[str, Any]]:
        limit = filters.pop("limit", 100)
        sources = self._read_latest(self.source_path, "source_id")
        sources = _apply_filters(sources, filters)
        sources.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return sources if limit is None else sources[: max(0, int(limit))]

    def search_sources(self, query: str, **filters: Any) -> list[dict[str, Any]]:
        limit = int(filters.pop("limit", 5))
        sources = self.list_sources(limit=None, **filters)
        return _rank_matches(sources, query, limit)

    def get_source(self, source_id: str) -> dict[str, Any] | None:
        wanted = str(source_id or "").strip()
        return next((item for item in self.list_sources(limit=None) if item.get("source_id") == wanted), None)

    @staticmethod
    def _append(path: Path, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        path.parent.mkdir(parents=True, exist_ok=True)
        with _write_lock:
            with path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(encoded + "\n")
                handle.flush()
                os.fsync(handle.fileno())

    @staticmethod
    def _read_latest(path: Path, id_field: str) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        latest: dict[str, dict[str, Any]] = {}
        try:
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    try:
                        item = json.loads(line)
                    except (json.JSONDecodeError, TypeError):
                        continue
                    if isinstance(item, dict) and str(item.get(id_field) or "").strip():
                        latest[str(item[id_field])] = item
        except OSError:
            return []
        return list(latest.values())


class GoogleDriveStorageAdapter(StorageAdapter):
    """Future adapter boundary; this phase intentionally performs no API calls."""

    configured = False

    def __init__(self, *_: Any, **__: Any) -> None:
        self.integration_status = "placeholder_only"

    @staticmethod
    def _unavailable() -> None:
        raise NotImplementedError("Google Drive storage is not enabled in Phase 5.7I")

    def save_record(self, record: dict[str, Any]) -> dict[str, Any]:
        self._unavailable()

    def list_records(self, **filters: Any) -> list[dict[str, Any]]:
        self._unavailable()

    def search_records(self, query: str, **filters: Any) -> list[dict[str, Any]]:
        self._unavailable()

    def save_file_metadata(self, source: dict[str, Any]) -> dict[str, Any]:
        self._unavailable()

    def list_sources(self, **filters: Any) -> list[dict[str, Any]]:
        self._unavailable()

    def get_source(self, source_id: str) -> dict[str, Any] | None:
        self._unavailable()


def _apply_filters(items: list[dict[str, Any]], filters: dict[str, Any]) -> list[dict[str, Any]]:
    active = {key: value for key, value in filters.items() if value not in (None, "")}
    return [item for item in items if all(item.get(key) == value for key, value in active.items())]


def _terms(value: str) -> list[str]:
    return list(
        dict.fromkeys(
            term.lower()
            for term in re.findall(r"[a-zA-Z0-9_./-]+|[\u3400-\u9fff]+", str(value or ""))
            if len(term) >= 2
        )
    )


def _rank_matches(items: list[dict[str, Any]], query: str, limit: int) -> list[dict[str, Any]]:
    terms = _terms(query)
    if not terms:
        return items[: max(0, limit)]
    ranked: list[tuple[int, str, dict[str, Any]]] = []
    for item in items:
        title = str(item.get("title") or "").lower()
        searchable = json.dumps(item, ensure_ascii=False, default=str).lower()
        score = sum(4 for term in terms if term in title) + sum(1 for term in terms if term in searchable)
        if score:
            ranked.append((score, str(item.get("created_at") or ""), item))
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [item for _, _, item in ranked[: max(0, limit)]]


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "to_dict"):
        return _json_safe(value.to_dict())
    return str(value)
