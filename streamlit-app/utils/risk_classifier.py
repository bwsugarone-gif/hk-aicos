"""
risk_classifier.py
HK-AICOS Phase 2.0 - Risk Classification (3-Tier)

Three risk levels only: 低風險 / 中風險 / 高風險
No 極高風險 exposed to clients — maps to 高風險.

Buildway Tech (HK) Limited
"""

# ── Risk Level Definitions (3-tier client version) ───────────────────────────
RISK_LEVELS = {
    "低風險": {
        "color": "#28a745",
        "bg_color": "#d4edda",
        "border_color": "#c3e6cb",
        "emoji": "🟢",
        "label": "低風險",
        "description": "日常工程事務，影響輕微",
        "action": "PM 審閱後可直接處理",
        "response_time": "24 小時內",
    },
    "中風險": {
        "color": "#e67e00",
        "bg_color": "#fff3cd",
        "border_color": "#ffeeba",
        "emoji": "🟠",
        "label": "中風險",
        "description": "對工程進度或成本有一定影響",
        "action": "需要 PM 確認後處理",
        "response_time": "4 小時內",
    },
    "高風險": {
        "color": "#dc3545",
        "bg_color": "#f8d7da",
        "border_color": "#f5c6cb",
        "emoji": "🔴",
        "label": "高風險",
        "description": "對工程、安全或法律有重大影響",
        "action": "需要 PM 及合資格專業人士確認",
        "response_time": "立即處理",
    },
}

# ── Risk Keywords ─────────────────────────────────────────────────────────────
RISK_KEYWORDS = {
    "高風險": [
        "死亡", "嚴重受傷", "住院", "結構倒塌", "火警", "爆炸",
        "觸電", "高壓電", "訴訟", "律師信", "法庭", "刑事",
        "掘路", "公共道路損壞", "危險品洩漏", "斜坡崩塌",
        "工傷", "意外", "緊急", "emergency", "critical",
        "結構改動", "承重牆", "高空工作", "密閉空間", "吊運",
        "大額VO", "合約爭議", "政府執法", "牌照問題",
        "延誤超過7天", "嚴重安全違規", "消防系統",
        "電力系統", "水務", "掘路申請",
    ],
    "中風險": [
        "延誤", "材料問題", "供應商", "VO申請", "工人問題",
        "質量問題", "測量偏差", "圖則修改", "成本超支",
        "付款爭議", "分判商糾紛",
    ],
}

HIGH_RISK_ANALYSIS_TYPES = ["安全風險分析", "法規 / 合規檢查", "臨時設施位置分析"]
MEDIUM_RISK_ANALYSIS_TYPES = ["圖紙 / CAP / MIB 分析", "成本 / 工期影響分析", "PM 綜合分析"]


def classify_risk(analysis_type: str, question: str, ai_response: str = "") -> str:
    """
    Classify risk level. Returns one of: 低風險 / 中風險 / 高風險.
    極高風險 is mapped to 高風險 for client display.
    """
    combined = f"{analysis_type} {question} {ai_response}".lower()

    for kw in RISK_KEYWORDS["高風險"]:
        if kw.lower() in combined:
            return "高風險"

    if analysis_type in HIGH_RISK_ANALYSIS_TYPES:
        return "高風險"

    for kw in RISK_KEYWORDS["中風險"]:
        if kw.lower() in combined:
            return "中風險"

    if analysis_type in MEDIUM_RISK_ANALYSIS_TYPES:
        return "中風險"

    return "低風險"


def get_risk_info(risk_level: str) -> dict:
    """Get full risk level info. Maps 極高風險 → 高風險."""
    if risk_level == "極高風險":
        risk_level = "高風險"
    return RISK_LEVELS.get(risk_level, RISK_LEVELS["中風險"])


def get_risk_color(risk_level: str) -> str:
    return get_risk_info(risk_level)["color"]


def get_risk_bg_color(risk_level: str) -> str:
    return get_risk_info(risk_level)["bg_color"]


def format_risk_badge(risk_level: str) -> str:
    info = get_risk_info(risk_level)
    return (
        f'<span style="'
        f'background-color:{info["bg_color"]};'
        f'color:{info["color"]};'
        f'border:1px solid {info["border_color"]};'
        f'padding:4px 12px;border-radius:4px;'
        f'font-weight:bold;font-size:1.1em;">'
        f'{info["emoji"]} {info["label"]}'
        f'</span>'
    )
