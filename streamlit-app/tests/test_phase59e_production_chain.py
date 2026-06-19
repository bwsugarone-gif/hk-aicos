import json
from dataclasses import dataclass
from pathlib import Path

from utils import analysis_pipeline, vision_client
from utils.analysis_pipeline import analyze_file_data_for_pipeline
from utils.followup_store import list_followups
from utils.knowledge_pack_store import read_knowledge_index
from utils.project_memory_store import read_all_memory
from utils.provider_health import get_provider_health, get_secret_value, technical_diagnostics_enabled
from utils.rag_indexer import read_rag_index
from utils.site_memory import MemoryItem, list_memory_items
from utils.site_record_store import SiteRecordStore
from utils.storage_adapters import LocalJsonStorageAdapter


APP_ROOT = Path(__file__).resolve().parents[1]
PROVIDER_KEYS = (
    "GEMINI_API_KEY", "GOOGLE_API_KEY", "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY", "TAVILY_API_KEY", "BRAVE_SEARCH_API_KEY",
)


def _clear_provider_env(monkeypatch):
    for key in PROVIDER_KEYS:
        monkeypatch.delenv(key, raising=False)


def _vision_result(*, status="success", category="cutting_grinding", manual_review=True):
    success = status == "success"
    observations = ["工人使用磨機切割金屬", "切割位置可見火花"] if success else []
    return {
        "configured": status != "not_configured",
        "performed": success,
        "status": status,
        "provider": "fixture",
        "model": "fixture",
        "category": category if success else "unknown",
        "confidence": 0.9 if success else 0.0,
        "extracted_text": "",
        "evidence_items": observations,
        "observations": observations,
        "risks": ["火花可能接觸附近物料"] if success else [],
        "unsupported_assumptions": [],
        "needs_manual_review": manual_review,
    }


def _image_file_data(path: Path):
    return {
        "type": "image", "filename": "grinder.jpg", "path": path,
        "content": "Image file", "extracted_text": "", "ocr_status": "OCR_FAILED",
        "ocr_used": False, "ocr_page_count": 0,
    }


def test_memory_reader_accepts_old_new_partial_dataclass_and_corrupt_rows(tmp_path):
    path = tmp_path / "memory.jsonl"
    rows = [
        {"memory_id": "old", "created_at": "2026-01-01", "source_type": "upload_analysis", "project_ref": "BW-OLD", "title": "舊記憶", "summary": "舊 shape"},
        {"memory_id": "partial", "project_ref": "BW-OLD", "summary": "缺少多個欄位"},
        {"memory_id": "new", "created_at": "2026-01-02", "memory_type": "qa_memory", "project_id": "BW-NEW", "title": "新記憶", "summary": "新 shape"},
    ]
    path.write_text("\n".join([*(json.dumps(row, ensure_ascii=False) for row in rows), "{corrupt"]), encoding="utf-8")
    adapter = LocalJsonStorageAdapter(memory_path=path, source_path=tmp_path / "sources.jsonl")

    all_items = list_memory_items(limit=None, adapter=adapter)
    old_items = list_memory_items(project_id="BW-OLD", limit=8, adapter=adapter)

    assert len(all_items) == 3
    assert {item.memory_id for item in old_items} == {"old", "partial"}
    assert all(isinstance(item, MemoryItem) for item in all_items)
    assert next(item for item in all_items if item.memory_id == "partial").title == "未命名記憶"


@dataclass
class _LegacyMemory:
    memory_id: str = "dataclass-old"
    created_at: str = "2026-01-01"
    project_ref: str = "BW-DATA"
    source_type: str = "manual_note"
    title: str = "Dataclass"
    summary: str = "相容測試"


def test_memory_model_accepts_dataclass_and_none_project_filter():
    item = MemoryItem.from_dict(_LegacyMemory())
    assert item.project_id == "BW-DATA"
    assert item.memory_type == "project_memory"
    assert item.status == "open"


