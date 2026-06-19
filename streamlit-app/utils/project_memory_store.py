"""Append-only UTF-8 JSONL project memory with latest-record reads."""

from __future__ import annotations

import json
import os
import re
import threading
import uuid
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .memory_models import (
    MEMORY_PRIORITIES,
    MEMORY_SOURCE_TYPES,
    MEMORY_STATUSES,
    ProjectMemoryRecord,
    ProjectMemorySummary,
)


DEFAULT_MEMORY_PATH = Path(__file__).resolve().parents[1] / "data" / "aicos_memory.jsonl"
_LOCK = threading.Lock()
_SECRET_KEY = re.compile(r"(?i)(api[_-]?key|secret|password|token|authorization)")
_SECRET_VALUE = re.compile(
    r"(?i)(sk-[a-z0-9_-]{8,}|bearer\s+[a-z0-9._-]+|"
    r"(?:api[_-]?key|secret|password|token)\s*[:=]\s*\S+)"
)
_CONSTRUCTION_TERMS = (
    "磨機", "火花", "熱工", "切割", "高空", "高處", "臨邊", "防墮",
    "滅火筒", "防火氈", "許可", "棚架", "護欄", "PPE", "漏水", "裂縫",
)
_MEMORY_INTENTS = ("最近", "上次", "記憶", "問題", "重複", "未完成", "跟進咗未", "跟進")


def append_memory(
    record: ProjectMemoryRecord | dict[str, Any],
    *,
    path: str | Path = DEFAULT_MEMORY_PATH,
) -> ProjectMemoryRecord:
    payload = record.to_dict() if isinstance(record, ProjectMemoryRecord) else dict(record)
    now = _now()
    normalized = ProjectMemoryRecord(
        memory_id=str(payload.get("memory_id") or f"pmem_{uuid.uuid4().hex}"),
        created_at=str(payload.get("created_at") or now),
        updated_at=str(payload.get("updated_at") or now),
        project_ref=_optional(payload.get("project_ref")),
        source_type=_choice(payload.get("source_type"), MEMORY_SOURCE_TYPES, "manual_note"),
        title=_clean_text(payload.get("title") or "未命名工程記憶", 180),
        summary=_clean_text(payload.get("summary"), 3000),
        raw_question=_optional_clean(payload.get("raw_question"), 1200),
        answer_summary=_optional_clean(payload.get("answer_summary"), 2500),
        analysis_type=_optional_clean(payload.get("analysis_type"), 120),
        risk_level=_optional_clean(payload.get("risk_level"), 40),
        confidence=_confidence(payload.get("confidence")),
        evidence_sources=_strings(payload.get("evidence_sources")),
        tags=_strings(payload.get("tags")),
        trade_tags=_strings(payload.get("trade_tags")),
        location_hint=_optional_clean(payload.get("location_hint"), 180),
        responsible_role=_optional_clean(payload.get("responsible_role"), 120),
        status=_choice(payload.get("status"), MEMORY_STATUSES, "open"),
        priority=_choice(payload.get("priority"), MEMORY_PRIORITIES, _priority(payload.get("risk_level"))),
        due_hint=_optional_clean(payload.get("due_hint"), 120),
        linked_record_ids=_strings(payload.get("linked_record_ids")),
        source_file_name=_optional_clean(payload.get("source_file_name"), 240),
        source_route=_optional_clean(payload.get("source_route"), 120),
        metadata=_sanitize(payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}),
    )
    _append(Path(path), normalized.to_dict())
    return normalized


def read_all_memory(*, path: str | Path = DEFAULT_MEMORY_PATH) -> list[ProjectMemoryRecord]:
    latest: dict[str, ProjectMemoryRecord] = {}
    file_path = Path(path)
    if not file_path.exists():
        return []
    try:
        for line in file_path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                payload = json.loads(line)
                record = ProjectMemoryRecord.from_dict(payload)
            except (json.JSONDecodeError, TypeError, ValueError, KeyError):
                continue
            latest[record.memory_id] = record
    except OSError:
        return []
    return sorted(latest.values(), key=lambda item: item.updated_at or item.created_at, reverse=True)


def search_memory(
    query: str,
    project_ref: str | None = None,
    tags: list[str] | None = None,
    status: str | None = None,
    limit: int = 10,
    *,
    path: str | Path = DEFAULT_MEMORY_PATH,
) -> list[ProjectMemoryRecord]:
    wanted_tags = {item.lower() for item in _strings(tags)}
    terms = _terms(query)
    ranked = []
    for record in read_all_memory(path=path):
        if project_ref and (record.project_ref or "").lower() != project_ref.lower():
            continue
        if status and record.status != status:
            continue
        record_tags = {item.lower() for item in [*record.tags, *record.trade_tags]}
        if wanted_tags and not wanted_tags.issubset(record_tags):
            continue
        text = json.dumps(record.to_dict(), ensure_ascii=False).lower()
        score = sum(5 if term in record.title.lower() else 1 for term in terms if term in text)
        if terms and not score:
            continue
        ranked.append((score, record.updated_at or record.created_at, record))
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    if not ranked and any(intent in str(query or "") for intent in _MEMORY_INTENTS):
        fallback = [
            item for item in read_all_memory(path=path)
            if not project_ref or (item.project_ref or "").lower() == project_ref.lower()
        ]
        if status:
            fallback = [item for item in fallback if item.status == status]
        return fallback[: max(0, int(limit))]
    return [record for _, _, record in ranked[: max(0, int(limit))]]


