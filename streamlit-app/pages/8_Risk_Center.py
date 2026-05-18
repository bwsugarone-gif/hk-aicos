# -*- coding: utf-8 -*-
"""
pages/8_Risk_Center.py
HK-AICOS Phase 3.1C — 工程風險中心
"""

import json
from collections import Counter
from datetime import date
from html import escape
from pathlib import Path
import sys

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logo_helper import sidebar_logo


BASE_DIR = Path(__file__).parent.parent
MEMORY_FILE = BASE_DIR / "data" / "session_memory.json"
RISK_ORDER = {"高風險": 3, "極高風險": 3, "中風險": 2, "低風險": 1}
RISK_FILTERS = ["全部", "高風險", "中風險", "低風險"]


st.set_page_config(
    page_title="工程風險中心 | HK-AICOS",
    page_icon="⚠️",
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

    .stat-card {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(26,58,92,0.08);
        border-top: 4px solid #c9a84c;
        min-height: 96px;
    }
    .stat-label { color: #666; font-size: 0.82rem; }
    .stat-value { color: #1a3a5c; font-size: 1.35rem; font-weight: 800; margin-top: 0.25rem; }

    .risk-card {
        background: white;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        box-shadow: 0 2px 8px rgba(26,58,92,0.08);
        margin-bottom: 0.9rem;
        border-left: 5px solid #ffc107;
    }
    .risk-card.high { border-left-color: #dc3545; }
    .risk-card.medium { border-left-color: #ffc107; }
    .risk-card.low { border-left-color: #28a745; }
    .risk-title {
        color: #1a3a5c;
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
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
    .risk-high { background: #fde8eb; color: #c0152a; border-color: #dc3545; }
    .risk-medium { background: #fff4e0; color: #b85c00; border-color: #ffc107; }
    .risk-low { background: #e6f4ec; color: #1a7a3c; border-color: #28a745; }
    .small-muted {
        color: #555;
        font-size: 0.86rem;
        line-height: 1.55;
    }
    .detail-box {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        border-left: 4px solid #1a3a5c;
        margin-top: 0.8rem;
    }

    @media (max-width: 768px) {
        .page-header { padding: 1.4rem 1rem; }
        .page-header h2 { font-size: 1.3rem; }
        .risk-card { padding: 0.9rem 1rem; }
        .stat-card { min-height: auto; }
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
    st.page_link("pages/9_Action_Tracker.py", label="✅ 跟進事項中心")
    st.page_link("pages/6_Memory_Manager.py", label="🧠 工程記憶管理")
    st.page_link("pages/5_Translate.py", label="📑 文件翻譯與轉換")
    st.page_link("pages/4_About.py", label="ℹ️ 關於 Buildway Tech")
    st.markdown("---")
    st.markdown('<div style="font-size:0.78rem;color:#aac4e0;">集中查看工程風險，不會修改資料。</div>', unsafe_allow_html=True)


def _load_sessions() -> tuple[list, str, bool]:
    if not MEMORY_FILE.exists():
        return [], "", False
    try:
        data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [], f"JSON 格式錯誤：{exc}", True
    except Exception as exc:
        return [], f"讀取風險紀錄失敗：{exc}", True
    if not isinstance(data, list):
        return [], "JSON 格式錯誤：風險紀錄必須是 session list。", True
    return data, "", True


def _normalise_risk(risk: str) -> str:
    return "高風險" if str(risk or "") == "極高風險" else str(risk or "中風險")


def _risk_value(risk: str) -> int:
    return RISK_ORDER.get(str(risk or "中風險"), 2)


def _risk_class(risk: str) -> str:
    if risk == "高風險":
        return "risk-high"
    if risk == "低風險":
        return "risk-low"
    return "risk-medium"


def _card_class(risk: str) -> str:
    if risk == "高風險":
        return "high"
    if risk == "低風險":
        return "low"
    return "medium"


def _time_value(record: dict) -> str:
    return str(record.get("upload_time", "") or record.get("time", ""))


def _date_value(record: dict) -> str:
    return _time_value(record)[:10]


def _join(items: list) -> str:
    cleaned = [str(item) for item in (items or []) if str(item).strip()]
    return "、".join(sorted(set(cleaned))) if cleaned else "—"


def _truncate(text: str, limit: int = 160) -> str:
    value = str(text or "").strip()
    if len(value) <= limit:
        return value or "—"
    return value[:limit] + "..."


def _risk_records(sessions: list) -> list:
    records = []
    for session in sessions:
        departments = session.get("departments", []) or session.get("government_departments", []) or []
        records.append({
            "project_ref": str(session.get("project_ref", "未填寫") or "未填寫"),
            "session_id": str(session.get("session_id", "") or ""),
            "upload_time": _time_value(session),
            "risk_level": _normalise_risk(
                session.get("calibrated_risk_level")
                or session.get("risk_level", "中風險")
            ),
            "original_risk_level": _normalise_risk(
                session.get("original_risk_level")
                or session.get("risk_level", "中風險")
            ),
            "calibrated_risk_level": _normalise_risk(
                session.get("calibrated_risk_level")
                or session.get("risk_level", "中風險")
            ),
            "highest_risk_agent": str(session.get("highest_risk_agent", "") or ""),
            "selected_agents": list(session.get("selected_agents", []) or []),
            "departments": list(departments or []),
            "question": str(session.get("question", "") or ""),
            "analysis_summary": str(session.get("analysis_summary", "") or session.get("summary", "") or ""),
            "file_names": list(session.get("file_names", []) or []),
        })
    return sorted(records, key=lambda r: (_risk_value(r["risk_level"]), r["upload_time"]), reverse=True)


def _apply_filters(records: list, project_ref: str, risk: str, agent: str, department: str, day_filter) -> list:
    query = project_ref.strip().lower()
    selected_date = day_filter.isoformat() if day_filter else ""
    filtered = []
    for record in records:
        if query and query not in record["project_ref"].lower():
            continue
        if risk != "全部" and record["risk_level"] != risk:
            continue
        if agent != "全部" and agent not in record["selected_agents"]:
            continue
        if department != "全部" and department not in record["departments"]:
            continue
        if selected_date and record["upload_time"][:10] != selected_date:
            continue
        filtered.append(record)
    return filtered


st.markdown("""
<div class="page-header">
    <h2>⚠️ 工程風險中心</h2>
    <p>集中查看、分類及追蹤所有工程風險紀錄。</p>
</div>
""", unsafe_allow_html=True)

sessions, load_error, memory_exists = _load_sessions()
st.markdown(f"**風險紀錄來源：** `{MEMORY_FILE}`")

if load_error:
    st.error(load_error)
    st.stop()

if not memory_exists or not sessions:
    st.info("暫未有風險紀錄")
    st.stop()

records = _risk_records(sessions)
if not records:
    st.info("暫未有風險紀錄")
    st.stop()

counts = Counter(record["risk_level"] for record in records)
projects_count = len({record["project_ref"] for record in records})
high_dates = [record["upload_time"] for record in records if record["risk_level"] == "高風險" and record["upload_time"]]
latest_high_date = max(high_dates)[:10] if high_dates else "—"

stat_cols = st.columns(5)
stats = [
    ("高風險數量", counts.get("高風險", 0)),
    ("中風險數量", counts.get("中風險", 0)),
    ("低風險數量", counts.get("低風險", 0)),
    ("涉及工程數量", projects_count),
    ("最近一次高風險日期", latest_high_date),
]
for col, (label, value) in zip(stat_cols, stats):
    with col:
        st.markdown(
            f'<div class="stat-card"><div class="stat-label">{label}</div>'
            f'<div class="stat-value">{value}</div></div>',
            unsafe_allow_html=True,
        )

all_agents = sorted({agent for record in records for agent in record["selected_agents"]})
all_departments = sorted({dept for record in records for dept in record["departments"]})

st.markdown("### 篩選")
col_project, col_risk, col_agent, col_dept, col_date = st.columns(5)
with col_project:
    project_filter = st.text_input("Project Ref", placeholder="例如：BW-2026")
with col_risk:
    risk_filter = st.selectbox("風險級別", RISK_FILTERS)
with col_agent:
    agent_filter = st.selectbox("Agent", ["全部"] + all_agents)
with col_dept:
    department_filter = st.selectbox("政府部門", ["全部"] + all_departments)
with col_date:
    use_date_filter = st.checkbox("啟用日期")
    date_filter = st.date_input("日期", value=date.today(), disabled=not use_date_filter)

filtered = _apply_filters(
    records,
    project_ref=project_filter,
    risk=risk_filter,
    agent=agent_filter,
    department=department_filter,
    day_filter=date_filter if use_date_filter else None,
)

st.markdown(f"### 風險列表（{len(filtered)} 條）")
if not filtered:
    st.info("暫未有風險紀錄")
    st.stop()

for idx, record in enumerate(filtered):
    risk_cls = _risk_class(record["risk_level"])
    card_cls = _card_class(record["risk_level"])
    st.markdown(
        f"""
<div class="risk-card {card_cls}">
  <div class="risk-title">{escape(record["project_ref"])}</div>
  <span class="pill {risk_cls}">{escape(record["risk_level"])}</span>
  <span class="pill">原始：{escape(record["original_risk_level"])}</span>
  <span class="pill">校準：{escape(record["calibrated_risk_level"])}</span>
  <span class="pill">{escape(record["upload_time"] or "—")}</span>
  <span class="pill">Session：{escape(record["session_id"] or "—")}</span>
  <div class="small-muted" style="margin-top:0.5rem;">
    問題：{escape(_truncate(record["question"], 120))}<br/>
    摘要：{escape(_truncate(record["analysis_summary"], 180))}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

st.markdown("---")
st.markdown("### 風險詳情")
detail_options = [
    f"{record['risk_level']}｜{record['project_ref']}｜{record['upload_time']}｜{record['session_id']}"
    for record in filtered
]
selected_label = st.selectbox("點選一條風險", detail_options)
selected_index = detail_options.index(selected_label)
selected = filtered[selected_index]

st.markdown(
    f"""
<div class="detail-box">
  <div class="risk-title">工程編號：{escape(selected["project_ref"])}</div>
  <div class="small-muted">
    分析時間：{escape(selected["upload_time"] or "—")}<br/>
    原始風險：{escape(selected["original_risk_level"])}<br/>
    校準風險：{escape(selected["calibrated_risk_level"])}<br/>
    主要影響 Agent：{escape(selected["highest_risk_agent"] or "—")}<br/>
    相關文件：{escape(_join(selected["file_names"]))}<br/>
    問題：{escape(selected["question"] or "—")}<br/>
    分析摘要：{escape(selected["analysis_summary"] or "—")}<br/>
    涉及部門：{escape(_join(selected["departments"]))}<br/>
    參與 Agent：{escape(_join(selected["selected_agents"]))}<br/>
    Session ID：{escape(selected["session_id"] or "—")}
  </div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown("""
<div style="text-align:center; color:#999; padding:1.5rem 0 0.5rem 0; font-size:0.82rem;">
    Buildway Tech (HK) Limited | HK-AICOS Phase 3.1C
</div>
""", unsafe_allow_html=True)
