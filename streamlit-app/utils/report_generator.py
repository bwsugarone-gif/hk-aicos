"""
report_generator.py
HK-AICOS Phase 2.0 - PDF Report Generator (Client Version)

Professional PDF report with Traditional Chinese support using MSung-Light.
No demo/API/backend text exposed to clients.

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
    HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# ── Font Setup ────────────────────────────────────────────────────────────────
# Register MSung-Light (built-in CID font for Traditional Chinese)
pdfmetrics.registerFont(UnicodeCIDFont("MSung-Light"))
CHINESE_FONT = "MSung-Light"

# ── Colors ────────────────────────────────────────────────────────────────────
DARK_BLUE = colors.HexColor("#1a3a5c")
MID_BLUE = colors.HexColor("#2d5a8e")
GOLD = colors.HexColor("#c9a84c")
LIGHT_BLUE_BG = colors.HexColor("#e8f0fe")
LIGHT_GREY = colors.HexColor("#f4f6f9")
BORDER_GREY = colors.HexColor("#cccccc")

RISK_COLORS = {
    "低風險": colors.HexColor("#28a745"),
    "中風險": colors.HexColor("#e67e00"),
    "高風險": colors.HexColor("#dc3545"),
}
RISK_BG_COLORS = {
    "低風險": colors.HexColor("#d4edda"),
    "中風險": colors.HexColor("#fff3cd"),
    "高風險": colors.HexColor("#f8d7da"),
}

DISCLAIMER_ZH = (
    "本報告為 AI 輔助工程分析結果，只供初步參考及內部評估用途。\n\n"
    "所有涉及結構、安全、法規、消防、電力、水務、公共道路、掘路、"
    "高風險工序、合約或法律責任之事項，必須由香港合資格專業人士最終確認。\n\n"
    "Buildway Tech (HK) Limited 不會取代認可人士、註冊工程師、安全主任、"
    "註冊電業工程人員、持牌水喉匠、法律專業人士或相關政府部門之正式審批。"
)

REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


# ── Style Builder ─────────────────────────────────────────────────────────────
def _build_styles(font: str) -> dict:
    base = getSampleStyleSheet()

    def ps(name, parent_name="Normal", **kwargs):
        return ParagraphStyle(name, parent=base[parent_name], fontName=font, **kwargs)

    return {
        "company": ps("Company", fontSize=11, textColor=colors.white,
                      alignment=TA_CENTER, spaceAfter=2),
        "title": ps("Title", fontSize=18, textColor=colors.white,
                    alignment=TA_CENTER, spaceAfter=4, leading=24),
        "subtitle": ps("Subtitle", fontSize=11, textColor=colors.HexColor("#c9d8f0"),
                       alignment=TA_CENTER, spaceAfter=2),
        "section": ps("Section", "Heading2", fontSize=12, textColor=DARK_BLUE,
                      spaceBefore=10, spaceAfter=4, leading=16),
        "body": ps("Body", fontSize=10, leading=16, spaceAfter=4,
                   alignment=TA_JUSTIFY),
        "bullet": ps("Bullet", fontSize=10, leading=16, leftIndent=14, spaceAfter=3),
        "meta_label": ps("MetaLabel", fontSize=9, textColor=DARK_BLUE),
        "meta_value": ps("MetaValue", fontSize=9, textColor=colors.HexColor("#333333")),
        "risk_text": ps("RiskText", fontSize=14, alignment=TA_CENTER,
                        spaceAfter=2, leading=18),
        "risk_sub": ps("RiskSub", fontSize=9, alignment=TA_CENTER,
                       textColor=colors.HexColor("#555555")),
        "disclaimer": ps("Disclaimer", fontSize=8, textColor=colors.HexColor("#721c24"),
                         leading=13, spaceAfter=3),
        "footer": ps("Footer", fontSize=7, textColor=colors.grey,
                     alignment=TA_CENTER),
        "warn": ps("Warn", fontSize=10, leading=15,
                   textColor=colors.HexColor("#856404"),
                   backColor=colors.HexColor("#fff3cd")),
    }


# ── Safe Paragraph ────────────────────────────────────────────────────────────
def _p(text: str, style) -> Paragraph:
    """Escape XML special chars and convert newlines for ReportLab."""
    text = str(text)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = text.replace("\n", "<br/>")
    try:
        return Paragraph(text, style)
    except Exception:
        safe = text.encode("ascii", "replace").decode()
        return Paragraph(safe, style)


# ── Main Generator ────────────────────────────────────────────────────────────
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
    Generate a professional PDF report and return as bytes.
    All content is in Traditional Chinese. No backend/API text exposed.
    """
    font = CHINESE_FONT
    styles = _build_styles(font)

    # Normalise risk level to 3-tier
    if risk_level not in ("低風險", "中風險", "高風險"):
        risk_level = "高風險"

    risk_color = RISK_COLORS.get(risk_level, colors.HexColor("#e67e00"))
    risk_bg = RISK_BG_COLORS.get(risk_level, colors.HexColor("#fff3cd"))

    buffer = io.BytesIO()
    now = datetime.now()
    report_id = f"RPT-{now.strftime('%Y%m%d-%H%M%S')}"

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

    story = []
    W = 174 * mm  # usable width

    # ── Cover Header ──────────────────────────────────────────────────────────
    header_table = Table([[
        _p("Buildway Tech (HK) Limited", styles["company"]),
    ]], colWidths=[W])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK_BLUE),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))

    title_table = Table([[
        _p("HK-AICOS  工程分析報告", styles["title"]),
    ]], colWidths=[W])
    title_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), MID_BLUE),
        ("PADDING", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))

    gold_bar = Table([[""]], colWidths=[W], rowHeights=[3])
    gold_bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GOLD),
        ("PADDING", (0, 0), (-1, -1), 0),
    ]))

    story.append(header_table)
    story.append(title_table)
    story.append(gold_bar)
    story.append(Spacer(1, 5 * mm))

    # ── Metadata Table ────────────────────────────────────────────────────────
    meta_rows = [
        ["報告編號", report_id, "日期", now.strftime("%Y-%m-%d  %H:%M")],
        ["分析類型", analysis_type, "工程編號", project_ref or "—"],
        ["上載文件", filename_hint or "—", "風險級別", risk_level],
    ]

    col_w = [22 * mm, 65 * mm, 22 * mm, 65 * mm]
    meta_table = Table(meta_rows, colWidths=col_w)
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_BLUE_BG),
        ("BACKGROUND", (2, 0), (2, -1), LIGHT_BLUE_BG),
        ("TEXTCOLOR", (0, 0), (0, -1), DARK_BLUE),
        ("TEXTCOLOR", (2, 0), (2, -1), DARK_BLUE),
        ("FONTNAME", (0, 0), (0, -1), font),
        ("FONTNAME", (2, 0), (2, -1), font),
        ("BACKGROUND", (3, 2), (3, 2), risk_bg),
        ("TEXTCOLOR", (3, 2), (3, 2), risk_color),
        ("FONTNAME", (3, 2), (3, 2), font),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_GREY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 5 * mm))

    # ── Question ──────────────────────────────────────────────────────────────
    story.append(_p("問題摘要", styles["section"]))
    story.append(HRFlowable(width=W, thickness=1, color=GOLD))
    story.append(Spacer(1, 2 * mm))
    story.append(_p(question, styles["body"]))
    story.append(Spacer(1, 4 * mm))

    # ── Risk Banner ───────────────────────────────────────────────────────────
    risk_banner = Table(
        [[_p(risk_level, ParagraphStyle(
            "RB", fontName=font, fontSize=16, alignment=TA_CENTER,
            textColor=risk_color, leading=20,
        ))]],
        colWidths=[W],
    )
    risk_banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), risk_bg),
        ("BOX", (0, 0), (-1, -1), 2, risk_color),
        ("PADDING", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(risk_banner)
    story.append(Spacer(1, 5 * mm))

    # ── Analysis Result ───────────────────────────────────────────────────────
    story.append(_p("工程分析報告", styles["section"]))
    story.append(HRFlowable(width=W, thickness=1, color=GOLD))
    story.append(Spacer(1, 3 * mm))

    for line in analysis_result.split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 2 * mm))
        elif line.startswith("###") or line.startswith("##"):
            story.append(_p(line.lstrip("#").strip(), styles["section"]))
        elif line.startswith("-") or line.startswith("•"):
            story.append(_p("• " + line.lstrip("-•").strip(), styles["bullet"]))
        elif line.startswith("⚠") or line.upper().startswith("WARNING"):
            story.append(_p(line, styles["warn"]))
        else:
            story.append(_p(line, styles["body"]))

    story.append(Spacer(1, 5 * mm))

    # ── Professionals Required ────────────────────────────────────────────────
    if professionals_required:
        story.append(_p("需要專業人士確認", styles["section"]))
        story.append(HRFlowable(width=W, thickness=1, color=GOLD))
        story.append(Spacer(1, 2 * mm))
        for prof in professionals_required:
            story.append(_p(f"• {prof}", styles["bullet"]))
        story.append(Spacer(1, 4 * mm))

    # ── Disclaimer ────────────────────────────────────────────────────────────
    story.append(HRFlowable(width=W, thickness=1.5, color=colors.HexColor("#dc3545")))
    story.append(Spacer(1, 2 * mm))

    disclaimer_table = Table(
        [[_p(DISCLAIMER_ZH, styles["disclaimer"])]],
        colWidths=[W],
    )
    disclaimer_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8d7da")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#dc3545")),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(disclaimer_table)

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 5 * mm))
    story.append(HRFlowable(width=W, thickness=0.5, color=BORDER_GREY))
    story.append(_p(
        f"Generated by HK-AICOS  |  Buildway Tech (HK) Limited  |  {now.strftime('%Y-%m-%d %H:%M')}",
        styles["footer"],
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
