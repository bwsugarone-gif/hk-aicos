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
from utils.risk_classifier import classify_risk, get_risk_info
from utils.file_loader import process_uploaded_file, is_allowed_file, get_file_type_label
from utils.rag_reader import build_rag_context
from utils.lang import UPLOAD, ANALYSIS_TYPES, AGENTS, AGENT_ORDER as AGENT_ORDER_LANG, NAV, BRAND
from utils.logo_helper import sidebar_logo
from utils.session_memory import save_session, get_prior_context, make_session_id
from utils.report_generator import _department_mapping

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

        # Preview each file
        for i, (uf, fd) in enumerate(zip(valid_files, all_file_data)):
            if fd["type"] == "image":
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.image(uf, caption=uf.name, use_container_width=True)
                with col2:
                    st.success(f"✅ 圖片已載入：{uf.name}")
            elif fd["type"] == "pdf":
                st.success(f"✅ PDF 已載入：{uf.name}")
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
st.markdown("選擇參與分析的 Agent。每個 Agent 負責不同範疇，可多選。至少選擇一個。")

# Initialise default: PM, Safety and Engineering only
if "selected_agents" not in st.session_state:
    st.session_state["selected_agents"] = list(DEFAULT_SELECTED_AGENTS)

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

# Update session state (don't allow empty selection)
if new_selection:
    st.session_state["selected_agents"] = new_selection
else:
    # Keep previous selection if user deselects everything
    st.warning("⚠️ 請至少選擇一個 Agent。")

# Show selected agent badges
selected_agents = st.session_state["selected_agents"]
if len(selected_agents) > 5:
    st.warning("選擇太多 Agent 會令報告過長，建議每次選 2 至 5 個。")

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

        # ── Project continuity: inject prior session context ──────────────────
        prior_context = get_prior_context(project_ref.strip()) if project_ref.strip() else ""
        prior_prefix = (
            f"\n\n【項目歷史分析記錄】\n{prior_context}\n\n【本次分析】\n"
            if prior_context else ""
        )

        full_prompt = build_prompt_from_agents(
            selected_agent_ids=selected_agent_ids,
            question=question,
            file_description=(
                prior_prefix
                + file_description
                + ("\n\n文件內容:\n" + file_content if file_content else "")
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

                # Classify risk and store result
                risk_level = classify_risk(selected_type, question, analysis_result)

                # Derive departments for session record
                _dept_text = "\n".join([selected_type, question, analysis_result])
                _departments = _department_mapping(_dept_text)

                # Collect file metadata for session record
                _all_fd = st.session_state.get("current_all_file_data", [])
                _valid_fs = st.session_state.get("current_valid_files", [])
                _file_names = [uf.name for uf in _valid_fs] if _valid_fs else (
                    [file_name] if file_name else []
                )
                _file_types = [fd.get("type", "unknown") for fd in _all_fd] if _all_fd else []

                # Save session to JSON memory
                try:
                    save_session(
                        project_ref=project_ref,
                        file_names=_file_names,
                        file_types=_file_types,
                        selected_agents=selected_agent_ids,
                        risk_level=risk_level,
                        departments=_departments,
                        analysis_result=analysis_result,
                        analysis_type=ANALYSIS_DISPLAY[selected_type][1],
                        question=question,
                        session_id=current_session_id,
                    )
                except Exception:
                    pass  # Never crash the main flow due to session save failure

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
                    "selected_agents": selected_agent_ids,
                    "session_id": current_session_id,
                }

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
