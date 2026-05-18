# -*- coding: utf-8 -*-
"""
pages/6_Memory_Manager.py
HK-AICOS Phase 3.1A — 工程記憶管理中心
"""

import json
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import sys

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logo_helper import sidebar_logo


BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
MEMORY_FILE = DATA_DIR / "session_memory.json"
RISK_ORDER = {"低風險": 1, "中風險": 2, "高風險": 3, "極高風險": 3}
TEST_REFS = ("TEST", "CAP-TEST", "BW-TEST")


st.set_page_config(
    page_title="工程記憶管理 | HK-AICOS",
    page_icon="🧠",
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

    .memory-card {
        background: white;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        box-shadow: 0 2px 8px rgba(26,58,92,0.08);
        margin-bottom: 1rem;
        border-left: 5px solid #c9a84c;
    }
    .memory-card h4 {
        color: #1a3a5c;
        font-size: 1rem;
        margin: 0 0 0.6rem 0;
    }
    .risk-pill {
        display: inline-block;
        border-radius: 14px;
        padding: 0.1rem 0.55rem;
        font-size: 0.78rem;
        font-weight: 700;
        background: #eaf0fb;
        color: #1a3a5c;
        margin-left: 0.25rem;
    }
    .danger-box {
        background: #fff1f1;
        border: 1px solid #e0a0a0;
        border-radius: 8px;
        padding: 1rem;
        margin-top: 0.8rem;
    }
    .small-muted {
        color: #666;
        font-size: 0.82rem;
        line-height: 1.5;
    }

    @media (max-width: 768px) {
        .page-header { padding: 1.4rem 1rem; }
        .page-header h2 { font-size: 1.3rem; }
        .memory-card { padding: 0.9rem 1rem; }
    }
</style>
""", unsafe_allow_html=True)


with st.sidebar:
    sidebar_logo()
    st.markdown("---")
    st.page_link("app.py", label="🏠 首頁")
    st.page_link("pages/1_Upload.py", label="📤 上載分析")
    st.page_link("pages/2_Report.py", label="📄 分析報告")
    st.page_link("pages/3_History.py", label="🕘 歷史紀錄")
    st.page_link("pages/6_Memory_Manager.py", label="🧠 工程記憶管理")
    st.page_link("pages/5_Translate.py", label="📑 文件翻譯與轉換")
    st.page_link("pages/4_About.py", label="ℹ️ 關於 Buildway Tech")
    st.markdown("---")
    st.markdown('<div style="font-size:0.78rem;color:#aac4e0;">只操作工程記憶 JSON，不會刪除程式碼。</div>', unsafe_allow_html=True)


def _load_memory() -> tuple[list, str]:
    if not MEMORY_FILE.exists():
        return [], ""
    try:
        data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [], f"JSON 格式錯誤：{exc}"
    except Exception as exc:
        return [], f"讀取記憶檔失敗：{exc}"
    if not isinstance(data, list):
        return [], "JSON 格式錯誤：工程記憶檔必須是 session list。"
    return data, ""


def _write_memory(sessions: list) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MEMORY_FILE.write_text(json.dumps(sessions, ensure_ascii=False, indent=2), encoding="utf-8")


def _backup_memory() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DATA_DIR / f"session_memory_backup_{ts}.json"
    if MEMORY_FILE.exists():
        shutil.copy2(MEMORY_FILE, backup_path)
    else:
        backup_path.write_text("[]", encoding="utf-8")
    st.session_state["last_memory_backup_path"] = str(backup_path)
    return backup_path


def _highest_risk(sessions: list) -> str:
    if not sessions:
        return "—"
    return max(
        (str(s.get("risk_level", "中風險")) for s in sessions),
        key=lambda risk: RISK_ORDER.get(risk, 2),
    )


def _project_summary(sessions: list) -> list:
    grouped = defaultdict(list)
    for session in sessions:
        grouped[str(session.get("project_ref", "未填寫") or "未填寫")].append(session)

    rows = []
    for project_ref, items in grouped.items():
        latest = max(str(s.get("upload_time", "")) for s in items) if items else ""
        rows.append({
            "project_ref": project_ref,
            "session_count": len(items),
            "latest_time": latest,
            "highest_risk": _highest_risk(items),
        })
    return sorted(rows, key=lambda row: row["latest_time"], reverse=True)


def _delete_and_refresh(new_sessions: list, success_message: str) -> None:
    backup_path = _backup_memory()
    _write_memory(new_sessions)
    st.success(f"{success_message} 已先建立備份：{backup_path.name}")
    st.rerun()


st.markdown("""
<div class="page-header">
    <h2>🧠 工程記憶管理</h2>
    <p>查看、備份、刪除及重置 HK-AICOS 工程分析記憶。</p>
</div>
""", unsafe_allow_html=True)

st.markdown(f"**Memory file path：** `{MEMORY_FILE}`")
last_backup = st.session_state.get("last_memory_backup_path", "")
if last_backup:
    st.markdown(f"**最新 backup path：** `{last_backup}`")

sessions, load_error = _load_memory()

if load_error:
    st.error(load_error)
    st.stop()

if not MEMORY_FILE.exists():
    st.info("暫未有工程記憶紀錄")
    if st.button("備份空白記憶檔", use_container_width=True):
        backup = _backup_memory()
        st.success(f"已建立備份：{backup}")
    st.stop()

if not sessions:
    st.info("暫未有工程記憶紀錄")
else:
    project_rows = _project_summary(sessions)

    st.markdown("### 工程記憶總覽")
    for row in project_rows:
        st.markdown(
            f"""
<div class="memory-card">
  <h4>{row["project_ref"]}<span class="risk-pill">{row["highest_risk"]}</span></h4>
  <div class="small-muted">
    Session 數量：{row["session_count"]}<br/>
    最新分析時間：{row["latest_time"] or "—"}
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    project_options = [row["project_ref"] for row in project_rows]
    selected_project = st.selectbox("選擇 Project Ref 查看詳情", project_options)
    selected_sessions = [
        s for s in sessions
        if str(s.get("project_ref", "未填寫") or "未填寫") == selected_project
    ]
    selected_sessions = sorted(
        selected_sessions,
        key=lambda s: str(s.get("upload_time", "")),
        reverse=True,
    )

    st.markdown("### Project Session 詳情")
    for session in selected_sessions:
        file_names = "、".join(session.get("file_names", []) or []) or "—"
        agents = "、".join(session.get("selected_agents", []) or []) or "—"
        departments = "、".join(session.get("departments", []) or []) or "—"
        st.markdown(
            f"""
<div class="memory-card">
  <h4>{session.get("session_id", "—")}<span class="risk-pill">{session.get("risk_level", "中風險")}</span></h4>
  <div class="small-muted">
    分析時間：{session.get("upload_time", "—")}<br/>
    文件：{file_names}<br/>
    Agent：{agents}<br/>
    涉及部門：{departments}<br/>
    問題：{session.get("question", "—")}<br/>
    摘要：{session.get("analysis_summary", "—")}
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

st.markdown("---")
st.markdown("### 記憶操作")

col_backup, col_session = st.columns(2)
with col_backup:
    if st.button("備份全部記憶", use_container_width=True):
        backup = _backup_memory()
        st.success(f"已建立備份：{backup}")

with col_session:
    session_ids = [str(s.get("session_id", "")) for s in sessions if s.get("session_id")]
    session_to_delete = st.selectbox(
        "刪除單次 session",
        [""] + session_ids,
        format_func=lambda sid: "請選擇 session_id" if not sid else sid,
    )
    if st.button("刪除選定 session", disabled=not session_to_delete, use_container_width=True):
        remaining = [s for s in sessions if str(s.get("session_id", "")) != session_to_delete]
        _delete_and_refresh(remaining, f"已刪除 session：{session_to_delete}")

col_project, col_tests = st.columns(2)
with col_project:
    project_options = [row["project_ref"] for row in _project_summary(sessions)] if sessions else []
    project_to_delete = st.selectbox(
        "刪除整個 Project Ref",
        [""] + project_options,
        format_func=lambda ref: "請選擇 Project Ref" if not ref else ref,
    )
    if st.button("刪除選定 Project Ref", disabled=not project_to_delete, use_container_width=True):
        remaining = [
            s for s in sessions
            if str(s.get("project_ref", "未填寫") or "未填寫") != project_to_delete
        ]
        _delete_and_refresh(remaining, f"已刪除 Project Ref：{project_to_delete}")

with col_tests:
    test_count = sum(
        1 for s in sessions
        if any(token in str(s.get("project_ref", "")).upper() for token in TEST_REFS)
    )
    st.markdown(f"測試記憶數量：**{test_count}**")
    if st.button("清空全部測試記憶", disabled=test_count == 0, use_container_width=True):
        remaining = [
            s for s in sessions
            if not any(token in str(s.get("project_ref", "")).upper() for token in TEST_REFS)
        ]
        _delete_and_refresh(remaining, "已清空測試記憶")

st.markdown('<div class="danger-box">', unsafe_allow_html=True)
st.markdown("### 危險操作：重置全部記憶")
st.warning("此操作會清空所有 session_memory.json 內容。系統會先建立備份。")
confirm_reset = st.checkbox("我確認需要重置全部工程記憶")
confirm_text = st.text_input("請輸入 RESET 確認")
if st.button(
    "重置全部記憶",
    disabled=not (confirm_reset and confirm_text == "RESET"),
    type="primary",
    use_container_width=True,
):
    _delete_and_refresh([], "已重置全部工程記憶")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center; color:#999; padding:1.5rem 0 0.5rem 0; font-size:0.82rem;">
    Buildway Tech (HK) Limited | HK-AICOS Phase 3.1A
</div>
""", unsafe_allow_html=True)

