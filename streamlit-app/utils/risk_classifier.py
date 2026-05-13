"""
risk_classifier.py
HK-AICOS Phase 2.0 - Risk Classification

Classifies risk levels based on analysis content and keywords.
"""

# Risk level definitions
RISK_LEVELS = {
    "低風險": {
        "color": "#28a745",       # Green
        "bg_color": "#d4edda",
        "border_color": "#c3e6cb",
        "emoji": "🟢",
        "label": "低風險",
        "label_en": "LOW RISK",
        "description": "日常工程事務，影響輕微",
        "action": "PM 審閱後可直接處理",
        "response_time": "24 小時內",
    },
    "中風險": {
        "color": "#ffc107",       # Yellow
        "bg_color": "#fff3cd",
        "border_color": "#ffeeba",
        "emoji": "🟡",
        "label": "中風險",
        "label_en": "MEDIUM RISK",
        "description": "對工程進度或成本有一定影響",
        "action": "需要 PM 確認後處理",
        "response_time": "4 小時內",
    },
    "高風險": {
        "color": "#fd7e14",       # Orange
        "bg_color": "#fde8d8",
        "border_color": "#fbd0b0",
        "emoji": "🔴",
        "label": "高風險",
        "label_en": "HIGH RISK",
        "description": "對工程、安全或法律有重大影響",
        "action": "需要 PM + 法律確認",
        "response_time": "2 小時內",
    },
    "極高風險": {
        "color": "#dc3545",       # Red
        "bg_color": "#f8d7da",
        "border_color": "#f5c6cb",
        "emoji": "⚫",
        "label": "極高風險",
        "label_en": "EXTREME RISK",
        "description": "涉及人命安全、重大法律責任或重大財務損失",
        "action": "立即處理，必須由香港合資格專業人士確認",
        "response_time": "立即",
    },
}

# Keywords that indicate each risk level
RISK_KEYWORDS = {
    "極高風險": [
        "死亡", "嚴重受傷", "住院", "結構倒塌", "火警", "爆炸",
        "觸電", "高壓電", "訴訟", "律師信", "法庭", "刑事",
        "掘路", "公共道路損壞", "危險品洩漏", "斜坡崩塌",
        "工傷", "意外", "緊急", "emergency", "critical",
    ],
    "高風險": [
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

# Analysis types that default to higher risk
HIGH_RISK_ANALYSIS_TYPES = ["安全風險分析", "法規 / 合規檢查", "臨時設施位置分析"]
MEDIUM_RISK_ANALYSIS_TYPES = ["圖紙 / CAP / MIB 分析", "成本 / 工期影響分析", "PM 綜合分析"]


def classify_risk(analysis_type: str, question: str, ai_response: str = "") -> str:
    """
    Classify risk level based on analysis type, question, and AI response.
    Returns risk level string.
    """
    combined_text = f"{analysis_type} {question} {ai_response}".lower()

    # Check for extreme risk keywords first
    for keyword in RISK_KEYWORDS["極高風險"]:
        if keyword.lower() in combined_text:
            return "極高風險"

    # Check for high risk keywords
    for keyword in RISK_KEYWORDS["高風險"]:
        if keyword.lower() in combined_text:
            return "高風險"

    # Check analysis type defaults
    if analysis_type in HIGH_RISK_ANALYSIS_TYPES:
        # Check for medium risk keywords
        for keyword in RISK_KEYWORDS["中風險"]:
            if keyword.lower() in combined_text:
                return "高風險"
        return "高風險"  # Safety/compliance always at least high risk

    if analysis_type in MEDIUM_RISK_ANALYSIS_TYPES:
        for keyword in RISK_KEYWORDS["中風險"]:
            if keyword.lower() in combined_text:
                return "中風險"
        return "中風險"

    # Check for medium risk keywords
    for keyword in RISK_KEYWORDS["中風險"]:
        if keyword.lower() in combined_text:
            return "中風險"

    return "低風險"


def get_risk_info(risk_level: str) -> dict:
    """Get full risk level information including colors and descriptions."""
    return RISK_LEVELS.get(risk_level, RISK_LEVELS["中風險"])


def get_risk_color(risk_level: str) -> str:
    """Get the hex color for a risk level."""
    return RISK_LEVELS.get(risk_level, RISK_LEVELS["中風險"])["color"]


def get_risk_bg_color(risk_level: str) -> str:
    """Get the background hex color for a risk level."""
    return RISK_LEVELS.get(risk_level, RISK_LEVELS["中風險"])["bg_color"]


def format_risk_badge(risk_level: str) -> str:
    """Format risk level as HTML badge for display."""
    info = get_risk_info(risk_level)
    return (
        f'<span style="'
        f'background-color:{info["bg_color"]};'
        f'color:{info["color"]};'
        f'border:1px solid {info["border_color"]};'
        f'padding:4px 12px;'
        f'border-radius:4px;'
        f'font-weight:bold;'
        f'font-size:1.1em;">'
        f'{info["emoji"]} {info["label"]}'
        f'</span>'
    )
