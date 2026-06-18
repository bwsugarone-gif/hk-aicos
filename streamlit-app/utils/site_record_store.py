"""Append-only local JSONL store for AICOS site records."""

from __future__ import annotations

import json
import os
import re
import threading
import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .analysis_models import ImageAnalysisResult, QAResponse, SiteRecord


DEFAULT_RECORD_PATH = Path(__file__).resolve().parents[1] / "data" / "site_records.jsonl"
VALID_RECORD_TYPES = {"image_analysis", "qa_session", "followup_action"}
STATUS_OPTIONS = ("open", "in_progress", "pending_contractor", "pending_client", "resolved", "closed")
PRIORITY_OPTIONS = ("low", "medium", "high", "urgent")
_write_lock = threading.Lock()


def normalize_status(value: str) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {"progress": "in_progress", "done": "resolved", "complete": "closed"}
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in STATUS_OPTIONS else "open"


def normalize_priority(value: str) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {"normal": "medium", "critical": "urgent"}
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in PRIORITY_OPTIONS else "low"


class SiteRecordStore:
    def __init__(self, path: str | Path = DEFAULT_RECORD_PATH):
        self.path = Path(path)

    def create_record(
        self,
        *,
        record_type: str,
        title: str,
        content_summary: str,
        source: str,
        category: str = "general",
        risk_level: str = "",
        priority: str = "",
        status: str = "open",
        responsible_role: str = "",
        due_hint: str = "",
        remarks: str = "",
        raw_payload: dict[str, Any] | None = None,
    ) -> SiteRecord:
        if record_type not in VALID_RECORD_TYPES:
            raise ValueError(f"Unsupported record type: {record_type}")
        return SiteRecord(
            record_id=f"rec_{uuid.uuid4().hex}",
            created_at=datetime.now(timezone.utc).isoformat(),
            record_type=record_type,
            title=str(title).strip() or "Untitled record",
            content_summary=str(content_summary).strip()[:1000],
            source=str(source).strip() or "local",
            category=str(category or "general"),
            risk_level=str(risk_level or ""),
            priority=normalize_priority(priority),
            status=normalize_status(status),
            responsible_role=str(responsible_role or "").strip(),
            due_hint=str(due_hint or "").strip(),
            remarks=str(remarks or "").strip(),
            updated_at="",
            history=[],
            raw_payload=_json_safe(raw_payload or {}),
        )

    def save(self, record: SiteRecord) -> SiteRecord:
        self._append_payload(record.to_dict())
        return record

    def list_records(self, *, limit: int | None = 100) -> list[SiteRecord]:
        if not self.path.exists():
            return []
        records_by_id: dict[str, SiteRecord] = {}
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    try:
                        item = json.loads(line)
                        if not isinstance(item, dict):
                            continue
                        if item.get("event_type") == "record_update":
                            record = records_by_id.get(str(item.get("record_id") or ""))
                            if record:
                                _apply_update_event(record, item)
                            continue
                        if item.get("record_id"):
                            record = SiteRecord.from_dict(item)
                            record.status = normalize_status(record.status)
                            record.priority = normalize_priority(record.priority)
                            records_by_id[record.record_id] = record
                    except (json.JSONDecodeError, TypeError, ValueError):
                        continue
        except OSError:
            return []
        records = list(records_by_id.values())
        records.sort(key=lambda item: item.created_at or "", reverse=True)
        return records if limit is None else records[: max(0, limit)]

    def get_record(self, record_id: str) -> SiteRecord | None:
        return next((item for item in self.list_records(limit=None) if item.record_id == record_id), None)

    def update_record(
        self,
        record_id: str,
        *,
        status: str | None = None,
        priority: str | None = None,
        responsible_role: str | None = None,
        due_hint: str | None = None,
        remarks: str | None = None,
        change_summary: str = "",
    ) -> SiteRecord:
        current = self.get_record(record_id)
        if current is None:
            raise KeyError(f"Record not found: {record_id}")

        requested = {
            "status": normalize_status(status) if status is not None else current.status,
            "priority": normalize_priority(priority) if priority is not None else current.priority,
            "responsible_role": str(responsible_role).strip() if responsible_role is not None else current.responsible_role,
            "due_hint": str(due_hint).strip() if due_hint is not None else current.due_hint,
            "remarks": str(remarks).strip() if remarks is not None else current.remarks,
        }
        changes = {
            field: value
            for field, value in requested.items()
            if value != getattr(current, field)
        }
        if not changes:
            return current

        updated_at = datetime.now(timezone.utc).isoformat()
        event = {
            "event_type": "record_update",
            "record_id": record_id,
            "updated_at": updated_at,
            "changes": changes,
            "change_summary": str(change_summary or "").strip() or "更新跟進狀態",
            "previous_status": current.status,
            "new_status": changes.get("status", current.status),
            "previous_priority": current.priority,
            "new_priority": changes.get("priority", current.priority),
        }
        self._append_payload(event)
        _apply_update_event(current, event)
        return current

    def _append_payload(self, payload: dict[str, Any]) -> None:
        encoded = json.dumps(_json_safe(payload), ensure_ascii=False, separators=(",", ":"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _write_lock:
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(encoded + "\n")
                handle.flush()
                os.fsync(handle.fileno())

    def search_records(
        self,
        *,
        keyword: str = "",
        record_type: str = "",
        category: str = "",
        status: str = "",
        priority: str = "",
        limit: int = 100,
    ) -> list[SiteRecord]:
        keyword = keyword.strip().lower()
        keyword_terms = list(
            dict.fromkeys(
                term
                for term in re.findall(r"[a-z0-9_./-]+|[\u3400-\u9fff]+", keyword)
                if len(term) >= 2
            )
        )
        matches = []
        for record in self.list_records(limit=None):
            if record_type and record.record_type != record_type:
                continue
            if category and record.category != category:
                continue
            if status and record.status != status:
                continue
            if priority and record.priority != priority:
                continue
            searchable = " ".join(
                [
                    record.title,
                    record.content_summary,
                    record.responsible_role,
                    record.due_hint,
                    record.remarks,
                    json.dumps(record.raw_payload, ensure_ascii=False),
                ]
            ).lower()
            if keyword and keyword not in searchable and not any(term in searchable for term in keyword_terms):
                continue
            matches.append(record)
            if len(matches) >= limit:
                break
        return matches


def save_image_analysis_record(
    analysis: ImageAnalysisResult | dict[str, Any],
    *,
    filename: str = "site image",
    store: SiteRecordStore | None = None,
) -> SiteRecord:
    payload = analysis.to_dict() if isinstance(analysis, ImageAnalysisResult) else _json_safe(analysis)
    category = str(payload.get("detected_category") or "unknown")
    observations = payload.get("key_observations") or []
    risks = payload.get("risks") or []
    followups = payload.get("recommended_followups") or []
    priority = _highest_priority(followups)
    primary_followup = next((item for item in followups if isinstance(item, dict)), {})
    risk_level = "high" if risks or category == "safety_issue" else "low"
    record_store = store or SiteRecordStore()
    record = record_store.create_record(
        record_type="image_analysis",
        title=f"圖片分析：{filename}",
        content_summary="；".join(observations[:3]) or "圖片分析已完成，等待人工覆核。",
        source=filename,
        category=category,
        risk_level=risk_level,
        priority=priority,
        responsible_role=str(primary_followup.get("responsible_role") or ""),
        due_hint=str(primary_followup.get("due_hint") or ""),
        raw_payload=payload,
    )
    return record_store.save(record)


def save_qa_session_record(
    question: str,
    response: QAResponse | dict[str, Any],
    *,
    question_type: str = "general",
    store: SiteRecordStore | None = None,
) -> SiteRecord:
    payload = response.to_dict() if isinstance(response, QAResponse) else _json_safe(response)
    answer = str(payload.get("answer") or "")
    record_store = store or SiteRecordStore()
    record = record_store.create_record(
        record_type="qa_session",
        title=f"問 AICOS：{question.strip()[:80]}",
        content_summary=answer[:500] or "AICOS 問答記錄",
        source="Ask AICOS",
        category=question_type,
        risk_level=str(payload.get("risk_level") or "unknown"),
        status="open",
        raw_payload={"question": question, "response": payload},
    )
    return record_store.save(record)


def _highest_priority(followups: list[Any]) -> str:
    ranking = {"urgent": 4, "high": 3, "medium": 2, "low": 1}
    priorities = [str(item.get("priority", "")) for item in followups if isinstance(item, dict)]
    return max(priorities, key=lambda item: ranking.get(item, 0), default="low")


def _apply_update_event(record: SiteRecord, event: dict[str, Any]) -> None:
    changes = event.get("changes") if isinstance(event.get("changes"), dict) else {}
    for field in ("status", "priority", "responsible_role", "due_hint", "remarks"):
        if field in changes:
            value = changes[field]
            if field == "status":
                value = normalize_status(value)
            elif field == "priority":
                value = normalize_priority(value)
            setattr(record, field, str(value or ""))
    record.updated_at = str(event.get("updated_at") or record.updated_at or "")
    history_item = {
        key: event.get(key)
        for key in (
            "updated_at", "change_summary", "previous_status", "new_status",
            "previous_priority", "new_priority", "changes",
        )
    }
    if history_item not in record.history:
        record.history.append(history_item)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
