import json

from utils.analysis_models import KnowledgeSnippet, SearchResult
from utils.llm_answer_client import _parse_provider_answer, answer_question
from utils.official_sources import (
    citation_from_source,
    classify_source_trust,
    extract_domain,
    filter_sources_by_mode,
    is_official_hk_source,
    normalize_url,
)
from utils.site_record_store import (
    SiteRecordStore,
    normalize_priority,
    normalize_status,
)
from utils.web_search_adapter import get_web_search_status, web_search


def _clear_provider_keys(monkeypatch):
    for name in (
        "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "GEMINI_API_KEY",
        "GOOGLE_API_KEY", "TAVILY_API_KEY", "BRAVE_SEARCH_API_KEY", "SERPAPI_API_KEY",
        "GOOGLE_CSE_ID",
    ):
        monkeypatch.delenv(name, raising=False)


def test_official_source_classification_and_url_normalization():
    assert normalize_url("LABOUR.gov.hk/safety#section") == "https://labour.gov.hk/safety"
    assert normalize_url("javascript:alert(1)") == ""
    assert extract_domain("https://www.bd.gov.hk/en/") == "bd.gov.hk"
    assert is_official_hk_source("https://service.e-legislation.gov.hk/cap59") is True
    assert classify_source_trust("https://www.cic.hk/eng/main/") == "trusted_industry"
    assert classify_source_trust("https://example.com/article") == "general_web"


def test_source_filtering_modes():
    results = [
        SearchResult("General", "https://example.com/a", "g", "test"),
        SearchResult("Industry", "https://cic.hk/a", "t", "test"),
        SearchResult("Official", "https://labour.gov.hk/a", "o", "test"),
    ]
    official = filter_sources_by_mode(results, "official_only")
    trusted_first = filter_sources_by_mode(results, "trusted_first")
    general = filter_sources_by_mode(results, "general_web")
    assert [item.title for item in official] == ["Official"]
    assert [item.trust_level for item in trusted_first] == ["official_hk", "trusted_industry", "general_web"]
    assert len(general) == 3


def test_source_trust_metadata_shape():
    citation = citation_from_source(
        SearchResult("Labour", "https://labour.gov.hk/safety", "Safety guide", "tavily"),
        used_in_answer=True,
    ).to_dict()
    assert set(citation) == {
        "source_id", "source_title", "source_url", "source_path", "source_type",
        "trust_level", "snippet", "used_in_answer", "provider", "retrieved_at",
    }
    assert citation["trust_level"] == "official_hk"


def test_web_search_unconfigured_fallback_metadata(monkeypatch):
    _clear_provider_keys(monkeypatch)
    assert web_search("香港高空工作法例", source_mode="official_only") == []
    status = get_web_search_status()
    assert status.performed is False
    assert status.trust_level == "fallback_only"
    assert status.source_mode == "official_only"
    assert status.result_count == 0


def test_ask_aicos_response_uses_only_supplied_source_citations(monkeypatch):
    _clear_provider_keys(monkeypatch)
    source = KnowledgeSnippet(
        title="高空工作守則",
        path="streamlit-app/rag_documents/cop.md",
        snippet="臨邊須設護欄。",
        score=9.0,
        source_type="local_internal",
        source_id="local_cop_1",
        trust_level="local_internal",
    )
    response = answer_question("臨邊如何處理？", "safety", "local_knowledge", [source])
    payload = response.to_dict()
    assert payload["sources"][0]["source_id"] == "local_cop_1"
    assert payload["sources"][0]["used_in_answer"] is True
    assert payload["sources"][0]["trust_level"] == "local_internal"
    assert "即時連線" in payload["answer"]


def test_provider_cannot_invent_citation_ids():
    source = KnowledgeSnippet(
        title="Internal note",
        path="docs/note.md",
        snippet="Known context",
        score=1.0,
        source_type="local_internal",
        source_id="local_real",
        trust_level="local_internal",
    )
    response = _parse_provider_answer(
        '{"answer":"Answer","practical_recommendations":[],"risk_level":"low",'
        '"source_ids":["invented_source"],"sources":["https://invented.example"],'
        '"followup_actions":[],"confidence":0.8}',
        "general",
        "local_knowledge",
        [source],
        "test-model",
    )
    assert [item.source_id for item in response.sources] == ["local_real"]
    assert response.sources[0].used_in_answer is False


def test_status_normalization():
    assert normalize_status("in-progress") == "in_progress"
    assert normalize_status("done") == "resolved"
    assert normalize_status("unexpected") == "open"


def test_priority_normalization():
    assert normalize_priority("HIGH") == "high"
    assert normalize_priority("critical") == "urgent"
    assert normalize_priority("unexpected") == "low"


def test_site_record_append_update_flow(tmp_path):
    store = SiteRecordStore(tmp_path / "records.jsonl")
    original = store.create_record(
        record_type="followup_action",
        title="臨邊圍封",
        content_summary="等待分判商處理",
        source="site",
    )
    store.save(original)
    updated = store.update_record(
        original.record_id,
        status="pending_contractor",
        priority="urgent",
        responsible_role="安全主任",
        due_hint="今日收工前",
        remarks="已通知分判商",
        change_summary="發出即時整改指示",
    )
    assert updated.status == "pending_contractor"
    assert updated.priority == "urgent"
    assert updated.responsible_role == "安全主任"
    assert updated.history[-1]["previous_status"] == "open"
    assert len((tmp_path / "records.jsonl").read_text(encoding="utf-8").splitlines()) == 2


def test_jsonl_read_safety_after_update(tmp_path):
    path = tmp_path / "records.jsonl"
    store = SiteRecordStore(path)
    record = store.create_record(record_type="qa_session", title="Q", content_summary="A", source="Ask")
    store.save(record)
    store.update_record(record.record_id, status="resolved")
    with path.open("a", encoding="utf-8") as handle:
        handle.write("{incomplete\n")
    loaded = store.get_record(record.record_id)
    assert loaded is not None
    assert loaded.status == "resolved"
    assert len(loaded.history) == 1


def test_record_filters_include_priority_and_status(tmp_path):
    store = SiteRecordStore(tmp_path / "records.jsonl")
    first = store.create_record(record_type="followup_action", title="A", content_summary="edge", source="site")
    second = store.create_record(record_type="followup_action", title="B", content_summary="material", source="site")
    store.save(first)
    store.save(second)
    store.update_record(second.record_id, status="in_progress", priority="high")
    matches = store.search_records(status="in_progress", priority="high")
    assert [item.record_id for item in matches] == [second.record_id]


def test_old_jsonl_record_remains_readable(tmp_path):
    path = tmp_path / "records.jsonl"
    old_record = {
        "record_id": "rec_old",
        "created_at": "2026-01-01T00:00:00+00:00",
        "record_type": "image_analysis",
        "title": "舊圖片記錄",
        "content_summary": "舊格式",
        "source": "old.jpg",
        "category": "safety_issue",
        "risk_level": "high",
        "status": "open",
        "raw_payload": {},
    }
    path.write_text(json.dumps(old_record, ensure_ascii=False) + "\n", encoding="utf-8")
    loaded = SiteRecordStore(path).list_records()
    assert loaded[0].record_id == "rec_old"
    assert loaded[0].priority == "low"
    assert loaded[0].history == []
