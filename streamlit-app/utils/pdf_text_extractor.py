"""Lightweight, page-aware PDF / text extraction for knowledge ingestion (Phase 6.4).

Uses :mod:`pypdf` for selectable text only — no heavy OCR dependency. A scanned
or image-only PDF degrades gracefully to a *metadata-only* result with a clear
Traditional-Chinese warning, instead of raising.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Status vocabulary for an extraction attempt.
STATUS_SELECTABLE = "selectable_text"
STATUS_METADATA_ONLY = "metadata_only"
STATUS_ERROR = "error"

METADATA_ONLY_WARNING = (
    "未能抽取清晰文字，已建立 metadata-only 知識來源；"
    "如需全文搜尋，請使用 OCR 版本或補充文字。"
)

# Minimum characters across the document to treat it as having usable text.
_MIN_TEXT_CHARS = 20
_SECRET_LINE = re.compile(r"(?i)(api[_-]?key|secret|password|token|authorization)\s*[:=]|sk-[a-z0-9_-]{8,}")


@dataclass
class PageText:
    page_number: int
    text: str


@dataclass
class ExtractionResult:
    status: str
    pages: list[PageText] = field(default_factory=list)
    page_count: int = 0
    total_chars: int = 0
    warning: str = ""

    @property
    def has_text(self) -> bool:
        return self.status == STATUS_SELECTABLE and self.total_chars >= _MIN_TEXT_CHARS

    @property
    def full_text(self) -> str:
        return "\n\n".join(page.text for page in self.pages if page.text)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "page_count": self.page_count,
            "total_chars": self.total_chars,
            "warning": self.warning,
            "pages": [{"page_number": page.page_number, "text": page.text} for page in self.pages],
        }


def _strip_secrets(text: str) -> str:
    return "\n".join(line for line in str(text or "").splitlines() if not _SECRET_LINE.search(line))


def extract_pdf_pages(path: str | Path) -> ExtractionResult:
    """Extract selectable text per page from a PDF.

    Returns an :class:`ExtractionResult`. Never raises: a missing file, an
    unreadable PDF or an image-only PDF all map to a ``metadata_only`` /
    ``error`` status with a warning.
    """
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return ExtractionResult(status=STATUS_ERROR, warning="找不到檔案或檔案無法讀取。")

    try:
        import pypdf
    except ImportError:
        return ExtractionResult(status=STATUS_ERROR, warning="PDF 讀取元件未安裝。")

    try:
        reader = pypdf.PdfReader(str(file_path))
        raw_pages = list(reader.pages)
    except Exception:
        return ExtractionResult(status=STATUS_ERROR, warning="無法解析 PDF 檔案內容。")

    pages: list[PageText] = []
    total_chars = 0
    for index, page in enumerate(raw_pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        text = _strip_secrets(text).strip()
        total_chars += len(text)
        if text:
            pages.append(PageText(page_number=index, text=text))

    page_count = len(raw_pages)
    if total_chars >= _MIN_TEXT_CHARS and pages:
        return ExtractionResult(
            status=STATUS_SELECTABLE,
            pages=pages,
            page_count=page_count,
            total_chars=total_chars,
        )
    return ExtractionResult(
        status=STATUS_METADATA_ONLY,
        pages=[],
        page_count=page_count,
        total_chars=total_chars,
        warning=METADATA_ONLY_WARNING,
    )


def extract_plain_text(path: str | Path, *, encoding: str = "utf-8") -> ExtractionResult:
    """Read a .txt / .md style file into a single-page extraction result."""
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return ExtractionResult(status=STATUS_ERROR, warning="找不到檔案或檔案無法讀取。")
    try:
        raw = file_path.read_text(encoding=encoding, errors="ignore")
    except OSError:
        return ExtractionResult(status=STATUS_ERROR, warning="無法讀取文字檔案。")
    text = _strip_secrets(raw).strip()
    if len(text) < _MIN_TEXT_CHARS:
        return ExtractionResult(
            status=STATUS_METADATA_ONLY,
            page_count=1,
            total_chars=len(text),
            warning=METADATA_ONLY_WARNING,
        )
    return ExtractionResult(
        status=STATUS_SELECTABLE,
        pages=[PageText(page_number=1, text=text)],
        page_count=1,
        total_chars=len(text),
    )


def result_from_text(text: str) -> ExtractionResult:
    """Wrap already-extracted text (e.g. DOCX) in an ExtractionResult."""
    clean = _strip_secrets(text or "").strip()
    if len(clean) < _MIN_TEXT_CHARS:
        return ExtractionResult(
            status=STATUS_METADATA_ONLY,
            page_count=1 if clean else 0,
            total_chars=len(clean),
            warning=METADATA_ONLY_WARNING,
        )
    return ExtractionResult(
        status=STATUS_SELECTABLE,
        pages=[PageText(page_number=1, text=clean)],
        page_count=1,
        total_chars=len(clean),
    )
