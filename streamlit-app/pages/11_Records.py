"""Unified records, memory, follow-up, and knowledge management page."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import streamlit as st


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from utils.followup_models import FOLLOWUP_PRIORITIES, FOLLOWUP_STATUSES
from utils.followup_store import list_followups, update_followup_status
from utils.google_drive_adapter import GoogleDriveKnowledgeAdapter
from utils.knowledge_models import KNOWLEDGE_TRUST_LABELS
from utils.knowledge_pack_store import build_or_refresh_knowledge_index, read_knowledge_index
from utils.logo_helper import sidebar_logo
from utils.memory_models import MEMORY_STATUSES
from utils.navigation import render_navigation_links
from utils.project_memory_store import read_all_memory
from utils.drawing_store import list_recent_drawing_documents, read_pages_for_document
from utils.drawing_models import (
    ACTION_TYPE_LABELS_ZH,
    DISCIPLINE_LABELS_ZH,
    PAGE_TYPE_LABELS_ZH,
)
from utils.rag_indexer import build_rag_index_from_knowledge_sources, read_rag_index
from utils.risk_evidence import build_analysis_basis, build_risk_evidence_trace
from utils.runtime_storage_health import get_runtime_storage_status
from utils.site_record_store import (
    DEFAULT_RECORD_PATH,
    PRIORITY_OPTIONS,
    STATUS_OPTIONS,
    SiteRecordStore,
)
from utils.ui_components import (
    compact_link_row,
    page_header,
    render_product_footer,
    render_risk_evidence_trace,
)


st.set_page_config(page_title="歷史紀錄", page_icon="🗂️", layout="wide")

with st.sidebar:
    sidebar_logo()
    st.markdown("---")
    render_navigation_links()

page_header("歷史紀錄", "集中查閱地盤記錄、工程記憶、跟進事項及知識來源。", "🗂️")
compact_link_row((
    ("pages/0_AICOS_Workspace.py", "🏗️ AICOS 工作台"),
    ("pages/1_Upload.py", "📤 上載分析"),
    ("pages/10_Ask_AICOS.py", "💬 問 AICOS"),
))

storage_health = get_runtime_storage_status()
if storage_health.warning_message:
    st.warning(storage_health.warning_message)
with st.expander("技術狀態", expanded=False):
    st.caption(f"儲存模式：{storage_health.mode} · 可寫入：{'是' if storage_health.writable else '否'}")
    st.caption("受影響資料：" + "、".join(storage_health.affected_files))
    st.caption(f"地盤記錄位置：{DEFAULT_RECORD_PATH.relative_to(APP_ROOT)}")

if st.session_state.get("records_message"):
    st.success(st.session_state.pop("records_message"))

site_tab, memory_tab, followup_tab, knowledge_tab, drawing_tab, handoff_tab = st.tabs(
    ["地盤記錄", "AICOS 記憶", "跟進事項", "知識來源"] + ["圖紙分析", "CAD/BIM 交接"]
)


with site_tab:
    store = SiteRecordStore()
    all_records = store.list_records(limit=None)
    projects = sorted({str(item.project_ref) for item in all_records if getattr(item, "project_ref", None)})
    statuses = sorted({item.status for item in all_records if item.status})
    risks = sorted({item.risk_level or item.priority for item in all_records if item.risk_level or item.priority})
    f_project, f_status, f_risk, f_keyword = st.columns([1, 1, 1, 2])
    site_project = f_project.selectbox("工程編號", [""] + projects, format_func=lambda value: value or "全部", key="site_project")
    site_status = f_status.selectbox("狀態", [""] + statuses, format_func=lambda value: value or "全部", key="site_status")
    site_risk = f_risk.selectbox("風險級別", [""] + risks, format_func=lambda value: value or "全部", key="site_risk")
    site_keyword = f_keyword.text_input("關鍵字", placeholder="搜尋標題、摘要或備註", key="site_keyword")

    records = []
    needle = site_keyword.strip().lower()
    for record in all_records:
        searchable = json.dumps(record.to_dict(), ensure_ascii=False).lower()
        if site_project and str(getattr(record, "project_ref", "") or "") != site_project:
            continue
        if site_status and record.status != site_status:
            continue
        if site_risk and (record.risk_level or record.priority) != site_risk:
            continue
        if needle and needle not in searchable:
            continue
        records.append(record)
    st.metric("記錄數量", len(records))

    if not records:
        st.info("未找到符合條件的地盤記錄。")
    else:
        for record in records[:200]:
            risk = record.risk_level or record.priority or "未分類"
            with st.expander(f"{record.created_at[:19].replace('T', ' ')} · {record.title}"):
                cols = st.columns(4)
                cols[0].markdown(f"**類型**  \n{record.record_type}")
                cols[1].markdown(f"**風險**  \n{risk}")
                cols[2].markdown(f"**狀態**  \n{record.status}")
                cols[3].markdown(f"**優先度**  \n{record.priority}")
                st.write(record.content_summary)
                record_sources = [{"source_type": "uploaded_record", "trust_level": "uploaded_record"}]
                record_trace = build_risk_evidence_trace(
                    risk,
                    question=record.content_summary,
                    sources=record_sources,
                )
                record_basis = build_analysis_basis(
                    sources=record_sources,
                    rules_matched=record_trace.rules_matched,
                )
                render_risk_evidence_trace(record_trace, record_basis, compact=True)
                if record.remarks:
                    st.markdown(f"**備註：** {record.remarks}")
                st.caption(f"來源：{record.source} · Record ID：{record.record_id}")

        record_map = {record.record_id: record for record in records}
        st.divider()
        st.subheader("更新地盤記錄")
        selected_id = st.selectbox(
            "選擇記錄",
            list(record_map),
            format_func=lambda item_id: f"{record_map[item_id].title} · {item_id}",
        )
        selected = record_map[selected_id]
        with st.form("site_record_update_form"):
            edit_status, edit_priority = st.columns(2)
            new_status = edit_status.selectbox(
                "處理狀態", list(STATUS_OPTIONS), index=list(STATUS_OPTIONS).index(selected.status)
            )
            new_priority = edit_priority.selectbox(
                "優先度", list(PRIORITY_OPTIONS), index=list(PRIORITY_OPTIONS).index(selected.priority)
            )
            responsible_role = st.text_input("負責角色", value=selected.responsible_role)
            due_hint = st.text_input("目標日期／時限", value=selected.due_hint)
            remarks = st.text_area("備註", value=selected.remarks, height=90)
            change_summary = st.text_input("更新摘要", placeholder="例如：已補交整改相片")
            save_site = st.form_submit_button("儲存更新", type="primary", use_container_width=True)
        if save_site:
            store.update_record(
                selected_id,
                status=new_status,
                priority=new_priority,
                responsible_role=responsible_role,
                due_hint=due_hint,
                remarks=remarks,
                change_summary=change_summary,
            )
            st.session_state["records_message"] = "地盤記錄已更新。"
            st.rerun()


with memory_tab:
    memories = read_all_memory()
    projects = sorted({item.project_ref for item in memories if item.project_ref})
    risks = sorted({item.risk_level for item in memories if item.risk_level})
    sources = sorted({item.source_type for item in memories if item.source_type})
    tags = sorted({tag for item in memories for tag in [*item.tags, *item.trade_tags] if tag})
    m1, m2, m3, m4, m5, m6 = st.columns([1, 1, 1, 1, 1, 2])
    memory_project = m1.selectbox("工程", [""] + projects, format_func=lambda value: value or "全部", key="memory_project")
    memory_status = m2.selectbox("狀態", [""] + sorted(MEMORY_STATUSES), format_func=lambda value: value or "全部", key="memory_status")
    memory_risk = m3.selectbox("風險", [""] + risks, format_func=lambda value: value or "全部", key="memory_risk")
    memory_source = m4.selectbox("來源", [""] + sources, format_func=lambda value: value or "全部", key="memory_source")
    memory_tag = m5.selectbox("標籤", [""] + tags, format_func=lambda value: value or "全部", key="memory_tag")
    memory_keyword = m6.text_input("關鍵字", key="memory_keyword")

    filtered_memories = []
    needle = memory_keyword.strip().lower()
    for item in memories:
        if memory_project and item.project_ref != memory_project:
            continue
        if memory_status and item.status != memory_status:
            continue
        if memory_risk and item.risk_level != memory_risk:
            continue
        if memory_source and item.source_type != memory_source:
            continue
        if memory_tag and memory_tag not in [*item.tags, *item.trade_tags]:
            continue
        if needle and needle not in json.dumps(item.to_dict(), ensure_ascii=False).lower():
            continue
        filtered_memories.append(item)
    st.metric("工程記憶", len(filtered_memories))
    if not filtered_memories:
        st.info("尚未有符合條件的工程記憶。")
    for item in filtered_memories[:200]:
        with st.expander(f"{item.created_at[:19].replace('T', ' ')} · {item.title}"):
            st.write(item.summary)
            st.caption(
                f"工程：{item.project_ref or '未指定'} · 來源：{item.source_type} · "
                f"狀態：{item.status} · 優先度：{item.priority} · 風險：{item.risk_level or '未分類'}"
            )
            if item.evidence_sources:
                st.caption("證據來源：" + "、".join(item.evidence_sources))
            if item.tags or item.trade_tags:
                st.caption("標籤：" + "、".join([*item.tags, *item.trade_tags]))
            if item.linked_record_ids:
                st.caption("相關記錄：" + "、".join(item.linked_record_ids))
            with st.expander("Metadata", expanded=False):
                st.json(item.metadata or {})


with followup_tab:
    followups = list_followups(limit=None)
    projects = sorted({item.project_ref for item in followups if item.project_ref})
    roles = sorted({item.responsible_role for item in followups if item.responsible_role})
    fu1, fu2, fu3, fu4, fu5 = st.columns([1, 1, 1, 1, 2])
    follow_project = fu1.selectbox("工程", [""] + projects, format_func=lambda value: value or "全部", key="follow_project")
    follow_status = fu2.selectbox("狀態", [""] + sorted(FOLLOWUP_STATUSES), format_func=lambda value: value or "全部", key="follow_status")
    follow_priority = fu3.selectbox("優先度", [""] + sorted(FOLLOWUP_PRIORITIES), format_func=lambda value: value or "全部", key="follow_priority")
    follow_role = fu4.selectbox("負責角色", [""] + roles, format_func=lambda value: value or "全部", key="follow_role")
    follow_keyword = fu5.text_input("關鍵字", key="follow_keyword")
    needle = follow_keyword.strip().lower()
    filtered_followups = [
        item for item in followups
        if (not follow_project or item.project_ref == follow_project)
        and (not follow_status or item.status == follow_status)
        and (not follow_priority or item.priority == follow_priority)
        and (not follow_role or item.responsible_role == follow_role)
        and (not needle or needle in json.dumps(item.to_dict(), ensure_ascii=False).lower())
    ]
    st.metric("跟進事項", len(filtered_followups))
    if not filtered_followups:
        st.info("尚未有符合條件的跟進事項。")
    else:
        for item in filtered_followups[:200]:
            with st.expander(f"{item.priority.upper()} · {item.title}"):
                st.write(item.description)
                st.caption(
                    f"工程：{item.project_ref or '未指定'} · 狀態：{item.status} · "
                    f"負責：{item.responsible_role or '未指定'} · 時限：{item.due_hint or '未指定'}"
                )
                if item.evidence_required:
                    st.markdown("**所需證據：** " + "、".join(item.evidence_required))
                if item.suggested_actions:
                    st.markdown("**建議行動：** " + "、".join(item.suggested_actions))
                if item.source_memory_id or item.source_record_id:
                    st.caption(
                        f"來源記憶：{item.source_memory_id or '無'} · "
                        f"來源記錄：{item.source_record_id or '無'}"
                    )

        followup_map = {item.followup_id: item for item in filtered_followups}
        st.divider()
        st.subheader("更新跟進狀態")
        followup_id = st.selectbox(
            "選擇跟進事項", list(followup_map),
            format_func=lambda item_id: followup_map[item_id].title,
        )
        current = followup_map[followup_id]
        with st.form("followup_update_form"):
            next_status = st.selectbox(
                "新狀態", sorted(FOLLOWUP_STATUSES),
                index=sorted(FOLLOWUP_STATUSES).index(current.status),
            )
            followup_remarks = st.text_area("更新備註", height=90)
            save_followup = st.form_submit_button("更新跟進事項", type="primary", use_container_width=True)
        if save_followup:
            update_followup_status(followup_id, next_status, followup_remarks)
            st.session_state["records_message"] = "跟進事項已更新。"
            st.rerun()


with knowledge_tab:
    sources = read_knowledge_index()
    rag_chunks = read_rag_index()
    trust_counts = Counter(item.trust_level for item in sources)
    drive = GoogleDriveKnowledgeAdapter()
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("知識來源", len(sources))
    k2.metric("RAG 片段", len(rag_chunks))
    k3.metric("官方來源", trust_counts.get("official", 0))
    k4.metric("可信來源", trust_counts.get("trusted", 0))
    k5.metric("公司內部", trust_counts.get("internal", 0))
    k6.metric("未核實", trust_counts.get("unverified", 0))
    st.caption("雲端知識庫：" + ("已預留設定" if drive.is_configured() else "未設定"))
    if rag_chunks:
        st.caption("RAG 最後更新：" + max(item.created_at for item in rag_chunks)[:19].replace("T", " "))

    b1, b2 = st.columns(2)
    if b1.button("更新本機知識索引", use_container_width=True):
        indexed = build_or_refresh_knowledge_index()
        st.session_state["records_message"] = f"已更新 {len(indexed)} 個知識來源。"
        st.rerun()
    if b2.button("更新 SOP / RAG 索引", use_container_width=True):
        chunks = build_rag_index_from_knowledge_sources()
        st.session_state["records_message"] = f"已建立 {len(chunks)} 個 RAG 片段。"
        st.rerun()

    trusts = sorted({item.trust_level for item in sources})
    source_types = sorted({item.source_type for item in sources})
    source_tags = sorted({tag for item in sources for tag in [*item.topic_tags, *item.trade_tags] if tag})
    ks1, ks2, ks3, ks4 = st.columns([1, 1, 1, 2])
    knowledge_trust = ks1.selectbox("可信度", [""] + trusts, format_func=lambda value: KNOWLEDGE_TRUST_LABELS.get(value, value) if value else "全部")
    knowledge_type = ks2.selectbox("來源類型", [""] + source_types, format_func=lambda value: value or "全部")
    knowledge_tag = ks3.selectbox("標籤", [""] + source_tags, format_func=lambda value: value or "全部")
    knowledge_keyword = ks4.text_input("搜尋知識來源")
    needle = knowledge_keyword.strip().lower()
    filtered_sources = [
        item for item in sources
        if (not knowledge_trust or item.trust_level == knowledge_trust)
        and (not knowledge_type or item.source_type == knowledge_type)
        and (not knowledge_tag or knowledge_tag in [*item.topic_tags, *item.trade_tags])
        and (not needle or needle in json.dumps(item.to_dict(), ensure_ascii=False).lower())
    ]
    if not filtered_sources:
        st.info("尚未有符合條件的知識來源；可先更新本機知識索引。")
    for item in filtered_sources[:200]:
        with st.expander(f"{KNOWLEDGE_TRUST_LABELS.get(item.trust_level, item.trust_level)} · {item.title}"):
            st.write(item.summary or "未有摘要。")
            st.caption(f"類型：{item.source_type} · 地區：{item.jurisdiction or '未指定'}")
            if item.extracted_refs:
                st.caption("參考：" + "、".join(item.extracted_refs[:6]))
            if item.path_or_url:
                with st.expander("來源路徑／網址", expanded=False):
                    st.code(item.path_or_url)



with drawing_tab:
    drawings = list_recent_drawing_documents(limit=100)
    st.metric("圖紙分析記錄", len(drawings))
    if not drawings:
        st.info("尚未有圖紙分析記錄；可於「圖紙分析」頁上載圖紙。")
    for document in drawings[:100]:
        disc = "、".join(DISCIPLINE_LABELS_ZH.get(d, d) for d in document.disciplines) or "未能確定"
        title = document.source_file_name or document.document_id
        with st.expander(f"{(document.created_at or '')[:19].replace('T', ' ')} · {title}"):
            cols = st.columns(4)
            cols[0].markdown(f"**項目**  \n{document.project_ref or '未指定'}")
            cols[1].markdown(f"**分析頁數**  \n{document.analyzed_page_count}")
            cols[2].markdown(f"**交接事項**  \n{len(document.handoff_items)}")
            cols[3].markdown(f"**專業**  \n{disc}")
            st.write(document.summary)
            if document.drawing_issues:
                st.markdown("**待確認：** " + "；".join(document.drawing_issues[:6]))
            if document.missing_information:
                st.markdown("**缺資料：** " + "；".join(document.missing_information[:6]))
            for page in read_pages_for_document(document.document_id):
                ptype = PAGE_TYPE_LABELS_ZH.get(page.page_type, page.page_type)
                pdisc = DISCIPLINE_LABELS_ZH.get(page.discipline, page.discipline)
                st.caption(
                    f"第 {page.page_number} 頁 · {ptype} · {pdisc} · "
                    f"圖號 {page.drawing_number or '未標示'} · 比例 {page.scale or '未標示'}"
                )


with handoff_tab:
    team_labels = {"cad": "CAD", "bim": "BIM", "both": "CAD／BIM"}
    priority_labels = {"low": "低", "medium": "中", "high": "高", "urgent": "緊急"}
    drawings = list_recent_drawing_documents(limit=100)
    rows = [(document, item) for document in drawings for item in document.handoff_items]
    st.metric("CAD/BIM 交接事項", len(rows))
    if not rows:
        st.info("尚未有 CAD/BIM 交接事項。")
    f_team, f_priority = st.columns(2)
    team_filter = f_team.selectbox("團隊", ["", "cad", "bim", "both"], format_func=lambda v: team_labels.get(v, "全部") if v else "全部", key="handoff_team")
    priority_filter = f_priority.selectbox("優先度", ["", "urgent", "high", "medium", "low"], format_func=lambda v: priority_labels.get(v, "全部") if v else "全部", key="handoff_priority")
    for document, item in rows[:300]:
        if team_filter and item.target_team != team_filter:
            continue
        if priority_filter and item.priority != priority_filter:
            continue
        team = team_labels.get(item.target_team, item.target_team)
        action = ACTION_TYPE_LABELS_ZH.get(item.action_type, item.action_type)
        priority = priority_labels.get(item.priority, item.priority)
        page_hint = f"（第 {item.page_number} 頁）" if item.page_number else ""
        with st.expander(f"[{team}｜{action}｜優先：{priority}] {item.title}{page_hint}"):
            st.write(item.description or "")
            st.caption(f"來源圖紙：{document.source_file_name or document.document_id} · 項目：{document.project_ref or '未指定'}")


render_product_footer()
