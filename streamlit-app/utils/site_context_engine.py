# -*- coding: utf-8 -*-
"""
utils/site_context_engine.py
HK-AICOS Phase 3.2E — Smart Site Context Awareness Layer

Detects:
  - Site environment (indoor/outdoor, confined space, plant room, etc.)
  - Construction stage (demolition, structure, MEP, finishing, T&C)
  - Work sequence reasonableness
  - Context-aware risk modifiers
  - Site constraints

Hallucination control: if context is unclear, returns "unknown" — never guesses.
"""

import re
from typing import Any

# ── Environment type keywords ─────────────────────────────────────────────────

_ENV_PATTERNS: dict[str, list[str]] = {
    "outdoor": [
        "outdoor", "外部", "戶外", "open air", "外牆", "rooftop", "天台",
        "external", "facade", "外露", "open site", "地盤外", "road", "道路",
        "footpath", "行人路", "slope", "斜坡", "retaining wall", "擋土牆",
    ],
    "indoor": [
        "indoor", "室內", "internal", "inside", "interior", "房間", "room",
        "corridor", "走廊", "lobby", "大堂", "staircase", "樓梯", "lift",
        "elevator", "電梯", "office", "辦公室", "flat", "單位", "apartment",
    ],
    "confined_space": [
        "confined space", "密閉空間", "confined", "manhole", "渠蓋", "tank",
        "水箱", "sewer", "下水道", "pit", "坑", "tunnel", "隧道", "duct",
        "風管", "culvert", "暗渠", "underground", "地下", "basement", "地庫",
        "caisson", "沉箱", "cofferdam", "圍堰",
    ],
    "plant_room": [
        "plant room", "機房", "electrical room", "電房", "generator room",
        "發電機房", "pump room", "泵房", "boiler room", "鍋爐房",
        "switch room", "開關房", "transformer", "變壓器", "substation", "變電站",
        "chiller", "冷凍機", "AHU", "空調機房", "server room", "伺服器房",
    ],
    "escape_route": [
        "escape route", "逃生路線", "exit", "出口", "emergency exit", "緊急出口",
        "fire exit", "防火門", "staircase", "樓梯", "refuge floor", "避難層",
        "assembly point", "集合點", "evacuation", "疏散",
    ],
    "temporary_work_area": [
        "temporary", "臨時", "temp", "hoarding", "圍板", "site office",
        "地盤辦公室", "welfare facility", "福利設施", "canteen", "飯堂",
        "storage area", "儲存區", "laydown area", "堆放區", "scaffold", "棚架",
        "falsework", "模板支撐", "formwork", "模板",
    ],
    "active_construction_zone": [
        "active", "施工中", "under construction", "建設中", "construction zone",
        "施工區", "work in progress", "進行中", "live site", "活躍地盤",
        "ongoing work", "工程進行", "excavation", "挖掘", "piling", "打樁",
        "concreting", "澆灌混凝土", "pouring", "澆灌",
    ],
    "high_risk_area": [
        "high risk", "高風險", "danger zone", "危險區", "exclusion zone",
        "禁區", "restricted", "限制區", "overhead work", "高空工作",
        "working at height", "高處工作", "edge", "邊緣", "opening", "開口",
        "void", "空洞", "excavation edge", "挖掘邊緣", "crane", "吊機",
        "lifting zone", "吊運區", "suspended load", "懸掛荷載",
    ],
}

# ── Construction stage keywords ───────────────────────────────────────────────

