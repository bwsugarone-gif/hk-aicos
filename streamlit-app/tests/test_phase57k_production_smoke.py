import json
import py_compile
from pathlib import Path

import pytest

from utils import llm_answer_client, vision_client
from utils.analysis_models import EvidenceContext, QAResponse
from utils.image_safety_hardening import (
    build_concise_image_summary,
    filter_unsupported_payload,
    render_concise_image_summary,
)
from utils.image_understanding import analyze_image


APP_ROOT = Path(__file__).resolve().parents[1]


def test_safe_answer_question_is_stable_export_and_returns_structured_fallback(monkeypatch):
    assert "safe_answer_question" in llm_answer_client.__all__
    assert callable(llm_answer_client.safe_answer_question)

    def provider_runtime_failure(**_kwargs):
        raise RuntimeError("secret provider detail")

    monkeypatch.setattr(llm_answer_client, "answer_question", provider_runtime_failure)
    response, recovered = llm_answer_client.safe_answer_question(
        question="高空工作如何處理？",
        question_type="safety",
        search_scope="all",
        context_snippets=[],
        answer_mode="site_simple",
    )
    assert isinstance(response, QAResponse)
    assert response.fallback_used is True
    assert recovered is True
    assert "secret provider detail" not in response.answer


def test_safe_answer_question_can_surface_programming_errors_in_tests(monkeypatch):
    monkeypatch.setattr(
        llm_answer_client,
        "answer_question",
        lambda **_kwargs: (_ for _ in ()).throw(TypeError("signature drift")),
    )
    with pytest.raises(TypeError, match="signature drift"):
        llm_answer_client.safe_answer_question(
            "問題",
            "general",
            "all",
            [],
            raise_on_error=True,
        )


def test_ask_and_workspace_pages_compile_and_import_stable_wrapper():
    for relative in ("pages/10_Ask_AICOS.py", "pages/0_AICOS_Workspace.py"):
        page = APP_ROOT / relative
        py_compile.compile(str(page), doraise=True)
        source = page.read_text(encoding="utf-8")
        assert "from utils.llm_answer_client import safe_answer_question" in source
        assert "safe_answer_question(" in source


def test_evidence_context_has_required_production_gate_fields():
    payload = EvidenceContext().to_dict()
    assert set(payload) == {
        "has_ocr_text",
        "ocr_confidence",
        "has_visual_analysis",
        "visual_confidence",
        "visual_observations",
        "user_description",
        "selected_analysis_type",
        "evidenced_terms",
        "unsupported_terms",
    }


def test_zero_visual_confidence_without_context_generates_no_specific_hazard(tmp_path):
    image_path = tmp_path / "site-photo.jpg"
    image_path.write_bytes(b"fixture")
    result = analyze_image(
        image_path,
        ocr_data={"ocr_status": "OCR_FAILED", "extracted_text": "", "filename": image_path.name},
        use_vision=False,
    )
    rendered = render_concise_image_summary(result)

    assert result.visual_confidence == 0.0
    assert result.image_category.value == "general_site_photo"
    assert result.risks == []
    assert "未能確認相片中的具體工序" in rendered
    for term in ("working at height", "高空工作", "scaffold", "棚架", "gas cylinder", "氣樽", "安全帶", "護欄", "踢腳板"):
        assert term not in rendered


def test_manual_grinder_sparks_context_classifies_without_claiming_visual_analysis(tmp_path):
    image_path = tmp_path / "site-photo.jpg"
    image_path.write_bytes(b"fixture")
    result = analyze_image(
        image_path,
        ocr_data={
            "ocr_status": "OCR_FAILED",
            "extracted_text": "",
            "filename": image_path.name,
            "manual_context": "工人正在室內用磨機切割門框，現場有火花。",
            "selected_analysis_type": "工地安全分析",
        },
        use_vision=False,
    )
    evidence_context = result.raw_metadata["evidence_context"]

    assert result.image_category.value in {"hot_work", "cutting_grinding", "fire_risk"}
    assert result.visual_confidence == 0.0
    assert evidence_context["has_visual_analysis"] is False
    assert evidence_context["user_description"].startswith("工人正在室內")
    assert any("火花" in risk for risk in result.risks)


def test_selected_safety_analysis_type_alone_is_not_visual_evidence(tmp_path):
    image_path = tmp_path / "site-photo.jpg"
    image_path.write_bytes(b"fixture")
    result = analyze_image(
        image_path,
        ocr_data={
            "ocr_status": "OCR_FAILED",
            "extracted_text": "",
            "filename": image_path.name,
            "selected_analysis_type": "工地安全分析",
        },
        use_vision=False,
    )
    assert result.risks == []
    assert result.raw_metadata["evidence_context"]["evidenced_terms"] == []


def test_unsupported_terms_are_removed_from_merged_risk_and_action_plan():
    payload = {
        "merged_risks": [
            {"label": "高空工作及棚架護欄風險", "score": 50},
            {"label": "火花引燃附近物料", "score": 40},
        ],
        "final_action_plan": [
            "檢查安全帶及踢腳板。",
            "清走火花附近可燃物。",
        ],
    }
    cleaned, unsupported = filter_unsupported_payload(
        payload,
        evidence_items=["磨機切割產生火花"],
    )
    encoded = json.dumps(cleaned, ensure_ascii=False)

    assert "火花" in encoded
    for term in ("高空工作", "棚架", "護欄", "安全帶", "踢腳板"):
        assert term not in encoded
    assert unsupported


def test_report_summary_excludes_unsupported_terms_when_vision_is_unavailable(tmp_path):
    image_path = tmp_path / "site-photo.jpg"
    image_path.write_bytes(b"fixture")
    result = analyze_image(
        image_path,
        ocr_data={"ocr_status": "OCR_FAILED", "extracted_text": "", "filename": image_path.name},
        use_vision=False,
    )
    summary = build_concise_image_summary(result)
    encoded = json.dumps(summary, ensure_ascii=False)
    assert summary["risk_level"] == "需人工覆核"
    for term in ("高空工作", "棚架", "氣樽", "安全帶", "護欄", "踢腳板"):
        assert term not in encoded


def test_gemini_vision_is_selected_without_live_network(monkeypatch, tmp_path):
    image_path = tmp_path / "site-photo.jpg"
    image_path.write_bytes(b"fixture")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    expected = {"configured": True, "performed": True, "status": "success", "provider": "gemini"}
    monkeypatch.setattr(vision_client, "_analyze_image_with_gemini", lambda *_args: expected)

    assert vision_client.analyze_image_with_vision(image_path) == expected


def test_upload_page_has_manual_context_and_safe_vision_status_copy():
    source = (APP_ROOT / "pages" / "1_Upload.py").read_text(encoding="utf-8")
    assert "補充現場描述 / 工序資料（選填）" in source
    assert "AI 視覺：已啟用" in source
    assert "AI 視覺：未設定" in source
    assert "AI 視覺：失敗，已改為人工覆核模式" in source
    assert "未能進行 AI 視覺辨識；請補充工序描述或啟用 Vision API。" in source
