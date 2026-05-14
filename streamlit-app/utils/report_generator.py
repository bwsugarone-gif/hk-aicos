"""
report_generator.py
HK-AICOS Phase 2.0 - PDF Report Generator (Client Version)

Professional PDF report with Traditional Chinese support.
Mobile-friendly, WhatsApp-shareable, no backend/demo text.

Buildway Tech (HK) Limited
"""

import io
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# Font Setup - MSung-Light is a built-in CID font, works on all platforms
pdfmetrics.registerFont(UnicodeCIDFont("MSung-Light"))
FONT = "MSung-Light"

# Colour Palette
DARK_BLUE   = colors.HexColor("#1a3a5c")
MID_BLUE    = colors.HexColor("#2d5a8e")
LIGHT_BLUE  = colors.HexColor("#4a6fa5")
GOLD        = colors.HexColor("#c9a84c")
GOLD_LIGHT  = colors.HexColor("#f5e6c0")
BG_GREY     = colors.HexColor("#f7f9fc")
BORDER_GREY = colors.HexColor("#d0d7e3")
TEXT_DARK   = colors.HexColor("#1a1a2e")
TEXT_MID    = colors.HexColor("#444466")

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
RISK_BORDER = {
    "低風險": colors.HexColor("#28a745"),
    "中風險": colors.HexColor("#e67e00"),
    "高風險": colors.HexColor("#dc3545"),
}
RISK_DESC = {
    "低風險": "一般記錄 / 可跟進",
    "中風險": "可能影響安全、工期、成本或文件責任",
    "高風險": "可能涉及法規、安全、結構、消防、電力、水務、公共道路、工傷、合約或公司責任",
}

DISCLAIMER = (
    "本報告為 AI 輔助工程分析結果，只供初步參考及內部評估用途。\n\n"
    "所有涉及結構、安全、法規、消防、電力、水務、公共道路、掘路、"
    "高風險工序、合約或法律責任之事項，必須由香港合資格專業人士最終確認。\n\n"
    "Buildway Tech (HK) Limited 不會取代認可人士、註冊工程師、安全主任、"
    "註冊電業工程人員、持牌水喉匠、法律專業人士或相關政府部門之正式審批。"
)

REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


# ── Style Builder ─────────────────────────────────────────────────────────────
def _styles() -> dict:
    base = getSampleStyleSheet()

    def ps(name, **kw):
        return ParagraphStyle(name, parent=base["Normal"], fontName=FONT, **kw)

    return {
        # Cover header
        "co_company": ps("co_company",
            fontSize=13, textColor=colors.white,
            alignment=TA_CENTER, leading=18, spaceAfter=2),
        "co_title": ps("co_title",
            fontSize=20, textColor=colors.white,
            alignment=TA_CENTER, leading=26, spaceAfter=4),
        "co_sub": ps("co_sub",
            fontSize=10, textColor=colors.HexColor("#c9d8f0"),
            alignment=TA_CENTER, leading=14),

        # Metadata
        "meta_label": ps("meta_label",
            fontSize=10, textColor=DARK_BLUE, leading=15),
        "meta_value": ps("meta_value",
            fontSize=10, textColor=TEXT_DARK, leading=15),

        # Section headings
        "section": ps("section",
            fontSize=13, textColor=DARK_BLUE,
            spaceBefore=12, spaceAfter=4, leading=18),

        # Body text - larger for mobile readability
        "body": ps("body",
            fontSize=11, leading=19, spaceAfter=5,
            textColor=TEXT_DARK),

        # Bullet points
        "bullet": ps("bullet",
            fontSize=11, leading=19, leftIndent=16,
            spaceAfter=4, textColor=TEXT_DARK),

        # Risk banner text
        "risk_level": ps("risk_level",
            fontSize=18, alignment=TA_CENTER,
            leading=24, spaceAfter=2),
        "risk_desc": ps("risk_desc",
            fontSize=10, alignment=TA_CENTER,
            textColor=TEXT_MID, leading=15),

        # Warning box
        "warn": ps("warn",
            fontSize=11, leading=17,
            textColor=colors.HexColor("#7a4400"),
            leftIndent=8),

        # Disclaimer
        "disclaimer": ps("disclaimer",
            fontSize=9, leading=15,
            textColor=colors.HexColor("#6b1520")),

        # Footer
        "footer": ps("footer",
            fontSize=8, textColor=colors.HexColor("#888888"),
            alignment=TA_CENTER, leading=12),

        # Professional confirm
        "prof": ps("prof",
            fontSize=11, leading=17,
            textColor=colors.HexColor("#5a3e00"),
            leftIndent=8),
    }


