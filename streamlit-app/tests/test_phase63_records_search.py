"""Phase 6.3 — unified records search / filter tests."""

from __future__ import annotations

from utils.drawing_models import CadBimHandoffItem, DrawingDocument, DrawingPageAnalysis
from utils.file_storage_models import StoredFileRecord
from utils.followup_models import FollowUpItem
from utils.knowledge_models import KnowledgeSource
from utils.memory_models import ProjectMemoryRecord
from utils.rag_models import RagChunk
from utils.records_filters import (
    filter_drawing_pages,
    filter_file_records,
    filter_handoff_items,
    filter_records_by_keyword,
    filter_records_by_project,
)
from utils.records_search import build_unified_record_index, search_unified_records


def _sample_index():
    document = DrawingDocument.from_dict(
        {
            "document_id": "draw_1",
            "created_at": "2026-06-01T00:00:00",
            "updated_at": "2026-06-01T00:00:00",
            "project_ref": "BW-001",
            "source_file_name": "A-101.pdf",
            "disciplines": ["architecture"],
            "summary": "地下層建築平面圖",
            "handoff_items": [
                {
                    "item_id": "h1",
                    "action_type": "verify_dimension",
                    "target_team": "cad",
                    "title": "核對地下層尺寸",
                    "priority": "high",
                    "status": "open",
                    "discipline": "architecture",
                    "sheet_number": "A-101",
                }
            ],
        }
    )
    page = DrawingPageAnalysis.from_dict(
        {
            "page_id": "draw_1_p001",
            "document_id": "draw_1",
            "page_number": 1,
            "sheet_number": "A-101",
            "page_type": "floor_plan",
            "discipline": "architecture",
            "sheet_title": "GROUND FLOOR PLAN",
        }
    )
    ksrc = KnowledgeSource.from_dict(
        {
            "source_id": "uksrc_1",
            "title": "hot work permit",
            "source_type": "uploaded_document",
            "summary": "熱工許可文件",
            "last_indexed_at": "2026-06-02T00:00:00",
        }
    )
    chunk = RagChunk.from_dict(
        {
            "chunk_id": "c1",
            "source_id": "uksrc_1",
            "title": "hot work permit",
            "text": "進行熱工序前必須申請熱工許可證並設置防火監察。",
            "page_number": 2,
            "source_file_name": "hot_work.pdf",
            "project_ref": "BW-001",
            "created_at": "2026-06-02T00:00:00",
        }
    )
    file_rec = StoredFileRecord.from_dict(
        {
            "file_id": "file_1",
            "original_file_name": "hot_work.pdf",
            "file_type": "knowledge_pdf",
            "project_ref": "BW-001",
        }
    )
    mem = ProjectMemoryRecord.from_dict(
        {"memory_id": "pmem_1", "title": "地盤巡查記憶", "summary": "棚架護欄", "project_ref": "BW-001"}
    )
    fu = FollowUpItem.from_dict(
        {"followup_id": "fu_1", "title": "補交整改相片", "description": "高空工作護欄", "project_ref": "BW-001"}
    )
    return build_unified_record_index(
        memories=[mem],
        followups=[fu],
        knowledge_sources=[ksrc],
        rag_chunks=[chunk],
        drawing_documents=[document],
        drawing_pages_by_doc={"draw_1": [page]},
        file_records=[file_rec],
        load_defaults=False,
    )


def test_index_covers_all_eight_record_types():
    index = _sample_index()
    types = {record.record_type for record in index}
    assert types == {
        "project_memory",
        "follow_up",
        "knowledge_source",
        "rag_chunk",
        "drawing_document",
        "drawing_page",
        "cad_bim_handoff",
        "file_record",
    }


def test_search_finds_drawing_page_by_sheet_number():
    index = _sample_index()
    results = search_unified_records(index, sheet_number="A-101")
    assert any(r.record_type == "drawing_page" for r in results)


def test_search_finds_handoff_by_team_status_priority():
    index = _sample_index()
    results = search_unified_records(
        index, record_type="cad_bim_handoff", responsible_team="cad", status="open", priority="high"
    )
    assert len(results) == 1 and results[0].record_id == "h1"


def test_search_finds_knowledge_source_by_file_name():
    index = _sample_index()
    results = search_unified_records(index, keyword="hot work")
    assert any(r.record_type == "knowledge_source" for r in results)


def test_search_finds_rag_chunk_by_keyword():
    index = _sample_index()
    results = search_unified_records(index, keyword="防火監察")
    assert any(r.record_type == "rag_chunk" for r in results)


def test_search_by_project_scopes_results():
    index = _sample_index()
    results = search_unified_records(index, project_ref="BW-001")
    assert results and all(
        (r.project_ref in (None, "BW-001")) for r in results
    )
    # An unknown project yields nothing that is explicitly tagged to BW-001.
    assert search_unified_records(index, project_ref="ZZ-999") == [] or all(
        r.project_ref != "BW-001" for r in search_unified_records(index, project_ref="ZZ-999")
    )


def test_filters_do_not_crash_on_missing_fields():
    # Dicts missing nearly every field must not raise.
    assert filter_drawing_pages([{}], sheet_number="X", keyword="y") == []
    assert filter_handoff_items([{}], team="cad", keyword="y") == []
    assert filter_file_records([{}], project_ref="X", keyword="y") == []
    assert filter_records_by_project([{}], "X") == []
    assert filter_records_by_keyword([{}], "y") == []
    # Building an index from dicts with missing fields also must not raise.
    build_unified_record_index(memories=[{}], file_records=[{}], load_defaults=False)


def test_filter_handoff_items_matches_native_objects():
    item = CadBimHandoffItem.from_dict(
        {"item_id": "h2", "action_type": "issue_rfi", "target_team": "bim", "title": "RFI", "status": "open", "priority": "urgent"}
    )
    assert filter_handoff_items([item], team="bim", priority="urgent") == [item]
    assert filter_handoff_items([item], team="cad") == []
