"""
app.py
HK-AICOS Phase 2.0 - 品牌首頁（客戶版）

Buildway Tech (HK) Limited
"""

import streamlit as st
from pathlib import Path
import sys
import os

sys.path.insert(0, str(Path(__file__).parent))

# ── 載入 .env（如存在）──────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

# Admin mode — 預設隱藏，只有設定環境變數才顯示
ADMIN_MODE = os.environ.get("ADMIN_MODE", "false").lower() == "true"

st.set_page_config(
    page_title="HK-AICOS | Buildway Tech",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 全域 CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* 隱藏 Streamlit 預設選單 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* 主色調 */
    :root {
        --primary: #1a3a5c;
        --accent: #c9a84c;
        --light-bg: #f4f6f9;
    }

    /* Sidebar 樣式 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a3a5c 0%, #0f2942 100%);
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    [data-testid="stSidebar"] .stMarkdown a {
        color: #c9a84c !important;
    }

    /* 主按鈕 */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #c9a84c 0%, #a8873a 100%);
        color: #1a3a5c;
        font-weight: 700;
        font-size: 1.15rem;
        padding: 0.85rem 2.5rem;
        border: none;
        border-radius: 8px;
        width: 100%;
        letter-spacing: 0.03em;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #a8873a 0%, #8a6e2e 100%);
    }

    /* 次要按鈕 */
    .stButton > button[kind="secondary"] {
        background: transparent;
        color: #1a3a5c;
        border: 2px solid #1a3a5c;
        font-weight: 600;
        border-radius: 8px;
        width: 100%;
    }

    /* 卡片 */
    .feature-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 12px rgba(26,58,92,0.08);
        border-top: 4px solid #c9a84c;
        height: 100%;
        margin-bottom: 1rem;
    }
    .feature-card h4 {
        color: #1a3a5c;
        font-size: 1.05rem;
        margin-bottom: 0.5rem;
    }
    .feature-card p {
        color: #555;
        font-size: 0.95rem;
        margin: 0;
    }

    /* 痛點卡片 */
    .pain-card {
        background: #fff8f0;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        border-left: 4px solid #fd7e14;
        margin-bottom: 0.8rem;
        color: #555;
        font-size: 0.95rem;
    }

    /* 解決方案卡片 */
    .solution-card {
        background: #f0f7ff;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        border-left: 4px solid #1a3a5c;
        margin-bottom: 0.8rem;
        color: #333;
        font-size: 0.95rem;
    }

    /* Hero 區域 */
    .hero-section {
        background: linear-gradient(135deg, #1a3a5c 0%, #2d5a8e 100%);
        color: white;
        padding: 3rem 2rem;
        border-radius: 16px;
        text-align: center;
        margin-bottom: 2rem;
    }
    .hero-section h1 {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        letter-spacing: 0.02em;
    }
    .hero-section h2 {
        font-size: 1.5rem;
        font-weight: 600;
        color: #c9a84c;
        margin-bottom: 1rem;
    }
    .hero-section p {
        font-size: 1.05rem;
        opacity: 0.92;
        max-width: 600px;
        margin: 0 auto;
    }

    /* 手機優化 */
    @media (max-width: 768px) {
        .hero-section h1 { font-size: 1.5rem; }
        .hero-section h2 { font-size: 1.2rem; }
        .hero-section p { font-size: 0.95rem; }
        .hero-section { padding: 2rem 1rem; }
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 1rem 0 0.5rem 0;">
        <div style="font-size:2.5rem;">🏗️</div>
        <div style="font-size:1.1rem; font-weight:700; color:white;">Buildway Tech</div>
        <div style="font-size:0.85rem; color:#c9a84c;">(HK) Limited</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.8rem; color:#aac4e0; text-align:center;">
        HK-AICOS AI 工程分析助手
    </div>
    """, unsafe_allow_html=True)
    st.markdown("")

    st.page_link("app.py", label="🏠 首頁", icon=None)
    st.page_link("pages/1_Upload.py", label="📤 上載分析", icon=None)
    st.page_link("pages/2_Report.py", label="📄 分析報告", icon=None)
    st.page_link("pages/3_History.py", label="🕘 歷史紀錄", icon=None)
    st.page_link("pages/4_About.py", label="ℹ️ 關於 Buildway Tech", icon=None)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.78rem; color:#aac4e0; padding: 0.5rem 0;">
        🔒 所有資料安全處理<br/>
        不會與第三方分享
    </div>
    """, unsafe_allow_html=True)

# ── Hero Section ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <h1>🏗️ Buildway Tech (HK) Limited</h1>
    <h2>HK-AICOS AI 工程分析助手</h2>
    <p>上載工程相片、圖紙或 PDF，快速取得工程、安全及合規分析。</p>
</div>
""", unsafe_allow_html=True)

# ── CTA Button ───────────────────────────────────────────────────────────────
col_l, col_c, col_r = st.columns([1, 2, 1])
with col_c:
    if st.button("📤 開始上載分析", type="primary", use_container_width=True):
        st.switch_page("pages/1_Upload.py")

st.markdown("<br/>", unsafe_allow_html=True)

# ── 痛點 vs 解決方案 ──────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("### 😓 工程公司常見問題")
    pains = [
        ("📁", "文件太多，難以整理及追蹤"),
        ("⏱️", "工程進度難以即時掌握"),
        ("⚠️", "安全風險容易遺漏，事後才發現"),
        ("📋", "法規要求繁多，難以逐項檢查"),
        ("📝", "報告製作花費大量人手時間"),
        ("💰", "成本超支及工期延誤難以預警"),
    ]
    for icon, text in pains:
        st.markdown(f'<div class="pain-card">{icon} {text}</div>', unsafe_allow_html=True)

with col_right:
    st.markdown("### ✅ Buildway Tech 幫你")
    solutions = [
        ("🔍", "快速分析工程相片，識別潛在問題"),
        ("🦺", "初步檢查安全風險，提早預警"),
        ("📐", "整理圖紙及 PDF 資料，提取重點"),
        ("⚖️", "提醒香港法規及合規風險"),
        ("📄", "自動生成手機可閱讀 PDF 報告"),
        ("📊", "成本及工期影響初步評估"),
    ]
    for icon, text in solutions:
        st.markdown(f'<div class="solution-card">{icon} {text}</div>', unsafe_allow_html=True)

st.markdown("---")

# ── 功能介紹 ──────────────────────────────────────────────────────────────────
st.markdown("### 🛠️ 分析功能")

features = [
    ("🦺", "工地安全分析", "分析工地相片，識別不安全行為、PPE 使用情況及高風險工序。"),
    ("⚖️", "法規合規檢查", "對照香港政府部門要求，初步檢查工程合規情況。"),
    ("📐", "圖紙分析", "分析圖紙、CAP 及 MIB，提取重點資料及潛在問題。"),
    ("🏗️", "臨時設施分析", "分析天秤、工人籠、臨時平台等位置及風險。"),
    ("📋", "PM 工程分析", "綜合分析工程進度、資源及風險，支援決策。"),
    ("💰", "成本及工期分析", "初步評估 VO、成本超支及工期延誤影響。"),
]

cols = st.columns(3)
for i, (icon, title, desc) in enumerate(features):
    with cols[i % 3]:
        st.markdown(
            f'<div class="feature-card"><h4>{icon} {title}</h4><p>{desc}</p></div>',
            unsafe_allow_html=True,
        )

st.markdown("<br/>", unsafe_allow_html=True)

# ── 第二個 CTA ────────────────────────────────────────────────────────────────
col_l2, col_c2, col_r2 = st.columns([1, 2, 1])
with col_c2:
    if st.button("📤 立即開始分析", type="primary", use_container_width=True, key="cta2"):
        st.switch_page("pages/1_Upload.py")

st.markdown("---")

# ── 免責聲明 ──────────────────────────────────────────────────────────────────
st.markdown("""
<div style="
    background:#f8f9fa;
    border-radius:8px;
    padding:1rem 1.5rem;
    border-left:4px solid #6c757d;
    font-size:0.85rem;
    color:#555;
">
<strong>⚠️ 重要聲明</strong><br/>
HK-AICOS 提供 AI 輔助工程分析，僅供初步參考及內部評估用途。
所有涉及結構、安全、法規、消防、電力、水務、公共道路、掘路、高風險工序、合約或法律責任之事項，
必須由香港合資格專業人士最終確認。
</div>
""", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; color:#999; padding:2rem 0 1rem 0; font-size:0.85rem;">
    <strong>Buildway Tech (HK) Limited</strong><br/>
    HK-AICOS Phase 2.0 | 專為香港建築業設計
</div>
""", unsafe_allow_html=True)
