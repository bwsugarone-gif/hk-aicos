"""
pages/4_About.py
HK-AICOS Phase 2.0 - 關於 Buildway Tech（客戶版）

Buildway Tech (HK) Limited
"""

import streamlit as st
from pathlib import Path
import sys
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.lang import ABOUT, NAV, BRAND

st.set_page_config(
    page_title="關於 Buildway Tech | HK-AICOS",
    page_icon="ℹ️",
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
    .info-card {
        background: white; border-radius: 10px; padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(26,58,92,0.08); margin-bottom: 1.2rem;
        border-top: 4px solid #c9a84c;
    }
    .info-card h3 { color: #1a3a5c; font-size: 1.1rem; margin-bottom: 0.8rem; }
    .info-card p, .info-card li { color: #444; font-size: 0.95rem; line-height: 1.7; }
    .contact-item {
        background: #f4f6f9; border-radius: 8px; padding: 0.8rem 1.2rem;
        margin-bottom: 0.5rem; font-size: 0.95rem; color: #333;
    }
    .phase-badge {
        display: inline-block; background: #1a3a5c; color: white;
        padding: 0.3rem 0.8rem; border-radius: 20px; font-size: 0.8rem;
        font-weight: 600; margin-right: 0.5rem;
    }
    .phase-badge-gold {
        display: inline-block; background: #c9a84c; color: #1a3a5c;
        padding: 0.3rem 0.8rem; border-radius: 20px; font-size: 0.8rem;
        font-weight: 600; margin-right: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

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

st.markdown("""
<div class="page-header">
    <h2>ℹ️ 關於 Buildway Tech</h2>
    <p>了解 HK-AICOS 系統及 Buildway Tech (HK) Limited。</p>
</div>
""", unsafe_allow_html=True)

# ── 公司介紹 ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="info-card">
    <h3>🏗️ Buildway Tech (HK) Limited</h3>
    <p>
    Buildway Tech (HK) Limited 專注為香港建築業提供 AI 科技解決方案。
    我們深明香港工程公司面對的挑戰：文件繁多、法規複雜、安全要求嚴格、報告製作耗時。
    </p>
    <p>
    HK-AICOS（Hong Kong AI Construction Operating System）是我們的旗艦產品，
    專為香港建築工程而設計，結合先進 AI 技術與香港本地工程知識，
    協助工程公司提升效率、降低風險。
    </p>
</div>
""", unsafe_allow_html=True)

# ── 系統功能 ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="info-card">
    <h3>🛠️ HK-AICOS 系統功能</h3>
    <ul>
        <li>📸 工地相片安全分析</li>
        <li>⚖️ 香港法規合規初步檢查</li>
        <li>📐 圖紙及工程文件分析</li>
        <li>🏗️ 臨時設施位置風險評估</li>
        <li>📋 PM 工程綜合分析</li>
        <li>💰 成本及工期影響評估</li>
        <li>📄 專業 PDF 報告生成</li>
    </ul>
</div>
""", unsafe_allow_html=True)

# ── 重要聲明 ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="info-card">
    <h3>⚠️ 重要免責聲明</h3>
    <p>
    本系統為 AI 輔助工程分析工具，所有分析結果僅供初步參考及內部評估用途。
    </p>
    <p>
    所有涉及以下範疇之事項，必須由香港合資格專業人士最終確認：
    </p>
    <ul>
        <li>結構安全及結構計算</li>
        <li>消防安全系統</li>
        <li>電力及機電工程</li>
        <li>水務及排水工程</li>
        <li>公共道路及掘路工程</li>
        <li>高風險施工工序</li>
        <li>合約及法律責任</li>
        <li>政府部門審批</li>
    </ul>
    <p>
    Buildway Tech (HK) Limited 不會取代認可人士（AP）、
    註冊結構工程師（RSE）、安全主任、
    註冊電業工程人員（REW）、持牌水喉匠、
    法律專業人士或相關政府部門之正式審批。
    </p>
</div>
""", unsafe_allow_html=True)

# ── 聯絡資料 ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="info-card">
    <h3>📞 聯絡我們</h3>
    <div class="contact-item">📧 Email：info@buildwaytech.hk</div>
    <div class="contact-item">🌐 網站：www.buildwaytech.hk</div>
    <div class="contact-item">📍 地址：香港</div>
    <p style="margin-top:1rem; font-size:0.88rem; color:#777;">
    如有任何技術問題或查詢，歡迎透過以上方式聯絡我們。
    </p>
</div>
""", unsafe_allow_html=True)

# ── 版本資訊 ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="info-card">
    <h3>📋 版本資訊</h3>
    <p>
        <span class="phase-badge-gold">Phase 2.0</span>
        HK-AICOS AI 工程分析助手（內測版）
    </p>
    <p style="font-size:0.88rem; color:#777; margin-top:0.8rem;">
    此為內測版本，功能持續更新中。如發現任何問題，請聯絡 Buildway Tech。
    </p>
</div>
""", unsafe_allow_html=True)

# Admin Mode 入口（隱藏，只有知道的人才能啟用）
ADMIN_MODE = os.environ.get("ADMIN_MODE", "false").lower() == "true"
if ADMIN_MODE:
    st.markdown("---")
    st.markdown("### 🔧 系統管理（Admin）")
    api_key_input = st.text_input(
        "設定 API Key（只在此 session 有效）",
        type="password",
        value=st.session_state.get("_api_key", ""),
        placeholder="sk-ant-...",
    )
    if api_key_input:
        st.session_state["_api_key"] = api_key_input
        st.success("✅ API Key 已設定（此 session 有效）")

st.markdown("""
<div style="text-align:center; color:#999; padding:1.5rem 0 0.5rem 0; font-size:0.82rem;">
    Buildway Tech (HK) Limited | HK-AICOS Phase 2.0
</div>
""", unsafe_allow_html=True)
