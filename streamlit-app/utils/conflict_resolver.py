# -*- coding: utf-8 -*-
"""
utils/conflict_resolver.py
HK-AICOS Phase 3.2C — Cross-Agent Conflict Resolution Layer

PM Agent has final authority.
resolve_agent_conflicts() returns a structured PM Final Summary.
"""

from __future__ import annotations
import re
from typing import Any

# ── Risk ordering ─────────────────────────────────────────────────────────────
_RISK_ORDER = {"低風險": 1, "中風險": 2, "高風險": 3, "極高風險": 4}
_RISK_LABEL = {1: "低風險", 2: "中風險", 3: "高風險", 4: "極高風險"}

# ── Immediate-danger keywords → Safety always overrides ──────────────────────
_IMMEDIATE_DANGER = [
    "open edge", "臨邊", "live electrical", "裸露電線", "帶電",
    "no harness", "無安全帶", "blocked fire escape", "堵塞逃生",
    "blocked exit", "逃生路線受阻", "immediate danger", "即時危險",
    "life threatening", "致命",
]

# ── Housekeeping-only keywords → Foreman may downgrade ───────────────────────
_HOUSEKEEPING_ONLY = [
    "housekeeping", "雜物", "untidy", "minor debris", "輕微雜物",
    "general untidy", "一般雜亂", "minor blockage", "臨時阻礙",
]

# ── Confidence defaults per agent ─────────────────────────────────────────────
_DEFAULT_CONFIDENCE = {
    "safety":      0.88,
    "hk_legal":    0.90,
    "legal":       0.90,
    "pm":          0.82,
    "engineering": 0.78,
    "foreman":     0.65,
    "qs":          0.72,
    "accounting":  0.68,
    "material":    0.60,
    "drafting":    0.62,
    "surveying":   0.70,
    "translator":  0.50,
}

_AGENT_DISPLAY = {
    "safety":      "Safety Agent",
    "hk_legal":    "HK Legal Layer",
    "legal":       "HK Legal Layer",
    "pm":          "PM Agent",
    "engineering": "Engineering Agent",
    "foreman":     "Foreman Agent",
    "qs":          "QS Agent",
    "accounting":  "Accounting Agent",
    "material":    "Material Agent",
    "drafting":    "Drafting Agent",
    "surveying":   "Surveying Agent",
    "translator":  "Translator Agent",
}


def _risk_int(level: str) -> int:
    return _RISK_ORDER.get(str(level or "").strip(), 2)


def _has_keyword(text: str, keywords: list[str]) -> bool:
    t = str(text or "").lower()
    return any(k.lower() in t for k in keywords)


def _extract_confidence(agent_data: dict, agent_id: str) -> float:
    c = agent_data.get("confidence") or agent_data.get("confidence_score")
    if c is not None:
        try:
            return float(c)
        except (TypeError, ValueError):
            pass
    return _DEFAULT_CONFIDENCE.get(agent_id, 0.70)


def _extract_risk_level(agent_data: Any) -> str:
    if isinstance(agent_data, dict):
        for key in ("risk_level", "calibrated_risk_level", "overall_risk_level"):
            v = agent_data.get(key)
            if v:
                return str(v).strip()
        output = str(agent_data.get("output") or agent_data.get("text") or "")
        if "高風險" in output or "極高風險" in output:
            return "高風險"
        if "中風險" in output:
            return "中風險"
        if "低風險" in output:
            return "低風險"
        return "中風險"
    return "中風險"


def _extract_output(agent_data: Any) -> str:
    if isinstance(agent_data, dict):
        return str(agent_data.get("output") or agent_data.get("text") or agent_data.get("summary") or "")
    return str(agent_data or "")


def resolve_agent_conflicts(
    agent_results: dict[str, Any],
    selected_agents: list[str],
    calibration_result: dict | None = None,
) -> dict:
    """
    Analyse conflicts between agent outputs and produce a PM Final Summary.

    Returns:
    {
        "overall_risk":         str,
        "can_continue":         str,   # "Yes" / "Limited" / "No"
        "final_recommendation": str,
        "final_action_plan":    list[str],
        "conflict_analysis":    list[dict],
        "override_agent":       str,
        "override_reason":      str,
        "merged_risks":         list[dict],
        "agent_confidence":     dict[str, float],
        "pm_summary":           str,
        "fallback_used":        bool,
    }
    """
    try:
        return _resolve(agent_results, selected_agents, calibration_result)
    except Exception as exc:
        # Fallback — never crash
        fallback_risk = "中風險"
        if calibration_result:
            fallback_risk = calibration_result.get("overall_risk_level", "中風險")
        return {
            "overall_risk": fallback_risk,
            "can_continue": "Limited",
            "final_recommendation": "請參閱各 Agent 分析報告。",
            "final_action_plan": ["跟進各 Agent 建議。"],
            "conflict_analysis": [],
            "override_agent": "PM Agent",
            "override_reason": f"Conflict resolution fallback: {exc}",
            "merged_risks": [],
            "agent_confidence": {},
            "pm_summary": "PM Agent 整合分析（fallback）：請參閱各 Agent 報告。",
            "fallback_used": True,
        }


