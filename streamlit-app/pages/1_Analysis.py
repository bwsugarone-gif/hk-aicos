"""
pages/1_Analysis.py
HK-AICOS Phase 2.0 - Main Analysis Page

Handles file upload, question input, and AI analysis generation.
"""

import streamlit as st
from pathlib import Path
import sys
import os

# Add parent directory to path for utils imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.agent_router import get_all_analysis_types, get_routing, build_analysis_prompt, get_required_professionals
from utils.risk_classifier import classify_risk, get_risk_info, format_risk_badge
from utils.file_loader import process_uploaded_file, is_allowed_file
from utils.rag_reader import build_rag_context
from utils.report_generator import generate_pdf_report

st.set_page_config(
    page_title="Analysis | HK-AICOS",
    page_icon="🔍",
    layout="wide",
)

st.markdown("""
<style>
    .analysis-header {
        background: linear-gradient(135deg, #1a3a5c 0%, #4a6fa5 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
    }
    .risk-box {
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border: 2px solid;
    }
    .result-box {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #4a6fa5;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="analysis-header">
    <h2>🔍 AI Construction Analysis</h2>
    <p>Upload a file and enter your question to get professional AI-assisted analysis.</p>
</div>
""", unsafe_allow_html=True)

# ── Step 1: Analysis Type ────────────────────────────────────────────────────
st.markdown("### Step 1: Select Analysis Type")
analysis_types = get_all_analysis_types()
analysis_type = st.selectbox(
    "Choose the type of analysis you need:",
    analysis_types,
    help="Select the most relevant analysis type for your question.",
)

routing = get_routing(analysis_type)
st.info(f"**Agents involved:** {', '.join(routing['agents'])}")

# ── Step 2: File Upload ──────────────────────────────────────────────────────
st.markdown("### Step 2: Upload File (Optional)")
uploaded_file = st.file_uploader(
    "Upload a site photo, drawing, or PDF document",
    type=["jpg", "jpeg", "png", "pdf"],
    help="Supported: JPG, PNG, PDF (max 20MB)",
)

file_data = None
if uploaded_file is not None:
    if not is_allowed_file(uploaded_file.name):
        st.error("❌ File type not supported. Please upload JPG, PNG, or PDF.")
    else:
        with st.spinner("Processing file..."):
            file_data = process_uploaded_file(uploaded_file)

        if file_data["type"] == "image":
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(uploaded_file, caption=uploaded_file.name, use_container_width=True)
            with col2:
                st.success(f"✅ Image loaded: {uploaded_file.name}")
                st.markdown(f"**Details:** {file_data['description']}")
        elif file_data["type"] == "pdf":
            st.success(f"✅ PDF loaded: {uploaded_file.name}")
            st.markdown(f"**Extracted:** {file_data['description']}")
            with st.expander("Preview extracted text"):
                st.text(file_data["content"][:2000] + ("..." if len(file_data["content"]) > 2000 else ""))

# ── Step 3: Question ─────────────────────────────────────────────────────────
st.markdown("### Step 3: Enter Your Question")
question = st.text_area(
    "Describe what you need analyzed:",
    placeholder="e.g. 請分析這張地盤照片的安全風險，特別是高空工作及PPE使用情況。",
    height=120,
    help="Be specific about what you want to know. Include project context if relevant.",
)

project_ref = st.text_input(
    "Project Reference (optional):",
    placeholder="e.g. BW-2025-001",
)

# ── Step 4: Generate Analysis ────────────────────────────────────────────────
st.markdown("### Step 4: Generate Analysis")

# API Key input
with st.expander("⚙️ AI Configuration", expanded=False):
    api_key = st.text_input(
        "Anthropic API Key:",
        type="password",
        help="Enter your Anthropic Claude API key. This is stored in session only.",
        placeholder="sk-ant-...",
    )
    model_choice = st.selectbox(
        "Model:",
        ["claude-opus-4-5", "claude-sonnet-4-5", "claude-3-5-haiku-20241022"],
        help="claude-opus-4-5 provides best analysis quality.",
    )

col1, col2 = st.columns([1, 3])
with col1:
    generate_btn = st.button("🚀 Generate Analysis", type="primary", use_container_width=True)

