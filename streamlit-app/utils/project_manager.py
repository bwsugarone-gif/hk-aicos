# -*- coding: utf-8 -*-
"""
utils/project_manager.py
HK-AICOS Phase 3.0A — Local project memory layer.

Storage: streamlit-app/projects/{PROJECT_REF}/
No database. Runtime project data is intentionally gitignored.
"""

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


_BASE_DIR = Path(__file__).parent.parent
_PROJECTS_DIR = _BASE_DIR / "projects"
_SUMMARY_CHARS = 300


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _safe_ref(project_ref: str) -> str:
    raw = str(project_ref or "").strip()
    if not raw:
        return ""
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", raw)
    safe = safe.strip(".-_")
    return safe[:80] or "PROJECT"


def _read_json(path: Path, default):
    try:
        if not path.exists():
            return default
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if data is not None else default
    except Exception:
        return default


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _project_dir(project_ref: str) -> Path:
    safe = _safe_ref(project_ref)
    if not safe:
        raise ValueError("project_ref is required")
    return _PROJECTS_DIR / safe


def create_project(project_ref: str) -> dict:
    """Create project folder structure if missing and return metadata."""
    safe = _safe_ref(project_ref)
    if not safe:
        return {}

    project_dir = _PROJECTS_DIR / safe
    for child in ["sessions", "uploads", "reports", "risks", "agent_memory"]:
        (project_dir / child).mkdir(parents=True, exist_ok=True)

    project_file = project_dir / "project.json"
    meta = _read_json(project_file, {})
    if not meta:
        meta = {
            "project_ref": str(project_ref or "").strip(),
            "project_ref_safe": safe,
            "created_at": _now(),
            "updated_at": _now(),
        }
    else:
        meta["project_ref"] = meta.get("project_ref") or str(project_ref or "").strip()
        meta["project_ref_safe"] = safe
        meta["updated_at"] = _now()
    _write_json(project_file, meta)

    pm_memory = project_dir / "agent_memory" / "pm_memory.json"
    if not pm_memory.exists():
        _write_json(pm_memory, {"summaries": [], "updated_at": _now()})

    timeline = project_dir / "risks" / "timeline.json"
    if not timeline.exists():
        _write_json(timeline, [])

    return meta


def list_projects() -> list:
    """Return project metadata records sorted by latest update."""
    if not _PROJECTS_DIR.exists():
        return []
    projects = []
    for path in _PROJECTS_DIR.iterdir():
        if not path.is_dir():
            continue
        meta = _read_json(path / "project.json", {})
        if meta:
            projects.append(meta)
    return sorted(projects, key=lambda p: p.get("updated_at", ""), reverse=True)


def load_project(project_ref: str) -> dict:
    """Load project metadata, sessions, risks, and PM memory."""
    safe = _safe_ref(project_ref)
    if not safe:
        return {"project": {}, "sessions": [], "risks": [], "pm_memory": {}, "repeated_incidents": []}

    project_dir = _PROJECTS_DIR / safe
    sessions_dir = project_dir / "sessions"
    sessions = []
    if sessions_dir.exists():
        for path in sessions_dir.glob("*.json"):
            record = _read_json(path, {})
            if record:
                sessions.append(record)
    sessions = sorted(sessions, key=lambda s: s.get("time", ""), reverse=True)

    risks = _read_json(project_dir / "risks" / "timeline.json", [])
    if not isinstance(risks, list):
        risks = []
    risks = sorted(risks, key=lambda r: r.get("date", ""), reverse=True)

    counter = Counter(
        (s.get("analysis_type", ""), s.get("risk_level", ""))
        for s in sessions
        if s.get("analysis_type") and s.get("risk_level")
    )
    repeated = [
        {"analysis_type": atype, "risk_level": risk, "count": count}
        for (atype, risk), count in counter.items()
        if count > 1
    ]

    return {
        "project": _read_json(project_dir / "project.json", {}),
        "sessions": sessions,
        "risks": risks,
        "pm_memory": _read_json(project_dir / "agent_memory" / "pm_memory.json", {}),
        "repeated_incidents": sorted(repeated, key=lambda r: r["count"], reverse=True),
    }


