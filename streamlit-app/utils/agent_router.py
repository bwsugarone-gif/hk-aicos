"""
HK-AICOS Phase 2.0 agent routing.

This module keeps routing simple and client-safe. Generated analysis prompts
ask for clean consultant-style Chinese text, not Markdown.
"""

# ── Agent definitions ─────────────────────────────────────────────────────────
# Each agent has: id, display name, icon, description, focus areas, regulations
AGENT_DEFINITIONS = {
    "safety": {
        "id": "safety",
        "name": "Safety Agent",
        "display": "安全 Agent",
        "icon": "🦺",
        "label": "Safety Agent（安全）",
        "desc": "分析工地安全風險、PPE 使用、高危工序及即時危險",
        "focus": ["現場安全", "即時風險", "PPE 使用", "高危工序", "停工或復工條件"],
        "regulations": ["勞工處", "消防處"],
        "risk_keywords": ["高空", "棚架", "受傷", "工傷", "觸電", "火警"],
        "report_section": "安全風險分析",
        "report_section_en": "Safety Risk Analysis",
    },
    "pm": {
        "id": "pm",
        "name": "PM Agent",
        "display": "PM Agent",
        "icon": "📋",
        "label": "PM Agent（項目管理）",
        "desc": "綜合分析工程進度、資源安排、責任分工及決策支援",
        "focus": ["工序影響", "延誤原因", "資源安排", "重點問題", "下一步行動"],
        "regulations": ["勞工處", "相關政府部門"],
        "risk_keywords": ["延誤", "進度", "工序", "分判", "綜合", "決策"],
        "report_section": "PM 工程進度分析",
        "report_section_en": "PM Progress Analysis",
    },
    "qs": {
        "id": "qs",
        "name": "QS Agent",
        "display": "QS Agent",
        "icon": "💰",
        "label": "QS Agent（工料測量）",
        "desc": "評估成本影響、工期延誤、VO 可能性及合約索償風險",
        "focus": ["成本影響", "工期影響", "VO 可能性", "索償風險"],
        "regulations": ["合約要求"],
        "risk_keywords": ["VO", "成本", "索償", "罰款", "工期"],
        "report_section": "成本及工期影響分析",
        "report_section_en": "Cost & Schedule Impact",
    },
    "legal": {
        "id": "legal",
        "name": "Legal Agent",
        "display": "法規 Agent",
        "icon": "⚖️",
        "label": "Legal Agent（法規合規）",
        "desc": "對照香港法規，檢查政府部門要求、牌照、通報及合規風險",
        "focus": ["政府部門", "合規風險", "確認要求", "牌照", "通報"],
        "regulations": ["屋宇署", "勞工處", "消防處", "EMSD", "水務署", "路政署"],
        "risk_keywords": ["通知", "牌照", "通報", "批准", "政府", "法規"],
        "report_section": "法規及合規分析",
        "report_section_en": "Legal & Compliance",
    },
    "risk": {
        "id": "risk",
        "name": "Risk Agent",
        "display": "風險 Agent",
        "icon": "⚠️",
        "label": "Risk Agent（風險評估）",
        "desc": "綜合評估項目整體風險、責任範圍及優先處理事項",
        "focus": ["整體風險評估", "責任範圍", "優先處理", "風險排序"],
        "regulations": ["相關政府部門"],
        "risk_keywords": ["風險", "責任", "緊急", "優先", "影響"],
        "report_section": "綜合風險評估",
        "report_section_en": "Risk Assessment",
    },
}

# Ordered list for UI display
AGENT_ORDER = ["safety", "pm", "qs", "legal", "risk"]

