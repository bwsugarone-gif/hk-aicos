import json
from pathlib import Path

from utils.google_drive_adapter import GoogleDriveFileMetadata, GoogleDriveKnowledgeAdapter
from utils.knowledge_models import KnowledgeSource
from utils.rag_indexer import (
    build_rag_index_from_knowledge_sources,
    chunk_text,
    index_text_source,
    read_rag_index,
)
from utils.rag_retriever import build_rag_context, search_rag, summarize_rag_hits


APP_ROOT = Path(__file__).resolve().parents[1]


def test_google_drive_adapter_is_safe_skeleton_without_config(monkeypatch):
    monkeypatch.delenv("GOOGLE_DRIVE_FOLDER_ID", raising=False)
    adapter = GoogleDriveKnowledgeAdapter()

    assert adapter.is_configured() is False
    assert adapter.list_files() == []
    assert adapter.status == "live_api_not_enabled"
    assert adapter.get_file_metadata("fixture") is None


def test_google_drive_metadata_converts_to_knowledge_source():
    adapter = GoogleDriveKnowledgeAdapter("folder-fixture")
    metadata = GoogleDriveFileMetadata(
        drive_file_id="file-1",
        name="熱工安全 SOP",
        mime_type="application/pdf",
        web_url="https://drive.google.com/file/d/file-1/view",
        tags=["HK", "熱工"],
        project_ref="BW-001",
        trust_level="internal",
    )

    source = adapter.build_source_from_drive_file(metadata)

    assert isinstance(source, KnowledgeSource)
    assert source.source_id == "gdrive:file-1"
    assert source.title == "熱工安全 SOP"
    assert source.jurisdiction == "HK"
    assert source.path_or_url == metadata.web_url


def test_rag_chunking_indexing_and_reference_shape(tmp_path):
    text = "Section 5.3 熱工安全要求。\n" + ("磨機切割時應控制火花並備有滅火筒。" * 80)
    chunks = chunk_text(text, max_chars=160, overlap=20)
    assert len(chunks) > 1
    assert all(len(item) <= 160 for item in chunks)

    index_path = tmp_path / "rag.jsonl"
    indexed = index_text_source(
        "sop-hot-work", "熱工安全 SOP", text,
        {"source_type": "sop", "trust_level": "internal", "project_ref": "BW-001"},
        index_path=index_path,
    )
    assert indexed
    assert indexed[0].section_ref == "5.3"
    assert len(read_rag_index(index_path=index_path)) == len(indexed)


def test_rag_keyword_and_chinese_search_and_context_shape(tmp_path):
    index_path = tmp_path / "rag.jsonl"
    index_text_source(
        "sop-1", "磨機熱工 SOP", "磨機切割會產生火花，應準備滅火筒及防火氈。",
        {"source_type": "sop", "trust_level": "trusted", "project_ref": "BW-001"},
        index_path=index_path,
    )
    index_text_source(
        "sop-2", "棚架巡查", "棚架巡查應核對工作平台及通道。",
        {"source_type": "sop", "trust_level": "internal", "project_ref": "BW-002"},
        index_path=index_path,
    )

    hits = search_rag("磨機 火花", project_ref="BW-001", index_path=index_path)
    chinese_hits = search_rag("棚架巡查", index_path=index_path)
    contexts = build_rag_context("磨機 火花", "BW-001", index_path=index_path)

    assert hits and hits[0].source_id == "sop-1"
    assert chinese_hits and chinese_hits[0].source_id == "sop-2"
    assert contexts and contexts[0].source_type == "rag_chunk"
    assert contexts[0].provider == "local_rag"
    assert contexts[0].source_id.startswith("rag:")
    assert summarize_rag_hits(hits)["total"] == 1


def test_rag_missing_index_and_safe_exclusion_do_not_leak_secret(tmp_path):
    missing = tmp_path / "missing.jsonl"
    assert read_rag_index(index_path=missing) == []
    assert search_rag("anything", index_path=missing) == []

    forbidden = APP_ROOT.parent / ".env"
    knowledge_path = tmp_path / "knowledge.jsonl"
    source = KnowledgeSource(
        source_id="env-fixture", title="設定檔 metadata", source_type="internal",
        path_or_url=str(forbidden), trust_level="internal", jurisdiction="HK",
        summary="只索引安全 metadata，不讀取設定值。",
    )
    knowledge_path.write_text(json.dumps(source.to_dict(), ensure_ascii=False) + "\n", encoding="utf-8")
    rag_path = tmp_path / "rag.jsonl"
    chunks = build_rag_index_from_knowledge_sources(
        knowledge_index_path=knowledge_path, rag_index_path=rag_path,
    )
    encoded = json.dumps([item.to_dict() for item in chunks], ensure_ascii=False)
    assert "API_KEY=" not in encoded
    assert "只索引安全 metadata" in encoded


def test_ask_workspace_and_records_integrate_rag_without_raw_chunk_dump():
    ask = (APP_ROOT / "pages" / "10_Ask_AICOS.py").read_text(encoding="utf-8")
    workspace = (APP_ROOT / "pages" / "0_AICOS_Workspace.py").read_text(encoding="utf-8")
    records = (APP_ROOT / "pages" / "11_Records.py").read_text(encoding="utf-8")
    for source in (ask, workspace):
        assert "build_rag_context(" in source
        assert '"rag"' in source
    assert "RAG 知識片段" in ask
    assert "更新 SOP / RAG 索引" in records
    assert "read_rag_index()" in records
