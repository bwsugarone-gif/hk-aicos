"""Focused tests for Phase 5.10 drawing analysis + CAD/BIM handoff."""

from pathlib import Path

import pytest

from utils.drawing_classifier import classify_drawing_page
from utils.drawing_handoff import extract_page_findings, generate_handoff_items
from utils.drawing_ingest import ingest_drawing
from utils.drawing_models import (
    CAD_BIM_ACTION_TYPES,
    CadBimHandoffItem,
    DrawingDocument,
    DrawingPageAnalysis,
)
from utils.drawing_title_block import extract_title_block


def _make_pdf(path: Path) -> Path:
    reportlab = pytest.importorskip("reportlab")
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path))
    c.drawString(72, 720, "DRAWING NO: A-101  Scale 1:100  Rev B  Date: 2026-05-12")
    c.drawString(72, 700, "Sheet Title: GROUND FLOOR PLAN")
    c.showPage()
    c.drawString(72, 720, "DRAWING NO: FS-03  Fire Services sprinkler and hydrant layout")
    c.showPage()
    c.save()
    return path


# ── 5.10A models / store ───────────────────────────────────────────────────
def test_models_defensive_from_dict():
    doc = DrawingDocument.from_dict({"document_id": "", "page_count": "3",
                                     "handoff_items": [{"action_type": "verify_dimension", "target_team": "cad", "title": "t"}]})
    assert doc.analysis_depth == "standard"
    assert doc.page_count == 3
    assert doc.handoff_items[0].action_type == "verify_dimension"
    # round trips
    assert DrawingDocument.from_dict(doc.to_dict()).document_id == doc.document_id
    page = DrawingPageAnalysis.from_dict({"page_id": "p", "document_id": "d", "page_number": "2"})
    assert page.page_number == 2
    assert page.page_type == "unknown"


def test_store_round_trip(tmp_path):
    from utils import drawing_store as ds

    doc_path = tmp_path / "drawing_analysis.jsonl"
    page_path = tmp_path / "drawing_pages.jsonl"
    doc = DrawingDocument.from_dict({
        "document_id": "draw_test", "created_at": "", "updated_at": "",
        "project_ref": "BW-1", "source_file_name": "x.pdf",
        "handoff_items": [{"action_type": "issue_rfi", "target_team": "cad", "title": "RFI", "priority": "high"}],
    })
    saved = ds.append_drawing_document(doc, path=doc_path)
    ds.append_drawing_pages([DrawingPageAnalysis(page_id="draw_test_p001", document_id=saved.document_id, page_number=1)], path=page_path)
    got = ds.get_drawing_document(saved.document_id, path=doc_path)
    assert got is not None and len(got.handoff_items) == 1
    pages = ds.read_pages_for_document(saved.document_id, path=page_path)
    assert len(pages) == 1
    recent = ds.list_recent_drawing_documents("BW-1", path=doc_path)
    assert recent and recent[0].document_id == saved.document_id


def test_store_handles_corrupt_lines(tmp_path):
    from utils import drawing_store as ds

    doc_path = tmp_path / "drawing_analysis.jsonl"
    doc_path.write_text('{not json}\n\n{"document_id": "ok", "created_at": "2026-01-01"}\n', encoding="utf-8")
    docs = ds.read_all_drawing_documents(path=doc_path)
    assert len(docs) == 1 and docs[0].document_id == "ok"


# ── 5.10B ingestion ────────────────────────────────────────────────────────
def test_ingest_pdf(tmp_path):
    pdf = _make_pdf(tmp_path / "dwg.pdf")
    result = ingest_drawing(pdf, max_pages=12)
    assert result["file_type"] == "pdf"
    assert result["page_count"] == 2
    assert result["ingestion_status"] in {"selectable_text", "ocr"}
    assert "A-101" in result["pages"][0]["text"]


def test_ingest_missing_and_unsupported(tmp_path):
    assert ingest_drawing(tmp_path / "nope.pdf")["ingestion_status"] == "unsupported"
    bad = tmp_path / "x.docx"
    bad.write_text("hi", encoding="utf-8")
    assert ingest_drawing(bad)["ingestion_status"] == "unsupported"


# ── 5.10C title block ──────────────────────────────────────────────────────
def test_title_block_english():
    fields = extract_title_block(
        "DRAWING NO: A-101 Rev: B Scale 1:100 Date: 2026-05-12\nProject No: BW-2026-007",
        filename="A-101.pdf",
    )["fields"]
    assert fields["drawing_number"] == "A-101"
    assert fields["scale"] == "1:100"
    assert fields["revision"] == "B"
    assert fields["project_number"] == "BW-2026-007"


def test_title_block_chinese():
    fields = extract_title_block("圖則編號：S-201 比例：1:50 修訂：A")["fields"]
    assert fields["drawing_number"] == "S-201"
    assert fields["scale"] == "1:50"


# ── 5.10D classification ───────────────────────────────────────────────────
def test_classify_floor_plan_architecture():
    out = classify_drawing_page("GROUND FLOOR PLAN general arrangement", sheet_number="A-101")
    assert out["page_type"] == "floor_plan"
    assert out["discipline"] == "architecture"