AGENT_ROUTING = {
    "安全風險分析": {
        "agents": ["安全 Agent", "PM Agent", "法規 Agent"],
        "focus": ["現場安全", "即時風險", "停工或復工條件"],
        "regulations": ["勞工處", "消防處"],
        "risk_keywords": ["高空", "棚架", "受傷", "工傷", "觸電", "火警"],
    },
    "圖則及文件分析": {
        "agents": ["工程 Agent", "法規 Agent", "PM Agent"],
        "focus": ["圖則差異", "施工影響", "需確認資料"],
        "regulations": ["屋宇署", "EMSD", "水務署"],
        "risk_keywords": ["圖則", "結構", "機電", "水喉", "改動"],
    },
    "工程進度分析": {
        "agents": ["工程 Agent", "PM Agent"],
        "focus": ["工序影響", "延誤原因", "資源安排"],
        "regulations": ["勞工處"],
        "risk_keywords": ["延誤", "進度", "工序", "分判"],
    },
    "法規及合規分析": {
        "agents": ["法規 Agent", "PM Agent"],
        "focus": ["政府部門", "合規風險", "確認要求"],
        "regulations": ["屋宇署", "勞工處", "消防處", "EMSD", "水務署", "路政署"],
        "risk_keywords": ["通知", "牌照", "通報", "批准", "政府"],
    },
    "成本及工期影響分析": {
        "agents": ["QS Agent", "工程 Agent", "PM Agent"],
        "focus": ["成本影響", "工期影響", "VO 可能性"],
        "regulations": ["合約要求"],
        "risk_keywords": ["VO", "成本", "索償", "付款", "工期"],
    },
    "PM 綜合分析": {
        "agents": ["PM Agent", "安全 Agent", "QS Agent", "法規 Agent"],
        "focus": ["重點問題", "風險排序", "下一步行動"],
        "regulations": ["相關政府部門"],
        "risk_keywords": ["綜合", "決策", "責任", "跟進"],
    },
}

ALIASES = {
    "安全": "安全風險分析",
    "圖則": "圖則及文件分析",
    "文件": "圖則及文件分析",
    "進度": "工程進度分析",
    "法規": "法規及合規分析",
    "合規": "法規及合規分析",
    "成本": "成本及工期影響分析",
    "工期": "成本及工期影響分析",
    "QS": "成本及工期影響分析",
    "PM": "PM 綜合分析",
}

EXTREME_RISK_TRIGGERS = [
    "死亡", "重傷", "墮下", "倒塌", "火警", "爆炸", "觸電", "結構安全",
    "停工令", "政府檢控", "重大事故",
]

PROFESSIONAL_CONFIRMATION_TRIGGERS = {
    "認可人士": ["結構", "改動", "樓板", "樑", "柱", "屋宇署"],
    "註冊結構工程師": ["結構", "裂縫", "承重", "倒塌"],
    "註冊電業工程人員": ["電力", "電箱", "臨時電", "觸電"],
    "消防專業人士": ["消防", "火警", "排煙", "滅火"],
    "持牌水喉匠": ["水務", "食水", "水喉", "供水"],
    "安全主任": ["高空", "棚架", "工傷", "受傷", "安全帶"],
    "QS 或合約負責人": ["VO", "成本", "索償", "付款", "工期"],
}


def _normalise_analysis_type(analysis_type: str) -> str:
    text = str(analysis_type or "")
    if text in AGENT_ROUTING:
        return text
    for keyword, target in ALIASES.items():
        if keyword.lower() in text.lower():
            return target
    return "PM 綜合分析"


def get_routing(analysis_type: str) -> dict:
    return AGENT_ROUTING[_normalise_analysis_type(analysis_type)]


def get_all_analysis_types() -> list:
    return list(AGENT_ROUTING.keys())


def check_extreme_risk(text: str) -> bool:
    return any(keyword in str(text or "") for keyword in EXTREME_RISK_TRIGGERS)


def get_required_professionals(analysis_type: str, question: str, file_description: str = "") -> list:
    combined_text = f"{analysis_type} {question} {file_description}"
    required = []
    for professional, keywords in PROFESSIONAL_CONFIRMATION_TRIGGERS.items():
        if any(keyword in combined_text for keyword in keywords):
            required.append(professional)
    return required


def get_agent_definitions() -> dict:
    """Return all agent definitions."""
    return AGENT_DEFINITIONS


def get_agents_ordered() -> list:
    """Return agent defs in display order."""
    return [AGENT_DEFINITIONS[k] for k in AGENT_ORDER]


