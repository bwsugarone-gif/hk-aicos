"""
utils/repeated_issue_detector.py
HK-AICOS Phase 3.3 — Repeated Issue Detection

Detects repeated risks across sessions for the same project_ref
using normalized keyword synonym groups, not full-text matching.

Buildway Tech (HK) Limited
"""

from __future__ import annotations
import re
from typing import Optional
from utils.project_manager import load_project

# ── Synonym groups ────────────────────────────────────────────────────────────
# Each group is a set of normalized keywords that represent the same risk.
# Add more groups as needed.
SYNONYM_GROUPS: list[set[str]] = [
    # Open edge / fall hazard
    {
        "open edge", "開口", "邊位未封", "臨邊未封", "未設護欄",
        "高空墮下", "墮下風險", "邊緣未保護", "臨邊", "open side",
        "unprotected edge", "fall hazard", "fall risk",
    },
    # Scaffolding
    {
        "棚架", "scaffold", "scaffolding", "棚架不穩", "棚架未固定",
        "棚架缺陷", "棚架問題", "棚架風險",
    },
    # PPE
    {
        "ppe", "個人防護裝備", "安全帽", "helmet", "hard hat",
        "安全帶", "harness", "safety belt", "手套", "gloves",
        "護目鏡", "goggles", "未佩戴", "沒有佩戴", "缺少防護",
    },
    # Electrical hazard
    {
        "電氣危險", "觸電", "electrical hazard", "electric shock",
        "裸露電線", "exposed wire", "臨電", "臨時電力", "電線",
        "漏電", "電力危險",
    },
    # Fire hazard
    {
        "火警", "fire", "fire hazard", "易燃物", "flammable",
        "消防", "fire safety", "滅火器", "fire extinguisher",
        "防火", "fire prevention",
    },
    # Working at height
    {
        "高空作業", "working at height", "高處工作", "高空工作",
        "升降台", "aerial platform", "吊籠", "gondola",
        "高空墮下", "fall from height",
    },
    # Material obstruction
    {
        "材料阻塞", "material obstruction", "通道阻塞", "blocked passage",
        "堆放不當", "improper storage", "材料堆放", "material storage",
        "阻塞通道", "blocked access",
    },
    # Confined space
    {
        "密閉空間", "confined space", "缺氧", "oxygen deficiency",
        "有毒氣體", "toxic gas", "confined area",
    },
    # Lifting / crane
    {
        "吊運", "lifting", "crane", "吊機", "吊重", "overhead lifting",
        "吊運危險", "lifting hazard", "吊運安全",
    },
    # Excavation
    {
        "挖掘", "excavation", "坑邊", "trench", "泥土崩塌",
        "soil collapse", "挖掘危險", "excavation hazard",
    },
    # E&M coordination
    {
        "e&m", "em", "機電", "機電未完成", "e&m 未完成",
        "機電工程", "electrical and mechanical", "em coordination",
    },
    # Waterproofing
    {
        "防水", "waterproofing", "防水未完成", "waterproofing incomplete",
        "防水層", "waterproof membrane",
    },
    # Plastering / tiling sequence
    {
        "泥水", "plastering", "批盪", "鋪磚", "tiling",
        "泥水未完成", "plastering incomplete",
    },
]

# Build a flat lookup: normalized_keyword → group_index
_KEYWORD_TO_GROUP: dict[str, int] = {}
for _gi, _group in enumerate(SYNONYM_GROUPS):
    for _kw in _group:
        _KEYWORD_TO_GROUP[_kw.lower().strip()] = _gi


def _normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"[，。！？、；：「」『』【】《》〈〉\(\)\[\]\{\}]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_risk_groups(text: str) -> set[int]:
    """
    Return the set of synonym group indices found in text.
    Uses substring matching against all known keywords.
    """
    norm = _normalize(text)
    found: set[int] = set()
    for kw, gi in _KEYWORD_TO_GROUP.items():
        if kw in norm:
            found.add(gi)
    return found


def detect_repeated_issues(
    project_ref: str,
    current_text: str,
    current_session_id: str,
    analysis_type: str = "",
) -> list[dict]:
    """
    Compare current analysis text against all previous sessions for the same
    project_ref. Return a list of repeated issue records.

    Each record:
    {
        "group_index": int,
        "group_keywords": list[str],
        "repeat_count": int,
        "first_seen": str (ISO date),
        "last_seen": str (ISO date),
        "sessions": list[str],
    }
    """
    if not project_ref or not current_text:
        return []

    try:
        project_data = load_project(project_ref)
    except Exception:
        return []

    sessions = project_data.get("sessions", []) or []
    # Exclude current session
    past_sessions = [s for s in sessions if s.get("session_id") != current_session_id]
    if not past_sessions:
        return []

    current_groups = extract_risk_groups(current_text)
    if not current_groups:
        return []

    # For each group found in current text, check how many past sessions also had it
    group_hits: dict[int, list[dict]] = {}  # group_index → list of matching sessions
    for session in past_sessions:
        session_text = " ".join([
            session.get("analysis_result", "") or "",
            session.get("summary", "") or "",
            session.get("question", "") or "",
        ])
        session_groups = extract_risk_groups(session_text)
        for gi in current_groups:
            if gi in session_groups:
                if gi not in group_hits:
                    group_hits[gi] = []
                group_hits[gi].append(session)

    results = []
    for gi, matching_sessions in group_hits.items():
        if not matching_sessions:
            continue
        all_times = sorted(
            s.get("time", "") or s.get("date", "") or ""
            for s in matching_sessions
            if s.get("time") or s.get("date")
        )
        first_seen = all_times[0][:10] if all_times else ""
        last_seen = all_times[-1][:10] if all_times else ""
        session_ids = [s.get("session_id", "") for s in matching_sessions]
        group_kws = sorted(SYNONYM_GROUPS[gi])[:5]  # show up to 5 representative keywords

        results.append({
            "group_index": gi,
            "group_keywords": group_kws,
            "repeat_count": len(matching_sessions) + 1,  # +1 for current
            "first_seen": first_seen,
            "last_seen": last_seen,
            "sessions": session_ids,
        })

    return results


def format_repeated_issues_for_report(repeated_issues: list[dict]) -> str:
    """Format repeated issues for display in the report."""
    if not repeated_issues:
        return ""
    lines = []
    for item in repeated_issues:
        kws = "、".join(item["group_keywords"][:3])
        lines.append(
            f"- 重覆風險（第 {item['repeat_count']} 次）：{kws}"
            + (f"  首次：{item['first_seen']}" if item["first_seen"] else "")
        )
    return "\n".join(lines)
