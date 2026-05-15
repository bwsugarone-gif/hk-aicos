"""
lang.py
HK-AICOS Phase 2.0 — 繁體中文 UI 字典

所有客戶前台顯示文字集中管理。
不要把中文字硬寫散落各 pages，統一從此處 import。

Buildway Tech (HK) Limited
"""

# ── 品牌 ──────────────────────────────────────────────────────────────────────
BRAND = {
    "company": "Buildway Tech (HK) Limited",
    "system": "HK-AICOS",
    "tagline": "AI 工程分析助手",
    "phase": "Phase 2.0",
    "footer": "Buildway Tech (HK) Limited | HK-AICOS Phase 2.0",
}

# ── 導航 ──────────────────────────────────────────────────────────────────────
NAV = {
    "home": "🏠 首頁",
    "upload": "📤 上載分析",
    "report": "📄 分析報告",
    "history": "🕘 歷史紀錄",
    "about": "ℹ️ 關於 Buildway Tech",
    "privacy": "🔒 所有資料安全處理",
}

# ── 首頁 ──────────────────────────────────────────────────────────────────────
HOME = {
    "hero_title": "Buildway Tech (HK) Limited",
    "hero_subtitle": "HK-AICOS AI 工程分析助手",
    "hero_desc": "上載工程相片、圖紙或 PDF，快速取得工程、安全及合規分析。",
    "cta_start": "📤 開始上載分析",
    "cta_start2": "📤 立即開始分析",
    "pain_title": "工程公司常見問題",
    "solution_title": "Buildway Tech 幫你",
    "features_title": "分析功能",
    "disclaimer_title": "重要聲明",
    "disclaimer_body": (
        "HK-AICOS 提供 AI 輔助工程分析，僅供初步參考及內部評估用途。"
        "所有涉及結構、安全、法規、消防、電力、水務、公共道路、掘路、高風險工序、合約或法律責任之事項，"
        "必須由香港合資格專業人士最終確認。"
    ),
}

# ── 上載分析頁 ────────────────────────────────────────────────────────────────
UPLOAD = {
    "page_title": "上載分析 | HK-AICOS",
    "page_icon": "📤",
    "header_title": "📤 上載分析",
    "header_desc": "上載工程相片、圖紙或 PDF，選擇分析類型，取得 AI 工程分析報告。",
    # 步驟
    "step1_label": "第一步",
    "step1_title": "📎 上載文件",
    "step1_hint": "支援 JPG、PNG、PDF（最大 20MB）",
    "step1_file_label": "選擇文件",
    "step2_label": "第二步",
    "step2_title": "🎯 選擇分析類型",
    "step3_label": "第三步",
    "step3_title": "❓ 描述你的問題",
    "step3_placeholder": "例如：呢張相有無不安全行為？呢個工人籠位置有無風險？",
    "step3_project_label": "工程編號（選填）",
    "step3_project_placeholder": "例如：BW-2025-001",
    "step4_label": "第四步",
    "step4_title": "🚀 生成分析報告",
    "btn_generate": "🚀 生成分析報告",
    # 錯誤 / 提示
    "err_no_question": "❌ 請先輸入你的問題。",
    "err_unsupported_file": "❌ 不支援此文件類型。請上載 JPG、PNG 或 PDF。",
    "err_service_unavailable": "⚠️ 系統暫時未能連接分析服務。請聯絡 Buildway Tech 取得協助。",
    "err_analysis_failed": "❌ 分析過程中發生錯誤。請稍後再試或聯絡 Buildway Tech。",
    "err_import": "❌ 分析服務暫時未能使用。請聯絡 Buildway Tech 取得協助。",
    "success_analysis": "✅ 分析完成！請前往「分析報告」查看結果。",
    "link_view_report": "📄 查看分析報告 →",
    "spinner_analysing": "正在分析中，請稍候...",
    "spinner_processing": "處理文件中...",
    "img_loaded": "✅ 圖片已載入：",
    "pdf_loaded": "✅ PDF 已載入：",
    "preview_label": "預覽文件內容",
    "selected_type_prefix": "已選擇：",
    # 無 API key 時的備用分析文字
    "fallback_analysis": (
        "## 工程分析\n\n"
        "分析服務暫時未能使用，請聯絡 Buildway Tech (HK) Limited 取得協助。\n\n"
        "## 建議跟進事項\n\n"
        "- 請聯絡 Buildway Tech (HK) Limited 安排人工評估\n"
        "- 如屬緊急安全事項，請即時通知現場安全主任\n\n"
        "## 需要人工確認事項\n\n"
        "- 本次分析需由合資格專業人士親身評估確認"
    ),
}