if generate_btn:
    if not question.strip():
        st.error("❌ Please enter a question before generating analysis.")
    else:
        # Build context
        file_description = file_data["description"] if file_data else ""
        file_content = file_data["content"] if file_data else ""

        # Get RAG context from knowledge base
        rag_context = build_rag_context(routing["regulations"])

        # Build prompt
        full_prompt = build_analysis_prompt(
            analysis_type=analysis_type,
            question=question,
            file_description=file_description + ("\n\nFile Content:\n" + file_content if file_content else ""),
            rag_context=rag_context,
        )

        # Get required professionals
        professionals = get_required_professionals(analysis_type, question, file_description)

        # Call AI
        with st.spinner("🤖 AI is analyzing... This may take 30-60 seconds."):
            try:
                if not api_key:
                    # Demo mode - show prompt only
                    st.warning("⚠️ No API key provided. Showing analysis prompt in demo mode.")
                    analysis_result = f"""[DEMO MODE - No API Key Provided]

This is what would be sent to Claude AI for analysis:

Analysis Type: {analysis_type}
Question: {question}
File: {file_description or 'No file uploaded'}

The AI would analyze this and provide:
1. Input Data Summary
2. Engineering Analysis  
3. Safety Analysis
4. Regulatory Compliance Analysis
5. Cost & Programme Impact
6. Risk Level Assessment
7. Recommended Follow-up Actions
8. Items Requiring Human PM Confirmation
9. Professional Confirmation Required

To enable full AI analysis, please enter your Anthropic API key in the configuration section above.
"""
                else:
                    import anthropic
                    client = anthropic.Anthropic(api_key=api_key)

                    # For image files, use vision API
                    if file_data and file_data["type"] == "image":
                        import base64
                        with open(file_data["path"], "rb") as img_file:
                            img_b64 = base64.standard_b64encode(img_file.read()).decode()
                        ext = file_data["path"].suffix.lower()
                        media_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"

                        message = client.messages.create(
                            model=model_choice,
                            max_tokens=4096,
                            messages=[{
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image",
                                        "source": {
                                            "type": "base64",
                                            "media_type": media_type,
                                            "data": img_b64,
                                        },
                                    },
                                    {"type": "text", "text": full_prompt},
                                ],
                            }],
                        )
                    else:
                        message = client.messages.create(
                            model=model_choice,
                            max_tokens=4096,
                            messages=[{"role": "user", "content": full_prompt}],
                        )

                    analysis_result = message.content[0].text

                # Store in session state
                st.session_state["last_analysis"] = {
                    "analysis_type": analysis_type,
                    "question": question,
                    "analysis_result": analysis_result,
                    "file_description": file_description,
                    "professionals": professionals,
                    "project_ref": project_ref,
                }

            except ImportError:
                st.error("❌ anthropic package not installed. Run: pip install anthropic")
                st.stop()
            except Exception as e:
                st.error(f"❌ Analysis failed: {str(e)}")
                st.stop()

        st.success("✅ Analysis complete!")

# ── Display Results ──────────────────────────────────────────────────────────
if "last_analysis" in st.session_state:
    data = st.session_state["last_analysis"]

    st.markdown("---")
    st.markdown("## 📊 Analysis Results")

    # Risk classification
    risk_level = classify_risk(
        data["analysis_type"],
        data["question"],
        data["analysis_result"],
    )
    risk_info = get_risk_info(risk_level)

    # Risk banner
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            f"""
            <div style="
                background:{risk_info['bg_color']};
                border:2px solid {risk_info['color']};
                border-radius:8px;
                padding:1rem;
                text-align:center;
                margin:1rem 0;
            ">
                <h2 style="color:{risk_info['color']}; margin:0;">
                    {risk_info['emoji']} {risk_info['label']}
                </h2>
                <p style="color:{risk_info['color']}; margin:0.5rem 0 0 0;">
                    {risk_info['description']}
                </p>
                <p style="color:{risk_info['color']}; font-weight:bold; margin:0.3rem 0 0 0;">
                    Action: {risk_info['action']} | Response: {risk_info['response_time']}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Analysis content
    st.markdown("### 📋 Analysis Report")
    st.markdown(
        f'<div class="result-box">{data["analysis_result"].replace(chr(10), "<br/>")}</div>',
        unsafe_allow_html=True,
    )

    # Professionals required
    if data["professionals"]:
        st.markdown("### 👷 Professional Confirmation Required")
        for prof in data["professionals"]:
            st.warning(f"⚠️ **{prof}** confirmation required")

    # Download PDF
    st.markdown("### 📥 Download Report")
    col1, col2 = st.columns([1, 3])
    with col1:
        try:
            pdf_bytes = generate_pdf_report(
                analysis_type=data["analysis_type"],
                question=data["question"],
                risk_level=risk_level,
                analysis_result=data["analysis_result"],
                filename_hint=data["file_description"],
                professionals_required=data["professionals"],
                project_ref=data["project_ref"],
            )
            st.download_button(
                label="📄 Download PDF Report",
                data=pdf_bytes,
                file_name=f"HK-AICOS-{data['analysis_type']}-Report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"PDF generation failed: {str(e)}")

    # Disclaimer
    st.markdown("---")
    st.error("""
    ⚠️ **Disclaimer**: This AI analysis is for reference only. 
    All findings must be reviewed and confirmed by qualified professionals before any action is taken.
    For matters involving structural safety, fire safety, electrical works, public roads, or legal issues,
    confirmation by Hong Kong registered professionals (AP, RSE, REW, etc.) is mandatory.
    """)
