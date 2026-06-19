"""Unified daily workspace for AICOS upload, Q&A, memory, and knowledge."""

from __future__ import annotations

import sys
from collections import Counter
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

from utils.analysis_models import KnowledgeSnippet
from utils.answer_modes import ANSWER_MODE_LABELS, DEFAULT_ANSWER_MODE
from utils.knowledge_search import search_local_knowledge
from utils.knowledge_tracker import build_knowledge_context, list_source_items
from utils.llm_answer_client import safe_answer_question
from utils.logo_helper import sidebar_logo
from utils.navigation import render_navigation_links
from utils.official_sources import SOURCE_MODE_LABELS_ZH, default_source_mode, source_id_for
from utils.search_query_builder import build_hk_official_query
from utils.site_memory import build_memory_context, list_memory_items, save_memory_item
from utils.site_record_store import SiteRecordStore
from utils.web_search_adapter import web_search
from utils.workspace_preview import build_recent_analysis_preview


st.set_page_config(page_title="AICOS 工作台", page_icon="🏗️", layout="wide")

QUESTION_TYPES = {
    "safety": "安全問題",
    "law_regulation": "法例／規例",
    "construction_method": "施工方法",
    "material": "物料",
    "document_search": "文件搜尋",
    "site_followup": "地盤跟進",
    "general": "一般問題",
}
SEARCH_SCOPES = {
    "local_knowledge": "本機知識",
    "uploaded_records": "已上載記錄／AICOS 記憶",
    "web_search": "網上搜尋",
    "all": "全部來源",
}


def _record_context(question: str) -> list[KnowledgeSnippet]:
    contexts = []
    for record in SiteRecordStore().search_records(keyword=question, limit=4):
        contexts.append(
            KnowledgeSnippet(
                title=record.title,
                path=f"地盤記錄 {record.record_id}",
                snippet=record.content_summary,
                score=5.0,
                source_type="uploaded_record",
                source_id=source_id_for(record.record_id, "record"),
                trust_level="uploaded_record",
                provider="site_record_store",
            )
        )
    return contexts


with st.sidebar:
    sidebar_logo()
    st.markdown("---")
    render_navigation_links()

st.title("🏗️ AICOS 工作台")
st.caption("上載地盤相片或文件，向 AICOS 提問，並集中查看工程記憶、知識來源與跟進記錄。")

quick_upload, quick_ask, quick_records = st.columns(3)
with quick_upload:
    st.page_link("pages/1_Upload.py", label="📤 上載分析", use_container_width=True)
with quick_ask:
    st.page_link("pages/10_Ask_AICOS.py", label="💬 問 AICOS", use_container_width=True)
with quick_records:
    st.page_link("pages/11_Records.py", label="🗂️ 地盤記錄", use_container_width=True)

st.divider()
upload_col, ask_col = st.columns(2, gap="large")

with upload_col:
    st.subheader("📤 上載相片／文件")
    st.write("使用完整上載分析流程進行 OCR、圖片判斷及跟進建議。")
    st.page_link("pages/1_Upload.py", label="開啟上載分析", use_container_width=True)
    recent_analysis = st.session_state.get("last_analysis")
    if isinstance(recent_analysis, dict):
        preview = build_recent_analysis_preview(recent_analysis)
        st.markdown("#### 最近分析預覽")
        st.markdown(f"**{preview['file_name']}**")
        st.caption(
            f"{preview['analysis_type']} · 風險：{preview['risk_level']}"
        )
        st.markdown("**相片所見**" if preview["is_image"] else "**分析摘要**")
        for item in preview["observations"][:2]:
            st.markdown(f"- {item}")
        if preview["recommendations"]:
            st.markdown("**建議**")
            for item in preview["recommendations"][:2]:
                st.markdown(f"- {item}")
        if preview["confirmations"]:
            st.markdown("**需確認事項**")
            for item in preview["confirmations"][:2]:
                st.markdown(f"- {item}")
        st.page_link("pages/2_Report.py", label="查看完整分析報告", use_container_width=True)
    else:
        recent_records = SiteRecordStore().list_records(limit=1)
        if recent_records:
            record = recent_records[0]
            st.markdown("#### 最近記錄")
            st.markdown(f"**{record.title}**")
            st.caption(f"{record.created_at[:19].replace('T', ' ')} · {record.status}")
            st.write(record.content_summary[:360])
        else:
            st.info("尚未有最近上載分析；可先上載一張地盤相片或文件。")