def build_prompt_from_agents(
    selected_agent_ids: list,
    question: str,
    file_description: str,
    rag_context: str = "",
) -> str:
    """
    Build an analysis prompt dynamically from a list of selected agent IDs.
    Each selected agent contributes its own report section to the output.
    """
    if not selected_agent_ids:
        selected_agent_ids = list(AGENT_ORDER)

    agents = [AGENT_DEFINITIONS[aid] for aid in selected_agent_ids if aid in AGENT_DEFINITIONS]

    # Collect all focus areas and regulations from selected agents
    all_focus = []
    all_regulations = []
    for agent in agents:
        for f in agent["focus"]:
            if f not in all_focus:
                all_focus.append(f)
        for r in agent["regulations"]:
            if r not in all_regulations:
                all_regulations.append(r)

    focus_text = "，".join(all_focus)
    regulation_text = "，".join(all_regulations)
    reference_text = rag_context if rag_context else "未有額外參考資料。"

    # Build the section instructions for each selected agent
    section_instructions = []
    for agent in agents:
        section_instructions.append(
            f"{agent['report_section']}\n"
            f"由 {agent['display']} 負責。用三至五行說明與此範疇相關的分析、風險及建議。"
        )
    sections_text = "\n\n".join(section_instructions)

    agent_names = "、".join([a["display"] for a in agents])

    # Detect multi-file context from description
    is_multi_file = "---" in file_description and "[檔案 2" in file_description
    multi_file_note = (
        "\n注意：以上附件包含多個來自同一工程項目的檔案，請綜合所有檔案內容進行分析。\n"
        if is_multi_file else ""
    )

    return f"""你是 HK-AICOS 香港工程顧問報告撰寫助手，由 Buildway Tech (HK) Limited 提供。

請用專業香港工程顧問報告語氣撰寫。
不得使用 Markdown。
不得使用井號、星號、項目符號、分隔線或粗體格式。
不得出現好的、以下是分析、我是AI、感謝使用等助手口吻。
不得提及模型、服務商、系統介面、開發、除錯或憑證字眼。

參與分析的 Agent
{agent_names}

現場問題
{question}

附件或文件摘要
{file_description if file_description else "未有附件或文件摘要。"}{multi_file_note}

分析重點
{focus_text}

相關參考
{regulation_text}

補充資料
{reference_text}

請只按以下章節輸出，每個章節保持短句。每個章節標題後換行，直接輸出內容。

{sections_text}
"""


def build_analysis_prompt(
    analysis_type: str,
    question: str,
    file_description: str,
    rag_context: str = "",
) -> str:
    routing = get_routing(analysis_type)
    professionals = get_required_professionals(analysis_type, question, file_description)
    focus_text = "，".join(routing["focus"])
    regulation_text = "，".join(routing["regulations"])
    professional_text = "，".join(professionals) if professionals else "按內容判斷，未有指定專業人士。"
    reference_text = rag_context if rag_context else "未有額外參考資料。"

    return f"""你是 HK-AICOS 香港工程顧問報告撰寫助手，由 Buildway Tech (HK) Limited 提供。

請用專業香港工程顧問報告語氣撰寫。
不得使用 Markdown。
不得使用井號、星號、項目符號、分隔線或粗體格式。
不得出現好的、以下是分析、我是AI、感謝使用等助手口吻。
不得提及模型、服務商、系統介面、開發、除錯或憑證字眼。

分析類型
{analysis_type}

現場問題
{question}

附件或文件摘要
{file_description if file_description else "未有附件或文件摘要。"}

分析重點
{focus_text}

相關參考
{regulation_text}

補充資料
{reference_text}

需確認人士
{professional_text}

請只按以下四個章節輸出，每個章節保持短句。

工程分析
用三至五行說明現場問題、涉及工序、責任範圍及需補充資料。

風險
用三至五行說明安全、進度、成本、合規或責任風險。

建議
用三至五行提出項目經理可即時跟進的建議。

處理方法
用三至五行說明即時處理、短期跟進及正式回覆前需確認事項。
"""
