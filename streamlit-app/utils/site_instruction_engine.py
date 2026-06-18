# -*- coding: utf-8 -*-
"""
utils/site_instruction_engine.py
HK-AICOS Phase 3.3E — Site Instruction & Follow-up Workflow Layer

Generates structured site instructions from analysis results:
- Site Instruction (正式現場指令)
- Corrective Action Notice (整改通知)
- Safety Follow-up (安全跟進)
- Subcontractor Follow-up (分判跟進)
- PM Internal Note (PM 內部備忘)

PM Agent has final control over all instruction generation.
Hallucination control: no evidence → no formal instruction.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── Storage ───────────────────────────────────────────────────────────────────
_BASE_DIR = Path(__file__).parent.parent
_DATA_DIR = _BASE_DIR / "data"
_INSTR_FILE = _DATA_DIR / "site_instructions.json"

# ── Instruction types ─────────────────────────────────────────────────────────
INSTRUCTION_TYPES = {
    "SiteInstruction":       "Site Instruction（正式現場指令）",
    "CorrectiveAction":      "Corrective Action Notice（整改通知）",
    "SafetyFollowUp":        "Safety Follow-up（安全跟進）",
    "SubcontractorFollowup": "Subcontractor Follow-up（分判跟進）",
    "PMInternalNote":        "PM Internal Note（PM 內部備忘）",
    "InsufficientData":      "需補充資料（資料不足）",
}

PRIORITY_MAP = {"高": "高", "中": "中", "低": "低"}


# ── Helpers ───────────────────────────────────────────────────────────────────
def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _make_id() -> str:
    return "SI-" + uuid.uuid4().hex[:8].upper()


def _ensure_file() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not _INSTR_FILE.exists():
        _INSTR_FILE.write_text("[]", encoding="utf-8")


def _load() -> list:
    _ensure_file()
    try:
        data = json.loads(_INSTR_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save(items: list) -> None:
    _ensure_file()
    _INSTR_FILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _fingerprint(project_ref: str, instr_type: str, related_risk: str) -> str:
    """Simple dedup key."""
    return f"{project_ref}|{instr_type}|{related_risk[:40]}"


def _is_duplicate(project_ref: str, instr_type: str, related_risk: str) -> bool:
    fp = _fingerprint(project_ref, instr_type, related_risk)
    existing = _load()
    for item in existing:
        existing_fp = _fingerprint(
            item.get("project_ref", ""),
            item.get("instruction_type", ""),
            item.get("related_risk", ""),
        )
        if existing_fp == fp:
            return True
    return False


def _build_instruction(
    project_ref: str,
    session_id: str,
    instr_type: str,
    issued_to: str,
    related_agent: str,
    related_risk: str,
    title: str,
    detail: str,
    required_action: str,
    priority: str,
    evidence_source: list,
    repeated: bool = False,
) -> dict:
    return {
        "instruction_id": _make_id(),
        "project_ref": project_ref or "未填寫",
        "session_id": session_id or "",
        "instruction_type": instr_type,
        "instruction_type_label": INSTRUCTION_TYPES.get(instr_type, instr_type),
        "issued_to": issued_to or "待確認",
        "related_agent": related_agent or "PM Agent",
        "related_risk": related_risk or "",
        "instruction_title": title[:100],
        "instruction_detail": detail,
        "required_action": required_action,
        "priority": priority if priority in PRIORITY_MAP else "中",
        "due_status": "待跟進",
        "evidence_source": evidence_source or [],
        "repeated_follow_up": repeated,
        "created_at": _now(),
    }


# ── PM Agent Control: decide instruction type ─────────────────────────────────
def _decide_instruction_type(
    risk_level: str,
    analysis_text: str,
    agent_id: str,
    resource_result: dict,
    delay_result: dict,
    site_logic_result: dict,
    evidence_class: str,
) -> Optional[str]:
    """
    PM Agent final control logic.
    Returns instruction type key or None if data insufficient.
    """
    text_lower = (analysis_text or "").lower()
    risk_high = risk_level in ("高風險", "極高風險")

    # Insufficient data guard
    if evidence_class in ("missing_evidence", "prohibited_inference"):
        return "InsufficientData"

    # Safety agent + high risk → Safety Follow-up
    if agent_id in ("safety", "safety_agent") and risk_high:
        return "SafetyFollowUp"

    # Safety keywords in text
    safety_kw = ["停工", "危險", "安全", "墮下", "倒塌", "觸電", "火警", "爆炸", "高空", "safety"]
    if risk_high and any(kw in text_lower for kw in safety_kw):
        return "SafetyFollowUp"

    # Legal / compliance → Corrective Action Notice
    legal_kw = ["違規", "違例", "法例", "條例", "合規", "legal", "compliance", "bd", "emsd", "fsd"]
    if any(kw in text_lower for kw in legal_kw):
        return "CorrectiveAction"

    # Resource / workforce issue → Subcontractor Follow-up
    if resource_result and resource_result.get("has_evidence"):
        impact = resource_result.get("resource_impact_level", "無明顯影響")
        if impact in ("中度影響", "嚴重影響"):
            return "SubcontractorFollowup"
        wf = resource_result.get("workforce_issues") or []
        tc = resource_result.get("trade_conflicts") or []
        mat = resource_result.get("material_issues") or []
        if wf or tc or mat:
            return "SubcontractorFollowup"

    # Delay concern → PM Internal Note
    if delay_result and delay_result.get("has_delay_concern"):
        return "PMInternalNote"
    delay_kw = ["延誤", "delay", "落後", "趕工", "工期"]
    if any(kw in text_lower for kw in delay_kw):
        return "PMInternalNote"

    # General high risk → Site Instruction
    if risk_high:
        return "SiteInstruction"

    # Medium risk with site logic issues
    if risk_level == "中風險" and site_logic_result and site_logic_result.get("has_issues"):
        return "SiteInstruction"

    # Low risk or no clear signal → PM Internal Note (lightweight)
    if risk_level == "低風險":
        return "PMInternalNote"

    return "SiteInstruction"


def _issued_to_from_type(instr_type: str, agent_id: str) -> str:
    mapping = {
        "SafetyFollowUp":        "安全主任 / 地盤主管",
        "CorrectiveAction":      "承建商 / 地盤主管",
        "SubcontractorFollowup": "相關分判商",
        "PMInternalNote":        "PM（內部）",
        "SiteInstruction":       "地盤主管 / 承建商",
        "InsufficientData":      "待確認",
    }
    return mapping.get(instr_type, "待確認")


def _required_action_from_type(instr_type: str, risk_level: str, analysis_text: str) -> str:
    text_short = (analysis_text or "")[:200]
    if instr_type == "SafetyFollowUp":
        return f"即時跟進安全事項，確認現場安全措施已到位。如有高風險工序，須由安全主任確認後方可繼續。"
    if instr_type == "CorrectiveAction":
        return f"即時整改，確認符合相關法例及規例要求，並提交整改記錄。"
    if instr_type == "SubcontractorFollowup":
        return f"確認分判商到場及資源安排，跟進人手、材料及機械是否到位。"
    if instr_type == "PMInternalNote":
        return f"PM 內部跟進，監察工程進度及資源安排，必要時調整施工計劃。"
    if instr_type == "InsufficientData":
        return f"補充相片、文件或現場紀錄後，再作正式評估。"
    return f"跟進現場工程事項，確認工序按計劃進行。"


def _priority_from_type(instr_type: str, risk_level: str) -> str:
    if instr_type in ("SafetyFollowUp", "CorrectiveAction"):
        return "高"
    if risk_level in ("高風險", "極高風險"):
        return "高"
    if instr_type == "SubcontractorFollowup":
        return "中"
    if instr_type == "PMInternalNote":
        return "中" if risk_level == "中風險" else "低"
    if risk_level == "中風險":
        return "中"
    return "低"


def _collect_evidence(data: dict) -> list:
    """Collect evidence sources from analysis data."""
    sources = []
    if data.get("file_name"):
        sources.append(data["file_name"])
    if data.get("analysis_type"):
        sources.append(data["analysis_type"])
    ev = data.get("evidence_result", {})
    if ev and ev.get("evidence_label_zh"):
        sources.append(ev["evidence_label_zh"])
    rw = data.get("resource_workforce_result", {})
    if rw and rw.get("has_evidence"):
        sources.append("Resource/Workforce Analysis")
    return sources[:4]


# ── Main entry point ──────────────────────────────────────────────────────────
def generate_site_instructions(data: dict) -> dict:
    """
    Main function called from 1_Upload.py after analysis.

    Args:
        data: session analysis dict from st.session_state["last_analysis"]

    Returns:
        dict with keys:
            has_instructions, instructions, instruction_count,
            high_priority_count, insufficient_data, pm_summary
    """
    if not data:
        return _empty_result("未有分析資料。")

    project_ref = str(data.get("project_ref", "") or "未填寫")
    session_id = str(data.get("session_id", "") or "")
    risk_level = data.get("risk_level", "中風險") or "中風險"
    analysis_text = data.get("analysis_result", "") or ""
    selected_agents = data.get("selected_agents") or []
    agent_id = selected_agents[0] if selected_agents else ""

    resource_result = data.get("resource_workforce_result") or {}
    delay_result = data.get("delay_concern_result") or {}
    site_logic_result = data.get("site_logic_result") or {}
    evidence_result = data.get("evidence_result") or {}
    evidence_class = evidence_result.get("evidence_class", "uncertain")

    # Hallucination guard: no meaningful text → insufficient data
    if not analysis_text.strip() or len(analysis_text.strip()) < 30:
        return _empty_result("資料不足以發出正式指令，建議先補充相片、文件或現場紀錄。")

    # PM Agent decides instruction type
    instr_type = _decide_instruction_type(
        risk_level=risk_level,
        analysis_text=analysis_text,
        agent_id=agent_id,
        resource_result=resource_result,
        delay_result=delay_result,
        site_logic_result=site_logic_result,
        evidence_class=evidence_class,
    )

    if instr_type is None:
        return _empty_result("目前分析結果未達生成正式指令的門檻。")

    issued_to = _issued_to_from_type(instr_type, agent_id)
    priority = _priority_from_type(instr_type, risk_level)
    required_action = _required_action_from_type(instr_type, risk_level, analysis_text)
    evidence_sources = _collect_evidence(data)

    # Build title from analysis
    question = data.get("question", "") or ""
    title_base = question[:60] if question else analysis_text[:60]
    title = f"{INSTRUCTION_TYPES.get(instr_type, instr_type)}：{title_base}"

    # Detail: first 300 chars of analysis
    detail = analysis_text[:300].strip()

    # Related agent label
    from utils.lang import AGENTS
    related_agent = AGENTS.get(agent_id, {}).get("label", agent_id) if agent_id else "PM Agent"

    # Duplicate check
    repeated = _is_duplicate(project_ref, instr_type, title_base)

    instruction = _build_instruction(
        project_ref=project_ref,
        session_id=session_id,
        instr_type=instr_type,
        issued_to=issued_to,
        related_agent=related_agent,
        related_risk=risk_level,
        title=title,
        detail=detail,
        required_action=required_action,
        priority=priority,
        evidence_source=evidence_sources,
        repeated=repeated,
    )

    # Persist (skip if duplicate)
    if not repeated:
        existing = _load()
        existing.append(instruction)
        _save(existing)

    # Build result
    instructions = [instruction]
    high_count = sum(1 for i in instructions if i.get("priority") == "高")
    insufficient = instr_type == "InsufficientData"

    pm_summary = _build_pm_summary(instructions, risk_level, insufficient)

    return {
        "has_instructions": True,
        "instructions": instructions,
        "instruction_count": len(instructions),
        "high_priority_count": high_count,
        "insufficient_data": insufficient,
        "pm_summary": pm_summary,
    }


def _empty_result(reason: str) -> dict:
    return {
        "has_instructions": False,
        "instructions": [],
        "instruction_count": 0,
        "high_priority_count": 0,
        "insufficient_data": True,
        "pm_summary": reason,
    }


def _build_pm_summary(instructions: list, risk_level: str, insufficient: bool) -> str:
    if insufficient:
        return "資料不足以發出正式指令，建議先補充相片、文件或現場紀錄。"
    if not instructions:
        return "未有需要跟進的指令。"
    lines = []
    for instr in instructions:
        label = instr.get("instruction_type_label", "")
        pri = instr.get("priority", "中")
        to = instr.get("issued_to", "待確認")
        action = instr.get("required_action", "")[:80]
        repeated_tag = "（重複跟進）" if instr.get("repeated_follow_up") else ""
        lines.append(f"[{pri}] {label} → {to}{repeated_tag}：{action}")
    return "\n".join(lines)


# ── Action Tracker integration ────────────────────────────────────────────────
def create_action_items_from_instructions(
    instructions: list, project_ref: str, session_id: str
) -> list:
    """
    For each instruction with priority 高/中, create an Action Item.
    Skips if a matching action already exists for this session_id + instruction_type.
    Returns list of created action dicts.
    """
    from utils.action_manager import load_action_items, add_action_item

    existing_actions = load_action_items()
    existing_keys = {
        (a.get("session_id", ""), a.get("action_title", "")[:40])
        for a in existing_actions
    }

    created = []
    for instr in instructions:
        if instr.get("priority") not in ("高", "中"):
            continue
        if instr.get("instruction_type") == "InsufficientData":
            continue

        title_key = instr.get("instruction_title", "")[:40]
        if (session_id, title_key) in existing_keys:
            continue  # already exists

        action = {
            "project_ref": project_ref,
            "session_id": session_id,
            "risk_level": "高風險" if instr.get("priority") == "高" else "中風險",
            "responsible_agent": instr.get("related_agent", "PM Agent"),
            "department": instr.get("issued_to", "待確認"),
            "action_title": instr.get("instruction_title", "跟進指令")[:80],
            "action_detail": instr.get("required_action", ""),
            "priority": instr.get("priority", "中"),
            "status": "未開始",
        }
        try:
            created_action = add_action_item(action)
            created.append(created_action)
            existing_keys.add((session_id, title_key))
        except Exception:
            pass

    return created


# ── Memory integration ────────────────────────────────────────────────────────
def write_instruction_to_memory(result: dict, session_data: dict) -> None:
    """
    Write instruction summary to session memory.
    Only writes if instruction_count > 0.
    """
    if not result.get("has_instructions"):
        return
    try:
        from utils.session_memory import write_session_memory
        session_data["generated_instructions"] = result.get("instructions", [])
        session_data["instruction_count"] = result.get("instruction_count", 0)
        session_data["high_priority_instruction_count"] = result.get("high_priority_count", 0)
        write_session_memory(session_data)
    except Exception:
        pass


# ── Report formatter ──────────────────────────────────────────────────────────
def format_instructions_for_report(result: dict) -> str:
    """Returns a plain-text summary for PDF / text report."""
    if not result or not result.get("has_instructions"):
        return result.get("pm_summary", "未有跟進指令。") if result else "未有跟進指令。"

    lines = ["【建議跟進指令】"]
    for instr in result.get("instructions", []):
        label = instr.get("instruction_type_label", "")
        pri = instr.get("priority", "中")
        to = instr.get("issued_to", "待確認")
        action = instr.get("required_action", "")
        ev = "、".join(instr.get("evidence_source", []))
        repeated = "（重複跟進）" if instr.get("repeated_follow_up") else ""
        lines.append(f"[{pri}] {label}{repeated}")
        lines.append(f"  對象：{to}")
        lines.append(f"  要求行動：{action}")
        if ev:
            lines.append(f"  證據來源：{ev}")
        lines.append("")
    return "\n".join(lines).strip()
