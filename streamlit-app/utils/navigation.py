"""Shared bilingual navigation for the primary AICOS workflows."""

from __future__ import annotations

import streamlit as st


LANGUAGE_OPTIONS = ("繁體中文", "English")
LANGUAGE_KEY = "aicos_navigation_language"
LANGUAGE_WIDGET_KEY = "_aicos_navigation_language_widget"

PRIMARY_PAGES = (
    ("workspace", "pages/0_AICOS_Workspace.py"),
    ("upload", "pages/1_Upload.py"),
    ("ask", "pages/10_Ask_AICOS.py"),
    ("records", "pages/11_Records.py"),
    ("report", "pages/2_Report.py"),
    ("history", "pages/3_History.py"),
    ("dashboard", "pages/7_Project_Dashboard.py"),
    ("risk", "pages/8_Risk_Center.py"),
    ("actions", "pages/9_Action_Tracker.py"),
)

SECONDARY_PAGES = (
    ("home", "app.py"),
    ("memory", "pages/6_Memory_Manager.py"),
    ("translate", "pages/5_Translate.py"),
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


def _store_language_choice() -> None:
    st.session_state[LANGUAGE_KEY] = st.session_state[LANGUAGE_WIDGET_KEY]


def render_navigation_links() -> str:
    """Render one consistent sidebar navigation and return its language."""
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] [data-baseweb="select"] * {
            color: #1a3a5c !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    saved_language = st.session_state.get(LANGUAGE_KEY, LANGUAGE_OPTIONS[0])
    if saved_language not in LANGUAGE_OPTIONS:
        saved_language = LANGUAGE_OPTIONS[0]
    st.session_state[LANGUAGE_WIDGET_KEY] = saved_language
    language = st.selectbox(
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
