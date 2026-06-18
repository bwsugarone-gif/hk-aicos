# -*- coding: utf-8 -*-
"""
pages/9_Action_Tracker.py
HK-AICOS Phase 3.1E — 跟進事項中心
"""

from html import escape
from pathlib import Path
import sys

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.action_manager import (
    OPEN_STATUSES,
    PRIORITIES,
    STATUSES,
    add_action_item,
    backup_action_items,
    delete_action_item,
    load_action_items,
    update_action_status,
)
from utils.logo_helper import sidebar_logo
from utils.navigation import render_navigation_links


BASE_DIR = Path(__file__).parent.parent
ACTION_FILE = BASE_DIR / "data" / "action_items.json"
PRIORITY_ORDER = {"高": 3, "中": 2, "低": 1}


st.set_page_config(
    page_title="跟進事項中心 | HK-AICOS",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a3a5c 0%, #0f2942 100%);
    }
    [data-testid="stSidebar"] * { color: white !important; }

    .page-header {
        background: linear-gradient(135deg, #1a3a5c 0%, #2d5a8e 100%);
        color: white;
        padding: 1.8rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.3rem;
    }
    .page-header h2 { font-size: 1.6rem; margin: 0 0 0.3rem 0; }
    .page-header p { font-size: 0.98rem; opacity: 0.92; margin: 0; }

    .action-card {
        background: white;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        box-shadow: 0 2px 8px rgba(26,58,92,0.08);
        border-left: 5px solid #c9a84c;
        margin-bottom: 0.9rem;
    }
    .action-title {
        color: #1a3a5c;
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 0.45rem;
    }
    .pill {
        display: inline-block;
        border-radius: 14px;
        padding: 0.12rem 0.6rem;
        font-size: 0.78rem;
        font-weight: 700;
        margin: 0.1rem 0.2rem 0.1rem 0;
        background: #eaf0fb;
        color: #1a3a5c;
        border: 1px solid #d0d7e3;
    }
    .priority-high { background: #fde8eb; color: #c0152a; border-color: #dc3545; }
    .priority-medium { background: #fff4e0; color: #b85c00; border-color: #ffc107; }
    .priority-low { background: #e6f4ec; color: #1a7a3c; border-color: #28a745; }
    .small-muted {
        color: #555;
        font-size: 0.86rem;
        line-height: 1.55;
    }
    .tool-box {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        border-left: 4px solid #1a3a5c;
        margin-bottom: 1rem;
    }

    @media (max-width: 768px) {
        .page-header { padding: 1.4rem 1rem; }
        .page-header h2 { font-size: 1.3rem; }
        .action-card { padding: 0.9rem 1rem; }
    }
</style>
""", unsafe_allow_html=True)


with st.sidebar:
    sidebar_logo()
    st.markdown("---")
    render_navigation_links()
    st.markdown("---")
    st.markdown('<div style="font-size:0.78rem;color:#aac4e0;">追蹤工程跟進事項，可更新狀態。</div>', unsafe_allow_html=True)


def _priority_class(priority: str) -> str:
    if priority == "高":
        return "priority-high"
    if priority == "低":
        return "priority-low"
    return "priority-medium"


def _load_actions_safe() -> tuple[list, str]:
    try:
        return load_action_items(), ""
    except Exception as exc:
        return [], f"讀取 action_items.json 失敗：{exc}"


def _sort_actions(items: list) -> list:
    return sorted(
        items,
        key=lambda item: (
            PRIORITY_ORDER.get(item.get("priority", "中"), 2),
            str(item.get("created_at", "")),
        ),
        reverse=True,
    )


def _filter_actions(items: list, project_ref: str, status: str, agent: str, department: str) -> list:
    query = project_ref.strip().lower()
    filtered = []
    for item in items:
        if query and query not in str(item.get("project_ref", "")).lower():
            continue
        if status == "未完成":
            if item.get("status") not in OPEN_STATUSES:
                continue
        elif status != "全部" and item.get("status") != status:
            continue
        if agent != "全部" and item.get("responsible_agent") != agent:
            continue
        if department != "全部" and item.get("department") != department:
            continue
        filtered.append(item)
    return _sort_actions(filtered)


def _label(item: dict) -> str:
    return f"{item.get('priority', '中')}｜{item.get('project_ref', '未填寫')}｜{item.get('action_title', '')}｜{item.get('action_id', '')}"


st.markdown("""
<div class="page-header">
    <h2>✅ 跟進事項中心</h2>
    <p>將工程風險及 Agent 建議轉成可追蹤 Action Items。</p>
</div>
""", unsafe_allow_html=True)

st.markdown(f"**Action storage：** `{ACTION_FILE}`")
last_backup = st.session_state.get("last_action_backup_path", "")
if last_backup:
    st.markdown(f"**最新 backup：** `{last_backup}`")

items, load_error = _load_actions_safe()
if load_error:
    st.error(load_error)
    st.stop()

if st.session_state.get("action_tracker_warning"):
    st.warning(st.session_state["action_tracker_warning"])

agents = sorted({str(item.get("responsible_agent", "")) for item in items if item.get("responsible_agent")})
departments = sorted({str(item.get("department", "")) for item in items if item.get("department")})

st.markdown("### 篩選")
col_project, col_status, col_agent, col_dept = st.columns(4)
with col_project:
    project_filter = st.text_input("Project Ref", placeholder="例如：BW-2026")
with col_status:
    status_filter = st.selectbox("狀態", ["未完成", "全部"] + STATUSES)
with col_agent:
    agent_filter = st.selectbox("Responsible Agent", ["全部"] + agents)
with col_dept:
    department_filter = st.selectbox("政府部門", ["全部"] + departments)

filtered = _filter_actions(items, project_filter, status_filter, agent_filter, department_filter)

st.markdown(f"### Action Items（{len(filtered)} 項）")
if not filtered:
    st.info("暫未有未完成跟進事項。")
else:
    for item in filtered:
        priority = item.get("priority", "中")
        st.markdown(
            f"""
<div class="action-card">
  <div class="action-title">{escape(item.get("action_title", "跟進工程風險事項"))}</div>
  <span class="pill {_priority_class(priority)}">優先級：{escape(priority)}</span>
  <span class="pill">狀態：{escape(item.get("status", "未開始"))}</span>
  <span class="pill">風險：{escape(item.get("risk_level", "中風險"))}</span>
  <span class="pill">Agent：{escape(item.get("responsible_agent", "PM Agent"))}</span>
  <div class="small-muted" style="margin-top:0.5rem;">
    工程：{escape(item.get("project_ref", "未填寫"))}<br/>
    部門：{escape(item.get("department", "待確認"))}<br/>
    詳情：{escape(item.get("action_detail", "") or "—")}<br/>
    Action ID：{escape(item.get("action_id", ""))}
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

st.markdown("---")
st.markdown("### 更新狀態 / 刪除")
if items:
    selected_label = st.selectbox("選擇 Action Item", [_label(item) for item in items])
    selected_item = items[[_label(item) for item in items].index(selected_label)]
    selected_action_id = selected_item.get("action_id", "")
    current_status = selected_item.get("status", "未開始")
    next_status = st.selectbox(
        "更新狀態",
        STATUSES,
        index=STATUSES.index(current_status) if current_status in STATUSES else 0,
    )
    col_update, col_delete = st.columns(2)
    with col_update:
        if st.button("儲存狀態", use_container_width=True):
            if update_action_status(selected_action_id, next_status):
                st.success("狀態已更新。")
                st.rerun()
            else:
                st.error("狀態更新失敗。")
    with col_delete:
        confirm_delete = st.checkbox("確認刪除此 Action Item")
        if st.button("刪除 Action Item", disabled=not confirm_delete, use_container_width=True):
            backup_path = delete_action_item(selected_action_id)
            st.session_state["last_action_backup_path"] = str(backup_path)
            st.success(f"已先建立備份並刪除：{backup_path.name}")
            st.rerun()
else:
    st.info("暫未有 Action Item 可更新。")

st.markdown("---")
st.markdown("### 手動新增 Action Item")
with st.form("manual_action_form"):
    col_a, col_b = st.columns(2)
    with col_a:
        project_ref = st.text_input("工程編號", placeholder="例如：BW-2026-001")
        session_id = st.text_input("Session ID（選填）")
        risk_level = st.selectbox("風險級別", ["高風險", "中風險", "低風險"], index=1)
        priority = st.selectbox("優先級", PRIORITIES, index=1)
    with col_b:
        responsible_agent = st.text_input("Responsible Agent", value="PM Agent")
        department = st.text_input("政府部門", value="待確認")
        status = st.selectbox("狀態", STATUSES)
    action_title = st.text_input("Action 標題")
    action_detail = st.text_area("Action 詳情", height=120)
    submitted = st.form_submit_button("新增 Action Item", use_container_width=True)
    if submitted:
        if not action_title.strip():
            st.error("請輸入 Action 標題。")
        else:
            add_action_item({
                "project_ref": project_ref,
                "session_id": session_id,
                "risk_level": risk_level,
                "responsible_agent": responsible_agent,
                "department": department,
                "action_title": action_title,
                "action_detail": action_detail,
                "priority": priority,
                "status": status,
            })
            st.success("Action Item 已新增。")
            st.rerun()

st.markdown("""
<div style="text-align:center; color:#999; padding:1.5rem 0 0.5rem 0; font-size:0.82rem;">
    Buildway Tech (HK) Limited | HK-AICOS Phase 3.1E
</div>
""", unsafe_allow_html=True)

