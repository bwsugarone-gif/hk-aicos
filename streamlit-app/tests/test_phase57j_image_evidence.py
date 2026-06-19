from pathlib import Path

from utils.analysis_models import OCRResult
from utils.image_safety_hardening import (
    build_concise_image_summary,
    filter_unsupported_assumptions,
    merge_credible_risk,
    render_concise_image_summary,
)
from utils.image_understanding import analyze_image


def _sample_vision_result():
    return {
        "configured": True,
        "performed": True,
        "status": "success",
        "provider": "fixture",
        "model": "fixture",
        "category": "general_site_photo",
        "confidence": 0.82,
        "extracted_text": "",
        "evidence_items": [
            "工人正在室內近門框使用磨機切割金屬",
            "切割工序產生明顯火花",
            "工人可見佩戴安全帽、手套及長袖保護",
        ],
        "observations": [
            "工人正在室內使用磨機或切割工具",
            "工序產生明顯火花",
        ],
        "risks": [
            "火花可能引燃附近裝修材料",
            "棚架沒有護欄及踢腳板",
            "高空工作工人沒有安全帶",
            "附近有氣樽",
        ],
        "unsupported_assumptions": [],
        "needs_manual_review": True,
    }


def test_ocr_confidence_is_separate_from_visual_confidence(monkeypatch, tmp_path):
    image_path = tmp_path / "site-photo.jpg"
    image_path.write_bytes(b"fixture")
    monkeypatch.setattr(
        "utils.image_understanding.analyze_image_with_vision",
        lambda *_args, **_kwargs: _sample_vision_result(),
    )

    result = analyze_image(
        image_path,
        ocr_data=OCRResult(text="", confidence=0.35, metadata={"ocr_status": "OCR_FAILED"}),
    )

    assert result.ocr_confidence == 0.35
    assert result.visual_confidence == 0.82
    assert result.confidence == result.visual_confidence
    assert result.confidence != result.ocr_confidence


def test_photo_without_text_still_produces_hot_work_visual_analysis(monkeypatch, tmp_path):
    image_path = tmp_path / "site-photo.jpg"
    image_path.write_bytes(b"fixture")
    monkeypatch.setattr(
        "utils.image_understanding.analyze_image_with_vision",
        lambda *_args, **_kwargs: _sample_vision_result(),
    )

    result = analyze_image(
        image_path,
        ocr_data=OCRResult(text="", confidence=0.0, metadata={"ocr_status": "OCR_FAILED"}),
    )

    assert result.ocr_text == ""
    assert result.image_category.value == "cutting_grinding"
    assert result.visual_observations
    assert any("火花" in item for item in result.visual_observations)
    assert any("磨機" in item or "切割" in item for item in result.visual_observations)


def test_filename_context_allows_conservative_hot_work_fallback_without_vision(tmp_path):
    image_path = tmp_path / "grinder-hot-work.jpg"
    image_path.write_bytes(b"fixture")
    result = analyze_image(
        image_path,
        ocr_data={"ocr_status": "OCR_FAILED", "extracted_text": "", "filename": image_path.name},
        use_vision=False,
    )

    assert result.image_category.value in {"hot_work", "cutting_grinding"}
    assert result.visual_confidence == 0.0
    assert result.needs_manual_review is True


def test_unsupported_assumptions_are_removed_without_evidence():
    claims = [
        "棚架沒有護欄及踢腳板",
        "高空工作工人沒有安全帶",
        "附近有氣樽",
        "切割工序產生火花",
    ]
    kept, unsupported = filter_unsupported_assumptions(
        claims,
        evidence_items=["工人使用磨機切割，產生火花"],
    )

    assert kept == ["切割工序產生火花"]
    unsupported_text = " ".join(unsupported)
    for term in ("棚架", "護欄", "踢腳板", "高空工作", "安全帶", "氣樽"):
        assert term in unsupported_text


def test_final_risk_cannot_downgrade_high_raw_risk_without_mitigation():
    assert merge_credible_risk("低風險", "高風險", {}) == "高風險"
    hot_work = {
        "image_category": "cutting_grinding",
        "evidence_items": ["室內使用磨機切割並產生火花"],
    }
    assert merge_credible_risk("低風險", "低風險", hot_work) == "高風險"


def test_concise_summary_is_bounded_and_does_not_repeat_sections():
    analysis = {
        "image_category": "hot_work",
        "visual_observations": [f"觀察 {index}" for index in range(8)],
        "risks": [f"風險 {index}" for index in range(8)],
        "recommended_followups": [
            {"action": f"建議 {index}", "responsible_role": "管工"}
            for index in range(8)
        ],
    }
    summary = build_concise_image_summary(analysis)
    rendered = render_concise_image_summary(analysis)

    assert len(summary["observations"]) <= 5
    assert len(summary["risks"]) <= 5
    assert len(summary["recommendations"]) <= 5
    assert len(summary["confirmations"]) <= 5
    rendered_lines = rendered.splitlines()
    for heading in ("相片所見", "初步風險級別", "主要風險", "建議", "需確認事項", "負責跟進", "來源 / 限制"):
        assert rendered_lines.count(heading) == 1


def test_sample_grinder_summary_focuses_only_on_supported_hot_work(monkeypatch, tmp_path):
    image_path = tmp_path / "site-photo.jpg"
    image_path.write_bytes(b"fixture")
    monkeypatch.setattr(
        "utils.image_understanding.analyze_image_with_vision",
        lambda *_args, **_kwargs: _sample_vision_result(),
    )
    result = analyze_image(
        image_path,
        ocr_data=OCRResult(text="", confidence=0.35, metadata={"ocr_status": "OCR_FAILED"}),
    )
    rendered = render_concise_image_summary(result)

    for expected in ("火花", "磨機", "防火", "PPE"):
        assert expected in rendered
    for unsupported in ("棚架", "高空工作", "氣樽", "安全帶", "護欄", "踢腳板"):
        assert unsupported not in rendered


def test_upload_ui_uses_separate_ocr_and_visual_status_copy():
    app_root = Path(__file__).resolve().parents[1]
    upload_page = (app_root / "pages" / "1_Upload.py").read_text(encoding="utf-8")
    assert "未偵測到清晰文字；地盤相片主要會使用 AI 視覺或現場描述作分析。" in upload_page
    assert "文字偵測：" in upload_page
    assert "OCR 文字：" not in upload_page
    assert "視覺分析：已根據可見內容分析" in upload_page
    assert 'if evidence_context.get("has_visual_analysis") and visual_confidence > 0:' in upload_page
