# -*- coding: utf-8 -*-
"""
HK-AICOS Phase 2.0 PDF report generator.

PDF generation strategy:
  1. Build a UTF-8 HTML document (saved as debug_report.html for inspection)
  2. Convert to PDF using reportlab with NotoSansCJKtc-Regular.otf embedded
     via TTFont — font is fully embedded so Chinese renders on iPhone/Android.

  WeasyPrint is NOT used because it requires GTK/Pango native libraries that
  are unavailable on Windows and Streamlit Cloud without extra system setup.
  ReportLab TTFont embedding is the correct cross-platform solution.
"""

import io
import re
import sys
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# ── UTF-8 stdout/stderr (Windows) ─────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ── Paths ─────────────────────────────────────────────────────────────────────
_BASE_DIR   = Path(__file__).parent.parent          # streamlit-app/
_FONTS_DIR  = _BASE_DIR / "assets" / "fonts"
_FONT_FILE  = _FONTS_DIR / "NotoSansCJKtc-Regular.otf"
REPORTS_DIR = _BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# ── Risk helpers ──────────────────────────────────────────────────────────────
RISK_ALIASES = {
    "低": "低風險", "低風險": "低風險",
    "中": "中風險", "中風險": "中風險",
    "高": "高風險", "高風險": "高風險",
    "緊急": "高風險", "極高": "高風險",
}

RISK_COLOR = {
    "低風險": "#1a7a3c",
    "中風險": "#b85c00",
    "高風險": "#c0152a",
}

RISK_BG = {
    "低風險": "#e6f4ec",
    "中風險": "#fff4e0",
    "高風險": "#fde8eb",
}

RISK_BORDER = {
    "低風險": "#28a745",
    "中風險": "#ffc107",
    "高風險": "#dc3545",
}

RISK_DESC = {
    "低風險": "一般跟進事項，按正常項目流程處理。",
    "中風險": "可能影響安全、進度、成本或合規，建議由項目經理確認。",
    "高風險": "可能涉及安全、法規、工期、成本或責任風險，需優先處理及保留紀錄。",
}

# ── Text-cleaning helpers ─────────────────────────────────────────────────────
AI_STYLE_PHRASES = (
    "好的", "以下是分析", "我是AI", "我是 AI", "感謝使用",
    "作為AI", "作為 AI", "我會為你", "我可以幫你",
)

BANNED_TECH_PATTERNS = (
    "DEMO MODE", "Claude", "Anthropic", "API", "backend", "debug",
    "token", "OpenAI", "Gemini", "LLM", "prompt", "system prompt",
    "developer", "No API Key",
)

MARKDOWN_LINE_PREFIX = re.compile(r"^\s{0,4}(#{1,6}|\*+|-+|=+|•+)\s*")
MARKDOWN_INLINE      = re.compile(r"[*_`>#]+")


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
        if any(p.lower() in line.lower() for p in BANNED_TECH_PATTERNS):
            continue
        for phrase in AI_STYLE_PHRASES:
            line = line.replace(phrase, "")
        line = MARKDOWN_LINE_PREFIX.sub("", line)
        line = MARKDOWN_INLINE.sub("", line)
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def _html_escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _lines_to_html(text: str, fallback: str = "未有補充資料。") -> str:
    cleaned = _clean_report_text(text)
    if not cleaned:
        cleaned = fallback
    return "".join(
        f"<p>{_html_escape(line)}</p>"
        for line in cleaned.splitlines()
        if line.strip()
    )


# ── Department mapping ────────────────────────────────────────────────────────
_DEPT_MAPPING = [
    (("工地安全","高空工作","棚架","竹棚","金屬棚","工人安全",
      "高空","工作台","防墮","安全帶","工傷","受傷"), "勞工處"),
    (("結構","樓宇","僭建","改則","樑","柱","樓板","改動","外牆架"), "屋宇署"),
    (("消防","走火通道","消防裝置","火警","滅火","排煙"), "消防處"),
    (("電力","機電","升降機","臨時電","電箱","電線"), "EMSD"),
    (("水管","供水","水錶","食水","水喉","水務"), "水務署"),
    (("排水","污水","渠務","污水渠","雨水渠"), "渠務署"),
    (("掘路","道路","行人路","行車道","路面"), "路政署"),
    (("交通改道","臨時交通安排","臨時交通","交通管制"), "運輸署"),
    (("土地","政府地","短期租約","地政","官地"), "地政總署"),
    (("環保","噪音","廢料","污水排放","廢棄物","環境污染"), "環保署"),
    (("土力","斜坡","擋土牆","岩土","山泥","地基"), "CEDD / GEO"),
]