def get_project_report_path(project_ref: str, session_id: str) -> Path:
    """Return the per-project PDF path for a session."""
    create_project(project_ref)
    safe_session = re.sub(r"[^A-Za-z0-9._-]+", "-", str(session_id or "session")).strip(".-_")
    return _project_dir(project_ref) / "reports" / f"HK-AICOS-{safe_session}.pdf"


def save_session(
    project_ref: str,
    session_id: str,
    selected_agents: list,
    analysis_type: str,
    analysis_result: str,
    risk_level: str,
    government_departments: list,
    report_path: str,
    question: str = "",
    file_names: list = None,
    file_types: list = None,
    time: str = "",
) -> dict:
    """Save one project session JSON and update PM memory summaries."""
    if not str(project_ref or "").strip():
        return {}

    create_project(project_ref)
    summary = str(analysis_result or "")[:_SUMMARY_CHARS]
    if len(str(analysis_result or "")) > _SUMMARY_CHARS:
        summary += "..."

    record = {
        "session_id": str(session_id or "").strip(),
        "project_ref": str(project_ref or "").strip(),
        "time": time or _now(),
        "selected_agents": list(selected_agents or []),
        "analysis_type": str(analysis_type or ""),
        "summary": summary,
        "risk_level": str(risk_level or "中風險"),
        "government_departments": list(government_departments or []),
        "report_path": str(report_path or ""),
        "question": str(question or "")[:200],
        "file_names": list(file_names or []),
        "file_types": list(file_types or []),
    }

    project_dir = _project_dir(project_ref)
    _write_json(project_dir / "sessions" / f"{record['session_id']}.json", record)

    pm_path = project_dir / "agent_memory" / "pm_memory.json"
    pm_memory = _read_json(pm_path, {"summaries": []})
    summaries = pm_memory.get("summaries", [])
    summaries.append({
        "session_id": record["session_id"],
        "time": record["time"],
        "risk_level": record["risk_level"],
        "analysis_type": record["analysis_type"],
        "summary": record["summary"],
    })
    pm_memory["summaries"] = summaries[-10:]
    pm_memory["updated_at"] = _now()
    _write_json(pm_path, pm_memory)

    meta_path = project_dir / "project.json"
    meta = _read_json(meta_path, {})
    meta["updated_at"] = _now()
    _write_json(meta_path, meta)
    return record


def append_risk_event(
    project_ref: str,
    session_id: str,
    risk: str,
    risk_level: str,
    status: str = "open",
    date: str = "",
) -> dict:
    """Append one risk timeline event."""
    if not str(project_ref or "").strip():
        return {}

    create_project(project_ref)
    event = {
        "date": date or _now(),
        "session_id": str(session_id or ""),
        "risk": str(risk or ""),
        "risk_level": str(risk_level or "中風險"),
        "status": str(status or "open"),
    }
    timeline_path = _project_dir(project_ref) / "risks" / "timeline.json"
    timeline = _read_json(timeline_path, [])
    if not isinstance(timeline, list):
        timeline = []
    timeline.append(event)
    _write_json(timeline_path, timeline)
    return event


def build_pm_memory_context(project_ref: str) -> str:
    """Return a compact PM Agent project memory block for prompt injection."""
    if not str(project_ref or "").strip():
        return ""

    data = load_project(project_ref)
    sessions = data.get("sessions", [])
    risks = data.get("risks", [])
    repeated = data.get("repeated_incidents", [])
    if not sessions and not risks and not repeated:
        return ""

    lines = [f"【PM Agent Project Memory — {project_ref.strip()}】"]

    previous = sessions[:5]
    if previous:
        lines.append("Previous project summaries:")
        for s in previous:
            ts = (s.get("time", "") or "")[:16].replace("T", " ")
            lines.append(
                f"- {ts} | {s.get('analysis_type', '')} | {s.get('risk_level', '')}: "
                f"{s.get('summary', '')}"
            )

    unresolved = [r for r in risks if r.get("status") != "resolved"][:5]
    if unresolved:
        lines.append("Unresolved risks:")
        for r in unresolved:
            ts = (r.get("date", "") or "")[:10]
            lines.append(f"- {ts} | {r.get('risk_level', '')} | {r.get('risk', '')}")

    if repeated:
        lines.append("Repeated incidents:")
        for item in repeated[:5]:
            lines.append(
                f"- {item.get('analysis_type', '')} / {item.get('risk_level', '')}: "
                f"{item.get('count', 0)} times"
            )

    return "\n".join(lines)

