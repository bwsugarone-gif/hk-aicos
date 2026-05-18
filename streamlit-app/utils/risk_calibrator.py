# -*- coding: utf-8 -*-
"""
utils/risk_calibrator.py
HK-AICOS Phase 3.2B.1 — Agent risk calibration layer (score-based).

Score thresholds:
  0–15   → 低風險
  16–35  → 中風險
  36–60  → 高風險
  61+    → 極高風險

Agent personality weights are defined in risk_matrix.AGENT_WEIGHTS.
"""

import re
from typing import Any

from utils.risk_matrix import (
    score_text,
    score_to_risk_level,
    risk_level_to_score,
    merge_duplicate_risks,
    filter_ocr_noise,
    AGENT_WEIGHTS,
)


# ── Legacy score mapping (kept for backward compat) ───────────────────────────
RISK_SCORE = {
    "低風險": 1,
    "中風險": 2,
    "高風險": 3,
    "極高風險": 4,
}

SCORE_RISK = {
    1: "低風險",
    2: "中風險",
    3: "高風險",
    4: "極高風險",
}

# ── Agent profiles (personality + weight) ─────────────────────────────────────
AGENT_RISK_PROFILES = {
    "safety": {
        "name": "Safety Agent",
        "style": "保守",
        "weight": AGENT_WEIGHTS["safety"],
        "rule": "safety high risk cannot be downgraded below medium",
    },
    "hk_legal": {
        "name": "HK Legal Layer",
        "style": "超保守",
        "weight": AGENT_WEIGHTS["hk_legal"],
        "rule": "legal / compliance issue increases final risk",
    },
    "legal": {
        "name": "HK Legal Layer",
        "style": "超保守",
        "weight": AGENT_WEIGHTS["legal"],
        "rule": "legal / compliance issue increases final risk",
    },
    "pm": {
        "name": "PM Agent",
        "style": "平衡",
        "weight": AGENT_WEIGHTS["pm"],
        "rule": "final coordinator",
    },
    "qs": {
        "name": "QS Agent",
        "style": "成本導向",
        "weight": AGENT_WEIGHTS["qs"],
        "rule": "cost risk affects commercial risk",
    },
    "foreman": {
        "name": "Foreman Agent",
        "style": "現場實務",
        "weight": AGENT_WEIGHTS["foreman"],
        "rule": "site practicality affects execution risk",
    },
    "engineering": {
        "name": "Engineering Agent",
        "style": "技術實務",
        "weight": AGENT_WEIGHTS["engineering"],
        "rule": "technical practicality affects engineering risk",
    },
    "accounting": {
        "name": "Accounting Agent",
        "style": "財務謹慎",
        "weight": AGENT_WEIGHTS["accounting"],
        "rule": "financial risk affects commercial risk",
    },
    "material": {
        "name": "Material Agent",
        "style": "供應鏈實務",
        "weight": AGENT_WEIGHTS["material"],
        "rule": "supply chain practicality affects delivery risk",
    },
    "drafting": {
        "name": "Drafting Agent",
        "style": "圖則細節",
        "weight": AGENT_WEIGHTS["drafting"],
        "rule": "drawing details affect coordination risk",
    },
    "surveying": {
        "name": "Surveying Agent",
        "style": "精準測量",
        "weight": AGENT_WEIGHTS["surveying"],
        "rule": "measurement accuracy affects site risk",
    },
    "translator": {
        "name": "Translator Agent",
        "style": "文件準確",
        "weight": AGENT_WEIGHTS["translator"],
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
    if "極高" in raw or "critical" in raw.lower():
        return "極高風險"
    if "高" in raw or "緊急" in raw:
        return "高風險"
    if "低" in raw:
        return "低風險"
    if "中" in raw:
        return "中風險"
    return "中風險"


def _risk_from_text(text: str) -> tuple[str, int, float]:
    """
    Returns (risk_level, raw_score, confidence) by running the score matrix
    against the text, then falling back to keyword counting.
    """
    cleaned = filter_ocr_noise(str(text or ""))
    result = score_text(cleaned)

    # If score matrix found something meaningful, use it
    if result["total_score"] > 0:
        return result["risk_level"], result["total_score"], result["confidence"]

    # Fallback: keyword counting (legacy behaviour)
    value = cleaned
    high_hits = len(re.findall(r"高風險|極高風險|重大|嚴重|停工|違規|危險|致命", value, flags=re.I))
    medium_hits = len(re.findall(r"中風險|需跟進|需要跟進|注意|可能|需確認", value, flags=re.I))
    low_hits = len(re.findall(r"低風險|輕微|一般|可接受|無明顯", value, flags=re.I))
    if high_hits:
        return "高風險", 45, 0.70
    if medium_hits:
        return "中風險", 25, 0.60
    if low_hits:
        return "低風險", 8, 0.50
    return "中風險", 25, 0.50


def _extract_risk(agent_result: Any) -> tuple[str, str, int, float]:
    """Returns (risk_level, output_text, raw_score, confidence)."""
    if isinstance(agent_result, dict):
        risk = (
            agent_result.get("risk_level")
            or agent_result.get("calibrated_risk_level")
            or agent_result.get("overall_risk_level")
        )
        output = str(
            agent_result.get("output")
            or agent_result.get("text")
            or agent_result.get("summary")
            or ""
        )
        if risk:
            normalised = _normalise_risk(risk)
            score = risk_level_to_score(normalised)
            return normalised, output, score, 0.70
        level, score, conf = _risk_from_text(output)
        return level, output, score, conf

    risk = getattr(agent_result, "risk_level", None)
    output = str(
        getattr(agent_result, "output", "")
        or getattr(agent_result, "text", "")
        or agent_result
        or ""
    )
    if risk:
        normalised = _normalise_risk(risk)
        score = risk_level_to_score(normalised)
        return normalised, output, score, 0.70
    level, score, conf = _risk_from_text(output)
    return level, output, score, conf


def _has_substantive_high_issue(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(keyword.lower() in lowered for keyword in _HIGH_SUBSTANTIVE_KEYWORDS)


def calculate_overall_project_risk(agent_results, selected_agents):
    """
    Calculate calibrated overall project risk from agent-level results.
    Uses score-based matrix (0–15/16–35/36–60/61+) with agent personality weights.

    Returns:
    - overall_risk_level
    - overall_risk_score        (0–100 scale, weighted average)
    - contributing_agents
    - highest_risk_agent
    - calibration_reason
    - safety_override
    - legal_override
    - agent_scores              {agent_id: {"raw_score", "weighted_score", "risk_level", "confidence"}}
    - detected_issues           merged list of detected risk issues
    """
    selected = [_normalise_agent_id(agent_id) for agent_id in (selected_agents or [])]
    if not selected:
        selected = [_normalise_agent_id(agent_id) for agent_id in (agent_results or {}).keys()]

    contributing = []
    all_detected_issues = []
    weighted_total = 0.0
    total_weight = 0.0
    highest_agent = ""
    highest_score = 0
    medium_count = 0
    high_with_substantive_issue = False
    safety_override = False
    legal_override = False
    agent_scores = {}

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

        risk_level, output, raw_score, confidence = _extract_risk(raw_result)
        weight = float(profile.get("weight", 1.0))

        # Run score matrix on output text for detected issues
        cleaned_output = filter_ocr_noise(output)
        matrix_result = score_text(cleaned_output)
        agent_detected = merge_duplicate_risks(matrix_result.get("detected_issues", []))
        all_detected_issues.extend(agent_detected)

        # Use matrix score if it's more informative than the text-level risk
        effective_score = max(raw_score, matrix_result["total_score"])
        effective_risk = score_to_risk_level(effective_score)

        weighted_total += effective_score * weight
        total_weight += weight

        if RISK_SCORE.get(effective_risk, 2) == 2:
            medium_count += 1
        if effective_score > highest_score:
            highest_score = effective_score
            highest_agent = profile.get("name", agent_id)
        if agent_id == "safety" and RISK_SCORE.get(effective_risk, 0) >= 3:
            safety_override = True
        if agent_id in ("hk_legal", "legal") and RISK_SCORE.get(effective_risk, 0) >= 3:
            legal_override = True
        if RISK_SCORE.get(effective_risk, 0) >= 3 and _has_substantive_high_issue(output):
            high_with_substantive_issue = True

        agent_scores[agent_id] = {
            "raw_score": effective_score,
            "weighted_score": round(effective_score * weight, 1),
            "risk_level": effective_risk,
            "confidence": round(confidence, 2),
        }

        contributing.append({
            "agent_id": agent_id,
            "agent_name": profile.get("name", agent_id),
            "style": profile.get("style", ""),
            "weight": weight,
            "risk_level": effective_risk,
            "risk_score": effective_score,
            "weighted_score": round(effective_score * weight, 1),
            "confidence": round(confidence, 2),
            "rule": profile.get("rule", ""),
        })

    if not contributing or total_weight <= 0:
        return {
            "overall_risk_level": "中風險",
            "overall_risk_score": 25.0,
            "contributing_agents": [],
            "highest_risk_agent": "",
            "calibration_reason": "未能取得 Agent 風險資料，使用中風險作保守 fallback。",
            "safety_override": False,
            "legal_override": False,
            "agent_scores": {},
            "detected_issues": [],
        }

    weighted_avg = weighted_total / total_weight
    overall = score_to_risk_level(int(weighted_avg))

    # Merge all detected issues across agents
    merged_issues = merge_duplicate_risks(all_detected_issues)

    reasons = [
        f"加權風險分數：{weighted_avg:.1f}（各 Agent 按職責權重計算）。",
    ]

    # Guard rails — prevent over-inflation
    if medium_count >= 2 and RISK_SCORE.get(overall, 2) < 2:
        overall = "中風險"
        reasons.append("多於兩個 Agent 判斷中風險，最終風險至少維持中風險。")

    if safety_override and RISK_SCORE.get(overall, 2) < 2:
        overall = "中風險"
        reasons.append("Safety Agent 判斷高風險，最終風險不可低於中風險。")
    elif safety_override:
        reasons.append("Safety Agent 高風險已納入最終整合。")

    if legal_override and RISK_SCORE.get(overall, 2) < 2:
        overall = "中風險"
        reasons.append("HK Legal Layer 判斷高風險，最終風險不可低於中風險。")
    elif legal_override:
        reasons.append("HK Legal Layer 高風險已納入最終整合。")

    # Only escalate to 高風險 if there is a substantive issue AND score is high enough
    if high_with_substantive_issue and weighted_avg >= 36:
        overall = "高風險"
        reasons.append("偵測到實質安全 / 法規 / 結構問題，風險升為高風險。")
    elif highest_score >= 36 and overall not in ("高風險", "極高風險"):
        reasons.append("偵測到單一高風險訊號，但整體加權分數未達高風險門檻，維持現有評級。")

    # Cap: only go to 極高風險 if weighted avg >= 61
    if overall == "極高風險" and weighted_avg < 61:
        overall = "高風險"
        reasons.append("加權分數未達極高風險門檻（61），降回高風險。")

    return {
        "overall_risk_level": overall,
        "overall_risk_score": round(weighted_avg, 1),
        "contributing_agents": contributing,
        "highest_risk_agent": highest_agent,
        "calibration_reason": " ".join(reasons),
        "safety_override": safety_override,
        "legal_override": legal_override,
        "agent_scores": agent_scores,
        "detected_issues": merged_issues,
    }
