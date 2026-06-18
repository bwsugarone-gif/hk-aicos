# -*- coding: utf-8 -*-
"""
utils/evidence_confidence.py
HK-AICOS Phase 3.2D — Evidence Confidence Layer

Reduces AI over-speculation, false violation judgements, and unjustified
risk escalation by classifying evidence and filtering hallucination patterns.

Evidence classes:
  confirmed          — explicitly visible or written in the source material
  uncertain          — signs present but cannot be fully confirmed
  missing_evidence   — information needed but not available
  prohibited_inference — cannot be inferred from image/text alone

Risk fallback rules:
  confirmed high risk   → may raise to high risk
  uncertain high risk   → cap at medium risk (unless multiple evidence)
  missing evidence      → list as "needs supplementary data" only
  prohibited inference  → excluded from final conclusion
"""

import re
import sys
from typing import Optional

# ── Evidence classification constants ────────────────────────────────────────

CONFIRMED          = "confirmed"
UNCERTAIN          = "uncertain"
MISSING_EVIDENCE   = "missing_evidence"
PROHIBITED_INFERENCE = "prohibited_inference"

EVIDENCE_LABELS_ZH = {
    CONFIRMED:           "已確認",
    UNCERTAIN:           "未能確認",
    MISSING_EVIDENCE:    "需補充資料",
    PROHIBITED_INFERENCE: "不可推測",
}

# ── Hallucination / over-speculation patterns ─────────────────────────────────
# Maps over-confident phrase → cautious replacement

_OVERCONFIDENT_PATTERNS: list[tuple[str, str]] = [
    # Definitive violation claims
    (r"必定違法",          "可能涉及違規"),
    (r"肯定違法",          "可能涉及違規"),
    (r"已違反",            "可能違反"),
    (r"確定違規",          "可能涉及違規"),
    (r"已違規",            "可能涉及違規"),
    # Definitive enforcement claims
    (r"必定停工",          "如情況屬實，可能需要停工整改"),
    (r"必須停工",          "如情況屬實，建議考慮停工整改"),
    (r"一定停工",          "如情況屬實，可能需要停工整改"),
    (r"必定罰款",          "如情況屬實，可能面臨罰款"),
    (r"一定罰款",          "如情況屬實，可能面臨罰款"),
    (r"肯定罰款",          "如情況屬實，可能面臨罰款"),
    # Definitive absence claims from visual evidence
    (r"沒有安全帶",        "未能確認安全帶，不可直接判定無安全帶"),
    (r"無安全帶",          "未能確認安全帶，不可直接判定無安全帶"),
    (r"一定無安全帶",      "未能確認安全帶，不可直接判定無安全帶"),
    (r"沒有護欄",          "未能確認護欄，不可直接判定無護欄"),
    (r"無護欄",            "未能確認護欄，不可直接判定無護欄"),
    (r"沒有安全網",        "未能確認安全網，不可直接判定無安全網"),
    # Definitive causal claims
    (r"必定導致",          "可能導致"),
    (r"一定導致",          "可能導致"),
    (r"肯定導致",          "可能導致"),
    # Definitive presence claims from unclear images
    (r"明顯沒有",          "未能確認"),
    (r"明顯缺乏",          "未能確認"),
]

# ── Safety / Legal prohibited inference rules ─────────────────────────────────
# These patterns in AI output indicate prohibited inference from visual evidence.

_PROHIBITED_INFERENCE_TRIGGERS: list[str] = [
    "未能確認安全帶",
    "看不清安全帶",
    "圖片不清晰",
    "相片角度",
    "未見護欄",
    "未見安全網",
    "未見",
    "看不到",
    "無法確認",
    "不能確認",
]

# ── Risk fallback rules ───────────────────────────────────────────────────────

_RISK_LEVEL_ORDER = ["低風險", "中風險", "高風險", "極高風險"]


