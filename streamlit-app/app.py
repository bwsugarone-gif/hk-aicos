"""
app.py
HK-AICOS Phase 2.0 - Streamlit MVP Main Page

Client-friendly AI Construction Assistant by Buildway Tech (HK) Limited
"""

import streamlit as st
from pathlib import Path

# Page config
st.set_page_config(
    page_title="HK-AICOS | Buildway Tech",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for professional look
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #1a3a5c 0%, #4a6fa5 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
        font-weight: 700;
    }
    .main-header p {
        font-size: 1.1rem;
        opacity: 0.95;
    }
    .feature-box {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #4a6fa5;
        margin-bottom: 1rem;
    }
    .feature-box h3 {
        color: #1a3a5c;
        margin-bottom: 0.5rem;
    }
    .info-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        background: #e8f0fe;
        color: #1a3a5c;
        border-radius: 4px;
        font-size: 0.9rem;
        margin: 0.2rem;
    }
    .stButton>button {
        background: linear-gradient(135deg, #1a3a5c 0%, #4a6fa5 100%);
        color: white;
        font-weight: 600;
        border: none;
        padding: 0.6rem 2rem;
        border-radius: 6px;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #0f2942 0%, #3a5f95 100%);
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🏗️ Buildway Tech (HK) Limited</h1>
    <h2>HK-AICOS</h2>
    <p>AI Construction Operating System</p>
    <p style="font-size: 0.95rem; margin-top: 0.5rem;">
        Upload site photos, drawings or PDF documents.<br/>
        Get professional construction, safety and compliance analysis.
    </p>
</div>
""", unsafe_allow_html=True)

# Introduction
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 🎯 What is HK-AICOS?")
    st.markdown("""
    **HK-AICOS** (Hong Kong AI Construction Operating System) is an AI-powered construction analysis platform 
    designed specifically for Hong Kong construction projects.
    
    Our system provides:
    - **Safety Risk Analysis** - Identify unsafe practices and hazards
    - **Drawing & CAP Analysis** - Review technical drawings and submissions
    - **Regulatory Compliance** - Check against Hong Kong regulations
    - **Temporary Works Analysis** - Evaluate crane positioning, worker cages, etc.
    - **Cost & Programme Impact** - Assess financial and schedule implications
    - **PM Comprehensive Analysis** - Integrated project management insights
    """)

with col2:
    st.markdown("### 📊 System Status")
    st.info("**Phase 2.0** - Semi-Automated AI Assistant")
    
    # Check knowledge base status
    from utils.rag_reader import check_knowledge_base_status
    kb_status = check_knowledge_base_status()
    
    st.markdown("**Knowledge Base:**")
    for name, info in kb_status.items():
        if info["exists"]:
            st.success(f"✅ {name.title()}: {info['file_count']} files")
        else:
            st.warning(f"⚠️ {name.title()}: Not found")

# Features
st.markdown("---")
st.markdown("### 🚀 Available Analysis Types")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="feature-box">
        <h3>🦺 Safety Analysis</h3>
        <p>Identify safety risks, PPE compliance, and hazardous conditions in site photos.</p>
        <span class="info-badge">High Priority</span>
        <span class="info-badge">Real-time</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-box">
        <h3>📐 Drawing Analysis</h3>
        <p>Review CAP, MIB, and technical drawings for compliance and constructability.</p>
        <span class="info-badge">Technical</span>
        <span class="info-badge">Regulatory</span>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-box">
        <h3>⚖️ Compliance Check</h3>
        <p>Verify compliance with Hong Kong regulations (BD, EMSD, EPD, Labour, etc.).</p>
        <span class="info-badge">Legal</span>
        <span class="info-badge">Mandatory</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-box">
        <h3>🏗️ Temporary Works</h3>
        <p>Analyze crane positioning, worker cages, and temporary platform locations.</p>
        <span class="info-badge">Safety Critical</span>
        <span class="info-badge">AP Required</span>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-box">
        <h3>💰 Cost & Programme</h3>
        <p>Assess cost implications, VO impacts, and schedule delays.</p>
        <span class="info-badge">Financial</span>
        <span class="info-badge">QS Review</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-box">
        <h3>📊 PM Analysis</h3>
        <p>Comprehensive project management analysis integrating all aspects.</p>
        <span class="info-badge">Holistic</span>
        <span class="info-badge">Decision Support</span>
    </div>
    """, unsafe_allow_html=True)

# How to use
st.markdown("---")
st.markdown("### 📖 How to Use")

st.markdown("""
1. **Select an analysis type** from the sidebar (left menu)
2. **Upload your file** (photo, drawing, or PDF document)
3. **Enter your question** or describe what you need analyzed
4. **Generate analysis** - Our AI will provide professional insights
5. **Download PDF report** - Get a mobile-friendly report with risk assessment

**Supported file types:** JPG, PNG, PDF (max 20MB)
""")

# Important notices
st.markdown("---")
st.markdown("### ⚠️ Important Notices")

col1, col2 = st.columns(2)

with col1:
    st.warning("""
    **AI-Assisted Analysis Only**
    
    This system provides AI-assisted analysis for reference purposes only. 
    All analyses must be reviewed and confirmed by qualified professionals.
    
    The AI does not make final decisions or provide formal professional opinions.
    """)

with col2:
    st.error("""
    **Professional Confirmation Required**
    
    For matters involving:
    - Structural safety
    - Fire safety systems
    - Electrical/MEP works
    - Public roads/excavation
    - Legal/contractual issues
    
    **Must be confirmed by Hong Kong registered professionals** (AP, RSE, REW, etc.)
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem 0;">
    <p><strong>Buildway Tech (HK) Limited</strong></p>
    <p>HK-AICOS Phase 2.0 | AI Construction Operating System</p>
    <p style="font-size: 0.85rem;">
        Powered by advanced AI technology | Designed for Hong Kong construction industry
    </p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### 🏗️ HK-AICOS")
    st.markdown("**Phase 2.0** - Semi-Automated AI Assistant")
    
    st.markdown("---")
    st.markdown("### 📋 Quick Start")
    st.markdown("""
    1. Choose analysis type from pages above
    2. Upload your file
    3. Enter question
    4. Generate report
    """)
    
    st.markdown("---")
    st.markdown("### 📞 Support")
    st.info("""
    For technical support or inquiries:
    
    **Buildway Tech (HK) Limited**
    
    Email: info@buildwaytech.hk
    """)
    
    st.markdown("---")
    st.markdown("### 🔒 Data Privacy")
    st.markdown("""
    <small>
    All uploaded files are processed securely and stored locally. 
    No data is shared with third parties.
    </small>
    """, unsafe_allow_html=True)