# ── 分析類型（UI 顯示用）─────────────────────────────────────────────────────
# key = 內部 analysis_type（與 agent_router.py 一致）
# value = (icon, 顯示名稱, 描述)
ANALYSIS_TYPES = {
    "安全風險分析": (
        "🦺",
        "工地安全分析",
        "分析工地相片，識別安全風險及不安全行為",
    ),
    "法規 / 合規檢查": (
        "⚖️",
        "法規合規檢查",
        "對照香港法規，初步檢查工程合規情況",
    ),
    "圖紙 / CAP / MIB 分析": (
        "📐",
        "圖紙 / 文件分析",
        "分析圖紙及工程文件，提取重點資料",
    ),
    "臨時設施位置分析": (
        "🏗️",
        "臨時設施分析",
        "分析天秤、工人籠、臨時平台等位置及風險",
    ),
    "PM 綜合分析": (
        "📋",
        "PM 工程分析",
        "綜合分析工程進度、資源及風險",
    ),
    "成本 / 工期影響分析": (
        "💰",
        "成本及工期分析",
        "初步評估 VO、成本超支及工期延誤影響",
    ),
}

# ── 報告頁 ────────────────────────────────────────────────────────────────────
REPORT = {
    "page_title": "分析報告 | HK-AICOS",
    "page_icon": "📄",
    "header_title": "📄 分析報告",
    "header_desc": "查看 AI 工程分析結果及下載 PDF 報告。",
    "no_result": "📭 暫無分析結果。請先前往「上載分析」頁面進行分析。",
    "link_go_upload": "📤 前往上載分析",
    "section_summary": "📋 問題摘要",
    "section_analysis": "📊 工程分析報告",
    "section_professionals": "👷 需要專業人士確認",
    "section_download": "📥 下載報告",
    "download_hint": "下載 PDF 報告，方便在手機或電腦查閱，或透過 WhatsApp 分享。",
    "btn_download": "📄 下載 PDF 報告",
    "err_pdf": "PDF 生成失敗，請稍後再試。",
    "label_type": "分析類型：",
    "label_project": "工程編號：",
    "label_file": "上載文件：",
    "label_risk": "風險級別：",
    "label_question": "問題：",
    "label_no_value": "未填寫",
    "label_no_file": "無",
    "professional_note": "此事項需要由以上專業人士確認後方可執行。",
    "action_label": "建議行動：",
    "response_label": "回應時間：",
    "link_reupload": "📤 重新上載分析",
    "disclaimer_title": "重要免責聲明",
    "disclaimer_body": (
        "本報告為 AI 輔助工程分析結果，只供初步參考及內部評估用途。\n\n"
        "所有涉及結構、安全、法規、消防、電力、水務、公共道路、掘路、高風險工序、合約或法律責任之事項，"
        "必須由香港合資格專業人士最終確認。\n\n"
        "Buildway Tech (HK) Limited 不會取代認可人士、註冊工程師、安全主任、"
        "註冊電業工程人員、持牌水喉匠、法律專業人士或相關政府部門之正式審批。"
    ),
    # 技術字眼過濾清單（不可出現在客戶報告）
    "banned_phrases": [
        "[示範模式", "[DEMO MODE", "No API Key", "API KEY", "Claude", "Anthropic",
        "This is what would be sent", "The AI would analyze", "backend", "prompt", "token",
    ],
    "banned_fallback": "分析結果暫時未能顯示。請重新進行分析或聯絡 Buildway Tech 取得協助。",
}

