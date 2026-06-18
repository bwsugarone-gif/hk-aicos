from pathlib import Path

import pytest

from utils.knowledge_tracker import (
    KnowledgeSourceItem,
    build_knowledge_context,
    list_source_items,
    save_source_item,
    search_sources,
)
from utils.navigation import PRIMARY_PAGES, navigation_labels
from utils.site_memory import (
    MemoryItem,
    build_memory_context,
    list_memory_items,
    save_memory_item,
    search_memory,
)
from utils.storage_adapters import GoogleDriveStorageAdapter, LocalJsonStorageAdapter


def _adapter(tmp_path: Path) -> LocalJsonStorageAdapter:
    return LocalJsonStorageAdapter(
        memory_path=tmp_path / "memory.jsonl",
        source_path=tmp_path / "sources.jsonl",
    )


def test_local_json_storage_adapter_saves_lists_searches_and_gets_source(tmp_path):
    adapter = _adapter(tmp_path)
    adapter.save_record(
        {
            "memory_id": "mem_1",
            "created_at": "2026-06-19T10:00:00+00:00",
            "memory_type": "issue_memory",
            "project_id": "BW-001",
            "title": "高空工作防墮",
            "summary": "檢查工作台及護欄",
        }
    )
    adapter.save_file_metadata(
        {
            "source_id": "src_1",
            "created_at": "2026-06-19T10:00:00+00:00",
            "source_type": "sop",
            "project_id": "BW-001",
            "title": "高空工作 SOP",
            "summary": "護欄及安全帶檢查",
        }
    )

    assert adapter.list_records(project_id="BW-001")[0]["memory_id"] == "mem_1"
    assert adapter.search_records("高空工作", project_id="BW-001")[0]["title"] == "高空工作防墮"
    assert adapter.list_sources(project_id="BW-001")[0]["source_id"] == "src_1"
    assert adapter.search_sources("安全帶", project_id="BW-001")[0]["source_id"] == "src_1"
    assert adapter.get_source("src_1")["title"] == "高空工作 SOP"


def test_memory_item_save_list_search_and_context_builder(tmp_path):
    adapter = _adapter(tmp_path)
    saved = save_memory_item(
        adapter=adapter,
        memory_type="followup_memory",
        project_id="BW-002",
        title="棚架護欄跟進",
        summary="管工需覆核踢腳板及護欄",
        tags=["棚架", "安全"],
        related_record_ids=["rec_1"],
        risk_level="high",
        status="open",
    )

    assert isinstance(saved, MemoryItem)
    assert saved.memory_id.startswith("mem_")
    assert list_memory_items(project_id="BW-002", adapter=adapter)[0].title == "棚架護欄跟進"
    assert search_memory("踢腳板", "BW-002", adapter=adapter)[0].memory_id == saved.memory_id
    context = build_memory_context("棚架護欄", "BW-002", adapter=adapter)
    assert context[0].source_id == f"memory:{saved.memory_id}"
    assert context[0].provider == "aicos_memory"


def test_knowledge_source_save_list_search_and_context_builder(tmp_path):
    adapter = _adapter(tmp_path)
    saved = save_source_item(
        adapter=adapter,
        source_type="official_guidance",
        title="竹棚架工作安全守則",
        storage_provider="google_drive",
        google_drive_file_id="drive-file-placeholder",
        google_drive_url="https://drive.google.com/file/d/placeholder",
        project_id="BW-003",
        tags=["棚架", "勞工處"],
        summary="包括工作台、護欄及防墮要求",
        indexed_status="pending",
    )

    assert isinstance(saved, KnowledgeSourceItem)
    assert saved.google_drive_file_id == "drive-file-placeholder"
    assert list_source_items(project_id="BW-003", adapter=adapter)[0].source_id == saved.source_id
    assert search_sources("防墮", "BW-003", adapter=adapter)[0].source_id == saved.source_id
    context = build_knowledge_context("護欄", "BW-003", adapter=adapter)
    assert context[0].source_id == f"knowledge:{saved.source_id}"
    assert context[0].path == saved.google_drive_url


def test_google_drive_adapter_is_placeholder_and_makes_no_api_call():
    adapter = GoogleDriveStorageAdapter()
    assert adapter.configured is False
    assert adapter.integration_status == "placeholder_only"
    with pytest.raises(NotImplementedError, match="not enabled"):
        adapter.list_sources()


def test_workspace_is_first_primary_navigation_and_bilingual():
    assert PRIMARY_PAGES[0] == ("workspace", "pages/0_AICOS_Workspace.py")
    assert navigation_labels("繁體中文")["workspace"] == "🏗️ AICOS 工作台"
    assert navigation_labels("English")["workspace"] == "🏗️ AICOS Workspace"


def test_workspace_and_memory_integration_contracts_are_present():
    app_root = Path(__file__).resolve().parents[1]
    workspace = (app_root / "pages" / "0_AICOS_Workspace.py").read_text(encoding="utf-8")
    ask_page = (app_root / "pages" / "10_Ask_AICOS.py").read_text(encoding="utf-8")
    upload_page = (app_root / "pages" / "1_Upload.py").read_text(encoding="utf-8")

    assert 'st.title("🏗️ AICOS 工作台")' in workspace
    assert 'st.columns(2, gap="large")' in workspace
    assert "build_memory_context" in workspace
    assert "build_knowledge_context" in workspace
    assert "Google Drive 欄位已預留" in workspace
    assert "build_memory_context(question" in ask_page
    assert "build_knowledge_context(question" in ask_page
    assert 'memory_type="qa_memory"' in ask_page
    assert 'memory_type="issue_memory" if risks else "followup_memory"' in upload_page


def test_architecture_note_explains_drive_is_storage_not_memory_brain():
    repo_root = Path(__file__).resolve().parents[2]
    note = (repo_root / "docs" / "KNOWLEDGE_MEMORY_ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "並不是「記憶大腦」" in note
    assert "GoogleDriveStorageAdapter" in note
    assert "Vector search／RAG index" in note
