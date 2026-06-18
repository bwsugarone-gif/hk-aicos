# -*- coding: utf-8 -*-
"""
HK-AICOS Phase 3.3A - Realtime Site Logic Engine.

Rule-based site logic only. This layer does not estimate programme duration;
it flags sequence, trade-conflict, and site-flow concerns when text evidence is
present in the current report, OCR, question, or site context.
"""

from __future__ import annotations

import re
from typing import Iterable


INSUFFICIENT_TIMELINE_MESSAGE = "目前資料不足以判斷實際工期狀況。"


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _contains(text: str, keywords: Iterable[str]) -> bool:
    lower = text.lower()
    return any(str(keyword).lower() in lower for keyword in keywords)


def _evidence(text: str, keywords: Iterable[str]) -> list:
    lower = text.lower()
    return [keyword for keyword in keywords if str(keyword).lower() in lower]


SEQUENCE_RULES = [
    {
        "id": "cable_tray_before_boarding",
        "title": "Cable tray 未完成不應封板",
        "prerequisite": ["cable tray", "電纜橋架", "線槽", "橋架"],
        "blocked_work": ["封板", "封牆", "ceiling board", "boarding", "close ceiling"],
        "finding": "偵測到 cable tray / 線槽 與封板工序同時出現，需確認 cable tray 已完成及驗收後才可封板。",
    },
    {
        "id": "waterproof_before_tiles",
        "title": "Waterproof 未完成不應鋪地磚",
        "prerequisite": ["waterproof", "waterproofing", "防水", "防水層"],
        "blocked_work": ["鋪地磚", "地磚", "tile", "tiling", "floor tile"],
        "finding": "偵測到 waterproof / 防水 與鋪磚工序同時出現，需確認防水完成及測試合格後才可鋪地磚。",
    },
    {
        "id": "testing_before_handover",
        "title": "Testing 未完成不應交場",
        "prerequisite": ["testing", "test", "測試", "檢測", "commissioning"],
        "blocked_work": ["交場", "handover", "交付", "移交"],
        "finding": "偵測到 testing / 測試 與交場同時出現，需確認測試完成才可進入交場。",
    },
    {
        "id": "scaffold_before_finishing",
        "title": "未拆棚不應進入 finishing",
        "prerequisite": ["未拆棚", "棚架未拆", "scaffold", "scaffolding"],
        "blocked_work": ["finishing", "油漆", "飾面", "收口", "裝修"],
        "finding": "偵測到棚架未拆或 scaffold 與 finishing 工序同時出現，需確認是否阻礙飾面及收口。",
    },
    {
        "id": "em_rough_in_before_ceiling",
        "title": "E&M rough-in 未完成不應封天花",
        "prerequisite": ["E&M rough-in", "em rough-in", "rough in", "機電預埋", "機電粗裝", "喉管", "線管"],
        "blocked_work": ["封天花", "ceiling close", "close ceiling", "假天花", "天花板"],
        "finding": "偵測到 E&M rough-in / 機電粗裝 與封天花同時出現，需確認機電粗裝及檢查完成後才可封天花。",
    },
]


TRADE_CONFLICT_RULES = [
    {
        "id": "painting_vs_welding",
        "title": "油漆 vs 焊接",
        "trade_a": ["油漆", "painting", "paint"],
        "trade_b": ["焊接", "welding", "hot work", "燒焊"],
        "finding": "油漆與焊接同場可能造成火警、氣味及表面污染風險，需分區或分時段處理。",
    },
    {
        "id": "lifting_vs_work_at_height",
        "title": "吊運 vs 高空工作",
        "trade_a": ["吊運", "lifting", "crane", "吊機"],
        "trade_b": ["高空工作", "work at height", "working at height", "棚架", "scaffold"],
        "finding": "吊運與高空工作同時進行會增加墮物及高空作業風險，需設吊運禁區及工序隔離。",
    },
    {
        "id": "waterproof_vs_em",
        "title": "防水 vs 機電施工",
        "trade_a": ["防水", "waterproof", "waterproofing"],
        "trade_b": ["機電", "E&M", "electrical", "喉管", "線管", "cable"],
        "finding": "防水與機電施工互相干擾，穿孔、開坑或後續改動可能破壞防水層。",
    },
    {
        "id": "cleaning_vs_demolition",
        "title": "清潔 vs 大型拆卸",
        "trade_a": ["清潔", "cleaning", "final clean"],
        "trade_b": ["大型拆卸", "拆卸", "demolition", "breaking"],
        "finding": "清潔與大型拆卸同場不合理，拆卸粉塵及廢料會令清潔工序失效並阻礙交場。",
    },
]


