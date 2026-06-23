"""PDF / image drawing ingestion for Phase 5.10B.

Turns an uploaded drawing file into a list of analyzable page payloads. It
reuses the existing OCR layer (``utils.ocr_engine``) and ``pypdf`` (already a
project dependency). Heavy rasterisation (``pdf2image`` / poppler) is optional:
when it is missing the ingest degrades gracefully to selectable-text / OCR /
metadata only -- it never raises for a readable file.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .ocr_engine import extract_text_with_ocr, ocr_image

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
DEFAULT_MAX_PAGES = 12
_PAGE_MARKER = re.compile(r"\[(?:OCR )?Page\s+(\d+)\]", re.IGNORECASE)


def _normalise(text: str) -> str:
    return "\n".join(line.strip() for line in str(text or "").splitlines() if line.strip())


def _split_marked_text(blob: str) -> dict[int, str]:
    """Split OCR-engine output that uses ``[Page N]`` / ``[OCR Page N]`` markers."""
    pages: dict[int, str] = {}
    if not blob:
        return pages
    parts = _PAGE_MARKER.split(blob)
    # parts = [pre, num, body, num, body, ...]
    for idx in range(1, len(parts) - 1, 2):
        try:
            number = int(parts[idx])
        except (TypeError, ValueError):
            continue
        pages[number] = _normalise(parts[idx + 1])
    return pages


def _ingest_image(file_path: Path) -> dict[str, Any]:
    result = ocr_image(file_path)
    text = _normalise(result.get("extracted_text", ""))
    status = str(result.get("ocr_status", "NOT_ATTEMPTED"))
    note = str(result.get("ocr_message") or result.get("warning") or "")
    page = {
        "page_number": 1,
        "text": text,
        "ocr_status": status,
        "image_path": str(file_path),
        "source": "image",
    }
    return {
        "file_type": "image",
        "page_count": 1,
        "analyzed_page_count": 1,
        "pages": [page],
        "ingestion_status": "ocr" if text else "image_only",
        "notes": [note] if note else [],
    }


def _ingest_pdf(file_path: Path, max_pages: int) -> dict[str, Any]:
    notes: list[str] = []
    try:
        import pypdf

        reader = pypdf.PdfReader(str(file_path))
        page_count = len(reader.pages)
    except Exception as exc:  # unreadable / encrypted PDF
        return {
            "file_type": "pdf",
            "page_count": 0,
            "analyzed_page_count": 0,
            "pages": [],
            "ingestion_status": "metadata_only",
            "notes": [f"PDF 無法解析：{type(exc).__name__}"],
        }

    limit = min(page_count, max(1, max_pages))
    if page_count > limit:
        notes.append(f"圖紙頁數較多，只分析前 {limit} 頁（共 {page_count} 頁）。")

    pages: list[dict[str, Any]] = []
    any_text = False
    for index in range(limit):
        try:
            raw = reader.pages[index].extract_text() or ""
        except Exception:
            raw = ""
        text = _normalise(raw)
        if text:
            any_text = True
        pages.append({
            "page_number": index + 1,
            "text": text,
            "ocr_status": "SELECTABLE_TEXT" if text else "EMPTY",
            "image_path": None,
            "source": "pdf_text",
        })

    ingestion_status = "selectable_text" if any_text else "metadata_only"

    # No selectable text anywhere -> attempt OCR fallback for the whole file.
    if not any_text:
        try:
            ocr = extract_text_with_ocr(file_path)
        except Exception as exc:
            ocr = {"ocr_status": "OCR_FAILED", "warning": f"{type(exc).__name__}: {exc}"}
        ocr_status = str(ocr.get("ocr_status", "OCR_FAILED"))
        message = str(ocr.get("ocr_message") or ocr.get("warning") or "")
        per_page = _split_marked_text(str(ocr.get("extracted_text", "")))
        if per_page:
            ingestion_status = "ocr"
            for page in pages:
                page_text = per_page.get(page["page_number"], "")
                if page_text:
                    page["text"] = page_text
                    page["ocr_status"] = ocr_status
                    page["source"] = "pdf_ocr"
        else:
            for page in pages:
                page["ocr_status"] = ocr_status
            if message:
                notes.append(message)
            else:
                notes.append("此 PDF 沒有可選取文字，且 OCR 未能抽取內容；只可作有限分析。")

    return {
        "file_type": "pdf",
        "page_count": page_count,
        "analyzed_page_count": len(pages),
        "pages": pages,
        "ingestion_status": ingestion_status,
        "notes": notes,
    }


def ingest_drawing(file_path: str | Path, *, max_pages: int = DEFAULT_MAX_PAGES) -> dict[str, Any]:
    """Ingest a drawing file into per-page payloads. Never raises for a readable file."""
    path = Path(file_path)
    suffix = path.suffix.lower()
    if not path.exists() or not path.is_file():
        return {
            "file_type": "unsupported",
            "page_count": 0,
            "analyzed_page_count": 0,
            "pages": [],
            "ingestion_status": "unsupported",
            "notes": ["找不到上載的圖紙檔案。"],
        }
    if suffix in IMAGE_SUFFIXES:
        return _ingest_image(path)
    if suffix == ".pdf":
        return _ingest_pdf(path, max_pages)
    return {
        "file_type": "unsupported",
        "page_count": 0,
        "analyzed_page_count": 0,
        "pages": [],
        "ingestion_status": "unsupported",
        "notes": [f"暫不支援此檔案類型：{suffix or '未知'}。請提供 PDF 或圖片圖紙。"],
    }


def rasterize_pdf_page(file_path: str | Path, page_number: int) -> Path | None:
    """Best-effort rasterisation of one PDF page to a temp PNG for vision.

    Returns ``None`` when ``pdf2image`` / poppler is unavailable. The caller is
    responsible for deleting the temp file.
    """
    try:
        from pdf2image import convert_from_path
    except Exception:
        return None
    try:
        import tempfile

        images = convert_from_path(str(file_path), first_page=page_number, last_page=page_number)
        if not images:
            return None
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tmp_path = Path(tmp.name)
        tmp.close()
        images[0].save(str(tmp_path), "PNG")
        return tmp_path
    except Exception:
        return None
