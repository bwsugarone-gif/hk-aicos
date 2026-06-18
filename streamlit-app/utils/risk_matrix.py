# -*- coding: utf-8 -*-
"""
utils/risk_matrix.py
HK-AICOS Phase 3.2B.1 — Risk Score Matrix, OCR Noise Filter, Duplicate Merge

Score-based risk calculation:
  0–15   → 低風險
  16–35  → 中風險
  36–60  → 高風險
  61+    → 極高風險

Confidence scoring: each detected issue carries a confidence 0.0–1.0.
"""

import re
from typing import Any

# ── Risk Score Matrix ─────────────────────────────────────────────────────────
# Each entry: (score, confidence, category, label_zh)

RISK_ITEMS = [
    # ── Critical (score 50–70) ────────────────────────────────────────────────
    (70, 0.95, "critical", "live electrical exposed",
     ["live wire", "exposed electrical", "裸露電線", "帶電", "電擊", "electrocution"]),
    (65, 0.95, "critical", "work at height no harness",
     ["no harness", "without harness", "無安全帶", "未佩戴安全帶", "高空無保護"]),
    (60, 0.92, "critical", "open edge no barrier",
     ["open edge", "no barrier", "no guard rail", "無欄杆", "臨邊無防護", "open void"]),
    (55, 0.90, "critical", "structural collapse risk",
     ["collapse", "倒塌", "structural failure", "結構失效", "unstable structure", "結構不穩"]),
    (55, 0.90, "critical", "fire hazard",
     ["fire hazard", "fire risk", "火警", "火災風險", "flammable material exposed"]),
    (50, 0.88, "critical", "confined space no permit",
     ["confined space", "密閉空間", "no permit to work", "無工作許可"]),

    # ── High (score 25–40) ────────────────────────────────────────────────────
    (40, 0.85, "high", "unsafe scaffold",
     ["unsafe scaffold", "不安全棚架", "scaffold defect", "棚架缺陷", "scaffold collapse"]),
    (35, 0.82, "high", "missing warning sign",
     ["missing warning", "no warning sign", "缺少警告標誌", "無警告牌", "no safety sign"]),
    (35, 0.80, "high", "blocked escape route",
     ["blocked escape", "blocked exit", "堵塞逃生", "逃生路線受阻", "emergency exit blocked"]),
    (30, 0.78, "high", "PPE not worn",
     ["no helmet", "no PPE", "未戴安全帽", "無個人防護", "PPE not worn", "without safety equipment"]),
    (30, 0.78, "high", "chemical / hazardous material",
     ["chemical spill", "hazardous material", "化學品", "危險品", "toxic", "有毒"]),
    (28, 0.75, "high", "working at height risk",
     ["working at height", "高空作業", "fall risk", "墮落風險", "height work"]),
    (25, 0.72, "high", "heavy lifting risk",
     ["crane risk", "lifting risk", "吊運風險", "重物吊運", "overhead load"]),

    # ── Medium (score 8–15) ───────────────────────────────────────────────────
    (15, 0.70, "medium", "wet / slippery floor",
     ["wet floor", "slippery", "濕滑地面", "地面濕滑", "slip hazard"]),
    (12, 0.65, "medium", "material scattered",
     ["material scattered", "物料散亂", "debris on floor", "雜物", "cluttered"]),
    (10, 0.62, "medium", "poor housekeeping",
     ["poor housekeeping", "環境雜亂", "untidy site", "工地雜亂"]),
    (10, 0.60, "medium", "inadequate lighting",
     ["poor lighting", "inadequate lighting", "光線不足", "照明不足"]),
    (8, 0.58, "medium", "missing documentation",
     ["missing document", "no record", "缺少文件", "無記錄", "documentation missing"]),

    # ── Low (score 2–5) ───────────────────────────────────────────────────────
    (5, 0.50, "low", "minor debris",
     ["minor debris", "輕微雜物", "small obstruction"]),
    (3, 0.45, "low", "temporary obstruction",
     ["temporary obstruction", "臨時阻礙", "minor blockage"]),
    (2, 0.40, "low", "general untidiness",
     ["general untidy", "一般雜亂", "minor housekeeping"]),
]

# ── OCR Noise Patterns to Ignore ─────────────────────────────────────────────
# These are WhatsApp / messaging app artefacts that carry no engineering meaning

_OCR_NOISE_PATTERNS = [
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"\b(星期[一二三四五六日])\b",
    r"\b\d{1,2}:\d{2}\s*(am|pm|上午|下午)?\b",
    r"\b(已讀|read|delivered|sent)\b",
    r"\b(voice message|語音訊息|voice note)\b",
    r"\b(forwarded|已轉發|轉發)\b",
    r"\b(sticker|貼圖|emoji)\b",
    r"\b(typing|正在輸入)\b",
    r"\b(online|離線|last seen)\b",
    r"[\U0001F300-\U0001FFFF]",   # emoji range
    r"\b(tap to retry|重試)\b",
    r"\b(photo|video|document)\s*\d*\b",
    r"\b(whatsapp|telegram|wechat|微信|line)\b",
    r"^\s*\d{1,2}/\d{1,2}\s*$",  # bare date like "5/18"
    r"^\s*[.…]+\s*$",             # ellipsis-only lines
]

_NOISE_RE = re.compile(
    "|".join(_OCR_NOISE_PATTERNS),
    flags=re.IGNORECASE | re.UNICODE,
)