def summarize_project_memory(
    project_ref: str | None = None,
    *,
    path: str | Path = DEFAULT_MEMORY_PATH,
) -> ProjectMemorySummary:
    records = [
        item for item in read_all_memory(path=path)
        if not project_ref or (item.project_ref or "").lower() == project_ref.lower()
    ]
    unresolved = [item for item in records if item.status in {"open", "in_progress"}]
    high = [item for item in records if (item.risk_level or "").lower() in {"high", "critical", "高風險", "極高風險"} or item.priority in {"high", "urgent"}]
    counts = Counter(tag for item in records for tag in [*item.tags, *item.trade_tags] if tag)
    repeated = sorted(((tag, count) for tag, count in counts.items() if count > 1), key=lambda row: (-row[1], row[0]))[:8]
    actions = []
    if high:
        actions.append(f"覆核 {len(high)} 項高風險記憶及相關控制措施。")
    if unresolved:
        actions.append(f"跟進 {len(unresolved)} 項未完成事項並補充完成證據。")
    if repeated:
        actions.append("優先檢查重複出現的風險主題：" + "、".join(tag for tag, _ in repeated[:3]) + "。")
    return ProjectMemorySummary(
        project_ref=project_ref,
        total_records=len(records),
        open_count=len(unresolved),
        high_risk_count=len(high),
        repeated_tags=repeated,
        recent_records=records[:3],
        unresolved_items=unresolved[:8],
        suggested_next_actions=actions,
    )


def update_memory_status(
    memory_id: str,
    status: str,
    remarks: str | None = None,
    *,
    path: str | Path = DEFAULT_MEMORY_PATH,
) -> ProjectMemoryRecord:
    normalized_status = _choice(status, MEMORY_STATUSES, "")
    if not normalized_status:
        raise ValueError("Unsupported memory status")
    record = _find(memory_id, path)
    metadata = dict(record.metadata)
    if remarks:
        metadata.setdefault("status_history", []).append({"at": _now(), "status": normalized_status, "remarks": _clean_text(remarks, 500)})
    return append_memory(replace(record, status=normalized_status, updated_at=_now(), metadata=metadata), path=path)


def link_memory_records(
    source_id: str,
    target_id: str,
    *,
    path: str | Path = DEFAULT_MEMORY_PATH,
) -> tuple[ProjectMemoryRecord, ProjectMemoryRecord]:
    source = _find(source_id, path)
    target = _find(target_id, path)
    source_links = list(dict.fromkeys([*source.linked_record_ids, target.memory_id]))
    target_links = list(dict.fromkeys([*target.linked_record_ids, source.memory_id]))
    return (
        append_memory(replace(source, linked_record_ids=source_links, updated_at=_now()), path=path),
        append_memory(replace(target, linked_record_ids=target_links, updated_at=_now()), path=path),
    )


def _find(memory_id: str, path: str | Path) -> ProjectMemoryRecord:
    found = next((item for item in read_all_memory(path=path) if item.memory_id == memory_id), None)
    if not found:
        raise KeyError(f"Unknown memory_id: {memory_id}")
    return found


def _append(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    with _LOCK:
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(encoded + "\n")
            handle.flush()
            os.fsync(handle.fileno())


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if not _SECRET_KEY.search(str(key))}
    if isinstance(value, (list, tuple, set)):
        return [_sanitize(item) for item in value]
    text = str(value) if not isinstance(value, (str, int, float, bool, type(None))) else value
    if isinstance(text, str) and _SECRET_VALUE.search(text):
        return "[敏感資料已移除]"
    return text


def _clean_text(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if _SECRET_VALUE.search(text):
        return "[敏感資料已移除]"
    return text[:limit]


def _optional_clean(value: Any, limit: int) -> str | None:
    clean = _clean_text(value, limit)
    return clean or None


def _optional(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [value]
    return list(dict.fromkeys(_clean_text(item, 120) for item in (value or []) if _clean_text(item, 120)))


def _choice(value: Any, choices: set[str], default: str) -> str:
    text = str(value or "").strip().lower()
    return text if text in choices else default


def _confidence(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return None


def _priority(risk: Any) -> str:
    return "high" if str(risk or "").lower() in {"high", "critical", "高風險", "極高風險"} else "medium"


def _terms(value: str) -> list[str]:
    text = str(value or "").lower()
    tokens = [term for term in re.findall(r"[a-z0-9_./-]+|[\u3400-\u9fff]+", text) if len(term) >= 2]
    known = [term.lower() for term in _CONSTRUCTION_TERMS if term.lower() in text]
    return list(dict.fromkeys([*known, *tokens]))[:20]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
