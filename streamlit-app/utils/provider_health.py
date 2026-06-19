"""Secret-safe capability health for text, vision, and web providers."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any


TEXT_PROVIDERS = (
    ("GEMINI_API_KEY", "Gemini"),
    ("DEEPSEEK_API_KEY", "DeepSeek"),
    ("ANTHROPIC_API_KEY", "Anthropic"),
    ("OPENAI_API_KEY", "OpenAI"),
)
VISION_PROVIDERS = (
    ("GEMINI_API_KEY", "Gemini Vision"),
    ("GOOGLE_API_KEY", "Gemini Vision"),
    ("ANTHROPIC_API_KEY", "Anthropic Vision"),
)
WEB_PROVIDERS = (
    ("TAVILY_API_KEY", "Tavily"),
    ("BRAVE_SEARCH_API_KEY", "Brave"),
)
CHECKED_SECRET_NAMES = tuple(dict.fromkeys(
    key for key, _ in (*TEXT_PROVIDERS, *VISION_PROVIDERS, *WEB_PROVIDERS)
))


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
    secret_presence: dict[str, dict[str, bool]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def get_secret_value(name: str, secrets: Mapping[str, Any] | None = None) -> str | None:
    """Read one internal credential from environment or Streamlit Secrets.

    Callers may use the value to contact the configured service, but must never
    render, log, persist, or include it in diagnostics.
    """
    env_value = str(os.getenv(name, "") or "").strip()
    if env_value:
        return env_value
    secret_store = _secret_store(secrets)
    try:
        value = str(secret_store.get(name, "") or "").strip()
    except Exception:
        return None
    return value or None


def get_provider_health(secrets: Mapping[str, Any] | None = None) -> ProviderHealth:
    secret_store = _secret_store(secrets)
    text_label = _first_configured(TEXT_PROVIDERS, secret_store)
    vision_label = _first_configured(VISION_PROVIDERS, secret_store)
    web_label = _first_configured(WEB_PROVIDERS, secret_store)
    presence = {
        name: {
            "environment": bool(str(os.getenv(name, "") or "").strip()),
            "streamlit_secrets": _store_has_value(secret_store, name),
        }
        for name in CHECKED_SECRET_NAMES
    }
    notes = [
        f"文字服務：{text_label or '未設定'}",
        f"視覺服務：{vision_label or '未設定'}",
        f"網上搜尋：{web_label or '未設定'}",
    ]
    for name, status in presence.items():
        notes.append(
            f"{name}：環境變數 {'有' if status['environment'] else '無'} · "
            f"Cloud Secrets {'有' if status['streamlit_secrets'] else '無'}"
        )
    if any(item["environment"] and not item["streamlit_secrets"] for item in presence.values()):
        notes.append("本機 .env 與 Streamlit Cloud Secrets 是分開的；雲端需在 Secrets 設定。")
    return ProviderHealth(
        text_llm_available=bool(text_label),
        text_llm_provider_label=text_label,
        vision_available=bool(vision_label),
        vision_provider_label=vision_label,
        web_search_available=bool(web_label),
        web_search_provider_label=web_label,
        fallback_mode=not bool(text_label),
        user_message=" ".join((
            "文字回答：已啟用" if text_label else "文字回答：使用本機備用模式",
            "AI 視覺：已啟用" if vision_label else "AI 視覺：未設定",
            "網上搜尋：已啟用" if web_label else "網上搜尋：未設定",
        )),
        technical_notes=notes,
        secret_presence=presence,
    )


def technical_diagnostics_enabled(secrets: Mapping[str, Any] | None = None) -> bool:
    """Gate provider labels and secret-presence diagnostics behind an admin flag."""
    value = str(get_secret_value("AICOS_ADMIN_DIAGNOSTICS", secrets) or "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _first_configured(options, secrets: Mapping[str, Any]) -> str:
    return next((label for key, label in options if get_secret_value(key, secrets)), "")


def _secret_store(secrets: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if secrets is not None:
        return secrets
    try:
        import streamlit as st

        return st.secrets
    except Exception:
        return {}


def _store_has_value(secrets: Mapping[str, Any], name: str) -> bool:
    try:
        return bool(str(secrets.get(name, "") or "").strip())
    except Exception:
        return False
