"""
pages/4_Settings.py
HK-AICOS Phase 2.0 - Settings & System Info Page
"""

import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.rag_reader import check_knowledge_base_status, list_available_regulations
from utils.agent_router import get_all_analysis_types, AGENT_ROUTING

st.set_page_config(
    page_title="Settings | HK-AICOS",
    page_icon="⚙️",
    layout="wide",
)

st.markdown("""
<style>
    .settings-header {
        background: linear-gradient(135deg, #1a3a5c 0%, #4a6fa5 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
    }
    .info-card {
        background: #f8f9fa;
        padding: 1.2rem;
        border-radius: 8px;
        border-left: 4px solid #4a6fa5;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="settings-header">
    <h2>⚙️ Settings & System Info</h2>
    <p>Configure API keys, view system status, and manage settings.</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["🔑 API Keys", "📊 System Status", "🤖 Agent Config", "📖 About"])

# ── Tab 1: API Keys ──────────────────────────────────────────────────────────
with tab1:
    st.markdown("### API Key Configuration")
    st.info("API keys are stored in session memory only and never saved to disk.")

    st.markdown("#### Anthropic Claude API")
    api_key = st.text_input(
        "Anthropic API Key:",
        type="password",
        value=st.session_state.get("api_key", ""),
        placeholder="sk-ant-...",
        help="Get your API key from https://console.anthropic.com",
    )
    if api_key:
        st.session_state["api_key"] = api_key
        st.success("✅ API key saved to session")

    st.markdown("#### Default Model")
    model = st.selectbox(
        "Default AI Model:",
        ["claude-opus-4-5", "claude-sonnet-4-5", "claude-3-5-haiku-20241022"],
        index=0,
        help="claude-opus-4-5 provides best quality. claude-3-5-haiku-20241022 is fastest.",
    )
    st.session_state["default_model"] = model

    st.markdown("---")
    st.markdown("#### .env File Setup (Recommended)")
    st.markdown("""
    For persistent API key storage, create a `.env` file in the `streamlit-app/` directory:
    
    ```
    ANTHROPIC_API_KEY=sk-ant-your-key-here
    ```
    
    Then the app will automatically load it on startup.
    """)

    st.warning("""
    ⚠️ Never commit your `.env` file to version control.
    Add `.env` to your `.gitignore` file.
    """)

# ── Tab 2: System Status ─────────────────────────────────────────────────────
with tab2:
    st.markdown("### System Status")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Knowledge Base")
        kb_status = check_knowledge_base_status()
        for name, info in kb_status.items():
            if info["exists"] and info["file_count"] > 0:
                st.success(f"✅ {name.title()}: {info['file_count']} files")
            elif info["exists"]:
                st.warning(f"⚠️ {name.title()}: Empty")
            else:
                st.error(f"❌ {name.title()}: Not found")

    with col2:
        st.markdown("#### Available Regulations")
        regs = list_available_regulations()
        if regs:
            for reg in sorted(regs):
                st.markdown(f"✅ `{reg}`")
        else:
            st.warning("No regulation files found in knowledge base.")

    st.markdown("---")
    st.markdown("#### File System Paths")

    base_dir = Path(__file__).parent.parent.parent
    paths = {
        "Project Root": base_dir,
        "Streamlit App": base_dir / "streamlit-app",
        "HK-AICOS KB": base_dir / "HK-AICOS",
        "Uploads": base_dir / "streamlit-app" / "uploads",
        "Reports": base_dir / "streamlit-app" / "reports",
    }

    for name, path in paths.items():
        exists = "✅" if path.exists() else "❌"
        st.markdown(f"{exists} **{name}:** `{path}`")

    st.markdown("---")
    st.markdown("#### Phase Roadmap")

    phases = {
        "Phase 1 ✅": "Document skeleton - Regulations, Agents, SOPs, RAG structure",
        "Phase 2.0 ✅": "Streamlit MVP - File upload, AI analysis, PDF reports",
        "Phase 2.5 🔄": "Vector DB - Qdrant/Chroma integration, semantic search",
        "Phase 3 📋": "Full system - Multi-agent, ERP, Dashboard, Memory learning",
    }

    for phase, desc in phases.items():
        st.markdown(f"**{phase}:** {desc}")

# ── Tab 3: Agent Config ──────────────────────────────────────────────────────
with tab3:
    st.markdown("### Agent Routing Configuration")
    st.markdown("View how analysis types map to agents and regulations.")

    for analysis_type, config in AGENT_ROUTING.items():
        with st.expander(f"**{analysis_type}**"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Agents Involved:**")
                for agent in config["agents"]:
                    st.markdown(f"- {agent}")
                st.markdown("**Focus Areas:**")
                for focus in config["focus"]:
                    st.markdown(f"- `{focus}`")
            with col2:
                st.markdown("**Regulations Referenced:**")
                for reg in config["regulations"]:
                    st.markdown(f"- `{reg}`")
                st.markdown("**Risk Keywords:**")
                for kw in config["risk_keywords"]:
                    st.markdown(f"- {kw}")

# ── Tab 4: About ─────────────────────────────────────────────────────────────
with tab4:
    st.markdown("### About HK-AICOS")

    st.markdown("""
    <div style="background:#f8f9fa; padding:1.5rem; border-radius:8px; border-left:4px solid #1a3a5c;">
        <h4 style="color:#1a3a5c;">HK-AICOS</h4>
        <p><strong>Hong Kong AI Construction Operating System</strong></p>
        <p>Developed by <strong>Buildway Tech (HK) Limited</strong></p>
        <p>Version: Phase 2.0 MVP</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### System Architecture")
    st.markdown("""
    ```
    User Input (Photo / PDF / Question)
           ↓
    Agent Router (selects relevant agents)
           ↓
    RAG Reader (loads HK regulations + governance rules)
           ↓
    Prompt Builder (constructs structured analysis prompt)
           ↓
    Claude AI (performs analysis)
           ↓
    Risk Classifier (assigns risk level)
           ↓
    PDF Report Generator (creates downloadable report)
           ↓
    User (views results + downloads report)
    ```
    """)

    st.markdown("---")
    st.markdown("#### Governance & Disclaimer")
    st.error("""
    **Important Legal Notice**
    
    HK-AICOS provides AI-assisted analysis for reference purposes only.
    
    This system:
    - Does NOT provide formal professional opinions
    - Does NOT replace qualified professionals
    - Does NOT make final decisions
    
    For all matters involving Hong Kong law, structural safety, fire safety,
    electrical works, water supply, public roads, or legal liability,
    confirmation by Hong Kong registered professionals is MANDATORY.
    
    Registered professionals include: AP, RSE, RGE, REW, Fire Engineer,
    Licensed Plumber, Hong Kong Solicitor, Safety Officer.
    """)

    st.markdown("---")
    st.markdown("#### Technology Stack")
    tech = {
        "Frontend": "Streamlit",
        "AI Model": "Anthropic Claude (claude-opus-4-5 / claude-sonnet-4-5)",
        "PDF Generation": "ReportLab",
        "File Processing": "pypdf, Pillow",
        "Knowledge Base": "Markdown files (Phase 2.0) → Vector DB (Phase 2.5)",
        "Language": "Python 3.10+",
    }
    for k, v in tech.items():
        st.markdown(f"- **{k}:** {v}")
