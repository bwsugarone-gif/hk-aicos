"""Phase 6.1 — file registry / storage foundation tests."""

from __future__ import annotations

import json
from pathlib import Path

from utils.drawing_integration import register_drawing_source_file
from utils.drawing_models import DrawingDocument
from utils.file_registry import (
    get_file_record,
    list_file_records,
    register_file,
    search_file_records,
    update_file_links,
)
from utils.file_storage import guess_file_type, safe_file_name
from utils.file_storage_models import StoredFileRecord


def test_registry_append_list_search(tmp_path):
    path = tmp_path / "file_registry.jsonl"
    r1 = register_file(
        {
            "original_file_name": "高空工作指引.pdf",
            "file_type": "knowledge_pdf",
            "source_module": "knowledge_ingestion",
            "project_ref": "BW-001",
            "tags": ["安全"],
        },
        path=path,
    )
    r2 = register_file(
        {
            "original_file_name": "A-101.pdf",
            "file_type": "drawing_pdf",
            "source_module": "drawing_analysis",
            "project_ref": "BW-001",
        },
        path=path,
    )
    assert r1.file_id and r2.file_id and r1.file_id != r2.file_id

    listed = list_file_records(path=path)
    assert len(listed) == 2

    found = search_file_records("A-101", path=path)
    assert any(item.original_file_name == "A-101.pdf" for item in found)

    by_type = list_file_records(file_type="knowledge_pdf", path=path)
    assert len(by_type) == 1 and by_type[0].original_file_name == "高空工作指引.pdf"

    got = get_file_record(r1.file_id, path=path)
    assert got is not None and got.project_ref == "BW-001"


def test_registry_handles_corrupt_jsonl(tmp_path):
    path = tmp_path / "file_registry.jsonl"
    register_file({"original_file_name": "ok.pdf"}, path=path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("{ this is not valid json\n")
        handle.write("\n")
        handle.write(json.dumps({"file_id": "file_x", "original_file_name": "also_ok.pdf"}) + "\n")
    listed = list_file_records(path=path)
    names = {item.original_file_name for item in listed}
    assert "ok.pdf" in names and "also_ok.pdf" in names
    assert len(listed) == 2  # the corrupt + blank lines are skipped


def test_registry_missing_file_returns_empty(tmp_path):
    path = tmp_path / "does_not_exist.jsonl"
    assert list_file_records(path=path) == []
    assert get_file_record("nope", path=path) is None
    assert search_file_records("anything", path=path) == []


def test_drawing_registration_links_without_exposing_path(tmp_path):
    path = tmp_path / "file_registry.jsonl"
    document = DrawingDocument.from_dict(
        {
            "document_id": "draw_1",
            "created_at": "2026-06-01T00:00:00",
            "updated_at": "2026-06-01T00:00:00",
            "project_ref": "BW-001",
            "source_file_name": "A-101.pdf",
            "disciplines": ["architecture"],
            "ingestion_status": "selectable_text",
        }
    )
    record = register_drawing_source_file(
        document,
        source_path=str(tmp_path / "uploads" / "A-101.pdf"),
        file_name="A-101.pdf",
        memory_id="pmem_1",
        registry_path=path,
    )
    assert record is not None
    assert record.linked_drawing_doc_id == "draw_1"
    assert record.linked_memory_id == "pmem_1"
    assert record.file_type == "drawing_pdf"

    public = record.to_safe_public_dict()
    assert "local_runtime_path" not in public
    blob = json.dumps(public, ensure_ascii=False)
    assert "/uploads/" not in blob and "\\uploads\\" not in blob

    listed = list_file_records(path=path)
    assert listed and listed[0].linked_drawing_doc_id == "draw_1"


def test_update_file_links_marks_drive_ready(tmp_path):
    path = tmp_path / "file_registry.jsonl"
    record = register_file({"original_file_name": "spec.pdf"}, path=path)
    updated = update_file_links(
        record.file_id,
        drive_file_id="drive-abc",
        drive_web_url="https://drive.example/abc",
        path=path,
    )
    assert updated is not None
    assert updated.storage_provider == "google_drive_ready"
    assert updated.drive_file_id == "drive-abc"


def test_storage_helpers_are_safe():
    assert safe_file_name("My File (1).PDF").endswith(".pdf")
    assert " " not in safe_file_name("a b c.txt")
    assert guess_file_type("plan.pdf", source_module="drawing_analysis") == "drawing_pdf"
    assert guess_file_type("guide.pdf", source_module="knowledge_ingestion") == "knowledge_pdf"
    assert guess_file_type("site.jpg", source_module="upload_analysis") == "site_photo"


def test_stored_file_record_from_dict_tolerates_missing_fields():
    record = StoredFileRecord.from_dict({})
    assert record.file_type == "unknown"
    assert record.storage_provider == "local_runtime"
    assert record.original_file_name == "未命名檔案"
