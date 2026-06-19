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
from utils.answer_formatter import format_answer_display
from utils.answer_modes import ANSWER_MODE_LABELS, DEFAULT_ANSWER_MODE
from utils.knowledge_search import search_local_knowledge
from utils.knowledge_tracker import build_knowledge_context, list_source_items
from utils.knowledge_pack_store import build_or_refresh_knowledge_index, read_knowledge_index
from utils.knowledge_retriever import build_knowledge_pack_context, summarize_knowledge_hits
from utils.llm_answer_client import safe_answer_question
from utils.logo_helper import sidebar_logo
from utils.navigation import render_navigation_links
from utils.official_sources import SOURCE_MODE_LABELS_ZH, default_source_mode, source_id_for
from utils.risk_evidence import build_analysis_basis, build_risk_evidence_trace, build_trace_from_analysis
from utils.followup_store import build_followup_context, list_followups, summarize_followups, update_followup_status
from utils.memory_indexer import build_project_memory_context
from utils.project_memory_store import append_memory, summarize_project_memory
from utils.provider_health import get_provider_health
from utils.rag_indexer import build_rag_index_from_knowledge_sources, read_rag_index
from utils.rag_retriever import build_rag_context
from utils.runtime_storage_health import get_runtime_storage_status
from utils.search_query_builder import build_hk_official_query
from utils.service_readiness import get_service_readiness
from utils.site_memory import build_memory_context, list_memory_items, save_memory_item
from utils.site_record_store import SiteRecordStore
from utils.web_search_adapter import web_search
from utils.workspace_preview import build_recent_analysis_preview
from utils.ui_components import (
    compact_link_row,
    page_header,
    render_answer_card,
    render_product_footer,
    render_risk_evidence_trace,
)


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
WORKSPACE_UPLOAD_MAX_BYTES = 50 * 1024 * 1024


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

page_header("AICOS 工作台", "上載地盤相片或文件、向 AICOS 提問，並集中查看工程記憶與跟進。", "🏗️")
compact_link_row((
    ("pages/1_Upload.py", "📤 上載分析"),
    ("pages/10_Ask_AICOS.py", "💬 問 AICOS"),
    ("pages/11_Records.py", "🗂️ 地盤記錄"),
))

provider_health = get_provider_health()
st.caption(provider_health.user_message)
with st.expander("技術狀態", expanded=False):
    for note in provider_health.technical_notes:
        st.caption(note)

st.divider()
upload_col, ask_col = st.columns(2, gap="large")

