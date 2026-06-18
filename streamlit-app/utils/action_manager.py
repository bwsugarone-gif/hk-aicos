# -*- coding: utf-8 -*-
"""
utils/action_manager.py
HK-AICOS Phase 3.1E — Project action item storage and helpers.
"""

import json
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path

# Import synonym-based keyword extractor for dedup (lazy to avoid circular imports)
def _extract_risk_groups(text: str) -> set:
    try:
        from utils.repeated_issue_detector import extract_risk_groups
        return extract_risk_groups(text)
    except Exception:
        return set()


_BASE_DIR = Path(__file__).parent.parent
_DATA_DIR = _BASE_DIR / "data"
_ACTION_FILE = _DATA_DIR / "action_items.json"

STATUSES = ["未開始", "跟進中", "已完成", "暫緩"]
PRIORITIES = ["高", "中", "低"]
OPEN_STATUSES = {"未開始", "跟進中", "暫緩"}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_action_file() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not _ACTION_FILE.exists():
        _ACTION_FILE.write_text("[]", encoding="utf-8")


def _read_json(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("action_items.json 必須是 list。")
    return data


def load_action_items() -> list:
    """Load action items. Auto-create an empty list when missing."""
    _ensure_action_file()
    return _read_json(_ACTION_FILE)


def save_action_items(items: list) -> None:
    _ensure_action_file()
    _ACTION_FILE.write_text(json.dumps(list(items or []), ensure_ascii=False, indent=2), encoding="utf-8")


def backup_action_items() -> Path:
    _ensure_action_file()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = _DATA_DIR / f"action_items_backup_{ts}.json"
    shutil.copy2(_ACTION_FILE, backup_path)
    return backup_path


def make_action_id() -> str:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"ACT-{ts}-{uuid.uuid4().hex[:4].upper()}"


def _normalise_risk(risk_level: str) -> str:
    risk = str(risk_level or "中風險")
    if "高" in risk:
        return "高風險"
    if "低" in risk:
        return "低風險"
    return "中風險"


def _priority_from_risk(risk_level: str) -> str:
    risk = _normalise_risk(risk_level)
    if risk == "高風險":
        return "高"
    if risk == "中風險":
        return "中"
    return "低"


def _first_text(value, fallback: str = "需跟進工程風險事項") -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return fallback
    return text[:240]


def _agent_from_session(session: dict) -> str:
    highest = str(session.get("highest_risk_agent", "") or "").strip()
    if highest:
        return highest
    agents = list(session.get("selected_agents", []) or [])
    if "pm" in agents:
        return "PM Agent"
    if "safety" in agents:
        return "Safety Agent"
    return str(agents[0]) if agents else "PM Agent"


def build_action_from_session(session: dict) -> dict:
    departments = (
        session.get("departments", [])
        or session.get("government_departments", [])
        or []
    )
    risk_level = _normalise_risk(
        session.get("calibrated_risk_level")
        or session.get("risk_level", "中風險")
    )
    department = str(departments[0]) if departments else "待確認"
    detail_source = (
        session.get("calibration_reason")
        or session.get("analysis_summary")
        or session.get("summary")
        or session.get("question")
        or ""
    )
    title_source = session.get("question") or detail_source
    return {
        "action_id": make_action_id(),
        "project_ref": str(session.get("project_ref", "未填寫") or "未填寫"),
        "session_id": str(session.get("session_id", "") or ""),
        "created_at": _now(),
        "risk_level": risk_level,
        "responsible_agent": _agent_from_session(session),
        "department": department,
        "action_title": _first_text(title_source, "跟進工程風險事項")[:80],
        "action_detail": _first_text(detail_source),
        "priority": _priority_from_risk(risk_level),
        "status": "未開始",
    }


def find_similar_action(
    project_ref: str,
    title_text: str,
    items: list,
) -> dict | None:
    """
    Return the first open action item for the same project_ref that shares
    at least one synonym risk group with title_text. Returns None if no match.
    """
    if not project_ref or not title_text:
        return None
    current_groups = _extract_risk_groups(title_text)
    if not current_groups:
        return None
    for item in items:
        if item.get("project_ref") != project_ref:
            continue
        if item.get("status") not in OPEN_STATUSES:
            continue
        existing_groups = _extract_risk_groups(
            (item.get("action_title") or "") + " " + (item.get("action_detail") or "")
        )
        if current_groups & existing_groups:
            return item
    return None


def auto_create_action_from_session(session: dict) -> dict:
    """
    Create one action for medium/high risk sessions.
    If a similar open action already exists for the same project_ref,
    update its repeat_count and last_seen instead of creating a duplicate.
    Low risk returns {}.
    """
    risk_level = _normalise_risk(
        session.get("calibrated_risk_level")
        or session.get("risk_level", "中風險")
    )
    if risk_level == "低風險":
        return {}

    action = build_action_from_session(session)
    items = load_action_items()

    # Dedup check: find existing similar open action for same project
    project_ref = str(session.get("project_ref", "") or "")
    title_text = action.get("action_title", "") + " " + action.get("action_detail", "")
    existing = find_similar_action(project_ref, title_text, items)

    if existing:
        # Update existing action instead of creating duplicate
        existing["repeat_count"] = int(existing.get("repeat_count") or 1) + 1
        existing["last_seen"] = _now()
        existing["repeated_follow_up"] = True
        # Escalate priority if risk is higher
        _priority_order = {"低": 0, "中": 1, "高": 2}
        if _priority_order.get(action.get("priority", "中"), 1) > _priority_order.get(existing.get("priority", "中"), 1):
            existing["priority"] = action["priority"]
            existing["risk_level"] = action["risk_level"]
        save_action_items(items)
        return existing

    # No duplicate found — create new action
    action["repeat_count"] = 1
    action["repeated_follow_up"] = False
    items.append(action)
    save_action_items(items)
    return action


def add_action_item(action: dict) -> dict:
    item = {
        "action_id": str(action.get("action_id") or make_action_id()),
        "project_ref": str(action.get("project_ref", "") or "未填寫"),
        "session_id": str(action.get("session_id", "") or ""),
        "created_at": str(action.get("created_at") or _now()),
        "risk_level": _normalise_risk(action.get("risk_level", "中風險")),
        "responsible_agent": str(action.get("responsible_agent", "") or "PM Agent"),
        "department": str(action.get("department", "") or "待確認"),
        "action_title": str(action.get("action_title", "") or "跟進工程風險事項"),
        "action_detail": str(action.get("action_detail", "") or ""),
        "priority": str(action.get("priority", "") or "中"),
        "status": str(action.get("status", "") or "未開始"),
    }
    if item["priority"] not in PRIORITIES:
        item["priority"] = "中"
    if item["status"] not in STATUSES:
        item["status"] = "未開始"
    items = load_action_items()
    items.append(item)
    save_action_items(items)
    return item


def update_action_status(action_id: str, status: str) -> bool:
    if status not in STATUSES:
        return False
    items = load_action_items()
    updated = False
    for item in items:
        if item.get("action_id") == action_id:
            item["status"] = status
            updated = True
            break
    if updated:
        save_action_items(items)
    return updated


def delete_action_item(action_id: str) -> Path:
    """Backup first, then delete the requested action item."""
    backup_path = backup_action_items()
    items = load_action_items()
    items = [item for item in items if item.get("action_id") != action_id]
    save_action_items(items)
    return backup_path


def get_project_action_summary() -> dict:
    try:
        items = load_action_items()
    except Exception:
        return {}
    summary = {}
    for item in items:
        project_ref = str(item.get("project_ref", "未填寫") or "未填寫")
        project_summary = summary.setdefault(project_ref, {"open": 0, "high": 0})
        if item.get("status") in OPEN_STATUSES:
            project_summary["open"] += 1
            if item.get("priority") == "高":
                project_summary["high"] += 1
    return summary

