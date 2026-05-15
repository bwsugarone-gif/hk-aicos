"""
HK-AICOS Phase 2.0 PDF report generator.

Client-facing reports are rendered as clean consultant-style Chinese text.
No markdown symbols, bullets, model names, debug wording, or assistant wording
should appear in the PDF body.
"""

import io
import re
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


pdfmetrics.registerFont(UnicodeCIDFont("MSung-Light"))
FONT = "MSung-Light"

DARK_BLUE = colors.HexColor("#1a3a5c")
MID_BLUE = colors.HexColor("#2d5a8e")
GOLD = colors.HexColor("#c9a84c")
BG_GREY = colors.HexColor("#f7f9fc")
BORDER_GREY = colors.HexColor("#d0d7e3")
TEXT_DARK = colors.HexColor("#1a1a2e")
TEXT_MID = colors.HexColor("#444466")

REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

RISK_ALIASES = {
    "低": "低風險",
    "低風險": "低風險",
    "中": "中風險",
    "中風險": "中風險",
    "高": "高風險",
    "高風險": "高風險",
    "緊急": "高風險",
    "極高": "高風險",
}

RISK_COLOR = {
    "低風險": colors.HexColor("#1a7a3c"),
    "中風險": colors.HexColor("#b85c00"),
    "高風險": colors.HexColor("#c0152a"),
}

RISK_BG = {
    "低風險": colors.HexColor("#e6f4ec"),
    "中風險": colors.HexColor("#fff4e0"),
    "高風險": colors.HexColor("#fde8eb"),
}

RISK_DESC = {
    "低風險": "一般跟進事項，按正常項目流程處理。",
    "中風險": "可能影響安全、進度、成本或合規，建議由項目經理確認。",
    "高風險": "可能涉及安全、法規、工期、成本或責任風險，需優先處理及保留紀錄。",
}

AI_STYLE_PHRASES = (
    "好的",
    "以下是分析",
    "我是AI",
    "我是 AI",
    "感謝使用",
    "作為AI",
    "作為 AI",
    "我會為你",
    "我可以幫你",
)

BANNED_TECH_PATTERNS = (
    "DEMO MODE",
    "Claude",
    "Anthropic",
    "API",
    "backend",
    "debug",
    "token",
    "OpenAI",
    "Gemini",
    "LLM",
    "prompt",
    "system prompt",
    "developer",
    "No API Key",
)

MARKDOWN_LINE_PREFIX = re.compile(r"^\s{0,4}(#{1,6}|\*+|-+|=+|•+)\s*")
MARKDOWN_INLINE = re.compile(r"[*_`>#]+")


def _styles() -> dict:
    base = getSampleStyleSheet()

    def ps(name, **kw):
        return ParagraphStyle(name, parent=base["Normal"], fontName=FONT, **kw)

    return {
        "company": ps("company", fontSize=13, textColor=colors.white, alignment=TA_CENTER, leading=18),
        "title": ps("title", fontSize=20, textColor=colors.white, alignment=TA_CENTER, leading=26),
        "meta_label": ps("meta_label", fontSize=10, textColor=DARK_BLUE, leading=15),
        "meta_value": ps("meta_value", fontSize=10, textColor=TEXT_DARK, leading=15),
        "section": ps("section", fontSize=14, textColor=DARK_BLUE, leading=20, spaceBefore=7, spaceAfter=4),
        "body": ps("body", fontSize=11, textColor=TEXT_DARK, leading=19, spaceAfter=5, alignment=TA_LEFT),
        "subtle": ps("subtle", fontSize=9, textColor=TEXT_MID, leading=14, alignment=TA_CENTER),
        "risk": ps("risk", fontSize=17, leading=23, alignment=TA_CENTER),
        "notice": ps("notice", fontSize=10, textColor=colors.HexColor("#5a3e00"), leading=16),
        "footer": ps("footer", fontSize=8, textColor=colors.HexColor("#888888"), leading=12, alignment=TA_CENTER),
    }


def _escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def _p(text: str, style) -> Paragraph:
    return Paragraph(_escape(text), style)


def _normalise_risk(risk_level: str) -> str:
    raw = str(risk_level or "").strip()
    for key, value in RISK_ALIASES.items():
        if key in raw:
            return value
    return "中風險"


def _clean_report_text(text: str) -> str:
    cleaned_lines = []
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if any(pattern.lower() in line.lower() for pattern in BANNED_TECH_PATTERNS):
            continue

        for phrase in AI_STYLE_PHRASES:
            line = line.replace(phrase, "")

        line = MARKDOWN_LINE_PREFIX.sub("", line)
        line = MARKDOWN_INLINE.sub("", line)
        line = re.sub(r"\s+", " ", line).strip()

        if line:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def _section_header(title: str, story: list, st: dict):
    story.append(Spacer(1, 4 * mm))
    story.append(_p(title, st["section"]))


