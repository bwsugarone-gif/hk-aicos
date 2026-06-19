import json
from pathlib import Path

from utils import vision_client
from utils.provider_health import get_provider_health


APP_ROOT = Path(__file__).resolve().parents[1]
PROVIDER_KEYS = (
    "GEMINI_API_KEY", "GOOGLE_API_KEY", "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY", "TAVILY_API_KEY", "BRAVE_SEARCH_API_KEY",
)


def _clear_providers(monkeypatch):
    for key in PROVIDER_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_provider_health_no_key_uses_fallback_without_provider_names(monkeypatch):
    _clear_providers(monkeypatch)
    health = get_provider_health({})

    assert health.text_llm_available is False
    assert health.vision_available is False
    assert health.web_search_available is False
    assert health.fallback_mode is True
    assert "文字回答：使用本機備用模式" in health.user_message
    for provider in ("Gemini", "DeepSeek", "Anthropic", "Tavily", "Brave"):
        assert provider not in health.user_message


def test_provider_health_gemini_and_deepseek_are_detected_only_in_technical_notes(monkeypatch):
    _clear_providers(monkeypatch)
    gemini = get_provider_health({"GEMINI_API_KEY": "fixture"})
    deepseek = get_provider_health({"DEEPSEEK_API_KEY": "fixture"})

    assert gemini.text_llm_available and gemini.vision_available
    assert deepseek.text_llm_available
    assert "Gemini" in " ".join(gemini.technical_notes)
    assert "DeepSeek" in " ".join(deepseek.technical_notes)
    assert "Gemini" not in gemini.user_message
    assert "DeepSeek" not in deepseek.user_message


class _FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")


def test_gemini_vision_mocked_http_returns_cutting_sparks(monkeypatch, tmp_path):
    image = tmp_path / "site.jpg"
    image.write_bytes(b"fixture-image")
    _clear_providers(monkeypatch)
    response_text = json.dumps({
        "category": "cutting_grinding",
        "confidence": 0.88,
        "extracted_text": "",
        "evidence_items": ["可見磨機切割金屬", "切割位置可見火花"],
        "observations": ["工人使用磨機切割", "可見火花"],
        "risks": ["火花可能接觸附近物料"],
        "unsupported_assumptions": [],
        "needs_manual_review": True,
    }, ensure_ascii=False)
    payload = {"candidates": [{"content": {"parts": [{"text": response_text}]}}]}
    monkeypatch.setattr(vision_client.urllib.request, "urlopen", lambda *_args, **_kwargs: _FakeResponse(payload))

    result = vision_client.analyze_image_with_vision(image, gemini_api_key="fixture-key")

    assert result["status"] == "success"
    assert result["provider"] == "gemini"
    assert result["category"] == "cutting_grinding"
    assert any("火花" in item for item in result["evidence_items"])
    encoded = json.dumps(result, ensure_ascii=False)
    for unsupported in ("棚架", "氣樽", "高空工作", "安全帶"):
        assert unsupported not in encoded


def test_gemini_vision_unavailable_and_error_are_safe(monkeypatch, tmp_path):
    image = tmp_path / "site.jpg"
    image.write_bytes(b"fixture-image")
    _clear_providers(monkeypatch)
    unavailable = vision_client.analyze_image_with_vision(image)
    assert unavailable["status"] == "not_configured"
    assert unavailable["performed"] is False

    monkeypatch.setattr(
        vision_client.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("network fixture-key failed")),
    )
    failed = vision_client.analyze_image_with_vision(image, gemini_api_key="fixture-key")
    assert failed["status"] == "error"
    assert failed["performed"] is False
    assert "fixture-key" not in failed.get("error", "")


def test_upload_uses_provider_neutral_vision_copy():
    source = (APP_ROOT / "pages" / "1_Upload.py").read_text(encoding="utf-8")
    assert "AI 視覺：已啟用" in source
    assert "AI 視覺暫時未能完成；已改用現場描述及人工覆核模式。" in source
    assert "get_provider_health()" in source
