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
from utils.knowledge_search import search_local_knowledge
from utils.llm_answer_client import answer_question
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
from utils.site_record_store import SiteRecordStore, save_qa_session_record
from utils.web_search_adapter import web_search


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

st.title("問 AICOS")
st.caption("毋須上載圖片：直接查詢安全、法例、施工方法、物料、文件及既有地盤記錄。")

quick_upload, quick_records = st.columns(2)
with quick_upload:
    st.page_link("pages/1_Upload.py", label="📤 上載相片／文件", use_container_width=True)
with quick_records:
    st.page_link("pages/11_Records.py", label="🗂️ 查看地盤記錄", use_container_width=True)

if st.button("清除／重設", key="clear_ask_aicos"):
    for key in ("ask_question", "ask_result", "ask_local_sources", "ask_web_sources", "ask_web_status", "ask_saved_record_id"):
        st.session_state.pop(key, None)
    st.rerun()

with st.form("ask_aicos_form"):
    question = st.text_area(
        "你的問題",
        key="ask_question",
        height=150,
        placeholder="例如：高空工作平台臨邊未有踢腳板，應即時做甚麼跟進？",
    )
    col_type, col_scope, col_trust = st.columns(3)
    with col_type:
        question_type = st.selectbox(
            "問題類型",
            list(QUESTION_TYPES),
            format_func=QUESTION_TYPES.get,
        )
    with col_scope:
        search_scope = st.selectbox(
            "搜尋範圍",
            list(SEARCH_SCOPES),
            format_func=SEARCH_SCOPES.get,
        )
    with col_trust:
        source_mode = st.selectbox(
            "網上來源信任模式",
            list(SOURCE_MODES),
            index=list(SOURCE_MODES).index(default_source_mode(question_type)),
            format_func=SOURCE_MODE_LABELS_ZH.get,
            help="只影響網上搜尋結果；本機文件及已儲存紀錄會保留並清楚標示。",
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
        if search_scope in {"web_search", "all"}:
            searched_query = build_hk_official_query(question, question_type, source_mode)
            web_response = web_search(searched_query, limit=5, mode=source_mode)
            web_sources = web_response.results
            st.session_state["ask_web_status"] = web_response.to_dict()
        else:
            st.session_state.pop("ask_web_status", None)

        contexts = [*local_sources, *record_sources, *web_sources]
        with st.spinner("AICOS 正在整理資料及建立現場建議…"):
            response = answer_question(question, question_type, search_scope, contexts)
        st.session_state["ask_result"] = {
            "question": question,
            "question_type": question_type,
            "search_scope": search_scope,
            "source_mode": source_mode,
            "response": response.to_dict(),
        }
        st.session_state["ask_local_sources"] = [item.to_dict() for item in [*local_sources, *record_sources]]
        st.session_state["ask_web_sources"] = [item.to_dict() for item in web_sources]
        st.session_state.pop("ask_saved_record_id", None)


result = st.session_state.get("ask_result")
if result:
    response_data = result["response"]
    source_data = response_data.get("sources", [])
    trust_levels = {item.get("trust_level", "unknown") for item in source_data if isinstance(item, dict)}
    web_status = st.session_state.get("ask_web_status")
    st.divider()
    if web_status:
        provider = str(web_status.get("provider") or "fallback")
        if web_status.get("error"):
            st.warning("搜尋失敗，已使用備援")
        elif web_status.get("fallback_used"):
            st.info("未設定網上搜尋")
        else:
            provider_label = {"tavily": "Tavily 已連接", "brave": "Brave 已連接"}.get(
                provider, f"{provider} 已連接"
            )
            st.success(provider_label)

        count_official, count_trusted, count_general = st.columns(3)
        count_official.metric("香港官方來源", int(web_status.get("official_results_count") or 0))
        count_trusted.metric("可信行業來源", int(web_status.get("trusted_results_count") or 0))
        count_general.metric("一般網上來源", int(web_status.get("general_results_count") or 0))

        with st.expander("搜尋詳情", expanded=False):
            st.markdown("**實際搜尋字串**")
            st.code(web_status.get("searched_query") or "（沒有搜尋字串）", language=None)
            if web_status.get("error"):
                st.caption(str(web_status["error"]))

        web_results = st.session_state.get("ask_web_sources", [])
        if web_results:
            st.markdown("#### 網上搜尋結果（按可信程度分類）")
            for trust, sources in _group_sources_by_trust(web_results):
                trust_label = TRUST_LABELS_ZH.get(trust, TRUST_LABELS_ZH["unknown"])
                with st.expander(f"{trust_label}（{len(sources)}）", expanded=trust == "official_hk"):
                    for source in sources:
                        title = source.get("title", "未命名搜尋結果")
                        url = source.get("url", "")
                        st.markdown(f"- [{title}]({url})" if url else f"- **{title}**")
                        if source.get("snippet"):
                            st.caption(_short_snippet(source["snippet"]))

    if result["question_type"] in {"safety", "law_regulation"}:
        st.warning("安全／法例資料必須以香港官方最新版本及合資格人士意見作最終核實；此回覆並非正式法律意見。")
    if response_data.get("fallback_used"):
        st.warning("目前使用本機回答後備模式；即使找到網上資料，答案仍須由合資格人士及最新官方文件覆核。")
    if result["question_type"] == "law_regulation" and "official_hk" not in trust_levels:
        st.error("本次沒有找到香港官方來源。作出合規或法律決定前，請查閱香港法例電子版或相關政府部門最新資料。")
    if result["question_type"] == "safety" and not trust_levels.intersection({"official_hk", "trusted_industry"}):
        st.warning("本次沒有官方或可信行業網上來源；請由安全主任及最新官方指引覆核。")
    if trust_levels.intersection({"local_internal", "uploaded_record"}) and not trust_levels.intersection({"official_hk", "trusted_industry"}):
        st.info("本回答引用本地內部文件或已儲存紀錄，這些資料不等同官方法例或最新守則。")

    st.subheader("AICOS 回覆")
    st.write(response_data["answer"])

    col_risk, col_confidence, col_mode = st.columns(3)
    col_risk.metric("風險級別", response_data["risk_level"].upper())
    col_confidence.metric("信心度", f"{float(response_data['confidence']):.0%}")
    col_mode.metric("回答模式", "本機後備" if response_data["fallback_used"] else response_data["model_name"])

    st.markdown("#### 實務建議")
    for item in response_data["practical_recommendations"]:
        st.markdown(f"- {item}")
    st.markdown("#### 跟進行動")
    for item in response_data["followup_actions"]:
        st.markdown(f"- {item}")

    st.markdown("#### 回答來源及可信程度")
    if not source_data:
        st.caption("本次沒有可顯示的來源。")
    for trust, sources in _group_sources_by_trust(source_data):
        st.markdown(f"##### {TRUST_LABELS_ZH.get(trust, TRUST_LABELS_ZH['unknown'])}")
        for source in sources:
            used_label = "已用於回答" if source.get("used_in_answer") else "參考資料（未聲稱引用）"
            title = source.get("source_title", "未命名來源")
            url = source.get("source_url", "")
            path = source.get("source_path", "")
            st.markdown(f"**{used_label}**")
            if url:
                st.markdown(f"[{title}]({url})")
            else:
                st.markdown(f"**{title}**" + (f"  ·  `{path}`" if path else ""))
            if source.get("snippet"):
                st.caption(_short_snippet(source["snippet"]))

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
