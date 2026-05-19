# -*- coding: utf-8 -*-
"""
HK-AICOS Phase 3.3C - Delay Concern & Early Warning Layer.

This module scores early delay concern signals. It does not predict delay days,
completion dates, or programme impact duration.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone


INSUFFICIENT_DELAY_MESSAGE = "目前資料不足以判斷實際工期影響。"


ISSUE_SIGNATURES = {
    "open edge": ["open edge", "edge protection", "臨邊", "邊位", "圍欄"],
    "water leakage": ["water leakage", "leakage", "water seepage", "滲漏", "漏水"],
    "blocked escape": ["blocked escape", "blocked access", "blocked walkway", "逃生通道", "走火通道", "阻塞通道"],
    "no harness": ["no harness", "harness", "安全帶", "未佩戴安全帶"],
    "no helmet": ["no helmet", "helmet", "安全帽", "未戴安全帽"],
    "live electrical": ["live electrical", "electrical", "帶電", "觸電"],
    "material not arrived": ["material not arrived", "material delay", "材料未到", "物料未到", "材料延誤"],
    "inspection not completed": ["inspection not completed", "inspection pending", "not inspected", "未完成檢查", "未驗收", "inspection"],
    "testing not completed": ["testing not completed", "test pending", "未完成測試", "testing"],
    "workflow conflict": ["workflow conflict", "out of sequence", "工序衝突", "工序不合理"],
}


SAFETY_SIGNATURES = {"open edge", "blocked escape", "no harness", "no helmet", "live electrical"}


CONCERN_LEVELS = [
    (61, "Critical Concern"),
    (41, "High Concern"),
    (21, "Moderate Concern"),
    (0, "Low Concern"),
]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _parse_dt(value: str):
    raw = str(value or "").strip()
    if not raw:
        return None
    raw = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        return None


def _days_between(first: str, last: str) -> int:
    start = _parse_dt(first)
    end = _parse_dt(last) or datetime.now()
    if not start:
        return 0
    return max(0, (end - start).days)


def _contains(text: str, keywords: list[str]) -> bool:
    lower = text.lower()
    return any(keyword.lower() in lower for keyword in keywords)


def detect_issue_signatures(text: str) -> list[str]:
    content = _norm(text)
    found = []
    for signature, keywords in ISSUE_SIGNATURES.items():
        if _contains(content, keywords):
            found.append(signature)
    return found


def _session_text(session: dict) -> str:
    return "\n".join([
        str(session.get("analysis_type", "")),
        str(session.get("question", "")),
        str(session.get("summary", "")),
        str(session.get("analysis_summary", "")),
        str(session.get("analysis_result", "")),
        str(session.get("ocr_text", "")),
        str(session.get("image_ocr_context", "")),
    ])


def _is_open_action(item: dict) -> bool:
    status = str(item.get("status", "") or "").strip().lower()
    if not status:
        return True
    closed_terms = ["resolved", "closed", "done", "complete", "completed", "完成", "已處理"]
    return not any(term in status for term in closed_terms)


def _level_from_score(score: int) -> str:
    for threshold, label in CONCERN_LEVELS:
        if score >= threshold:
            return label
    return "Low Concern"


def _unique_event_key(event: dict) -> tuple:
    return (
        event.get("signature", ""),
        event.get("session_id") or event.get("time") or event.get("source") or "",
    )


def analyse_delay_concern(
    project_ref: str = "",
    current_session: dict | None = None,
    project_data: dict | None = None,
    action_items: list | None = None,
    site_logic_result: dict | None = None,
    progress_result: dict | None = None,
    ocr_text: str = "",
    now: str = "",
) -> dict:
    """Return Delay Concern score, level, signals, and PM summary."""
    current_session = current_session or {}
    project_data = project_data or {}
    action_items = list(action_items or [])
    site_logic_result = site_logic_result or {}
    progress_result = progress_result or {}
    current_time = (
        current_session.get("time")
        or current_session.get("upload_time")
        or now
        or datetime.now().isoformat(timespec="seconds")
    )
    current_session_id = str(current_session.get("session_id", "") or "")

    current_text = "\n".join([_session_text(current_session), str(ocr_text or "")])
    current_signatures = detect_issue_signatures(current_text)

    previous_sessions = [
        s for s in (project_data.get("sessions", []) or [])
        if str(s.get("session_id", "") or "") != current_session_id
    ]
    previous_events = []
    for session in previous_sessions:
        for signature in detect_issue_signatures(_session_text(session)):
            previous_events.append({
                "signature": signature,
                "session_id": session.get("session_id", ""),
                "time": session.get("time") or session.get("upload_time") or "",
                "source": "session",
            })
    for risk in (project_data.get("risks", []) or []):
        for signature in detect_issue_signatures(str(risk.get("risk", ""))):
            previous_events.append({
                "signature": signature,
                "session_id": risk.get("session_id", ""),
                "time": risk.get("date", ""),
                "source": "risk_timeline",
            })

    deduped_events = { _unique_event_key(event): event for event in previous_events }
    event_counter = Counter(event["signature"] for event in deduped_events.values())

    repeated_issues = []
    for signature in current_signatures:
        count = event_counter.get(signature, 0) + 1
        if count >= 2:
            dates = [
                event.get("time", "")
                for event in deduped_events.values()
                if event.get("signature") == signature and event.get("time")
            ]
            dates.append(current_time)
            first_seen = min(dates) if dates else ""
            repeated_issues.append({
                "signature": signature,
                "count": count,
                "first_seen": first_seen,
                "latest_seen": current_time,
                "unresolved_days": _days_between(first_seen, current_time),
                "source": "timeline",
            })

    repeated_ocr_findings = []
    for signature in detect_issue_signatures(ocr_text):
        prior_count = event_counter.get(signature, 0)
        if prior_count:
            repeated_ocr_findings.append({
                "signature": signature,
                "count": prior_count + 1,
                "source": "ocr",
            })

    project_actions = [
        item for item in action_items
        if not project_ref or str(item.get("project_ref", "")).strip() == str(project_ref).strip()
    ]
    open_actions = [item for item in project_actions if _is_open_action(item)]
    long_unresolved_actions = []
    action_title_counter = Counter()
    for item in open_actions:
        title = _norm(item.get("action_title") or item.get("action_detail") or "")
        if title:
            action_title_counter[title.lower()[:80]] += 1
        age_days = _days_between(item.get("created_at", ""), current_time)
        if age_days > 7:
            long_unresolved_actions.append({
                "action_id": item.get("action_id", ""),
                "title": item.get("action_title", ""),
                "age_days": age_days,
                "status": item.get("status", ""),
                "priority": item.get("priority", ""),
            })
    repeated_actions = [
        {"title": title, "count": count}
        for title, count in action_title_counter.items()
        if count >= 2
    ]

    workflow_blockages = []
    for key in ("sequence_findings", "trade_conflicts", "flow_findings"):
        for item in site_logic_result.get(key, []) or []:
            workflow_blockages.append({
                "title": item.get("title", ""),
                "finding": item.get("finding", ""),
                "rule_id": item.get("rule_id", ""),
                "source": key,
            })

    score = 0
    signals = []

    for item in repeated_issues:
        signature = item["signature"]
        if signature == "open edge":
            points = 15
            label = "Repeated Open Edge"
        elif signature in SAFETY_SIGNATURES:
            points = 20
            label = "Repeated safety issue"
        elif signature in {"material not arrived", "inspection not completed", "testing not completed"}:
            points = 15
            label = signature
        elif signature == "workflow conflict":
            points = 10
            label = "Repeated workflow conflict"
        else:
            points = 10
            label = "Repeated issue"
        score += points
        signals.append({"signal": label, "points": points, "detail": f"{signature} 第 {item['count']} 次出現"})

    for item in repeated_ocr_findings:
        points = 10
        score += points
        signals.append({"signal": "Repeated OCR finding", "points": points, "detail": f"{item['signature']} 第 {item['count']} 次出現"})

    for item in long_unresolved_actions:
        points = 20
        score += points
        signals.append({"signal": "Action unresolved > 7 days", "points": points, "detail": f"{item.get('title') or item.get('action_id')} unresolved {item.get('age_days')} days"})

    for item in repeated_actions:
        points = 10
        score += points
        signals.append({"signal": "Repeated action item", "points": points, "detail": f"{item['title']} x {item['count']}"})

    if workflow_blockages:
        points = 10 * len(workflow_blockages)
        score += points
        signals.append({"signal": "Workflow Blockage", "points": points, "detail": f"{len(workflow_blockages)} workflow blockage signal(s)"})

    if any(sig in current_signatures for sig in ["material not arrived"]):
        score += 15
        signals.append({"signal": "Material issue", "points": 15, "detail": "material not arrived / material delay evidence"})

    if any(sig in current_signatures for sig in ["inspection not completed", "testing not completed"]):
        score += 15
        signals.append({"signal": "Inspection not completed", "points": 15, "detail": "inspection/testing not completed evidence"})

    has_evidence = bool(
        previous_sessions
        or project_data.get("risks")
        or open_actions
        or workflow_blockages
        or current_signatures
    )
    if not has_evidence:
        score = 0
        level = "Insufficient Data"
        summary = INSUFFICIENT_DELAY_MESSAGE
        trend = "insufficient_data"
    else:
        level = _level_from_score(score)
        trend = "delay trend emerging" if score >= 21 else "no clear delay trend"
        summary = f"Delay Concern Score {score}: {level}."

    repeated_lines = [
        f"- {item['signature']}: 第 {item['count']} 次出現。"
        for item in repeated_issues[:5]
    ] or ["- 未偵測到重覆 issue。"]
    blockage_lines = [
        f"- {item.get('title')}: {item.get('finding')}"
        for item in workflow_blockages[:5]
    ] or ["- 未偵測到 workflow blockage。"]
    progress_lines = [
        f"- {signal['signal']} (+{signal['points']}): {signal['detail']}"
        for signal in signals[:8]
    ] or [f"- {INSUFFICIENT_DELAY_MESSAGE if level == 'Insufficient Data' else '未見明確 delay concern signal。'}"]

    pm_summary = "\n".join([
        "Delay Concern Summary",
        f"- Concern Level: {level}",
        f"- Concern Score: {score}",
        f"- Delay Trend: {trend}",
        "- 哪些問題開始影響進度: " + ("; ".join(signal["detail"] for signal in signals[:3]) if signals else INSUFFICIENT_DELAY_MESSAGE),
        "- 哪些工序可能阻塞: " + ("; ".join(item.get("title", "") for item in workflow_blockages[:3]) if workflow_blockages else "未有明確 workflow blockage 證據。"),
        "- 哪些 action item 長期未完成: " + (f"{len(long_unresolved_actions)} 項超過 7 日" if long_unresolved_actions else "未有長期未完成 action 證據。"),
        "- 哪些風險重覆出現: " + ("; ".join(f"{item['signature']} 第 {item['count']} 次" for item in repeated_issues[:3]) if repeated_issues else "未有重覆風險證據。"),
    ])

    return {
        "project_ref": project_ref,
        "score": score,
        "level": level,
        "trend": trend,
        "summary": summary,
        "signals": signals,
        "repeated_issues": repeated_issues,
        "repeated_ocr_findings": repeated_ocr_findings,
        "long_unresolved_actions": long_unresolved_actions,
        "repeated_actions": repeated_actions,
        "workflow_blockages": workflow_blockages,
        "progress_concern": "\n".join(progress_lines),
        "repeated_issues_text": "\n".join(repeated_lines),
        "workflow_blockage_text": "\n".join(blockage_lines),
        "pm_summary": pm_summary,
        "has_evidence": has_evidence,
        "memory_should_record": level in {"Moderate Concern", "High Concern", "Critical Concern"},
        "insufficient_message": INSUFFICIENT_DELAY_MESSAGE,
    }


def format_delay_concern_for_report(result: dict) -> str:
    if not result:
        return "Delay Concern\n- 目前資料不足以判斷實際工期影響。"
    lines = [
        "Delay Concern",
        f"- Concern Score: {result.get('score', 0)}",
        f"- Concern Level: {result.get('level', 'Insufficient Data')}",
        f"- Summary: {result.get('summary', INSUFFICIENT_DELAY_MESSAGE)}",
        "Repeated Issues",
        result.get("repeated_issues_text") or "- 未偵測到重覆 issue。",
        "Workflow Blockage",
        result.get("workflow_blockage_text") or "- 未偵測到 workflow blockage。",
        "Progress Concern",
        result.get("progress_concern") or "- 未見明確 delay concern signal。",
    ]
    return "\n".join(lines)