def _department_mapping(text: str) -> list:
    content = str(text or "")
    departments = []
    for keywords, department in _DEPT_MAPPING:
        if any(k in content for k in keywords) and department not in departments:
            departments.append(department)
    return departments


# ── Agent definitions ─────────────────────────────────────────────────────────
AGENT_ORDER_PDF = [
    "accounting", "drafting", "engineering", "foreman", "material",
    "pm", "qs", "safety", "surveying", "hk_legal",
]

AGENT_SECTION_FALLBACKS = {
    "accounting": "未能取得 Accounting Agent 的完整段落，請補充付款、發票、成本及會計記錄後再分析。",
    "drafting":   "未能取得 Drafting Agent 的完整段落，請補充圖則、版本、RFI 或設計文件後再分析。",
    "engineering":"未能取得 Engineering Agent 的完整段落，請補充施工方法、進度或工程資料後再分析。",
    "foreman":    "未能取得 Foreman Agent 的完整段落，請補充現場人手、工序及即時安排後再分析。",
    "material":   "未能取得 Material Agent 的完整段落，請補充物料、到貨、測試及批核文件後再分析。",
    "pm":         "未能取得 PM Agent 的完整段落，請補充項目背景、責任分工及決策要求後再分析。",
    "qs":         "未能取得 QS Agent 的完整段落，請補充合約、VO、付款或成本資料後再分析。",
    "safety":     "未能取得 Safety Agent 的完整段落，請補充安全風險、工序及現場控制措施後再分析。",
    "surveying":  "未能取得 Surveying Agent 的完整段落，請補充測量、放線、標高或監測記錄後再分析。",
    "hk_legal":   "未能取得 HK Legal Layer 的完整段落，請補充法規、合約責任或監管要求後再分析。",
}


def _split_agent_sections(analysis_result: str, selected_agents: list) -> dict:
    from utils.agent_router import AGENT_DEFINITIONS

    sections = {}
    text = _clean_report_text(analysis_result)

    for agent_id in selected_agents:
        if agent_id not in AGENT_DEFINITIONS:
            continue
        section_title = AGENT_DEFINITIONS[agent_id]["report_section"]
        idx = text.find(section_title)
        if idx != -1:
            end_idx = len(text)
            for other_id in selected_agents:
                if other_id == agent_id or other_id not in AGENT_DEFINITIONS:
                    continue
                other_title = AGENT_DEFINITIONS[other_id]["report_section"]
                other_idx = text.find(other_title, idx + len(section_title))
                if other_idx != -1 and other_idx < end_idx:
                    end_idx = other_idx
            sections[agent_id] = text[idx + len(section_title):end_idx].strip()
        else:
            sections[agent_id] = ""

    if all(v == "" for v in sections.values()) and selected_agents:
        sections[selected_agents[0]] = text

    return sections


# ── HTML template ─────────────────────────────────────────────────────────────
def _build_html(
    report_id: str,
    now: datetime,
    analysis_type: str,
    question: str,
    risk_level: str,
    clean_risk: str,
    agent_labels: str,
    project_ref: str,
    filename_hint: str,
    departments: list,
    agent_sections_html: str,
    dept_html: str,
    professionals_html: str,
    font_path: str,
) -> str:
    risk_color  = RISK_COLOR[clean_risk]
    risk_bg     = RISK_BG[clean_risk]
    risk_border = RISK_BORDER[clean_risk]
    risk_desc   = RISK_DESC[clean_risk]
    dept_meta   = "、".join(departments) if departments else "需由相關專業人士確認實際監管部門"

    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>HK-AICOS 工程分析報告 {_html_escape(report_id)}</title>
<style>
/* ── Font embedding ── */
@font-face {{
    font-family: 'NotoSansCJKTC';
    src: url('{font_path}') format('opentype');
    font-weight: normal;
    font-style: normal;
}}

/* ── Global ── */
* {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}}
html, body {{
    font-family: 'NotoSansCJKTC', sans-serif;
    font-size: 11pt;
    color: #1a1a2e;
    background: #ffffff;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
}}

