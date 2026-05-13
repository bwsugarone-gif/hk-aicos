"""
agent_router.py
HK-AICOS Phase 2.0 - Agent Routing Logic

Routes analysis requests to appropriate agents based on analysis type.
Clients never see agent names - this is internal routing only.
"""

# Analysis type to agent mapping
AGENT_ROUTING = {
    "安全風險分析": {
        "agents": ["Safety Agent", "PM Agent", "Legal Agent"],
        "focus": ["site_safety", "risk_assessment", "legal_compliance"],
        "regulations": ["hk-labour-layer", "hk-fsd-layer"],
        "risk_keywords": ["高空", "密閉空間", "吊運", "電力", "危險品", "腳手架", "工人籠"],
    },
    "圖紙 / CAP / MIB 分析": {
        "agents": ["Drafting Agent", "Engineering Agent", "Surveying Agent", "PM Agent", "Legal Agent"],
        "focus": ["drawing_review", "structural_check", "compliance_check"],
        "regulations": ["hk-bd-layer", "hk-emsd-layer"],
        "risk_keywords": ["結構", "承重", "改動", "認可人士", "AP", "RSE"],
    },
    "工程進度分析": {
        "agents": ["Engineering Agent", "Foreman Agent", "PM Agent"],
        "focus": ["progress_tracking", "delay_analysis", "resource_planning"],
        "regulations": ["hk-labour-layer"],
        "risk_keywords": ["延誤", "工期", "分判", "工序"],
    },
    "法規 / 合規檢查": {
        "agents": ["Legal Agent", "PM Agent"],
        "focus": ["regulatory_compliance", "legal_review", "permit_check"],
        "regulations": ["hk-bd-layer", "hk-emsd-layer", "hk-epd-layer", "hk-labour-layer",
                        "hk-fsd-layer", "hk-wsd-layer", "hk-landsd-layer", "hk-hyd-layer",
                        "hk-cedd-layer", "hk-dsd-layer", "hk-td-layer", "hk-legal-layer"],
        "risk_keywords": ["法例", "牌照", "許可證", "政府", "部門", "條例"],
    },
    "臨時設施位置分析": {
        "agents": ["Engineering Agent", "Safety Agent", "Surveying Agent", "PM Agent", "Legal Agent"],
        "focus": ["temporary_works", "crane_positioning", "access_safety"],
        "regulations": ["hk-labour-layer", "hk-bd-layer", "hk-emsd-layer"],
        "risk_keywords": ["天秤", "塔吊", "工人籠", "人貨升降機", "臨時平台", "臨時支撐", "吊運"],
    },
    "成本 / 工期影響分析": {
        "agents": ["QS Agent", "Engineering Agent", "PM Agent", "Accounting Agent"],
        "focus": ["cost_analysis", "programme_impact", "vo_assessment"],
        "regulations": ["hk-legal-layer"],
        "risk_keywords": ["VO", "索償", "合約", "費用", "預算", "工期"],
    },
    "PM 綜合分析": {
        "agents": ["PM Agent", "Engineering Agent", "Safety Agent", "QS Agent", "Legal Agent"],
        "focus": ["comprehensive_review", "risk_management", "decision_support"],
        "regulations": ["hk-bd-layer", "hk-labour-layer", "hk-legal-layer"],
        "risk_keywords": ["綜合", "整體", "決策", "風險管理"],
    },
}

# High-risk keywords that always trigger L4 (Extreme Risk)
EXTREME_RISK_TRIGGERS = [
    "死亡", "嚴重受傷", "結構倒塌", "火警", "爆炸", "觸電", "高壓",
    "訴訟", "律師信", "法庭", "刑事", "掘路", "公共道路損壞",
]

# Keywords requiring professional confirmation
PROFESSIONAL_CONFIRMATION_TRIGGERS = {
    "認可人士 (AP)": ["結構", "承重牆", "建築改動", "圖則審批", "屋宇署"],
    "註冊結構工程師 (RSE)": ["結構計算", "基礎", "深開挖", "斜坡"],
    "岩土工程師 (RGE)": ["斜坡", "土力", "地基", "深開挖"],
    "註冊電業工程人員 (REW)": ["電力", "電氣", "高壓", "電力系統", "機電"],
    "消防工程師": ["消防", "火警系統", "逃生", "危險品"],
    "持牌水喉匠": ["食水", "水喉", "水務", "排水"],
    "香港律師": ["法律責任", "訴訟", "合約爭議", "索償", "律師信"],
    "安全主任": ["工傷", "安全事故", "危險工序", "高空工作"],
}


def get_routing(analysis_type: str) -> dict:
    """Get routing configuration for a given analysis type."""
    return AGENT_ROUTING.get(analysis_type, AGENT_ROUTING["PM 綜合分析"])


def get_all_analysis_types() -> list:
    """Return list of all available analysis types for UI display."""
    return list(AGENT_ROUTING.keys())


def check_extreme_risk(text: str) -> bool:
    """Check if input contains extreme risk keywords."""
    text_lower = text.lower()
    return any(kw in text for kw in EXTREME_RISK_TRIGGERS)


def get_required_professionals(analysis_type: str, question: str, file_description: str = "") -> list:
    """Determine which professionals need to confirm based on content."""
    combined_text = f"{analysis_type} {question} {file_description}"
    required = []
    for professional, keywords in PROFESSIONAL_CONFIRMATION_TRIGGERS.items():
        if any(kw in combined_text for kw in keywords):
            required.append(professional)
    return required


def build_analysis_prompt(
    analysis_type: str,
    question: str,
    file_description: str,
    rag_context: str = "",
) -> str:
    """
    Build the analysis prompt for the selected analysis type.
    This is the core prompt sent to the AI model.
    """
    routing = get_routing(analysis_type)
    professionals = get_required_professionals(analysis_type, question, file_description)

    prompt = f"""你是 HK-AICOS AI 建築工程分析系統，由 Buildway Tech (HK) Limited 提供。

## 分析任務
分析類型：{analysis_type}
用戶問題：{question}
上傳文件描述：{file_description if file_description else "無上傳文件"}

## 分析重點
{chr(10).join(f"- {f}" for f in routing["focus"])}

## 相關法規參考
{chr(10).join(f"- {r}" for r in routing["regulations"])}

{"## RAG 參考資料" + chr(10) + rag_context if rag_context else ""}

## 輸出要求
請按以下格式提供專業分析報告：

### 1. 輸入資料摘要
簡述收到的資料及問題。

### 2. 工程分析
從工程技術角度分析。

### 3. 安全分析
識別安全風險及建議措施。

### 4. 法規 / 合規分析
列出相關香港法例及政府部門要求。

### 5. 成本及工期影響
評估對成本及工期的潛在影響。

### 6. 風險級別
評定風險級別：低風險 / 中風險 / 高風險 / 極高風險
並說明原因。

### 7. 建議跟進事項
列出具體建議行動（按優先次序）。

### 8. 需要人工確認事項
列出需要人類 PM 確認的事項。

### 9. 需要香港合資格人士確認
{"需要以下專業人士確認：" + chr(10) + chr(10).join(f"- {p}" for p in professionals) if professionals else "本分析暫時不需要特定專業人士確認，但如有疑問請諮詢相關專業人士。"}

## 重要提示
- 分析僅供 AI 輔助參考
- 不可取代專業人士判斷
- 高風險事項必須由人類 PM 最終確認
"""
    return prompt
