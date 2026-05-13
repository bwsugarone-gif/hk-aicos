"""
pages/3_Knowledge_Base.py
HK-AICOS Phase 2.0 - Knowledge Base Viewer

Browse HK regulations, agent docs, and SOPs from the knowledge base.
"""

import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.rag_reader import (
    check_knowledge_base_status,
    read_markdown_file,
    KNOWLEDGE_BASE_PATHS,
    REGULATION_FILES,
)

st.set_page_config(
    page_title="Knowledge Base | HK-AICOS",
    page_icon="📚",
    layout="wide",
)

st.markdown("""
<style>
    .kb-header {
        background: linear-gradient(135deg, #1a3a5c 0%, #4a6fa5 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
    }
    .reg-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 6px;
        border-left: 3px solid #4a6fa5;
        margin-bottom: 0.5rem;
        cursor: pointer;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="kb-header">
    <h2>📚 Knowledge Base</h2>
    <p>Browse Hong Kong regulations, agent documentation, and SOPs.</p>
</div>
""", unsafe_allow_html=True)

# Status overview
st.markdown("### 📊 Knowledge Base Status")
kb_status = check_knowledge_base_status()

cols = st.columns(len(kb_status))
for col, (name, info) in zip(cols, kb_status.items()):
    with col:
        if info["exists"] and info["file_count"] > 0:
            st.metric(
                label=name.title(),
                value=f"{info['file_count']} files",
                delta="✅ Ready",
            )
        elif info["exists"]:
            st.metric(label=name.title(), value="0 files", delta="⚠️ Empty")
        else:
            st.metric(label=name.title(), value="—", delta="❌ Missing")

st.markdown("---")

# Tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["⚖️ HK Regulations", "🤖 Agents", "📋 SOPs", "🗂️ RAG Structure"])

# ── Tab 1: Regulations ───────────────────────────────────────────────────────
with tab1:
    st.markdown("### Hong Kong Government Regulatory Layer")
    st.markdown("Select a department to view its regulatory documentation.")

    reg_dir = KNOWLEDGE_BASE_PATHS["regulations"]

    DEPT_INFO = {
        "hk-bd-layer": ("🏢 BD 屋宇署", "Buildings Department - Building plans, structural safety, AP/RSE requirements"),
        "hk-emsd-layer": ("⚡ EMSD 機電工程署", "Electrical & Mechanical Services - MEP, lifts, escalators"),
        "hk-epd-layer": ("🌿 EPD 環保署", "Environmental Protection - Noise, dust, waste management"),
        "hk-labour-layer": ("👷 Labour 勞工處", "Labour Department - Site safety, working hours, compensation"),
        "hk-fsd-layer": ("🔥 FSD 消防處", "Fire Services - Fire safety, dangerous goods, evacuation"),
        "hk-wsd-layer": ("💧 WSD 水務署", "Water Supplies - Water mains, plumbing, licensed plumbers"),
        "hk-landsd-layer": ("🗺️ LandsD 地政總署", "Lands Department - Land use, lease conditions, occupation permits"),
        "hk-hyd-layer": ("🛣️ HyD 路政署", "Highways Department - Roads, bridges, footpaths"),
        "hk-cedd-layer": ("⛰️ CEDD 土木工程拓展署", "Civil Engineering - Slopes, geotechnical, reclamation"),
        "hk-dsd-layer": ("🚰 DSD 渠務署", "Drainage Services - Sewers, stormwater, flood prevention"),
        "hk-td-layer": ("🚗 TD 運輸署", "Transport Department - Traffic, road opening, transport assessment"),
        "hk-legal-layer": ("⚖️ Legal 法律合規", "Hong Kong Legal & Contract Compliance Layer"),
    }

    col1, col2 = st.columns([1, 2])

    with col1:
        selected_reg = st.radio(
            "Select Department:",
            list(DEPT_INFO.keys()),
            format_func=lambda k: DEPT_INFO[k][0],
        )

    with col2:
        if selected_reg:
            dept_name, dept_desc = DEPT_INFO[selected_reg]
            st.markdown(f"#### {dept_name}")
            st.markdown(f"*{dept_desc}*")
            st.markdown("---")

            filename = REGULATION_FILES.get(selected_reg)
            if filename:
                file_path = reg_dir / filename
                content = read_markdown_file(file_path, max_chars=10000)
                if "[File not found" in content:
                    st.warning(f"⚠️ File not found: {file_path}")
                    st.markdown("This regulation document has not been created yet.")
                    st.markdown(f"Expected path: `{file_path}`")
                else:
                    st.markdown(content)