def test_provider_health_checks_env_and_streamlit_secrets_without_leaking(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "env-secret-fixture")
    env_health = get_provider_health({})
    secrets_health = get_provider_health({"GEMINI_API_KEY": "cloud-secret-fixture", "TAVILY_API_KEY": "web-secret-fixture"})

    assert get_secret_value("DEEPSEEK_API_KEY", {}) == "env-secret-fixture"
    assert env_health.text_llm_available is True
    assert secrets_health.text_llm_available is True
    assert secrets_health.vision_available is True
    assert secrets_health.web_search_available is True
    assert secrets_health.secret_presence["GEMINI_API_KEY"]["streamlit_secrets"] is True
    encoded = json.dumps(secrets_health.to_dict(), ensure_ascii=False)
    for raw in ("env-secret-fixture", "cloud-secret-fixture", "web-secret-fixture"):
        assert raw not in encoded
    for forbidden in ("Gemini", "Anthropic", "Tavily", "Brave", "API key", "API_KEY"):
        assert forbidden not in secrets_health.user_message


def test_provider_health_no_key_is_safe_fallback(monkeypatch):
    _clear_provider_env(monkeypatch)
    health = get_provider_health({})
    assert health.fallback_mode is True
    assert health.user_message == "文字回答：使用本機備用模式 AI 視覺：未設定 網上搜尋：未設定"
    assert technical_diagnostics_enabled({}) is False
    assert technical_diagnostics_enabled({"AICOS_ADMIN_DIAGNOSTICS": "true"}) is True


def test_pipeline_vision_sparks_produces_high_risk_evidence_chain(monkeypatch, tmp_path):
    image = tmp_path / "site.jpg"
    image.write_bytes(b"fixture")
    monkeypatch.setattr("utils.image_understanding.analyze_image_with_vision", lambda *_args, **_kwargs: _vision_result())
    monkeypatch.setattr(analysis_pipeline, "get_vision_readiness", lambda: {"configured": True, "provider_label": "fixture", "last_attempt": "success", "error_category": ""})

    result = analyze_file_data_for_pipeline(
        _image_file_data(image), file_name="grinder.jpg", provider_health=get_provider_health({}), save_memory=False,
    )

    assert result.image_category in {"cutting_grinding", "hot_work", "fire_risk"}
    assert result.risk_level == "高風險"
    assert result.visual_confidence > 0
    assert "切割／打磨" in result.risk_evidence_trace.rules_matched
    assert "熱工／火花" in result.risk_evidence_trace.rules_matched
    assert {"滅火筒", "防火氈", "熱工許可"}.issubset(result.risk_evidence_trace.missing_confirmations)
    assert "判斷依據" in result.agent_answer
    encoded = json.dumps(result.to_dict(), ensure_ascii=False)
    for unsupported in ("棚架", "氣樽", "高空工作"):
        assert unsupported not in encoded


def test_pipeline_without_vision_or_manual_stays_conservative(monkeypatch, tmp_path):
    image = tmp_path / "site.jpg"
    image.write_bytes(b"fixture")
    monkeypatch.setattr("utils.image_understanding.analyze_image_with_vision", lambda *_args, **_kwargs: _vision_result(status="not_configured"))
    monkeypatch.setattr(analysis_pipeline, "get_vision_readiness", lambda: {"configured": False, "provider_label": "未設定", "last_attempt": "not_run", "error_category": ""})

    result = analyze_file_data_for_pipeline(_image_file_data(image), file_name="site.jpg", save_memory=False)

    assert result.risk_level == "需人工覆核"
    assert result.visual_confidence == 0
    assert result.observations == ["未能確認相片中的具體工序；請補充位置、工序及需跟進事項。"]
    assert any("未能確認相片中的具體工序" in item for item in result.warnings)
    encoded = json.dumps(result.to_dict(), ensure_ascii=False)
    for unsupported in ("棚架", "氣樽", "高空工作", "火花", "磨機"):
        assert unsupported not in encoded


def test_pipeline_manual_grinder_sparks_works_when_vision_fails(monkeypatch, tmp_path):
    image = tmp_path / "site.jpg"
    image.write_bytes(b"fixture")
    monkeypatch.setattr("utils.image_understanding.analyze_image_with_vision", lambda *_args, **_kwargs: {**_vision_result(status="error"), "error": "TimeoutError: redacted"})
    monkeypatch.setattr(analysis_pipeline, "get_vision_readiness", lambda: {"configured": True, "provider_label": "fixture", "last_attempt": "fail", "error_category": "TimeoutError"})

    result = analyze_file_data_for_pipeline(
        _image_file_data(image), file_name="site.jpg",
        manual_description="工人使用磨機切割，有火花", save_memory=False,
    )

    assert result.risk_level == "高風險"
    assert result.image_category in {"cutting_grinding", "hot_work", "fire_risk"}
    assert result.visual_confidence == 0
    assert "使用者補充描述" in result.risk_evidence_trace.evidence_sources
    assert any("AI 視覺暫時未能完成" in item for item in result.warnings)
    assert "redacted" not in json.dumps(result.to_dict(), ensure_ascii=False)


