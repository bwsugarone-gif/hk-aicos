"""
HK-AICOS Phase 2.0 agent routing.

The Agent Selector is driven by the full agent library. Prompts are generated
from the selected agents only, with optional file-backed instructions loaded
from the project-level agents directory.
"""

from pathlib import Path


AGENT_DEFINITIONS = {
    "accounting": {
        "id": "accounting",
        "name": "Accounting Agent",
        "display": "Accounting Agent",
        "icon": "AC",
        "label": "Accounting Agent",
        "desc": "檢視付款、發票、成本記錄、工資及會計風險。",
        "focus": ["付款及發票", "工資及成本記錄", "會計合規", "財務風險"],
        "regulations": ["Accounting", "Contract", "MPF"],
        "report_section": "Accounting Agent 分析",
        "instruction_files": ["agents-accounting-agent.md", "accounting-agent.md"],
        "fallback_instruction": "從會計、付款、發票、成本記錄及財務控制角度分析事項，指出金額、責任、證據及跟進建議。",
    },
    "drafting": {
        "id": "drafting",
        "name": "Drafting Agent",
        "display": "Drafting Agent",
        "icon": "DR",
        "label": "Drafting Agent",
        "desc": "檢視圖則、版本、標註、RFI 及設計文件一致性。",
        "focus": ["圖則版本", "設計文件", "RFI", "圖則不一致"],
        "regulations": ["Drawings", "RFI", "BIM"],
        "report_section": "Drafting Agent 分析",
        "instruction_files": ["agents-drafting-agent.md", "drafting-agent.md"],
        "fallback_instruction": "從圖則、設計文件、版本控制、標註及 RFI 角度分析，指出圖則差異及需澄清事項。",
    },
    "engineering": {
        "id": "engineering",
        "name": "Engineering Agent",
        "display": "Engineering Agent",
        "icon": "EN",
        "label": "Engineering Agent",
        "desc": "分析施工方法、進度、技術風險、工序及工程影響。",
        "focus": ["施工方法", "工程進度", "技術風險", "工序協調"],
        "regulations": ["BD", "EMSD", "CEDD", "HyD", "DSD", "WSD"],
        "report_section": "Engineering Agent 分析",
        "instruction_files": ["agents-engineering-agent.md", "engineering-agent.md"],
        "fallback_instruction": "從工程技術、施工方法、進度、工序協調及現場可行性角度分析，列出影響及跟進行動。",
    },
    "foreman": {
        "id": "foreman",
        "name": "Foreman Agent",
        "display": "Foreman Agent",
        "icon": "FM",
        "label": "Foreman Agent",
        "desc": "以地盤前線角度檢視人手、工序、現場狀況及即時安排。",
        "focus": ["地盤前線", "人手安排", "工序執行", "即時跟進"],
        "regulations": ["Site Management", "SOP"],
        "report_section": "Foreman Agent 分析",
        "instruction_files": ["agents-foreman-agent.md", "foreman-agent.md"],
        "fallback_instruction": "從地盤前線、人手、機具、材料到場、工序銜接及即日行動角度分析，提出可執行跟進。",
    },
    "material": {
        "id": "material",
        "name": "Material Agent",
        "display": "Material Agent",
        "icon": "MT",
        "label": "Material Agent",
        "desc": "檢視物料採購、到貨、測試、批核及品質文件。",
        "focus": ["物料採購", "物料到貨", "測試報告", "品質文件"],
        "regulations": ["Material", "QA/QC", "Procurement"],
        "report_section": "Material Agent 分析",
        "instruction_files": ["agents-material-agent.md", "material-agent.md"],
        "fallback_instruction": "從物料採購、到貨、批核、測試報告、品質文件及替代物料風險角度分析。",
    },
    "pm": {
        "id": "pm",
        "name": "PM Agent",
        "display": "PM Agent",
        "icon": "PM",
        "label": "PM Agent",
        "desc": "整合跨部門風險、責任、優先次序、進度及管理決策。",
        "focus": ["項目管理", "進度整合", "責任分工", "管理決策"],
        "regulations": ["Project Management", "Contract", "All departments"],
        "report_section": "PM Agent 分析",
        "instruction_files": ["agents-pm-agent.md", "pm-agent.md"],
        "fallback_instruction": "從項目管理、跨部門協調、責任分工、進度影響、客戶溝通及決策優先次序角度整合分析。",
    },
    "qs": {
        "id": "qs",
        "name": "QS Agent",
        "display": "QS Agent",
        "icon": "QS",
        "label": "QS Agent",
        "desc": "分析合約、VO、成本、付款、索償及工期金錢影響。",
        "focus": ["合約金額", "VO", "索償", "付款", "成本及工期影響"],
        "regulations": ["Contract", "QS", "VO"],
        "report_section": "QS Agent 分析",
        "instruction_files": ["agents-qs-agent.md", "qs-agent.md"],
        "fallback_instruction": "從合約、VO、付款、索償、成本及工期金錢影響角度分析，指出證據及商務跟進。",
    },
    "safety": {
        "id": "safety",
        "name": "Safety Agent",
        "display": "Safety Agent",
        "icon": "SF",
        "label": "Safety Agent",
        "desc": "分析安全風險、法定要求、PPE、事故預防及即時控制措施。",
        "focus": ["安全風險", "PPE", "高危工序", "事故預防", "即時控制措施"],
        "regulations": ["Labour", "FSD", "EMSD", "BD"],
        "report_section": "Safety Agent 分析",
        "instruction_files": ["agents-safety-agent.md", "safety-agent.md"],
        "fallback_instruction": "從安全風險、PPE、高危工序、法定安全要求、事故預防及即時控制措施角度分析。",
    },
    "surveying": {
        "id": "surveying",
        "name": "Surveying Agent",
        "display": "Surveying Agent",
        "icon": "SV",
        "label": "Surveying Agent",
        "desc": "檢視測量、放線、標高、尺寸偏差及監測記錄。",
        "focus": ["測量", "放線", "標高", "尺寸偏差", "監測記錄"],
        "regulations": ["Surveying", "Monitoring", "QA/QC"],
        "report_section": "Surveying Agent 分析",
        "instruction_files": ["agents-surveying-agent.md", "surveying-agent.md"],
        "fallback_instruction": "從測量、放線、標高、尺寸偏差、監測記錄及竣工資料角度分析，指出偏差及復核需要。",
    },
    "hk_legal": {
        "id": "hk_legal",
        "name": "HK Legal Layer",
        "display": "HK Legal Layer",
        "icon": "HK",
        "label": "HK Legal Layer",
        "desc": "檢視香港法規、合約責任、監管要求及法律風險。",
        "focus": ["香港法規", "合約責任", "監管要求", "法律風險"],
        "regulations": ["HK Legal", "BD", "Labour", "FSD", "EMSD", "EPD"],
        "report_section": "HK Legal Layer 分析",
        "instruction_files": ["regulationshk-legal-layer.md", "hk-legal-layer.md", "legal-agent.md"],
        "fallback_instruction": "從香港法律、監管要求、合約責任、法定通知、責任承擔及法律風險角度分析。",
    },
}