with ask_col:
    st.subheader("💬 問 AICOS")
    with st.form("workspace_quick_ask"):
        quick_question = st.text_area(
            "問題",
            height=100,
            placeholder="例如：高空工作現場應先檢查甚麼？",
        )
        question_type = st.selectbox("問題類型", list(QUESTION_TYPES), format_func=QUESTION_TYPES.get)
        search_scope = st.selectbox(
            "搜尋範圍",
            list(SEARCH_SCOPES),
            index=list(SEARCH_SCOPES).index("all"),
            format_func=SEARCH_SCOPES.get,
        )
        answer_mode = st.selectbox(
            "回答模式",
            list(ANSWER_MODE_LABELS),
            index=list(ANSWER_MODE_LABELS).index(DEFAULT_ANSWER_MODE),
            format_func=ANSWER_MODE_LABELS.get,
        )
        project_id = st.text_input("項目編號（選填）", placeholder="例如：BW-001")
        remember_answer = st.checkbox("儲存為 AICOS 問答記憶", value=True)
        quick_submitted = st.form_submit_button("向 AICOS 提問", type="primary", use_container_width=True)

    if quick_submitted:
        if not quick_question.strip():
            st.error("請先輸入問題。")
        else:
            source_mode = default_source_mode(question_type)
            local_contexts: list[KnowledgeSnippet] = []
            web_contexts = []
            if search_scope in {"local_knowledge", "all"}:
                local_contexts.extend(search_local_knowledge(quick_question, limit=4))
            if search_scope in {"uploaded_records", "all"}:
                local_contexts.extend(_record_context(quick_question))
                local_contexts.extend(build_memory_context(quick_question, project_id or None, limit=4))
                local_contexts.extend(build_knowledge_context(quick_question, project_id or None, limit=4))
            if search_scope in {"web_search", "all"}:
                searched_query = build_hk_official_query(quick_question, question_type, source_mode)
                web_response = web_search(searched_query, limit=5, mode=source_mode)
                web_contexts = web_response.results
                st.session_state["ask_web_status"] = web_response.to_dict()
            else:
                st.session_state.pop("ask_web_status", None)

            with st.spinner("AICOS 正在整理現場建議及來源…"):
                response, recovered_from_error = safe_answer_question(
                    question=quick_question,
                    question_type=question_type,
                    search_scope=search_scope,
                    context_snippets=[*local_contexts, *web_contexts],
                    answer_mode=answer_mode,
                )
            if recovered_from_error:
                st.warning("AICOS 暫時未能使用部分搜尋內容，已改用安全的本機後備答案。")
            response_data = response.to_dict()
            st.session_state["workspace_quick_result"] = response_data
            st.session_state["ask_result"] = {
                "question": quick_question,
                "question_type": question_type,
                "search_scope": search_scope,
                "source_mode": source_mode,
                "answer_mode": answer_mode,
                "response": response_data,
            }
            st.session_state["ask_local_sources"] = [item.to_dict() for item in local_contexts]
            st.session_state["ask_web_sources"] = [item.to_dict() for item in web_contexts]
            if remember_answer:
                memory = save_memory_item(
                    memory_type="qa_memory",
                    project_id=project_id,
                    title=f"問 AICOS：{quick_question[:80]}",
                    summary=response.answer[:1200],
                    tags=[question_type, answer_mode],
                    risk_level=response.risk_level,
                    status="answered",
                    related_source_ids=[
                        str(source.get("source_id") or "")
                        for source in response_data.get("sources", [])
                        if source.get("source_id")
                    ],
                    raw_payload={"question": quick_question, "response": response_data},
                )
                st.session_state["workspace_saved_memory_id"] = memory.memory_id

    quick_result = st.session_state.get("workspace_quick_result")
    if isinstance(quick_result, dict):
        st.markdown("#### AICOS 簡短預覽")
        st.markdown(str(quick_result.get("answer") or "")[:1600])
        st.caption(
            f"風險：{str(quick_result.get('risk_level') or 'unknown').upper()} · "
            f"來源：{len(quick_result.get('sources') or [])} · "
            f"回答模式：{ANSWER_MODE_LABELS.get(answer_mode, ANSWER_MODE_LABELS[DEFAULT_ANSWER_MODE])}"
        )
        if st.session_state.get("workspace_saved_memory_id"):
            st.success(f"已儲存問答記憶：{st.session_state['workspace_saved_memory_id']}")
        st.page_link("pages/10_Ask_AICOS.py", label="查看完整答案及來源", use_container_width=True)