def _risk_index(level: str) -> int:
    try:
        return _RISK_LEVEL_ORDER.index(level)
    except ValueError:
        return 1  # default to 中風險 index


def apply_evidence_risk_fallback(
    risk_level: str,
    evidence_class: str,
    supporting_evidence_count: int = 1,
) -> str:
    """
    Apply evidence-based risk fallback rules.

    Rules:
      confirmed + high/extreme → keep as-is
      uncertain + high/extreme → cap at 中風險 unless ≥3 supporting evidence
      missing_evidence         → cap at 中風險
      prohibited_inference     → cap at 低風險 (excluded from final conclusion)
    """
    idx = _risk_index(risk_level)

    if evidence_class == CONFIRMED:
        return risk_level  # confirmed evidence — no cap

    if evidence_class == UNCERTAIN:
        if idx >= 2 and supporting_evidence_count < 3:
            # uncertain high/extreme → cap at medium
            return "中風險"
        return risk_level

    if evidence_class == MISSING_EVIDENCE:
        # missing evidence → cap at medium
        if idx >= 2:
            return "中風險"
        return risk_level

    if evidence_class == PROHIBITED_INFERENCE:
        # prohibited inference → cap at low
        return "低風險"

    return risk_level


# ── Hallucination filter ──────────────────────────────────────────────────────

def filter_overconfident_language(text: str) -> tuple[str, list[str]]:
    """
    Replace over-confident / hallucination phrases with cautious alternatives.

    Returns:
        (filtered_text, list_of_replacements_made)
    """
    replacements_made: list[str] = []
    result = text

    for pattern, replacement in _OVERCONFIDENT_PATTERNS:
        new_result, count = re.subn(pattern, replacement, result)
        if count > 0:
            replacements_made.append(f"「{pattern}」→「{replacement}」（{count} 處）")
            result = new_result

    return result, replacements_made


# ── Evidence section parser ───────────────────────────────────────────────────

def parse_evidence_sections(analysis_text: str) -> dict:
    """
    Parse structured evidence sections from AI output.

    Looks for sections:
      已確認事項：
      未能確認事項：
      合理懷疑：
      不可推測事項：
      建議補充資料：

    Returns a dict with keys: confirmed, uncertain, suspicion,
    prohibited, supplementary — each a list of strings.
    """
    sections = {
        "confirmed":     [],
        "uncertain":     [],
        "suspicion":     [],
        "prohibited":    [],
        "supplementary": [],
    }

    _section_map = {
        "已確認事項":   "confirmed",
        "未能確認事項": "uncertain",
        "合理懷疑":     "suspicion",
        "不可推測事項": "prohibited",
        "建議補充資料": "supplementary",
    }

    current_key = None
    for line in analysis_text.splitlines():
        stripped = line.strip()
        matched = False
        for header, key in _section_map.items():
            if stripped.startswith(header):
                current_key = key
                matched = True
                # Inline content after the colon
                after = stripped[len(header):].lstrip("：: ").strip()
                if after:
                    sections[current_key].append(after)
                break
        if not matched and current_key and stripped:
            # Continuation line — add to current section
            clean = stripped.lstrip("-•·▪ ").strip()
            if clean:
                sections[current_key].append(clean)

    return sections


# ── Evidence classification helper ───────────────────────────────────────────