with upload_col:
    with st.container(border=True):
        st.markdown(
            '<div class="aicos-upload-cta"><strong>📤 上載相片 / 文件</strong>'
            '<p>拖放相片或文件，AICOS 會協助整理相片所見、風險及跟進建議。</p></div>',
            unsafe_allow_html=True,
        )
        if st.button("立即上載分析", type="primary", use_container_width=True):
            st.switch_page("pages/1_Upload.py")
        workspace_file = st.file_uploader(
            "拖放檔案到這裡",
            type=["jpg", "jpeg", "png", "pdf", "docx", "xlsx"],
            accept_multiple_files=False,
            key="workspace_file_uploader",
        )
        if workspace_file is not None:
            if workspace_file.size > WORKSPACE_UPLOAD_MAX_BYTES:
                st.error("檔案超過 50MB，請壓縮或分批上載。")
            else:
                st.session_state["workspace_upload_handoff"] = {
                    "name": workspace_file.name,
                    "size": workspace_file.size,
                    "mime_type": workspace_file.type,
                    "data": workspace_file.getvalue(),
                }
                st.success(f"已收到檔案：{workspace_file.name}；請按「開始分析」。")
                if st.button("開始分析", type="primary", use_container_width=True):
                    st.switch_page("pages/1_Upload.py")
        st.page_link("pages/1_Upload.py", label="前往完整上載頁", use_container_width=True)
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
        recent_trace, recent_basis = build_trace_from_analysis(recent_analysis)
        render_risk_evidence_trace(recent_trace, recent_basis, compact=True)
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
            project_memory_contexts: list[KnowledgeSnippet] = []
            followup_contexts: list[KnowledgeSnippet] = []
            knowledge_pack_contexts: list[KnowledgeSnippet] = []
            rag_contexts: list[KnowledgeSnippet] = []
            if search_scope in {"local_knowledge", "all"}:
                local_contexts.extend(search_local_knowledge(quick_question, limit=4))
                knowledge_pack_contexts = build_knowledge_pack_context(quick_question, limit=4)
                rag_contexts = build_rag_context(quick_question, project_id or None, limit=4)
            if search_scope in {"uploaded_records", "all"}:
                local_contexts.extend(_record_context(quick_question))
                local_contexts.extend(build_memory_context(quick_question, project_id or None, limit=4))
                local_contexts.extend(build_knowledge_context(quick_question, project_id or None, limit=4))
                project_memory_contexts = build_project_memory_context(quick_question, project_id or None, limit=4)
                followup_contexts = build_followup_context(quick_question, project_id or None, limit=4)
            if search_scope in {"web_search", "all"}:
                searched_query = build_hk_official_query(quick_question, question_type, source_mode)
                web_response = web_search(searched_query, limit=5, mode=source_mode)
                web_contexts = web_response.results
                st.session_state["ask_web_status"] = web_response.to_dict()
            else:
                st.session_state.pop("ask_web_status", None)

            with st.spinner("AICOS 正在整理現場建議及來源…"):
                all_contexts = [
                    *local_contexts, *knowledge_pack_contexts, *rag_contexts,
                    *project_memory_contexts, *followup_contexts, *web_contexts,
                ]
                response, recovered_from_error = safe_answer_question(
                    question=quick_question,
                    question_type=question_type,
                    search_scope=search_scope,
                    context_snippets=all_contexts,
                    answer_mode=answer_mode,
                )
            if recovered_from_error:
                st.session_state["workspace_answer_recovered"] = True
            else:
                st.session_state["workspace_answer_recovered"] = False
            response_data = response.to_dict()
            retrieval_counts = {
                "memory": len(project_memory_contexts),
                "followups": len(followup_contexts),
                "knowledge": len(local_contexts) + len(knowledge_pack_contexts),
                "rag": len(rag_contexts),
                "official": sum(1 for item in all_contexts if getattr(item, "trust_level", "") == "official_hk"),
            }
            st.session_state["workspace_quick_result"] = response_data
            st.session_state["ask_result"] = {
                "question": quick_question,
                "question_type": question_type,
                "search_scope": search_scope,
                "source_mode": source_mode,
                "answer_mode": answer_mode,
                "response": response_data,
                "retrieval_counts": retrieval_counts,
                "project_ref": project_id or None,
            }
            st.session_state["ask_local_sources"] = [
                item.to_dict() for item in [
                    *local_contexts, *knowledge_pack_contexts, *rag_contexts,
                    *project_memory_contexts, *followup_contexts,
                ]
            ]
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
                project_memory = append_memory({
                    "source_type": "ask_aicos",
                    "project_ref": project_id or None,
                    "title": f"問 AICOS：{quick_question[:80]}",
                    "summary": response.answer[:2500],
                    "raw_question": quick_question,
                    "answer_summary": response.answer[:1800],
                    "risk_level": response.risk_level,
                    "confidence": response.confidence,
                    "evidence_sources": [item.source_type for item in all_contexts],
                    "tags": [question_type, answer_mode],
                    "status": "resolved",
                    "priority": "high" if response.risk_level in {"high", "critical"} else "medium",
                    "source_route": "/AICOS_Workspace",
                    "metadata": {"retrieval_counts": retrieval_counts},
                })
                st.session_state["workspace_project_memory_id"] = project_memory.memory_id

    quick_result = st.session_state.get("workspace_quick_result")
    if isinstance(quick_result, dict):
        st.markdown("#### AICOS 簡短預覽")
        quick_sources = [item for item in quick_result.get("sources", []) if isinstance(item, dict)]
        quick_question_for_trace = str(
            (st.session_state.get("ask_result") or {}).get("question") or ""
        )
        quick_trace = build_risk_evidence_trace(
            quick_result.get("risk_level", "unknown"),
            question=quick_question_for_trace,
            sources=quick_sources,
        )
        quick_basis = build_analysis_basis(
            sources=quick_sources,
            rules_matched=quick_trace.rules_matched,
        )
        official_titles = [
            str(item.get("source_title") or "").strip()
            for item in quick_sources
            if item.get("trust_level") == "official_hk" and item.get("source_title")
        ]
        quick_warnings = (
            ["部分搜尋內容暫時不可用，已改用安全的本機備用答案。"]
            if st.session_state.get("workspace_answer_recovered") else []
        )
        display = format_answer_display(
            quick_result.get("answer", ""),
            answer_mode=answer_mode,
            risk_level=quick_result.get("risk_level", "unknown"),
            confidence=quick_result.get("confidence", 0.0),
            source_summary=official_titles,
            warnings=quick_warnings,
            source_available=bool(official_titles),
            memory_save_status=(
                f"已儲存問答記憶：{st.session_state['workspace_saved_memory_id']}"
                if st.session_state.get("workspace_saved_memory_id") else ""
            ),
            fallback_used=bool(quick_result.get("fallback_used")),
            risk_trace=quick_trace,
            analysis_basis=quick_basis,
            technical_status=get_service_readiness(),
        )
        render_answer_card(display, compact=True)
        render_risk_evidence_trace(quick_trace, quick_basis, compact=True)
        quick_counts = (st.session_state.get("ask_result") or {}).get("retrieval_counts") or {}
        st.caption(
            f"分析依據：地盤記憶 {int(quick_counts.get('memory', 0))} · "
            f"未完成跟進 {int(quick_counts.get('followups', 0))} · "
            f"知識來源 {int(quick_counts.get('knowledge', 0))} · "
            f"RAG 片段 {int(quick_counts.get('rag', 0))}"
        )
        if not any(int(quick_counts.get(key, 0)) for key in ("memory", "followups", "knowledge", "rag")):
            st.info("目前未找到相關工程記憶或知識來源；以下為一般建議，需由現場負責人覆核。")
        st.page_link("pages/10_Ask_AICOS.py", label="查看完整答案及來源", use_container_width=True)

