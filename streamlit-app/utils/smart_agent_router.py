"""
utils/smart_agent_router.py
HK-AICOS Phase 2.5H — Smart Agent Activation Layer

Analyses uploaded file types, extracted text, and user question to
recommend the most relevant agents. Prevents all agents firing on
insufficient data.

Buildway Tech (HK) Limited
"""

from __future__ import annotations
from typing import Literal

# ── Sufficiency score type ────────────────────────────────────────────────────
SufficiencyScore = Literal["sufficient", "partial", "insufficient"]


# ── Keyword maps for file-content-based routing ───────────────────────────────

_QUESTION_KEYWORDS: dict[str, list[str]] = {
    "safety": [
        "安全", "safety", "ppe", "高空", "吊運", "事故", "受傷", "危險", "風險",
        "防護", "安全帶", "scaffolding", "fall", "hazard", "risk",
    ],
    "engineering": [
        "工程", "施工", "工序", "進度", "技術", "結構", "method", "construction",
        "programme", "sequence", "structural", "foundation", "concrete",
    ],
    "foreman": [
        "地盤", "前線", "人手", "工人", "現場", "即時", "site", "worker",
        "labour", "manpower", "foreman", "supervisor",
    ],
    "drafting": [
        "圖則", "圖紙", "drawing", "rfi", "設計", "版本", "標註", "bim",
        "plan", "section", "elevation", "detail", "revision",
    ],
    "surveying": [
        "測量", "放線", "標高", "偏差", "監測", "survey", "level", "setting out",
        "monitoring", "tolerance", "dimension",
    ],
    "qs": [
        "合約", "VO", "成本", "付款", "索償", "報價", "contract", "variation",
        "claim", "payment", "cost", "tender", "bill",
    ],
    "accounting": [
        "發票", "invoice", "工資", "salary", "wage", "會計", "accounting",
        "mpf", "payroll", "receipt", "financial",
    ],
    "material": [
        "物料", "材料", "採購", "到貨", "delivery", "material", "po",
        "purchase order", "inventory", "stock", "supplier", "品質",
    ],
    "pm": [
        "項目", "管理", "進度", "協調", "決策", "project", "management",
        "programme", "coordination", "milestone", "delay",
    ],
    "hk_legal": [
        "法規", "法例", "permit", "許可", "政府", "government", "approval",
        "合規", "compliance", "ordinance", "regulation", "bd", "emsd",
        "labour department", "fsd", "epd", "wsd",
    ],
}

# File-type routing rules: (file_type_set, content_keywords) → recommended agents
_FILE_TYPE_RULES: list[tuple[set[str], list[str], list[str]]] = [
    # (file_types, content_keywords_any, recommended_agents)
    # Image / site photo
    ({"image"}, [], ["safety", "foreman", "engineering"]),

    # Excel — cost / payment / wages
    ({"xlsx"}, ["成本", "cost", "payment", "付款", "工資", "wage", "salary", "報價", "tender", "invoice", "發票"],
     ["qs", "accounting", "pm"]),
    ({"xlsx"}, ["物料", "material", "delivery", "po", "inventory", "採購"],
     ["material", "qs", "pm"]),
    ({"xlsx"}, [], ["qs", "accounting", "pm"]),  # default for xlsx

    # PDF — method statement / risk assessment
    ({"pdf"}, ["method statement", "施工方法", "risk assessment", "安全評估", "ms&ra", "msra"],
     ["pm", "safety", "engineering", "hk_legal"]),
    ({"pdf"}, ["drawing", "圖則", "圖紙", "plan", "section", "elevation", "rfi"],
     ["drafting", "engineering", "surveying", "safety"]),
    ({"pdf"}, ["contract", "合約", "vo", "variation", "payment", "付款", "claim", "索償"],
     ["qs", "pm", "hk_legal"]),
    ({"pdf"}, ["permit", "許可", "approval", "政府", "government", "ordinance", "法規"],
     ["hk_legal", "pm", "safety"]),
    ({"pdf"}, [], ["pm", "safety", "engineering"]),  # default for pdf

    # DOCX — similar to PDF
    ({"docx"}, ["method statement", "施工方法", "risk assessment", "安全評估"],
     ["pm", "safety", "engineering", "hk_legal"]),
    ({"docx"}, ["contract", "合約", "vo", "variation", "payment", "付款"],
     ["qs", "pm", "hk_legal"]),
    ({"docx"}, [], ["pm", "safety", "engineering"]),  # default for docx

    # Multi-file: use question keywords primarily
    ({"multi"}, [], ["pm", "safety", "engineering"]),
]

