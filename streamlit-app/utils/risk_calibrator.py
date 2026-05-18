# -*- coding: utf-8 -*-
"""
utils/risk_calibrator.py
HK-AICOS Phase 3.1D — Agent risk calibration layer.
"""

import re
from typing import Any


RISK_SCORE = {
    "低風險": 1,
    "中風險": 2,
    "高風險": 3,
    "極高風險": 3,
}

SCORE_RISK = {
    1: "低風險",
    2: "中風險",
    3: "高風險",
}

AGENT_RISK_PROFILES = {
    "safety": {
        "name": "Safety Agent",
        "style": "保守",
        "weight": 1.4,
        "rule": "safety high risk cannot be downgraded below medium",
    },
    "hk_legal": {
        "name": "HK Legal Layer",
        "style": "超保守",
        "weight": 1.5,
        "rule": "legal / compliance issue increases final risk",
    },
    "legal": {
        "name": "HK Legal Layer",
        "style": "超保守",
        "weight": 1.5,
        "rule": "legal / compliance issue increases final risk",
    },
    "pm": {
        "name": "PM Agent",
        "style": "平衡",
        "weight": 1.0,
        "rule": "final coordinator",
    },
    "qs": {
        "name": "QS Agent",
        "style": "成本導向",
        "weight": 0.9,
        "rule": "cost risk affects commercial risk",
    },
    "foreman": {
        "name": "Foreman Agent",
        "style": "現場實務",
        "weight": 1.1,
        "rule": "site practicality affects execution risk",
    },
    "engineering": {
        "name": "Engineering Agent",
        "style": "技術實務",
        "weight": 1.2,
        "rule": "technical practicality affects engineering risk",
    },
    "accounting": {
        "name": "Accounting Agent",
        "style": "財務謹慎",
        "weight": 0.9,
        "rule": "financial risk affects commercial risk",
    },
    "material": {
        "name": "Material Agent",
        "style": "供應鏈實務",
        "weight": 0.8,
        "rule": "supply chain practicality affects delivery risk",
    },
    "drafting": {
        "name": "Drafting Agent",
        "style": "圖則細節",
        "weight": 1.0,
        "rule": "drawing details affect coordination risk",
    },
    "surveying": {
        "name": "Surveying Agent",
        "style": "精準測量",
        "weight": 1.1,
        "rule": "measurement accuracy affects site risk",
    },
    "translator": {
        "name": "Translator Agent",
        "style": "文件準確",
        "weight": 0.6,
        "rule": "document accuracy affects communication risk",
    },
}

_AGENT_NAME_TO_ID = {
    profile["name"].lower(): agent_id
    for agent_id, profile in AGENT_RISK_PROFILES.items()
}

_HIGH_SUBSTANTIVE_KEYWORDS = (
    "安全", "safety", "高空", "吊運", "倒塌", "結構", "structure", "structural",
    "電力", "電氣", "electric", "消防", "fire", "法規", "法例", "legal",
    "compliance", "違規", "停工", "危險", "致命", "受傷",
)


def _normalise_agent_id(agent_id: str) -> str:
    raw = str(agent_id or "").strip()
    lower = raw.lower()
    if lower in AGENT_RISK_PROFILES:
        return lower
    return _AGENT_NAME_TO_ID.get(lower, lower)


def _normalise_risk(risk_level: str) -> str:
    raw = str(risk_level or "").strip()
    if "高" in raw or "緊急" in raw:
        return "高風險"
    if "低" in raw:
        return "低風險"
    if "中" in raw:
        return "中風險"
    return "中風險"


def _risk_from_text(text: str) -> str:
    value = str(text or "")
    high_hits = len(re.findall(r"高風險|極高風險|重大|嚴重|停工|違規|危險|致命", value, flags=re.I))
    medium_hits = len(re.findall(r"中風險|需跟進|需要跟進|注意|可能|需確認", value, flags=re.I))
    low_hits = len(re.findall(r"低風險|輕微|一般|可接受|無明顯", value, flags=re.I))
    if high_hits:
        return "高風險"
    if medium_hits:
        return "中風險"
    if low_hits:
        return "低風險"
    return "中風險"


def _extract_risk(agent_result: Any) -> tuple[str, str]:
    if isinstance(agent_result, dict):
        risk = (
            agent_result.get("risk_level")
            or agent_result.get("calibrated_risk_level")
            or agent_result.get("overall_risk_level")
        )
        output = str(agent_result.get("output") or agent_result.get("text") or agent_result.get("summary") or "")
        if risk:
            return _normalise_risk(risk), output
        return _risk_from_text(output), output

    risk = getattr(agent_result, "risk_level", None)
    output = str(getattr(agent_result, "output", "") or getattr(agent_result, "text", "") or agent_result or "")
    if risk:
        return _normalise_risk(risk), output
    return _risk_from_text(output), output


