"""圖紙分析 — PDF／圖片圖紙分析及 CAD/BIM 交接（Phase 5.10F）。"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(APP_ROOT.parent / ".env")
except ImportError:
    pass

from utils.drawing_analyzer import analyze_drawing
from utils.drawing_integration import save_drawing_analysis
from utils.drawing_models import (
    ACTION_TYPE_LABELS_ZH,
    DISCIPLINE_LABELS_ZH,
    DRAWING_DISCIPLINES,
    PAGE_TYPE_LABELS_ZH,
)
from utils.file_loader import save_uploaded_file
from utils.logo_helper import sidebar_logo
from utils.navigation import render_navigation_links
from utils.ui_components import compact_link_row, page_header, render_product_footer


st.set_page_config(page_title="圖紙分析", page_icon="📐", layout="wide")

DEPTH_LABELS = {"quick": "快速", "standard": "標準", "detailed": "詳細"}
TEAM_LABELS = {"cad": "CAD", "bim": "BIM", "both": "CAD／BIM"}
PRIORITY_LABELS = {"low": "低", "medium": "中", "high": "高", "urgent": "緊急"}
INGEST_LABELS = {
    "selectable_text": "已讀取圖紙文字",
    "ocr": "已透過 OCR 讀取文字",
    "image": "圖片圖紙",
    "image_only": "圖片圖紙（未抽取文字）",
    "metadata_only": "僅基本資料（未能抽取文字）",
    "unsupported": "不支援的檔案",
    "unknown": "未知",
}
_ALLOWED = {".pdf", ".jpg", ".jpeg", ".png"}


with st.sidebar:
    sidebar_logo()
    st.markdown("---")
    render_navigation_links()

page_header("圖紙分析", "上載 PDF 或圖片圖紙，產生問題清單及 CAD/BIM 交接事項。", "📐")
compact_link_row((
    ("pages/1_Upload.py", "📤 上載相片／文件"),
    ("pages/11_Records.py", "🗂️ 查看記錄"),
    ("pages/10_Ask_AICOS.py", "💬 問 AICOS"),
))

if st.button("清除／重設", key="clear_drawing"):
    st.session_state.pop("drawing_result", None)
    st.rerun()

with st.container(border=True):
    st.markdown("#### 圖紙分析設定")
    with st.form("drawing_form"):
        uploaded = st.file_uploader(
            "上載圖紙（PDF／JPG／PNG）",
            type=["pdf", "jpg", "jpeg", "png"],
            accept_multiple_files=False,
        )
        col_a, col_b = st.columns(2)
        with col_a:
            project_ref = st.text_input("項目編號（選填）", placeholder="例如：BW-001", key="drawing_project")
            discipline_options = [""] + sorted(d for d in DRAWING_DISCIPLINES if d != "unknown")
            discipline_hint = st.selectbox(
                "專業範疇提示（選填）",
                discipline_options,
                format_func=lambda value: DISCIPLINE_LABELS_ZH.get(value, value) if value else "自動判斷",
                key="drawing_discipline",
            )
        with col_b:
            page_limit = st.number_input("分析頁數上限", min_value=1, max_value=20, value=12, step=1, key="drawing_pages")
            depth = st.selectbox(
                "分析深度",
                list(DEPTH_LABELS),
                index=1,
                format_func=DEPTH_LABELS.get,
                key="drawing_depth",
            )
        description = st.text_area("圖紙說明（選填）", placeholder="例如：地下層建築平面圖一套", key="drawing_desc", height=80)
        submitted = st.form_submit_button("開始分析", type="primary", use_container_width=True)

if submitted:
    if not uploaded:
        st.error("請先上載圖紙檔案。")
    elif Path(uploaded.name).suffix.lower() not in _ALLOWED:
        st.error("只支援 PDF、JPG 或 PNG 圖紙。")
    else:
        with st.spinner("AICOS 正在分析圖紙並整理 CAD/BIM 交接事項…"):
            try:
                saved_path = save_uploaded_file(uploaded)
                result = analyze_drawing(
                    saved_path,
                    project_ref=(project_ref or None),
                    description=(description or None),
                    discipline_hint=(discipline_hint or None),
                    file_name=uploaded.name,
                    max_pages=int(page_limit),
                    depth=depth,
                )
                links = save_drawing_analysis(result.document)
                st.session_state["drawing_result"] = {
                    "document": result.document.to_dict(),
                    "pages": [page.to_dict() for page in result.pages],
                    "memory_id": links.get("memory_id"),
                    "followups": len(links.get("followups") or []),
                }
            except Exception:
                st.session_state["drawing_result"] = {"error": True}

result = st.session_state.get("drawing_result")
if result and result.get("error"):
    st.error("分析圖紙時發生問題，請改用較清晰的 PDF 或圖片再試一次。")
elif result:
    document = result["document"]
    pages = result["pages"]

    st.divider()
    st.markdown("### 文件概覽")
    overview = st.columns(4)
    overview[0].metric("分析頁數", document.get("analyzed_page_count", 0))
    overview[1].metric("總頁數", document.get("page_count", 0))
    overview[2].metric("CAD/BIM 交接", len(document.get("handoff_items", [])))
    overview[3].metric("待確認問題", len(document.get("drawing_issues", [])))
    disc = "、".join(DISCIPLINE_LABELS_ZH.get(d, d) for d in document.get("disciplines", [])) or "未能確定"
    types = "、".join(PAGE_TYPE_LABELS_ZH.get(t, t) for t in document.get("page_types", []) if t != "unknown") or "未能分類"
    st.write(document.get("summary", ""))
    st.caption(f"涵蓋專業：{disc} · 圖紙類型：{types} · 讀取方式：{INGEST_LABELS.get(document.get('ingestion_status'), '未知')}")
    if result.get("memory_id"):
        st.success(f"已儲存為工程記憶，並建立 {result.get('followups', 0)} 項跟進事項。")

    st.markdown("### 圖紙頁面摘要")
    if not pages:
        st.info("未能由此檔案抽取可分析的頁面。")
    for page in pages:
        ptype = PAGE_TYPE_LABELS_ZH.get(page.get("page_type"), page.get("page_type"))
        pdisc = DISCIPLINE_LABELS_ZH.get(page.get("discipline"), page.get("discipline"))
        header = f"第 {page.get('page_number')} 頁 · {ptype} · {pdisc}"
        with st.expander(header):
            meta = st.columns(4)
            meta[0].markdown(f"**圖紙編號**  \n{page.get('drawing_number') or '未標示'}")
            meta[1].markdown(f"**比例**  \n{page.get('scale') or '未標示'}")
            meta[2].markdown(f"**修訂**  \n{page.get('revision') or '未標示'}")
            meta[3].markdown(f"**判斷信心**  \n{int(round(float(page.get('classification_confidence') or 0) * 100))}%")
            if page.get("sheet_title"):
                st.caption("圖紙名稱：" + page["sheet_title"])
            if page.get("drawing_issues"):
                st.markdown("**待確認：** " + "；".join(page["drawing_issues"]))
            if page.get("missing_information"):
                st.markdown("**缺資料：** " + "；".join(page["missing_information"]))
            if page.get("coordination_flags"):
                st.markdown("**協調提示：** " + "；".join(page["coordination_flags"]))

    st.markdown("### 問題與待確認")
    issues = document.get("drawing_issues", [])
    missing = document.get("missing_information", [])
    coord = document.get("coordination_flags", [])
    if not (issues or missing or coord):
        st.info("未發現明顯問題；仍建議由相關工程師覆核。")
    if issues:
        st.markdown("**圖紙問題**")
        for item in issues:
            st.markdown(f"- {item}")
    if missing:
        st.markdown("**待補資料**")
        for item in missing:
            st.markdown(f"- {item}")
    if coord:
        st.markdown("**跨專業協調**")
        for item in coord:
            st.markdown(f"- {item}")

    st.markdown("### CAD/BIM 交接清單")
    handoff = document.get("handoff_items", [])
    if not handoff:
        st.info("暫無 CAD/BIM 交接事項。")
    for item in handoff:
        team = TEAM_LABELS.get(item.get("target_team"), item.get("target_team"))
        action = ACTION_TYPE_LABELS_ZH.get(item.get("action_type"), item.get("action_type"))
        priority = PRIORITY_LABELS.get(item.get("priority"), item.get("priority"))
        page_hint = f"（第 {item.get('page_number')} 頁）" if item.get("page_number") else ""
        with st.expander(f"[{team}｜{action}｜優先：{priority}] {item.get('title')}{page_hint}"):
            st.write(item.get("description") or "")
            if item.get("references"):
                st.caption("參考：" + "、".join(item["references"]))

    st.markdown("### 分析依據")
    basis_lines = [
        f"圖紙讀取方式：{INGEST_LABELS.get(document.get('ingestion_status'), '未知')}",
        f"分析深度：{DEPTH_LABELS.get(document.get('analysis_depth'), document.get('analysis_depth'))}",
        "AI 視覺輔助：" + ("已使用" if document.get("vision_used") else "未使用（以文字及標題欄判斷）"),
        f"已分析 {document.get('analyzed_page_count', 0)} 頁，產生 {len(handoff)} 項交接事項。",
    ]
    for line in basis_lines:
        st.markdown(f"- {line}")
    st.caption("圖紙分析為輔助參考，最終須由合資格人員及 CAD/BIM 團隊覆核。")

    with st.expander("技術狀態", expanded=False):
        st.caption(f"文件編號：{document.get('document_id')}")
        st.caption(f"讀取狀態：{document.get('ingestion_status')}")
        notes = document.get("technical_notes") or []
        if notes:
            for note in notes:
                st.caption("· " + str(note))
        else:
            st.caption("沒有額外技術備註。")

render_product_footer()