_STAGE_PATTERNS: dict[str, list[str]] = {
    "demolition": [
        "demolition", "拆卸", "demolish", "拆除", "strip out", "清拆",
        "breaking", "打鑿", "hacking", "鑿", "removal", "移除",
        "asbestos", "石棉", "decommission", "停用", "deconstruct", "解構",
        "soft strip", "軟拆", "structural demolition", "結構拆卸",
    ],
    "structure": [
        "structure", "結構", "structural", "concrete", "混凝土", "rebar",
        "鋼筋", "formwork", "模板", "falsework", "模板支撐", "piling", "打樁",
        "foundation", "地基", "footing", "基腳", "column", "柱", "beam", "樑",
        "slab", "樓板", "shear wall", "剪力牆", "core wall", "核心牆",
        "frame", "框架", "steel structure", "鋼結構", "erection", "安裝",
        "concreting", "澆灌", "pouring", "澆灌混凝土", "curing", "養護",
    ],
    "mep": [
        "MEP", "mechanical", "機械", "electrical", "電氣", "plumbing", "水喉",
        "HVAC", "冷氣", "air conditioning", "空調", "ventilation", "通風",
        "drainage", "排水", "water supply", "供水", "fire services", "消防",
        "sprinkler", "灑水", "cable", "電纜", "conduit", "線管", "trunking",
        "線槽", "ductwork", "風管", "pipe", "管道", "valve", "閥門",
        "pump", "泵", "fan", "風機", "chiller", "冷凍機", "boiler", "鍋爐",
        "generator", "發電機", "switchboard", "配電板", "panel", "電箱",
        "BMS", "樓宇管理系統", "ELV", "弱電",
    ],
    "finishing": [
        "finishing", "裝修", "fit out", "裝配", "interior", "室內裝修",
        "tiling", "鋪磚", "flooring", "地板", "ceiling", "天花", "partition",
        "間隔", "plastering", "批盪", "painting", "油漆", "carpentry", "木工",
        "joinery", "細木工", "glazing", "玻璃", "curtain wall", "幕牆",
        "cladding", "外牆板", "waterproofing", "防水", "screed", "地台",
        "raised floor", "架空地板", "suspended ceiling", "吊頂",
    ],
    "testing_commissioning": [
        "testing", "測試", "commissioning", "試運", "T&C", "handover", "交付",
        "inspection", "驗收", "defect", "缺陷", "snagging", "修補",
        "pre-commissioning", "試運前", "functional test", "功能測試",
        "pressure test", "壓力測試", "load test", "負荷測試",
        "fire drill", "消防演習", "witness test", "見證測試",
        "certificate", "證書", "occupation permit", "入伙紙", "OP",
        "completion", "完工", "practical completion", "實際完工",
    ],
}

# ── Stage risk modifiers ──────────────────────────────────────────────────────
# Each stage has a base risk multiplier and specific hazard notes.

_STAGE_RISK_PROFILE: dict[str, dict] = {
    "demolition": {
        "risk_multiplier": 1.4,
        "hazards": [
            "結構不穩定風險",
            "粉塵及有害物質（石棉、鉛）",
            "倒塌風險",
            "噪音及震動",
            "廢料處理",
        ],
        "required_permits": ["拆卸令", "石棉調查報告（如適用）", "噪音許可證"],
        "label_zh": "拆卸階段",
    },
    "structure": {
        "risk_multiplier": 1.3,
        "hazards": [
            "高空工作（模板、鋼筋）",
            "混凝土澆灌安全",
            "模板支撐失效",
            "打樁噪音及震動",
            "地基沉降",
        ],
        "required_permits": ["建築圖則批准", "地盤監督", "打樁許可（如適用）"],
        "label_zh": "結構階段",
    },
    "mep": {
        "risk_multiplier": 1.2,
        "hazards": [
            "電氣危險（帶電工作）",
            "密閉空間（管道、水箱）",
            "高壓系統",
            "氣體洩漏",
            "高空管道安裝",
        ],
        "required_permits": ["電業工程人員牌照", "水喉匠牌照", "密閉空間工作許可"],
        "label_zh": "機電工程階段",
    },
    "finishing": {
        "risk_multiplier": 1.1,
        "hazards": [
            "化學品（油漆、溶劑）",
            "粉塵（打磨、批盪）",
            "高空工作（天花、幕牆）",
            "電動工具安全",
        ],
        "required_permits": ["裝修許可（如適用）"],
        "label_zh": "裝修階段",
    },
    "testing_commissioning": {
        "risk_multiplier": 1.0,
        "hazards": [
            "帶電系統測試",
            "高壓測試",
            "消防系統啟動",
            "電梯測試",
        ],
        "required_permits": ["相關系統測試證書", "入伙紙申請"],
        "label_zh": "測試及試運階段",
    },
    "unknown": {
        "risk_multiplier": 1.0,
        "hazards": [],
        "required_permits": [],
        "label_zh": "工程階段不明",
    },
}