def _has_substantive_high_issue(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(keyword.lower() in lowered for keyword in _HIGH_SUBSTANTIVE_KEYWORDS)


def _risk_from_score(score: float) -> str:
    if score >= 2.6:
        return "高風險"
    if score >= 1.5:
        return "中風險"
    return "低風險"


def calculate_overall_project_risk(agent_results, selected_agents):
    """
    Calculate calibrated overall project risk from agent-level results.

    Returns:
    - overall_risk_level
    - overall_risk_score
    - contributing_agents
    - highest_risk_agent
    - calibration_reason
    - safety_override
    - legal_override
    """
    selected = [_normalise_agent_id(agent_id) for agent_id in (selected_agents or [])]
    if not selected:
        selected = [_normalise_agent_id(agent_id) for agent_id in (agent_results or {}).keys()]

    contributing = []
    weighted_total = 0.0
    total_weight = 0.0
    highest_agent = ""
    highest_score = 0
    medium_count = 0
    high_with_substantive_issue = False
    safety_override = False
    legal_override = False

    for agent_id in selected:
        profile = AGENT_RISK_PROFILES.get(agent_id, {
            "name": agent_id or "Unknown Agent",
            "style": "一般",
            "weight": 1.0,
            "rule": "standard risk contribution",
        })
        raw_result = (agent_results or {}).get(agent_id)
        if raw_result is None and agent_id == "hk_legal":
            raw_result = (agent_results or {}).get("legal")
        if raw_result is None and agent_id == "legal":
            raw_result = (agent_results or {}).get("hk_legal")
        risk_level, output = _extract_risk(raw_result)
        score = RISK_SCORE.get(risk_level, 2)
        weight = float(profile.get("weight", 1.0))

        weighted_total += score * weight
        total_weight += weight
        if score == 2:
            medium_count += 1
        if score > highest_score:
            highest_score = score
            highest_agent = profile.get("name", agent_id)
        if agent_id == "safety" and score == 3:
            safety_override = True
        if agent_id in ("hk_legal", "legal") and score == 3:
            legal_override = True
        if score == 3 and _has_substantive_high_issue(output):
            high_with_substantive_issue = True

        contributing.append({
            "agent_id": agent_id,
            "agent_name": profile.get("name", agent_id),
            "style": profile.get("style", ""),
            "weight": weight,
            "risk_level": risk_level,
            "risk_score": score,
            "weighted_score": round(score * weight, 3),
            "rule": profile.get("rule", ""),
        })

    if not contributing or total_weight <= 0:
        return {
            "overall_risk_level": "中風險",
            "overall_risk_score": 2.0,
            "contributing_agents": [],
            "highest_risk_agent": "",
            "calibration_reason": "未能取得 Agent 風險資料，使用中風險作保守 fallback。",
            "safety_override": False,
            "legal_override": False,
        }

    weighted_score = weighted_total / total_weight
    overall = _risk_from_score(weighted_score)

    reasons = [
        f"PM Agent final authority 已按 Agent risk weight 計算加權分數 {weighted_score:.2f}。",
    ]

    if medium_count >= 2 and RISK_SCORE[overall] < 2:
        overall = "中風險"
        reasons.append("多於兩個 Agent 判斷中風險，最終風險至少維持中風險。")

    if safety_override and RISK_SCORE[overall] < 2:
        overall = "中風險"
        reasons.append("Safety Agent 判斷高風險，最終風險不可低於中風險。")
    elif safety_override:
        reasons.append("Safety Agent 高風險已納入最終整合。")

    if legal_override and RISK_SCORE[overall] < 2:
        overall = "中風險"
        reasons.append("HK Legal Layer 判斷高風險，最終風險不可低於中風險。")
    elif legal_override:
        reasons.append("HK Legal Layer 高風險已納入最終整合。")

    if high_with_substantive_issue and weighted_score >= 2.0:
        overall = "高風險"
        reasons.append("高風險 Agent 涉及實質安全 / 法規 / 結構 / 電力 / 消防問題，最終風險升為高風險。")
    elif highest_score == 3 and overall != "高風險":
        reasons.append("偵測到單一高風險訊號，但未有足夠實質重大問題，不自動升至高風險。")

    return {
        "overall_risk_level": overall,
        "overall_risk_score": round(weighted_score, 3),
        "contributing_agents": contributing,
        "highest_risk_agent": highest_agent,
        "calibration_reason": " ".join(reasons),
        "safety_override": safety_override,
        "legal_override": legal_override,
    }

