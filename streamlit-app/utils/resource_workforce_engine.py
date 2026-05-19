# -*- coding: utf-8 -*-
"""
HK-AICOS Phase 3.3D - Resource & Workforce Logic Layer.

This module analyses workforce, trade coordination, material, and plant/equipment
issues based on keyword evidence. It does not estimate delay days or make assumptions
without explicit evidence.
"""

from __future__ import annotations

import re
from typing import Iterable


INSUFFICIENT_RESOURCE_MESSAGE = "目前資料不足以確認資源或人手是否足夠。"


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _contains(text: str, keywords: Iterable[str]) -> bool:
    lower = text.lower()
    return any(str(keyword).lower() in lower for keyword in keywords)


def _evidence(text: str, keywords: Iterable[str]) -> list:
    lower = text.lower()
    return [keyword for keyword in keywords if str(keyword).lower() in lower]


WORKFORCE_RULES = [
    {
        "id": "worker_shortage",
        "title": "人手不足",
        "keywords": ["人手不足", "工人不足", "worker shortage", "manpower shortage", "缺人", "人數不夠"],
        "finding": "偵測到人手不足跡象，需確認工人數量是否足夠完成工序。",
        "priority": "高",
    },
    {
        "id": "trade_absent",
        "title": "主要工種缺席",
        "keywords": ["工種未到", "分判未到", "subcontractor absent", "trade not arrived", "未到場"],
        "finding": "偵測到主要工種或分判未到場，可能影響工序進度。",
        "priority": "高",
    },
    {
        "id": "supervision_gap",
        "title": "監督不足",
        "keywords": ["無監督", "監督不足", "no supervision", "lack of supervision", "無人監管"],
        "finding": "偵測到監督不足，高風險工序需要足夠監督人員。",
        "priority": "中",
    },
    {
        "id": "night_shift_shortage",
        "title": "夜間施工人手不足",
        "keywords": ["夜間人手不足", "night shift shortage", "夜班不足", "通宵工人不足"],
        "finding": "偵測到夜間施工人手不足，需確認夜班人手配置。",
        "priority": "中",
    },
    {
        "id": "too_many_trades",
        "title": "同一區域工種過多",
        "keywords": ["工種重疊", "太多工種", "too many trades", "overcrowded", "擠迫"],
        "finding": "偵測到同一區域有太多工種同時施工，可能造成工序衝突及安全風險。",
        "priority": "中",
    },
]


TRADE_COORDINATION_RULES = [
    {
        "id": "em_before_boarding",
        "title": "E&M 未完成不應封板",
        "trade_a": ["E&M", "機電", "electrical", "mechanical", "cable tray", "線槽"],
        "trade_b": ["封板", "封牆", "boarding", "close ceiling", "ceiling board"],
        "finding": "E&M 工序未完成前不應封板，需確認機電工序已完成及驗收。",
        "priority": "高",
    },
    {
        "id": "waterproof_before_tiles",
        "title": "防水未完成不應鋪磚",
        "trade_a": ["防水", "waterproof", "waterproofing"],
        "trade_b": ["鋪磚", "鋪地磚", "tile", "tiling", "floor tile"],
        "finding": "防水層未完成及測試前不應鋪磚，需確認防水測試合格。",
        "priority": "高",
    },
    {
        "id": "plaster_before_paint",
        "title": "泥水未完成不應油漆",
        "trade_a": ["泥水", "批盪", "plaster", "plastering", "render"],
        "trade_b": ["油漆", "painting", "paint"],
        "finding": "泥水批盪未完成前不應油漆，需確認批盪已乾透。",
        "priority": "中",
    },
    {
        "id": "lifting_vs_height_work",
        "title": "吊運時不應同區高空作業",
        "trade_a": ["吊運", "lifting", "crane", "吊機", "hoist"],
        "trade_b": ["高空作業", "work at height", "working at height", "棚架工作"],
        "finding": "吊運與高空作業同時進行會增加墮物風險，需設吊運禁區及工序隔離。",
        "priority": "高",
    },
    {
        "id": "welding_near_flammable",
        "title": "焊接附近不應有易燃物或油漆",
        "trade_a": ["焊接", "welding", "hot work", "燒焊"],
        "trade_b": ["油漆", "painting", "易燃物", "flammable", "paint"],
        "finding": "焊接附近有易燃物或油漆工序會造成火警風險，需分區或分時段處理。",
        "priority": "高",
    },
]


