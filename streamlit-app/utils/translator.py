# -*- coding: utf-8 -*-
"""
utils/translator.py
HK-AICOS Phase 2.5G — Document Translation & Conversion Engine

Supports:
  - Text translation via AI (EN→TC, TC→EN)
  - DOCX text extraction + translation
  - XLSX text extraction + translation
  - PDF text extraction + translation
  - Excel → PDF conversion
  - DOCX → PDF conversion
  - Image → PowerPoint (BETA — entry point only)

All outputs use embedded NotoSansTC font for cross-platform Chinese rendering.
Never overwrites source files — always returns bytes for download.
"""

import io
import sys
import traceback
from pathlib import Path
from typing import Optional

# ── Font path (same as report_generator) ─────────────────────────────────────
_BASE_DIR  = Path(__file__).parent.parent
_FONT_PATH = _BASE_DIR / "assets" / "fonts" / "NotoSansTC-Regular.ttf"

# ── ReportLab ─────────────────────────────────────────────────────────────────
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
        Image as RLImage,
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    _REPORTLAB_OK = True
except ImportError:
    _REPORTLAB_OK = False

# ── Register font once ────────────────────────────────────────────────────────
_FONT_REGISTERED = False

def _ensure_font() -> str:
    """Register NotoSansTC and return font name. Falls back to Helvetica with warning."""
    global _FONT_REGISTERED
    if not _REPORTLAB_OK:
        return "Helvetica"
    if _FONT_REGISTERED:
        return "NotoSansTC"
    if _FONT_PATH.exists():
        try:
            pdfmetrics.registerFont(TTFont("NotoSansTC", str(_FONT_PATH)))
            _FONT_REGISTERED = True
            return "NotoSansTC"
        except Exception as e:
            print(f"[translator] WARNING: font registration failed: {e}", file=sys.stderr)
    else:
        print(f"[translator] WARNING: font not found at {_FONT_PATH}", file=sys.stderr)
    return "Helvetica"


# ── AI translation helper ─────────────────────────────────────────────────────

# Chunk / document limits
CHUNK_SIZE      = 6000    # characters per chunk sent to AI
MAX_TOTAL_CHARS = 100_000  # hard cap — warn user above this


def _build_instruction(text: str, direction: str) -> str:
    if direction == "en_to_tc":
        return (
            "你是一位專業的工程文件翻譯員，專門處理香港建築及工程行業文件。\n"
            "請將以下英文文字翻譯成繁體中文。\n"
            "規則：\n"
            "1. 保持原文件結構及段落\n"
            "2. 工程術語使用香港慣用繁體中文\n"
            "3. 不改變原意\n"
            "4. 不加入額外解釋\n"
            "5. 只輸出翻譯結果，不輸出任何說明\n\n"
            f"原文：\n{text}"
        )
    elif direction == "tc_to_en":
        return (
            "You are a professional engineering document translator specialising in "
            "Hong Kong construction and engineering documents.\n"
            "Translate the following Traditional Chinese text into English.\n"
            "Rules:\n"
            "1. Preserve original document structure and paragraphs\n"
            "2. Use standard Hong Kong engineering terminology in English\n"
            "3. Do not alter the original meaning\n"
            "4. Do not add extra explanations\n"
            "5. Output only the translation, no commentary\n\n"
            f"Source text:\n{text}"
        )
    else:
        raise ValueError(f"Unknown translation direction: {direction}")


def _call_ai(instruction: str, ai_client, ai_provider: str, model: str) -> str:
    """Single AI call — raises RuntimeError on failure."""
    if ai_provider == "anthropic":
        _model = model or "claude-3-5-haiku-20241022"
        response = ai_client.messages.create(
            model=_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": instruction}],
        )
        return response.content[0].text.strip()

    elif ai_provider in ("openai", "deepseek"):
        # Both use OpenAI-compatible chat completions
        _model = model or ("deepseek-chat" if ai_provider == "deepseek" else "gpt-4o-mini")
        response = ai_client.chat.completions.create(
            model=_model,
            messages=[{"role": "user", "content": instruction}],
            max_tokens=4096,
        )
        return response.choices[0].message.content.strip()

    else:
        raise RuntimeError(f"Unsupported AI provider: {ai_provider}")


