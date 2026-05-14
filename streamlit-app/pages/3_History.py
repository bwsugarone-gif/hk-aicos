"""
pages/3_History.py
HK-AICOS Phase 2.0 - 歷史紀錄頁（客戶版）

Buildway Tech (HK) Limited
"""

import streamlit as st
from pathlib import Path
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.lang import HISTORY, NAV, BRAND
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
        color: white; padding: 1.8rem 2rem; border-radius: 12px; margin-bottom: 1.5rem;
    }
    .page-header h2 { font-size: 1.6rem; margin: 0 0 0.3rem 0; }
    .page-header p { font-size: 1rem; opacity: 0.9; margin: 0; }
    .history-card {
        background: white; border-radius: 10px; padding: 1.2rem;
        box-shadow: 0 2px 8px rgba(26,58,92,0.08); margin-bottom: 1rem;
        border-left: 5px solid #c9a84c;
    }
    .history-card h4 { color: #1a3a5c; margin: 0 0 0.5rem 0; font-size: 1rem; }
    .history-meta { font-size: 0.85rem; color: #777; margin-bottom: 0.5rem; }
    .file-row {
        background: #f8f9fa; border-radius: 6px; padding: 0.6rem 1rem;
        margin-bottom: 0.4rem; font-size: 0.88rem; color: #444;
        display: flex; justify-content: space-between;
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
    st.page_link("pages/4_About.py", label="ℹ️ 關於 Buildway Tech")
    st.markdown("---")
    st.markdown('<div style="font-size:0.78rem; color:#aac4e0;">🔒 所有資料安全處理</div>', unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
    <h2>🕘 歷史紀錄</h2>
    <p>查閱過往分析記錄及下載報告。</p>
</div>
""", unsafe_allow_html=True)

# ── 最近一次分析 ──────────────────────────────────────────────────────────────
if "last_analysis" in st.session_state:
    data = st.session_state["last_analysis"]
    risk_level = data.get("risk_level", "中風險")
    if risk_level == "極高風險":
        risk_level = "高風險"
    risk_emoji = {"低風險": "🟢", "中風險": "🟠", "高風險": "🔴"}.get(risk_level, "🟠")

    st.markdown("### 📋 最近一次分析")
    st.markdown(f"""
    <div class="history-card">
        <h4>{data.get('analysis_display_name', data.get('analysis_type', ''))}</h4>
        <div class="history-meta">
            工程編號：{data.get('project_ref', '未填寫') or '未填寫'} &nbsp;|&nbsp;
            文件：{data.get('file_name', '無') or '無'} &nbsp;|&nbsp;
            風險：{risk_emoji} {risk_level}
        </div>
        <div style="font-size:0.92rem; color:#333;">
            問題：{data.get('question', '')[:200]}{'...' if len(data.get('question','')) > 200 else ''}
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.page_link("pages/2_Report.py", label="📄 查看分析報告")
    with col2:
        try:
            from utils.report_generator import generate_pdf_report
            pdf_bytes = generate_pdf_report(
                analysis_type=data.get("analysis_display_name", data.get("analysis_type", "")),
                question=data.get("question", ""),
                risk_level=risk_level,
                analysis_result=data.get("analysis_result", ""),
                filename_hint=data.get("file_name", ""),
                professionals_required=data.get("professionals", []),
                project_ref=data.get("project_ref", ""),
            )
            safe_name = data.get("analysis_display_name", "報告").replace("/", "-").replace(" ", "-")
            st.download_button(
                label="📄 下載 PDF 報告",
                data=pdf_bytes,
                file_name=f"HK-AICOS-{safe_name}-報告.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception:
            st.error("PDF 生成失敗，請稍後再試。")
else:
    st.info("📭 暫無分析記錄。請先前往「上載分析」頁面進行分析。")

st.markdown("---")

# ── 已儲存報告 ────────────────────────────────────────────────────────────────
st.markdown("### 📁 已儲存報告")

reports_dir = Path(__file__).parent.parent / "reports"
if reports_dir.exists():
    pdf_files = sorted(reports_dir.glob("*.pdf"), key=lambda f: f.stat().st_mtime, reverse=True)
    if pdf_files:
        st.markdown(f"共找到 **{len(pdf_files)}** 份報告：")
        for pdf_file in pdf_files[:20]:
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.markdown(f"📄 `{pdf_file.name}`")
            with col2:
                size_kb = pdf_file.stat().st_size / 1024
                st.markdown(f"<small>{size_kb:.0f} KB</small>", unsafe_allow_html=True)
            with col3:
                with open(pdf_file, "rb") as f:
                    st.download_button(
                        label="下載",
                        data=f.read(),
                        file_name=pdf_file.name,
                        mime="application/pdf",
                        key=f"dl_{pdf_file.name}",
                        use_container_width=True,
                    )
    else:
        st.info("📭 暫無已儲存報告。")
else:
    st.info("📭 暫無已儲存報告。")

st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#999; padding:1rem 0 0.5rem 0; font-size:0.82rem;">
    Buildway Tech (HK) Limited | HK-AICOS Phase 2.0
</div>
""", unsafe_allow_html=True)
