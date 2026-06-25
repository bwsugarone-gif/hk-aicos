"""Phase 6.4 — Ask AICOS document / RAG context routing tests."""

from __future__ import annotations

import utils.ask_context_bridge as bridge
from utils.analysis_models import KnowledgeSnippet
from utils.ask_intent_router import classify_ask_intent
from utils.knowledge_ingestion import ingest_text
from utils.rag_persistence import build_ingested_rag_context


def test_pdf_and_document_questions_route_to_document_intents():
    assert classify_ask_intent("呢份 PDF 有冇講熱工許可？").intent_type == "pdf_question"
    assert classify_ask_intent("搵返文件入面關於高空工作嘅內容").intent_type == "knowledge_document_question"
    assert classify_ask_intent("呢份文件有冇防火監察要求？").intent_type == "knowledge_document_question"


def test_drawing_question_not_hijacked_by_document_intent():
    # Contains 圖紙 -> must stay a drawing question, not a document question.
    assert classify_ask_intent("我之前上載過咩圖紙？").intent_type == "drawing_question"
    assert classify_ask_intent("搵返所有 CAD team 未完成事項").intent_type == "cad_bim_handoff_question"


def test_build_ingested_rag_context_retrieves_relevant_chunk(tmp_path):
    rpath = tmp_path / "ingested_rag.jsonl"
    ingest_text(
        text="Hot work permit and fire watch monitoring are required before grinding. " * 6,
        title="hot work doc",
        original_file_name="hot_work.pdf",
        project_ref="BW-001",
        knowledge_path=tmp_path / "k.jsonl",
        rag_path=rpath,
    )
    snippets = build_ingested_rag_context("hot work permit", "BW-001", limit=5, path=rpath)
    assert snippets
    assert any("hot work" in s.snippet.lower() for s in snippets)
    assert all(s.source_type == "rag_chunk" for s in snippets)


def _silence_other_retrievers(monkeypatch):
    for name in (
        "search_local_knowledge",
        "build_knowledge_pack_context",
        "build_knowledge_context",
        "build_rag_context",
        "build_project_memory_context",
        "build_followup_context",
    ):
        monkeypatch.setattr(bridge, name, lambda *a, **k: [])
    monkeypatch.setattr(bridge, "read_all_memory", lambda *a, **k: [])


def test_ask_context_uses_document_chunks_for_pdf_question(monkeypatch):
    _silence_other_retrievers(monkeypatch)
    snippet = KnowledgeSnippet(
        title="hot work permit（第 1 頁）",
        path="知識文件 / hot_work.pdf",
        snippet="進行熱工序前必須申請熱工許可證並設置防火監察。",
        score=5.0,
        source_type="rag_chunk",
        source_id="ingrag:abc",
        trust_level="uploaded_record",
        provider="ingested_documents",
    )
    monkeypatch.setattr(bridge, "build_ingested_rag_context", lambda *a, **k: [snippet])
    monkeypatch.setattr(bridge, "_has_metadata_only_documents", lambda *a, **k: False)

    selection = bridge.build_ask_context_selection(
        "呢份 PDF 有冇講熱工許可？", search_scope="all", project_ref="BW-001"
    )
    assert selection.intent.intent_type == "pdf_question"
    assert selection.retrieval_counts.get("document_chunks", 0) >= 1
    assert any(getattr(c, "source_id", "") == "ingrag:abc" for c in selection.contexts)


def test_ask_context_reports_metadata_only_when_no_text(monkeypatch):
    _silence_other_retrievers(monkeypatch)
    monkeypatch.setattr(bridge, "build_ingested_rag_context", lambda *a, **k: [])
    monkeypatch.setattr(bridge, "_has_metadata_only_documents", lambda *a, **k: True)

    selection = bridge.build_ask_context_selection(
        "呢份文件有冇防火監察要求？", search_scope="all", project_ref="BW-001"
    )
    assert selection.intent.intent_type == "knowledge_document_question"
    assert selection.retrieval_counts.get("document_metadata_only") == 1
    assert any(
        getattr(c, "source_id", "") == "doc-guidance:metadata-only" for c in selection.contexts
    )
    assert any("metadata" in line for line in selection.context_basis)