def _add_clean_lines(story: list, text: str, st: dict, fallback: str = "未有補充資料。"):
    cleaned = _clean_report_text(text)
    if not cleaned:
        cleaned = fallback
    for line in cleaned.splitlines():
        story.append(_p(line, st["body"]))


# Keyword → department mapping table (order matters: first match wins for dedup)
_DEPT_MAPPING = [
    # 勞工處
    (("工地安全", "高空工作", "棚架", "竹棚", "金屬棚", "工人安全",
      "高空", "工作台", "防墮", "安全帶", "工傷", "受傷"), "勞工處"),
    # 屋宇署
    (("結構", "樓宇", "僭建", "改則", "樑", "柱", "樓板", "改動", "外牆架"), "屋宇署"),
    # 消防處
    (("消防", "走火通道", "消防裝置", "火警", "滅火", "排煙"), "消防處"),
    # EMSD
    (("電力", "機電", "升降機", "臨時電", "電箱", "電線"), "EMSD"),
    # 水務署
    (("水管", "供水", "水錶", "食水", "水喉", "水務"), "水務署"),
    # 渠務署
    (("排水", "污水", "渠務", "污水渠", "雨水渠"), "渠務署"),
    # 路政署
    (("掘路", "道路", "行人路", "行車道", "路面"), "路政署"),
    # 運輸署
    (("交通改道", "臨時交通安排", "臨時交通", "交通管制"), "運輸署"),
    # 地政總署
    (("土地", "政府地", "短期租約", "地政", "官地"), "地政總署"),
    # 環保署
    (("環保", "噪音", "廢料", "污水排放", "廢棄物", "環境污染"), "環保署"),
    # CEDD / GEO
    (("土力", "斜坡", "擋土牆", "岩土", "山泥", "地基"), "CEDD / GEO"),
]


def _department_mapping(text: str) -> list:
    content = str(text or "")
    departments = []
    for keywords, department in _DEPT_MAPPING:
        if any(keyword in content for keyword in keywords) and department not in departments:
            departments.append(department)
    return departments


# ── Agent section definitions for dynamic PDF rendering ──────────────────────
# Maps agent_id → (section_title, fallback_text)
AGENT_SECTION_MAP = {
    "safety": (
        "安全風險分析",
        "現階段未有足夠資料作安全風險分析。",
    ),
    "pm": (
        "PM 工程進度分析",
        "現階段未有足夠資料作工程進度分析。",
    ),
    "qs": (
        "成本及工期影響分析",
        "現階段未有足夠資料作成本及工期影響分析。",
    ),
    "legal": (
        "法規及合規分析",
        "現階段未有足夠資料作法規及合規分析。",
    ),
    "risk": (
        "綜合風險評估",
        "現階段未有足夠資料作綜合風險評估。",
    ),
}

AGENT_ORDER_PDF = ["safety", "pm", "qs", "legal", "risk"]


def _split_agent_sections(analysis_result: str, selected_agents: list) -> dict:
    """
    Split the AI output into per-agent sections by matching section headers.
    Returns dict of {agent_id: section_text}.
    Falls back to putting all text under the first agent if no headers found.
    """
    from utils.agent_router import AGENT_DEFINITIONS

    sections = {}
    text = _clean_report_text(analysis_result)

    for agent_id in selected_agents:
        if agent_id not in AGENT_DEFINITIONS:
            continue
        section_title = AGENT_DEFINITIONS[agent_id]["report_section"]
        # Find the section in the text
        idx = text.find(section_title)
        if idx != -1:
            # Find the end: next known section title or end of text
            end_idx = len(text)
            for other_id in selected_agents:
                if other_id == agent_id or other_id not in AGENT_DEFINITIONS:
                    continue
                other_title = AGENT_DEFINITIONS[other_id]["report_section"]
                other_idx = text.find(other_title, idx + len(section_title))
                if other_idx != -1 and other_idx < end_idx:
                    end_idx = other_idx
            section_text = text[idx + len(section_title):end_idx].strip()
            sections[agent_id] = section_text
        else:
            sections[agent_id] = ""

    # If no sections were found at all, put everything under the first agent
    if all(v == "" for v in sections.values()) and selected_agents:
        sections[selected_agents[0]] = text

    return sections


