"""Shared bilingual navigation for the primary AICOS workflows."""

from __future__ import annotations

import streamlit as st


LANGUAGE_OPTIONS = ("繁體中文", "English")
DEFAULT_LANGUAGE = LANGUAGE_OPTIONS[0]
LANGUAGE_KEY = "aicos_navigation_language"
LANGUAGE_WIDGET_KEY = "_aicos_navigation_language_widget"

SIDEBAR_STYLE_CSS = """
<style>
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #102a43 0%, #0b2035 100%) !important;
    border-right: 1px solid #294d6b;
}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding-top: .65rem;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] summary,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: #eef5fb !important;
}
[data-testid="stSidebar"] img {
    display: block;
    width: min(100%, 180px) !important;
    margin: 0 auto .35rem auto;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a {
    color: #edf5fb !important;
    border-radius: 9px;
    padding: .48rem .62rem;
    margin: .08rem 0;
    text-decoration: none;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
    background: rgba(255, 255, 255, .10) !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] {
    background: #d4ad4d !important;
    color: #102a43 !important;
    font-weight: 700;
    box-shadow: inset 3px 0 0 #fff3c4;
}
[data-testid="stSidebar"] [data-testid="stExpander"] {
    border-color: rgba(255, 255, 255, .18);
    border-radius: 9px;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: #f7fbff !important;
    border-color: #7997af !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] span,
[data-testid="stSidebar"] [data-baseweb="select"] input {
    color: #102a43 !important;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(255, 255, 255, .18) !important;
    margin: .7rem 0;
}
</style>
"""

PRIMARY_PAGES = (
    ("workspace", "pages/0_AICOS_Workspace.py"),
    ("records", "pages/11_Records.py"),
    ("report", "pages/2_Report.py"),
    ("history", "pages/3_History.py"),
    ("dashboard", "pages/7_Project_Dashboard.py"),
    ("risk", "pages/8_Risk_Center.py"),
    ("actions", "pages/9_Action_Tracker.py"),
)

SECONDARY_PAGES = (
    ("upload", "pages/1_Upload.py"),
    ("ask", "pages/10_Ask_AICOS.py"),
    ("drawing", "pages/12_Drawing_Analysis.py"),
    ("translate", "pages/5_Translate.py"),
    ("memory", "pages/6_Memory_Manager.py"),
    ("home", "app.py"),
    ("about", "pages/4_About.py"),
)

_LABELS = {
    "zh": {
        "section": "主要功能",
        "more": "更多工具",
        "workspace": "🏗️ AICOS 工作台",
        "home": "🏠 首頁",
        "upload": "📤 上載分析",
        "ask": "💬 問 AICOS",
        "drawing": "📐 圖紙分析",
        "records": "🗂️ 地盤記錄",
        "report": "📄 分析報告",
        "history": "📜 歷史紀錄",
        "dashboard": "📊 工程總覽",
        "risk": "⚠️ 風險中心",
        "actions": "✅ 行動追蹤",
        "memory": "🧠 工程記憶管理",
        "translate": "📑 文件翻譯與轉換",
        "about": "ℹ️ 關於 Buildway Tech",
    },
    "en": {
        "section": "Primary workflows",
        "more": "More tools",
        "workspace": "🏗️ AICOS Workspace",
        "home": "🏠 Home",
        "upload": "📤 Upload Analysis",
        "ask": "💬 Ask AICOS",
        "drawing": "📐 Drawing Analysis",
        "records": "🗂️ Site Records",
        "report": "📄 Analysis Report",
        "history": "📜 History",
        "dashboard": "📊 Project Dashboard",
        "risk": "⚠️ Risk Center",
        "actions": "✅ Action Tracker",
        "memory": "🧠 Project Memory",
        "translate": "📑 Document Translation",
        "about": "ℹ️ About Buildway Tech",
    },
}


def navigation_labels(language: str) -> dict[str, str]:
    return dict(_LABELS["en" if language == "English" else "zh"])


def _resolve_language(state) -> str:
    """Safely initialise, validate and persist the navigation language.

    Operates on a session-state mapping so it works even on a direct route load
    where neither the stored key nor the widget key exists yet (the Streamlit
    Cloud crash this guards against). Always returns a supported language and
    keeps Traditional Chinese as the default. Must run *before* the language
    widget is instantiated, since it writes the widget key.
    """
    if LANGUAGE_KEY not in state:
        state[LANGUAGE_KEY] = DEFAULT_LANGUAGE
    if LANGUAGE_WIDGET_KEY not in state:
        state[LANGUAGE_WIDGET_KEY] = state.get(LANGUAGE_KEY, DEFAULT_LANGUAGE)
    selected = state.get(LANGUAGE_WIDGET_KEY, state.get(LANGUAGE_KEY, DEFAULT_LANGUAGE))
    if selected not in LANGUAGE_OPTIONS:
        selected = DEFAULT_LANGUAGE
    state[LANGUAGE_KEY] = selected
    state[LANGUAGE_WIDGET_KEY] = selected
    return selected


def _store_language_choice() -> None:
    """on_change callback: mirror the widget choice into the persistent key.

    Reads defensively (``.get``) so a missing widget key never raises, and only
    writes the non-widget key -- writing the widget key inside its own callback
    is not allowed by Streamlit.
    """
    selected = st.session_state.get(LANGUAGE_WIDGET_KEY, st.session_state.get(LANGUAGE_KEY, DEFAULT_LANGUAGE))
    if selected not in LANGUAGE_OPTIONS:
        selected = DEFAULT_LANGUAGE
    st.session_state[LANGUAGE_KEY] = selected


def render_navigation_links() -> str:
    """Render one consistent sidebar navigation and return its language."""
    st.markdown(SIDEBAR_STYLE_CSS, unsafe_allow_html=True)
    language = _resolve_language(st.session_state)
    st.selectbox(
        "語言 / Language",
        LANGUAGE_OPTIONS,
        key=LANGUAGE_WIDGET_KEY,
        on_change=_store_language_choice,
    )
    labels = navigation_labels(language)
    st.caption(labels["section"])
    for label_key, page_path in PRIMARY_PAGES:
        st.page_link(page_path, label=labels[label_key])
    with st.expander(labels["more"], expanded=False):
        for label_key, page_path in SECONDARY_PAGES:
            st.page_link(page_path, label=labels[label_key])
    return language