st.divider()
st.subheader("🧠 記憶 / Knowledge")
st.caption("Memory 記錄發生過的事情與跟進；Knowledge 登記 SOP、官方指引、文件及未來 RAG 來源。")

filter_col, summary_col = st.columns([1, 2])
with filter_col:
    knowledge_project = st.text_input("按項目篩選", key="workspace_knowledge_project", placeholder="留空顯示全部")
    memory_items = list_memory_items(project_id=knowledge_project or None, limit=8)
    source_items = list_source_items(project_id=knowledge_project or None, limit=8)
    st.metric("最近記憶", len(memory_items))
    st.metric("知識來源", len(source_items))

with summary_col:
    status_counts = Counter(item.status or "未分類" for item in memory_items)
    risk_counts = Counter(item.risk_level or "未分類" for item in memory_items)
    metric_cols = st.columns(3)
    metric_cols[0].metric("待跟進", sum(count for status, count in status_counts.items() if status not in {"resolved", "closed", "answered"}))
    metric_cols[1].metric("高風險記憶", sum(count for risk, count in risk_counts.items() if risk.lower() in {"high", "critical", "urgent", "高"}))
    metric_cols[2].metric("已建立索引", sum(1 for item in source_items if item.indexed_status in {"indexed", "ready"}))
    tags = Counter(tag for item in [*memory_items, *source_items] for tag in item.tags)
    st.markdown("**常用標籤**")
    st.write(" · ".join(f"`{tag}` {count}" for tag, count in tags.most_common(10)) or "尚未有標籤")

memory_tab, source_tab, followup_tab = st.tabs(["最近記憶", "知識來源", "最近跟進"])
with memory_tab:
    if not memory_items:
        st.info("尚未建立 AICOS 記憶。完成問答或儲存圖片分析後便會顯示。")
    for item in memory_items[:5]:
        st.markdown(f"**{item.title}**")
        st.caption(f"{item.memory_type} · {item.created_at[:19].replace('T', ' ')} · {item.status or '未分類'}")
        st.write(item.summary[:300])

with source_tab:
    if not source_items:
        st.info("尚未登記知識來源；Google Drive 欄位已預留，但本階段不會連接 Google API。")
    for item in source_items[:5]:
        st.markdown(f"**{item.title}**")
        st.caption(f"{item.source_type} · {item.storage_provider} · {item.indexed_status}")
        st.write(item.summary[:300])
        if item.google_drive_url:
            st.markdown(f"[開啟 Google Drive 文件]({item.google_drive_url})")

with followup_tab:
    followups = [item for item in memory_items if item.memory_type in {"issue_memory", "followup_memory"}]
    if not followups:
        st.info("目前沒有最近跟進記憶。")
    for item in followups[:5]:
        st.markdown(f"**{item.title}**")
        st.caption(f"風險：{item.risk_level or '未分類'} · 狀態：{item.status or '未分類'}")
        st.write(item.summary[:300])

st.caption("AICOS Knowledge Foundation · 本階段使用本機 JSONL metadata；Google Drive、Supabase 及向量索引只保留未來 adapter 接口。")
