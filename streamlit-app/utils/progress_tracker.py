# -*- coding: utf-8 -*-
"""
HK-AICOS Phase 3.3B - Progress Tracking Layer.

Compares the current session with project session history, risk timeline, and
open action items. This is not a delay prediction engine; it only raises delay
concern when repeated evidence or unresolved actions are present.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone
from typing import Iterable


INSUFFICIENT_TIMELINE_MESSAGE = "目前資料不足以判斷實際工期狀況。"


RISK_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}


RISK_SIGNATURES = {
    "open edge": ["open edge", "臨邊", "邊位", "edge protection", "圍欄"],
    "no harness": ["no harness", "安全帶", "未佩戴安全帶", "harness"],
    "no helmet": ["no helmet", "安全帽", "未戴安全帽", "helmet"],
    "blocked escape": ["blocked escape", "逃生通道", "走火通道", "阻塞通道"],
    "live electrical": ["live electrical", "帶電", "觸電", "electrical"],
    "waterproof": ["waterproof", "防水", "滲漏"],
    "cable tray": ["cable tray", "線槽", "橋架"],
    "housekeeping": ["housekeeping", "凌亂", "雜亂", "材料阻路"],
    "hot work": ["hot work", "焊接", "燒焊", "火警"],
}


OPEN_STATUS_HINTS = {
    "open", "pending", "in_progress", "todo", "未完成", "未處理", "跟進中",
    "待處理", "頝脖葉", "?芷?憪?", "?怎楨",
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _risk_rank(risk_level: str) -> str:
    text = str(risk_level or "").lower()
    if any(token in text for token in ["critical", "emergency", "極高", "璆菟"]):
        return "critical"
    if any(token in text for token in ["high", "高", "擃"]):
        return "high"
    if any(token in text for token in ["low", "低", "雿"]):
        return "low"
    return "medium"


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
    a = _parse_dt(first)
    b = _parse_dt(last) or datetime.now()
    if not a:
        return 0
    return max(0, (b - a).days)


def _contains(text: str, keywords: Iterable[str]) -> bool:
    lower = text.lower()
    return any(str(keyword).lower() in lower for keyword in keywords)


def detect_risk_signatures(text: str) -> list:
    content = _norm(text)
    found = []
    for signature, keywords in RISK_SIGNATURES.items():
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
    ])


def _is_open_action(item: dict) -> bool:
    status = str(item.get("status", "")).strip()
    if not status:
        return True
    status_lower = status.lower()
    return status in OPEN_STATUS_HINTS or status_lower in OPEN_STATUS_HINTS or "完成" not in status


def analyse_progress(
    project_ref: str,
    current_session: dict,
    project_data: dict | None = None,
    action_items: list | None = None,
    now: str = "",
) -> dict:
    """Compare current session against available project memory."""
    project_data = project_data or {}
    sessions = list(project_data.get("sessions", []) or [])
    risks = list(project_data.get("risks", []) or [])
    action_items = list(action_items or [])
    current_session = current_session or {}
    current_session_id = str(current_session.get("session_id", "") or "")
    current_time = current_session.get("time") or current_session.get("upload_time") or now or datetime.now().isoformat(timespec="seconds")

    previous_sessions = [
        s for s in sessions
        if str(s.get("session_id", "") or "") != current_session_id
    ]
    previous_sessions = sorted(
        previous_sessions,
        key=lambda s: s.get("time") or s.get("upload_time") or "",
        reverse=True,
    )
    last_session = previous_sessions[0] if previous_sessions else {}

    current_text = _session_text(current_session)
    current_signatures = detect_risk_signatures(current_text)

    signature_events = []
    for session in previous_sessions:
        for signature in detect_risk_signatures(_session_text(session)):
            signature_events.append({
                "signature": signature,
                "session_id": session.get("session_id", ""),
                "time": session.get("time") or session.get("upload_time") or "",
            })
    for risk in risks:
        for signature in detect_risk_signatures(str(risk.get("risk", ""))):
            signature_events.append({
                "signature": signature,
                "session_id": risk.get("session_id", ""),
                "time": risk.get("date", ""),
            })

    repeated = []
    unique_signature_events = {}
    for event in signature_events:
        unique_key = event.get("session_id") or event.get("time") or ""
        unique_signature_events[(event.get("signature"), unique_key)] = event
    deduped_events = list(unique_signature_events.values())
    event_counter = Counter(event["signature"] for event in deduped_events)
    for signature in current_signatures:
        count = event_counter.get(signature, 0) + 1
        if count >= 2:
            event_dates = [event.get("time", "") for event in deduped_events if event.get("signature") == signature]
            event_dates.append(current_time)
            event_dates = [d for d in event_dates if d]
            first_seen = min(event_dates) if event_dates else ""
            repeated.append({
                "signature": signature,
                "count": count,
                "first_seen": first_seen,
                "latest_seen": current_time,
                "unresolved_days": _days_between(first_seen, current_time),
                "message": f"{signature} issue 第 {count} 次出現。",
            })

    project_actions = [
        item for item in action_items
        if not project_ref or str(item.get("project_ref", "")).strip() == str(project_ref).strip()
    ]
    open_actions = [item for item in project_actions if _is_open_action(item)]
    long_unresolved_actions = []
    for item in open_actions:
        created_at = item.get("created_at", "")
        age_days = _days_between(created_at, current_time)
        if age_days >= 7:
            long_unresolved_actions.append({
                "action_id": item.get("action_id", ""),
                "title": item.get("action_title", ""),
                "status": item.get("status", ""),
                "age_days": age_days,
                "priority": item.get("priority", ""),
            })

    current_risk = _risk_rank(current_session.get("risk_level") or current_session.get("calibrated_risk_level", ""))
    last_risk = _risk_rank(last_session.get("risk_level") or last_session.get("calibrated_risk_level", "")) if last_session else ""
    if last_risk:
        if RISK_ORDER[current_risk] > RISK_ORDER[last_risk]:
            risk_change = "風險增加"
        elif RISK_ORDER[current_risk] < RISK_ORDER[last_risk]:
            risk_change = "風險減少"
        else:
            risk_change = "風險大致持平"
    else:
        risk_change = "沒有足夠上一個 Session 作比較"

    if not previous_sessions:
        progress_change = INSUFFICIENT_TIMELINE_MESSAGE
    elif repeated or long_unresolved_actions:
        progress_change = "有重覆問題或長時間 unresolved action，工程推進需 PM 跟進。"
    elif risk_change == "風險減少":
        progress_change = "與上次 Session 比較，現場風險有改善跡象。"
    else:
        progress_change = "與上次 Session 比較，未見明確進度惡化證據。"

    delay_points = 0
    delay_reasons = []
    if repeated:
        delay_points += len(repeated)
        delay_reasons.append("重覆問題仍然出現")
    if long_unresolved_actions:
        delay_points += 2
        delay_reasons.append("存在超過 7 日未完成 action item")
    if len(open_actions) >= 3:
        delay_points += 1
        delay_reasons.append("未完成 action item 數量偏多")

    if not previous_sessions and not open_actions and not risks:
        delay_concern = "insufficient_data"
        delay_message = INSUFFICIENT_TIMELINE_MESSAGE
    elif delay_points >= 3:
        delay_concern = "high"
        delay_message = "Delay Concern: 高。原因：" + "、".join(delay_reasons)
    elif delay_points >= 1:
        delay_concern = "watch"
        delay_message = "Delay Concern: 需觀察。原因：" + "、".join(delay_reasons)
    else:
        delay_concern = "low"
        delay_message = "Delay Concern: 暫未見明確 delay 證據。"

    stage = "未能判斷"
    current_lower = current_text.lower()
    if _contains(current_lower, ["handover", "交場", "移交"]):
        stage = "交場 / 移交階段"
    elif _contains(current_lower, ["finishing", "油漆", "飾面", "裝修"]):
        stage = "Finishing / 飾面階段"
    elif _contains(current_lower, ["rough-in", "機電", "線槽", "cable tray", "喉管"]):
        stage = "E&M rough-in / 機電施工階段"
    elif _contains(current_lower, ["防水", "waterproof"]):
        stage = "防水 / 濕區工程階段"

    pm_summary = [
        f"現場工程階段：{stage}",
        f"進度變化：{progress_change}",
        f"風險變化：{risk_change}",
        delay_message,
    ]
    if repeated:
        pm_summary.append("重覆問題：" + "；".join(item["message"] for item in repeated[:3]))
    if long_unresolved_actions:
        pm_summary.append(f"未完成整改：{len(long_unresolved_actions)} 項 action item 已超過 7 日。")

    return {
        "project_ref": project_ref,
        "has_timeline": bool(previous_sessions),
        "current_session_id": current_session_id,
        "last_session_id": last_session.get("session_id", ""),
        "stage": stage,
        "completion": "未能以現有資料量化完成度",
        "unfinished_items": [item.get("title", "") for item in long_unresolved_actions[:5]],
        "risk_change": risk_change,
        "progress_change": progress_change,
        "repeated_risks": repeated,
        "open_actions_count": len(open_actions),
        "long_unresolved_actions": long_unresolved_actions,
        "delay_concern": delay_concern,
        "delay_message": delay_message,
        "pm_summary": "\n".join(f"- {line}" for line in pm_summary),
        "timeline_comparison": {
            "previous_session": last_session.get("session_id", ""),
            "current_session": current_session_id,
            "risk_change": risk_change,
            "progress_change": progress_change,
            "repeated_count": len(repeated),
        },
    }


def format_progress_for_report(result: dict) -> str:
    if not result:
        return "進度追蹤分析\n- 目前資料不足以判斷實際工期狀況。"
    lines = [
        "進度追蹤分析",
        f"- 工程階段：{result.get('stage', '未能判斷')}",
        f"- 工序完成度：{result.get('completion', '未能以現有資料量化完成度')}",
        f"- 進度變化：{result.get('progress_change', INSUFFICIENT_TIMELINE_MESSAGE)}",
        f"- 風險變化：{result.get('risk_change', '')}",
        f"- Delay Concern：{result.get('delay_message', INSUFFICIENT_TIMELINE_MESSAGE)}",
    ]
    repeated = result.get("repeated_risks", []) or []
    if repeated:
        lines.append("- 重覆問題：")
        for item in repeated[:5]:
            lines.append(
                f"  - {item.get('signature')} 第 {item.get('count')} 次出現，"
                f"未整改時間約 {item.get('unresolved_days', 0)} 日。"
            )
    unresolved = result.get("long_unresolved_actions", []) or []
    if unresolved:
        lines.append("- 長時間 unresolved action：")
        for item in unresolved[:5]:
            lines.append(f"  - {item.get('title') or item.get('action_id')}，{item.get('age_days', 0)} 日。")
    if not repeated and not unresolved:
        lines.append("- 暫未偵測到重覆問題或長時間 unresolved action。")
    return "\n".join(lines)