MATERIAL_RULES = [
    {
        "id": "material_not_arrived",
        "title": "材料未到場",
        "keywords": ["材料未到", "物料未到", "material not arrived", "material delay", "材料延誤"],
        "finding": "偵測到材料未到場，可能影響工序進度。",
        "priority": "高",
    },
    {
        "id": "material_blocking",
        "title": "材料阻塞通道",
        "keywords": ["材料阻路", "材料阻塞", "blocked by material", "material blocking", "阻塞通道"],
        "finding": "偵測到材料阻塞通道，需即時清理以保持現場 flow 及逃生路線。",
        "priority": "中",
    },
    {
        "id": "material_shortage",
        "title": "材料短缺",
        "keywords": ["材料不足", "材料短缺", "material shortage", "insufficient material"],
        "finding": "偵測到材料短缺，需確認材料供應是否足夠。",
        "priority": "中",
    },
    {
        "id": "wrong_stage_material",
        "title": "材料與施工階段不匹配",
        "keywords": ["材料不對", "wrong material", "材料錯誤", "material mismatch"],
        "finding": "偵測到材料與當前施工階段不匹配，需確認材料規格及時序。",
        "priority": "中",
    },
]


PLANT_RULES = [
    {
        "id": "plant_not_ready",
        "title": "機械未準備",
        "keywords": ["機械未到", "設備未到", "plant not ready", "equipment not ready", "吊機未到"],
        "finding": "偵測到機械或設備未準備，可能影響工序進度。",
        "priority": "高",
    },
    {
        "id": "lifting_equipment_missing",
        "title": "吊運設備未配合",
        "keywords": ["吊運設備不足", "crane not available", "hoist not ready", "吊機不足"],
        "finding": "偵測到吊運設備未配合，需確認吊運計劃及設備安排。",
        "priority": "高",
    },
    {
        "id": "temp_power_insufficient",
        "title": "臨電不足",
        "keywords": ["臨電不足", "電力不足", "power insufficient", "temporary power", "供電不足"],
        "finding": "偵測到臨時電力不足，需確認電力供應是否足夠。",
        "priority": "中",
    },
    {
        "id": "lighting_insufficient",
        "title": "照明不足",
        "keywords": ["照明不足", "lighting insufficient", "燈光不足", "光線不足"],
        "finding": "偵測到照明不足，需確認工作區域照明是否符合安全要求。",
        "priority": "中",
    },
    {
        "id": "tools_missing",
        "title": "工具機具未配合",
        "keywords": ["工具不足", "機具不足", "tools missing", "equipment missing"],
        "finding": "偵測到工具或機具未配合工序，需確認工具配置。",
        "priority": "低",
    },
]


def analyse_resource_workforce(
    text: str = "",
    question: str = "",
    ocr_text: str = "",
    site_context: dict | None = None,
) -> dict:
    """
    Analyse resource and workforce issues with explicit evidence only.
    Returns impact level and auto-generated action items.
    """
    site_context = site_context or {}
    context_bits = []
    if site_context:
        context_bits.extend(site_context.get("environment_labels_zh", []) or [])
        context_bits.extend(site_context.get("site_constraints", []) or [])
        context_bits.extend(site_context.get("risk_modifier", {}).get("risk_notes", []) or [])

    combined = _norm("\n".join([text or "", question or "", ocr_text or "", "\n".join(map(str, context_bits))]))
    
    if not combined:
        return {
            "has_evidence": False,
            "workforce_issues": [],
            "trade_conflicts": [],
            "material_issues": [],
            "plant_issues": [],
            "resource_impact_level": "無明顯影響",
            "action_items": [],
            "pm_summary": INSUFFICIENT_RESOURCE_MESSAGE,
            "memory_should_record": False,
            "insufficient_message": INSUFFICIENT_RESOURCE_MESSAGE,
        }

    workforce_issues = []
    for rule in WORKFORCE_RULES:
        evidence = _evidence(combined, rule["keywords"])
        if evidence:
            workforce_issues.append({
                "rule_id": rule["id"],
                "title": rule["title"],
                "finding": rule["finding"],
                "evidence": evidence[:3],
                "priority": rule["priority"],
            })

    trade_conflicts = []
    for rule in TRADE_COORDINATION_RULES:
        trade_a = _evidence(combined, rule["trade_a"])
        trade_b = _evidence(combined, rule["trade_b"])
        if trade_a and trade_b:
            trade_conflicts.append({
                "rule_id": rule["id"],
                "title": rule["title"],
                "finding": rule["finding"],
                "evidence": trade_a[:2] + trade_b[:2],
                "priority": rule["priority"],
            })

    material_issues = []
    for rule in MATERIAL_RULES:
        evidence = _evidence(combined, rule["keywords"])
        if evidence:
            material_issues.append({
                "rule_id": rule["id"],
                "title": rule["title"],
                "finding": rule["finding"],
                "evidence": evidence[:3],
                "priority": rule["priority"],
            })

    plant_issues = []
    for rule in PLANT_RULES:
        evidence = _evidence(combined, rule["keywords"])
        if evidence:
            plant_issues.append({
                "rule_id": rule["id"],
                "title": rule["title"],
                "finding": rule["finding"],
                "evidence": evidence[:3],
                "priority": rule["priority"],
            })

    total_findings = len(workforce_issues) + len(trade_conflicts) + len(material_issues) + len(plant_issues)
    
    if total_findings == 0:
        has_evidence = False
        impact_level = "無明顯影響"
        pm_summary = INSUFFICIENT_RESOURCE_MESSAGE
        memory_should_record = False
    else:
        has_evidence = True
        if total_findings >= 5:
            impact_level = "嚴重影響"
        elif total_findings >= 3:
            impact_level = "中度影響"
        elif total_findings >= 1:
            impact_level = "輕微影響"
        else:
            impact_level = "無明顯影響"
        
        memory_should_record = impact_level in {"中度影響", "嚴重影響"}
        
        summary_parts = []
        if workforce_issues:
            summary_parts.append(f"{len(workforce_issues)} 項人手問題")
        if trade_conflicts:
            summary_parts.append(f"{len(trade_conflicts)} 項工種協調問題")
        if material_issues:
            summary_parts.append(f"{len(material_issues)} 項材料問題")
        if plant_issues:
            summary_parts.append(f"{len(plant_issues)} 項機械設備問題")
        
        pm_summary = f"資源與人手協調分析：偵測到 {summary_parts[0] if summary_parts else '問題'}，影響程度：{impact_level}。需由 PM / Foreman 核實現場資源配置。"

    action_items = []
    for issue in workforce_issues:
        if issue["priority"] == "高":
            action_items.append({
                "title": issue["title"],
                "detail": issue["finding"],
                "priority": "高",
                "category": "workforce",
            })
    
    for conflict in trade_conflicts:
        if conflict["priority"] == "高":
            action_items.append({
                "title": conflict["title"],
                "detail": conflict["finding"],
                "priority": "高" if conflict["priority"] == "高" else "中",
                "category": "trade_coordination",
            })
    
    for issue in material_issues:
        if issue["priority"] in {"高", "中"}:
            action_items.append({
                "title": issue["title"],
                "detail": issue["finding"],
                "priority": issue["priority"],
                "category": "material",
            })
    
    for issue in plant_issues:
        if issue["priority"] in {"高", "中"}:
            action_items.append({
                "title": issue["title"],
                "detail": issue["finding"],
                "priority": issue["priority"],
                "category": "plant",
            })

    return {
        "has_evidence": has_evidence,
        "workforce_issues": workforce_issues,
        "trade_conflicts": trade_conflicts,
        "material_issues": material_issues,
        "plant_issues": plant_issues,
        "resource_impact_level": impact_level,
        "action_items": action_items,
        "pm_summary": pm_summary,
        "memory_should_record": memory_should_record,
        "insufficient_message": INSUFFICIENT_RESOURCE_MESSAGE,
    }


