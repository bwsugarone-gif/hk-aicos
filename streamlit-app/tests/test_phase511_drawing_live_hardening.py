"""Focused tests for Phase 5.11 — Drawing Analysis Live Hardening.

Covers: real PDF/image ingestion safety, title-block EN/ZH labels, classifier vs.
hot-work safety text, task-oriented CAD/BIM handoff wording, Records search
filters, Ask AICOS drawing context (with and without analysis), page compilation
and no-secret / no-raw-output exposure in normal UI strings.
"""

from __future__ import annotations

import py_compile
from pathlib import Path

import pytest

from utils.drawing_analyzer import analyze_drawing
from utils.drawing_classifier import classify_drawing_page
from utils.drawing_handoff import extract_page_findings, generate_handoff_items
from utils.drawing_ingest import ingest_drawing
from utils.drawing_models import (
    CAD_BIM_ACTION_TYPES,
    DrawingDocument,
    DrawingPageAnalysis,
)
from utils.drawing_records import filter_drawing_documents, filter_handoff_rows
from utils.drawing_store import append_drawing_document, get_drawing_document, update_handoff_item_status
from utils.drawing_title_block import extract_title_block


APP_ROOT = Path(__file__).resolve().parents[1]
_VERIFY_ACTIONS = {"verify_dimension", "verify_level", "verify_opening", "verify_mep_coordination", "site_verify"}


def _make_pdf(path: Path, pages_text: list[str | None], *, title: str | None = None, author: str | None = None) -> Path:
    pytest.importorskip("reportlab")
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path))
    if title:
        c.setTitle(title)
    if author:
        c.setAuthor(author)
    for text in pages_text:
        if text:
            for index, line in enumerate(text.split("\n")):
                c.drawString(72, 720 - index * 18, line)
        c.showPage()
    c.save()
    return path


# ── 1. PDF ingestion: multi-page + metadata, safely ────────────────────────
def test_pdf_ingestion_multipage_and_metadata(tmp_path):
    pdf = _make_pdf(
        tmp_path / "set.pdf",
        ["DRAWING NO: A-101 Scale 1:100 Rev B\nSheet Title: GROUND FLOOR PLAN",
         "DRAWING NO: FS-03 Fire Services sprinkler layout"],
        title="GF Plan Set", author="Buildway",
    )
    result = ingest_drawing(pdf, max_pages=12)
    assert result["file_type"] == "pdf"
    assert result["page_count"] == 2
    assert result["ingestion_status"] in {"selectable_text", "ocr"}
    assert "pages_without_text" in result
    assert result["metadata"].get("title") == "GF Plan Set"
    assert "A-101" in result["pages"][0]["text"]


def test_pdf_scanned_no_text_does_not_crash(tmp_path, monkeypatch):
    import utils.drawing_ingest as di

    # Simulate no OCR backend so an image-only / scanned PDF degrades gracefully.
    monkeypatch.setattr(di, "extract_text_with_ocr", lambda *a, **k: {"ocr_status": "OCR_UNAVAILABLE", "extracted_text": ""})
    pdf = _make_pdf(tmp_path / "scan.pdf", [None, None])
    result = ingest_drawing(pdf, max_pages=12)
    assert result["page_count"] == 2
    assert result["pages_without_text"] == 2
    assert result["ingestion_status"] in {"metadata_only", "ocr"}
    assert all(page["placeholder"] for page in result["pages"])
    assert all(page["summary"] for page in result["pages"])  # placeholder summary present


# ── 2. Image drawing ingestion -> single page ──────────────────────────────
def test_image_ingestion_single_page(tmp_path, monkeypatch):
    pytest.importorskip("PIL")
    from PIL import Image

    img_path = tmp_path / "dwg.png"
    Image.new("RGB", (64, 48), "white").save(img_path)
    import utils.drawing_ingest as di

    monkeypatch.setattr(di, "ocr_image", lambda *a, **k: {"extracted_text": "FLOOR PLAN A-101", "ocr_status": "OCR_OK"})
    result = ingest_drawing(img_path)
    assert result["file_type"] == "image"
    assert result["page_count"] == 1
    assert len(result["pages"]) == 1
    assert result["pages"][0]["page_number"] == 1


# ── 3. Title block: English + Chinese labels ───────────────────────────────
def test_title_block_english_and_chinese_labels():
    fields = extract_title_block(
        "Dwg No: A-12  Drawing Title: GROUND FLOOR PLAN  Rev: C  Scale 1:50\n"
        "圖名：地下層平面圖  比例：1:50  修訂：C  樓層：1/F"
    )["fields"]
    assert fields["drawing_number"] == "A-12"
    assert fields["scale"] == "1:50"
    assert fields["revision"] == "C"
    assert "GROUND FLOOR PLAN" in (fields.get("sheet_title") or "")
    assert fields.get("level_hint")  # 1/F detected


def test_title_block_does_not_capture_note_paragraph_as_title():
    fields = extract_title_block(
        "Title: refer to general notes and structural drawings for all setting out dimensions before construction"
    )["fields"]
    # A long note paragraph must not be stored as a title.
    assert not fields.get("sheet_title")