# ── Tab 2: Agents ────────────────────────────────────────────────────────────
with tab2:
    st.markdown("### Agent Documentation")
    st.markdown("View the role and responsibilities of each AI agent.")

    agents_dir = KNOWLEDGE_BASE_PATHS["agents"]

    AGENT_INFO = {
        "engineering-agent": "🔧 Engineering Agent",
        "safety-agent": "🦺 Safety Agent",
        "material-agent": "📦 Material Agent",
        "qs-agent": "💰 QS Agent",
        "accounting-agent": "📊 Accounting Agent",
        "foreman-agent": "👷 Foreman Agent",
        "pm-agent": "📋 PM Agent",
        "surveying-agent": "📐 Surveying Agent",
        "drafting-agent": "✏️ Drafting Agent",
        "legal-agent": "⚖️ Legal Agent",
    }

    col1, col2 = st.columns([1, 2])

    with col1:
        selected_agent = st.radio(
            "Select Agent:",
            list(AGENT_INFO.keys()),
            format_func=lambda k: AGENT_INFO[k],
        )

    with col2:
        if selected_agent:
            agent_path = agents_dir / f"{selected_agent}.md"
            content = read_markdown_file(agent_path, max_chars=10000)
            if "[File not found" in content:
                st.warning(f"⚠️ Agent document not found: {agent_path}")
            else:
                st.markdown(content)

# ── Tab 3: SOPs ──────────────────────────────────────────────────────────────
with tab3:
    st.markdown("### Standard Operating Procedures")

    sop_dir = KNOWLEDGE_BASE_PATHS["sop"]

    SOP_INFO = {
        "SOP_SYSTEM": "📋 SOP System Overview",
        "daily-site-report-sop": "📝 Daily Site Report",
        "safety-inspection-sop": "🦺 Safety Inspection",
        "material-control-sop": "📦 Material Control",
        "rfi-risc-sop": "📋 RFI / RISC",
        "vo-management-sop": "💰 VO Management",
        "legal-review-sop": "⚖️ Legal Review",
    }

    col1, col2 = st.columns([1, 2])

    with col1:
        selected_sop = st.radio(
            "Select SOP:",
            list(SOP_INFO.keys()),
            format_func=lambda k: SOP_INFO[k],
        )

    with col2:
        if selected_sop:
            sop_path = sop_dir / f"{selected_sop}.md"
            content = read_markdown_file(sop_path, max_chars=10000)
            if "[File not found" in content:
                st.warning(f"⚠️ SOP document not found: {sop_path}")
            else:
                st.markdown(content)

# ── Tab 4: RAG Structure ─────────────────────────────────────────────────────
with tab4:
    st.markdown("### RAG Knowledge Base Structure")
    st.markdown("""
    The RAG (Retrieval-Augmented Generation) system organizes reference documents 
    for AI analysis. Phase 2.0 uses file-based reading. Phase 2.5 will add vector search.
    """)

    rag_dir = KNOWLEDGE_BASE_PATHS["rag"]

    RAG_FOLDERS = {
        "company-reference": "🏢 Company Reference Documents",
        "technical-specification": "📐 Technical Specifications",
        "quality-management": "✅ Quality Management",
        "method-statement": "📋 Method Statements",
        "inspection-test-plan": "🔍 Inspection & Test Plans",
        "contract-reference": "📄 Contract References",
        "legal-reference": "⚖️ Legal References",
    }

    for folder, label in RAG_FOLDERS.items():
        folder_path = rag_dir / folder
        if folder_path.exists():
            files = list(folder_path.glob("*"))
            non_gitkeep = [f for f in files if f.name != ".gitkeep"]
            status = f"✅ {len(non_gitkeep)} file(s)" if non_gitkeep else "📂 Empty (ready for documents)"
        else:
            status = "❌ Folder not found"

        st.markdown(f"**{label}** — {status}")

    st.markdown("---")
    st.info("""
    **How to add documents to RAG:**
    1. Place PDF/Word files in the appropriate subfolder under `HK-AICOS/rag/`
    2. Phase 2.5 will automatically index new documents into the vector database
    3. Agents will then be able to search and retrieve relevant content
    """)

    # Show RAG system doc if available
    rag_system_path = rag_dir / "RAG_SYSTEM.md"
    if rag_system_path.exists():
        with st.expander("📖 RAG System Documentation"):
            st.markdown(read_markdown_file(rag_system_path, max_chars=5000))