# ── Environment risk modifiers ────────────────────────────────────────────────

_ENV_RISK_MODIFIER: dict[str, float] = {
    "outdoor":                1.1,
    "indoor":                 1.0,
    "confined_space":         1.5,
    "plant_room":             1.3,
    "escape_route":           1.2,
    "temporary_work_area":    1.1,
    "active_construction_zone": 1.2,
    "high_risk_area":         1.4,
    "unknown":                1.0,
}

_ENV_LABEL_ZH: dict[str, str] = {
    "outdoor":                "戶外",
    "indoor":                 "室內",
    "confined_space":         "密閉空間",
    "plant_room":             "機房",
    "escape_route":           "逃生路線",
    "temporary_work_area":    "臨時工作區",
    "active_construction_zone": "活躍施工區",
    "high_risk_area":         "高風險區域",
    "unknown":                "環境不明",
}

# ── Work sequence reasonableness rules ───────────────────────────────────────
# Maps (stage, observed_activity) → reasonableness verdict

_SEQUENCE_RULES: list[dict] = [
    {
        "stage": "demolition",
        "activity_keywords": ["concrete", "混凝土", "rebar", "鋼筋", "formwork", "模板"],
        "verdict": "unusual",
        "reason": "拆卸階段不應進行新混凝土澆灌或鋼筋安裝，請確認工序是否正確。",
    },
    {
        "stage": "demolition",
        "activity_keywords": ["finishing", "裝修", "tiling", "鋪磚", "painting", "油漆"],
        "verdict": "unusual",
        "reason": "拆卸階段不應進行裝修工序，請確認工序順序。",
    },
    {
        "stage": "structure",
        "activity_keywords": ["finishing", "裝修", "tiling", "鋪磚", "painting", "油漆", "curtain wall", "幕牆"],
        "verdict": "unusual",
        "reason": "結構階段通常不應進行裝修工序，除非有特別安排。",
    },
    {
        "stage": "structure",
        "activity_keywords": ["rubbish", "雜物", "debris", "廢料", "waste", "垃圾", "clutter", "堆積"],
        "verdict": "warning",
        "reason": "結構階段發現雜物堆積，可能阻礙施工及造成安全隱患，需立即清理。",
    },
    {
        "stage": "mep",
        "activity_keywords": ["demolition", "拆卸", "demolish", "拆除", "hacking", "鑿"],
        "verdict": "warning",
        "reason": "機電工程階段進行拆卸工序，需確認不影響已安裝系統。",
    },
    {
        "stage": "finishing",
        "activity_keywords": ["piling", "打樁", "excavation", "挖掘", "concreting", "澆灌"],
        "verdict": "unusual",
        "reason": "裝修階段不應進行結構工序，請確認工序安排。",
    },
    {
        "stage": "testing_commissioning",
        "activity_keywords": ["demolition", "拆卸", "excavation", "挖掘", "piling", "打樁"],
        "verdict": "unusual",
        "reason": "測試及試運階段不應進行重型施工工序，請確認工程狀態。",
    },
]


# ── Core detection functions ──────────────────────────────────────────────────

def detect_environment(text: str) -> list[str]:
    """
    Detect site environment types from text.
    Returns list of detected environment keys (may be multiple).
    Returns ["unknown"] if nothing detected.
    Hallucination control: only returns what is explicitly evidenced in text.
    """
    if not text or not text.strip():
        return ["unknown"]

    text_lower = text.lower()
    detected = []

    for env_key, keywords in _ENV_PATTERNS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                if env_key not in detected:
                    detected.append(env_key)
                break  # one match per env type is enough

    return detected if detected else ["unknown"]


