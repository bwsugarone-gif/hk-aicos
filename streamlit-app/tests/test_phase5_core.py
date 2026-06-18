from pathlib import Path

from PIL import Image

from utils.analysis_models import ImageAnalysisResult, ImageCategory, QAResponse
from utils.followup_generator import generate_followups
from utils.image_classifier import normalize_image_category
from utils.image_understanding import analyze_image
from utils.knowledge_search import search_local_knowledge
from utils.llm_answer_client import answer_question
from utils.ocr_engine import run_ocr
from utils.site_record_store import (
    SiteRecordStore,
    save_image_analysis_record,
    save_qa_session_record,
)
from utils.web_search_adapter import get_web_search_status, web_search


def _clear_ai_keys(monkeypatch):
    for name in (
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


def test_image_category_normalization():
    assert normalize_image_category("safety") is ImageCategory.SAFETY_ISSUE
    assert normalize_image_category("attendance-or-timesheet") is ImageCategory.ATTENDANCE_OR_TIMESHEET
    assert normalize_image_category("not-a-category") is ImageCategory.UNKNOWN


def test_ocr_fallback_without_api_key(tmp_path, monkeypatch):
    _clear_ai_keys(monkeypatch)
    image_path = tmp_path / "site.png"
    Image.new("RGB", (20, 20), "white").save(image_path)
    result = analyze_image(
        image_path,
        ocr_data={"extracted_text": "Danger open edge", "ocr_status": "OCR_SUCCESS", "ocr_used": True},
    )
    assert result.detected_category is ImageCategory.SAFETY_ISSUE
    assert result.raw_metadata["fallback_used"] is True
    assert result.raw_metadata["vision"]["status"] == "not_configured"


def test_unsupported_ocr_returns_structured_failure(tmp_path):
    source = tmp_path / "sample.bmp"
    source.write_bytes(b"not-an-image")
    result = run_ocr(source)
    assert result.text == ""
    assert result.metadata["ocr_status"] == "UNSUPPORTED_FILE_TYPE"


def test_image_analysis_contains_required_fields(monkeypatch):
    _clear_ai_keys(monkeypatch)
    result = analyze_image(
        ocr_data={"extracted_text": "送貨單 批次 A-10 數量 30", "ocr_status": "OCR_SUCCESS", "ocr_used": True},
        use_vision=False,
    )
    payload = result.to_dict()
    assert set(payload) == {
        "extracted_text", "detected_category", "confidence", "key_observations",
        "risks", "recommended_followups", "source_engine", "raw_metadata",
    }
    assert payload["detected_category"] == "material_delivery"


def test_followup_generator_returns_structured_suggestions():
    suggestions = generate_followups("construction_defect", ["牆身裂縫"], ["可能滲水"])
    assert suggestions
    assert suggestions[0].title
    assert suggestions[0].responsible_role
    assert suggestions[0].priority in {"urgent", "high", "medium", "low"}


def test_knowledge_search_ranks_relevant_document(tmp_path):
    doc_dir = tmp_path / "HK-AICOS" / "docs"
    doc_dir.mkdir(parents=True)
    (doc_dir / "height-safety.md").write_text(
        "# 高空工作安全指引\n高空工作必須檢查工作平台、護欄及安全帶。",
        encoding="utf-8",
    )
    results = search_local_knowledge("高空工作平台臨邊沒有安全帶應如何跟進", project_root=tmp_path)
    assert results
    assert results[0].path.endswith("height-safety.md")
    assert "安全帶" in results[0].snippet


def test_knowledge_search_excludes_unsafe_paths(tmp_path):
    root = tmp_path / "streamlit-app"
    (root / "node_modules").mkdir(parents=True)
    (root / "node_modules" / "secret.md").write_text("unique-secret-term", encoding="utf-8")
    (root / ".env").write_text("API_KEY=unique-secret-term", encoding="utf-8")
    assert search_local_knowledge("unique-secret-term", project_root=tmp_path) == []


def test_llm_answer_client_fallback_structure(monkeypatch):
    _clear_ai_keys(monkeypatch)
    response = answer_question("高空工作有甚麼即時措施？", "safety", "web_search", [])
    assert isinstance(response, QAResponse)
    assert response.fallback_used is True
    assert response.model_name == "local-fallback"
    assert response.used_search_scope == "web_search"
    assert "沒有" in response.answer or "本機" in response.answer


def test_qa_response_model_structure():
    response = QAResponse(answer="測試", used_search_scope="all")
    assert set(response.to_dict()) == {
        "answer", "practical_recommendations", "risk_level", "sources",
        "followup_actions", "confidence", "used_search_scope", "model_name", "fallback_used",
    }


def test_web_search_fallback_when_not_configured(monkeypatch):
    for name in ("TAVILY_API_KEY", "BRAVE_SEARCH_API_KEY", "SERPAPI_API_KEY", "GOOGLE_CSE_ID", "GOOGLE_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    assert web_search("Hong Kong construction safety") == []
    status = get_web_search_status()
    assert status.configured is False
    assert status.performed is False


def test_site_record_store_writes_reads_and_generates_unique_ids(tmp_path):
    store = SiteRecordStore(tmp_path / "records.jsonl")
    first = store.create_record(record_type="followup_action", title="A", content_summary="one", source="test")
    second = store.create_record(record_type="followup_action", title="B", content_summary="two", source="test")
    store.save(first)
    store.save(second)
    records = store.list_records()
    assert len(records) == 2
    assert first.record_id != second.record_id
    assert {item.title for item in records} == {"A", "B"}
    assert store.search_records(keyword="please find two record")[0].title == "B"


def test_qa_session_can_be_saved(tmp_path):
    store = SiteRecordStore(tmp_path / "records.jsonl")
    response = QAResponse(answer="先圍封現場", risk_level="high", followup_actions=["通知安全主任"])
    saved = save_qa_session_record("臨邊危險如何處理？", response, question_type="safety", store=store)
    assert saved.record_type == "qa_session"
    assert store.list_records()[0].raw_payload["question"] == "臨邊危險如何處理？"


def test_image_analysis_can_be_saved(tmp_path):
    store = SiteRecordStore(tmp_path / "records.jsonl")
    analysis = ImageAnalysisResult(
        extracted_text="warning",
        detected_category=ImageCategory.SAFETY_ISSUE,
        confidence=0.8,
        key_observations=["臨邊位置"],
        risks=["墮下風險"],
        recommended_followups=generate_followups("safety_issue", risks=["墮下風險"]),
    )
    saved = save_image_analysis_record(analysis, filename="site.jpg", store=store)
    assert saved.record_type == "image_analysis"
    assert saved.category == "safety_issue"
    assert store.list_records()[0].raw_payload["extracted_text"] == "warning"
