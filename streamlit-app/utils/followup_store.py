"""Local JSONL follow-up tracker and risk-trace conversion helpers."""

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

from .analysis_models import KnowledgeSnippet
from .evidence_models import RiskEvidenceTrace
from .followup_models import FOLLOWUP_PRIORITIES, FOLLOWUP_STATUSES, FollowUpItem


DEFAULT_FOLLOWUP_PATH = Path(__file__).resolve().parents[1] / "data" / "followups.jsonl"
_LOCK = threading.Lock()
_FOLLOWUP_TERMS = ("磨機", "火花", "熱工", "切割", "高空", "臨邊", "防墮", "滅火筒", "防火氈")


def create_followup_from_analysis(
    *,
    title: str,
    description: str,
    project_ref: str | None = None,
    source_memory_id: str | None = None,
    source_record_id: str | None = None,
    risk_level: str | None = None,
    priority: str | None = None,
    responsible_role: str | None = None,
    due_hint: str | None = None,
    evidence_required: list[str] | None = None,
    suggested_actions: list[str] | None = None,
    path: str | Path = DEFAULT_FOLLOWUP_PATH,
) -> FollowUpItem:
    now = _now()
    item = FollowUpItem(
        followup_id=f"follow_{uuid.uuid4().hex}",
        created_at=now,
        updated_at=now,
        project_ref=_optional(project_ref),
        title=_clean(title, 180) or "需跟進事項",
        description=_clean(description, 2500),
        source_memory_id=_optional(source_memory_id),
        source_record_id=_optional(source_record_id),
        risk_level=_optional(risk_level),
        priority=_priority(priority, risk_level),
        status="open",
        responsible_role=_optional(responsible_role),
        due_hint=_optional(due_hint),
        evidence_required=_strings(evidence_required),
        suggested_actions=_strings(suggested_actions),
        history=[{"at": now, "status": "open", "remarks": "建立跟進事項"}],
    )
    _append(Path(path), item.to_dict())
    return item


def list_followups(
    project_ref: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    *,
    path: str | Path = DEFAULT_FOLLOWUP_PATH,
    limit: int | None = 100,
) -> list[FollowUpItem]:
    latest: dict[str, FollowUpItem] = {}
    file_path = Path(path)
    if file_path.exists():
        try:
            for line in file_path.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    item = FollowUpItem.from_dict(json.loads(line))
                except (json.JSONDecodeError, TypeError, ValueError, KeyError):
                    continue
                if item.followup_id:
                    latest[item.followup_id] = item
        except OSError:
            return []
    items = sorted(latest.values(), key=lambda item: item.updated_at or item.created_at, reverse=True)
    if project_ref:
        items = [item for item in items if (item.project_ref or "").lower() == project_ref.lower()]
    if status:
        items = [item for item in items if item.status == status]
    if priority:
        items = [item for item in items if item.priority == priority]
    return items if limit is None else items[: max(0, int(limit))]


def update_followup_status(
    followup_id: str,
    status: str,
    remarks: str | None = None,
    *,
    path: str | Path = DEFAULT_FOLLOWUP_PATH,
) -> FollowUpItem:
    normalized = str(status or "").strip().lower()
    if normalized not in FOLLOWUP_STATUSES:
        raise ValueError("Unsupported follow-up status")
    current = next((item for item in list_followups(path=path, limit=None) if item.followup_id == followup_id), None)
    if not current:
        raise KeyError(f"Unknown followup_id: {followup_id}")
    history = [*current.history, {"at": _now(), "status": normalized, "remarks": _clean(remarks, 500)}]
    updated = replace(
        current,
        status=normalized,
        updated_at=_now(),
        closeout_notes=_optional(remarks) if normalized == "resolved" else current.closeout_notes,
        history=history,
    )
    _append(Path(path), updated.to_dict())
    return updated


def summarize_followups(project_ref: str | None = None, *, path: str | Path = DEFAULT_FOLLOWUP_PATH) -> dict:
    items = list_followups(project_ref=project_ref, path=path, limit=None)
    status_counts = Counter(item.status for item in items)
    priority_counts = Counter(item.priority for item in items)
    open_items = [item for item in items if item.status in {"open", "in_progress", "waiting"}]
    return {
        "total": len(items),
        "open_count": len(open_items),
        "status_counts": dict(status_counts),
        "priority_counts": dict(priority_counts),
        "recent_open": open_items[:5],
    }