def test_classify_fire_services_and_chinese():
    assert classify_drawing_page("Fire Services sprinkler layout", sheet_number="FS-03")["discipline"] == "fire_services"
    zh = classify_drawing_page("結構梁柱大樣詳圖", sheet_number="S-201")
    assert zh["page_type"] == "detail" and zh["discipline"] == "structural"


def test_classify_discipline_hint_overrides():
    out = classify_drawing_page("some text", discipline_hint="drainage")
    assert out["discipline"] == "drainage"


# ── 5.10E findings + handoff ───────────────────────────────────────────────
def test_findings_and_handoff_generation():
    page = {
        "page_number": 1, "page_type": "floor_plan", "discipline": "mep",
        "title_block_fields": {"drawing_number": "M-101"}, "text": "ductwork layout TBC",
    }
    findings = extract_page_findings(page)
    assert findings["coordination_flags"]  # mep coordination prompt
    assert any("待確認" in i or "TBC" in i for i in findings["drawing_issues"])
    items = generate_handoff_items(page, findings)
    assert items and all(isinstance(i, CadBimHandoffItem) for i in items)
    assert all(i.action_type in CAD_BIM_ACTION_TYPES for i in items)
    assert any(i.action_type == "verify_mep_coordination" for i in items)


# ── 5.10B-E analyzer end-to-end ────────────────────────────────────────────
def test_analyze_drawing_pipeline(tmp_path):
    from utils.drawing_analyzer import analyze_drawing

    pdf = _make_pdf(tmp_path / "dwg.pdf")
    res = analyze_drawing(pdf, project_ref="BW-1", file_name="dwg.pdf",
                          depth="standard", use_vision=False, persist=False)
    assert res.document.analyzed_page_count == 2
    assert "architecture" in res.document.disciplines
    assert res.document.handoff_items
    assert res.pages[0].drawing_number == "A-101"


# ── 5.10G memory + follow-up integration ───────────────────────────────────
def test_memory_source_type_registered():
    from utils.memory_models import MEMORY_SOURCE_TYPES

    assert "drawing_analysis" in MEMORY_SOURCE_TYPES


def test_register_drawing_memory_and_followups():
    from utils.drawing_integration import register_drawing_memory, create_followups_for_handoff

    doc = DrawingDocument.from_dict({
        "document_id": "d1", "created_at": "", "updated_at": "", "project_ref": "BW-1",
        "source_file_name": "a.pdf", "summary": "s", "disciplines": ["fire_services"],
        "drawing_issues": ["issue"], "missing_information": ["缺比例"],
        "handoff_items": [
            {"action_type": "check_fire_protection", "target_team": "cad", "title": "消防", "priority": "high"},
            {"action_type": "site_verify", "target_team": "both", "title": "核實", "priority": "low"},
        ],
    })
    mem = register_drawing_memory(doc, persist=False)
    assert mem.source_type == "drawing_analysis"
    assert mem.priority == "high"
    follows = create_followups_for_handoff(doc, persist=False)
    assert len(follows) == 1  # only the high-priority item


# ── 5.10H Ask AICOS drawing context ────────────────────────────────────────
def test_drawing_intent_classification():
    from utils.ask_intent_router import classify_ask_intent

    assert classify_ask_intent("呢份圖紙有咩問題？").intent_type == "drawing_question"
    assert classify_ask_intent("CAD team 要做咩？").intent_type == "cad_bim_handoff_question"
    assert classify_ask_intent("這份圖紙有冇缺資料？").intent_type == "drawing_question"
    # generic safety must not be hijacked
    assert classify_ask_intent("高空工作幾高要防墮？").intent_type == "general_safety_question"


def test_build_drawing_context(monkeypatch):
    from utils import drawing_context as dc

    doc = DrawingDocument.from_dict({
        "document_id": "d9", "created_at": "2026-06-01", "updated_at": "2026-06-01",
        "project_ref": "BW-1", "source_file_name": "plan.pdf", "summary": "地下層平面圖",
        "disciplines": ["architecture"], "page_types": ["floor_plan"],
        "drawing_issues": ["缺修訂"], "missing_information": ["缺比例"],
        "handoff_items": [{"action_type": "verify_dimension", "target_team": "bim", "title": "核對尺寸", "priority": "medium", "page_number": 1}],
    })
    monkeypatch.setattr(dc, "list_recent_drawing_documents", lambda *a, **k: [doc])
    snippets = dc.build_drawing_context("呢份圖紙有咩問題", "BW-1", intent_type="drawing_question")
    types = {s.source_type for s in snippets}
    assert "drawing_analysis" in types and "cad_bim_handoff" in types
    # handoff-first ordering for cad/bim intent
    handoff_first = dc.build_drawing_context("CAD team 要做咩", "BW-1", intent_type="cad_bim_handoff_question")
    assert handoff_first[0].source_type == "cad_bim_handoff"