def translate_text_via_ai(
    text: str,
    direction: str,          # "en_to_tc" | "tc_to_en"
    ai_client=None,
    ai_provider: str = "anthropic",
    model: str = "",
) -> str:
    """
    Translate text using the configured AI provider.
    Returns translated text, or raises RuntimeError if AI is unavailable.
    Single-call version — use translate_chunks_via_ai for large documents.
    """
    if not text or not text.strip():
        return ""
    if ai_client is None:
        raise RuntimeError("AI client not provided. Please configure API key.")
    try:
        instruction = _build_instruction(text, direction)
        return _call_ai(instruction, ai_client, ai_provider, model)
    except Exception as e:
        raise RuntimeError(f"Translation failed: {e}") from e


def split_into_chunks(text: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    """
    Split text into chunks of at most chunk_size characters.
    Tries to split on paragraph boundaries (double newline) to preserve structure.
    """
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    remaining = text

    while len(remaining) > chunk_size:
        # Try to find a paragraph break near the chunk boundary
        split_at = remaining.rfind("\n\n", 0, chunk_size)
        if split_at == -1:
            # Fall back to single newline
            split_at = remaining.rfind("\n", 0, chunk_size)
        if split_at == -1 or split_at < chunk_size // 2:
            # No good break point — hard split
            split_at = chunk_size

        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()

    if remaining:
        chunks.append(remaining)

    return chunks


def translate_chunks_via_ai(
    text: str,
    direction: str,
    ai_client=None,
    ai_provider: str = "anthropic",
    model: str = "",
    progress_callback=None,   # callable(current: int, total: int, message: str)
) -> dict:
    """
    Translate a large document by splitting into chunks and translating each.

    Returns a dict:
    {
        "translated":        str,   # full merged translation
        "total_chunks":      int,
        "success_chunks":    int,
        "failed_chunks":     int,
        "failed_details":    list[dict],  # [{chunk: int, error: str}]
        "is_complete":       bool,
        "truncated":         bool,   # True if text was capped at MAX_TOTAL_CHARS
    }
    """
    if ai_client is None:
        raise RuntimeError("AI client not provided. Please configure API key.")

    truncated = False
    if len(text) > MAX_TOTAL_CHARS:
        text = text[:MAX_TOTAL_CHARS]
        truncated = True

    chunks = split_into_chunks(text, CHUNK_SIZE)
    total  = len(chunks)

    translated_parts: list[str] = []
    failed_details:   list[dict] = []

    for i, chunk in enumerate(chunks, start=1):
        if progress_callback:
            progress_callback(i, total, f"正在翻譯第 {i} / {total} 段...")

        try:
            instruction = _build_instruction(chunk, direction)
            result = _call_ai(instruction, ai_client, ai_provider, model)
            translated_parts.append(result)
        except Exception as e:
            failed_details.append({"chunk": i, "error": str(e)})
            # Keep a placeholder so ordering is preserved
            translated_parts.append(f"[第 {i} 段翻譯失敗：{e}]")

    success_chunks = total - len(failed_details)
    merged = "\n\n".join(translated_parts)

    return {
        "translated":     merged,
        "total_chunks":   total,
        "success_chunks": success_chunks,
        "failed_chunks":  len(failed_details),
        "failed_details": failed_details,
        "is_complete":    len(failed_details) == 0,
        "truncated":      truncated,
    }


# ── DOCX extraction ───────────────────────────────────────────────────────────
def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract all paragraph text from a DOCX file."""
    try:
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except Exception as e:
        raise RuntimeError(f"DOCX extraction failed: {e}") from e


def extract_text_from_xlsx(file_bytes: bytes) -> str:
    """Extract all cell text from an XLSX file."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        lines = []
        for sheet in wb.worksheets:
            lines.append(f"[Sheet: {sheet.title}]")
            for row in sheet.iter_rows(values_only=True):
                row_text = "\t".join(str(c) if c is not None else "" for c in row)
                if row_text.strip():
                    lines.append(row_text)
        return "\n".join(lines)
    except Exception as e:
        raise RuntimeError(f"XLSX extraction failed: {e}") from e


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file using pypdf."""
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"[Page {i+1}]\n{text.strip()}")
        selectable = "\n\n".join(pages)
        if selectable.strip():
            return selectable

        from utils.ocr_engine import extract_text_from_bytes_with_ocr
        ocr = extract_text_from_bytes_with_ocr(file_bytes, "upload.pdf")
        if ocr.get("extracted_text"):
            return ocr["extracted_text"]
        return ""
    except Exception as e:
        raise RuntimeError(f"PDF extraction failed: {e}") from e


def extract_text_from_image(file_bytes: bytes, source_filename: str) -> str:
    """Extract text from JPG/PNG using OCR."""
    try:
        from utils.ocr_engine import extract_text_from_bytes_with_ocr
        ocr = extract_text_from_bytes_with_ocr(file_bytes, source_filename)
        return ocr.get("extracted_text", "")
    except Exception as e:
        raise RuntimeError(f"Image OCR extraction failed: {e}") from e


# ── Output builders ───────────────────────────────────────────────────────────
def build_translated_pdf(
    translated_text: str,
    source_filename: str,
    direction: str,
    original_text: str = "",
) -> bytes:
    """
    Build a PDF from translated text with embedded NotoSansTC font.
    Returns PDF bytes.
    """
    if not _REPORTLAB_OK:
        raise RuntimeError("reportlab not installed")

    font_name = _ensure_font()
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
        title=f"Translation — {source_filename}",
        author="HK-AICOS | Buildway Tech (HK) Limited",
    )

    direction_label = "英文 → 繁體中文" if direction == "en_to_tc" else "繁體中文 → 英文"

    styles = {
        "title": ParagraphStyle(
            "title", fontName=font_name, fontSize=16, leading=22,
            textColor=colors.HexColor("#1a3a5c"), spaceAfter=6,
        ),
        "meta": ParagraphStyle(
            "meta", fontName=font_name, fontSize=9, leading=13,
            textColor=colors.HexColor("#666666"), spaceAfter=4,
        ),
        "heading": ParagraphStyle(
            "heading", fontName=font_name, fontSize=11, leading=16,
            textColor=colors.HexColor("#1a3a5c"), spaceBefore=10, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body", fontName=font_name, fontSize=10, leading=16,
            textColor=colors.HexColor("#222222"), spaceAfter=4,
        ),
        "disclaimer": ParagraphStyle(
            "disclaimer", fontName=font_name, fontSize=8, leading=12,
            textColor=colors.HexColor("#888888"),
        ),
    }

    story = []

    # Header
    story.append(Paragraph("HK-AICOS 文件翻譯", styles["title"]))
    story.append(Paragraph(f"翻譯方向：{direction_label}", styles["meta"]))
    story.append(Paragraph(f"來源文件：{source_filename}", styles["meta"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#c9a84c"), spaceAfter=8))

    # Translated content
    story.append(Paragraph("翻譯結果", styles["heading"]))
    for line in translated_text.split("\n"):
        line = line.strip()
        if line:
            # Escape XML special chars
            safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(safe, styles["body"]))
        else:
            story.append(Spacer(1, 4))

    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc"), spaceAfter=6))
    story.append(Paragraph(
        "本翻譯由 HK-AICOS AI 系統生成，僅供參考。工程術語及法律文件請由專業人士確認。"
        " | Buildway Tech (HK) Limited",
        styles["disclaimer"],
    ))

    doc.build(story)
    return buf.getvalue()


def build_translated_docx(
    translated_text: str,
    source_filename: str,
    direction: str,
) -> bytes:
    """Build a DOCX from translated text. Returns DOCX bytes."""
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except ImportError:
        raise RuntimeError("python-docx not installed")

    direction_label = "英文 → 繁體中文" if direction == "en_to_tc" else "繁體中文 → 英文"

    doc = Document()

    # Title
    title_para = doc.add_heading("HK-AICOS 文件翻譯", level=1)
    title_para.runs[0].font.color.rgb = RGBColor(0x1a, 0x3a, 0x5c)

    doc.add_paragraph(f"翻譯方向：{direction_label}")
    doc.add_paragraph(f"來源文件：{source_filename}")
    doc.add_paragraph("─" * 40)

    doc.add_heading("翻譯結果", level=2)

    for line in translated_text.split("\n"):
        doc.add_paragraph(line)

    doc.add_paragraph("─" * 40)
    disclaimer = doc.add_paragraph(
        "本翻譯由 HK-AICOS AI 系統生成，僅供參考。工程術語及法律文件請由專業人士確認。"
        " | Buildway Tech (HK) Limited"
    )
    disclaimer.runs[0].font.size = Pt(8)
    disclaimer.runs[0].font.color.rgb = RGBColor(0x88, 0x88, 0x88)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_translated_txt(translated_text: str, source_filename: str, direction: str) -> bytes:
    """Build a plain UTF-8 TXT from translated text."""
    direction_label = "英文 → 繁體中文" if direction == "en_to_tc" else "繁體中文 → 英文"
    header = (
        f"HK-AICOS 文件翻譯\n"
        f"翻譯方向：{direction_label}\n"
        f"來源文件：{source_filename}\n"
        f"{'─' * 40}\n\n"
    )
    footer = (
        f"\n{'─' * 40}\n"
        "本翻譯由 HK-AICOS AI 系統生成，僅供參考。\n"
        "Buildway Tech (HK) Limited\n"
    )
    return (header + translated_text + footer).encode("utf-8")


# ── Excel → PDF ───────────────────────────────────────────────────────────────

def _xlsx_image_anchor(xlsx_image):
    """
    Return (row_0based, col_0based) anchor from an openpyxl image.
    Returns (None, None) if anchor cannot be read.
    openpyxl uses 0-based row/col in anchor._from.
    """
    try:
        marker = getattr(xlsx_image.anchor, "_from", None)
        if marker is not None:
            return int(marker.row), int(marker.col)
    except Exception:
        pass
    return None, None


def _xlsx_image_anchor_row(xlsx_image) -> int:
    """Return approximate 1-based row for an openpyxl embedded image (for sorting)."""
    row, _ = _xlsx_image_anchor(xlsx_image)
    return (row + 1) if row is not None else 0


def _xlsx_image_bytes(xlsx_image) -> bytes:
    """
    Extract raw bytes from an openpyxl embedded image.

    openpyxl stores image data in different ways depending on version:
      - older versions: xlsx_image._data is a callable (method)
      - newer versions: xlsx_image._data is a bytes property or BytesIO
    We try both forms so this works across openpyxl versions.
    """
    # Try as a callable first (older openpyxl)
    raw = getattr(xlsx_image, "_data", None)
    if callable(raw):
        data = raw()
    else:
        data = raw

    if isinstance(data, bytes) and data:
        return data
    if hasattr(data, "read"):
        result = data.read()
        if isinstance(result, bytes) and result:
            return result

    # Fallback: try ref attribute (openpyxl stores path inside zip)
    ref = getattr(xlsx_image, "ref", None)
    if ref and hasattr(xlsx_image, "_parent"):
        try:
            parent = xlsx_image._parent
            archive = getattr(parent, "_archive", None) or getattr(parent, "archive", None)
            if archive:
                return archive.read(ref)
        except Exception:
            pass

    raise ValueError(f"unsupported openpyxl image data type: {type(data)}")


def _build_xlsx_image_flowable(xlsx_image, max_width: float, max_height: float):
    """
    Create a resized ReportLab Image flowable from an openpyxl image.
    Constrains to max_width × max_height while preserving aspect ratio.
    """
    image_bytes = _xlsx_image_bytes(xlsx_image)
    image_stream = io.BytesIO(image_bytes)

    try:
        from PIL import Image as PILImage
        with PILImage.open(io.BytesIO(image_bytes)) as pil_img:
            width_px, height_px = pil_img.size
    except Exception:
        width_px = float(getattr(xlsx_image, "width", 0) or 0)
        height_px = float(getattr(xlsx_image, "height", 0) or 0)

    if not width_px or not height_px:
        width_px, height_px = 320, 180

    # Treat pixels roughly as points, then constrain to cell/content area.
    scale = min(max_width / width_px, max_height / height_px, 1.0)
    draw_width = width_px * scale
    draw_height = height_px * scale
    return RLImage(image_stream, width=draw_width, height=draw_height)


def _build_image_cell_content(xlsx_image, col_width: float, cell_text: str,
                               cell_style, font_name: str):
    """
    Build a list of flowables for a table cell that contains an image.
    Image is shown first; if there is also text, it appears below the image.
    Returns (flowable_list, draw_height) or (None, 0) on failure.
    draw_height is the rendered image height in points (for row height calculation).
    """
    # Leave a small margin inside the cell
    img_max_w = max(col_width - 6, 10)
    # Cap image height at a reasonable value per cell
    img_max_h = 72 * mm

    try:
        img_flowable = _build_xlsx_image_flowable(xlsx_image, img_max_w, img_max_h)
    except Exception as e:
        print(f"[translator] WARNING: image flowable failed: {e}", file=sys.stderr)
        return None, 0  # signal failure

    draw_height = img_flowable.drawHeight  # actual rendered height in points

    items = [img_flowable]
    if cell_text and cell_text.strip():
        safe = cell_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        items.append(Paragraph(safe[:100], cell_style))
        draw_height += 14  # approximate text line height

    return items, draw_height


def excel_to_pdf(file_bytes: bytes, source_filename: str) -> bytes:
    """
    Convert XLSX to PDF using reportlab.
    Renders each sheet as a table in the PDF.
    Images are placed in the table cell matching their Excel anchor (row, col).
    Images that cannot be positioned fall back to an appendix section.
    """
    if not _REPORTLAB_OK:
        raise RuntimeError("reportlab not installed")

    try:
        import openpyxl
    except ImportError:
        raise RuntimeError("openpyxl not installed")

    font_name = _ensure_font()

    # Must NOT use read_only=True — _images is unavailable in read-only mode
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15*mm,
        rightMargin=15*mm,
        topMargin=15*mm,
        bottomMargin=15*mm,
        title=f"Excel Export — {source_filename}",
        author="HK-AICOS | Buildway Tech (HK) Limited",
    )

    title_style = ParagraphStyle(
        "title", fontName=font_name, fontSize=14, leading=20,
        textColor=colors.HexColor("#1a3a5c"), spaceAfter=4,
    )
    sheet_style = ParagraphStyle(
        "sheet", fontName=font_name, fontSize=11, leading=16,
        textColor=colors.HexColor("#2d5a8e"), spaceBefore=8, spaceAfter=4,
    )
    cell_style = ParagraphStyle(
        "cell", fontName=font_name, fontSize=8, leading=11,
        textColor=colors.HexColor("#222222"),
    )
    warning_style = ParagraphStyle(
        "warning", fontName=font_name, fontSize=9, leading=13,
        textColor=colors.HexColor("#cc6600"), spaceBefore=6, spaceAfter=4,
    )
    disclaimer_style = ParagraphStyle(
        "disclaimer", fontName=font_name, fontSize=8, leading=12,
        textColor=colors.HexColor("#888888"),
    )

    story = []
    any_image_warning = False   # True if any image failed entirely
    any_fallback_image = False  # True if any image fell back to appendix

    story.append(Paragraph(f"Excel 轉換：{source_filename}", title_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#c9a84c"), spaceAfter=6))

    MAX_COLS = 10
    available_width = A4[0] - 30 * mm

    for sheet in wb.worksheets:
        story.append(Paragraph(f"工作表：{sheet.title}", sheet_style))

        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            story.append(Paragraph("（此工作表為空）", cell_style))
            continue

        # ── Step 1: Build image anchor map ────────────────────────────────────
        # key: (row_0based, col_0based) → openpyxl image object
        # Images whose anchor falls outside the table go to fallback list.
        sheet_images = list(getattr(sheet, "_images", []) or [])
        image_map: dict = {}       # (row, col) → xlsx_image
        fallback_images: list = [] # images that couldn't be mapped to a cell

        num_data_rows = len(rows)
        num_data_cols = min(MAX_COLS, len(rows[0]) if rows else 0)

        for xlsx_image in sheet_images:
            try:
                anchor_row, anchor_col = _xlsx_image_anchor(xlsx_image)
                if (anchor_row is not None and anchor_col is not None
                        and 0 <= anchor_row < num_data_rows
                        and 0 <= anchor_col < num_data_cols):
                    # If multiple images share a cell, keep the first one
                    key = (anchor_row, anchor_col)
                    if key not in image_map:
                        image_map[key] = xlsx_image
                    else:
                        fallback_images.append(xlsx_image)
                else:
                    fallback_images.append(xlsx_image)
            except Exception as e:
                print(f"[translator] WARNING: could not read image anchor: {e}", file=sys.stderr)
                fallback_images.append(xlsx_image)

        # ── Step 2: Build table data with images in correct cells ─────────────
        col_width = available_width / max(num_data_cols, 1)

        # Track which rows need extra height because they contain images
        row_heights: list = []

        table_data = []
        for r_idx, row in enumerate(rows):
            row_cells = []
            row_has_image = False
            row_img_height = 0  # max image height in this row (points)

            for c_idx, cell_val in enumerate(row[:MAX_COLS]):
                cell_text = str(cell_val) if cell_val is not None else ""
                img_key = (r_idx, c_idx)

                if img_key in image_map:
                    # This cell has an image — build combined cell content
                    row_has_image = True
                    cell_content, img_h = _build_image_cell_content(
                        image_map[img_key],
                        col_width,
                        cell_text,
                        cell_style,
                        font_name,
                    )
                    if cell_content is not None:
                        # ReportLab Table accepts a list of flowables per cell
                        row_cells.append(cell_content)
                        row_img_height = max(row_img_height, img_h)
                    else:
                        # Image build failed — fall back to text only
                        any_image_warning = True
                        safe = cell_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        row_cells.append(Paragraph(safe[:100], cell_style))
                        fallback_images.append(image_map[img_key])
                else:
                    safe = cell_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    row_cells.append(Paragraph(safe[:100], cell_style))

            # Pad if fewer columns than header
            while len(row_cells) < num_data_cols:
                row_cells.append(Paragraph("", cell_style))

            table_data.append(row_cells)

            # Rows with images get an explicit minimum height so the image is visible.
            # Add 8pt padding (top+bottom) on top of the image height.
            if row_has_image and row_img_height > 0:
                row_heights.append(row_img_height + 8)
            else:
                row_heights.append(None)  # auto height for text-only rows

        if not table_data:
            continue

        tbl = Table(
            table_data,
            colWidths=[col_width] * num_data_cols,
            rowHeights=row_heights,
            repeatRows=1,
        )
        tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#1a3a5c")),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",      (0, 0), (-1, -1), font_name),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7fa")]),
            ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 8))

        # ── Step 3: Fallback appendix for images that couldn't be placed ──────
        if fallback_images:
            any_fallback_image = True
            story.append(Paragraph(
                "部分圖片未能按原 Excel 位置顯示，已改為附錄顯示。",
                warning_style,
            ))
            story.append(Paragraph(f"【{sheet.title}】附錄圖片", sheet_style))
            for fb_idx, xlsx_image in enumerate(fallback_images, 1):
                try:
                    anchor_row, anchor_col = _xlsx_image_anchor(xlsx_image)
                    if anchor_row is not None and anchor_col is not None:
                        loc_label = f"原位置約 第{anchor_row + 1}行 / 第{anchor_col + 1}列"
                    else:
                        loc_label = "原工作表位置不明"
                    story.append(Paragraph(f"附錄圖片 {fb_idx}（{loc_label}）", cell_style))
                    story.append(_build_xlsx_image_flowable(
                        xlsx_image,
                        max_width=available_width,
                        max_height=85 * mm,
                    ))
                    story.append(Spacer(1, 5))
                except Exception as e:
                    any_image_warning = True
                    print(f"[translator] WARNING: could not render fallback XLSX image: {e}", file=sys.stderr)

    if any_image_warning:
        story.append(Paragraph("部分 Excel 圖片未能轉換，已保留文字內容。", disclaimer_style))
        story.append(Spacer(1, 4))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc"), spaceAfter=4))
    story.append(Paragraph(
        "由 HK-AICOS 轉換 | Buildway Tech (HK) Limited",
        disclaimer_style,
    ))

    doc.build(story)
    return buf.getvalue()


# ── DOCX → PDF ────────────────────────────────────────────────────────────────
def docx_to_pdf(file_bytes: bytes, source_filename: str) -> bytes:
    """
    Convert DOCX to PDF using reportlab.
    Extracts paragraphs and renders them with embedded font.
    """
    if not _REPORTLAB_OK:
        raise RuntimeError("reportlab not installed")

    try:
        from docx import Document
    except ImportError:
        raise RuntimeError("python-docx not installed")

    font_name = _ensure_font()
    doc_in = Document(io.BytesIO(file_bytes))

    buf = io.BytesIO()
    doc_out = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
        title=f"DOCX Export — {source_filename}",
        author="HK-AICOS | Buildway Tech (HK) Limited",
    )

    title_style = ParagraphStyle(
        "title", fontName=font_name, fontSize=14, leading=20,
        textColor=colors.HexColor("#1a3a5c"), spaceAfter=4,
    )
    h1_style = ParagraphStyle(
        "h1", fontName=font_name, fontSize=13, leading=18,
        textColor=colors.HexColor("#1a3a5c"), spaceBefore=8, spaceAfter=4,
    )
    h2_style = ParagraphStyle(
        "h2", fontName=font_name, fontSize=11, leading=16,
        textColor=colors.HexColor("#2d5a8e"), spaceBefore=6, spaceAfter=3,
    )
    body_style = ParagraphStyle(
        "body", fontName=font_name, fontSize=10, leading=16,
        textColor=colors.HexColor("#222222"), spaceAfter=3,
    )
    disclaimer_style = ParagraphStyle(
        "disclaimer", fontName=font_name, fontSize=8, leading=12,
        textColor=colors.HexColor("#888888"),
    )

    story = []
    story.append(Paragraph(f"文件轉換：{source_filename}", title_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#c9a84c"), spaceAfter=8))

    for para in doc_in.paragraphs:
        text = para.text.strip()
        if not text:
            story.append(Spacer(1, 4))
            continue

        safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        style_name = para.style.name if para.style else ""

        if "Heading 1" in style_name or style_name.startswith("Title"):
            story.append(Paragraph(safe, h1_style))
        elif "Heading 2" in style_name:
            story.append(Paragraph(safe, h2_style))
        else:
            story.append(Paragraph(safe, body_style))

    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc"), spaceAfter=4))
    story.append(Paragraph(
        "由 HK-AICOS 轉換 | Buildway Tech (HK) Limited",
        disclaimer_style,
    ))

    doc_out.build(story)
    return buf.getvalue()


# ── Image → PowerPoint (BETA) ─────────────────────────────────────────────────
def image_to_pptx_beta(file_bytes: bytes, source_filename: str) -> bytes:
    """
    BETA: Convert image to a single-slide PowerPoint.
    Requires python-pptx. Returns PPTX bytes.
    """
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor as PptxRGB
    except ImportError:
        raise RuntimeError(
            "python-pptx not installed. "
            "此功能為 Beta 版，需要安裝 python-pptx。"
        )

    prs = Presentation()
    slide_layout = prs.slide_layouts[6]  # blank
    slide = prs.slides.add_slide(slide_layout)

    # Add image
    img_stream = io.BytesIO(file_bytes)
    slide.shapes.add_picture(img_stream, Inches(0.5), Inches(0.5), width=Inches(9))

    # Add caption
    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(6.8), Inches(9), Inches(0.5))
    tf = txBox.text_frame
    tf.text = f"來源：{source_filename} | HK-AICOS Beta | Buildway Tech (HK) Limited"
    tf.paragraphs[0].runs[0].font.size = Pt(9)
    tf.paragraphs[0].runs[0].font.color.rgb = PptxRGB(0x88, 0x88, 0x88)

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


# ── Translator Agent personality (for prompt injection) ───────────────────────
TRANSLATOR_AGENT_INSTRUCTION = """你是 HK-AICOS 文件翻譯 Agent，專門處理香港建築及工程行業文件翻譯。

性格：準確、保守、工程術語優先、香港工程語境、不亂改原意。

職責：
- 英文轉繁體中文（香港工程術語）
- 繁體中文轉英文（標準工程英文）
- 保持原文件結構及段落
- 工程術語使用香港慣用表達
- 不加入額外解釋或意見
- 不改變原意

輸出規則：
- 只輸出翻譯結果
- 不輸出任何說明、前言或後記
- 保持原文段落結構
- 數字、代號、圖則編號保持原樣
"""