def _resolve(
    agent_results: dict[str, Any],
    selected_agents: list[str],
    calibration_result: dict | None,
) -> dict:
    selected = [str(a).strip() for a in (selected_agents or [])]
    if not selected:
        selected = list(agent_results.keys())

    # ── Collect per-agent data ────────────────────────────────────────────────
    agent_data: dict[str, dict] = {}
    for aid in selected:
        raw = (agent_results or {}).get(aid)
        if raw is None and aid == "hk_legal":
            raw = (agent_results or {}).get("legal")
        if raw is None and aid == "legal":
            raw = (agent_results or {}).get("hk_legal")
        risk = _extract_risk_level(raw)
        output = _extract_output(raw)
        conf = _extract_confidence(raw if isinstance(raw, dict) else {}, aid)
        agent_data[aid] = {
            "risk_level": risk,
            "risk_int": _risk_int(risk),
            "output": output,
            "confidence": conf,
            "display": _AGENT_DISPLAY.get(aid, aid),
        }

    # ── Detect conflicts ──────────────────────────────────────────────────────
    risk_levels = {aid: d["risk_int"] for aid, d in agent_data.items()}
    unique_risks = set(risk_levels.values())
    has_conflict = len(unique_risks) > 1

    conflict_analysis: list[dict] = []
    if has_conflict:
        max_r = max(unique_risks)
        min_r = min(unique_risks)
        high_agents = [aid for aid, r in risk_levels.items() if r == max_r]
        low_agents  = [aid for aid, r in risk_levels.items() if r == min_r]
        conflict_analysis.append({
            "type": "risk_level_conflict",
            "description": (
                f"風險級別衝突：{', '.join(_AGENT_DISPLAY.get(a,a) for a in high_agents)} "
                f"判斷 {_RISK_LABEL[max_r]}，"
                f"而 {', '.join(_AGENT_DISPLAY.get(a,a) for a in low_agents)} "
                f"判斷 {_RISK_LABEL[min_r]}。"
            ),
            "agents_high": high_agents,
            "agents_low": low_agents,
        })

    # ── Apply override rules ──────────────────────────────────────────────────
    override_agent = "PM Agent"
    override_reason = "PM Agent 按加權分數整合各 Agent 意見。"
    final_risk_int = max(risk_levels.values()) if risk_levels else 2

    # Use calibration result as base if available
    if calibration_result:
        cal_risk = calibration_result.get("overall_risk_level", "中風險")
        final_risk_int = _risk_int(cal_risk)

    # Rule A: Safety + Legal both High → cannot go below High
    safety_high = agent_data.get("safety", {}).get("risk_int", 0) >= 3
    legal_high  = (
        agent_data.get("hk_legal", {}).get("risk_int", 0) >= 3
        or agent_data.get("legal", {}).get("risk_int", 0) >= 3
    )
    if safety_high and legal_high and final_risk_int < 3:
        final_risk_int = 3
        override_agent = "Safety Agent + HK Legal Layer"
        override_reason = "Safety 及 Legal 同時判斷高風險，最終風險不可低於高風險（Rule A）。"
        conflict_analysis.append({
            "type": "safety_legal_override",
            "description": override_reason,
        })

    # Rule B: Foreman says OK but Safety detects immediate danger → Safety override
    foreman_low = agent_data.get("foreman", {}).get("risk_int", 0) <= 2
    safety_output = agent_data.get("safety", {}).get("output", "")
    if foreman_low and safety_high and _has_keyword(safety_output, _IMMEDIATE_DANGER):
        final_risk_int = max(final_risk_int, 3)
        override_agent = "Safety Agent"
        override_reason = "Safety Agent 偵測到即時生命危險，覆蓋 Foreman 判斷（Rule B）。"
        conflict_analysis.append({
            "type": "safety_override_foreman",
            "description": override_reason,
        })

    # Rule C: Only housekeeping issues → Foreman may downgrade to Medium
    all_outputs = " ".join(d["output"] for d in agent_data.values())
    if (
        _has_keyword(all_outputs, _HOUSEKEEPING_ONLY)
        and not _has_keyword(all_outputs, _IMMEDIATE_DANGER)
        and final_risk_int >= 3
        and not safety_high
        and not legal_high
    ):
        final_risk_int = min(final_risk_int, 2)
        override_agent = "Foreman Agent"
        override_reason = "僅涉及 housekeeping 問題，Foreman 判斷可降至中風險（Rule C）。"
        conflict_analysis.append({
            "type": "foreman_downgrade",
            "description": override_reason,
        })

    # Rule D: Critical safety keywords → Legal/Safety priority
    if _has_keyword(all_outputs, _IMMEDIATE_DANGER):
        final_risk_int = max(final_risk_int, 3)
        if override_agent == "PM Agent":
            override_agent = "Safety Agent / HK Legal Layer"
            override_reason = "偵測到臨邊、帶電、無安全帶或堵塞逃生等關鍵詞，Legal/Safety 優先（Rule D）。"
        conflict_analysis.append({
            "type": "critical_keyword_override",
            "description": "偵測到即時危險關鍵詞，Safety/Legal 優先。",
        })

    # Rule E: QS high cost risk but safety low → only raise Commercial Risk
    qs_high = agent_data.get("qs", {}).get("risk_int", 0) >= 3
    if qs_high and not safety_high and final_risk_int < 3:
        conflict_analysis.append({
            "type": "qs_commercial_only",
            "description": "QS 判斷高商業風險，但安全風險低，不提升整體安全風險（Rule E）。",
        })

    final_risk = _RISK_LABEL.get(final_risk_int, "中風險")

    # ── Merge duplicate risks ─────────────────────────────────────────────────
    merged_risks = _merge_risks(agent_data)

    # ── Can continue? ─────────────────────────────────────────────────────────
    if final_risk_int >= 4:
        can_continue = "No"
    elif final_risk_int == 3:
        can_continue = "Limited"
    else:
        can_continue = "Yes"

    # ── Final recommendation ──────────────────────────────────────────────────
    if can_continue == "No":
        final_rec = "立即停工，整改後方可復工。所有高危工序須暫停，並通知相關負責人。"
    elif can_continue == "Limited":
        final_rec = "有限度施工，高危工序須即時整改，其餘工序可在安全措施到位後繼續。"
    else:
        final_rec = "可繼續施工，按各 Agent 建議跟進改善事項。"

    # ── Final action plan ─────────────────────────────────────────────────────
    action_plan = _build_action_plan(merged_risks, final_risk_int, agent_data)

    # ── Agent confidence ──────────────────────────────────────────────────────
    agent_confidence = {aid: round(d["confidence"], 2) for aid, d in agent_data.items()}

    # ── PM Summary text ───────────────────────────────────────────────────────
    conflict_desc = (
        "；".join(c["description"] for c in conflict_analysis)
        if conflict_analysis else "各 Agent 意見一致，無明顯衝突。"
    )
    merged_desc = (
        "、".join(r["label"] for r in merged_risks[:3])
        if merged_risks else "未偵測到具體風險項目。"
    )
    pm_summary = (
        f"整體風險：{final_risk}。\n"
        f"衝突分析：{conflict_desc}\n"
        f"主要風險：{merged_desc}\n"
        f"最終建議：{final_rec}\n"
        f"可否繼續施工：{can_continue}。\n"
        f"裁決依據：{override_reason}"
    )

    return {
        "overall_risk": final_risk,
        "can_continue": can_continue,
        "final_recommendation": final_rec,
        "final_action_plan": action_plan,
        "conflict_analysis": conflict_analysis,
        "override_agent": override_agent,
        "override_reason": override_reason,
        "merged_risks": merged_risks,
        "agent_confidence": agent_confidence,
        "pm_summary": pm_summary,
        "fallback_used": False,
    }