def detect_construction_stage(text: str) -> str:
    """
    Detect the most likely construction stage from text.
    Returns a single stage key (the one with most keyword hits).
    Returns "unknown" if nothing detected.
    Hallucination control: requires at least 2 keyword hits to confirm a stage.
    """
    if not text or not text.strip():
        return "unknown"

    text_lower = text.lower()
    scores: dict[str, int] = {}

    for stage_key, keywords in _STAGE_PATTERNS.items():
        count = sum(1 for kw in keywords if kw.lower() in text_lower)
        if count > 0:
            scores[stage_key] = count

    if not scores:
        return "unknown"

    # Require at least 2 keyword hits to avoid false positives
    best_stage = max(scores, key=lambda k: scores[k])
    if scores[best_stage] < 2:
        return "unknown"

    return best_stage


def check_work_sequence(stage: str, text: str) -> dict[str, Any]:
    """
    Check if observed activities are reasonable for the detected construction stage.

    Returns:
        {
            "verdict": "ok" | "warning" | "unusual" | "unknown",
            "reason": str,
            "rule_triggered": str,
        }
    """
    if stage == "unknown" or not text:
        return {"verdict": "unknown", "reason": "工程階段不明，無法判斷工序合理性。", "rule_triggered": ""}

    text_lower = text.lower()

    for rule in _SEQUENCE_RULES:
        if rule["stage"] != stage:
            continue
        for kw in rule["activity_keywords"]:
            if kw.lower() in text_lower:
                return {
                    "verdict": rule["verdict"],
                    "reason": rule["reason"],
                    "rule_triggered": f"{stage}+{kw}",
                }

    return {"verdict": "ok", "reason": "工序與工程階段相符，未發現明顯異常。", "rule_triggered": ""}


def calculate_context_risk_modifier(environments: list[str], stage: str) -> dict[str, Any]:
    """
    Calculate combined risk modifier from environment + stage.

    Returns:
        {
            "combined_modifier": float,
            "env_modifier": float,
            "stage_modifier": float,
            "dominant_env": str,
            "stage": str,
            "risk_notes": list[str],
        }
    """
    # Pick the highest-risk environment as dominant
    env_modifiers = [_ENV_RISK_MODIFIER.get(e, 1.0) for e in environments]
    dominant_env = environments[env_modifiers.index(max(env_modifiers))] if environments else "unknown"
    env_modifier = max(env_modifiers) if env_modifiers else 1.0

    stage_profile = _STAGE_RISK_PROFILE.get(stage, _STAGE_RISK_PROFILE["unknown"])
    stage_modifier = stage_profile["risk_multiplier"]

    # Combined: multiply, but cap at 2.0 to avoid extreme inflation
    combined = min(env_modifier * stage_modifier, 2.0)

    risk_notes = list(stage_profile["hazards"])
    if dominant_env == "confined_space":
        risk_notes.insert(0, "密閉空間：需持有效工作許可，並有人員監察")
    if dominant_env == "high_risk_area":
        risk_notes.insert(0, "高風險區域：需加強安全措施及監督")
    if dominant_env == "plant_room":
        risk_notes.insert(0, "機房：需注意電氣及機械危險")

    return {
        "combined_modifier": round(combined, 2),
        "env_modifier": round(env_modifier, 2),
        "stage_modifier": round(stage_modifier, 2),
        "dominant_env": dominant_env,
        "stage": stage,
        "risk_notes": risk_notes[:6],  # cap at 6 notes
    }


def apply_context_risk_to_level(
    base_risk_level: str,
    combined_modifier: float,
) -> str:
    """
    Adjust risk level based on context modifier.
    Only elevates, never lowers (conservative approach).

    modifier >= 1.5 → elevate by 2 levels
    modifier >= 1.3 → elevate by 1 level
    modifier >= 1.0 → no change
    """
    levels = ["低風險", "中風險", "高風險", "極高風險"]
    current_idx = levels.index(base_risk_level) if base_risk_level in levels else 1

    if combined_modifier >= 1.5:
        new_idx = min(current_idx + 2, len(levels) - 1)
    elif combined_modifier >= 1.3:
        new_idx = min(current_idx + 1, len(levels) - 1)
    else:
        new_idx = current_idx

    return levels[new_idx]