/* ── Page layout ── */
@page {{
    size: A4;
    margin: 15mm 18mm;
}}

/* ── Header ── */
.header-company {{
    background: #1a3a5c;
    color: #ffffff;
    text-align: center;
    padding: 9pt 0;
    font-size: 13pt;
}}
.header-title {{
    background: #2d5a8e;
    color: #ffffff;
    text-align: center;
    padding: 13pt 0;
    font-size: 20pt;
}}
.header-accent {{
    background: #c9a84c;
    height: 4pt;
}}

/* ── Meta table ── */
.meta-table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 14pt;
    margin-bottom: 14pt;
}}
.meta-table td {{
    padding: 7pt 8pt;
    border: 0.5pt solid #d0d7e3;
    vertical-align: middle;
    font-size: 10pt;
}}
.meta-table .label {{
    background: #eaf0fb;
    color: #1a3a5c;
    width: 80pt;
    font-weight: bold;
}}
.meta-table .value {{
    color: #1a1a2e;
}}
.meta-table .risk-value {{
    background: {risk_bg};
    color: {risk_color};
    font-weight: bold;
}}

/* ── Risk banner ── */
.risk-banner {{
    background: {risk_bg};
    border: 1.2pt solid {risk_border};
    border-radius: 6pt;
    text-align: center;
    padding: 10pt;
    margin-bottom: 14pt;
}}
.risk-banner .risk-label {{
    font-size: 18pt;
    font-weight: bold;
    color: {risk_color};
}}
.risk-banner .risk-desc {{
    font-size: 9pt;
    color: #444466;
    margin-top: 4pt;
}}

/* ── Section headers ── */
.section-header {{
    font-size: 14pt;
    color: #1a3a5c;
    margin-top: 14pt;
    margin-bottom: 6pt;
    padding-bottom: 3pt;
    border-bottom: 1.5pt solid #c9a84c;
}}

/* ── Body paragraphs ── */
p {{
    font-size: 11pt;
    line-height: 1.7;
    margin-bottom: 5pt;
    color: #1a1a2e;
}}

/* ── Notice box ── */
.notice-box {{
    background: #fff7dc;
    border: 0.8pt solid #c9a84c;
    border-radius: 4pt;
    padding: 9pt;
    margin-top: 14pt;
    font-size: 10pt;
    color: #5a3e00;
    line-height: 1.6;
}}

/* ── Footer ── */
.footer {{
    text-align: center;
    font-size: 8pt;
    color: #888888;
    margin-top: 12pt;
}}

/* ── Dept tags ── */
.dept-tag {{
    display: inline-block;
    background: #eaf0fb;
    color: #1a3a5c;
    border: 0.5pt solid #d0d7e3;
    border-radius: 10pt;
    padding: 2pt 8pt;
    font-size: 9pt;
    margin: 2pt 3pt 2pt 0;
}}
</style>
</head>
<body>

<div class="header-company">Buildway Tech (HK) Limited</div>
<div class="header-title">HK-AICOS 工程分析報告</div>
<div class="header-accent"></div>

<table class="meta-table">
  <tr><td class="label">報告編號</td><td class="value">{_html_escape(report_id)}</td></tr>
  <tr><td class="label">報告日期</td><td class="value">{now.strftime('%Y-%m-%d %H:%M')}</td></tr>
  <tr><td class="label">分析類型</td><td class="value">{_html_escape(_clean_report_text(analysis_type) or '工程分析')}</td></tr>
  <tr><td class="label">參與 Agent</td><td class="value">{_html_escape(agent_labels or '全部')}</td></tr>
  <tr><td class="label">項目編號</td><td class="value">{_html_escape(_clean_report_text(project_ref) or '待確認')}</td></tr>
  <tr><td class="label">參考文件</td><td class="value">{_html_escape(_clean_report_text(filename_hint) or '待確認')}</td></tr>
  <tr><td class="label">可能涉及部門</td><td class="value">{_html_escape(dept_meta)}</td></tr>
  <tr><td class="label">風險級別</td><td class="value risk-value">{_html_escape(clean_risk)}</td></tr>
</table>

<div class="risk-banner">
  <div class="risk-label">{_html_escape(clean_risk)}</div>
  <div class="risk-desc">{_html_escape(risk_desc)}</div>
</div>

{agent_sections_html}