def generate_pdf_report(
    analysis_type: str,
    question: str,
    risk_level: str,
    analysis_result: str,
    filename_hint: str = "",
    professionals_required: list = None,
    project_ref: str = "",
    selected_agents: list = None,
) -> bytes:
    st = _styles()
    now = datetime.now()
    report_id = f"RPT-{now.strftime('%Y%m%d-%H%M%S')}"
    clean_risk = _normalise_risk(risk_level)
    combined_text = "\n".join([analysis_type or "", question or "", analysis_result or ""])
    departments = _department_mapping(combined_text)

    # Determine which agents to render sections for
    if not selected_agents:
        selected_agents = AGENT_ORDER_PDF

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"HK-AICOS 工程分析報告 {report_id}",
        author="Buildway Tech (HK) Limited",
    )

    width = 174 * mm
    story = []

    company_bar = Table([[_p("Buildway Tech (HK) Limited", st["company"])]], colWidths=[width])
    company_bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK_BLUE),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    title_bar = Table([[_p("HK-AICOS 工程分析報告", st["title"])]], colWidths=[width])
    title_bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), MID_BLUE),
        ("TOPPADDING", (0, 0), (-1, -1), 13),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 13),
    ]))
    accent = Table([[""]], colWidths=[width], rowHeights=[4])
    accent.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GOLD)]))

    story.extend([company_bar, title_bar, accent, Spacer(1, 6 * mm)])

    # Build agent label string for metadata
    try:
        from utils.agent_router import AGENT_DEFINITIONS as _AD
        agent_labels = "、".join(
            _AD[aid]["display"] for aid in selected_agents if aid in _AD
        )
    except Exception:
        agent_labels = "、".join(selected_agents)

    dept_meta_value = "、".join(departments) if departments else "需由相關專業人士確認實際監管部門"
    meta_rows = [
        ("報告編號", report_id),
        ("報告日期", now.strftime("%Y-%m-%d %H:%M")),
        ("分析類型", _clean_report_text(analysis_type) or "工程分析"),
        ("參與 Agent", agent_labels or "全部"),
        ("項目編號", _clean_report_text(project_ref) or "待確認"),
        ("參考文件", _clean_report_text(filename_hint) or "待確認"),
        ("可能涉及部門", dept_meta_value),
        ("風險級別", clean_risk),
    ]
    meta_table = Table(
        [[_p(label, st["meta_label"]), _p(value, st["meta_value"])] for label, value in meta_rows],
        colWidths=[34 * mm, 140 * mm],
    )
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eaf0fb")),
        ("BACKGROUND", (1, 7), (1, 7), RISK_BG[clean_risk]),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_GREY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6 * mm))

    risk_table = Table(
        [[_p(clean_risk, ParagraphStyle("risk_value", fontName=FONT, fontSize=18, alignment=TA_CENTER, textColor=RISK_COLOR[clean_risk], leading=24))],
         [_p(RISK_DESC[clean_risk], st["subtle"])]],
        colWidths=[width],
    )
    risk_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), RISK_BG[clean_risk]),
        ("BOX", (0, 0), (-1, -1), 1.2, RISK_COLOR[clean_risk]),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(risk_table)

    # ── Dynamic agent sections ────────────────────────────────────────────────
    agent_sections = _split_agent_sections(analysis_result, selected_agents)

    for agent_id in selected_agents:
        if agent_id not in AGENT_SECTION_MAP:
            continue
        section_title, fallback = AGENT_SECTION_MAP[agent_id]
        _section_header(section_title, story, st)
        section_text = agent_sections.get(agent_id, "")
        _add_clean_lines(story, section_text, st, fallback=fallback)

    # ── Departments ───────────────────────────────────────────────────────────
    _section_header("可能涉及部門", story, st)
    if departments:
        for department in departments:
            story.append(_p(department, st["body"]))
        story.append(_p("如不確定，需由相關專業人士確認實際監管部門。", st["body"]))
    else:
        story.append(_p("需由相關專業人士確認實際監管部門。", st["body"]))

    if professionals_required:
        _section_header("需確認人士", story, st)
        for professional in professionals_required:
            story.append(_p(_clean_report_text(professional), st["body"]))

    story.append(Spacer(1, 6 * mm))
    notice = (
        "本報告供項目管理及工程跟進使用。正式行動、對外回覆及合約立場，"
        "須由項目經理及相關合資格專業人士確認。"
    )
    notice_table = Table([[_p(notice, st["notice"])]], colWidths=[width])
    notice_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff7dc")),
        ("BOX", (0, 0), (-1, -1), 0.8, GOLD),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
    ]))
    story.append(notice_table)

    story.append(Spacer(1, 5 * mm))
    story.append(_p(f"Buildway Tech (HK) Limited  {now.strftime('%Y-%m-%d %H:%M')}  {report_id}", st["footer"]))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def save_report(pdf_bytes: bytes, report_id: str = "") -> Path:
    if not report_id:
        report_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"HK-AICOS-Report-{report_id}.pdf"
    path = REPORTS_DIR / filename
    path.write_bytes(pdf_bytes)
    return path