def build_site_context_prompt_block(site_context: dict[str, Any]) -> str:
    """
    Build a formatted prompt block for injection into agent prompts.
    PM Agent uses this for final decision-making.
    """
    if not site_context or site_context.get("context_available") is False:
        return ""

    lines = ["[SITE CONTEXT]"]

    # Environment
    envs = site_context.get("environments", ["unknown"])
    env_labels = [_ENV_LABEL_ZH.get(e, e) for e in envs if e != "unknown"]
    if env_labels:
        lines.append(f"現場環境：{', '.join(env_labels)}")
    else:
        lines.append("現場環境：不明（請提供更多資料）")

    # Stage
    stage = site_context.get("stage", "unknown")
    stage_label = _STAGE_RISK_PROFILE.get(stage, {}).get("label_zh", "不明")
    lines.append(f"工程階段：{stage_label}")

    # Work sequence
    seq = site_context.get("sequence_check", {})
    seq_verdict = seq.get("verdict", "unknown")
    seq_reason = seq.get("reason", "")
    verdict_label = {
        "ok": "✅ 工序合理",
        "warning": "⚠️ 工序需注意",
        "unusual": "🚫 工序異常",
        "unknown": "❓ 無法判斷",
    }.get(seq_verdict, "❓ 無法判斷")
    lines.append(f"工序判斷：{verdict_label}")
    if seq_reason and seq_verdict != "ok":
        lines.append(f"工序備注：{seq_reason}")

    # Risk modifier
    risk_mod = site_context.get("risk_modifier", {})
    modifier = risk_mod.get("combined_modifier", 1.0)
    if modifier > 1.0:
        lines.append(f"現場風險加乘：×{modifier:.1f}")

    # Risk notes
    risk_notes = risk_mod.get("risk_notes", [])
    if risk_notes:
        lines.append(f"現場危險因素：{', '.join(risk_notes[:3])}")

    # Required permits
    permits = _STAGE_RISK_PROFILE.get(stage, {}).get("required_permits", [])
    if permits:
        lines.append(f"相關許可要求：{', '.join(permits)}")

    # Site constraints
    constraints = site_context.get("site_constraints", [])
    if constraints:
        lines.append(f"現場限制：{', '.join(constraints[:3])}")

    lines.append("")
    lines.append("PM Agent 指示：請根據以上現場 context 調整最終風險判斷及行動建議。")
    lines.append("如現場環境或工程階段不明，請在報告中標注「需現場確認」，不可推測。")

    return "\n".join(lines)


def detect_site_constraints(text: str, environments: list[str], stage: str) -> list[str]:
    """
    Detect specific site constraints from text + context.
    Returns list of constraint descriptions.
    """
    constraints = []
    text_lower = text.lower()

    # Confined space constraints
    if "confined_space" in environments:
        constraints.append("密閉空間：需持有效工作許可及緊急救援安排")

    # Escape route constraints
    if "escape_route" in environments:
        constraints.append("逃生路線：不可阻塞，需保持暢通")

    # Active zone constraints
    if "active_construction_zone" in environments:
        constraints.append("活躍施工區：需設置適當圍板及警示標誌")

    # Stage-specific constraints
    if stage == "demolition":
        if any(kw in text_lower for kw in ["asbestos", "石棉", "lead", "鉛", "hazardous"]):
            constraints.append("危險物質：需進行石棉/有害物質調查及處理")

    if stage == "structure":
        if any(kw in text_lower for kw in ["formwork", "模板", "falsework", "模板支撐"]):
            constraints.append("模板支撐：需由工程師審批及監督")

    if stage == "mep":
        if any(kw in text_lower for kw in ["live", "帶電", "energized", "high voltage", "高壓"]):
            constraints.append("帶電工作：需持有效工作許可及隔離措施")

    # General constraints from text
    if any(kw in text_lower for kw in ["night work", "夜間工作", "night shift", "夜班"]):
        constraints.append("夜間工作：需額外照明及安全措施")

    if any(kw in text_lower for kw in ["typhoon", "颱風", "rainstorm", "暴雨", "bad weather", "惡劣天氣"]):
        constraints.append("惡劣天氣：需暫停高空及戶外工作")

    return constraints[:5]  # cap at 5