<div class="section-header">可能涉及部門</div>
{dept_html}

{professionals_html}

<div class="notice-box">
本報告供項目管理及工程跟進使用。正式行動、對外回覆及合約立場，須由項目經理及相關合資格專業人士確認。
</div>

<div class="footer">
Buildway Tech (HK) Limited &nbsp;|&nbsp; {now.strftime('%Y-%m-%d %H:%M')} &nbsp;|&nbsp; {_html_escape(report_id)}
</div>

</body>
</html>"""


# ── Font registration (module-level, done once) ───────────────────────────────
# Priority: bundled OTF → bundled VF TTF → Linux system → Windows system
_FONT_CANDIDATES = [
    ("NotoSansCJKTC", _FONTS_DIR / "NotoSansCJKtc-Regular.otf"),
    ("NotoSansCJKTC", _FONTS_DIR / "NotoSansTC-VF.ttf"),
    ("NotoSansCJKTC", _FONTS_DIR / "NotoSansTC-Regular.ttf"),
    ("NotoSansCJKTC", Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")),
    ("NotoSansCJKTC", Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc")),
    ("NotoSansCJKTC", Path("C:/Windows/Fonts/msjh.ttc")),
    ("NotoSansCJKTC", Path("C:/Windows/Fonts/msyh.ttc")),
    ("NotoSansCJKTC", Path("C:/Windows/Fonts/mingliu.ttc")),
]

FONT = "NotoSansCJKTC"
_font_registered = False

for _fname, _fpath in _FONT_CANDIDATES:
    if _fpath.exists():
        try:
            if _fpath.suffix.lower() == ".ttc":
                pdfmetrics.registerFont(TTFont(_fname, str(_fpath), subfontIndex=0))
            else:
                pdfmetrics.registerFont(TTFont(_fname, str(_fpath)))
            FONT = _fname
            _font_registered = True
            break
        except Exception:
            continue

if not _font_registered:
    # Absolute last resort — will not embed but won't crash
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    FONT = "STSong-Light"


def _rl_styles() -> dict:
    """Return reportlab ParagraphStyle dict using the registered CJK font."""
    base = getSampleStyleSheet()

    def ps(name, **kw):
        return ParagraphStyle(name, parent=base["Normal"], fontName=FONT, **kw)

    return {
        "company":    ps("company",    fontSize=13, textColor=colors.white,              alignment=TA_CENTER, leading=18),
        "title":      ps("title",      fontSize=20, textColor=colors.white,              alignment=TA_CENTER, leading=26),
        "meta_label": ps("meta_label", fontSize=10, textColor=colors.HexColor("#1a3a5c"), leading=15),
        "meta_value": ps("meta_value", fontSize=10, textColor=colors.HexColor("#1a1a2e"), leading=15),
        "section":    ps("section",    fontSize=14, textColor=colors.HexColor("#1a3a5c"), leading=20, spaceBefore=7, spaceAfter=4),
        "body":       ps("body",       fontSize=11, textColor=colors.HexColor("#1a1a2e"), leading=19, spaceAfter=5, alignment=TA_LEFT),
        "subtle":     ps("subtle",     fontSize=9,  textColor=colors.HexColor("#444466"), leading=14, alignment=TA_CENTER),
        "notice":     ps("notice",     fontSize=10, textColor=colors.HexColor("#5a3e00"), leading=16),
        "footer":     ps("footer",     fontSize=8,  textColor=colors.HexColor("#888888"), leading=12, alignment=TA_CENTER),
    }


def _rl_escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def _rl_p(text: str, style) -> Paragraph:
    return Paragraph(_rl_escape(text), style)


def _rl_section_header(title: str, story: list, st: dict):
    story.append(Spacer(1, 4 * mm))
    story.append(_rl_p(title, st["section"]))


def _rl_add_lines(story: list, text: str, st: dict, fallback: str = "未有補充資料。"):
    cleaned = _clean_report_text(text)
    if not cleaned:
        cleaned = fallback
    for line in cleaned.splitlines():
        story.append(_rl_p(line, st["body"]))


# ── Main public API ───────────────────────────────────────────────────────────
def generate_pdf_report(
    analysis_type: str,
    question: str,
    risk_level: str,
    analysis_result: str,
    filename_hint: str = "",
    professionals_required: list = None,
    project_ref: str = "",
    selected_agents: list = None,
    session_id: str = "",
) -> bytes:
    st         = _rl_styles()
    now        = datetime.now()
    report_id  = f"RPT-{now.strftime('%Y%m%d-%H%M%S')}"
    clean_risk = _normalise_risk(risk_level)

    combined_text = "\n".join([analysis_type or "", question or "", analysis_result or ""])
    departments   = _department_mapping(combined_text)

    if not selected_agents:
        selected_agents = AGENT_ORDER_PDF

    # ── Save debug HTML (UTF-8) before PDF generation ─────────────────────────
    try:
        from utils.agent_router import AGENT_DEFINITIONS as _AD
        agent_labels = "、".join(_AD[aid]["display"] for aid in selected_agents if aid in _AD)
    except Exception:
        _AD = {}
        agent_labels = "、".join(selected_agents)

    agent_sections = _split_agent_sections(analysis_result, selected_agents)

    agent_sections_html = ""
    for agent_id in selected_agents:
        if agent_id not in _AD:
            continue
        section_title = _AD[agent_id]["report_section"]
        fallback = AGENT_SECTION_FALLBACKS.get(agent_id, "未能取得該 Agent 的完整段落。")
        section_text = agent_sections.get(agent_id, "")
        agent_sections_html += (
            f'<div class="section-header">{_html_escape(section_title)}</div>\n'
            + _lines_to_html(section_text, fallback=fallback) + "\n"
        )

    dept_html = (
        "".join(f'<span class="dept-tag">{_html_escape(d)}</span>' for d in departments)
        + "<p>如不確定，需由相關專業人士確認實際監管部門。</p>"
        if departments else "<p>需由相關專業人士確認實際監管部門。</p>"
    )

    professionals_html = ""
    if professionals_required:
        professionals_html = '<div class="section-header">需確認人士</div>\n'
        for prof in professionals_required:
            professionals_html += f"<p>{_html_escape(_clean_report_text(prof))}</p>\n"

    html_content = _build_html(
        report_id=report_id, now=now,
        analysis_type=analysis_type or "", question=question or "",
        risk_level=risk_level or "", clean_risk=clean_risk,
        agent_labels=agent_labels, project_ref=project_ref or "",
        filename_hint=filename_hint or "", departments=departments,
        agent_sections_html=agent_sections_html, dept_html=dept_html,
        professionals_html=professionals_html,
        font_path=_FONT_FILE.as_posix(),
    )
    (REPORTS_DIR / "debug_report.html").write_text(html_content, encoding="utf-8")

    # ── Build PDF with reportlab (font fully embedded via TTFont) ─────────────
    DARK_BLUE   = colors.HexColor("#1a3a5c")
    MID_BLUE    = colors.HexColor("#2d5a8e")
    GOLD        = colors.HexColor("#c9a84c")
    BORDER_GREY = colors.HexColor("#d0d7e3")
    risk_color  = colors.HexColor(RISK_COLOR[clean_risk])
    risk_bg     = colors.HexColor(RISK_BG[clean_risk])

    # Build PDF metadata — project_ref, session_id, agents embedded as subject/keywords
    _agents_str = "、".join(selected_agents) if selected_agents else ""
    _proj_str   = str(project_ref or "").strip() or "未填寫"
    _sid_str    = str(session_id or "").strip() or report_id

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=18*mm, leftMargin=18*mm,
        topMargin=15*mm, bottomMargin=15*mm,
        title=f"HK-AICOS 工程分析報告 {report_id}",
        author="Buildway Tech (HK) Limited",
        subject=f"項目編號: {_proj_str} | Session: {_sid_str}",
        keywords=f"HK-AICOS, {_proj_str}, {_sid_str}, {_agents_str}",
        creator="HK-AICOS Phase 2.5E",
    )
    width = 174 * mm
    story = []

    # Header
    company_bar = Table([[_rl_p("Buildway Tech (HK) Limited", st["company"])]], colWidths=[width])
    company_bar.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), DARK_BLUE),
        ("TOPPADDING", (0,0), (-1,-1), 9), ("BOTTOMPADDING", (0,0), (-1,-1), 9),
    ]))
    title_bar = Table([[_rl_p("HK-AICOS 工程分析報告", st["title"])]], colWidths=[width])
    title_bar.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), MID_BLUE),
        ("TOPPADDING", (0,0), (-1,-1), 13), ("BOTTOMPADDING", (0,0), (-1,-1), 13),
    ]))
    accent = Table([[""]], colWidths=[width], rowHeights=[4])
    accent.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), GOLD)]))
    story.extend([company_bar, title_bar, accent, Spacer(1, 6*mm)])

    # Metadata
    dept_meta_value = "、".join(departments) if departments else "需由相關專業人士確認實際監管部門"
    meta_rows = [
        ("報告編號",    report_id),
        ("報告日期",    now.strftime("%Y-%m-%d %H:%M")),
        ("分析類型",    _clean_report_text(analysis_type) or "工程分析"),
        ("參與 Agent", agent_labels or "全部"),
        ("項目編號",    _clean_report_text(project_ref) or "待確認"),
        ("參考文件",    _clean_report_text(filename_hint) or "待確認"),
        ("可能涉及部門", dept_meta_value),
        ("風險級別",    clean_risk),
    ]
    meta_table = Table(
        [[_rl_p(lbl, st["meta_label"]), _rl_p(val, st["meta_value"])] for lbl, val in meta_rows],
        colWidths=[34*mm, 140*mm],
    )
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#eaf0fb")),
        ("BACKGROUND", (1,7), (1,7),  risk_bg),
        ("GRID",       (0,0), (-1,-1), 0.5, BORDER_GREY),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 7), ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",(0,0), (-1,-1), 8), ("RIGHTPADDING",  (0,0), (-1,-1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6*mm))

    # Risk banner
    risk_style = ParagraphStyle("risk_val", fontName=FONT, fontSize=18,
                                alignment=TA_CENTER, textColor=risk_color, leading=24)
    risk_table = Table(
        [[_rl_p(clean_risk, risk_style)],
         [_rl_p(RISK_DESC[clean_risk], st["subtle"])]],
        colWidths=[width],
    )
    risk_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), risk_bg),
        ("BOX",        (0,0), (-1,-1), 1.2, risk_color),
        ("TOPPADDING", (0,0), (-1,-1), 9), ("BOTTOMPADDING", (0,0), (-1,-1), 9),
        ("LEFTPADDING",(0,0), (-1,-1), 10),("RIGHTPADDING",  (0,0), (-1,-1), 10),
    ]))
    story.append(risk_table)

    # Agent sections
    try:
        from utils.agent_router import AGENT_DEFINITIONS as _AD2
    except Exception:
        _AD2 = {}

    for agent_id in selected_agents:
        if agent_id not in _AD2:
            continue
        section_title = _AD2[agent_id]["report_section"]
        fallback = AGENT_SECTION_FALLBACKS.get(agent_id, "未能取得該 Agent 的完整段落。")
        _rl_section_header(section_title, story, st)
        _rl_add_lines(story, agent_sections.get(agent_id, ""), st, fallback=fallback)

    # Departments
    _rl_section_header("可能涉及部門", story, st)
    if departments:
        for dept in departments:
            story.append(_rl_p(dept, st["body"]))
        story.append(_rl_p("如不確定，需由相關專業人士確認實際監管部門。", st["body"]))
    else:
        story.append(_rl_p("需由相關專業人士確認實際監管部門。", st["body"]))

    # Professionals
    if professionals_required:
        _rl_section_header("需確認人士", story, st)
        for prof in professionals_required:
            story.append(_rl_p(_clean_report_text(prof), st["body"]))

    # Notice
    story.append(Spacer(1, 6*mm))
    notice_text = (
        "本報告供項目管理及工程跟進使用。正式行動、對外回覆及合約立場，"
        "須由項目經理及相關合資格專業人士確認。"
    )
    notice_table = Table([[_rl_p(notice_text, st["notice"])]], colWidths=[width])
    notice_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#fff7dc")),
        ("BOX",        (0,0), (-1,-1), 0.8, GOLD),
        ("TOPPADDING", (0,0), (-1,-1), 9), ("BOTTOMPADDING", (0,0), (-1,-1), 9),
        ("LEFTPADDING",(0,0), (-1,-1), 9), ("RIGHTPADDING",  (0,0), (-1,-1), 9),
    ]))
    story.append(notice_table)

    story.append(Spacer(1, 5*mm))
    story.append(_rl_p(
        f"Buildway Tech (HK) Limited  {now.strftime('%Y-%m-%d %H:%M')}  {report_id}",
        st["footer"],
    ))

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
