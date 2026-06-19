"""Text-first construction Q&A for HK-AICOS."""

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

from utils.analysis_models import KnowledgeSnippet, QAResponse, SearchResult
from utils.answer_formatter import format_answer_display
from utils.answer_modes import ANSWER_MODE_LABELS, DEFAULT_ANSWER_MODE
from utils.knowledge_search import search_local_knowledge
from utils.knowledge_tracker import build_knowledge_context
from utils.llm_answer_client import safe_answer_question
from utils.logo_helper import sidebar_logo
from utils.navigation import render_navigation_links
from utils.official_sources import (
    SOURCE_MODES,
    SOURCE_MODE_LABELS_ZH,
    TRUST_LABELS_ZH,
    default_source_mode,
    source_id_for,
)
from utils.search_query_builder import build_hk_official_query
from utils.risk_evidence import build_analysis_basis, build_risk_evidence_trace
from utils.service_readiness import get_service_readiness
from utils.site_memory import build_memory_context, save_memory_item
from utils.site_record_store import SiteRecordStore, save_qa_session_record
from utils.source_reference_extractor import (
    extract_source_reference,
    extract_source_references,
    format_source_reference,
    has_specific_reference,
)
from utils.web_search_adapter import web_search
from utils.ui_components import (
    compact_link_row,
    page_header,
    render_answer_card,
    render_product_footer,
    render_risk_evidence_trace,
    risk_badge,
)


st.set_page_config(page_title="問 AICOS", page_icon="💬", layout="wide")

QUESTION_TYPES = {
    "safety": "安全問題",
    "law_regulation": "法例及規例",
    "construction_method": "施工方法",
    "material": "物料處理",
    "document_search": "文件搜尋",
    "site_followup": "地盤跟進",
    "general": "一般問題",
}
SEARCH_SCOPES = {
    "local_knowledge": "本機知識庫",
    "uploaded_records": "已儲存地盤記錄",
    "web_search": "網上搜尋",
    "all": "全部來源",
}
TRUST_DISPLAY_ORDER = (
    "official_hk",
    "trusted_industry",
    "local_internal",
    "uploaded_record",
    "general_web",
    "unknown",
    "fallback_only",
)


def _group_sources_by_trust(sources: list[dict]) -> list[tuple[str, list[dict]]]:
    grouped: dict[str, list[dict]] = {}
    for source in sources:
        if isinstance(source, dict):
            grouped.setdefault(str(source.get("trust_level") or "unknown"), []).append(source)
    ordered = [(trust, grouped.pop(trust)) for trust in TRUST_DISPLAY_ORDER if trust in grouped]
    ordered.extend(sorted(grouped.items()))
    return ordered


def _short_snippet(value: object, limit: int = 280) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


with st.sidebar:
    sidebar_logo()
    st.markdown("---")
    render_navigation_links()

page_header("問 AICOS", "查詢安全、法例、施工方法、物料、文件及既有地盤記錄。", "💬")
compact_link_row((
    ("pages/1_Upload.py", "📤 上載相片／文件"),
    ("pages/11_Records.py", "🗂️ 查看地盤記錄"),
))

if st.button("清除／重設", key="clear_ask_aicos"):
    for key in (
        "ask_question",
        "ask_question_type",
        "ask_search_scope",
        "ask_source_mode",
        "ask_answer_mode",
        "ask_project_id",
        "ask_remember_answer",
        "ask_memory_id",
        "ask_answer_recovered",
        "ask_result",
        "ask_local_sources",
        "ask_web_sources",
        "ask_web_status",
        "ask_saved_record_id",
    ):
        st.session_state.pop(key, None)
    st.rerun()

with st.container(border=True):
    st.markdown("#### 提問設定")
    with st.form("ask_aicos_form"):
        question = st.text_area(
            "你的問題",
            key="ask_question",
            height=130,
            placeholder="例如：香港地盤高空工作幾高需要設置防墮措施？",
        )
        col_type, col_scope = st.columns(2)
        with col_type:
            question_type = st.selectbox(
                "問題類型",
                list(QUESTION_TYPES),
                format_func=QUESTION_TYPES.get,
                key="ask_question_type",
            )
        with col_scope:
            search_scope = st.selectbox(
                "搜尋範圍",
                list(SEARCH_SCOPES),
                index=list(SEARCH_SCOPES).index("all"),
                format_func=SEARCH_SCOPES.get,
                key="ask_search_scope",
            )
        col_trust, col_answer_mode = st.columns(2)
        with col_trust:
            source_mode = st.selectbox(
                "網上來源信任模式",
                list(SOURCE_MODES),
                index=list(SOURCE_MODES).index(default_source_mode(question_type)),
                format_func=SOURCE_MODE_LABELS_ZH.get,
                help="只影響網上搜尋結果；本機文件及已儲存紀錄會保留並清楚標示。",
                key="ask_source_mode",
            )
        with col_answer_mode:
            answer_mode = st.selectbox(
                "回答模式",
                list(ANSWER_MODE_LABELS),
                index=list(ANSWER_MODE_LABELS).index(DEFAULT_ANSWER_MODE),
                format_func=ANSWER_MODE_LABELS.get,
                key="ask_answer_mode",
                help="簡明現場版最精簡；需要更多合規內容時才選擇法例來源詳細版。",
            )
        col_project, col_memory = st.columns(2)
        with col_project:
            project_id = st.text_input(
                "項目編號（選填）",
                placeholder="例如：BW-001",
                key="ask_project_id",
            )
        with col_memory:
            remember_answer = st.checkbox(
                "儲存為 AICOS 問答記憶",
                value=True,
                key="ask_remember_answer",
            )
        submitted = st.form_submit_button("提交問題", type="primary", use_container_width=True)

