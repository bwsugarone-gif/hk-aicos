# -*- coding: utf-8 -*-
"""
pages/3_History.py
HK-AICOS Phase 2.5E — 歷史分析紀錄

Buildway Tech (HK) Limited
"""

import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.session_memory import get_all_sessions, get_sessions_by_project
from utils.logo_helper import sidebar_logo

st.set_page_config(
    page_title="歷史紀錄 | HK-AICOS",
    page_icon="🕘",
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
        margin-bottom: 1.5rem;
    }
    .page-header h2 { font-size: 1.6rem; margin: 0 0 0.3rem 0; }
    .page-header p  { font-size: 1rem; opacity: 0.9; margin: 0; }

    .history-card {
        background: white;
        border-radius: 10px;
        padding: 1.2rem 1.4rem;
        box-shadow: 0 2px 8px rgba(26,58,92,0.08);
        margin-bottom: 1rem;
        border-left: 5px solid #c9a84c;
    }
    .history-card-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        flex-wrap: wrap;
        gap: 0.4rem;
        margin-bottom: 0.6rem;
    }
    .history-proj {
        font-size: 1.05rem;
        font-weight: 700;
        color: #1a3a5c;
    }
    .history-date {
        font-size: 0.82rem;
        color: #888;
    }
    .risk-badge {
        display: inline-block;
        border-radius: 20px;
        padding: 0.15rem 0.75rem;
        font-size: 0.8rem;
        font-weight: 700;
    }
    .risk-low    { background: #e6f4ec; color: #1a7a3c; border: 1px solid #28a745; }
    .risk-medium { background: #fff4e0; color: #b85c00; border: 1px solid #ffc107; }
    .risk-high   { background: #fde8eb; color: #c0152a; border: 1px solid #dc3545; }

    .agent-tag {
        display: inline-block;
        background: #eaf0fb;
        color: #1a3a5c;
        border: 1px solid #d0d7e3;
        border-radius: 12px;
        padding: 0.1rem 0.6rem;
        font-size: 0.78rem;
        margin: 0.1rem 0.2rem 0.1rem 0;
    }
    .dept-tag {
        display: inline-block;
        background: #f4f6f9;
        color: #444;
        border: 1px solid #d0d7e3;
        border-radius: 12px;
        padding: 0.1rem 0.6rem;
        font-size: 0.78rem;
        margin: 0.1rem 0.2rem 0.1rem 0;
    }
    .summary-text {
        font-size: 0.88rem;
        color: #555;
        line-height: 1.6;
        margin-top: 0.5rem;
        border-top: 1px solid #f0f0f0;
        padding-top: 0.5rem;
    }

    @media (max-width: 768px) {
        .page-header h2 { font-size: 1.3rem; }
        .history-card { padding: 0.9rem 1rem; }
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    sidebar_logo()
    st.markdown("---")
    st.page_link("app.py",              label="🏠 首頁")
    st.page_link("pages/1_Upload.py",   label="📤 上載分析")
    st.page_link("pages/2_Report.py",   label="📄 分析報告")
    st.page_link("pages/3_History.py",  label="🕘 歷史紀錄")
    st.page_link("pages/4_About.py",    label="ℹ️ 關於 Buildway Tech")
    st.markdown("---")
    st.markdown(
        '<div style="font-size:0.78rem; color:#aac4e0;">🔒 所有資料安全處理</div>',
        unsafe_allow_html=True,
    )

# ── Page Header ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <h2>🕘 歷史分析紀錄</h2>
    <p>查看同一工程項目的過往分析記錄，追蹤風險及部門跟進情況。</p>
</div>
""", unsafe_allow_html=True)

# ── Filter by project ref ─────────────────────────────────────────────────────
col_filter, col_clear = st.columns([4, 1])
with col_filter:
    filter_ref = st.text_input(
        "按工程編號篩選",
        placeholder="例如：BW-001（留空顯示全部）",
        label_visibility="visible",
    )
with col_clear:
    st.markdown("<br/>", unsafe_allow_html=True)
    if st.button("🔄 顯示全部", use_container_width=True):
        filter_ref = ""
        st.rerun()

# ── Load sessions ─────────────────────────────────────────────────────────────
try:
    if filter_ref.strip():
        sessions = get_sessions_by_project(filter_ref.strip())
    else:
        sessions = get_all_sessions()
except Exception:
    sessions = []

# ── Risk badge helper ─────────────────────────────────────────────────────────
_RISK_CLASS = {
    "低風險": "risk-low",
    "中風險": "risk-medium",
    "高風險": "risk-high",
}
_RISK_EMOJI = {
    "低風險": "🟢",
    "中風險": "🟠",
    "高風險": "🔴",
}

# ── Display ───────────────────────────────────────────────────────────────────
if not sessions:
    st.info("暫未有歷史分析記錄。")
    st.page_link("pages/1_Upload.py", label="📤 前往上載分析")
else:
    st.markdown(f"**共 {len(sessions)} 條記錄**")
    st.markdown("---")

    for s in sessions:
        proj    = s.get("project_ref", "未填寫")
        ts      = s.get("upload_time", "")[:16].replace("T", " ")
        risk    = s.get("risk_level", "中風險")
        atype   = s.get("analysis_type", "")
        agents  = s.get("selected_agents", [])
        depts   = s.get("departments", [])
        fnames  = s.get("file_names", [])
        ftypes  = s.get("file_types", [])
        summary = s.get("analysis_summary", "")
        sid     = s.get("session_id", "")
        q       = s.get("question", "")

        risk_cls   = _RISK_CLASS.get(risk, "risk-medium")
        risk_emoji = _RISK_EMOJI.get(risk, "🟠")

        # Agent tags
        agent_tags_html = "".join(
            f'<span class="agent-tag">{a}</span>' for a in agents
        ) if agents else '<span class="agent-tag">—</span>'

        # Dept tags
        dept_tags_html = "".join(
            f'<span class="dept-tag">{d}</span>' for d in depts
        ) if depts else '<span class="dept-tag">—</span>'

        # File info
        file_count = len(fnames)
        file_type_str = "、".join(set(ftypes)) if ftypes else "—"
        file_names_str = "、".join(fnames) if fnames else "—"

        st.markdown(f"""
<div class="history-card">
  <div class="history-card-header">
    <div>
      <span class="history-proj">📁 {proj}</span>
      &nbsp;&nbsp;
      <span class="risk-badge {risk_cls}">{risk_emoji} {risk}</span>
    </div>
    <span class="history-date">🕐 {ts}</span>
  </div>
  <div style="font-size:0.88rem; color:#444; margin-bottom:0.4rem;">
    <strong>分析類型：</strong>{atype}
    &nbsp;&nbsp;
    <strong>文件數量：</strong>{file_count} 個
    &nbsp;&nbsp;
    <strong>文件類型：</strong>{file_type_str}
  </div>
  <div style="font-size:0.85rem; color:#555; margin-bottom:0.3rem;">
    <strong>文件名稱：</strong>{file_names_str}
  </div>
  <div style="margin-bottom:0.3rem;">
    <strong style="font-size:0.85rem;">參與 Agent：</strong>{agent_tags_html}
  </div>
  <div style="margin-bottom:0.3rem;">
    <strong style="font-size:0.85rem;">涉及部門：</strong>{dept_tags_html}
  </div>
  <div class="summary-text">
    <strong>問題：</strong>{q[:120] + ('…' if len(q) > 120 else '')}<br/>
    <strong>摘要：</strong>{summary}
  </div>
  <div style="font-size:0.75rem; color:#aaa; margin-top:0.5rem;">Session ID: {sid}</div>
</div>
""", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; color:#999; padding:1.5rem 0 0.5rem 0; font-size:0.82rem;">
    Buildway Tech (HK) Limited | HK-AICOS Phase 2.5E
</div>
""", unsafe_allow_html=True)
