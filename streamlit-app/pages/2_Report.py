"""
pages/2_Report.py
HK-AICOS Phase 2.0 - 分析報告頁（客戶版）

Buildway Tech (HK) Limited
"""

import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.risk_classifier import get_risk_info
from utils.report_generator import generate_pdf_report
from utils.lang import REPORT, NAV, BRAND, AGENTS, AGENT_ORDER
from utils.logo_helper import sidebar_logo

st.set_page_config(
    page_title="分析報告 | HK-AICOS",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a3a5c 0%, #0f2942 100%);
    }
    [data-testid="stSidebar"] * { color: white !important; }

    .agent-badge {
        display: inline-block;
        background: #1a3a5c;
        color: white;
        border-radius: 20px;
        padding: 0.15rem 0.75rem;
        font-size: 0.78rem;
        font-weight: 600;
        margin: 0.15rem 0.2rem 0.15rem 0;
    }
    .agent-badge-row {
        margin-top: 0.4rem;
        margin-bottom: 0.2rem;
    }

    .page-header {
        background: linear-gradient(135deg, #1a3a5c 0%, #2d5a8e 100%);
        color: white;
        padding: 1.8rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
    }
    .page-header h2 { font-size: 1.6rem; margin: 0 0 0.3rem 0; }
    .page-header p { font-size: 1rem; opacity: 0.9; margin: 0; }

    .report-section {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(26,58,92,0.08);
        margin-bottom: 1.2rem;
    }
    .report-section h3 {
        color: #1a3a5c;
        font-size: 1.1rem;
        border-bottom: 2px solid #c9a84c;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
    }

    .risk-banner-low {
        background: #d4edda; border: 3px solid #28a745;
        border-radius: 12px; padding: 1.2rem; text-align: center;
        margin: 1rem 0;
    }
    .risk-banner-medium {
        background: #fff3cd; border: 3px solid #ffc107;
        border-radius: 12px; padding: 1.2rem; text-align: center;
        margin: 1rem 0;
    }
    .risk-banner-high {
        background: #f8d7da; border: 3px solid #dc3545;
        border-radius: 12px; padding: 1.2rem; text-align: center;
        margin: 1rem 0;
    }

    .result-content {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1.2rem;
        border-left: 4px solid #4a6fa5;
        font-size: 0.97rem;
        line-height: 1.7;
    }

    .professional-alert {
        background: #fff3cd;
        border: 2px solid #ffc107;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.6rem;
        font-size: 0.95rem;
    }

    .disclaimer-box {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1rem 1.5rem;
        border-left: 4px solid #6c757d;
        font-size: 0.82rem;
        color: #555;
        margin-top: 1rem;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #1a3a5c 0%, #2d5a8e 100%);
        color: white;
        font-weight: 700;
        font-size: 1.1rem;
        padding: 0.9rem 2rem;
        border: none;
        border-radius: 10px;
        width: 100%;
    }

    @media (max-width: 768px) {
        .page-header h2 { font-size: 1.3rem; }
        .report-section { padding: 1rem; }
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    sidebar_logo()
    st.markdown("---")
    st.page_link("app.py", label="🏠 首頁")
    st.page_link("pages/1_Upload.py", label="📤 上載分析")
    st.page_link("pages/2_Report.py", label="📄 分析報告")
    st.page_link("pages/3_History.py", label="🕘 歷史紀錄")
    st.page_link("pages/4_About.py", label="ℹ️ 關於 Buildway Tech")
    st.markdown("---")
    st.markdown('<div style="font-size:0.78rem; color:#aac4e0;">🔒 所有資料安全處理</div>', unsafe_allow_html=True)

# ── Page Header ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <h2>📄 分析報告</h2>
    <p>查看 AI 工程分析結果及下載 PDF 報告。</p>
</div>
""", unsafe_allow_html=True)

# ── 無分析結果 ────────────────────────────────────────────────────────────────
if "last_analysis" not in st.session_state:
    st.info("📭 暫無分析結果。請先前往「上載分析」頁面進行分析。")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.page_link("pages/1_Upload.py", label="📤 前往上載分析")
    st.stop()

# ── 顯示分析結果 ──────────────────────────────────────────────────────────────
data = st.session_state["last_analysis"]
risk_level = data.get("risk_level", "中風險")

# 統一風險級別（只保留三級）
if risk_level == "極高風險":
    risk_level = "高風險"
risk_info = get_risk_info(risk_level)

# 風險顏色對應
risk_css_class = {
    "低風險": "risk-banner-low",
    "中風險": "risk-banner-medium",
    "高風險": "risk-banner-high",
}.get(risk_level, "risk-banner-medium")

risk_emoji = {"低風險": "🟢", "中風險": "🟠", "高風險": "🔴"}.get(risk_level, "🟠")
risk_color = {"低風險": "#28a745", "中風險": "#e67e00", "高風險": "#dc3545"}.get(risk_level, "#e67e00")

# ── 風險橫幅 ──────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="{risk_css_class}">
        <div style="font-size:2rem; margin-bottom:0.3rem;">{risk_emoji}</div>
        <div style="font-size:1.6rem; font-weight:700; color:{risk_color};">{risk_level}</div>
        <div style="font-size:1rem; color:{risk_color}; margin-top:0.3rem;">
            {risk_info.get('description', '')}
        </div>
        <div style="font-size:0.9rem; color:{risk_color}; font-weight:600; margin-top:0.4rem;">
            建議行動：{risk_info.get('action', '')} | 回應時間：{risk_info.get('response_time', '')}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── 問題摘要 ──────────────────────────────────────────────────────────────────
st.markdown('<div class="report-section">', unsafe_allow_html=True)
st.markdown('<h3>📋 問題摘要</h3>', unsafe_allow_html=True)

display_name = data.get("analysis_display_name", data.get("analysis_type", ""))
col1, col2 = st.columns(2)
with col1:
    st.markdown(f"**分析類型：** {display_name}")
    st.markdown(f"**工程編號：** {data.get('project_ref', '未填寫') or '未填寫'}")
with col2:
    st.markdown(f"**上載文件：** {data.get('file_name', '無') or '無'}")
    st.markdown(f"**風險級別：** {risk_emoji} {risk_level}")

st.markdown(f"**問題：** {data.get('question', '')}")

# ── 參與 Agent 標籤 ───────────────────────────────────────────────────────────
selected_agents = data.get("selected_agents", [])
if selected_agents:
    badges_html = "".join(
        f'<span class="agent-badge">{AGENTS[aid]["icon"]} {AGENTS[aid]["label"]}</span>'
        for aid in selected_agents
        if aid in AGENTS
    )
    st.markdown(
        f'<div class="agent-badge-row"><strong>參與 Agent：</strong>{badges_html}</div>',
        unsafe_allow_html=True,
    )

st.markdown('</div>', unsafe_allow_html=True)

# ── 分析內容 ──────────────────────────────────────────────────────────────────
st.markdown('<div class="report-section">', unsafe_allow_html=True)
st.markdown('<h3>📊 工程分析報告</h3>', unsafe_allow_html=True)

analysis_text = data.get("analysis_result", "")
# 清理任何技術性內容（不應出現在客戶版）
for tech_phrase in [
    "[示範模式", "[DEMO MODE", "No API Key", "API KEY", "Claude", "Anthropic",
    "This is what would be sent", "The AI would analyze", "backend", "prompt", "token",
]:
    if tech_phrase.lower() in analysis_text.lower():
        analysis_text = "分析結果暫時未能顯示。請重新進行分析或聯絡 Buildway Tech 取得協助。"
        break

st.markdown(
    f'<div class="result-content">{analysis_text.replace(chr(10), "<br/>")}</div>',
    unsafe_allow_html=True,
)
st.markdown('</div>', unsafe_allow_html=True)

# ── 可能涉及部門 ──────────────────────────────────────────────────────────────
from utils.report_generator import _department_mapping

_dept_combined = "\n".join([
    data.get("analysis_type", ""),
    data.get("question", ""),
    analysis_text,
])
_departments = _department_mapping(_dept_combined)

st.markdown('<div class="report-section">', unsafe_allow_html=True)
st.markdown('<h3>🏛️ 可能涉及部門</h3>', unsafe_allow_html=True)
if _departments:
    dept_tags = "".join(
        f'<span style="display:inline-block;background:#eaf0fb;color:#1a3a5c;'
        f'border:1px solid #d0d7e3;border-radius:16px;padding:0.2rem 0.85rem;'
        f'font-size:0.9rem;font-weight:600;margin:0.2rem 0.3rem 0.2rem 0;">{d}</span>'
        for d in _departments
    )
    st.markdown(dept_tags, unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.85rem;color:#666;margin-top:0.6rem;">'
        '如不確定，需由相關專業人士確認實際監管部門。</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '<div style="font-size:0.9rem;color:#666;">需由相關專業人士確認實際監管部門。</div>',
        unsafe_allow_html=True,
    )
st.markdown('</div>', unsafe_allow_html=True)

# ── 參考文件 ──────────────────────────────────────────────────────────────────
try:
    from utils.rag_reader import get_matched_rag_docs
    from utils.agent_router import AGENT_DEFINITIONS as _AD_REF

    _reg_keys = []
    for aid in selected_agents:
        if aid in _AD_REF:
            for reg in _AD_REF[aid]["regulations"]:
                if reg not in _reg_keys:
                    _reg_keys.append(reg)

    _rag_docs = get_matched_rag_docs(_reg_keys, top_k=3) if _reg_keys else []
except Exception:
    _rag_docs = []

if _rag_docs:
    st.markdown('<div class="report-section">', unsafe_allow_html=True)
    st.markdown('<h3>📚 參考文件</h3>', unsafe_allow_html=True)
    for _doc in _rag_docs:
        _dept  = _doc.get("source_department", "")
        _cat   = _doc.get("category", "").replace("_", " ")
        _summ  = _doc.get("summary", "")
        _fname = _doc.get("file_name", "")
        _tag   = f" · {_dept}" if _dept else ""
        _cat_tag = f" · {_cat}" if _cat else ""
        st.markdown(
            f'<div style="font-size:0.9rem;padding:0.4rem 0;border-bottom:1px solid #f0f0f0;">'
            f'📄 <strong>{_fname}</strong>{_tag}{_cat_tag}'
            + (f'<br/><span style="color:#666;font-size:0.82rem;">{_summ}</span>' if _summ else "")
            + "</div>",
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

# ── 需要專業人士確認 ──────────────────────────────────────────────────────────
professionals = data.get("professionals", [])
if professionals:
    st.markdown('<div class="report-section">', unsafe_allow_html=True)
    st.markdown('<h3>👷 需要專業人士確認</h3>', unsafe_allow_html=True)
    for prof in professionals:
        st.markdown(
            f'<div class="professional-alert">⚠️ <strong>{prof}</strong> — 此事項需要由以上專業人士確認後方可執行。</div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

# ── 下載 PDF ──────────────────────────────────────────────────────────────────
st.markdown('<div class="report-section">', unsafe_allow_html=True)
st.markdown('<h3>📥 下載報告</h3>', unsafe_allow_html=True)
st.markdown("下載 PDF 報告，方便在手機或電腦查閱，或透過 WhatsApp 分享。")

try:
    pdf_bytes = generate_pdf_report(
        analysis_type=display_name,
        question=data.get("question", ""),
        risk_level=risk_level,
        analysis_result=analysis_text,
        filename_hint=data.get("file_name", ""),
        professionals_required=professionals,
        project_ref=data.get("project_ref", ""),
        selected_agents=data.get("selected_agents") or None,
        session_id=data.get("session_id", ""),
    )
    safe_name = display_name.replace("/", "-").replace(" ", "-")
    st.download_button(
        label="📄 下載 PDF 報告",
        data=pdf_bytes,
        file_name=f"HK-AICOS-{safe_name}-報告.pdf",
        mime="application/pdf",
        use_container_width=True,
        type="primary",
    )
except ValueError as e:
    if str(e) == "AI 輸出已亂碼":
        st.error("AI 輸出已亂碼")
    else:
        st.error("PDF 生成失敗，請稍後再試。")
except Exception:
    st.error("PDF 生成失敗，請稍後再試。")

st.markdown('</div>', unsafe_allow_html=True)

# ── 免責聲明 ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="disclaimer-box">
<strong>⚠️ 重要免責聲明</strong><br/><br/>
本報告為 AI 輔助工程分析結果，只供初步參考及內部評估用途。<br/><br/>
所有涉及結構、安全、法規、消防、電力、水務、公共道路、掘路、高風險工序、合約或法律責任之事項，
必須由香港合資格專業人士最終確認。<br/><br/>
Buildway Tech (HK) Limited 不會取代認可人士、註冊工程師、安全主任、
註冊電業工程人員、持牌水喉匠、法律專業人士或相關政府部門之正式審批。
</div>
""", unsafe_allow_html=True)

# ── 重新分析 ──────────────────────────────────────────────────────────────────
st.markdown("<br/>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.page_link("pages/1_Upload.py", label="📤 重新上載分析")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; color:#999; padding:1.5rem 0 0.5rem 0; font-size:0.82rem;">
    Buildway Tech (HK) Limited | HK-AICOS Phase 2.0
</div>
""", unsafe_allow_html=True)
