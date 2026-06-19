"""Provider-neutral readiness checks for AICOS user interfaces."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any


TEXT_LLM_KEYS = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
)
VISION_KEYS = ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")
WEB_SEARCH_KEYS = ("TAVILY_API_KEY", "BRAVE_SEARCH_API_KEY")


def get_runtime_secret(name: str, secrets: Mapping[str, Any] | None = None) -> str:
    """Read one configured value without logging names, values, or failures."""
    value = os.getenv(name, "").strip()
    if value:
        return value
    if secrets is None:
        try:
            import streamlit as st

            secrets = st.secrets
        except Exception:
            secrets = {}
    try:
        return str(secrets.get(name, "") or "").strip()
    except Exception:
        return ""


def get_secret_value(name: str, secrets: Mapping[str, Any] | None = None) -> str | None:
    """Compatibility alias for internal callers that need one configured value."""
    return get_runtime_secret(name, secrets) or None


def get_service_readiness(secrets: Mapping[str, Any] | None = None) -> dict[str, bool]:
    """Return capability status only; never expose a selected provider."""
    return {
        "text_answer": any(get_runtime_secret(name, secrets) for name in TEXT_LLM_KEYS),
        "ai_vision": any(get_runtime_secret(name, secrets) for name in VISION_KEYS),
        "web_search": any(get_runtime_secret(name, secrets) for name in WEB_SEARCH_KEYS),
    }