# ── 4. Classifier separates hot-work safety text from drawing page types ───
def test_classifier_separates_hotwork_from_drawing_types():
    hot = classify_drawing_page("熱工序 動火 火花 焊接 切割 防火監察 hot work permit fire watch")
    assert hot["page_type"] == "unknown"
    assert hot["discipline"] == "unknown"
    plan = classify_drawing_page("GROUND FLOOR PLAN general arrangement", sheet_number="A-101")
    assert plan["page_type"] == "floor_plan"
    assert plan["discipline"] == "architecture"


# ── 5. CAD/BIM handoff wording is task-oriented ────────────────────────────
def test_handoff_items_are_task_oriented():
    page = {
        "page_number": 2, "page_type": "floor_plan", "discipline": "mep",
        "title_block_fields": {"drawing_number": "M-201", "sheet_number": "M-201"},
        "text": "ductwork and pipe penetration opening layout",
    }
    items = generate_handoff_items(page, extract_page_findings(page))
    assert items
    assert all(item.action_type in CAD_BIM_ACTION_TYPES for item in items)
    # responsible team on every item
    assert all(item.target_team in {"cad", "bim", "both"} for item in items)
    # required output on every item
    assert all(item.required_output for item in items)
    # who verifies on every item
    assert all(item.verify_by for item in items)
    # at least one verification-type action
    assert any(item.action_type in _VERIFY_ACTIONS for item in items)
    # page / sheet reference present
    assert all(item.page_number == 2 for item in items)
    assert any(item.sheet_number == "M-201" for item in items)


def test_handoff_does_not_claim_dimension_check_without_notes():
    page = {"page_number": 1, "page_type": "floor_plan", "discipline": "architecture",
            "title_block_fields": {"drawing_number": "A-1", "revision": "A", "scale": "1:100"},
            "text": "general arrangement floor plan"}
    items = generate_handoff_items(page, extract_page_findings(page))
    # No dimension notes -> a site-verify is handed off, not a dimension claim.
    assert any(item.action_type == "site_verify" for item in items)
    assert not any(item.action_type == "verify_dimension" for item in items)


# ── 6. Records drawing search filters ──────────────────────────────────────
def test_records_drawing_filters():
    doc1 = DrawingDocument.from_dict({
        "document_id": "d1", "created_at": "2026-06-01", "updated_at": "2026-06-01",
        "project_ref": "BW-1", "source_file_name": "arch.pdf", "summary": "floor plan",
        "disciplines": ["architecture"], "page_types": ["floor_plan"],
        "handoff_items": [{"action_type": "site_verify", "target_team": "both", "title": "現場核實",
                          "priority": "low", "discipline": "architecture", "sheet_number": "A-101", "required_output": "x"}],
    })
    doc2 = DrawingDocument.from_dict({
        "document_id": "d2", "created_at": "2026-06-02", "updated_at": "2026-06-02",
        "project_ref": "BW-1", "source_file_name": "fire.pdf", "summary": "sprinkler layout",
        "disciplines": ["fire_services"], "page_types": ["floor_plan"],
        "handoff_items": [{"action_type": "check_fire_protection", "target_team": "cad", "title": "消防保護",
                          "priority": "high", "discipline": "fire_services", "sheet_number": "FS-03", "required_output": "y"}],
    })
    page1 = DrawingPageAnalysis(page_id="d1_p001", document_id="d1", page_number=1, sheet_number="A-101", drawing_number="A-101")
    page2 = DrawingPageAnalysis(page_id="d2_p001", document_id="d2", page_number=1, sheet_number="FS-03", drawing_number="FS-03")
    docs = [doc2, doc1]
    pages_by_doc = {"d1": [page1], "d2": [page2]}

    assert [d.document_id for d in filter_drawing_documents(docs, pages_by_doc, discipline="architecture")] == ["d1"]
    assert [d.document_id for d in filter_drawing_documents(docs, pages_by_doc, sheet_number="FS-03")] == ["d2"]
    assert [d.document_id for d in filter_drawing_documents(docs, pages_by_doc, keyword="sprinkler")] == ["d2"]

    rows = [(d, item) for d in docs for item in d.handoff_items]
    high = filter_handoff_rows(rows, priority="high")
    assert len(high) == 1 and high[0][1].discipline == "fire_services"
    assert len(filter_handoff_rows(rows, discipline="fire_services")) == 1
    by_sheet = filter_handoff_rows(rows, keyword="A-101")
    assert len(by_sheet) == 1 and by_sheet[0][1].sheet_number == "A-101"


