# -*- coding: utf-8 -*-
"""
utils/ocr_engine.py
HK-AICOS Phase 3.2A — OCR layer for scanned PDFs and image files.

Local OCR only. No cloud OCR, no background queue.
"""

import tempfile
from pathlib import Path
from typing import Any

import pypdf
from PIL import Image

from .analysis_models import OCRResult


MAX_OCR_PDF_PAGES = 20
OCR_UNAVAILABLE_MESSAGE = "OCR 功能暫未可用，請提供可選取文字的 PDF。"
OCR_FAILED_MESSAGE = "未能透過 OCR 抽取文字，請提供較清晰文件或可選取文字 PDF。"
OCR_SUCCESS_MESSAGE = "已透過 OCR 成功抽取文字"
OCR_LARGE_PDF_MESSAGE = "大型掃描 PDF 暫只處理前 20 頁，完整 OCR 將於後續版本支援。"
OCR_PHASE_MESSAGE = "此文件可能為掃描 PDF，OCR 將於 Phase 3.2 支援。"


def _base_result(file_path: Path, file_type: str) -> dict[str, Any]:
    return {
        "file_path": str(file_path),
        "file_type": file_type,
        "extracted_text": "",
        "selectable_text": "",
        "ocr_used": False,
        "ocr_page_count": 0,
        "ocr_status": "NOT_ATTEMPTED",
        "ocr_message": "",
        "page_count": 0,
        "is_scanned_pdf": False,
        "warning": "",
    }


def _normalise_text(text: str) -> str:
    return "\n".join(line.strip() for line in str(text or "").splitlines() if line.strip())


def extract_selectable_pdf_text(file_path: Path, max_pages: int | None = None) -> tuple[str, int]:
    """Extract selectable text from a PDF using pypdf."""
    reader = pypdf.PdfReader(str(file_path))
    page_count = len(reader.pages)
    limit = min(page_count, max_pages) if max_pages else page_count
    parts = []
    for idx, page in enumerate(reader.pages[:limit], 1):
        text = page.extract_text() or ""
        if text.strip():
            parts.append(f"[Page {idx}]\n{text.strip()}")
    return "\n\n".join(parts), page_count


def _tesseract_available() -> tuple[bool, str]:
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True, ""
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _ocr_image_object(image) -> str:
    import pytesseract

    return pytesseract.image_to_string(image, lang="eng+chi_tra")


def ocr_image(file_path: Path) -> dict[str, Any]:
    """OCR a JPG / PNG image."""
    result = _base_result(file_path, "image")
    available, reason = _tesseract_available()
    if not available:
        result.update({
            "ocr_status": "OCR_UNAVAILABLE",
            "ocr_message": OCR_UNAVAILABLE_MESSAGE,
            "warning": reason,
        })
        return result

    try:
        with Image.open(file_path) as image:
            text = _normalise_text(_ocr_image_object(image))
        if text:
            result.update({
                "extracted_text": text,
                "ocr_used": True,
                "ocr_page_count": 1,
                "ocr_status": "OCR_SUCCESS",
                "ocr_message": OCR_SUCCESS_MESSAGE,
            })
        else:
            result.update({
                "ocr_status": "OCR_FAILED",
                "ocr_message": OCR_FAILED_MESSAGE,
            })
    except Exception as exc:
        result.update({
            "ocr_status": "OCR_FAILED",
            "ocr_message": OCR_FAILED_MESSAGE,
            "warning": f"{type(exc).__name__}: {exc}",
        })
    return result