def classify_evidence_from_text(analysis_text: str) -> str:
    """
    Heuristically classify the overall evidence level from AI output text.

    Returns one of: confirmed, uncertain, missing_evidence, prohibited_inference
    """
    text_lower = analysis_text.lower()

    # Check for prohibited inference signals
    for trigger in _PROHIBITED_INFERENCE_TRIGGERS:
        if trigger in analysis_text:
            return PROHIBITED_INFERENCE

    # Check for missing evidence signals
    missing_signals = ["需補充", "需要更多資料", "資料不足", "無法評估", "缺乏資料", "沒有足夠"]
    if any(s in analysis_text for s in missing_signals):
        return MISSING_EVIDENCE

    # Check for uncertainty signals
    uncertain_signals = ["可能", "疑似", "懷疑", "未能確認", "不確定", "有跡象"]
    confirmed_signals = ["確認", "明顯", "清晰可見", "已記錄", "文件顯示", "相片顯示"]

    uncertain_count = sum(1 for s in uncertain_signals if s in analysis_text)
    confirmed_count = sum(1 for s in confirmed_signals if s in analysis_text)

    if confirmed_count > uncertain_count:
        return CONFIRMED
    if uncertain_count > 0:
        return UNCERTAIN

    return UNCERTAIN  # default to uncertain when ambiguous


# ── Prompt injection block ────────────────────────────────────────────────────

EVIDENCE_PROMPT_RULES = """
【證據可信度規則 — 必須遵守】

每個 Agent 章節必須按以下結構輸出（使用原文標題，不加 Markdown 符號）：

已確認事項：
（圖片或文字中明確可見或明確寫出的事項）

未能確認事項：
（有跡象但不能完全確認的事項）

合理懷疑：
（基於現有資料的合理推斷，但需進一步確認）

不可推測事項：
（不可單靠圖片或文字推斷的事項，例如：看不清的安全設備）

建議補充資料：
（需要但目前沒有的資料）

【Safety / Legal 特別規則】
- 不可因「未能確認安全帶」直接判定「沒有安全帶」
- 不可因「未見護欄」直接判定「沒有護欄」
- 不可因「可能違規」直接寫成「已違規」
- 不可在無足夠資料下寫「必定停工令」或「必定罰款」
- 不可使用：必定違法、一定罰款、必定停工、一定無安全帶
- 應使用：可能涉及、需進一步確認、如情況屬實，可能需要跟進

【風險判斷規則】
- 已確認高風險 → 可提升高風險
- 未能確認高風險 → 最多中風險（除非有 3 個或以上獨立證據支持）
- 資料不足 → 只列為需補充資料，不可直接判高風險
- 不可推測事項 → 不可進入最終結論
"""


def get_evidence_prompt_injection() -> str:
    """Return the evidence rules block for injection into agent prompts."""
    return EVIDENCE_PROMPT_RULES


# ── Full analysis post-processing ────────────────────────────────────────────

def process_analysis_output(
    analysis_text: str,
    risk_level: str,
) -> dict:
    """
    Full post-processing pipeline for AI analysis output.

    1. Filter overconfident language
    2. Parse evidence sections
    3. Classify overall evidence level
    4. Apply risk fallback

    Returns:
    {
        "filtered_text":        str,
        "replacements_made":    list[str],
        "evidence_sections":    dict,
        "evidence_class":       str,
        "evidence_label_zh":    str,
        "adjusted_risk_level":  str,
        "risk_was_adjusted":    bool,
    }
    """
    # Step 1: filter hallucination language
    filtered_text, replacements = filter_overconfident_language(analysis_text)

    # Step 2: parse structured sections
    evidence_sections = parse_evidence_sections(filtered_text)

    # Step 3: classify evidence
    evidence_class = classify_evidence_from_text(filtered_text)

    # Count supporting evidence items
    supporting_count = (
        len(evidence_sections["confirmed"])
        + len(evidence_sections["suspicion"])
    )

    # Step 4: apply risk fallback
    adjusted_risk = apply_evidence_risk_fallback(
        risk_level, evidence_class, supporting_count
    )
    risk_was_adjusted = adjusted_risk != risk_level

    return {
        "filtered_text":       filtered_text,
        "replacements_made":   replacements,
        "evidence_sections":   evidence_sections,
        "evidence_class":      evidence_class,
        "evidence_label_zh":   EVIDENCE_LABELS_ZH.get(evidence_class, evidence_class),
        "adjusted_risk_level": adjusted_risk,
        "risk_was_adjusted":   risk_was_adjusted,
    }
