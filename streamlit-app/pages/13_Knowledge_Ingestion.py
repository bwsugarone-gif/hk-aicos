"""知識匯入 — 上載 PDF／文件，抽取文字並建立知識來源及 RAG 片段（Phase 6.4）。"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from utils.file_loader import save_uploaded_file
from utils.knowledge_ingestion import ingest_document
from utils.logo_helper import sidebar_logo
from utils.navigation import render_navigation_links
from utils.ui_components import compact_link_row, page_header, render_product_footer


st.set_page_config(page_title="知識匯入", page_icon="📚", layout="wide")

_ALLOWED = {".pdf", ".txt", ".md", ".docx", ".xlsx"}

with st.sidebar:
    sidebar_logo()
    st.markdown("---")
    render_navigation_links()

page_header("知識匯入", "上載 PDF 或文件，抽取文字並建立可搜尋的知識來源及 RAG 片段。", "📚")
compact_link_row((
    ("pages/11_Records.py", "🗂️ 查看記錄"),
    ("pages/10_Ask_AICOS.py", "💬 問 AICOS"),
    ("pages/12_Drawing_Analysis.py", "📐 圖紙分析"),
))

if st.button("清除／重設", key="clear_ingestion"):
    st.session_state.pop("ingestion_result", None)
    st.rerun()

with st.container(border=True):
    st.markdown("#### 匯入設定")
    with st.form("knowledge_ingestion_form"):
        uploaded = st.file_uploader(
            "上載文件（PDF／TXT／MD／DOCX／XLSX）",
            type=["pdf", "txt", "md", "docx", "xlsx"],
            accept_multiple_files=False,
        )
        col_a, col_b = st.columns(2)
        with col_a:
            project_ref = st.text_input("項目編號（選填）", placeholder="例如：BW-001", key="ingest_project")
        with col_b:
            tags_raw = st.text_input("標籤（以逗號分隔，選填）", placeholder="例如：安全, 熱工, 消防", key="ingest_tags")
        description = st.text_area("文件說明（選填）", placeholder="例如：地盤安全作業指引第三版", key="ingest_desc", height=80)
        submitted = st.form_submit_button("開始匯入", type="primary", use_container_width=True)

if submitted:
    if not uploaded:
        st.error("請先上載文件。")
    elif Path(uploaded.name).suffix.lower() not in _ALLOWED:
        st.error("只支援 PDF、TXT、MD、DOCX 或 XLSX 文件。")
    else:
        with st.spinner("AICOS 正在抽取文字並建立知識來源…"):
            try:
                saved_path = save_uploaded_file(uploaded)
                tags = [tag.strip() for tag in (tags_raw or "").replace("，", ",").split(",") if tag.strip()]
                result = ingest_document(
                    file_path=saved_path,
                    original_file_name=uploaded.name,
                    project_ref=(project_ref or None),
                    tags=tags,
                    description=(description or ""),
                )
                st.session_state["ingestion_result"] = result.to_public_dict()
            except Exception:
                st.session_state["ingestion_result"] = {"error": True}

result = st.session_state.get("ingestion_result")
if result and result.get("error"):
    st.error("匯入文件時發生問題，請改用較清晰的 PDF 或補充文字版本再試一次。")
elif result:
    st.divider()
    st.markdown("### 匯入結果")
    if result.get("metadata_only"):
        st.warning(
            "未能抽取清晰文字，已建立 metadata-only 知識來源；"
            "如需全文搜尋，請使用 OCR 版本或補充文字。"
        )
    else:
        st.success("檔案已登記 · 原檔儲存：本機暫存 / Drive-ready · 已建立知識來源及 RAG 片段。")

    cols = st.columns(4)
    cols[0].metric("抽取字元", int(result.get("extracted_chars", 0) or 0))
    cols[1].metric("抽取頁數", int(result.get("pages_extracted", 0) or 0))
    cols[2].metric("RAG 片段", int(result.get("chunk_count", 0) or 0))
    cols[3].metric("知識來源", 1)
    st.caption(f"知識來源編號：{result.get('source_id', '—')}")

    extra_warnings = [w for w in (result.get("warnings") or []) if w]
    for warning in extra_warnings:
        st.caption("· " + warning)

    st.markdown("可於「記錄」頁的「知識來源」、「RAG 片段」及「全部記錄搜尋」查閱及搜尋此文件，或於「問 AICOS」就文件內容提問。")
    compact_link_row((
        ("pages/11_Records.py", "🗂️ 前往記錄"),
        ("pages/10_Ask_AICOS.py", "💬 就此文件提問"),
    ))

render_product_footer()
