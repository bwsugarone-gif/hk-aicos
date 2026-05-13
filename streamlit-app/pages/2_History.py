"""
pages/2_History.py
HK-AICOS Phase 2.0 - Analysis History Page

Shows recent analyses stored in session state.
Phase 3: Will connect to database for persistent history.
"""

import streamlit as st
from pathlib import Path
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.risk_classifier import get_risk_info, classify_risk
from utils.report_generator import generate_pdf_report

st.set_page_config(
    page_title="History | HK-AICOS",
    page_icon="📋",
    layout="wide",
)

st.markdown("""
<style>
    .history-card {
        background: #f8f9fa;
        padding: 1.2rem;
        border-radius: 8px;
        border-left: 4px solid #4a6fa5;
        margin-bottom: 1rem;
    }
    .history-header {
        background: linear-gradient(135deg, #1a3a5c 0%, #4a6fa5 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="history-header">
    <h2>📋 Analysis History</h2>
    <p>Review your recent AI analyses and download reports.</p>
</div>
""", unsafe_allow_html=True)

# Phase notice
st.info("""
**Phase 2.0 Note:** History is stored in session memory only. 
Closing the browser will clear history. 
Phase 3 will add persistent database storage.
""")

# Check for history
if "analysis_history" not in st.session_state:
    st.session_state["analysis_history"] = []

# Add current analysis to history if exists
if "last_analysis" in st.session_state:
    last = st.session_state["last_analysis"]
    # Check if already in history
    if not st.session_state["analysis_history"] or \
       st.session_state["analysis_history"][0].get("question") != last.get("question"):
        entry = {
            **last,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "risk_level": classify_risk(
                last["analysis_type"],
                last["question"],
                last["analysis_result"],
            ),
        }
        st.session_state["analysis_history"].insert(0, entry)

history = st.session_state["analysis_history"]

if not history:
    st.markdown("""
    <div style="text-align:center; padding: 3rem; color: #666;">
        <h3>📭 No analyses yet</h3>
        <p>Go to the <strong>Analysis</strong> page to run your first analysis.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"**{len(history)} analysis record(s) in session**")

    # Clear history button
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("🗑️ Clear History", type="secondary"):
            st.session_state["analysis_history"] = []
            st.rerun()

    st.markdown("---")

    for i, entry in enumerate(history):
        risk_info = get_risk_info(entry.get("risk_level", "中風險"))

        with st.expander(
            f"{risk_info['emoji']} [{entry.get('timestamp', '—')}] "
            f"{entry.get('analysis_type', '—')} | "
            f"{entry.get('question', '')[:60]}{'...' if len(entry.get('question','')) > 60 else ''}",
            expanded=(i == 0),
        ):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"**Analysis Type:** {entry.get('analysis_type', '—')}")
                st.markdown(f"**Question:** {entry.get('question', '—')}")
                st.markdown(f"**Project Ref:** {entry.get('project_ref', '—') or '—'}")
                st.markdown(f"**File:** {entry.get('file_description', '—') or 'No file'}")

            with col2:
                st.markdown(
                    f"""
                    <div style="
                        background:{risk_info['bg_color']};
                        border:2px solid {risk_info['color']};
                        border-radius:8px;
                        padding:0.8rem;
                        text-align:center;
                    ">
                        <strong style="color:{risk_info['color']};">
                            {risk_info['emoji']} {risk_info['label']}
                        </strong>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown("**Analysis Result:**")
            st.markdown(
                f'<div style="background:#fff;padding:1rem;border-radius:6px;border:1px solid #dee2e6;">'
                f'{entry.get("analysis_result","—").replace(chr(10),"<br/>")}'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Professionals
            if entry.get("professionals"):
                st.markdown("**Professionals Required:**")
                for prof in entry["professionals"]:
                    st.warning(f"⚠️ {prof}")

            # Download PDF
            try:
                pdf_bytes = generate_pdf_report(
                    analysis_type=entry.get("analysis_type", ""),
                    question=entry.get("question", ""),
                    risk_level=entry.get("risk_level", "中風險"),
                    analysis_result=entry.get("analysis_result", ""),
                    filename_hint=entry.get("file_description", ""),
                    professionals_required=entry.get("professionals", []),
                    project_ref=entry.get("project_ref", ""),
                )
                st.download_button(
                    label="📄 Download PDF",
                    data=pdf_bytes,
                    file_name=f"HK-AICOS-Report-{entry.get('timestamp','').replace(' ','-').replace(':','')}.pdf",
                    mime="application/pdf",
                    key=f"dl_{i}",
                )
            except Exception as e:
                st.error(f"PDF error: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#666; font-size:0.85rem;">
    Phase 3 will add: Persistent DB storage | Search & filter | Export to Excel | Team sharing
</div>
""", unsafe_allow_html=True)