def build_followup_context(
    query: str,
    project_ref: str | None = None,
    limit: int = 5,
    *,
    path: str | Path = DEFAULT_FOLLOWUP_PATH,
) -> list[KnowledgeSnippet]:
    query_text = str(query or "").lower()
    terms = [term for term in re.findall(r"[a-z0-9_./-]+|[\u3400-\u9fff]+", query_text) if len(term) >= 2]
    terms = list(dict.fromkeys([*(term.lower() for term in _FOLLOWUP_TERMS if term.lower() in query_text), *terms]))
    ranked = []
    for item in list_followups(project_ref=project_ref, path=path, limit=None):
        if item.status not in {"open", "in_progress", "waiting"}:
            continue
        searchable = json.dumps(item.to_dict(), ensure_ascii=False).lower()
        score = sum(3 if term in item.title.lower() else 1 for term in terms if term in searchable)
        if terms and not score:
            continue
        ranked.append((score, item.updated_at, item))
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    if not ranked and any(term in query_text for term in ("跟進", "未完成", "上次")):
        fallback = [
            item for item in list_followups(project_ref=project_ref, path=path, limit=None)
            if item.status in {"open", "in_progress", "waiting"}
        ]
        ranked = [(0, item.updated_at, item) for item in fallback]
    return [
        KnowledgeSnippet(
            title=item.title,
            path=f"AICOS Follow-up / {item.followup_id}",
            snippet=item.description,
            score=max(1.0, float(limit - rank)),
            source_type="follow_up",
            source_id=f"follow-up:{item.followup_id}",
            trust_level="uploaded_record",
            provider="followup_store",
        )
        for rank, (_, _, item) in enumerate(ranked[: max(0, int(limit))])
    ]


def generate_followups_from_risk_trace(
    risk_trace: RiskEvidenceTrace | dict[str, Any],
    project_ref: str | None = None,
    *,
    source_memory_id: str | None = None,
    path: str | Path = DEFAULT_FOLLOWUP_PATH,
    persist: bool = True,
) -> list[FollowUpItem]:
    trace = risk_trace if isinstance(risk_trace, RiskEvidenceTrace) else RiskEvidenceTrace(**{
        key: value for key, value in dict(risk_trace).items() if key in RiskEvidenceTrace.__dataclass_fields__
    })
    text = " ".join([*trace.triggered_by, *trace.rules_matched, trace.final_reason]).lower()
    insufficient = any(term in text for term in ("未有足夠", "暫不判斷", "人工覆核")) and not trace.rules_matched
    hot_work = any(term in text for term in ("磨機", "切割", "火花", "熱工", "hot work"))
    if insufficient:
        spec = {
            "title": "需補充資料 / 人工覆核",
            "description": "目前證據不足以判斷具體危害；請補充工序、位置、工具、附近物料及防護措施。",
            "priority": "medium",
            "evidence": ["現場相片", "工序及位置描述", "現有防護措施"],
            "actions": ["由管工／安全主任現場覆核後更新記錄。"],
        }
    elif hot_work:
        spec = {
            "title": "確認磨機切割熱工防火措施",
            "description": "證據顯示可能涉及磨機切割及火花；需確認熱工許可、滅火筒、防火氈及工後巡查。",
            "priority": "high",
            "evidence": ["熱工許可", "滅火筒位置相片", "防火氈或遮蓋措施相片", "工後巡查記錄"],
            "actions": ["開工前由管工／安全主任確認防火措施。", "完工後保存巡查及整改證據。"],
        }
    else:
        spec = {
            "title": "覆核風險判斷及未確認事項",
            "description": trace.final_reason or "請按風險證據及現場狀況覆核。",
            "priority": "high" if str(trace.risk_level).lower() in {"high", "critical", "高風險", "極高風險"} else "medium",
            "evidence": trace.missing_confirmations or ["現場覆核記錄"],
            "actions": ["指定負責人及完成時限，並上載整改證據。"],
        }
    kwargs = dict(
        title=spec["title"], description=spec["description"], project_ref=project_ref,
        source_memory_id=source_memory_id, risk_level=trace.risk_level,
        priority=spec["priority"], responsible_role="管工／安全主任",
        evidence_required=spec["evidence"], suggested_actions=spec["actions"], path=path,
    )
    if persist:
        return [create_followup_from_analysis(**kwargs)]
    now = _now()
    return [FollowUpItem(
        followup_id="preview", created_at=now, updated_at=now, project_ref=project_ref,
        title=spec["title"], description=spec["description"], source_memory_id=source_memory_id,
        risk_level=trace.risk_level, priority=spec["priority"], responsible_role="管工／安全主任",
        evidence_required=spec["evidence"], suggested_actions=spec["actions"], status="open",
    )]


def _append(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    with _LOCK:
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(encoded + "\n")
            handle.flush()
            os.fsync(handle.fileno())


def _priority(value: str | None, risk: str | None) -> str:
    text = str(value or "").lower()
    if text in FOLLOWUP_PRIORITIES:
        return text
    return "high" if str(risk or "").lower() in {"high", "critical", "高風險", "極高風險"} else "medium"


def _strings(value) -> list[str]:
    if isinstance(value, str):
        value = [value]
    return list(dict.fromkeys(_clean(item, 200) for item in (value or []) if _clean(item, 200)))


def _clean(value, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def _optional(value) -> str | None:
    text = _clean(value, 500)
    return text or None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