def _merge_risks(agent_data: dict) -> list[dict]:
    """Collect all risk mentions across agents and deduplicate."""
    from utils.risk_matrix import RISK_ITEMS, merge_duplicate_risks

    all_issues: list[dict] = []
    seen_labels: set[str] = set()

    for aid, data in agent_data.items():
        output = data.get("output", "")
        lowered = output.lower()
        for score, confidence, category, label, keywords in RISK_ITEMS:
            for kw in keywords:
                if kw.lower() in lowered and label not in seen_labels:
                    all_issues.append({
                        "label": label,
                        "score": score,
                        "confidence": confidence,
                        "category": category,
                        "agents": [_AGENT_DISPLAY.get(aid, aid)],
                    })
                    seen_labels.add(label)
                    break

    # Merge duplicates
    merged = merge_duplicate_risks(all_issues)

    # Annotate with agent count
    for issue in merged:
        agents_involved = []
        for aid, data in agent_data.items():
            if issue["label"].lower() in data.get("output", "").lower():
                agents_involved.append(_AGENT_DISPLAY.get(aid, aid))
        issue["agents"] = list(dict.fromkeys(agents_involved))

    return sorted(merged, key=lambda x: x.get("score", 0), reverse=True)


def _build_action_plan(
    merged_risks: list[dict],
    final_risk_int: int,
    agent_data: dict,
) -> list[str]:
    actions = []
    for risk in merged_risks[:3]:
        cat = risk.get("category", "")
        label = risk.get("label", "")
        if cat == "critical":
            actions.append(f"立即處理：{label}。")
        elif cat == "high":
            actions.append(f"優先跟進：{label}。")
        elif cat == "medium":
            actions.append(f"安排整改：{label}。")

    if final_risk_int >= 3 and not actions:
        actions.append("立即進行現場安全檢查，識別並隔離高危區域。")

    if final_risk_int >= 3:
        actions.append("通知相關負責人及安全主任，記錄事件並跟進整改。")

    if not actions:
        actions.append("按各 Agent 建議跟進改善事項，定期複查。")

    return actions[:5]