# ── Safe Paragraph ────────────────────────────────────────────────────────────
def _p(text: str, style) -> Paragraph:
    text = str(text)
    text = (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br/>"))
    try:
        return Paragraph(text, style)
    except Exception:
        safe = text.encode("ascii", "replace").decode()
        return Paragraph(safe, style)


# ── Section Header ────────────────────────────────────────────────────────────
def _section_header(title: str, W: float, st: dict) -> list:
    """Returns a list of flowables for a styled section header."""
    return [
        Spacer(1, 4 * mm),
        _p(title, st["section"]),
        HRFlowable(width=W, thickness=1.5, color=GOLD, spaceAfter=3),
        Spacer(1, 2 * mm),
    ]


# ── Parse Analysis Text ───────────────────────────────────────────────────────
def _parse_analysis(text: str, st: dict) -> list:
    """
    Parse analysis text into styled flowables.
    Handles markdown-style headings and bullet points.
    Strips any banned technical phrases.
    """
    BANNED = [
        "demo mode", "[demo", "api key", "no api key", "api_key",
        "claude", "anthropic", "token", "model name", "backend",
        "debug", "prompt", "developer", "system prompt",
        "this is what would be sent", "the ai would analyze",
        "input data summary", "engineering analysis",
        "safety analysis", "regulatory compliance analysis",
        "no api", "openai", "gemini", "llm", "language model",
    ]

    items = []
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            items.append(Spacer(1, 2 * mm))
            continue

        # Check for banned content
        line_lower = line.lower()
        if any(b in line_lower for b in BANNED):
            continue

        # Section headings (## or ###)
        if line.startswith("###") or line.startswith("##"):
            heading = line.lstrip("#").strip()
            items.append(Spacer(1, 3 * mm))
            items.append(_p(heading, st["section"]))
            items.append(HRFlowable(width="100%", thickness=1, color=GOLD, spaceAfter=2))
        # Bullet points
        elif line.startswith("-") or line.startswith("•") or line.startswith("*"):
            content = line.lstrip("-•* ").strip()
            items.append(_p("•  " + content, st["bullet"]))
        # Warning lines
        elif line.startswith("!") or "注意" in line or "警告" in line:
            items.append(_p(line.lstrip("! "), st["warn"]))
        # Normal body
        else:
            items.append(_p(line, st["body"]))

    return items


# ── Main Generator ─────────────────────────────────────────────────────────────
def generate_pdf_report(
    analysis_type: str,
    question: str,
    risk_level: str,
    analysis_result: str,
    filename_hint: str = "",
    professionals_required: list = None,
    project_ref: str = "",
) -> bytes:
    """
    Generate a professional mobile-friendly PDF report.
    Returns PDF as bytes. No backend/API/demo text exposed.
    """
    st = _styles()

    # Normalise risk level
    if risk_level not in ("低風險", "中風險", "高風險"):
        risk_level = "高風險"

    r_color  = RISK_COLOR[risk_level]
    r_bg     = RISK_BG[risk_level]
    r_border = RISK_BORDER[risk_level]
    r_desc   = RISK_DESC[risk_level]

    buffer = io.BytesIO()
    now = datetime.now()
    report_id = f"RPT-{now.strftime('%Y%m%d-%H%M%S')}"

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"HK-AICOS 工程分析報告 {report_id}",
        author="Buildway Tech (HK) Limited",
    )

    story = []
    W = 170 * mm  # usable width

    # ── COVER HEADER ──────────────────────────────────────────────────────────
    # Company name bar (dark blue)
    company_bar = Table(
        [[_p("Buildway Tech (HK) Limited", st["co_company"])]],
        colWidths=[W],
    )
    company_bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK_BLUE),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
    ]))

    # Title bar (mid blue)
    title_bar = Table(
        [[_p("HK-AICOS  工程分析報告", st["co_title"])]],
        colWidths=[W],
    )
    title_bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), MID_BLUE),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
    ]))

    # Gold accent bar
    gold_bar = Table([[""]], colWidths=[W], rowHeights=[4])
    gold_bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GOLD),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    story.append(company_bar)
    story.append(title_bar)
    story.append(gold_bar)
    story.append(Spacer(1, 6 * mm))

    # ── METADATA TABLE ────────────────────────────────────────────────────────
    # Two-column layout: label | value
    meta_data = [
        ("報告編號", report_id),
        ("日期", now.strftime("%Y-%m-%d  %H:%M")),
        ("分析類型", analysis_type),
        ("工程編號", project_ref or "—"),
        ("上載文件", filename_hint or "—"),
        ("風險級別", f"[{risk_level}]"),
    ]

    meta_rows = []
    for label, value in meta_data:
        if label == "風險級別":
            val_para = _p(
                f"[{risk_level}]",
                ParagraphStyle("rl", fontName=FONT, fontSize=11,
                               textColor=r_color, leading=16),
            )
        else:
            val_para = _p(value, st["meta_value"])
        meta_rows.append([_p(label, st["meta_label"]), val_para])

    meta_table = Table(meta_rows, colWidths=[35 * mm, 135 * mm])
    meta_table.setStyle(TableStyle([
        ("FONTNAME",       (0, 0), (-1, -1), FONT),
        ("BACKGROUND",     (0, 0), (0, -1), colors.HexColor("#eaf0fb")),
        ("TEXTCOLOR",      (0, 0), (0, -1), DARK_BLUE),
        ("GRID",           (0, 0), (-1, -1), 0.5, BORDER_GREY),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",     (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 7),
        ("LEFTPADDING",    (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 8),
        # Highlight risk row background
        ("BACKGROUND",     (1, 5), (1, 5), r_bg),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6 * mm))

    # ── RISK BANNER ───────────────────────────────────────────────────────────
    risk_banner = Table(
        [[
            _p(
                f"[{risk_level}]",
                ParagraphStyle("rb", fontName=FONT, fontSize=20,
                               alignment=TA_CENTER, textColor=r_color,
                               leading=26, spaceAfter=3),
            )
        ],
        [_p(r_desc, st["risk_desc"])]],
        colWidths=[W],
    )
    risk_banner.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), r_bg),
        ("BOX",           (0, 0), (-1, -1), 2.5, r_border),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(KeepTogether([risk_banner]))
    story.append(Spacer(1, 6 * mm))

    # ── 1. 問題摘要 ───────────────────────────────────────────────────────────
    story.extend(_section_header("1.  問題摘要", W, st))
    story.append(_p(question, st["body"]))
    story.append(Spacer(1, 4 * mm))

    # ── 2. 工程分析 ───────────────────────────────────────────────────────────
    story.extend(_section_header("2.  工程分析", W, st))
    story.extend(_parse_analysis(analysis_result, st))
    story.append(Spacer(1, 4 * mm))

    # ── 3-7: Extract structured sections from analysis_result if present ──────
    # These sections are rendered if the AI output contains them as headings.
    # The _parse_analysis function already handles ## headings inline,
    # so we add explicit section separators for the standard chapters
    # only if they are NOT already present in the analysis text.

    analysis_lower = analysis_result.lower()

    def _has_section(keywords):
        return any(k in analysis_lower for k in keywords)

    if not _has_section(["安全風險", "安全分析"]):
        story.extend(_section_header("3.  安全風險分析", W, st))
        story.append(_p("• 請參閱上方工程分析內容。", st["bullet"]))
        story.append(Spacer(1, 3 * mm))

    if not _has_section(["法規", "合規"]):
        story.extend(_section_header("4.  法規與合規提醒", W, st))
        story.append(_p("• 如涉及法規事項，請諮詢相關合資格專業人士。", st["bullet"]))
        story.append(Spacer(1, 3 * mm))

    if not _has_section(["成本", "工期"]):
        story.extend(_section_header("5.  成本及工期影響", W, st))
        story.append(_p("• 如有成本或工期影響，請由項目經理評估。", st["bullet"]))
        story.append(Spacer(1, 3 * mm))

    if not _has_section(["建議", "跟進"]):
        story.extend(_section_header("6.  建議跟進事項", W, st))
        story.append(_p("• 請根據上方分析結果安排跟進。", st["bullet"]))
        story.append(Spacer(1, 3 * mm))

    # ── 需要人工確認事項 ──────────────────────────────────────────────────────
    if professionals_required:
        story.extend(_section_header("7.  需要人工確認事項", W, st))
        for prof in professionals_required:
            story.append(_p(f"•  {prof}", st["bullet"]))
        story.append(Spacer(1, 3 * mm))

    # ── 專業人士確認提醒 ──────────────────────────────────────────────────────
    story.extend(_section_header("8.  專業人士確認提醒", W, st))
    confirm_items = [
        "所有結構及承重改動 — 認可人士 (AP) / 結構工程師 (RSE)",
        "消防系統及逃生設施 — 消防安全顧問 / 消防處",
        "電力裝置及高壓工程 — 註冊電業工程人員",
        "水務及排水工程 — 持牌水喉匠 / 水務署",
        "公共道路及掘路工程 — 路政署 / 相關政府部門",
        "工地安全及高風險工序 — 註冊安全主任 (RSO)",
        "合約及法律責任事項 — 法律專業人士",
    ]
    for item in confirm_items:
        story.append(_p(f"•  {item}", st["bullet"]))
    story.append(Spacer(1, 6 * mm))

    # ── 免責聲明 ──────────────────────────────────────────────────────────────
    story.append(HRFlowable(width=W, thickness=2, color=colors.HexColor("#c0152a"),
                            spaceAfter=3))
    disclaimer_table = Table(
        [[_p(DISCLAIMER, st["disclaimer"])]],
        colWidths=[W],
    )
    disclaimer_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#fde8eb")),
        ("BOX",           (0, 0), (-1, -1), 1, colors.HexColor("#c0152a")),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    story.append(disclaimer_table)

    # ── FOOTER ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 5 * mm))
    story.append(HRFlowable(width=W, thickness=0.5, color=BORDER_GREY))
    story.append(Spacer(1, 2 * mm))
    story.append(_p(
        f"HK-AICOS 工程分析報告  |  Buildway Tech (HK) Limited  |  {now.strftime('%Y-%m-%d %H:%M')}  |  {report_id}",
        st["footer"],
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def save_report(pdf_bytes: bytes, report_id: str = "") -> Path:
    """Save PDF bytes to the reports directory and return the path."""
    if not report_id:
        report_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"HK-AICOS-Report-{report_id}.pdf"
    path = REPORTS_DIR / filename
    path.write_bytes(pdf_bytes)
    return path