if submitted:
    if not question.strip():
        st.error("請先輸入問題。")
    else:
        local_sources: list[KnowledgeSnippet] = []
        record_sources: list[KnowledgeSnippet] = []
        web_sources: list[SearchResult] = []
        if search_scope in {"local_knowledge", "all"}:
            local_sources = search_local_knowledge(question, limit=5)
        if search_scope in {"uploaded_records", "all"}:
            for record in SiteRecordStore().search_records(keyword=question, limit=5):
                record_sources.append(
                    KnowledgeSnippet(
                        title=record.title,
                        path=f"本機記錄 {record.record_id}",
                        snippet=record.content_summary,
                        score=5.0,
                        source_type="uploaded_record",
                        source_id=source_id_for(record.record_id, "record"),
                        trust_level="uploaded_record",
                        provider="site_record_store",
                    )
                )
            record_sources.extend(build_memory_context(question, project_id or None, limit=5))
            record_sources.extend(build_knowledge_context(question, project_id or None, limit=5))
        if search_scope in {"web_search", "all"}:
            searched_query = build_hk_official_query(question, question_type, source_mode)
            web_response = web_search(searched_query, limit=5, mode=source_mode)
            web_sources = web_response.results
            st.session_state["ask_web_status"] = web_response.to_dict()
        else:
            st.session_state.pop("ask_web_status", None)

        contexts = [*local_sources, *record_sources, *web_sources]
        with st.spinner("AICOS 正在整理資料及建立現場建議…"):
            response, recovered_from_error = safe_answer_question(
                question=question,
                question_type=question_type,
                search_scope=search_scope,
                context_snippets=contexts,
                answer_mode=answer_mode,
            )
        st.session_state["ask_answer_recovered"] = recovered_from_error
        st.session_state["ask_result"] = {
            "question": question,
            "question_type": question_type,
            "search_scope": search_scope,
            "source_mode": source_mode,
            "answer_mode": answer_mode,
            "response": response.to_dict(),
        }
        st.session_state["ask_local_sources"] = [item.to_dict() for item in [*local_sources, *record_sources]]
        st.session_state["ask_web_sources"] = [item.to_dict() for item in web_sources]
        st.session_state.pop("ask_saved_record_id", None)
        st.session_state.pop("ask_memory_id", None)
        if remember_answer:
            response_data = response.to_dict()
            memory = save_memory_item(
                memory_type="qa_memory",
                project_id=project_id,
                title=f"問 AICOS：{question.strip()[:80]}",
                summary=response.answer[:1200],
                tags=[question_type, answer_mode],
                risk_level=response.risk_level,
                status="answered",
                related_source_ids=[
                    str(source.get("source_id") or "")
                    for source in response_data.get("sources", [])
                    if source.get("source_id")
                ],
                raw_payload={"question": question, "response": response_data},
            )
            st.session_state["ask_memory_id"] = memory.memory_id