# Analysis-type → default agents
_ANALYSIS_TYPE_DEFAULTS: dict[str, list[str]] = {
    "安全風險分析":   ["safety", "pm", "engineering"],
    "工程及進度分析": ["engineering", "foreman", "pm"],
    "合約及成本分析": ["qs", "accounting", "pm"],
    "綜合項目分析":   ["pm", "safety", "engineering"],
}


# ── Core routing function ─────────────────────────────────────────────────────

def recommend_agents(
    file_type: str,
    file_content: str,
    question: str,
    analysis_type: str,
) -> list[str]:
    """
    Return a list of recommended agent IDs based on file type, content, and question.

    Priority:
    1. File-type + content keyword rules
    2. Question keyword boosting
    3. Analysis-type defaults as fallback
    """
    file_type_norm = (file_type or "").lower().strip()
    content_lower  = (file_content or "").lower()
    question_lower = (question or "").lower()
    combined_lower = content_lower + " " + question_lower

    recommended: list[str] = []

    # Step 1: File-type rules
    for file_types, content_kws, agents in _FILE_TYPE_RULES:
        if file_type_norm not in file_types:
            continue
        if not content_kws:
            # Default rule for this file type — use if no better rule matched yet
            if not recommended:
                recommended = list(agents)
            break
        if any(kw in combined_lower for kw in content_kws):
            recommended = list(agents)
            break

    # Step 2: Question keyword boosting — add agents not yet in list
    for agent_id, keywords in _QUESTION_KEYWORDS.items():
        if agent_id not in recommended:
            if any(kw in question_lower for kw in keywords):
                recommended.append(agent_id)

    # Step 3: Fallback to analysis-type defaults
    if not recommended:
        recommended = list(
            _ANALYSIS_TYPE_DEFAULTS.get(analysis_type, ["pm", "safety", "engineering"])
        )

    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for aid in recommended:
        if aid not in seen:
            seen.add(aid)
            result.append(aid)

    return result


# ── Context sufficiency scoring ───────────────────────────────────────────────

def score_agent_sufficiency(
    agent_id: str,
    file_type: str,
    file_content: str,
    question: str,
) -> SufficiencyScore:
    """
    Score how much context is available for a given agent.

    sufficient   — clear signals in file content or question
    partial      — some signals, agent can contribute partially
    insufficient — no relevant signals at all
    """
    content_lower  = (file_content or "").lower()
    question_lower = (question or "").lower()
    combined       = content_lower + " " + question_lower
    file_type_norm = (file_type or "").lower()

    keywords = _QUESTION_KEYWORDS.get(agent_id, [])
    hit_count = sum(1 for kw in keywords if kw in combined)

    # Image-specific agents always get at least partial for images
    if file_type_norm == "image" and agent_id in ("safety", "foreman", "engineering"):
        return "sufficient" if hit_count >= 1 else "partial"

    # Excel-specific agents
    if file_type_norm == "xlsx" and agent_id in ("qs", "accounting", "material"):
        return "sufficient" if hit_count >= 1 else "partial"

    # PM agent always gets partial if any file is present
    if agent_id == "pm" and (file_content or file_type_norm):
        return "sufficient" if hit_count >= 2 else "partial"

    if hit_count >= 3:
        return "sufficient"
    if hit_count >= 1:
        return "partial"
    return "insufficient"


def filter_agents_by_sufficiency(
    agent_ids: list[str],
    file_type: str,
    file_content: str,
    question: str,
) -> tuple[list[str], list[str], list[str]]:
    """
    Split agents into three buckets.

    Returns:
        (sufficient_agents, partial_agents, insufficient_agents)
    Only sufficient + partial agents should appear in the main report.
    Insufficient agents are logged to incident/debug report only.
    """
    sufficient: list[str] = []
    partial:    list[str] = []
    insufficient: list[str] = []

    for aid in agent_ids:
        score = score_agent_sufficiency(aid, file_type, file_content, question)
        if score == "sufficient":
            sufficient.append(aid)
        elif score == "partial":
            partial.append(aid)
        else:
            insufficient.append(aid)

    return sufficient, partial, insufficient


def build_insufficient_notice(agent_ids: list[str], agent_definitions: dict) -> str:
    """
    Build a short incident-report notice for insufficient agents.
    Never included in the main report — only in debug/incident log.
    """
    if not agent_ids:
        return ""
    lines = ["【資料不足 Agent 記錄】"]
    for aid in agent_ids:
        label = agent_definitions.get(aid, {}).get("label", aid)
        lines.append(f"- {label}：本次資料不足以進行此 Agent 分析。")
    return "\n".join(lines)
