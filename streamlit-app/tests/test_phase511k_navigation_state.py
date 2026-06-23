"""Phase 5.11K — direct-route navigation language session-state hotfix.

Guards the Streamlit Cloud crash where opening a route directly (e.g.
``/Drawing_Analysis``) hit a ``KeyError`` because the language widget key was not
initialised yet. The state logic now lives in pure helpers that can be exercised
with a plain dict, no Streamlit runtime required.
"""

from __future__ import annotations

import py_compile
from pathlib import Path

from utils import navigation
from utils.navigation import (
    DEFAULT_LANGUAGE,
    LANGUAGE_KEY,
    LANGUAGE_OPTIONS,
    LANGUAGE_WIDGET_KEY,
    _resolve_language,
    _store_language_choice,
)


APP_ROOT = Path(__file__).resolve().parents[1]
DIRECT_ROUTE_PAGES = (
    "pages/0_AICOS_Workspace.py",
    "pages/12_Drawing_Analysis.py",
    "pages/11_Records.py",
    "pages/10_Ask_AICOS.py",
    "pages/1_Upload.py",
)


def test_default_language_is_traditional_chinese():
    assert DEFAULT_LANGUAGE == "繁體中文"
    assert DEFAULT_LANGUAGE in LANGUAGE_OPTIONS


def test_resolve_language_on_direct_route_without_any_keys():
    # Fresh session (direct route open): neither key present -> must not raise.
    state: dict = {}
    language = _resolve_language(state)
    assert language == DEFAULT_LANGUAGE
    assert state[LANGUAGE_KEY] == DEFAULT_LANGUAGE
    assert state[LANGUAGE_WIDGET_KEY] == DEFAULT_LANGUAGE


def test_resolve_language_without_widget_key_only():
    # Stored language exists but the widget key was never created on this page.
    state = {LANGUAGE_KEY: "English"}
    language = _resolve_language(state)
    assert language == "English"
    assert state[LANGUAGE_WIDGET_KEY] == "English"


def test_resolve_language_persists_widget_selection():
    # A widget selection should persist into the cross-route stored key.
    state = {LANGUAGE_KEY: "繁體中文", LANGUAGE_WIDGET_KEY: "English"}
    language = _resolve_language(state)
    assert language == "English"
    assert state[LANGUAGE_KEY] == "English"


def test_resolve_language_rejects_invalid_value():
    state = {LANGUAGE_WIDGET_KEY: "Français"}
    language = _resolve_language(state)
    assert language == DEFAULT_LANGUAGE
    assert state[LANGUAGE_KEY] == DEFAULT_LANGUAGE


def test_store_language_choice_safe_without_widget_key(monkeypatch):
    # The on_change callback must not raise when the widget key is missing.
    monkeypatch.setattr(navigation.st, "session_state", {})
    _store_language_choice()
    assert navigation.st.session_state[LANGUAGE_KEY] == DEFAULT_LANGUAGE


def test_store_language_choice_mirrors_widget_to_stored_key(monkeypatch):
    monkeypatch.setattr(navigation.st, "session_state", {LANGUAGE_WIDGET_KEY: "English"})
    _store_language_choice()
    assert navigation.st.session_state[LANGUAGE_KEY] == "English"


def test_direct_route_pages_compile():
    for rel in DIRECT_ROUTE_PAGES:
        py_compile.compile(str(APP_ROOT / rel), doraise=True)
