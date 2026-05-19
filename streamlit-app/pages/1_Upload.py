"""
pages/1_Upload.py
HK-AICOS Phase 2.0 - 上載分析頁（客戶版）

Buildway Tech (HK) Limited
"""

import streamlit as st
from pathlib import Path
from datetime import datetime
import sys
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    # 先嘗試 streamlit-app/.env，再嘗試 project root .env
    _env1 = Path(__file__).parent.parent / ".env"
    _env2 = Path(__file__).parent.parent.parent / ".env"
    if _env1.exists():
        load_dotenv(_env1)
    elif _env2.exists():
        load_dotenv(_env2)
    else:
        load_dotenv()
except ImportError:
    pass

from utils.agent_router import (
    get_all_analysis_types, get_routing, build_analysis_prompt,
    get_required_professionals, get_agents_ordered, build_prompt_from_agents,
    AGENT_DEFINITIONS, AGENT_ORDER, DEFAULT_SELECTED_AGENTS,
)
from utils.smart_agent_router import (
    recommend_agents,
    filter_agents_by_sufficiency,
    build_insufficient_notice,
)
from utils.risk_classifier import classify_risk, get_risk_info
from utils.file_loader import process_uploaded_file, is_allowed_file, get_file_type_label
from utils.rag_reader import build_rag_context
from utils.rag_manager import get_relevant_context_for_agents
from utils.lang import UPLOAD, ANALYSIS_TYPES, AGENTS, AGENT_ORDER as AGENT_ORDER_LANG, NAV, BRAND
from utils.logo_helper import sidebar_logo
from utils.session_memory import save_session as save_legacy_session, get_prior_context, make_session_id
from utils.report_generator import _department_mapping, _split_agent_sections, generate_pdf_report
from utils.risk_calibrator import calculate_overall_project_risk
from utils.conflict_resolver import resolve_agent_conflicts
from utils.project_manager import (
    append_risk_event,
    build_pm_memory_context,
    create_project,
    get_project_report_path,
    load_project,
    save_session as save_project_session,
)
from utils.action_manager import auto_create_action_from_session, load_action_items
from utils.image_understanding import process_image_with_understanding
from utils.site_context_engine import (
    analyse_site_context,
    apply_context_risk_to_level,
)
from utils.site_logic_engine import analyse_site_logic, format_site_logic_for_report
from utils.progress_tracker import analyse_progress, format_progress_for_report
from utils.delay_concern_engine import analyse_delay_concern, format_delay_concern_for_report