# ── Main pipeline function ────────────────────────────────────────────────────

def analyse_site_context(
    text: str,
    question: str = "",
    ocr_text: str = "",
) -> dict[str, Any]:
    """
    Full site context analysis pipeline.

    Args:
        text:      Combined file content / description
        question:  User's question (may contain context clues)
        ocr_text:  OCR-extracted text from images

    Returns:
        {
            "context_available": bool,
            "environments": list[str],
            "environment_labels_zh": list[str],
            "stage": str,
            "stage_label_zh": str,
            "sequence_check": dict,
            "risk_modifier": dict,
            "adjusted_risk_level": str | None,  # None if base not provided
            "site_constraints": list[str],
            "prompt_block": str,
            "confidence": str,  # "high" | "medium" | "low"
        }
    """
    # Combine all available text for analysis
    combined = " ".join(filter(None, [text, question, ocr_text]))

    if not combined.strip():
        return {
            "context_available": False,
            "environments": ["unknown"],
            "environment_labels_zh": ["環境不明"],
            "stage": "unknown",
            "stage_label_zh": "工程階段不明",
            "sequence_check": {"verdict": "unknown", "reason": "無文字資料可分析。", "rule_triggered": ""},
            "risk_modifier": {"combined_modifier": 1.0, "env_modifier": 1.0, "stage_modifier": 1.0,
                              "dominant_env": "unknown", "stage": "unknown", "risk_notes": []},
            "adjusted_risk_level": None,
            "site_constraints": [],
            "prompt_block": "",
            "confidence": "low",
        }

    # Step 1: Detect environment
    environments = detect_environment(combined)

    # Step 2: Detect construction stage
    stage = detect_construction_stage(combined)

    # Step 3: Check work sequence reasonableness
    sequence_check = check_work_sequence(stage, combined)

    # Step 4: Calculate risk modifier
    risk_modifier = calculate_context_risk_modifier(environments, stage)

    # Step 5: Detect site constraints
    site_constraints = detect_site_constraints(combined, environments, stage)

    # Step 6: Build prompt block for PM Agent
    context_data = {
        "context_available": True,
        "environments": environments,
        "stage": stage,
        "sequence_check": sequence_check,
        "risk_modifier": risk_modifier,
        "site_constraints": site_constraints,
    }
    prompt_block = build_site_context_prompt_block(context_data)

    # Step 7: Assess confidence
    # High: both env and stage detected
    # Medium: one of them detected
    # Low: neither detected
    env_known = environments != ["unknown"]
    stage_known = stage != "unknown"
    if env_known and stage_known:
        confidence = "high"
    elif env_known or stage_known:
        confidence = "medium"
    else:
        confidence = "low"

    env_labels_zh = [_ENV_LABEL_ZH.get(e, e) for e in environments]
    stage_label_zh = _STAGE_RISK_PROFILE.get(stage, {}).get("label_zh", "工程階段不明")

    return {
        "context_available": env_known or stage_known,
        "environments": environments,
        "environment_labels_zh": env_labels_zh,
        "stage": stage,
        "stage_label_zh": stage_label_zh,
        "sequence_check": sequence_check,
        "risk_modifier": risk_modifier,
        "adjusted_risk_level": None,  # caller applies this with apply_context_risk_to_level()
        "site_constraints": site_constraints,
        "prompt_block": prompt_block,
        "confidence": confidence,
    }
