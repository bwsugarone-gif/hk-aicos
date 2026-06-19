"""Minimal searchable view over local AICOS JSONL records."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from utils.site_record_store import (
    DEFAULT_RECORD_PATH,
    PRIORITY_OPTIONS,
    STATUS_OPTIONS,
    SiteRecordStore,
)
from utils.logo_helper import sidebar_logo
from utils.navigation import render_navigation_links
from utils.ui_components import compact_link_row, page_header, render_product_footer


st.set_page_config(page_title="地盤記錄", page_icon="🗂️", layout="wide")

with st.sidebar:
    sidebar_logo()
    st.markdown("---")
    render_navigation_links()

page_header("地盤記錄", "搜尋、覆核及更新地盤跟進記錄。", "🗂️")
compact_link_row([
    ("pages/1_Upload.py", "📤 上載相片／文件"),
    ("pages/10_Ask_AICOS.py", "💬 問 AICOS"),
])
with st.expander("技術狀態", expanded=False):
    st.caption(f"本機記錄位置：{DEFAULT_RECORD_PATH.relative_to(APP_ROOT)}")
if st.session_state.get("record_update_message"):
    st.success(st.session_state.pop("record_update_message"))

store = SiteRecordStore()
all_records = store.list_records(limit=None)
record_types = sorted({item.record_type for item in all_records})
categories = sorted({item.category for item in all_records if item.category})
statuses = sorted({item.status for item in all_records if item.status})
priorities = sorted({item.priority for item in all_records if item.priority})

col_keyword, col_type, col_category, col_status, col_priority = st.columns([2, 1, 1, 1, 1])
keyword = col_keyword.text_input("關鍵字", placeholder="搜尋標題、摘要或內容")
record_type = col_type.selectbox("記錄類型", [""] + record_types, format_func=lambda value: value or "全部")
category = col_category.selectbox("分類", [""] + categories, format_func=lambda value: value or "全部")
status = col_status.selectbox("狀態", [""] + statuses, format_func=lambda value: value or "全部")
priority = col_priority.selectbox("優先度", [""] + priorities, format_func=lambda value: value or "全部")

records = store.search_records(
    keyword=keyword,
    record_type=record_type,
    category=category,
    status=status,
    priority=priority,
    limit=200,
)
st.metric("記錄數目", len(records))

if not records:
    st.info("暫時沒有符合條件的記錄。可由上載分析或問 AICOS 頁面儲存第一筆記錄。")
else:
    for record in records:
        risk = record.risk_level or record.priority or "—"
        with st.expander(f"{record.created_at[:19].replace('T', ' ')} · {record.title}"):
            col1, col2, col3, col4 = st.columns(4)
            col1.markdown(f"**類型**  \n{record.record_type}")
            col2.markdown(f"**分類**  \n{record.category or '—'}")
            col3.markdown(f"**風險／優先度**  \n{risk}")
            col4.markdown(f"**狀態**  \n{record.status}")
            st.write(record.content_summary)
            if record.responsible_role or record.due_hint:
                st.caption(f"負責：{record.responsible_role or '未指定'} · 時限：{record.due_hint or '未指定'}")
            if record.remarks:
                st.markdown(f"**備註：** {record.remarks}")
            if record.history:
                st.markdown(f"**最近更新（共 {len(record.history)} 次）：**")
                for event in reversed(record.history[-3:]):
                    st.caption(
                        f"{event.get('updated_at', '')[:19].replace('T', ' ')} · "
                        f"{event.get('change_summary', '更新記錄')} · "
                        f"狀態 {event.get('previous_status')} → {event.get('new_status')} · "
                        f"優先度 {event.get('previous_priority')} → {event.get('new_priority')}"
                    )
            st.caption(f"來源：{record.source} · Record ID：{record.record_id}")

    st.divider()
    st.subheader("更新跟進記錄")
    record_map = {record.record_id: record for record in records}
    selected_id = st.selectbox(
        "選擇記錄",
        list(record_map),
        format_func=lambda record_id: f"{record_map[record_id].title} · {record_id}",
    )
    selected = record_map[selected_id]
    with st.form("record_update_form"):
        col_edit_status, col_edit_priority = st.columns(2)
        edit_status = col_edit_status.selectbox(
            "跟進狀態",
            list(STATUS_OPTIONS),
            index=list(STATUS_OPTIONS).index(selected.status),
        )
        edit_priority = col_edit_priority.selectbox(
            "優先度",
            list(PRIORITY_OPTIONS),
            index=list(PRIORITY_OPTIONS).index(selected.priority),
        )
        responsible_role = st.text_input("負責角色", value=selected.responsible_role, placeholder="例如：安全主任／地盤主管")
        due_hint = st.text_input("完成時限", value=selected.due_hint, placeholder="例如：今日收工前／2026-06-20")
        remarks = st.text_area("備註", value=selected.remarks, height=100)
        change_summary = st.text_input("更新摘要", placeholder="例如：分判商已完成臨邊圍封")
        save_update = st.form_submit_button("儲存更新", type="primary", use_container_width=True)
    if save_update:
        updated = store.update_record(
            selected_id,
            status=edit_status,
            priority=edit_priority,
            responsible_role=responsible_role,
            due_hint=due_hint,
            remarks=remarks,
            change_summary=change_summary,
        )
        st.session_state["record_update_message"] = f"已更新記錄：{updated.record_id}"
        st.rerun()

render_product_footer()
