"""
report_generator.py
HK-AICOS Phase 2.0 - PDF Report Generator

Generates mobile-friendly PDF reports using reportlab.
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
    HRFlowable, PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# Risk level colors
RISK_COLORS = {
    "低風險":  colors.HexColor("#28a745"),
    "中風險":  colors.HexColor("#ffc107"),
    "高風險":  colors.HexColor("#fd7e14"),
    "極高風險": colors.HexColor("#dc3545"),
}

RISK_BG_COLORS = {
    "低風險":  colors.HexColor("#d4edda"),
    "中風險":  colors.HexColor("#fff3cd"),
    "高風險":  colors.HexColor("#fde8d8"),
    "極高風險": colors.HexColor("#f8d7da"),
}

DISCLAIMER_TEXT = """
⚠ 本分析只作 AI 輔助參考用途。

如涉及香港法例、政府部門要求、結構安全、消防安全、電力工程、水務工程、
公共道路、掘路工程、高風險工序或法律責任，必須由香港合資格專業人士、
安全主任、認可人士 (AP)、註冊工程師 (RSE/RGE)、
註冊電業工程人員 (REW) 或相關專業人士確認。

AI-assisted analysis only. Final decision shall be confirmed by qualified professionals.
"""


def _build_styles():
    """Build custom paragraph styles."""
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "HKTitle",
        parent=styles["Title"],
        fontSize=20,
        textColor=colors.HexColor("#1a3a5c"),
        spaceAfter=6,
        alignment=TA_CENTER,
    )
    subtitle_style = ParagraphStyle(
        "HKSubtitle",
        parent=styles["Normal"],
        fontSize=12,
        textColor=colors.HexColor("#4a6fa5"),
        spaceAfter=4,
        alignment=TA_CENTER,
    )
    section_header_style = ParagraphStyle(
        "HKSection",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor("#1a3a5c"),
        spaceBefore=12,
        spaceAfter=4,
        borderPad=4,
    )
    body_style = ParagraphStyle(
        "HKBody",
        parent=styles["Normal"],
        fontSize=11,
        leading=16,
        spaceAfter=6,
        alignment=TA_JUSTIFY,
    )
    bullet_style = ParagraphStyle(
        "HKBullet",
        parent=styles["Normal"],
        fontSize=11,
        leading=16,
        leftIndent=16,
        spaceAfter=3,
    )
    disclaimer_style = ParagraphStyle(
        "HKDisclaimer",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#721c24"),
        leading=14,
        spaceAfter=4,
    )
    footer_style = ParagraphStyle(
        "HKFooter",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER,
    )

    return {
        "title": title_style,
        "subtitle": subtitle_style,
        "section": section_header_style,
        "body": body_style,
        "bullet": bullet_style,
        "disclaimer": disclaimer_style,
        "footer": footer_style,
    }


def _safe_para(text: str, style) -> Paragraph:
    """Create a Paragraph, escaping any problematic characters."""
    # Basic XML escaping for reportlab
    text = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Restore intentional line breaks
    text = text.replace("\n", "<br/>")
    try:
        return Paragraph(text, style)
    except Exception:
        return Paragraph(str(text).encode("ascii", "replace").decode(), style)


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
    Generate a PDF report and return as bytes.

    Args:
        analysis_type: The type of analysis performed
        question: The user's question
        risk_level: Risk level string (低風險/中風險/高風險/極高風險)
        analysis_result: The full AI analysis text
        filename_hint: Original uploaded filename
        professionals_required: List of professionals needed for confirmation
        project_ref: Optional project reference number

    Returns:
        PDF content as bytes
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = _build_styles()
    story = []
    now = datetime.now()
    report_id = f"RPT-{now.strftime('%Y%m%d-%H%M%S')}"

    # ── Cover / Header ──────────────────────────────────────────────
    story.append(Spacer(1, 8 * mm))
    story.append(_safe_para("Buildway Tech (HK) Limited", styles["title"]))
    story.append(_safe_para("HK-AICOS  |  AI Construction Analysis Report", styles["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a3a5c")))
    story.append(Spacer(1, 4 * mm))

    # Report metadata table
    meta_data = [
        ["Report ID", report_id, "Date", now.strftime("%Y-%m-%d %H:%M")],
        ["Analysis Type", analysis_type, "Project Ref", project_ref or "—"],
        ["File", filename_hint or "—", "Risk Level", risk_level],
    ]
    risk_color = RISK_COLORS.get(risk_level, colors.grey)
    risk_bg = RISK_BG_COLORS.get(risk_level, colors.white)

    meta_table = Table(meta_data, colWidths=[35 * mm, 65 * mm, 30 * mm, 45 * mm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f0fe")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#e8f0fe")),
        ("BACKGROUND", (3, 2), (3, 2), risk_bg),
        ("TEXTCOLOR", (3, 2), (3, 2), risk_color),
        ("FONTNAME", (3, 2), (3, 2), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6 * mm))

    # ── Question ────────────────────────────────────────────────────
    story.append(_safe_para("Question / Input", styles["section"]))
    story.append(_safe_para(question, styles["body"]))
    story.append(Spacer(1, 4 * mm))

    # ── Risk Level Banner ───────────────────────────────────────────
    risk_emojis = {"低風險": "🟢", "中風險": "🟡", "高風險": "🔴", "極高風險": "⚫"}
    risk_emoji = risk_emojis.get(risk_level, "")
    risk_banner_data = [[f"Risk Level  /  風險等級:  {risk_level}  {risk_emoji}"]]
    risk_banner = Table(risk_banner_data, colWidths=[175 * mm])
    risk_banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), risk_bg),
        ("TEXTCOLOR", (0, 0), (-1, -1), risk_color),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 13),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 1.5, risk_color),
    ]))
    story.append(risk_banner)
    story.append(Spacer(1, 6 * mm))

    # ── Analysis Result ─────────────────────────────────────────────
    story.append(_safe_para("Analysis Report  /  分析報告", styles["section"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#aaaaaa")))
    story.append(Spacer(1, 3 * mm))

    # Split analysis result into lines for better formatting
    for line in analysis_result.split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 2 * mm))
        elif line.startswith("###"):
            story.append(_safe_para(line.lstrip("#").strip(), styles["section"]))
        elif line.startswith("##"):
            story.append(_safe_para(line.lstrip("#").strip(), styles["section"]))
        elif line.startswith("-") or line.startswith("•"):
            story.append(_safe_para("• " + line.lstrip("-•").strip(), styles["bullet"]))
        elif line.startswith("⚠") or line.startswith("WARNING"):
            warn_style = ParagraphStyle(
                "warn", parent=styles["body"],
                textColor=colors.HexColor("#856404"),
                backColor=colors.HexColor("#fff3cd"),
            )
            story.append(_safe_para(line, warn_style))
        else:
            story.append(_safe_para(line, styles["body"]))

    story.append(Spacer(1, 6 * mm))

    # ── Professionals Required ──────────────────────────────────────
    if professionals_required:
        story.append(_safe_para("Professional Confirmation Required  /  需要專業人士確認", styles["section"]))
        for prof in professionals_required:
            story.append(_safe_para(f"• {prof}", styles["bullet"]))
        story.append(Spacer(1, 4 * mm))

    # ── Disclaimer ──────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#dc3545")))
    story.append(Spacer(1, 3 * mm))
    disclaimer_box_data = [[DISCLAIMER_TEXT.strip()]]
    disclaimer_table = Table(disclaimer_box_data, colWidths=[175 * mm])
    disclaimer_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8d7da")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#721c24")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#dc3545")),
    ]))
    story.append(disclaimer_table)

    # ── Final Page Footer ───────────────────────────────────────────
    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(_safe_para(
        f"Generated by HK-AICOS Phase 2.0  |  Buildway Tech (HK) Limited  |  {now.strftime('%Y-%m-%d %H:%M')}",
        styles["footer"],
    ))
    story.append(_safe_para(
        "AI-assisted analysis only. Final decision shall be confirmed by qualified professionals.",
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