def format_resource_workforce_for_report(result: dict) -> str:
    """Format resource & workforce analysis for report display."""
    if not result or not result.get("has_evidence"):
        return "資源與人手協調分析\n- 目前資料不足以確認資源或人手是否足夠。"
    
    lines = [
        "資源與人手協調分析",
        f"- 影響程度：{result.get('resource_impact_level', '無明顯影響')}",
    ]
    
    workforce = result.get("workforce_issues", []) or []
    if workforce:
        lines.append("- 人手狀況：")
        for item in workforce[:5]:
            evidence = "、".join(map(str, item.get("evidence", [])))
            lines.append(f"  - {item.get('title')}: {item.get('finding')} Evidence: {evidence}")
    else:
        lines.append("- 人手狀況：未偵測到明確人手問題。")
    
    trades = result.get("trade_conflicts", []) or []
    if trades:
        lines.append("- 工種協調：")
        for item in trades[:5]:
            evidence = "、".join(map(str, item.get("evidence", [])))
            lines.append(f"  - {item.get('title')}: {item.get('finding')} Evidence: {evidence}")
    else:
        lines.append("- 工種協調：未偵測到明確工種衝突。")
    
    materials = result.get("material_issues", []) or []
    if materials:
        lines.append("- 材料狀況：")
        for item in materials[:5]:
            evidence = "、".join(map(str, item.get("evidence", [])))
            lines.append(f"  - {item.get('title')}: {item.get('finding')} Evidence: {evidence}")
    else:
        lines.append("- 材料狀況：未偵測到明確材料問題。")
    
    plants = result.get("plant_issues", []) or []
    if plants:
        lines.append("- 機械 / 設備：")
        for item in plants[:5]:
            evidence = "、".join(map(str, item.get("evidence", [])))
            lines.append(f"  - {item.get('title')}: {item.get('finding')} Evidence: {evidence}")
    else:
        lines.append("- 機械 / 設備：未偵測到明確機械設備問題。")
    
    lines.append(f"- 對進度影響：{result.get('resource_impact_level', '無明顯影響')}")
    
    action_items = result.get("action_items", []) or []
    if action_items:
        lines.append("- 建議跟進：")
        for item in action_items[:5]:
            lines.append(f"  - [{item.get('priority')}] {item.get('title')}")
    else:
        lines.append("- 建議跟進：暫無需即時跟進事項。")
    
    return "\n".join(lines)