def ocr_pdf(file_path: Path, page_count: int = 0, max_pages: int = MAX_OCR_PDF_PAGES) -> dict[str, Any]:
    """OCR the first max_pages pages of a scanned PDF."""
    result = _base_result(file_path, "pdf")
    result["page_count"] = page_count
    result["is_scanned_pdf"] = True

    available, reason = _tesseract_available()
    if not available:
        result.update({
            "ocr_status": "OCR_UNAVAILABLE",
            "ocr_message": OCR_UNAVAILABLE_MESSAGE,
            "warning": reason,
        })
        return result

    try:
        from pdf2image import convert_from_path
    except Exception as exc:
        result.update({
            "ocr_status": "OCR_UNAVAILABLE",
            "ocr_message": OCR_UNAVAILABLE_MESSAGE,
            "warning": f"pdf2image unavailable: {type(exc).__name__}: {exc}",
        })
        return result

    try:
        pages_to_process = min(page_count or max_pages, max_pages)
        images = convert_from_path(
            str(file_path),
            first_page=1,
            last_page=pages_to_process,
        )
        parts = []
        for idx, image in enumerate(images, 1):
            text = _normalise_text(_ocr_image_object(image))
            if text:
                parts.append(f"[OCR Page {idx}]\n{text}")
        merged = "\n\n".join(parts)
        if merged:
            warning = OCR_LARGE_PDF_MESSAGE if page_count > max_pages else ""
            result.update({
                "extracted_text": merged,
                "ocr_used": True,
                "ocr_page_count": len(images),
                "ocr_status": "OCR_SUCCESS",
                "ocr_message": OCR_SUCCESS_MESSAGE,
                "warning": warning,
            })
        else:
            result.update({
                "ocr_page_count": len(images),
                "ocr_status": "OCR_FAILED",
                "ocr_message": OCR_FAILED_MESSAGE,
            })
    except Exception as exc:
        result.update({
            "ocr_status": "OCR_FAILED",
            "ocr_message": OCR_FAILED_MESSAGE,
            "warning": f"{type(exc).__name__}: {exc}",
        })
    return result


def extract_text_with_ocr(file_path: Path) -> dict[str, Any]:
    """
    Extract text from PDF/JPG/PNG with OCR fallback.

    For PDFs, selectable text is preferred. If no selectable text exists,
    OCR is attempted for the first 20 pages only.
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        result = _base_result(file_path, "pdf")
        try:
            selectable_text, page_count = extract_selectable_pdf_text(file_path)
            result["page_count"] = page_count
            result["selectable_text"] = selectable_text
            if selectable_text.strip():
                result.update({
                    "extracted_text": selectable_text,
                    "ocr_status": "SELECTABLE_TEXT",
                    "ocr_message": "PDF 已包含可選取文字，無需 OCR。",
                    "ocr_page_count": 0,
                })
                return result
            result["ocr_status"] = "OCR_REQUIRED"
            result["ocr_message"] = OCR_PHASE_MESSAGE
            return ocr_pdf(file_path, page_count=page_count)
        except Exception as exc:
            result.update({
                "ocr_status": "OCR_FAILED",
                "ocr_message": OCR_FAILED_MESSAGE,
                "warning": f"{type(exc).__name__}: {exc}",
            })
            return result

    if suffix in {".jpg", ".jpeg", ".png"}:
        return ocr_image(file_path)

    result = _base_result(file_path, suffix.lstrip(".") or "unknown")
    result["ocr_status"] = "UNSUPPORTED_FILE_TYPE"
    result["ocr_message"] = "此文件類型不需要 OCR。"
    return result


def extract_text_from_bytes_with_ocr(file_bytes: bytes, filename: str) -> dict[str, Any]:
    """Write bytes to a temp file and run extract_text_with_ocr()."""
    suffix = Path(filename).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = Path(tmp.name)
    try:
        return extract_text_with_ocr(tmp_path)
    finally:
        try:
            tmp_path.unlink()
        except Exception:
            pass


def to_ocr_result(result: dict[str, Any] | OCRResult | None) -> OCRResult:
    """Convert the legacy OCR dictionary into the shared typed model."""
    if isinstance(result, OCRResult):
        return result
    result = dict(result or {})
    status = str(result.get("ocr_status", "NOT_ATTEMPTED"))
    confidence_by_status = {
        "SELECTABLE_TEXT": 0.98,
        "OCR_SUCCESS": 0.72,
        "OCR_FAILED": 0.0,
        "OCR_UNAVAILABLE": 0.0,
        "UNSUPPORTED_FILE_TYPE": 0.0,
    }
    text = str(result.get("extracted_text") or result.get("text") or "").strip()
    metadata = {
        key: value
        for key, value in result.items()
        if key not in {"extracted_text", "text", "selectable_text"}
    }
    return OCRResult(
        text=text,
        confidence=confidence_by_status.get(status, 0.45 if text else 0.0),
        engine="pypdf" if status == "SELECTABLE_TEXT" else "tesseract_local",
        language="eng+chi_tra",
        metadata=metadata,
    )


def run_ocr(file_path: str | Path) -> OCRResult:
    """Run local OCR and always return a non-throwing structured result."""
    try:
        return to_ocr_result(extract_text_with_ocr(Path(file_path)))
    except Exception as exc:  # final safety net for optional native OCR dependencies
        return OCRResult(
            engine="local_ocr",
            metadata={
                "ocr_status": "OCR_FAILED",
                "warning": f"{type(exc).__name__}: {exc}",
            },
        )