FLOW_RULES = [
    {
        "id": "cluttered_site",
        "title": "工地過度凌亂",
        "keywords": ["凌亂", "雜亂", "混亂", "clutter", "messy", "poor housekeeping", "housekeeping"],
        "finding": "現場有凌亂或 housekeeping 問題，可能影響施工 flow 及安全通道。",
    },
    {
        "id": "blocked_materials",
        "title": "材料阻路",
        "keywords": ["材料阻路", "阻塞通道", "blocked access", "blocked escape", "blocked walkway", "走火通道", "逃生通道"],
        "finding": "材料或雜物可能阻塞通道，需即時清理以保持現場 flow 及逃生路線。",
    },
    {
        "id": "out_of_sequence",
        "title": "工序不合理",
        "keywords": ["工序不合理", "out of sequence", "sequence issue", "未完成先做", "返工"],
        "finding": "文字證據顯示工序可能 out of sequence，需由 PM / Foreman 確認現場排序。",
    },
]


def analyse_site_logic(
    text: str = "",
    question: str = "",
    ocr_text: str = "",
    site_context: dict | None = None,
) -> dict:
    """Analyse current-session site logic with explicit evidence only."""
    site_context = site_context or {}
    context_bits = []
    if site_context:
        context_bits.extend(site_context.get("environment_labels_zh", []) or [])
        context_bits.extend(site_context.get("site_constraints", []) or [])
        context_bits.extend(site_context.get("risk_modifier", {}).get("risk_notes", []) or [])

    combined = _norm("\n".join([text or "", question or "", ocr_text or "", "\n".join(map(str, context_bits))]))
    if not combined:
        return {
            "context_available": False,
            "sequence_findings": [],
            "trade_conflicts": [],
            "flow_findings": [],
            "blocked_works": [],
            "delay_concern": "insufficient_data",
            "summary": "未有足夠現場資料進行工序合理性分析。",
            "pm_summary": INSUFFICIENT_TIMELINE_MESSAGE,
        }

    sequence_findings = []
    for rule in SEQUENCE_RULES:
        prereq = _evidence(combined, rule["prerequisite"])
        blocked = _evidence(combined, rule["blocked_work"])
        if prereq and blocked:
            sequence_findings.append({
                "rule_id": rule["id"],
                "title": rule["title"],
                "finding": rule["finding"],
                "evidence": prereq[:3] + blocked[:3],
                "severity": "warning",
            })

    trade_conflicts = []
    for rule in TRADE_CONFLICT_RULES:
        trade_a = _evidence(combined, rule["trade_a"])
        trade_b = _evidence(combined, rule["trade_b"])
        if trade_a and trade_b:
            trade_conflicts.append({
                "rule_id": rule["id"],
                "title": rule["title"],
                "finding": rule["finding"],
                "evidence": trade_a[:3] + trade_b[:3],
                "severity": "warning",
            })

    flow_findings = []
    for rule in FLOW_RULES:
        evidence = _evidence(combined, rule["keywords"])
        if evidence:
            flow_findings.append({
                "rule_id": rule["id"],
                "title": rule["title"],
                "finding": rule["finding"],
                "evidence": evidence[:5],
                "severity": "warning",
            })

    blocked_works = [
        item["title"]
        for item in sequence_findings + trade_conflicts + flow_findings
    ]

    issue_count = len(sequence_findings) + len(trade_conflicts) + len(flow_findings)
    if issue_count >= 3:
        delay_concern = "high"
    elif issue_count >= 1:
        delay_concern = "watch"
    else:
        delay_concern = "low"

    if issue_count:
        summary = f"偵測到 {issue_count} 項工序/工種/現場 flow 關注點，需由 PM / Foreman 核實現場安排。"
        pm_summary = "現場可能存在工序阻塞或工種衝突，PM Agent 應跟進分區、分時段及整改責任。"
    else:
        summary = "未從現有文字證據偵測到明確工序衝突；仍需以現場最新紀錄確認。"
        pm_summary = "目前未見明確工序阻塞證據。"

    return {
        "context_available": True,
        "sequence_findings": sequence_findings,
        "trade_conflicts": trade_conflicts,
        "flow_findings": flow_findings,
        "blocked_works": blocked_works,
        "delay_concern": delay_concern,
        "summary": summary,
        "pm_summary": pm_summary,
    }


def format_site_logic_for_report(result: dict) -> str:
    """Compact human-readable block for prompts, reports, and tests."""
    if not result or not result.get("context_available"):
        return "工序合理性分析\n- 未有足夠現場資料進行工序合理性分析。"

    lines = ["工序合理性分析", f"- 總結：{result.get('summary', '')}"]
    for label, key in [
        ("工程序列", "sequence_findings"),
        ("工種衝突", "trade_conflicts"),
        ("現場 flow", "flow_findings"),
    ]:
        items = result.get(key, []) or []
        if items:
            lines.append(f"- {label}：")
            for item in items[:5]:
                evidence = "、".join(map(str, item.get("evidence", [])))
                lines.append(f"  - {item.get('title')}: {item.get('finding')} Evidence: {evidence}")
    if not result.get("blocked_works"):
        lines.append("- 暫未偵測到明確阻塞工序。")
    return "\n".join(lines)