def filter_ocr_noise(text: str) -> str:
    """
    Remove WhatsApp / messaging artefacts from OCR text.
    Returns cleaned text with only engineering-relevant content.
    """
    if not text:
        return ""
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if _NOISE_RE.search(stripped):
            continue
        cleaned.append(stripped)
    return "\n".join(cleaned)


# ── Risk Score Calculation ────────────────────────────────────────────────────

def _text_lower(text: str) -> str:
    return str(text or "").lower()


def score_text(text: str) -> dict:
    """
    Scan text for risk keywords and return:
    {
        "total_score": int,
        "risk_level": str,
        "detected_issues": [{"label": str, "score": int, "confidence": float, "category": str}],
        "confidence": float,   # overall confidence (avg of detected)
    }
    """
    cleaned = filter_ocr_noise(text)
    lowered = _text_lower(cleaned)

    detected = []
    seen_labels = set()

    for score, confidence, category, label, keywords in RISK_ITEMS:
        for kw in keywords:
            if kw.lower() in lowered:
                if label not in seen_labels:
                    detected.append({
                        "label": label,
                        "score": score,
                        "confidence": confidence,
                        "category": category,
                    })
                    seen_labels.add(label)
                break

    total = sum(d["score"] for d in detected)
    overall_confidence = (
        sum(d["confidence"] for d in detected) / len(detected)
        if detected else 0.5
    )

    return {
        "total_score": total,
        "risk_level": score_to_risk_level(total),
        "detected_issues": detected,
        "confidence": round(overall_confidence, 2),
    }


def score_to_risk_level(score: int) -> str:
    if score >= 61:
        return "極高風險"
    if score >= 36:
        return "高風險"
    if score >= 16:
        return "中風險"
    return "低風險"


def risk_level_to_score(risk_level: str) -> int:
    """Map a text risk level to a representative score for blending."""
    mapping = {
        "極高風險": 65,
        "高風險": 45,
        "中風險": 25,
        "低風險": 8,
    }
    return mapping.get(str(risk_level or "").strip(), 25)


# ── Duplicate Risk Merge ──────────────────────────────────────────────────────
# Synonyms that represent the same underlying risk

_DUPLICATE_GROUPS = [
    {"open edge", "no barrier", "no guard rail", "fall risk", "臨邊無防護", "墮落風險"},
    {"no harness", "without harness", "無安全帶", "未佩戴安全帶"},
    {"unsafe scaffold", "scaffold defect", "棚架缺陷"},
    {"no helmet", "no PPE", "未戴安全帽", "無個人防護"},
    {"missing warning", "no warning sign", "缺少警告標誌", "無警告牌"},
    {"wet floor", "slippery", "濕滑地面", "slip hazard"},
    {"material scattered", "物料散亂", "debris on floor", "雜物"},
    {"fire hazard", "fire risk", "火警", "火災風險"},
    {"live wire", "exposed electrical", "裸露電線", "帶電"},
    {"collapse", "倒塌", "structural failure", "結構失效"},
]


def merge_duplicate_risks(issues: list[dict]) -> list[dict]:
    """
    Given a list of detected issue dicts (each with 'label'),
    merge duplicates that belong to the same synonym group.
    Returns deduplicated list, keeping the highest-score entry per group.
    """
    if not issues:
        return []

    merged = []
    used_indices = set()

    for i, issue in enumerate(issues):
        if i in used_indices:
            continue
        label_i = issue.get("label", "").lower()
        group_match = None
        for group in _DUPLICATE_GROUPS:
            if any(g.lower() in label_i or label_i in g.lower() for g in group):
                group_match = group
                break

        if group_match is None:
            merged.append(issue)
            used_indices.add(i)
            continue

        # Find all issues in the same group
        group_issues = [issue]
        used_indices.add(i)
        for j, other in enumerate(issues):
            if j in used_indices:
                continue
            label_j = other.get("label", "").lower()
            if any(g.lower() in label_j or label_j in g.lower() for g in group_match):
                group_issues.append(other)
                used_indices.add(j)

        # Keep highest score
        best = max(group_issues, key=lambda x: x.get("score", 0))
        merged.append(best)

    return merged


# ── Agent-level Score Calculation ─────────────────────────────────────────────

AGENT_WEIGHTS = {
    "safety":      1.3,
    "hk_legal":    1.5,
    "legal":       1.5,
    "pm":          1.0,
    "foreman":     0.8,
    "qs":          0.9,
    "engineering": 1.2,
    "accounting":  0.9,
    "material":    0.8,
    "drafting":    1.0,
    "surveying":   1.1,
    "translator":  0.6,
}


def calculate_weighted_score(agent_scores: dict[str, int]) -> dict:
    """
    agent_scores: {agent_id: raw_score}
    Returns weighted total score and final risk level.
    """
    if not agent_scores:
        return {"weighted_score": 0, "risk_level": "低風險", "agent_breakdown": {}}

    total_weighted = 0.0
    total_weight = 0.0
    breakdown = {}

    for agent_id, raw_score in agent_scores.items():
        weight = AGENT_WEIGHTS.get(agent_id, 1.0)
        weighted = raw_score * weight
        total_weighted += weighted
        total_weight += weight
        breakdown[agent_id] = {
            "raw_score": raw_score,
            "weight": weight,
            "weighted_score": round(weighted, 1),
            "risk_level": score_to_risk_level(raw_score),
        }

    avg_weighted = total_weighted / total_weight if total_weight > 0 else 0
    return {
        "weighted_score": round(avg_weighted, 1),
        "risk_level": score_to_risk_level(int(avg_weighted)),
        "agent_breakdown": breakdown,
    }
