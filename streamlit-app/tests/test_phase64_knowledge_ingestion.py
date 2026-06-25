"""Phase 6.4 — PDF extraction + knowledge / RAG ingestion tests."""

from __future__ import annotations

import json

import pytest

from utils.knowledge_ingestion import (
    ingest_document,
    ingest_text,
    read_ingested_knowledge_sources,
)
from utils.pdf_text_extractor import (
    METADATA_ONLY_WARNING,
    STATUS_METADATA_ONLY,
    STATUS_SELECTABLE,
    extract_pdf_pages,
)
from utils.rag_persistence import read_ingested_chunks


def _make_text_pdf(path):
    reportlab = pytest.importorskip("reportlab")
    from reportlab.pdfgen import canvas  # noqa: WPS433

    pdf = canvas.Canvas(str(path))
    pdf.drawString(72, 720, "Hot work permit required before grinding or cutting.")
    pdf.drawString(72, 700, "Working at height above two metres needs fall protection.")
    pdf.showPage()
    pdf.drawString(72, 720, "Page two: fire watch monitoring is required after hot work.")
    pdf.showPage()
    pdf.save()
    return path


def _make_blank_pdf(path):
    pypdf = pytest.importorskip("pypdf")
    from pypdf import PdfWriter  # noqa: WPS433

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with open(path, "wb") as handle:
        writer.write(handle)
    return path


def test_pdf_extractor_reads_selectable_text(tmp_path):
    pdf_path = _make_text_pdf(tmp_path / "permit.pdf")
    result = extract_pdf_pages(pdf_path)
    assert result.status == STATUS_SELECTABLE
    assert result.has_text
    assert result.page_count == 2
    assert any("hot work permit" in page.text.lower() for page in result.pages)


def test_scanned_pdf_degrades_to_metadata_only(tmp_path):
    pdf_path = _make_blank_pdf(tmp_path / "scan.pdf")
    result = extract_pdf_pages(pdf_path)
    assert result.status == STATUS_METADATA_ONLY
    assert not result.has_text
    assert result.warning == METADATA_ONLY_WARNING


def test_missing_pdf_does_not_crash(tmp_path):
    result = extract_pdf_pages(tmp_path / "nope.pdf")
    assert result.status == "error"
    assert not result.has_text


def test_ingest_text_creates_source_and_chunks(tmp_path):
    kpath = tmp_path / "ingested_knowledge.jsonl"
    rpath = tmp_path / "ingested_rag.jsonl"
    result = ingest_text(
        text="Hot work permit required. Working at height needs fall protection. " * 6,
        title="safety doc",
        original_file_name="safety.pdf",
        project_ref="BW-001",
        tags=["safety"],
        knowledge_path=kpath,
        rag_path=rpath,
    )
    assert result.status == STATUS_SELECTABLE
    assert result.chunk_count >= 1
    assert not result.metadata_only

    sources = read_ingested_knowledge_sources(path=kpath)
    assert sources and sources[0].source_id == result.source_id

    chunks = read_ingested_chunks(path=rpath)
    assert chunks
    assert all(chunk.source_file_name == "safety.pdf" for chunk in chunks)
    assert all(chunk.page_number == 1 for chunk in chunks)


def test_ingest_pdf_preserves_page_number_and_file_name(tmp_path):
    pdf_path = _make_text_pdf(tmp_path / "permit.pdf")
    kpath = tmp_path / "ingested_knowledge.jsonl"
    rpath = tmp_path / "ingested_rag.jsonl"
    regpath = tmp_path / "file_registry.jsonl"
    result = ingest_document(
        file_path=pdf_path,
        original_file_name="permit.pdf",
        project_ref="BW-001",
        knowledge_path=kpath,
        rag_path=rpath,
        registry_path=regpath,
    )
    assert not result.metadata_only
    assert result.pages_extracted >= 1

    chunks = read_ingested_chunks(path=rpath)
    assert chunks
    assert all(chunk.source_file_name == "permit.pdf" for chunk in chunks)
    assert any(chunk.page_number for chunk in chunks)

    # A file-registry row was created and links to the knowledge source.
    from utils.file_registry import list_file_records

    files = list_file_records(path=regpath)
    assert files and files[0].linked_knowledge_source_id == result.source_id


def test_scanned_pdf_ingest_is_metadata_only(tmp_path):
    pdf_path = _make_blank_pdf(tmp_path / "scan.pdf")
    kpath = tmp_path / "ingested_knowledge.jsonl"
    rpath = tmp_path / "ingested_rag.jsonl"
    result = ingest_document(
        file_path=pdf_path,
        original_file_name="scan.pdf",
        knowledge_path=kpath,
        rag_path=rpath,
        register_in_file_registry=False,
    )
    assert result.metadata_only
    assert result.chunk_count == 0
    assert any("metadata-only" in warning for warning in result.warnings)


def test_public_dicts_expose_no_local_path(tmp_path):
    result = ingest_text(
        text="Hot work permit content. " * 10,
        title="doc",
        original_file_name="doc.pdf",
        knowledge_path=tmp_path / "k.jsonl",
        rag_path=tmp_path / "r.jsonl",
    )
    public = result.to_public_dict()
    blob = json.dumps(public, ensure_ascii=False)
    assert "local_runtime_path" not in blob
    assert "/" not in str(public.get("source_id", ""))