st.set_page_config(
    page_title="上載分析 | HK-AICOS",
    page_icon="📤",
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

    .agent-card {
        background: #f4f6f9;
        border: 2px solid #e0e6ef;
        border-radius: 10px;
        padding: 0.9rem 1rem;
        margin-bottom: 0.6rem;
        transition: border-color 0.2s, background 0.2s;
    }
    .agent-card.selected {
        border-color: #1a3a5c;
        background: #eaf0fb;
    }
    .agent-card-title {
        font-size: 1rem;
        font-weight: 700;
        color: #1a3a5c;
        margin-bottom: 0.2rem;
    }
    .agent-card-desc {
        font-size: 0.85rem;
        color: #555;
        margin: 0;
    }
    .agent-badge {
        display: inline-block;
        background: #1a3a5c;
        color: white;
        border-radius: 20px;
        padding: 0.15rem 0.7rem;
        font-size: 0.78rem;
        font-weight: 600;
        margin: 0.15rem 0.2rem 0.15rem 0;
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

    .step-box {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(26,58,92,0.08);
        margin-bottom: 1.2rem;
        border-left: 5px solid #c9a84c;
    }
    .step-label {
        font-size: 0.8rem;
        font-weight: 700;
        color: #c9a84c;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.5rem;
    }
    .step-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #1a3a5c;
        margin-bottom: 0.8rem;
    }

    .analysis-type-btn {
        background: #f4f6f9;
        border: 2px solid #e0e6ef;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        cursor: pointer;
        transition: all 0.2s;
        margin-bottom: 0.5rem;
        width: 100%;
        text-align: left;
        font-size: 0.95rem;
        color: #1a3a5c;
    }
    .analysis-type-btn:hover {
        border-color: #1a3a5c;
        background: #e8f0fe;
    }
    .analysis-type-btn.selected {
        border-color: #c9a84c;
        background: #fdf8ee;
        font-weight: 600;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #c9a84c 0%, #a8873a 100%);
        color: #1a3a5c;
        font-weight: 700;
        font-size: 1.2rem;
        padding: 1rem 2rem;
        border: none;
        border-radius: 10px;
        width: 100%;
    }

    @media (max-width: 768px) {
        .page-header h2 { font-size: 1.3rem; }
        .step-box { padding: 1rem; }
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
    st.page_link("pages/3_History.py",   label="🕘 歷史紀錄")
    st.page_link("pages/7_Project_Dashboard.py", label="📊 工程總覽")
    st.page_link("pages/8_Risk_Center.py", label="⚠️ 工程風險中心")
    st.page_link("pages/9_Action_Tracker.py", label="✅ 跟進事項中心")
    st.page_link("pages/6_Memory_Manager.py", label="🧠 工程記憶管理")
    st.page_link("pages/5_Translate.py", label="📑 文件翻譯與轉換")
    st.page_link("pages/4_About.py",     label="ℹ️ 關於 Buildway Tech")
    st.markdown("---")
    st.markdown('<div style="font-size:0.78rem; color:#aac4e0;">🔒 所有資料安全處理</div>', unsafe_allow_html=True)

# ── Page Header ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <h2>📤 上載分析</h2>
    <p>上載工程相片、圖紙或 PDF，選擇分析類型，取得 AI 工程分析報告。</p>
</div>
""", unsafe_allow_html=True)

# ── 第一步：上載文件 ──────────────────────────────────────────────────────────
MAX_FILES = 3
MAX_TOTAL_SIZE_MB = 50
MAX_TOTAL_SIZE_BYTES = MAX_TOTAL_SIZE_MB * 1024 * 1024

st.markdown('<div class="step-box">', unsafe_allow_html=True)
st.markdown('<div class="step-label">第一步</div>', unsafe_allow_html=True)
st.markdown('<div class="step-title">📎 上載文件</div>', unsafe_allow_html=True)
st.markdown(
    f"支援 JPG、PNG、PDF、DOCX、XLSX"
    f"（最多 {MAX_FILES} 個檔案，總大小上限 {MAX_TOTAL_SIZE_MB}MB）"
)

uploaded_files = st.file_uploader(
    "選擇文件",
    type=["jpg", "jpeg", "png", "pdf", "docx", "xlsx"],
    accept_multiple_files=True,
    label_visibility="collapsed",
)

# ── 多檔案驗證及處理 ──────────────────────────────────────────────────────────
all_file_data = []  # list of processed file_data dicts

if uploaded_files:
    # Enforce max file count
    if len(uploaded_files) > MAX_FILES:
        st.error(f"❌ 最多只能上載 {MAX_FILES} 個檔案，請移除多餘的檔案。")
        uploaded_files = uploaded_files[:MAX_FILES]

    # Check total size
    total_size_bytes = sum(uf.size for uf in uploaded_files)
    total_size_mb = total_size_bytes / (1024 * 1024)

    if total_size_bytes > MAX_TOTAL_SIZE_BYTES:
        st.error(f"❌ 檔案過大，請分批提交或壓縮文件。（總大小：{total_size_mb:.1f} MB，上限：{MAX_TOTAL_SIZE_MB} MB）")
        uploaded_files = []

    # File list UI — show type, size, count
    if uploaded_files:
        st.markdown(
            f"**已上載檔案：** 共 {len(uploaded_files)} 個，"
            f"總大小 {total_size_mb:.2f} MB"
        )
        file_list_rows = []
        type_error_files = []

        for uf in uploaded_files:
            size_mb = uf.size / (1024 * 1024)
            type_label = get_file_type_label(uf.name)

            if not is_allowed_file(uf.name):
                type_error_files.append(uf.name)
                file_list_rows.append(
                    f"❌ **{uf.name}** — {size_mb:.2f} MB — 不支援格式"
                )
            else:
                file_list_rows.append(
                    f"✅ **{uf.name}** — {size_mb:.2f} MB — {type_label}"
                )

        for row in file_list_rows:
            st.markdown(row)

        if type_error_files:
            st.error(
                f"❌ 不支援此文件類型：{', '.join(type_error_files)}。"
                f"請上載 JPG、PNG、PDF、DOCX 或 XLSX。"
            )

    # Process valid files
    valid_files = [
        uf for uf in uploaded_files
        if is_allowed_file(uf.name)
    ]

    if valid_files:
        with st.spinner("處理文件中..."):
            for uf in valid_files:
                fd = process_uploaded_file(uf)
                all_file_data.append(fd)

        # Preview each file + process image understanding
        for i, (uf, fd) in enumerate(zip(valid_files, all_file_data)):
            ocr_status = fd.get("ocr_status", "")
            ocr_message = fd.get("ocr_message", "")
            ocr_warning = fd.get("ocr_warning", "")
            
            # Process image understanding for images with OCR
            if fd["type"] == "image" and fd.get("ocr_used"):
                try:
                    understanding_result = process_image_with_understanding(fd)
                    fd["image_understanding"] = understanding_result
                except Exception as img_err:
                    print(f"[Image Understanding] WARNING: {img_err}", file=sys.stderr)
                    fd["image_understanding"] = None
            
            if fd["type"] == "image":
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.image(uf, caption=uf.name, use_container_width=True)
                with col2:
                    st.success(f"✅ 圖片已載入：{uf.name}")
                    if ocr_status == "OCR_SUCCESS":
                        st.success("✅ 已透過 OCR 成功抽取文字")
                        
                        # Show image understanding results
                        img_understanding = fd.get("image_understanding")
                        if img_understanding:
                            structured = img_understanding.get("structured_info", {})
                            
                            # Show safety warnings prominently
                            if structured.get("has_safety_concern"):
                                st.warning("⚠️ 此圖片包含安全警告或風險關鍵字")
                            
                            # Show extracted info in expander
                            with st.expander("📋 圖片文字辨識詳情"):
                                if structured.get("safety_keywords_found"):
                                    st.markdown(f"**安全關鍵字：** {', '.join(structured['safety_keywords_found'])}")
                                if structured.get("warnings"):
                                    st.markdown(f"**警告內容：** {', '.join(structured['warnings'])}")
                                if structured.get("locations"):
                                    st.markdown(f"**位置：** {', '.join(structured['locations'])}")
                                if structured.get("numbers"):
                                    st.markdown(f"**編號/數字：** {', '.join(structured['numbers'])}")
                                if structured.get("dates"):
                                    st.markdown(f"**日期：** {', '.join(structured['dates'])}")
                                
                                extracted_text = fd.get("extracted_text", "")
                                if extracted_text:
                                    preview = extracted_text[:300] + ("..." if len(extracted_text) > 300 else "")
                                    st.text_area("辨識到的文字", value=preview, height=150, disabled=True)
                    
                    elif ocr_status in {"OCR_FAILED", "OCR_UNAVAILABLE"}:
                        st.warning("未能透過 OCR 抽取文字，請提供較清晰文件或可選取文字 PDF。")
            elif fd["type"] == "pdf":
                st.success(f"✅ PDF 已載入：{uf.name}")
                if ocr_status == "OCR_SUCCESS":
                    st.success("已透過 OCR 成功抽取文字")
                elif ocr_status in {"OCR_FAILED", "OCR_UNAVAILABLE"}:
                    st.warning("未能透過 OCR 抽取文字，請提供較清晰文件或可選取文字 PDF。")
                elif ocr_status == "OCR_REQUIRED":
                    st.info("此文件可能為掃描 PDF，OCR 將於 Phase 3.2 支援。")
                if ocr_warning:
                    st.info(ocr_warning)
                with st.expander(f"預覽：{uf.name}"):
                    preview = fd["content"][:1500] + ("..." if len(fd["content"]) > 1500 else "")
                    st.text(preview)
            elif fd["type"] == "docx":
                st.success(f"✅ Word 文件已載入：{uf.name}")
                with st.expander(f"預覽：{uf.name}"):
                    preview = fd["content"][:1500] + ("..." if len(fd["content"]) > 1500 else "")
                    st.text(preview)
            elif fd["type"] == "xlsx":
                st.success(f"✅ Excel 試算表已載入：{uf.name}")
                with st.expander(f"預覽：{uf.name}"):
                    preview = fd["content"][:1500] + ("..." if len(fd["content"]) > 1500 else "")
                    st.text(preview)

        # Merge all file data into session state
        # combined_description: all file descriptions joined
        # combined_content: all text content joined
        # primary_file_data: first file (used for image API calls)
        combined_description = "\n\n---\n\n".join(
            f"[檔案 {i+1}：{fd['description']}]" for i, fd in enumerate(all_file_data)
        )
        combined_content = "\n\n---\n\n".join(
            f"[檔案 {i+1}：{valid_files[i].name}]\n{fd['content']}"
            for i, fd in enumerate(all_file_data)
            if fd.get("content")
        )
        combined_names = "、".join(uf.name for uf in valid_files)

        # Build a merged file_data object
        merged_file_data = {
            "type": all_file_data[0]["type"] if len(all_file_data) == 1 else "multi",
            "description": combined_description,
            "content": combined_content,
            "path": all_file_data[0].get("path") if len(all_file_data) == 1 else None,
            "file_count": len(all_file_data),
            "all_file_data": all_file_data,
        }

        st.session_state["current_file_data"] = merged_file_data
        st.session_state["current_file_name"] = combined_names
        st.session_state["current_all_file_data"] = all_file_data
        st.session_state["current_valid_files"] = valid_files

        if len(valid_files) > 1:
            st.info(f"ℹ️ 已合併 {len(valid_files)} 個檔案，將作為同一工程項目進行分析。")

st.markdown('</div>', unsafe_allow_html=True)

# ── 第二步：選擇分析類型 ──────────────────────────────────────────────────────
st.markdown('<div class="step-box">', unsafe_allow_html=True)
st.markdown('<div class="step-label">第二步</div>', unsafe_allow_html=True)
st.markdown('<div class="step-title">🎯 選擇分析類型</div>', unsafe_allow_html=True)

# 客戶友善的分析類型顯示 — 從 lang.py 統一管理
ANALYSIS_DISPLAY = ANALYSIS_TYPES

# 預設選擇
if "selected_analysis_type" not in st.session_state:
    st.session_state["selected_analysis_type"] = "安全風險分析"

cols_type = st.columns(2)
analysis_keys = list(ANALYSIS_DISPLAY.keys())
for i, key in enumerate(analysis_keys):
    icon, display_name, desc = ANALYSIS_DISPLAY[key]
    with cols_type[i % 2]:
        is_selected = st.session_state["selected_analysis_type"] == key
        check = "✓ " if is_selected else ""
        if st.button(
            f"{check}{icon} {display_name}\n{desc}",
            key=f"type_{key}",
            use_container_width=True,
        ):
            st.session_state["selected_analysis_type"] = key
            st.rerun()

selected_type = st.session_state["selected_analysis_type"]
icon_s, name_s, _ = ANALYSIS_DISPLAY[selected_type]
st.info(f"已選擇：**{icon_s} {name_s}**")

st.markdown('</div>', unsafe_allow_html=True)

# ── 第二點五步：選擇 Agent ────────────────────────────────────────────────────
st.markdown('<div class="step-box">', unsafe_allow_html=True)
st.markdown('<div class="step-label">第二點五步</div>', unsafe_allow_html=True)
st.markdown('<div class="step-title">🤖 選擇分析 Agent</div>', unsafe_allow_html=True)

# ── Smart recommendation: compute based on current file + question ────────────
_current_fd   = st.session_state.get("current_file_data")
_smart_ftype  = _current_fd["type"] if _current_fd else ""
_smart_fcont  = _current_fd.get("content", "") if _current_fd else ""
_smart_q      = st.session_state.get("_smart_question_preview", "")
_smart_type   = st.session_state.get("selected_analysis_type", "綜合項目分析")

_recommended = recommend_agents(
    file_type=_smart_ftype,
    file_content=_smart_fcont,
    question=_smart_q,
    analysis_type=_smart_type,
)
_auto_selected_agents = _recommended if _recommended else ["pm", "safety"]


def _apply_agent_checkbox_state(agent_ids: list[str]) -> None:
    st.session_state["selected_agents"] = list(agent_ids)
    for _agent_id in AGENT_ORDER:
        st.session_state[f"agent_cb_{_agent_id}"] = _agent_id in agent_ids

# Only auto-apply recommendation on first load or when file changes
_file_sig = f"{_smart_ftype}:{st.session_state.get('current_file_name','')}"
if (
    "selected_agents" not in st.session_state
    or st.session_state.get("_last_file_sig") != _file_sig
):
    _apply_agent_checkbox_state(_auto_selected_agents)
    st.session_state["_last_file_sig"]  = _file_sig

# Show smart recommendation notice
if _auto_selected_agents:
    rec_badges = "".join(
        f'<span class="agent-badge">{AGENTS[aid]["icon"]} {AGENTS[aid]["label"]}</span>'
        for aid in _auto_selected_agents
        if aid in AGENTS
    )
    st.markdown(
        f'<div style="background:#eaf0fb;border-left:4px solid #1a3a5c;'
        f'border-radius:6px;padding:0.7rem 1rem;margin-bottom:0.8rem;font-size:0.9rem;">'
        f'💡 系統已根據文件類型自動選擇建議 Agent，可自行調整。<br/>'
        f'建議：{rec_badges}</div>',
        unsafe_allow_html=True,
    )

st.markdown("選擇參與分析的 Agent。每個 Agent 負責不同範疇，可多選。至少選擇一個。")

agent_cols = st.columns(2)
new_selection = []
for idx, agent_id in enumerate(AGENT_ORDER):
    agent_ui = AGENTS[agent_id]
    is_checked = agent_id in st.session_state["selected_agents"]
    with agent_cols[idx % 2]:
        checked = st.checkbox(
            f"{agent_ui['icon']} **{agent_ui['label']}** — {agent_ui['sublabel']}",
            value=is_checked,
            key=f"agent_cb_{agent_id}",
            help=agent_ui["desc"],
        )
        if checked:
            new_selection.append(agent_id)

# Update session state and warn on empty selection
st.session_state["selected_agents"] = new_selection

if not new_selection:
    st.warning("⚠️ 請至少選擇一個 Agent。")

# Show selected agent badges + over-selection warning
selected_agents = st.session_state["selected_agents"]
if len(selected_agents) > 5:
    st.warning(
        "⚠️ 選擇太多 Agent 可能令報告過長或出現資料不足，建議每次選 2 至 5 個。"
    )

if selected_agents:
    badges_html = "".join(
        f'<span class="agent-badge">{AGENTS[aid]["icon"]} {AGENTS[aid]["label"]}</span>'
        for aid in selected_agents
        if aid in AGENTS
    )
    st.markdown(
        f'<div style="margin-top:0.5rem;">已選擇 Agent：{badges_html}</div>',
        unsafe_allow_html=True,
    )

st.markdown('</div>', unsafe_allow_html=True)

# ── 第三步：輸入問題 ──────────────────────────────────────────────────────────
st.markdown('<div class="step-box">', unsafe_allow_html=True)
st.markdown('<div class="step-label">第三步</div>', unsafe_allow_html=True)
st.markdown('<div class="step-title">❓ 描述你的問題</div>', unsafe_allow_html=True)

question = st.text_area(
    "問題",
    placeholder="例如：呢張相有無不安全行為？呢個工人籠位置有無風險？",
    height=130,
    label_visibility="collapsed",
)

project_ref = st.text_input(
    "工程編號（選填）",
    placeholder="例如：BW-2025-001",
)

st.markdown('</div>', unsafe_allow_html=True)

# ── 第四步：生成分析 ──────────────────────────────────────────────────────────
st.markdown('<div class="step-box">', unsafe_allow_html=True)
st.markdown('<div class="step-label">第四步</div>', unsafe_allow_html=True)
st.markdown('<div class="step-title">🚀 生成分析報告</div>', unsafe_allow_html=True)

# API Key — 從環境變數或 secrets 取得，不向客戶顯示
def _get_api_key() -> tuple:
    """
    Returns (provider, api_key).
    provider: "anthropic" | "deepseek"
    Checks in order: Streamlit secrets → environment variables → session state.
    Never exposes key values to the UI.
    """
    # 1. Streamlit secrets — Anthropic
    try:
        key = st.secrets["ANTHROPIC_API_KEY"]
        if key:
            return ("anthropic", key)
    except Exception:
        pass

    # 2. Streamlit secrets — DeepSeek
    try:
        key = st.secrets["DEEPSEEK_API_KEY"]
        if key:
            return ("deepseek", key)
    except Exception:
        pass

    # 3. 環境變數 — Anthropic
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return ("anthropic", key)

    # 4. 環境變數 — DeepSeek
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return ("deepseek", key)

    # 5. Session state（Admin 模式下設定）
    key = st.session_state.get("_api_key", "")
    provider = st.session_state.get("_api_provider", "anthropic")
    return (provider, key)

generate_btn = st.button("🚀 生成分析報告", type="primary", use_container_width=True)

if generate_btn:
    if not question.strip():
        st.error("❌ 請先輸入你的問題。")
    elif not st.session_state.get("selected_agents"):
        st.error("❌ 請至少選擇一個 Agent。")
    else:
        file_data_to_use = st.session_state.get("current_file_data")
        file_description = file_data_to_use["description"] if file_data_to_use else ""
        file_content = file_data_to_use["content"] if file_data_to_use else ""
        file_name = st.session_state.get("current_file_name", "")

        # Build prompt from selected agents (agent-driven mode)
        selected_agent_ids = st.session_state["selected_agents"]
        all_regulations = []
        for aid in selected_agent_ids:
            if aid in AGENT_DEFINITIONS:
                for reg in AGENT_DEFINITIONS[aid]["regulations"]:
                    if reg not in all_regulations:
                        all_regulations.append(reg)
        rag_context = build_rag_context(all_regulations)
        try:
            rag_lite_context = get_relevant_context_for_agents(
                selected_agent_ids,
                question,
                ANALYSIS_DISPLAY[selected_type][1],
                top_k=5,
            )
            if rag_lite_context:
                rag_context = (
                    rag_context
                    + "\n\n## RAG Lite Relevant Context\n"
                    + rag_lite_context
                    if rag_context else
                    "## RAG Lite Relevant Context\n" + rag_lite_context
                )
        except Exception as rag_error:
            print(f"[RAG Lite] WARNING: context injection failed: {rag_error}", file=sys.stderr)

        # ── Project continuity: inject prior session context ──────────────────
        project_ref_clean = project_ref.strip()
        if project_ref_clean:
            try:
                create_project(project_ref_clean)
            except Exception:
                pass

        prior_context = get_prior_context(project_ref_clean) if project_ref_clean else ""
        pm_memory_context = (
            build_pm_memory_context(project_ref_clean)
            if project_ref_clean and "pm" in selected_agent_ids else ""
        )
        continuity_blocks = []
        if pm_memory_context:
            continuity_blocks.append(pm_memory_context)
        if prior_context:
            continuity_blocks.append(f"【項目歷史分析記錄】\n{prior_context}")
        if "pm" in selected_agent_ids:
            continuity_blocks.append(
                "【Phase 3.3A/3.3B/3.3C PM Agent 指示】\n"
                "- PM Agent 需要檢查工程時序、工序合理性、工種衝突、現場 flow。\n"
                "- PM Agent 需要引用 project timeline、repeated risks、unresolved actions。\n"
                "- PM Agent 需要輸出 Delay Concern Summary，但不可估算 delay days 或完工日期。\n"
                "- 如資料不足，不可估算工期，必須輸出：目前資料不足以判斷實際工期影響。"
            )
        prior_prefix = (
            "\n\n" + "\n\n".join(continuity_blocks) + "\n\n【本次分析】\n"
            if continuity_blocks else ""
        )

        # ── Collect file metadata early (needed for image context) ───────────
        _all_fd = st.session_state.get("current_all_file_data", [])

        # ── Image Text Understanding: build IMAGE_TEXT_CONTEXT for prompt ────
        _image_text_context_parts = []
        _image_safety_keywords = []
        _image_warnings = []
        _image_risk_elevated = False
        _image_risk_reason = ""
        for _fd in _all_fd:
            _img_und = _fd.get("image_understanding")
            if _img_und and _img_und.get("image_text_context"):
                _image_text_context_parts.append(_img_und["image_text_context"])
            if _img_und:
                _si = _img_und.get("structured_info", {})
                _image_safety_keywords.extend(_si.get("safety_keywords_found", []))
                _image_warnings.extend(_si.get("warnings", []))
                if _img_und.get("should_elevate_risk") and not _image_risk_elevated:
                    _image_risk_elevated = True
                    _image_risk_reason = _img_und.get("risk_elevation_reason", "")

        _combined_image_context = "\n\n".join(_image_text_context_parts)

        full_prompt = build_prompt_from_agents(
            selected_agent_ids=selected_agent_ids,
            question=question,
            file_description=(
                prior_prefix
                + file_description
                + ("\n\n文件內容:\n" + file_content if file_content else "")
                + ("\n\n" + _combined_image_context if _combined_image_context else "")
            ),
            rag_context=rag_context,
        )
        professionals = get_required_professionals(selected_type, question, file_description)
        provider, api_key = _get_api_key()

        # Generate a session_id now so it can be stored in last_analysis for PDF
        current_session_id = make_session_id()

        with st.spinner("正在分析中，請稍候..."):
            try:
                if not api_key:
                    # 無 API Key — 顯示診斷資訊
                    _secrets_keys = []
                    try:
                        _secrets_keys = list(st.secrets.keys())
                    except Exception:
                        _secrets_keys = ["(無法讀取 secrets)"]
                    st.error(
                        f"❌ 未能取得 API Key。\n\n"
                        f"**診斷資訊：**\n"
                        f"- provider 偵測：`{provider}`\n"
                        f"- st.secrets 可用 keys：`{_secrets_keys}`\n"
                        f"- DEEPSEEK_API_KEY 環境變數：`{bool(os.environ.get('DEEPSEEK_API_KEY'))}`\n"
                        f"- ANTHROPIC_API_KEY 環境變數：`{bool(os.environ.get('ANTHROPIC_API_KEY'))}`\n\n"
                        f"請在 Streamlit Cloud → Settings → Secrets 加入：\n"
                        f"```\nDEEPSEEK_API_KEY = \"sk-...\"\n```"
                    )
                    st.stop()

                elif provider == "deepseek":
                    # DeepSeek — OpenAI-compatible API
                    from openai import OpenAI as _OpenAI
                    ds_client = _OpenAI(
                        api_key=api_key,
                        base_url="https://api.deepseek.com",
                    )
                    ds_prompt = full_prompt
                    if file_data_to_use and file_data_to_use["type"] == "image":
                        ds_prompt = f"[圖片已上載：{file_name}]\n\n{full_prompt}"
                    response = ds_client.chat.completions.create(
                        model="deepseek-chat",
                        max_tokens=4096,
                        messages=[{"role": "user", "content": ds_prompt}],
                    )
                    analysis_result = response.choices[0].message.content

                else:
                    # Anthropic (default)
                    import anthropic
                    client = anthropic.Anthropic(api_key=api_key)

                    if file_data_to_use and file_data_to_use["type"] == "image":
                        import base64
                        with open(file_data_to_use["path"], "rb") as img_file:
                            img_b64 = base64.standard_b64encode(img_file.read()).decode()
                        ext = file_data_to_use["path"].suffix.lower()
                        media_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
                        message = client.messages.create(
                            model="claude-opus-4-5",
                            max_tokens=4096,
                            messages=[{
                                "role": "user",
                                "content": [
                                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": img_b64}},
                                    {"type": "text", "text": full_prompt},
                                ],
                            }],
                        )
                    else:
                        message = client.messages.create(
                            model="claude-opus-4-5",
                            max_tokens=4096,
                            messages=[{"role": "user", "content": full_prompt}],
                        )
                    analysis_result = message.content[0].text

                # Classify risk, then calibrate with Agent risk weights
                original_risk_level = classify_risk(selected_type, question, analysis_result)
                risk_level = original_risk_level
                # Elevate risk if image OCR detected safety keywords
                if _image_risk_elevated and risk_level == "低風險":
                    risk_level = "中風險"
                    original_risk_level = "中風險"
                calibration_result = {
                    "overall_risk_level": original_risk_level,
                    "overall_risk_score": 0.0,
                    "contributing_agents": [],
                    "highest_risk_agent": "",
                    "calibration_reason": "Risk calibration 未執行，使用原始風險。",
                    "safety_override": False,
                    "legal_override": False,
                }
                calibration_warning = ""
                try:
                    agent_sections = _split_agent_sections(analysis_result, selected_agent_ids)
                    agent_risk_inputs = {}
                    for aid in selected_agent_ids:
                        section_text = agent_sections.get(aid, "")
                        if section_text:
                            agent_risk_inputs[aid] = {"output": section_text}
                        else:
                            agent_risk_inputs[aid] = {
                                "output": analysis_result,
                                "risk_level": original_risk_level,
                            }
                    calibration_result = calculate_overall_project_risk(
                        agent_risk_inputs,
                        selected_agent_ids,
                    )
                    risk_level = calibration_result.get("overall_risk_level") or original_risk_level
                except Exception as cal_error:
                    calibration_warning = f"Risk calibration failed: {type(cal_error).__name__}: {cal_error}"
                    risk_level = original_risk_level

                # ── Conflict Resolution ───────────────────────────────────────
                conflict_result = {}
                try:
                    conflict_result = resolve_agent_conflicts(
                        agent_results=agent_risk_inputs if "agent_risk_inputs" in dir() else {},
                        selected_agents=selected_agent_ids,
                        calibration_result=calibration_result,
                    )
                    # PM override may further adjust risk level
                    _pm_risk = conflict_result.get("overall_risk")
                    if _pm_risk and _pm_risk != risk_level:
                        risk_level = _pm_risk
                except Exception:
                    conflict_result = {"fallback_used": True}

                # ── Site Context Awareness ────────────────────────────────────
                site_context = {}
                try:
                    _ocr_combined = " ".join(
                        fd.get("extracted_text", "") or ""
                        for fd in _all_fd
                    )
                    site_context = analyse_site_context(
                        text=file_content,
                        question=question,
                        ocr_text=_ocr_combined,
                    )
                    # Apply context risk modifier to current risk level
                    _ctx_modifier = site_context.get("risk_modifier", {}).get("combined_modifier", 1.0)
                    if _ctx_modifier > 1.0:
                        risk_level = apply_context_risk_to_level(risk_level, _ctx_modifier)
                        original_risk_level = risk_level
                except Exception as _ctx_err:
                    import sys as _sys
                    print(f"[site_context] WARNING: {_ctx_err}", file=_sys.stderr)

                # ── Evidence Confidence Layer ─────────────────────────────────
                evidence_result = {}
                try:
                    from utils.evidence_confidence import process_analysis_output
                    evidence_result = process_analysis_output(analysis_result, risk_level)
                    # Apply filtered text and adjusted risk
                    analysis_result = evidence_result.get("filtered_text", analysis_result)
                    _ev_adjusted_risk = evidence_result.get("adjusted_risk_level", risk_level)
                    if _ev_adjusted_risk != risk_level:
                        risk_level = _ev_adjusted_risk
                except Exception as _ev_err:
                    print(f"[evidence_confidence] WARNING: {_ev_err}", file=sys.stderr)

                # ── Phase 3.3A/B: Site logic + progress tracking ─────────────
                site_logic_result = {}
                progress_result = {}
                delay_concern_result = {}
                try:
                    _ocr_combined_for_logic = " ".join(
                        fd.get("extracted_text", "") or ""
                        for fd in _all_fd
                    )
                    site_logic_result = analyse_site_logic(
                        text="\n".join([file_content or "", analysis_result or ""]),
                        question=question,
                        ocr_text=_ocr_combined_for_logic,
                        site_context=site_context,
                    )
                except Exception as _logic_err:
                    print(f"[site_logic] WARNING: {_logic_err}", file=sys.stderr)

                try:
                    _project_data = load_project(project_ref_clean) if project_ref_clean else {}
                    try:
                        _action_items = load_action_items()
                    except Exception:
                        _action_items = []
                    _current_progress_session = {
                        "session_id": current_session_id,
                        "project_ref": project_ref_clean,
                        "time": datetime.now().isoformat(timespec="seconds"),
                        "analysis_type": ANALYSIS_DISPLAY[selected_type][1],
                        "analysis_result": analysis_result,
                        "summary": (analysis_result or "")[:300],
                        "question": question,
                        "risk_level": risk_level,
                        "calibrated_risk_level": risk_level,
                    }
                    progress_result = analyse_progress(
                        project_ref_clean,
                        _current_progress_session,
                        project_data=_project_data,
                        action_items=_action_items,
                    )
                except Exception as _progress_err:
                    print(f"[progress_tracker] WARNING: {_progress_err}", file=sys.stderr)

                try:
                    delay_concern_result = analyse_delay_concern(
                        project_ref=project_ref_clean,
                        current_session=_current_progress_session if "_current_progress_session" in locals() else {
                            "session_id": current_session_id,
                            "project_ref": project_ref_clean,
                            "time": datetime.now().isoformat(timespec="seconds"),
                            "analysis_result": analysis_result,
                            "summary": (analysis_result or "")[:300],
                            "question": question,
                            "risk_level": risk_level,
                        },
                        project_data=_project_data if "_project_data" in locals() else {},
                        action_items=_action_items if "_action_items" in locals() else [],
                        site_logic_result=site_logic_result,
                        progress_result=progress_result,
                        ocr_text=_ocr_combined_for_logic if "_ocr_combined_for_logic" in locals() else "",
                    )
                except Exception as _delay_err:
                    print(f"[delay_concern] WARNING: {_delay_err}", file=sys.stderr)

                if site_logic_result or progress_result or delay_concern_result:
                    pm_phase_33_block = "\n\nPM 工程狀態總結\n"
                    if site_logic_result:
                        pm_phase_33_block += format_site_logic_for_report(site_logic_result) + "\n"
                    if progress_result:
                        pm_phase_33_block += format_progress_for_report(progress_result) + "\n"
                    if delay_concern_result:
                        pm_phase_33_block += format_delay_concern_for_report(delay_concern_result) + "\n"
                    analysis_result = (analysis_result or "") + pm_phase_33_block

                # Derive departments for session record
                _dept_text = "\n".join([selected_type, question, analysis_result])
                _departments = _department_mapping(_dept_text)

                # Collect file metadata for session record
                _valid_fs = st.session_state.get("current_valid_files", [])
                _file_names = [uf.name for uf in _valid_fs] if _valid_fs else (
                    [file_name] if file_name else []
                )
                _file_types = [fd.get("type", "unknown") for fd in _all_fd] if _all_fd else []
                _ocr_used = any(fd.get("ocr_used") for fd in _all_fd)
                _ocr_page_count = sum(int(fd.get("ocr_page_count", 0) or 0) for fd in _all_fd)
                _ocr_status = "、".join(
                    sorted({str(fd.get("ocr_status", "")) for fd in _all_fd if fd.get("ocr_status")})
                )

                # Save session to JSON memory
                try:
                    save_legacy_session(
                        project_ref=project_ref,
                        file_names=_file_names,
                        file_types=_file_types,
                        selected_agents=selected_agent_ids,
                        risk_level=risk_level,
                        original_risk_level=original_risk_level,
                        calibrated_risk_level=risk_level,
                        calibrated_risk_score=calibration_result.get("overall_risk_score", 0.0),
                        highest_risk_agent=calibration_result.get("highest_risk_agent", ""),
                        calibration_reason=(
                            calibration_warning
                            or calibration_result.get("calibration_reason", "")
                        ),
                        ocr_used=_ocr_used,
                        ocr_page_count=_ocr_page_count,
                        ocr_status=_ocr_status,
                        image_ocr_context=_combined_image_context,
                        image_safety_keywords=list(dict.fromkeys(_image_safety_keywords)),
                        image_warnings=list(dict.fromkeys(_image_warnings)),
                        departments=_departments,
                        analysis_result=analysis_result,
                        analysis_type=ANALYSIS_DISPLAY[selected_type][1],
                        question=question,
                        session_id=current_session_id,
                    )
                except Exception:
                    pass  # Never crash the main flow due to session save failure

                report_path = ""
                if project_ref_clean:
                    try:
                        pdf_bytes = generate_pdf_report(
                            analysis_type=ANALYSIS_DISPLAY[selected_type][1],
                            question=question,
                            risk_level=risk_level,
                            analysis_result=analysis_result,
                            filename_hint=file_name,
                            professionals_required=professionals,
                            project_ref=project_ref_clean,
                            selected_agents=selected_agent_ids,
                            session_id=current_session_id,
                            original_risk_level=original_risk_level,
                            highest_risk_agent=calibration_result.get("highest_risk_agent", ""),
                            site_logic_result=site_logic_result,
                            progress_result=progress_result,
                            delay_concern_result=delay_concern_result,
                        )
                        project_report_path = get_project_report_path(project_ref_clean, current_session_id)
                        project_report_path.write_bytes(pdf_bytes)
                        report_path = str(project_report_path)
                    except Exception:
                        report_path = ""

                    try:
                        save_project_session(
                            project_ref=project_ref_clean,
                            session_id=current_session_id,
                            selected_agents=selected_agent_ids,
                            analysis_type=ANALYSIS_DISPLAY[selected_type][1],
                            analysis_result=analysis_result,
                            risk_level=risk_level,
                            original_risk_level=original_risk_level,
                            calibrated_risk_level=risk_level,
                            calibrated_risk_score=calibration_result.get("overall_risk_score", 0.0),
                            highest_risk_agent=calibration_result.get("highest_risk_agent", ""),
                            calibration_reason=(
                                calibration_warning
                                or calibration_result.get("calibration_reason", "")
                            ),
                            ocr_used=_ocr_used,
                            ocr_page_count=_ocr_page_count,
                            ocr_status=_ocr_status,
                            government_departments=_departments,
                            report_path=report_path,
                            question=question,
                            file_names=_file_names,
                            file_types=_file_types,
                        )
                        if risk_level != "低風險":
                            append_risk_event(
                                project_ref=project_ref_clean,
                                session_id=current_session_id,
                                risk=(analysis_result or "")[:160],
                                risk_level=risk_level,
                                status="open",
                            )
                        if delay_concern_result.get("memory_should_record"):
                            append_risk_event(
                                project_ref=project_ref_clean,
                                session_id=current_session_id,
                                risk=(
                                    f"Delay Concern {delay_concern_result.get('level')}: "
                                    f"score {delay_concern_result.get('score')} - "
                                    f"{delay_concern_result.get('summary', '')}"
                                )[:160],
                                risk_level=delay_concern_result.get("level", "Moderate Concern"),
                                status="open",
                            )
                    except Exception:
                        pass

                # ── Risk Score UI ─────────────────────────────────────────────
                _agent_scores = calibration_result.get("agent_scores", {})
                _detected_issues = calibration_result.get("detected_issues", [])
                _overall_score = calibration_result.get("overall_risk_score", 0)

                _risk_color = {
                    "低風險": "#28a745",
                    "中風險": "#fd7e14",
                    "高風險": "#dc3545",
                    "極高風險": "#6f0000",
                }.get(risk_level, "#6c757d")

                st.markdown(f"""
<div style="background:#f8f9fa;border:1px solid #dee2e6;border-radius:10px;
            padding:1rem 1.2rem;margin:1rem 0;">
  <div style="font-size:1rem;font-weight:700;color:#1a3a5c;margin-bottom:0.6rem;">
    📊 風險評分
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:0.8rem;margin-bottom:0.6rem;">
""", unsafe_allow_html=True)

                for _aid, _as in _agent_scores.items():
                    from utils.risk_calibrator import AGENT_RISK_PROFILES as _ARP
                    _aname = _ARP.get(_aid, {}).get("name", _aid)
                    _alevel = _as.get("risk_level", "中風險")
                    _ascore = _as.get("raw_score", 0)
                    _aconf = _as.get("confidence", 0)
                    _acolor = {
                        "低風險": "#28a745", "中風險": "#fd7e14",
                        "高風險": "#dc3545", "極高風險": "#6f0000",
                    }.get(_alevel, "#6c757d")
                    st.markdown(
                        f'<div style="background:white;border:1px solid #dee2e6;'
                        f'border-radius:6px;padding:0.4rem 0.8rem;font-size:0.85rem;">'
                        f'<b>{_aname}</b><br/>'
                        f'<span style="color:{_acolor};font-weight:600;">{_alevel}</span>'
                        f' &nbsp;分數：{_ascore}'
                        f' &nbsp;信心：{int(_aconf*100)}%'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                st.markdown(f"""
  </div>
  <div style="font-size:1rem;">
    整體風險：
    <span style="color:{_risk_color};font-weight:700;font-size:1.1rem;">{risk_level}</span>
    &nbsp;（加權分數：{_overall_score:.1f}）
  </div>
""", unsafe_allow_html=True)

                if _detected_issues:
                    with st.expander("🔍 偵測到的風險項目"):
                        for _issue in _detected_issues[:6]:
                            _icat = _issue.get("category", "")
                            _iconf = int(_issue.get("confidence", 0) * 100)
                            _iscore = _issue.get("score", 0)
                            _ilabel = _issue.get("label", "")
                            _icolor = {
                                "critical": "#6f0000", "high": "#dc3545",
                                "medium": "#fd7e14", "low": "#28a745",
                            }.get(_icat, "#6c757d")
                            st.markdown(
                                f'<span style="color:{_icolor};font-weight:600;">'
                                f'[{_icat.upper()}]</span> {_ilabel}'
                                f' — 分數 {_iscore}，信心 {_iconf}%',
                                unsafe_allow_html=True,
                            )

                st.markdown('</div>', unsafe_allow_html=True)

                # ── Agent Conflict Analysis UI ────────────────────────────────
                if conflict_result and not conflict_result.get("fallback_used"):
                    _conflicts = conflict_result.get("conflict_analysis", [])
                    _override_agent = conflict_result.get("override_agent", "PM Agent")
                    _override_reason = conflict_result.get("override_reason", "")
                    _can_continue = conflict_result.get("can_continue", "")
                    _merged_risks = conflict_result.get("merged_risks", [])
                    _agent_conf = conflict_result.get("agent_confidence", {})
                    _final_rec = conflict_result.get("final_recommendation", "")
                    _action_plan = conflict_result.get("final_action_plan", [])

                    _cc_color = {"Yes": "#28a745", "Limited": "#fd7e14", "No": "#dc3545"}.get(_can_continue, "#6c757d")
                    _cc_label = {"Yes": "✅ 可繼續施工", "Limited": "⚠️ 有限度施工", "No": "🚫 須停工整改"}.get(_can_continue, _can_continue)

                    st.markdown(f"""
<div style="background:#fff8f0;border:1px solid #fd7e14;border-radius:10px;
            padding:1rem 1.2rem;margin:1rem 0;">
  <div style="font-size:1rem;font-weight:700;color:#1a3a5c;margin-bottom:0.6rem;">
    🤝 PM Agent 最終整合判斷
  </div>
  <div style="margin-bottom:0.5rem;">
    可否繼續施工：<span style="color:{_cc_color};font-weight:700;">{_cc_label}</span>
  </div>
  <div style="font-size:0.9rem;color:#555;margin-bottom:0.4rem;">
    裁決依據：{_override_agent}
  </div>
  <div style="font-size:0.88rem;color:#666;">{_override_reason}</div>
</div>
""", unsafe_allow_html=True)

                    if _conflicts:
                        with st.expander("⚡ Agent 衝突分析"):
                            for _c in _conflicts:
                                st.markdown(f"- {_c.get('description', '')}")

                    if _merged_risks:
                        with st.expander("🔗 跨 Agent 合併風險"):
                            for _mr in _merged_risks[:5]:
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

                    if _action_plan:
                        with st.expander("📋 最終行動計劃"):
                            for _ap in _action_plan:
                                st.markdown(f"- {_ap}")

                st.session_state["last_analysis"] = {
                    "analysis_type": selected_type,
                    "analysis_display_name": ANALYSIS_DISPLAY[selected_type][1],
                    "question": question,
                    "analysis_result": analysis_result,
                    "file_description": file_description,
                    "file_name": file_name,
                    "professionals": professionals,
                    "project_ref": project_ref_clean,
                    "risk_level": risk_level,
                    "original_risk_level": original_risk_level,
                    "calibrated_risk_level": risk_level,
                    "calibrated_risk_score": calibration_result.get("overall_risk_score", 0.0),
                    "highest_risk_agent": calibration_result.get("highest_risk_agent", ""),
                    "evidence_result": evidence_result,
                    "calibration_reason": (
                        calibration_warning
                        or calibration_result.get("calibration_reason", "")
                    ),
                    "selected_agents": selected_agent_ids,
                    "session_id": current_session_id,
                    "departments": _departments,
                    "report_path": report_path,
                    "ocr_used": _ocr_used,
                    "ocr_page_count": _ocr_page_count,
                    "ocr_status": _ocr_status,
                    "agent_scores": _agent_scores,
                    "detected_issues": _detected_issues,
                    "conflict_result": conflict_result,
                    "site_context": site_context,
                    "site_logic_result": site_logic_result,
                    "progress_result": progress_result,
                    "delay_concern_result": delay_concern_result,
                }

                if risk_level != "低風險":
                    try:
                        auto_create_action_from_session({
                            "project_ref": project_ref_clean or "未填寫",
                            "session_id": current_session_id,
                            "risk_level": risk_level,
                            "calibrated_risk_level": risk_level,
                            "highest_risk_agent": calibration_result.get("highest_risk_agent", ""),
                            "selected_agents": selected_agent_ids,
                            "departments": _departments,
                            "question": question,
                            "analysis_summary": (analysis_result or "")[:300],
                            "calibration_reason": (
                                calibration_warning
                                or calibration_result.get("calibration_reason", "")
                            ),
                        })
                    except Exception as action_error:
                        st.session_state["action_tracker_warning"] = (
                            f"Action item 生成失敗：{type(action_error).__name__}: {action_error}"
                        )

            except ImportError as e:
                st.error(f"❌ 缺少依賴套件：`{e}`\n\n請確認 requirements.txt 包含 `openai` 及 `anthropic`。")
                st.stop()
            except Exception as e:
                st.error(f"❌ 分析錯誤：`{type(e).__name__}: {e}`")
                st.stop()

        st.success("✅ 分析完成！請前往「分析報告」查看結果。")
        st.page_link("pages/2_Report.py", label="📄 查看分析報告 →")

st.markdown('</div>', unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; color:#999; padding:1.5rem 0 0.5rem 0; font-size:0.82rem;">
    Buildway Tech (HK) Limited | HK-AICOS Phase 2.0
</div>
""", unsafe_allow_html=True)