AGENT_ORDER = [
    "accounting",
    "drafting",
    "engineering",
    "foreman",
    "material",
    "pm",
    "qs",
    "safety",
    "surveying",
    "hk_legal",
]

DEFAULT_SELECTED_AGENTS = ["pm", "safety", "engineering"]


AGENT_ROUTING = {
    "安全風險分析": {
        "agents": ["Safety Agent", "PM Agent", "HK Legal Layer"],
        "focus": ["安全風險", "高危工序", "即時控制措施"],
        "regulations": ["Labour", "FSD", "BD"],
    },
    "工程及進度分析": {
        "agents": ["Engineering Agent", "Foreman Agent", "PM Agent"],
        "focus": ["施工方法", "工程進度", "工序協調"],
        "regulations": ["BD", "SOP"],
    },
    "合約及成本分析": {
        "agents": ["QS Agent", "Accounting Agent", "PM Agent"],
        "focus": ["VO", "成本", "付款", "索償"],
        "regulations": ["Contract", "QS"],
    },
    "綜合項目分析": {
        "agents": ["PM Agent", "Engineering Agent", "Safety Agent"],
        "focus": ["項目管理", "進度整合", "風險排序"],
        "regulations": ["All departments"],
    },
}


PROFESSIONAL_CONFIRMATION_TRIGGERS = {
    "PM Agent": ["重大", "高風險", "延誤", "停工", "客戶", "決策"],
    "Safety Agent": ["安全", "受傷", "PPE", "高空", "吊運", "事故"],
    "Engineering Agent": ["圖則", "施工", "工序", "結構", "進度", "技術"],
    "QS Agent": ["VO", "索償", "付款", "成本", "合約", "變更"],
    "HK Legal Layer": ["法律", "法例", "合規", "責任", "訴訟", "監管"],
}