st.divider()
st.subheader("🧠 工程記憶與跟進")
storage_health = get_runtime_storage_status()
if storage_health.warning_message:
    st.warning(storage_health.warning_message)
project_filter = st.text_input("工程篩選（選填）", key="phase58_project_filter", placeholder="例如：BW-001")
memory_summary = summarize_project_memory(project_filter or None)
followup_summary = summarize_followups(project_filter or None)
knowledge_index = read_knowledge_index()
knowledge_summary = summarize_knowledge_hits(knowledge_index)
rag_chunks = read_rag_index()
dashboard_metrics = st.columns(5)
dashboard_metrics[0].metric("工程記憶", memory_summary.total_records)
dashboard_metrics[1].metric("未完成跟進", followup_summary["open_count"])
dashboard_metrics[2].metric("高風險記憶", memory_summary.high_risk_count)
dashboard_metrics[3].metric("知識來源", knowledge_summary["total"])
dashboard_metrics[4].metric("RAG 片段", len(rag_chunks))

with st.expander("今日 / 最近工程記憶", expanded=True):
    if not memory_summary.recent_records:
        st.caption("尚未有 Phase 5.8 工程記憶。")
    for item in memory_summary.recent_records[:3]:
        st.markdown(f"**{item.title}**")
        st.caption(f"工程：{item.project_ref or '未指定'} · 風險：{item.risk_level or '未分類'} · 狀態：{item.status}")

with st.expander("未完成跟進", expanded=True):
    open_followups = list_followups(project_ref=project_filter or None, limit=5)
    open_followups = [item for item in open_followups if item.status in {"open", "in_progress", "waiting"}]
    if not open_followups:
        st.caption("目前沒有未完成跟進。")
    for item in open_followups:
        st.markdown(f"**[{item.priority.upper()}] {item.title}**")
        st.caption(f"負責：{item.responsible_role or '未指定'} · 時限：{item.due_hint or '待確認'} · 狀態：{item.status}")
        if item.status == "open" and st.button("標記為進行中", key=f"start_followup_{item.followup_id}"):
            update_followup_status(item.followup_id, "in_progress", "由 AICOS 工作台更新")
            st.rerun()

with st.expander("重複風險提示"):
    if not memory_summary.repeated_tags:
        st.caption("尚未偵測到重複風險主題。")
    for tag, count in memory_summary.repeated_tags:
        st.markdown(f"- {tag} 出現 {count} 次")

with st.expander("知識來源狀態"):
    trust_counts = knowledge_summary.get("trust_counts", {})
    st.caption(
        f"官方 {trust_counts.get('official', 0)} · 可信 {trust_counts.get('trusted', 0)} · "
        f"內部 {trust_counts.get('internal', 0)} · 未核實 {trust_counts.get('unverified', 0)}"
    )
    if knowledge_summary.get("last_indexed_at"):
        st.caption("最後索引：" + str(knowledge_summary["last_indexed_at"])[:19].replace("T", " "))
    if st.button("更新本機知識索引", use_container_width=True):
        indexed = build_or_refresh_knowledge_index()
        st.success(f"已更新 {len(indexed)} 個本機知識來源。")
        st.rerun()
    if st.button("更新 SOP / RAG 索引", use_container_width=True):
        chunks = build_rag_index_from_knowledge_sources()
        st.success(f"已建立 {len(chunks)} 個 RAG 知識片段。")
        st.rerun()

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
        st.caption(f"知識來源 · 狀態：{item.indexed_status}")
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
render_product_footer()