def test_pipeline_storage_failure_keeps_analysis_available(monkeypatch, tmp_path):
    image = tmp_path / "site.jpg"
    image.write_bytes(b"fixture")
    monkeypatch.setattr("utils.image_understanding.analyze_image_with_vision", lambda *_args, **_kwargs: _vision_result())
    monkeypatch.setattr(analysis_pipeline, "get_vision_readiness", lambda: {"configured": True, "provider_label": "fixture", "last_attempt": "success", "error_category": ""})
    monkeypatch.setattr(analysis_pipeline, "_persist_pipeline_result", lambda *_args: (_ for _ in ()).throw(PermissionError("read only")))

    result = analyze_file_data_for_pipeline(
        _image_file_data(image), file_name="site.jpg", save_memory=True,
    )

    assert result.risk_level == "高風險"
    assert any("暫時未能寫入本機記憶" in item for item in result.warnings)
    assert "read only" not in json.dumps(result.to_dict(), ensure_ascii=False)


def test_vision_readiness_uses_same_secret_helper_and_tracks_mocked_attempt(monkeypatch, tmp_path):
    _clear_provider_env(monkeypatch)
    image = tmp_path / "site.jpg"
    image.write_bytes(b"fixture")
    monkeypatch.setattr(vision_client, "get_secret_value", lambda name, _secrets=None: "configured" if name == "GEMINI_API_KEY" else None)
    monkeypatch.setattr(vision_client, "_analyze_image_with_gemini", lambda *_args: _vision_result())

    before = vision_client.get_vision_readiness({})
    result = vision_client.analyze_image_with_vision(image)
    after = vision_client.get_vision_readiness({})

    assert before["configured"] is True
    assert result["status"] == "success"
    assert after["last_attempt"] == "success"


def test_all_jsonl_readers_skip_corrupt_and_default_partial_shapes(tmp_path):
    def write(path, rows):
        path.write_text("\n".join([*(json.dumps(row, ensure_ascii=False) for row in rows), "{broken"]), encoding="utf-8")

    site_path = tmp_path / "site.jsonl"
    write(site_path, [{"record_id": "r1", "title": "舊地盤記錄", "summary": "partial"}])
    assert SiteRecordStore(site_path).list_records()[0].status == "open"

    project_path = tmp_path / "project.jsonl"
    write(project_path, [{"memory_id": "m1", "title": "舊工程記憶", "summary": "partial"}])
    assert read_all_memory(path=project_path)[0].source_type == "manual_note"

    follow_path = tmp_path / "follow.jsonl"
    write(follow_path, [{"followup_id": "f1", "title": "舊跟進"}])
    assert list_followups(path=follow_path, limit=None)[0].status == "open"

    knowledge_path = tmp_path / "knowledge.jsonl"
    write(knowledge_path, [{"source_id": "k1", "title": "舊知識"}])
    assert read_knowledge_index(index_path=knowledge_path)[0].trust_level == "unverified"

    rag_path = tmp_path / "rag.jsonl"
    write(rag_path, [{"chunk_id": "c1", "source_id": "k1", "summary": "舊 RAG 片段"}])
    assert read_rag_index(index_path=rag_path)[0].text == "舊 RAG 片段"


def test_workspace_and_upload_use_shared_pipeline_and_clean_ui_contract():
    workspace = (APP_ROOT / "pages" / "0_AICOS_Workspace.py").read_text(encoding="utf-8")
    upload = (APP_ROOT / "pages" / "1_Upload.py").read_text(encoding="utf-8")
    assert "立即上載分析" not in workspace
    assert "開始分析" in workspace
    assert "process_uploaded_file_for_analysis(" in workspace
    assert "analyze_file_data_for_pipeline(" in upload
    assert "請在下方選擇同一檔案" not in upload
    assert "如 AI 視覺未設定，請補充工序、位置、工具、火花、附近物料及防護措施。" in upload
    assert "暫時未有相關工程記憶。" in workspace