def test_handoff_status_update_round_trip(tmp_path):
    doc_path = tmp_path / "drawing_analysis.jsonl"
    doc = DrawingDocument.from_dict({
        "document_id": "draw_status", "created_at": "2026-06-01", "updated_at": "2026-06-01",
        "handoff_items": [{"item_id": "h1", "action_type": "issue_rfi", "target_team": "cad", "title": "RFI", "status": "open"}],
    })
    append_drawing_document(doc, path=doc_path)
    update_handoff_item_status("draw_status", "h1", "done", path=doc_path)
    refreshed = get_drawing_document("draw_status", path=doc_path)
    assert refreshed is not None
    assert refreshed.handoff_items[0].status == "done"
    # Unknown status is ignored, not stored.
    update_handoff_item_status("draw_status", "h1", "not_a_status", path=doc_path)
    assert get_drawing_document("draw_status", path=doc_path).handoff_items[0].status == "done"


# ── 7-8. Ask AICOS drawing context ─────────────────────────────────────────
def _silence_bridge(monkeypatch):
    from utils import ask_context_bridge as bridge

    for name in ("search_local_knowledge", "build_knowledge_pack_context", "build_knowledge_context", "build_rag_context"):
        monkeypatch.setattr(bridge, name, lambda *a, **k: [])
    monkeypatch.setattr(bridge, "build_followup_context", lambda *a, **k: [])
    monkeypatch.setattr(bridge, "build_project_memory_context", lambda *a, **k: [])
    monkeypatch.setattr(bridge, "_latest_upload_memory", lambda *a, **k: None)
    return bridge


def test_ask_context_uses_recent_drawing(monkeypatch):
    bridge = _silence_bridge(monkeypatch)
    from utils import drawing_context as dc

    doc = DrawingDocument.from_dict({
        "document_id": "d9", "created_at": "2026-06-01", "updated_at": "2026-06-01",
        "project_ref": "BW-1", "source_file_name": "plan.pdf", "summary": "地下層平面圖",
        "disciplines": ["architecture"], "page_types": ["floor_plan"], "analyzed_page_count": 3,
        "handoff_items": [{"action_type": "verify_dimension", "target_team": "bim", "title": "核對尺寸",
                          "priority": "medium", "page_number": 1, "required_output": "已核對尺寸記錄"}],
    })
    monkeypatch.setattr(dc, "list_recent_drawing_documents", lambda *a, **k: [doc])

    selection = bridge.build_ask_context_selection("CAD team 要做咩？", search_scope="all", project_ref="BW-1")
    assert "cad_bim_handoff" in {s.source_type for s in selection.contexts}
    basis = "\n".join(selection.context_basis)
    assert "問題類型：圖紙 / CAD-BIM 查詢" in basis
    assert "最近圖紙分析：已引用" in basis
    assert "CAD/BIM 交接事項：1 項" in basis
    assert "圖紙頁面：3 頁" in basis


def test_ask_context_no_drawing_returns_guidance(monkeypatch):
    bridge = _silence_bridge(monkeypatch)
    from utils import drawing_context as dc

    monkeypatch.setattr(dc, "list_recent_drawing_documents", lambda *a, **k: [])
    selection = bridge.build_ask_context_selection("呢份圖紙有咩問題？", search_scope="all")
    guidance = [s for s in selection.contexts if s.source_type == "drawing_guidance"]
    assert guidance and "上載" in guidance[0].snippet
    assert "最近圖紙分析：未找到" in "\n".join(selection.context_basis)


# ── 9. Drawing-related pages compile ───────────────────────────────────────
def test_drawing_pages_compile():
    for rel in ("app.py", "pages/12_Drawing_Analysis.py", "pages/11_Records.py", "pages/10_Ask_AICOS.py"):
        py_compile.compile(str(APP_ROOT / rel), doraise=True)


# ── 10. Normal UI strings expose no secrets / raw output ───────────────────
def test_no_secret_or_raw_exposure_in_drawing_outputs(tmp_path):
    pdf = _make_pdf(
        tmp_path / "x.pdf",
        ["DRAWING NO: A-101 Scale 1:100 Rev B\nSheet Title: GROUND FLOOR PLAN",
         "DRAWING NO: FS-03 Fire Services sprinkler layout"],
        title="t", author="a",
    )
    result = analyze_drawing(pdf, file_name="x.pdf", depth="standard", use_vision=False, persist=False)
    document = result.document
    user_strings = [document.summary, *document.drawing_issues, *document.missing_information, *document.coordination_flags]
    for item in document.handoff_items:
        user_strings += [item.title, item.description, item.required_output, item.evidence, item.verify_by]
    for page in result.pages:
        user_strings += [page.sheet_title or "", *page.drawing_issues, *page.missing_information]
    blob = "\n".join(user_strings)
    low = blob.lower()
    for forbidden in ("gemini", "deepseek", "tavily", "anthropic", "api key", "api_key", "traceback", "sk-", "c:\\", "/users/", "/home/"):
        assert forbidden not in low, forbidden
    assert '{"' not in blob  # not raw JSON

    for rel in ("pages/12_Drawing_Analysis.py", "pages/11_Records.py"):
        source = (APP_ROOT / rel).read_text(encoding="utf-8")
        for token in ("Gemini", "DeepSeek", "Tavily", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "Traceback"):
            assert token not in source, (rel, token)
