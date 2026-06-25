"""發佈就緒 / 試用 — 釋出閘門、雲端冒煙清單及客戶試用工作流程（Phase 6.5 / 6.6）。"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from utils.demo_project import is_demo_seeded, seed_demo_data
from utils.logo_helper import sidebar_logo
from utils.navigation import render_navigation_links
from utils.release_gate import CHECKED_SECRETS, evaluate_release_gate
from utils.trial_mode import (
    DEMO_PROJECT_REF,
    build_trial_checklist,
    trial_flow_cards,
    trial_warnings,
)
from utils.ui_components import compact_link_row, page_header, render_product_footer


st.set_page_config(page_title="發佈就緒 / 試用", page_icon="🚦", layout="wide")

_STATUS_ICON = {"pass": "✅", "warn": "🟡", "fail": "❌"}

with st.sidebar:
    sidebar_logo()
    st.markdown("---")
    render_navigation_links()

page_header("發佈就緒 / 試用", "釋出前自我檢查、雲端冒煙測試清單，以及客戶試用工作流程。", "🚦")
compact_link_row((
    ("pages/0_AICOS_Workspace.py", "🏗️ AICOS 工作台"),
    ("pages/11_Records.py", "🗂️ 記錄"),
    ("pages/13_Knowledge_Ingestion.py", "📚 知識匯入"),
))

if st.session_state.get("readiness_message"):
    st.success(st.session_state.pop("readiness_message"))

report = evaluate_release_gate()

gate_tab, smoke_tab, trial_tab = st.tabs(["釋出就緒", "冒煙測試清單", "客戶試用工作流程"])


with gate_tab:
    cols = st.columns(3)
    cols[0].metric("就緒分數", f"{report.score}/100")
    cols[1].metric("阻塞項目", len(report.blocking_issues))
    cols[2].metric("提示", len(report.warnings))
    if report.ready:
        st.success("核心頁面與功能模組已就緒，可進行雲端冒煙測試及試用。")
    else:
        st.error("仍有阻塞項目，請先修復再進行雲端冒煙測試。")

    st.markdown("#### 檢查項目")
    for check in report.checks:
        icon = _STATUS_ICON.get(check.status, "•")
        st.caption(f"{icon} {check.label}　—　{check.detail}")

    if report.blocking_issues:
        st.markdown("#### 阻塞項目")
        for item in report.blocking_issues:
            st.markdown(f"- ❌ {item}")

    if report.warnings:
        st.markdown("#### 提示")
        for item in report.warnings:
            st.markdown(f"- 🟡 {item}")

    st.markdown("#### 下一步建議")
    for item in report.next_actions:
        st.markdown(f"- {item}")

    with st.expander("管理員診斷（只顯示已設定 / 未設定，不顯示任何金鑰值）", expanded=False):
        st.caption("以下只反映設定狀態，不會顯示任何金鑰、供應商錯誤或本機路徑。")
        for name, label in CHECKED_SECRETS:
            configured = report.secret_status.get(name, False)
            st.caption(f"{'✅ 已設定' if configured else '⚪ 未設定'}　{label}（{name}）")


with smoke_tab:
    st.caption("依序完成下列雲端冒煙測試，確認核心試用流程可用。")
    for index, step in enumerate(report.smoke_test_flow, start=1):
        st.markdown(f"{index}. {step}")
    st.info("完成全部步驟後，可於「客戶試用工作流程」分頁帶客戶走一次。")


with trial_tab:
    for warning in trial_warnings():
        st.warning(warning)

    st.markdown("#### 試用流程")
    cards = trial_flow_cards()
    grid = st.columns(2)
    for index, card in enumerate(cards):
        with grid[index % 2].container(border=True):
            st.markdown(f"**{card.order}. {card.title}**")
            st.caption(card.description)
            st.page_link(card.page, label=card.page_label)

    st.markdown("#### 試用進度檢查")
    checklist = build_trial_checklist()
    done = sum(1 for item in checklist if item.done)
    st.progress(done / len(checklist) if checklist else 0.0)
    for item in checklist:
        st.caption(f"{'✅' if item.done else '⬜'} {item.label}")

    st.markdown("#### Demo 試用資料")
    st.caption(f"可建立示範項目「{DEMO_PROJECT_REF}」的安全樣本資料，方便試用 Records 及 Ask AICOS。")
    seeded = is_demo_seeded()
    if seeded:
        st.success("Demo 試用資料已建立；可於「記錄」搜尋或向 AICOS 提問。")
    if st.button("建立 Demo 試用資料", type="primary", disabled=seeded):
        result = seed_demo_data()
        if result.already_seeded:
            st.session_state["readiness_message"] = "Demo 試用資料已存在，未重複建立。"
        else:
            st.session_state["readiness_message"] = "已建立 Demo 試用資料（記憶、跟進、圖紙、交接、檔案、知識）。"
        st.rerun()
    compact_link_row((
        ("pages/11_Records.py", "🗂️ 前往記錄搜尋"),
        ("pages/10_Ask_AICOS.py", "💬 問 AICOS"),
    ))


render_product_footer()
