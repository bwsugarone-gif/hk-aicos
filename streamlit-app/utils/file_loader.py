"""
file_loader.py
HK-AICOS Phase 2.0 - File Loading Utilities

Handles uploaded files (images, PDFs) and extracts content for analysis.
"""

import os
import uuid
from datetime import datetime
from pathlib import Path

from PIL import Image
import pypdf

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
MAX_FILE_SIZE_MB = 20


def save_uploaded_file(uploaded_file) -> Path:
    """Save a Streamlit uploaded file to the uploads directory. Returns the saved path."""
    ext = Path(uploaded_file.name).suffix.lower()
    unique_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
    save_path = UPLOAD_DIR / unique_name
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return save_path


def is_allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def extract_pdf_text(file_path: Path) -> str:
    """Extract text content from a PDF file."""
    try:
        reader = pypdf.PdfReader(str(file_path))
        text_parts = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(f"[Page {i + 1}]\n{page_text.strip()}")
        return "\n\n".join(text_parts) if text_parts else "[PDF contains no extractable text - may be scanned image]"
    except Exception as e:
        return f"[Error reading PDF: {str(e)}]"


def get_image_description(file_path: Path) -> str:
    """Get basic image metadata as description."""
    try:
        with Image.open(file_path) as img:
            width, height = img.size
            mode = img.mode
            fmt = img.format or Path(file_path).suffix.upper().lstrip(".")
            return f"Image file: {fmt}, {width}x{height}px, mode={mode}"
    except Exception as e:
        return f"[Error reading image: {str(e)}]"


def load_file_content(file_path: Path) -> dict:
    """
    Load file and return a dict with type, description, and raw content.
    Returns:
        {
            "type": "image" | "pdf",
            "filename": str,
            "description": str,   # short description for prompt
            "content": str,        # extracted text (PDF) or metadata (image)
            "path": Path,
        }
    """
    ext = file_path.suffix.lower()
    filename = file_path.name

    if ext in {".jpg", ".jpeg", ".png"}:
        description = get_image_description(file_path)
        return {
            "type": "image",
            "filename": filename,
            "description": description,
            "content": description,
            "path": file_path,
        }
    elif ext == ".pdf":
        text = extract_pdf_text(file_path)
        # Truncate very long PDFs to avoid token overflow
        if len(text) > 8000:
            text = text[:8000] + "\n\n[... content truncated for analysis ...]"
        description = f"PDF document ({len(text)} chars extracted)"
        return {
            "type": "pdf",
            "filename": filename,
            "description": description,
            "content": text,
            "path": file_path,
        }
    else:
        return {
            "type": "unknown",
            "filename": filename,
            "description": "Unsupported file type",
            "content": "",
            "path": file_path,
        }


def process_uploaded_file(uploaded_file) -> dict:
    """
    Full pipeline: save uploaded file then load its content.
    Returns content dict (see load_file_content).
    """
    saved_path = save_uploaded_file(uploaded_file)
    return load_file_content(saved_path)