result = st.session_state.get("ask_result")
if result:
    response_data = result["response"]
    source_data = response_data.get("sources", [])
    trust_levels = {item.get("trust_level", "unknown") for item in source_data if isinstance(item, dict)}
    web_status = st.session_state.get("ask_web_status")
    references = extract_source_references(source_data, result["question"])
    official_references = [reference for reference in references if reference.trust_level == "official_hk"]
    source_summary_lines = [format_source_reference(reference) for reference in official_references[:3]]
    risk_trace = build_risk_evidence_trace(
        response_data.get("risk_level", "unknown"),
        question=result["question"],
        sources=source_data,
    )
    analysis_basis = build_analysis_basis(
        sources=source_data,
        rules_matched=risk_trace.rules_matched,
    )
    review_warnings = []
    if st.session_state.get("ask_answer_recovered"):
        review_warnings.append("部分搜尋內容暫時不可用，已改用安全的本機備用答案。")
    if result["question_type"] in {"safety", "law_regulation"}:
        review_warnings.append("安全／法例資料須按香港官方最新版本及合資格人士意見覆核；本回覆並非正式法律意見。")
    if result["question_type"] == "law_regulation" and "official_hk" not in trust_levels:
        review_warnings.append("本次沒有可核實香港官方來源；作出合規決定前請查閱官方最新資料。")
    elif result["question_type"] == "safety" and not trust_levels.intersection({"official_hk", "trusted_industry"}):
        review_warnings.append("本次沒有官方或可信行業來源；請由安全主任按最新指引覆核。")
    answer_display = format_answer_display(
        response_data.get("answer", ""),
        answer_mode=result.get("answer_mode", DEFAULT_ANSWER_MODE),
        risk_level=response_data.get("risk_level", "unknown"),
        confidence=response_data.get("confidence", 0.0),
        source_summary=source_summary_lines,
        warnings=review_warnings,
        source_available="official_hk" in trust_levels,
        memory_save_status=(
            f"已儲存 AICOS 問答記憶：{st.session_state['ask_memory_id']}"
            if st.session_state.get("ask_memory_id") else ""
        ),
        fallback_used=bool(response_data.get("fallback_used")),
        risk_trace=risk_trace,
        analysis_basis=analysis_basis,
        technical_status=get_service_readiness(),
    )
    st.divider()
    render_answer_card(answer_display)

    col_risk, col_confidence, col_mode = st.columns(3)
    with col_risk:
        st.caption("風險級別")
        risk_badge(response_data["risk_level"])
    col_confidence.metric("回答信心", answer_display.confidence_label)
    col_mode.metric("回答模式", ANSWER_MODE_LABELS.get(result.get("answer_mode"), ANSWER_MODE_LABELS[DEFAULT_ANSWER_MODE]))
    render_risk_evidence_trace(risk_trace, analysis_basis)
    st.markdown("#### 具體來源參考")
    if official_references:
        for reference in official_references[:3]:
            st.markdown(f"- {format_source_reference(reference)}")
    else:
        st.caption("本次未能核實官方具體章節，請以最新官方文件及安全主任覆核為準。")

    if web_status:
        with st.expander("搜尋詳情", expanded=False):
            st.caption("網上搜尋：" + ("未設定或未完成" if web_status.get("fallback_used") else "已完成"))
            count_official, count_trusted, count_general = st.columns(3)
            count_official.metric("香港官方來源", int(web_status.get("official_results_count") or 0))
            count_trusted.metric("可信行業來源", int(web_status.get("trusted_results_count") or 0))
            count_general.metric("一般網上來源", int(web_status.get("general_results_count") or 0))
            st.markdown("**實際搜尋字串**")
            st.code(web_status.get("searched_query") or "（沒有搜尋字串）", language=None)

    st.markdown("#### 完整來源清單")
    if not source_data:
        st.caption("本次沒有可顯示的來源。")
    for trust, sources in _group_sources_by_trust(source_data):
        trust_label = TRUST_LABELS_ZH.get(trust, TRUST_LABELS_ZH["unknown"])
        st.markdown(f"##### {trust_label}（{len(sources)}）")
        for source in sources:
            reference = extract_source_reference(source, result["question"])
            used_label = "已用於回答" if source.get("used_in_answer") else "參考資料"
            title = source.get("source_title", "未命名來源")
            url = source.get("source_url", "")
            path = source.get("source_path", "")
            st.markdown(f"**{title}** · {used_label}")
            st.caption(format_source_reference(reference))
            if url:
                st.markdown(f"[開啟來源]({url})")
            elif path:
                st.caption(f"本機路徑：`{path}`")
            excerpt = reference.excerpt or _short_snippet(source.get("snippet", ""), 180)
            if excerpt:
                st.caption("摘錄：" + _short_snippet(excerpt, 180))
            full_snippet = str(source.get("snippet") or "").strip()
            if full_snippet:
                with st.expander(f"查看完整來源摘錄：{title}", expanded=False):
                    st.write(full_snippet)
            if has_specific_reference(reference):
                st.caption(f"參考辨識信心：{reference.reference_confidence:.0%}")
            st.divider()

    if st.session_state.get("ask_saved_record_id"):
        st.success(f"已儲存記錄：{st.session_state['ask_saved_record_id']}")
    elif st.button("儲存此問答記錄", type="secondary", use_container_width=True):
        saved = save_qa_session_record(
            result["question"],
            QAResponse(**response_data),
            question_type=result["question_type"],
        )
        st.session_state["ask_saved_record_id"] = saved.record_id
        st.rerun()

render_product_footer()