# ── 歷史紀錄頁 ────────────────────────────────────────────────────────────────
HISTORY = {
    "page_title": "歷史紀錄 | HK-AICOS",
    "page_icon": "🕘",
    "header_title": "🕘 歷史紀錄",
    "header_desc": "查閱過往分析記錄及下載報告。",
    "section_recent": "📋 最近一次分析",
    "section_saved": "📁 已儲存報告",
    "no_history": "📭 暫無分析記錄。請先前往「上載分析」頁面進行分析。",
    "no_saved": "📭 暫無已儲存報告。",
    "found_reports": "共找到",
    "found_reports_unit": "份報告：",
    "link_view_report": "📄 查看分析報告",
    "btn_download": "📄 下載 PDF 報告",
    "btn_download_short": "下載",
    "err_pdf": "PDF 生成失敗，請稍後再試。",
    "label_project": "工程編號：",
    "label_file": "文件：",
    "label_risk": "風險：",
    "label_no_value": "未填寫",
    "label_no_file": "無",
}

# ── 關於頁 ────────────────────────────────────────────────────────────────────
ABOUT = {
    "page_title": "關於 Buildway Tech | HK-AICOS",
    "page_icon": "ℹ️",
    "header_title": "ℹ️ 關於 Buildway Tech",
    "header_desc": "了解 HK-AICOS 系統及 Buildway Tech (HK) Limited。",
    "section_company": "🏗️ Buildway Tech (HK) Limited",
    "section_features": "🛠️ HK-AICOS 系統功能",
    "section_disclaimer": "⚠️ 重要免責聲明",
    "section_contact": "📞 聯絡我們",
    "section_version": "📋 版本資訊",
    "admin_section": "🔧 系統管理",
    "admin_key_label": "設定服務金鑰（只在此 session 有效）",
    "admin_key_success": "✅ 服務金鑰已設定（此 session 有效）",
}

# ── Agent Selector UI ────────────────────────────────────────────────────────
# Mirrors AGENT_DEFINITIONS in agent_router.py — UI labels and descriptions only
AGENTS = {
    "safety": {
        "icon": "🦺",
        "label": "Safety Agent",
        "sublabel": "安全 Agent",
        "desc": "分析工地安全風險、PPE 使用、高危工序及即時危險",
    },
    "pm": {
        "icon": "📋",
        "label": "PM Agent",
        "sublabel": "項目管理 Agent",
        "desc": "綜合分析工程進度、資源安排、責任分工及決策支援",
    },
    "qs": {
        "icon": "💰",
        "label": "QS Agent",
        "sublabel": "工料測量 Agent",
        "desc": "評估成本影響、工期延誤、VO 可能性及合約索償風險",
    },
    "legal": {
        "icon": "⚖️",
        "label": "Legal Agent",
        "sublabel": "法規合規 Agent",
        "desc": "對照香港法規，檢查政府部門要求、牌照、通報及合規風險",
    },
    "risk": {
        "icon": "⚠️",
        "label": "Risk Agent",
        "sublabel": "風險評估 Agent",
        "desc": "綜合評估項目整體風險、責任範圍及優先處理事項",
    },
}

AGENT_ORDER = ["safety", "pm", "qs", "legal", "risk"]

# ── 風險級別 ──────────────────────────────────────────────────────────────────
RISK = {
    "low": "低風險",
    "medium": "中風險",
    "high": "高風險",
    "action_prefix": "建議行動：",
    "response_prefix": "回應時間：",
}

# ── 系統狀態 ──────────────────────────────────────────────────────────────────
SYSTEM = {
    "status_title": "系統狀態",
    "status_ok": "服務正常",
    "status_degraded": "服務受限",
    "status_offline": "服務暫停",
    "knowledge_base": "知識庫",
    "knowledge_base_ok": "已載入",
    "knowledge_base_empty": "未載入",
}
