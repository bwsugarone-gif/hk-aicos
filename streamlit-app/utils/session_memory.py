# -*- coding: utf-8 -*-
"""
utils/session_memory.py
HK-AICOS Phase 2.5E — Lightweight Project Session Memory

Storage: JSON file (streamlit-app/data/session_memory.json)
No database, no login, no cloud.

Session record schema:
{
    "session_id":   "SES-20260516-143022-abc1",
    "project_ref":  "BW-001",
    "upload_time":  "2026-05-16T14:30:22",
    "file_names":   ["plan.pdf", "photo.jpg"],
    "file_types":   ["pdf", "image"],
    "selected_agents": ["pm", "safety", "engineering"],
    "risk_level":   "高風險",
    "departments":  ["勞工處", "屋宇署"],
    "analysis_summary": "首 300 字摘要...",
    "analysis_type": "安全風險分析",
    "question":     "呢個工地有無安全問題？"
}

Rules:
- Keep only the latest 5 sessions per project_ref.
- Total cap: 50 sessions across all projects (oldest pruned first).
- If file is missing or corrupt, return empty list — never crash.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

_DATA_DIR  = Path(__file__).parent.parent / "data"
_MEM_FILE  = _DATA_DIR / "session_memory.json"
_MAX_PER_PROJECT = 5
_MAX_TOTAL       = 50
_SUMMARY_CHARS   = 300


def _ensure_dir():
    _DATA_DIR.mkdir(exist_ok=True)


def _load_all() -> list:
    """Load all sessions from JSON. Returns [] on any error."""
    _ensure_dir()
    if not _MEM_FILE.exists():
        return []
    try:
        raw = _MEM_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def _save_all(sessions: list):
    """Persist sessions list to JSON."""
    _ensure_dir()
    _MEM_FILE.write_text(
        json.dumps(sessions, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def make_session_id() -> str:
    """Generate a unique session ID."""
    ts  = datetime.now().strftime("%Y%m%d-%H%M%S")
    uid = uuid.uuid4().hex[:4].upper()
    return f"SES-{ts}-{uid}"


def save_session(
    project_ref: str,
    file_names: list,
    file_types: list,
    selected_agents: list,
    risk_level: str,
    departments: list,
    analysis_result: str,
    analysis_type: str,
    question: str,
    session_id: str = "",
) -> str:
    """
    Save a new session record.
    Returns the session_id used.
    Enforces per-project cap (5) and total cap (50).
    """
    if not session_id:
        session_id = make_session_id()

    # Truncate analysis to summary
    summary = str(analysis_result or "")[:_SUMMARY_CHARS]
    if len(str(analysis_result or "")) > _SUMMARY_CHARS:
        summary += "…"

    record = {
        "session_id":       session_id,
        "project_ref":      str(project_ref or "").strip() or "未填寫",
        "upload_time":      datetime.now().isoformat(timespec="seconds"),
        "file_names":       list(file_names or []),
        "file_types":       list(file_types or []),
        "selected_agents":  list(selected_agents or []),
        "risk_level":       str(risk_level or "中風險"),
        "departments":      list(departments or []),
        "analysis_summary": summary,
        "analysis_type":    str(analysis_type or ""),
        "question":         str(question or "")[:200],
    }

    sessions = _load_all()
    sessions.append(record)

    # Enforce per-project cap: keep latest _MAX_PER_PROJECT per project_ref
    proj = record["project_ref"]
    proj_sessions = [s for s in sessions if s.get("project_ref") == proj]
    if len(proj_sessions) > _MAX_PER_PROJECT:
        # Remove oldest for this project
        oldest = proj_sessions[0]
        sessions = [s for s in sessions if s.get("session_id") != oldest.get("session_id")]

    # Enforce total cap
    if len(sessions) > _MAX_TOTAL:
        sessions = sessions[-_MAX_TOTAL:]

    _save_all(sessions)
    return session_id


def get_all_sessions() -> list:
    """Return all sessions, newest first."""
    sessions = _load_all()
    return list(reversed(sessions))


def get_sessions_by_project(project_ref: str) -> list:
    """Return sessions for a specific project_ref, newest first."""
    if not project_ref or not project_ref.strip():
        return []
    sessions = _load_all()
    proj = project_ref.strip()
    filtered = [s for s in sessions if s.get("project_ref", "").strip() == proj]
    return list(reversed(filtered))


def get_prior_context(project_ref: str) -> str:
    """
    Return a formatted string of prior session summaries for the same project_ref.
    Used to inject into the AI prompt for project continuity.
    Returns "" if no prior sessions exist.
    """
    if not project_ref or not project_ref.strip():
        return ""

    sessions = get_sessions_by_project(project_ref)
    if not sessions:
        return ""

    lines = [f"以下為同一工程項目（{project_ref.strip()}）之前的分析摘要：\n"]
    for i, s in enumerate(sessions[:_MAX_PER_PROJECT], 1):
        ts   = s.get("upload_time", "")[:16].replace("T", " ")
        risk = s.get("risk_level", "")
        atype = s.get("analysis_type", "")
        q    = s.get("question", "")[:80]
        summ = s.get("analysis_summary", "")
        depts = "、".join(s.get("departments", []))
        lines.append(
            f"[第 {i} 次分析 — {ts}]\n"
            f"分析類型：{atype}　風險：{risk}　涉及部門：{depts}\n"
            f"問題：{q}\n"
            f"摘要：{summ}\n"
        )

    return "\n".join(lines)


def clear_all_sessions():
    """Delete all session records (for testing/reset)."""
    if _MEM_FILE.exists():
        _MEM_FILE.unlink()
