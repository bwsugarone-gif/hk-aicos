# -*- coding: utf-8 -*-
"""
pages/7_Project_Dashboard.py
HK-AICOS Phase 3.1B — 工程總覽 Dashboard
"""

import json
from collections import defaultdict
from html import escape
from pathlib import Path
import sys

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logo_helper import sidebar_logo


BASE_DIR = Path(__file__).parent.parent
MEMORY_FILE = BASE_DIR / "data" / "session_memory.json"
RISK_ORDER = {"高風險": 3, "極高風險": 3, "中風險": 2, "低風險": 1}
RISK_LABELS = ["全部", "高風險", "中風險", "低風險"]


st.set_page_config(
    page_title="工程總覽 | HK-AICOS",
    page_icon="📊",
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

    .project-card {
        background: white;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        box-shadow: 0 2px 8px rgba(26,58,92,0.08);
        border-left: 5px solid #c9a84c;
        margin-bottom: 1rem;
    }
    .project-title {
        color: #1a3a5c;
        font-size: 1.05rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .metric-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-bottom: 0.55rem;
    }
    .metric-pill {
        display: inline-block;
        background: #eaf0fb;
        color: #1a3a5c;
        border: 1px solid #d0d7e3;
        border-radius: 14px;
        padding: 0.12rem 0.6rem;
        font-size: 0.78rem;
        font-weight: 600;
    }
    .risk-high { background: #fde8eb; color: #c0152a; border-color: #dc3545; }
    .risk-medium { background: #fff4e0; color: #b85c00; border-color: #ffc107; }
    .risk-low { background: #e6f4ec; color: #1a7a3c; border-color: #28a745; }
    .summary-block {
        font-size: 0.88rem;
        color: #555;
        line-height: 1.55;
        border-top: 1px solid #f0f0f0;
        padding-top: 0.55rem;
        margin-top: 0.55rem;
    }
    .timeline-item {
        background: #f8f9fa;
        border-radius: 8px;
        border-left: 4px solid #1a3a5c;
        padding: 0.85rem 1rem;
        margin-bottom: 0.65rem;
    }
    .small-muted {
        color: #666;
        font-size: 0.82rem;
        line-height: 1.5;
    }

    @media (max-width: 768px) {
        .page-header { padding: 1.4rem 1rem; }
        .page-header h2 { font-size: 1.3rem; }
        .project-card { padding: 0.9rem 1rem; }
        .metric-row { gap: 0.3rem; }
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
    st.page_link("pages/7_Project_Dashboard.py", label="📊 工程總覽")
    st.page_link("pages/8_Risk_Center.py", label="⚠️ 工程風險中心")
    st.page_link("pages/6_Memory_Manager.py", label="🧠 工程記憶管理")
    st.page_link("pages/5_Translate.py", label="📑 文件翻譯與轉換")
    st.page_link("pages/4_About.py", label="ℹ️ 關於 Buildway Tech")
    st.markdown("---")
    st.markdown('<div style="font-size:0.78rem;color:#aac4e0;">從工程記憶讀取總覽，不會修改資料。</div>', unsafe_allow_html=True)


def _load_sessions() -> tuple[list, str, bool]:
    if not MEMORY_FILE.exists():
        return [], "", False
    try:
        data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [], f"JSON 格式錯誤：{exc}", True
    except Exception as exc:
        return [], f"讀取工程紀錄失敗：{exc}", True
    if not isinstance(data, list):
        return [], "JSON 格式錯誤：工程紀錄必須是 session list。", True
    return data, "", True


def _risk_value(risk: str) -> int:
    return RISK_ORDER.get(str(risk or "中風險"), 2)


def _normalise_risk(risk: str) -> str:
    return "高風險" if str(risk or "") == "極高風險" else str(risk or "中風險")


def _risk_class(risk: str) -> str:
    if risk in ("高風險", "極高風險"):
        return "risk-high"
    if risk == "低風險":
        return "risk-low"
    return "risk-medium"


def _join(items: list) -> str:
    cleaned = [str(item) for item in (items or []) if str(item).strip()]
    return "、".join(sorted(set(cleaned))) if cleaned else "—"


def _session_time(session: dict) -> str:
    return str(session.get("upload_time", "") or session.get("time", ""))


def _project_ref(session: dict) -> str:
    return str(session.get("project_ref", "未填寫") or "未填寫")


def _project_records(sessions: list) -> list:
    grouped = defaultdict(list)
    for session in sessions:
        grouped[_project_ref(session)].append(session)

    records = []
    for project_ref, items in grouped.items():
        ordered = sorted(items, key=_session_time, reverse=True)
        latest = ordered[0] if ordered else {}
        risks = [_normalise_risk(s.get("risk_level", "中風險")) for s in ordered]
        highest_risk = max(risks, key=_risk_value) if risks else "中風險"
        departments = []
        agents = []
        file_names = []
        pdf_count = 0
        for s in ordered:
            departments.extend(s.get("departments", []) or s.get("government_departments", []) or [])
            agents.extend(s.get("selected_agents", []) or [])
            file_names.extend(s.get("file_names", []) or [])
            if s.get("report_path") or s.get("pdf_path"):
                pdf_count += 1
        records.append({
            "project_ref": project_ref,
            "sessions": ordered,
            "session_count": len(ordered),
            "latest_time": _session_time(latest),
            "highest_risk": highest_risk,
            "departments": sorted(set(str(d) for d in departments if str(d).strip())),
            "agents": sorted(set(str(a) for a in agents if str(a).strip())),
            "file_count": len([name for name in file_names if str(name).strip()]),
            "pdf_count": pdf_count,
            "latest_question": str(latest.get("question", "") or ""),
            "latest_summary": str(
                latest.get("analysis_summary", "")
                or latest.get("summary", "")
                or ""
            ),
        })

    return sorted(records, key=lambda r: (_risk_value(r["highest_risk"]), r["latest_time"]), reverse=True)


def _filter_records(records: list, query: str, risk: str, agent: str, department: str) -> list:
    query_norm = query.strip().lower()
    filtered = []
    for record in records:
        if query_norm and query_norm not in record["project_ref"].lower():
            continue
        if risk != "全部" and record["highest_risk"] != risk:
            continue
        if agent != "全部" and agent not in record["agents"]:
            continue
        if department != "全部" and department not in record["departments"]:
            continue
        filtered.append(record)
    return filtered


def _truncate(text: str, limit: int = 180) -> str:
    value = str(text or "").strip()
    if len(value) <= limit:
        return value or "—"
    return value[:limit] + "..."


st.markdown("""
<div class="page-header">
    <h2>📊 工程總覽</h2>
    <p>集中查看所有工程狀態、風險、Agent、涉及部門及最近分析摘要。</p>
</div>
""", unsafe_allow_html=True)

sessions, load_error, memory_exists = _load_sessions()
st.markdown(f"**工程紀錄來源：** `{MEMORY_FILE}`")

if load_error:
    st.error(load_error)
    st.stop()

if not memory_exists or not sessions:
    st.info("暫未有工程紀錄")
    st.stop()

records = _project_records(sessions)

all_agents = sorted({agent for record in records for agent in record["agents"]})
all_departments = sorted({dept for record in records for dept in record["departments"]})

st.markdown("### 篩選")
col_search, col_risk, col_agent, col_dept = st.columns(4)
with col_search:
    search_text = st.text_input("Project Ref 搜尋", placeholder="例如：BW-2026")
with col_risk:
    risk_filter = st.selectbox("風險級別", RISK_LABELS)
with col_agent:
    agent_filter = st.selectbox("Agent", ["全部"] + all_agents)
with col_dept:
    dept_filter = st.selectbox("政府部門", ["全部"] + all_departments)

filtered_records = _filter_records(records, search_text, risk_filter, agent_filter, dept_filter)

st.markdown(f"### 工程列表（{len(filtered_records)} 個）")
if not filtered_records:
    st.info("未找到符合條件的工程。")
    st.stop()

for record in filtered_records:
    risk_cls = _risk_class(record["highest_risk"])
    st.markdown(
        f"""
<div class="project-card">
  <div class="project-title">{escape(record["project_ref"])}</div>
  <div class="metric-row">
    <span class="metric-pill">Session：{record["session_count"]}</span>
    <span class="metric-pill {risk_cls}">最高風險：{record["highest_risk"]}</span>
    <span class="metric-pill">最近：{escape(record["latest_time"] or "—")}</span>
    <span class="metric-pill">文件：{record["file_count"]}</span>
    <span class="metric-pill">PDF：{record["pdf_count"]}</span>
  </div>
  <div class="small-muted">
    涉及政府部門：{escape(_join(record["departments"]))}<br/>
    已使用 Agent：{escape(_join(record["agents"]))}
  </div>
  <div class="summary-block">
    <strong>最近一次問題摘要：</strong>{escape(_truncate(record["latest_question"]))}<br/>
    <strong>最近一次分析摘要：</strong>{escape(_truncate(record["latest_summary"]))}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

st.markdown("---")
st.markdown("### Project Detail View")

selected_project = st.selectbox(
    "選擇工程查看詳情",
    [record["project_ref"] for record in filtered_records],
)
selected_record = next(record for record in filtered_records if record["project_ref"] == selected_project)

st.markdown(f"#### {selected_project}")
st.markdown(
    f"最高風險：**{selected_record['highest_risk']}**　"
    f"Session：**{selected_record['session_count']}**　"
    f"文件：**{selected_record['file_count']}**　"
    f"PDF：**{selected_record['pdf_count']}**"
)

st.markdown("#### Timeline / Sessions")
for session in selected_record["sessions"]:
    file_names = _join(session.get("file_names", []))
    agents = _join(session.get("selected_agents", []))
    departments = _join(session.get("departments", []) or session.get("government_departments", []))
    risk = _normalise_risk(session.get("risk_level", "中風險"))
    risk_cls = _risk_class(risk)
    st.markdown(
        f"""
<div class="timeline-item">
  <div class="metric-row">
    <span class="metric-pill">{escape(_session_time(session) or "—")}</span>
    <span class="metric-pill {risk_cls}">{escape(risk)}</span>
    <span class="metric-pill">Session：{escape(str(session.get("session_id", "—")))}</span>
  </div>
  <div class="small-muted">
    相關文件名：{escape(file_names)}<br/>
    參與 Agent：{escape(agents)}<br/>
    涉及部門：{escape(departments)}<br/>
    問題：{escape(_truncate(session.get("question", ""), 220))}<br/>
    每次分析摘要：{escape(_truncate(session.get("analysis_summary", "") or session.get("summary", ""), 260))}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

st.markdown("#### Risk History")
risk_history = defaultdict(int)
for session in selected_record["sessions"]:
    risk_history[_normalise_risk(session.get("risk_level", "中風險"))] += 1

for risk in ["高風險", "中風險", "低風險"]:
    st.markdown(f"- {risk}：{risk_history.get(risk, 0)} 次")

st.markdown("""
<div style="text-align:center; color:#999; padding:1.5rem 0 0.5rem 0; font-size:0.82rem;">
    Buildway Tech (HK) Limited | HK-AICOS Phase 3.1B
</div>
""", unsafe_allow_html=True)
