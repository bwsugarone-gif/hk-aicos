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
from utils.report_generator import generate_pdf_report, highlight_report_keywords_html
from utils.site_logic_engine import format_site_logic_for_report
from utils.progress_tracker import format_progress_for_report
from utils.delay_concern_engine import format_delay_concern_for_report
from utils.resource_workforce_engine import format_resource_workforce_for_report
from utils.repeated_issue_detector import format_repeated_issues_for_report
from utils.lang import REPORT, NAV, BRAND, AGENTS, AGENT_ORDER
from utils.logo_helper import sidebar_logo
from utils.navigation import render_navigation_links
from utils.project_manager import load_project

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
    .report-keyword {
        color: #c0152a;
        font-weight: 700;
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

    .phase33-box {
        background: #f8f9fa;
        border-left: 4px solid #1a3a5c;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        font-size: 0.94rem;
        line-height: 1.7;
        margin-bottom: 0.75rem;
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
    render_navigation_links()
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
    if data.get("original_risk_level") and data.get("original_risk_level") != risk_level:
        st.markdown(f"**原始風險：** {data.get('original_risk_level')}")
    if data.get("highest_risk_agent"):
        st.markdown(f"**主要影響 Agent：** {data.get('highest_risk_agent')}")

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

# ── Project memory linkage ────────────────────────────────────────────────────
project_ref = data.get("project_ref", "").strip()
current_session_id = data.get("session_id", "")
if project_ref:
    try:
        project_memory = load_project(project_ref)
    except Exception:
        project_memory = {"sessions": [], "risks": []}

    project_sessions = [
        s for s in project_memory.get("sessions", [])
        if s.get("session_id") != current_session_id
    ]
    project_risks = project_memory.get("risks", [])

    st.markdown('<div class="report-section">', unsafe_allow_html=True)
    st.markdown('<h3>🧠 Project Memory</h3>', unsafe_allow_html=True)
    st.markdown(f"**工程歷史：** {len(project_sessions)} 次過往分析")
    st.markdown(f"**風險總數：** {len(project_risks)} 項")
    st.markdown(f"**未解決 / 需跟進風險：** {len([r for r in project_risks if r.get('status') != 'resolved'])} 項")

    if project_sessions:
        st.markdown("**過往摘要：**")
        for s in project_sessions[:3]:
            ts = (s.get("time", "") or "")[:16].replace("T", " ")
            st.markdown(
                f"- {ts}｜{s.get('analysis_type', '')}｜{s.get('risk_level', '')}："
                f"{s.get('summary', '')}"
            )

    if project_risks:
        st.markdown("**Risk Timeline：**")
        for risk in project_risks[:5]:
            ts = (risk.get("date", "") or "")[:10]
            st.markdown(
                f"- {ts}｜{risk.get('risk_level', '')}｜"
                f"{risk.get('status', 'open')}｜{risk.get('risk', '')}"
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
    f'<div class="result-content">{highlight_report_keywords_html(analysis_text).replace(chr(10), "<br/>")}</div>',
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

# ── Agent 衝突分析 ────────────────────────────────────────────────────────────
_conflict_result = data.get("conflict_result", {})
if _conflict_result and not _conflict_result.get("fallback_used"):
    _cr_conflicts   = _conflict_result.get("conflict_analysis", [])
    _cr_override    = _conflict_result.get("override_agent", "PM Agent")
    _cr_reason      = _conflict_result.get("override_reason", "")
    _cr_can         = _conflict_result.get("can_continue", "")
    _cr_merged      = _conflict_result.get("merged_risks", [])
    _cr_conf        = _conflict_result.get("agent_confidence", {})
    _cr_action      = _conflict_result.get("final_action_plan", [])
    _cr_rec         = _conflict_result.get("final_recommendation", "")

    _cc_color = {"Yes": "#28a745", "Limited": "#fd7e14", "No": "#dc3545"}.get(_cr_can, "#6c757d")
    _cc_label = {"Yes": "✅ 可繼續施工", "Limited": "⚠️ 有限度施工", "No": "🚫 須停工整改"}.get(_cr_can, _cr_can)

    st.markdown('<div class="report-section">', unsafe_allow_html=True)
    st.markdown('<h3>🤝 Agent 衝突分析</h3>', unsafe_allow_html=True)

    st.markdown(f"""
<div style="background:#fff8f0;border:1px solid #fd7e14;border-radius:8px;
            padding:0.9rem 1.1rem;margin-bottom:0.8rem;">
  <div style="margin-bottom:0.4rem;">
    可否繼續施工：<span style="color:{_cc_color};font-weight:700;">{_cc_label}</span>
  </div>
  <div style="font-size:0.9rem;color:#555;margin-bottom:0.3rem;">裁決依據：{_cr_override}</div>
  <div style="font-size:0.88rem;color:#666;">{_cr_reason}</div>
</div>
""", unsafe_allow_html=True)

    if _cr_rec:
        st.markdown(f"**最終建議：** {_cr_rec}")

    if _cr_conflicts:
        with st.expander("⚡ 衝突詳情"):
            for _c in _cr_conflicts:
                st.markdown(f"- {_c.get('description', '')}")

    if _cr_merged:
        with st.expander("🔗 跨 Agent 合併風險"):
            for _mr in _cr_merged[:5]:
                _agents_str = "、".join(_mr.get("agents", []))
                _mcat = _mr.get("category", "")
                _mcolor = {
                    "critical": "#6f0000", "high": "#dc3545",
                    "medium": "#fd7e14", "low": "#28a745",
                }.get(_mcat, "#6c757d")
                st.markdown(
                    f'<span style="color:{_mcolor};font-weight:600;">[{_mcat.upper()}]</span> '
                    f'{_mr.get("label","")} — 涉及：{_agents_str}',
                    unsafe_allow_html=True,
                )

    if _cr_conf:
        with st.expander("📊 Agent 信心分數"):
            for _aid, _conf in _cr_conf.items():
                st.markdown(f"- **{_aid}**：{int(_conf * 100)}%")

    if _cr_action:
        with st.expander("📋 最終行動計劃"):
            for _ap in _cr_action:
                st.markdown(f"- {_ap}")

    st.markdown('</div>', unsafe_allow_html=True)

# ── 現場 Context ──────────────────────────────────────────────────────────────
_site_context = data.get("site_context", {})
if _site_context and _site_context.get("context_available"):
    _sc_envs      = _site_context.get("environment_labels_zh", [])
    _sc_stage     = _site_context.get("stage_label_zh", "不明")
    _sc_seq       = _site_context.get("sequence_check", {})
    _sc_mod       = _site_context.get("risk_modifier", {})
    _sc_constr    = _site_context.get("site_constraints", [])
    _sc_conf      = _site_context.get("confidence", "low")
    _sc_seq_v     = _sc_seq.get("verdict", "unknown")
    _sc_seq_r     = _sc_seq.get("reason", "")
    _sc_modifier  = _sc_mod.get("combined_modifier", 1.0)
    _sc_notes     = _sc_mod.get("risk_notes", [])

    _conf_color = {"high": "#28a745", "medium": "#fd7e14", "low": "#6c757d"}.get(_sc_conf, "#6c757d")
    _conf_label = {"high": "高", "medium": "中", "low": "低"}.get(_sc_conf, "低")
    _seq_icon   = {"ok": "✅", "warning": "⚠️", "unusual": "🚫", "unknown": "❓"}.get(_sc_seq_v, "❓")
    _seq_label  = {"ok": "工序合理", "warning": "工序需注意", "unusual": "工序異常", "unknown": "無法判斷"}.get(_sc_seq_v, "無法判斷")

    st.markdown("""
<div style="background:#f0f4ff;border:1px solid #2d5a8e;border-radius:10px;
            padding:1rem 1.2rem;margin:1rem 0;">
  <div style="font-size:1rem;font-weight:700;color:#1a3a5c;margin-bottom:0.7rem;">
    🏗️ 現場 Context 分析
  </div>
""", unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        env_str = "、".join(_sc_envs) if _sc_envs else "不明"
        st.metric("現場環境", env_str)
    with col_b:
        st.metric("工程階段", _sc_stage)
    with col_c:
        st.metric("Context 信心", f"{_conf_label}信心", delta=None)

    st.markdown(f"""
  <div style="margin:0.6rem 0 0.3rem 0;font-size:0.95rem;">
    工序判斷：<span style="font-weight:700;">{_seq_icon} {_seq_label}</span>
  </div>
""", unsafe_allow_html=True)
    if _sc_seq_r and _sc_seq_v != "ok":
        st.warning(_sc_seq_r)

    if _sc_modifier > 1.0:
        st.markdown(
            f'<div style="font-size:0.9rem;color:#cc6600;margin:0.3rem 0;">'
            f'⚡ 現場風險加乘：<b>×{_sc_modifier:.1f}</b></div>',
            unsafe_allow_html=True,
        )

    if _sc_notes:
        with st.expander("⚠️ 現場危險因素"):
            for _n in _sc_notes:
                st.markdown(f"- {_n}")

    if _sc_constr:
        with st.expander("🔒 現場限制"):
            for _c in _sc_constr:
                st.markdown(f"- {_c}")

    st.markdown('</div>', unsafe_allow_html=True)

# ── Phase 3.3A/B: Site Logic + Progress Tracking ─────────────────────────────
_site_logic_result = data.get("site_logic_result", {})
_progress_result = data.get("progress_result", {})
_delay_concern_result = data.get("delay_concern_result", {})


def _has_meaningful_text(text: str) -> bool:
    """Return True only if text has real content beyond placeholder/fallback messages."""
    if not text or not text.strip():
        return False
    _empty_markers = (
        "目前資料不足", "未有足夠", "未偵測到", "未見明確",
        "no issue detected", "insufficient data", "- 未",
    )
    _stripped = text.strip()
    return not any(_stripped.startswith(m) or _stripped == m for m in _empty_markers)


# Check raw data fields directly — never rely on formatted text strings
def _delay_has_real_data(result: dict) -> bool:
    """Return True only if delay concern result has actual findings in raw data."""
    if not result:
        return False
    # score must be > 0
    if (result.get("score") or 0) <= 0:
        return False
    # at least one signal must exist
    return bool(result.get("signals"))


def _has_repeated_issues(result: dict) -> bool:
    return bool(result and result.get("repeated_issues"))


def _has_workflow_blockage(result: dict) -> bool:
    return bool(result and result.get("workflow_blockages"))


def _has_progress_concern(result: dict) -> bool:
    """Return True only if progress concern has real signal data (not just placeholder lines)."""
    if not result:
        return False
    signals = result.get("signals") or []
    return bool(signals)


# Only render the whole section if at least one sub-section has real content
_has_logic = bool(_site_logic_result and _site_logic_result.get("has_issues"))
_has_progress = bool(_progress_result and _progress_result.get("has_data"))
_has_delay = _delay_has_real_data(_delay_concern_result)

# Also check timeline for real data
_timeline_has_data = False
if _progress_result:
    _tl = _progress_result.get("timeline_comparison", {})
    _timeline_has_data = bool(
        _tl.get("previous_session") or
        (_tl.get("risk_change") and _tl.get("risk_change") not in ("未有足夠資料", "")) or
        (_tl.get("progress_change") and _tl.get("progress_change") not in ("目前資料不足以判斷實際工期狀況。", ""))
    )

if _has_logic or _has_progress or _has_delay or _timeline_has_data:
    st.markdown('<div class="report-section">', unsafe_allow_html=True)
    st.markdown('<h3>工程時序分析</h3>', unsafe_allow_html=True)

    # Timeline — only show if has real data
    if _timeline_has_data and _progress_result:
        _timeline = _progress_result.get("timeline_comparison", {})
        _timeline_text = (
            f"上次 Session：{_timeline.get('previous_session') or '未有足夠資料'}\n"
            f"今次 Session：{_timeline.get('current_session') or data.get('session_id', '')}\n"
            f"風險變化：{_timeline.get('risk_change') or '未有足夠資料'}\n"
            f"進度變化：{_timeline.get('progress_change') or '未有足夠資料'}"
        )
        st.markdown(
            f'<div class="phase33-box">{highlight_report_keywords_html(_timeline_text).replace(chr(10), "<br/>")}</div>',
            unsafe_allow_html=True,
        )

    # Site logic — only show if has_issues flag is set
    if _has_logic:
        _logic_text = format_site_logic_for_report(_site_logic_result)
        st.markdown('<h3>工序合理性分析</h3>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="phase33-box">{highlight_report_keywords_html(_logic_text).replace(chr(10), "<br/>")}</div>',
            unsafe_allow_html=True,
        )

    # Progress tracking — only show if has_data flag is set
    if _has_progress:
        _progress_text = format_progress_for_report(_progress_result)
        st.markdown('<h3>進度追蹤分析</h3>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="phase33-box">{highlight_report_keywords_html(_progress_text).replace(chr(10), "<br/>")}</div>',
            unsafe_allow_html=True,
        )

    # Delay Concern — only show if score > 0 AND signals exist
    if _has_delay:
        _delay_text = format_delay_concern_for_report(_delay_concern_result)
        st.markdown('<h3>Delay Concern</h3>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="phase33-box">{highlight_report_keywords_html(_delay_text).replace(chr(10), "<br/>")}</div>',
            unsafe_allow_html=True,
        )

        # Repeated Issues — only show if raw repeated_issues list is non-empty
        if _has_repeated_issues(_delay_concern_result):
            _repeated_text = _delay_concern_result.get("repeated_issues_text", "") or ""
            st.markdown('<h3>Repeated Issues</h3>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="phase33-box">{highlight_report_keywords_html(_repeated_text).replace(chr(10), "<br/>")}</div>',
                unsafe_allow_html=True,
            )

        # Workflow Blockage — only show if raw workflow_blockages list is non-empty
        if _has_workflow_blockage(_delay_concern_result):
            _blockage_text = _delay_concern_result.get("workflow_blockage_text", "") or ""
            st.markdown('<h3>Workflow Blockage</h3>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="phase33-box">{highlight_report_keywords_html(_blockage_text).replace(chr(10), "<br/>")}</div>',
                unsafe_allow_html=True,
            )

        # Progress Concern — only show if signals exist
        if _has_progress_concern(_delay_concern_result):
            _progress_concern_text = _delay_concern_result.get("progress_concern", "") or ""
            st.markdown('<h3>Progress Concern</h3>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="phase33-box">{highlight_report_keywords_html(_progress_concern_text).replace(chr(10), "<br/>")}</div>',
                unsafe_allow_html=True,
            )

    # PM summary — only show if has real content (not placeholder)
    _pm_parts = [
        (_site_logic_result.get("pm_summary") or "") if _has_logic else "",
        (_progress_result.get("pm_summary") or "") if _has_progress else "",
        (_delay_concern_result.get("pm_summary") or "") if _has_delay else "",
    ]
    _pm_text = "\n".join(p for p in _pm_parts if p and p.strip()).strip()
    if _pm_text:
        st.markdown('<h3>PM 工程狀態總結</h3>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="phase33-box">{highlight_report_keywords_html(_pm_text).replace(chr(10), "<br/>")}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)

# ── Phase 3.3D: Resource & Workforce Analysis ─────────────────────────────────
_resource_workforce_result = data.get("resource_workforce_result", {})
if _resource_workforce_result and _resource_workforce_result.get("has_evidence"):
    _rw_impact = _resource_workforce_result.get("resource_impact_level", "無明顯影響")
    _rw_impact_color = {
        "嚴重影響": "#dc3545",
        "中度影響": "#fd7e14",
        "輕微影響": "#ffc107",
        "無明顯影響": "#28a745",
    }.get(_rw_impact, "#6c757d")

    st.markdown('<div class="report-section">', unsafe_allow_html=True)
    st.markdown('<h3>👷 資源與人手協調分析</h3>', unsafe_allow_html=True)

    st.markdown(
        f'<div style="display:inline-block;background:{_rw_impact_color};color:white;'
        f'border-radius:20px;padding:0.2rem 1rem;font-weight:700;font-size:0.95rem;'
        f'margin-bottom:0.8rem;">對進度影響：{_rw_impact}</div>',
        unsafe_allow_html=True,
    )

    # Workforce issues — only show sub-section if there are actual issues
    _wf_issues = _resource_workforce_result.get("workforce_issues", []) or []
    if _wf_issues:
        st.markdown('<h3>人手狀況</h3>', unsafe_allow_html=True)
        for _item in _wf_issues[:5]:
            _pri_color = {"高": "#dc3545", "中": "#fd7e14", "低": "#28a745"}.get(_item.get("priority", "中"), "#6c757d")
            _ev_str = "、".join(_item.get("evidence", []))
            st.markdown(
                f'<div class="phase33-box">'
                f'<span style="color:{_pri_color};font-weight:700;">[{_item.get("priority")}]</span> '
                f'<strong>{highlight_report_keywords_html(_item.get("title",""))}</strong><br/>'
                f'{highlight_report_keywords_html(_item.get("finding",""))}'
                + (f'<br/><span style="font-size:0.85rem;color:#666;">Evidence: {_ev_str}</span>' if _ev_str else "")
                + '</div>',
                unsafe_allow_html=True,
            )

    # Trade coordination — only show if conflicts found
    _tc_issues = _resource_workforce_result.get("trade_conflicts", []) or []
    if _tc_issues:
        st.markdown('<h3>工種協調</h3>', unsafe_allow_html=True)
        for _item in _tc_issues[:5]:
            _pri_color = {"高": "#dc3545", "中": "#fd7e14", "低": "#28a745"}.get(_item.get("priority", "中"), "#6c757d")
            _ev_str = "、".join(_item.get("evidence", []))
            st.markdown(
                f'<div class="phase33-box">'
                f'<span style="color:{_pri_color};font-weight:700;">[{_item.get("priority")}]</span> '
                f'<strong>{highlight_report_keywords_html(_item.get("title",""))}</strong><br/>'
                f'{highlight_report_keywords_html(_item.get("finding",""))}'
                + (f'<br/><span style="font-size:0.85rem;color:#666;">Evidence: {_ev_str}</span>' if _ev_str else "")
                + '</div>',
                unsafe_allow_html=True,
            )

    # Material issues — only show if issues found
    _mat_issues = _resource_workforce_result.get("material_issues", []) or []
    if _mat_issues:
        st.markdown('<h3>材料狀況</h3>', unsafe_allow_html=True)
        for _item in _mat_issues[:5]:
            _pri_color = {"高": "#dc3545", "中": "#fd7e14", "低": "#28a745"}.get(_item.get("priority", "中"), "#6c757d")
            _ev_str = "、".join(_item.get("evidence", []))
            st.markdown(
                f'<div class="phase33-box">'
                f'<span style="color:{_pri_color};font-weight:700;">[{_item.get("priority")}]</span> '
                f'<strong>{highlight_report_keywords_html(_item.get("title",""))}</strong><br/>'
                f'{highlight_report_keywords_html(_item.get("finding",""))}'
                + (f'<br/><span style="font-size:0.85rem;color:#666;">Evidence: {_ev_str}</span>' if _ev_str else "")
                + '</div>',
                unsafe_allow_html=True,
            )

    # Plant / equipment issues — only show if issues found
    _plant_issues = _resource_workforce_result.get("plant_issues", []) or []
    if _plant_issues:
        st.markdown('<h3>機械 / 設備</h3>', unsafe_allow_html=True)
        for _item in _plant_issues[:5]:
            _pri_color = {"高": "#dc3545", "中": "#fd7e14", "低": "#28a745"}.get(_item.get("priority", "中"), "#6c757d")
            _ev_str = "、".join(_item.get("evidence", []))
            st.markdown(
                f'<div class="phase33-box">'
                f'<span style="color:{_pri_color};font-weight:700;">[{_item.get("priority")}]</span> '
                f'<strong>{highlight_report_keywords_html(_item.get("title",""))}</strong><br/>'
                f'{highlight_report_keywords_html(_item.get("finding",""))}'
                + (f'<br/><span style="font-size:0.85rem;color:#666;">Evidence: {_ev_str}</span>' if _ev_str else "")
                + '</div>',
                unsafe_allow_html=True,
            )

    # Action items
    _rw_actions = _resource_workforce_result.get("action_items", []) or []
    if _rw_actions:
        st.markdown('<h3>建議跟進</h3>', unsafe_allow_html=True)
        for _act in _rw_actions[:6]:
            _act_color = {"高": "#dc3545", "中": "#fd7e14", "低": "#28a745"}.get(_act.get("priority", "中"), "#6c757d")
            st.markdown(
                f'<div style="background:#fff8f0;border-left:4px solid {_act_color};'
                f'border-radius:6px;padding:0.6rem 0.9rem;margin-bottom:0.4rem;font-size:0.93rem;">'
                f'<span style="color:{_act_color};font-weight:700;">[{_act.get("priority")}]</span> '
                f'{highlight_report_keywords_html(_act.get("title",""))}<br/>'
                f'<span style="font-size:0.87rem;color:#555;">{_act.get("detail","")}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # PM summary
    _rw_pm = _resource_workforce_result.get("pm_summary", "")
    if _rw_pm:
        st.markdown('<h3>PM 資源協調總結</h3>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="phase33-box">{highlight_report_keywords_html(_rw_pm).replace(chr(10), "<br/>")}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)

# ── Repeated Issue Detection ──────────────────────────────────────────────────
_repeated_issues_detected = data.get("repeated_issues_detected", []) or []
if _repeated_issues_detected:
    st.markdown('<div class="report-section">', unsafe_allow_html=True)
    st.markdown('<h3>🔁 重覆風險偵測</h3>', unsafe_allow_html=True)
    st.markdown(
        '<div style="background:#fff3cd;border-left:4px solid #ffc107;border-radius:6px;'
        'padding:0.6rem 1rem;margin-bottom:0.8rem;font-size:0.93rem;">'
        '⚠️ 以下風險在同一工程中重覆出現，請優先跟進。'
        '</div>',
        unsafe_allow_html=True,
    )
    for _ri in _repeated_issues_detected:
        _ri_kws = "、".join(_ri.get("group_keywords", [])[:3])
        _ri_count = _ri.get("repeat_count", 2)
        _ri_first = _ri.get("first_seen", "")
        _ri_last = _ri.get("last_seen", "")
        _date_str = ""
        if _ri_first:
            _date_str = f"首次：{_ri_first}"
        if _ri_last and _ri_last != _ri_first:
            _date_str += f"　最近：{_ri_last}"
        st.markdown(
            f'<div style="background:#fde8eb;border-left:4px solid #dc3545;'
            f'border-radius:6px;padding:0.7rem 1rem;margin-bottom:0.5rem;">'
            f'<span style="color:#dc3545;font-weight:700;">重覆風險（第 {_ri_count} 次）</span>　'
            f'<strong>{highlight_report_keywords_html(_ri_kws)}</strong>'
            + (f'<br/><span style="font-size:0.83rem;color:#888;">{_date_str}</span>' if _date_str else "")
            + '</div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

# ── 證據可信度 ────────────────────────────────────────────────────────────────
_evidence_result = data.get("evidence_result", {})
if _evidence_result:
    _ev_class    = _evidence_result.get("evidence_class", "")
    _ev_label    = _evidence_result.get("evidence_label_zh", "")
    _ev_sections = _evidence_result.get("evidence_sections", {})
    _ev_replaced = _evidence_result.get("replacements_made", [])
    _ev_adjusted = _evidence_result.get("risk_was_adjusted", False)
    _ev_adj_risk = _evidence_result.get("adjusted_risk_level", "")

    _ev_color = {
        "confirmed":           "#28a745",
        "uncertain":           "#fd7e14",
        "missing_evidence":    "#6c757d",
        "prohibited_inference":"#dc3545",
    }.get(_ev_class, "#6c757d")

    st.markdown('<div class="report-section">', unsafe_allow_html=True)
    st.markdown('<h3>🔍 證據可信度</h3>', unsafe_allow_html=True)

    st.markdown(
        f'<div style="display:inline-block;background:{_ev_color};color:white;'
        f'border-radius:20px;padding:0.2rem 1rem;font-weight:700;font-size:0.95rem;'
        f'margin-bottom:0.8rem;">{_ev_label}</div>',
        unsafe_allow_html=True,
    )

    if _ev_adjusted and _ev_adj_risk:
        st.markdown(
            f'<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:6px;'
            f'padding:0.5rem 0.9rem;font-size:0.9rem;margin-bottom:0.6rem;">'
            f'⚠️ 風險級別已根據證據可信度調整為：<strong>{_ev_adj_risk}</strong></div>',
            unsafe_allow_html=True,
        )

    _section_labels = {
        "confirmed":     ("✅ 已確認事項", "#28a745"),
        "uncertain":     ("❓ 未能確認事項", "#fd7e14"),
        "suspicion":     ("🔶 合理懷疑", "#e67e00"),
        "prohibited":    ("🚫 不可推測事項", "#dc3545"),
        "supplementary": ("📋 建議補充資料", "#6c757d"),
    }
    for sec_key, (sec_label, sec_color) in _section_labels.items():
        items = _ev_sections.get(sec_key, [])
        if items:
            st.markdown(
                f'<div style="font-weight:600;color:{sec_color};margin-top:0.5rem;">'
                f'{sec_label}</div>',
                unsafe_allow_html=True,
            )
            for item in items[:5]:
                safe_item = item.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                st.markdown(f"- {safe_item}")

    if _ev_replaced:
        with st.expander(f"🔧 已自動修正 {len(_ev_replaced)} 處過度推測字眼"):
            for r in _ev_replaced:
                st.markdown(f"- {r}")

    st.markdown('</div>', unsafe_allow_html=True)

# ── Phase 3.3E: Site Instruction & Follow-up Workflow ─────────────────────────
_site_instruction_result = data.get("site_instruction_result", {})
if _site_instruction_result and _site_instruction_result.get("has_instructions"):
    st.markdown('<div class="report-section">', unsafe_allow_html=True)
    st.markdown('<h3>📋 建議跟進指令</h3>', unsafe_allow_html=True)
    
    _instructions = _site_instruction_result.get("instructions", [])
    _high_count = _site_instruction_result.get("high_priority_count", 0)
    _insufficient = _site_instruction_result.get("insufficient_data", False)
    
    if _insufficient:
        st.warning("⚠️ 資料不足以發出正式指令，建議先補充相片、文件或現場紀錄。")
    
    if _high_count > 0:
        st.markdown(
            f'<div style="background:#fde8eb;border-left:4px solid #dc3545;'
            f'border-radius:6px;padding:0.7rem 1rem;margin-bottom:0.8rem;">'
            f'<strong style="color:#dc3545;">⚠️ 有 {_high_count} 項高優先級指令需即時跟進</strong>'
            f'</div>',
            unsafe_allow_html=True,
        )
    
    for instr in _instructions:
        _instr_type_label = instr.get("instruction_type_label", "")
        _instr_priority = instr.get("priority", "中")
        _instr_issued_to = instr.get("issued_to", "待確認")
        _instr_title = instr.get("instruction_title", "")
        _instr_detail = instr.get("instruction_detail", "")
        _instr_action = instr.get("required_action", "")
        _instr_evidence = instr.get("evidence_source", [])
        _instr_repeated = instr.get("repeated_follow_up", False)
        
        _pri_color = {"高": "#dc3545", "中": "#fd7e14", "低": "#28a745"}.get(_instr_priority, "#6c757d")
        _repeated_tag = '<span style="color:#dc3545;font-weight:600;"> (重複跟進)</span>' if _instr_repeated else ""
        
        st.markdown(
            f'<div style="background:#f8f9fa;border-left:4px solid {_pri_color};'
            f'border-radius:6px;padding:0.8rem 1rem;margin-bottom:0.8rem;">'
            f'<div style="font-weight:700;color:{_pri_color};margin-bottom:0.3rem;">'
            f'[{_instr_priority}] {_instr_type_label}{_repeated_tag}</div>'
            f'<div style="font-size:0.95rem;margin-bottom:0.4rem;"><strong>對象：</strong>{_instr_issued_to}</div>'
            f'<div style="font-size:0.9rem;color:#555;margin-bottom:0.4rem;">{highlight_report_keywords_html(_instr_title)}</div>'
            f'<div style="font-size:0.88rem;color:#666;margin-bottom:0.4rem;">{highlight_report_keywords_html(_instr_action)}</div>',
            unsafe_allow_html=True,
        )
        if _instr_evidence:
            _ev_str = "、".join(_instr_evidence)
            st.markdown(
                f'<div style="font-size:0.82rem;color:#888;">證據來源：{_ev_str}</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)
    
    _pm_summary = _site_instruction_result.get("pm_summary", "")
    if _pm_summary:
        st.markdown('<h3>PM 指令總結</h3>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="phase33-box">{highlight_report_keywords_html(_pm_summary).replace(chr(10), "<br/>")}</div>',
            unsafe_allow_html=True,
        )
    
    st.markdown('</div>', unsafe_allow_html=True)

# ── 下載 PDF ──────────────────────────────────────────────────────────────────
st.markdown('<div class="report-section">', unsafe_allow_html=True)
st.markdown('<h3>📥 下載報告</h3>', unsafe_allow_html=True)
st.markdown("下載 PDF 報告，方便在手機或電腦查閱，或透過 WhatsApp 分享。")

try:
    saved_report_value = data.get("report_path", "")
    saved_report_path = Path(saved_report_value) if saved_report_value else None
    if saved_report_path and saved_report_path.is_file():
        pdf_bytes = saved_report_path.read_bytes()
    else:
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
            original_risk_level=data.get("original_risk_level", risk_level),
            highest_risk_agent=data.get("highest_risk_agent", ""),
            site_logic_result=data.get("site_logic_result", {}),
            progress_result=data.get("progress_result", {}),
            delay_concern_result=data.get("delay_concern_result", {}),
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
