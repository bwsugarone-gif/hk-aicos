"""
pages/1_Upload.py
HK-AICOS Phase 2.0 - 上載分析頁（客戶版）

Buildway Tech (HK) Limited
"""

import streamlit as st
from pathlib import Path
import sys
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from utils.agent_router import get_all_analysis_types, get_routing, build_analysis_prompt, get_required_professionals
from utils.risk_classifier import classify_risk, get_risk_info
from utils.file_loader import process_uploaded_file, is_allowed_file
from utils.rag_reader import build_rag_context

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
    st.markdown("""
    <div style="text-align:center; padding: 1rem 0 0.5rem 0;">
        <div style="font-size:2.5rem;">🏗️</div>
        <div style="font-size:1.1rem; font-weight:700;">Buildway Tech</div>
        <div style="font-size:0.85rem; color:#c9a84c;">(HK) Limited</div>
    </div>
    """, unsafe_allow_html=True)
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
    <h2>📤 上載分析</h2>
    <p>上載工程相片、圖紙或 PDF，選擇分析類型，取得 AI 工程分析報告。</p>
</div>
""", unsafe_allow_html=True)

# ── 第一步：上載文件 ──────────────────────────────────────────────────────────
st.markdown('<div class="step-box">', unsafe_allow_html=True)
st.markdown('<div class="step-label">第一步</div>', unsafe_allow_html=True)
st.markdown('<div class="step-title">📎 上載文件</div>', unsafe_allow_html=True)
st.markdown("支援 JPG、PNG、PDF（最大 20MB）")

uploaded_file = st.file_uploader(
    "選擇文件",
    type=["jpg", "jpeg", "png", "pdf"],
    label_visibility="collapsed",
)

file_data = None
if uploaded_file is not None:
    if not is_allowed_file(uploaded_file.name):
        st.error("❌ 不支援此文件類型。請上載 JPG、PNG 或 PDF。")
    else:
        with st.spinner("處理文件中..."):
            file_data = process_uploaded_file(uploaded_file)
        st.session_state["current_file_data"] = file_data
        st.session_state["current_file_name"] = uploaded_file.name

        if file_data["type"] == "image":
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(uploaded_file, caption=uploaded_file.name, use_container_width=True)
            with col2:
                st.success(f"✅ 圖片已載入：{uploaded_file.name}")
        elif file_data["type"] == "pdf":
            st.success(f"✅ PDF 已載入：{uploaded_file.name}")
            with st.expander("預覽文件內容"):
                st.text(file_data["content"][:1500] + ("..." if len(file_data["content"]) > 1500 else ""))

st.markdown('</div>', unsafe_allow_html=True)

# ── 第二步：選擇分析類型 ──────────────────────────────────────────────────────
st.markdown('<div class="step-box">', unsafe_allow_html=True)
st.markdown('<div class="step-label">第二步</div>', unsafe_allow_html=True)
st.markdown('<div class="step-title">🎯 選擇分析類型</div>', unsafe_allow_html=True)

# 客戶友善的分析類型顯示
ANALYSIS_DISPLAY = {
    "安全風險分析": ("🦺", "工地安全分析", "分析工地相片，識別安全風險及不安全行為"),
    "法規 / 合規檢查": ("⚖️", "法規合規檢查", "對照香港法規，初步檢查工程合規情況"),
    "圖紙 / CAP / MIB 分析": ("📐", "圖紙 / 文件分析", "分析圖紙及工程文件，提取重點資料"),
    "臨時設施位置分析": ("🏗️", "臨時設施分析", "分析天秤、工人籠、臨時平台等位置及風險"),
    "PM 綜合分析": ("📋", "PM 工程分析", "綜合分析工程進度、資源及風險"),
    "成本 / 工期影響分析": ("💰", "成本及工期分析", "初步評估 VO、成本超支及工期延誤影響"),
}

# 預設選擇
if "selected_analysis_type" not in st.session_state:
    st.session_state["selected_analysis_type"] = "安全風險分析"

cols_type = st.columns(2)
analysis_keys = list(ANALYSIS_DISPLAY.keys())
for i, key in enumerate(analysis_keys):
    icon, display_name, desc = ANALYSIS_DISPLAY[key]
    with cols_type[i % 2]:
        is_selected = st.session_state["selected_analysis_type"] == key
        border_color = "#c9a84c" if is_selected else "#e0e6ef"
        bg_color = "#fdf8ee" if is_selected else "#f4f6f9"
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
def _get_api_key() -> str:
    # 1. Streamlit secrets
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        pass
    # 2. 環境變數
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    # 3. Session state（Admin 模式下設定）
    return st.session_state.get("_api_key", "")

generate_btn = st.button("🚀 生成分析報告", type="primary", use_container_width=True)

if generate_btn:
    if not question.strip():
        st.error("❌ 請先輸入你的問題。")
    else:
        file_data_to_use = st.session_state.get("current_file_data")
        file_description = file_data_to_use["description"] if file_data_to_use else ""
        file_content = file_data_to_use["content"] if file_data_to_use else ""
        file_name = st.session_state.get("current_file_name", "")

        routing = get_routing(selected_type)
        rag_context = build_rag_context(routing["regulations"])
        full_prompt = build_analysis_prompt(
            analysis_type=selected_type,
            question=question,
            file_description=file_description + ("\n\n文件內容:\n" + file_content if file_content else ""),
            rag_context=rag_context,
        )
        professionals = get_required_professionals(selected_type, question, file_description)
        api_key = _get_api_key()

        with st.spinner("正在分析中，請稍候..."):
            try:
                if not api_key:
                    # 無 API Key — 顯示友善提示，不暴露技術細節
                    st.warning("⚠️ 系統暫時未能連接分析服務。請聯絡 Buildway Tech 取得協助。")
                    analysis_result = (
                        "## 工程分析\n\n"
                        "分析服務暫時未能使用，請聯絡 Buildway Tech (HK) Limited 取得協助。\n\n"
                        "## 建議跟進事項\n\n"
                        "- 請聯絡 Buildway Tech (HK) Limited 安排人工評估\n"
                        "- 如屬緊急安全事項，請即時通知現場安全主任\n\n"
                        "## 需要人工確認事項\n\n"
                        "- 本次分析需由合資格專業人士親身評估確認"
                    )
                else:
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

                # 儲存結果
                from utils.risk_classifier import classify_risk
                risk_level = classify_risk(selected_type, question, analysis_result)

                st.session_state["last_analysis"] = {
                    "analysis_type": selected_type,
                    "analysis_display_name": ANALYSIS_DISPLAY[selected_type][1],
                    "question": question,
                    "analysis_result": analysis_result,
                    "file_description": file_description,
                    "file_name": file_name,
                    "professionals": professionals,
                    "project_ref": project_ref,
                    "risk_level": risk_level,
                }

            except ImportError:
                st.error("❌ 分析服務暫時未能使用。請聯絡 Buildway Tech 取得協助。")
                st.stop()
            except Exception as e:
                st.error("❌ 分析過程中發生錯誤。請稍後再試或聯絡 Buildway Tech。")
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