EXTREME_RISK_TRIGGERS = ["死亡", "重傷", "停工", "倒塌", "火警", "訴訟", "重大索償"]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _agents_dir() -> Path:
    return _project_root() / "agents"


def _read_text_safely(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp950", "big5", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except Exception:
            continue
    return ""


def get_agent_instruction(agent_id: str) -> str:
    agent = AGENT_DEFINITIONS.get(agent_id)
    if not agent:
        return ""

    for filename in agent.get("instruction_files", []):
        path = _agents_dir() / filename
        if path.exists():
            content = _read_text_safely(path).strip()
            if content:
                return content

    return agent["fallback_instruction"]


def _normalise_analysis_type(analysis_type: str) -> str:
    text = str(analysis_type or "")
    if text in AGENT_ROUTING:
        return text
    if any(keyword in text for keyword in ["安全", "PPE", "事故"]):
        return "安全風險分析"
    if any(keyword in text for keyword in ["QS", "VO", "成本", "合約"]):
        return "合約及成本分析"
    if any(keyword in text for keyword in ["工程", "進度", "圖則", "施工"]):
        return "工程及進度分析"
    return "綜合項目分析"


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
        if any(keyword.lower() in combined_text.lower() for keyword in keywords):
            required.append(professional)
    return required


def get_agent_definitions() -> dict:
    return AGENT_DEFINITIONS


def get_agents_ordered() -> list:
    return [AGENT_DEFINITIONS[k] for k in AGENT_ORDER]


def _selected_agent_defs(selected_agent_ids: list) -> list:
    ids = selected_agent_ids or list(DEFAULT_SELECTED_AGENTS)
    return [AGENT_DEFINITIONS[aid] for aid in ids if aid in AGENT_DEFINITIONS]


def build_prompt_from_agents(
    selected_agent_ids: list,
    question: str,
    file_description: str,
    rag_context: str = "",
) -> str:
    """
    Build an analysis prompt dynamically from selected agents.
    Existing agents/*.md files are preferred as instructions. If a file cannot
    be read, the agent fallback instruction is used silently.
    """
    agents = _selected_agent_defs(selected_agent_ids)
    selected_names = "、".join(agent["display"] for agent in agents)

    focus_items = []
    regulation_items = []
    for agent in agents:
        for item in agent["focus"]:
            if item not in focus_items:
                focus_items.append(item)
        for item in agent["regulations"]:
            if item not in regulation_items:
                regulation_items.append(item)

    instruction_blocks = []
    output_sections = []
    for agent in agents:
        instruction = get_agent_instruction(agent["id"])
        instruction_blocks.append(
            f"Agent：{agent['display']}\n"
            f"Instruction：\n{instruction}"
        )
        output_sections.append(
            f"{agent['report_section']}\n"
            f"請只輸出與 {agent['display']} 職責相關的重點、風險、影響及跟進建議。"
        )

    reference_text = rag_context.strip() if rag_context else "沒有額外參考資料。"

    return f"""你是 HK-AICOS 工程分析系統，代表 Buildway Tech (HK) Limited 生成客戶可讀的繁體中文分析報告。
請根據用戶選擇的 Agent 動態分析，不要加入未被選中的 Agent 章節。
不要輸出大量 Markdown 符號，例如 #、##、**、===、---。
不要提及 backend、prompt、model、API、debug 或系統內部字眼。
語氣要專業、直接、可交付，重點放在工程事實、風險、責任、影響及下一步行動。

已選擇 Agent：
{selected_names}

用戶問題：
{question}

文件或相片資料：
{file_description if file_description else "沒有上載文件或相片資料。"}

重點分析範圍：
{"、".join(focus_items)}

相關規例或資料層：
{"、".join(regulation_items)}

參考資料：
{reference_text}

Agent instructions：
{chr(10).join(instruction_blocks)}

請按以下次序輸出，每個標題使用原文，不要使用 Markdown 標題符號：
{chr(10).join(output_sections)}
"""


def build_analysis_prompt(
    analysis_type: str,
    question: str,
    file_description: str,
    rag_context: str = "",
) -> str:
    routing = get_routing(analysis_type)
    route_agents = []
    for name in routing["agents"]:
        for agent_id, agent in AGENT_DEFINITIONS.items():
            if agent["display"] == name:
                route_agents.append(agent_id)
                break
    return build_prompt_from_agents(route_agents, question, file_description, rag_context)
