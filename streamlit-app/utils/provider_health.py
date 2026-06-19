"""Secret-safe capability health for text, vision, and web providers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .service_readiness import get_runtime_secret


@dataclass
class ProviderHealth:
    text_llm_available: bool
    text_llm_provider_label: str
    vision_available: bool
    vision_provider_label: str
    web_search_available: bool
    web_search_provider_label: str
    fallback_mode: bool
    user_message: str
    technical_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def get_provider_health(secrets=None) -> ProviderHealth:
    text_label = _first_configured((
        ("GEMINI_API_KEY", "Gemini"),
        ("DEEPSEEK_API_KEY", "DeepSeek"),
        ("ANTHROPIC_API_KEY", "Anthropic"),
        ("OPENAI_API_KEY", "OpenAI"),
    ), secrets)
    vision_label = _first_configured((
        ("GEMINI_API_KEY", "Gemini Vision"),
        ("GOOGLE_API_KEY", "Gemini Vision"),
        ("ANTHROPIC_API_KEY", "Anthropic Vision"),
    ), secrets)
    web_label = _first_configured((
        ("TAVILY_API_KEY", "Tavily"),
        ("BRAVE_SEARCH_API_KEY", "Brave"),
    ), secrets)
    text_available = bool(text_label)
    normal = " ".join((
        "文字回答：已啟用" if text_available else "文字回答：使用本機備用模式",
        "AI 視覺：已啟用" if vision_label else "AI 視覺：未設定",
        "網上搜尋：已啟用" if web_label else "網上搜尋：未設定",
    ))
    notes = [
        f"文字 LLM：{text_label or '未設定'}",
        f"視覺：{vision_label or '未設定'}",
        f"網上搜尋：{web_label or '未設定'}",
    ]
    return ProviderHealth(
        text_llm_available=text_available,
        text_llm_provider_label=text_label,
        vision_available=bool(vision_label),
        vision_provider_label=vision_label,
        web_search_available=bool(web_label),
        web_search_provider_label=web_label,
        fallback_mode=not text_available,
        user_message=normal,
        technical_notes=notes,
    )


def _first_configured(options, secrets) -> str:
    return next((label for key, label in options if get_runtime_secret(key, secrets)), "")
