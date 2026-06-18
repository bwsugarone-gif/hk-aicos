# HK-AICOS / Buildway AICOS

**AI-powered construction site assistant for Hong Kong site follow-up, OCR, safety Q&A, official source search, and records tracking.**

HK-AICOS 是 Buildway Tech 為香港建造業工作流程而設的 AI 工程助理，協助整理地盤相片及文件、辨識文字、查詢安全與法規資料、搜尋香港官方來源，以及追蹤現場跟進記錄。

## 專案概覽（Project Overview）

本專案以實用、可追溯及審慎使用 AI 為原則，將文件／圖片分析、文字問答、知識搜尋、來源可信程度及地盤記錄集中於同一個 Streamlit 應用程式。

主要使用者包括項目管理人員、安全主任、地盤管理人員及需要整理工程資料的團隊。介面預設使用繁體中文，並提供中英文導覽切換。

## 目前狀態（Current Status）

- 當前穩定基線：**Phase 5.7F — Runtime + Navigation Hardening**
- 基線提交：`6e0157fcb9d3cfb30ea5cfcc7cfca0313007efdc`
- 主要應用程式：`streamlit-app/app.py`
- 建議執行環境：**Python 3.11.9**
- Tavily 即時搜尋已完成實際驗證；Brave Search 保留為第二優先供應商。
- 已完成 Streamlit 導覽、Widget Session State、測試流程及 tracked `__pycache__`／`.pyc` 清理。

> `HK-AICOS/phase-2/` 及部分較早文件保留 Phase 2.0 歷史設計內容。現行產品狀態及啟動方式以本 README 的 Phase 5.7F 基線為準。

## 主要功能（Key Features）

- 圖片 OCR、文字擷取及圖片後續跟進建議
- 上載相片、PDF、DOCX、XLSX 等工程文件進行分析
- **Ask AICOS** 文字問答：安全、法例、施工方法、物料及文件搜尋
- 本機工程知識搜尋（local knowledge search / RAG foundation）
- Tavily／Brave 真實網上搜尋供應商支援
- 香港官方來源可信程度分類及過濾
- 來源引用、可信標籤及「是否用於回答」標示
- 地盤記錄頁（Records）及本機 JSONL 記錄
- 跟進事項狀態、優先級、備註及變更歷史
- 繁體中文預設的中英文導覽
- Streamlit runtime／navigation hardening
- Python bytecode cache 已從 Git tracking 移除

## 技術棧（Tech Stack）

- **Python 3.11.9**（建議版本）
- **Streamlit**：Web UI 與多頁工作流程
- **Pytest**：單元及回歸測試
- **Tavily / Brave Search API**：即時網上搜尋
- **OCR / Vision providers**：圖片文字及工程內容理解
- **Local knowledge search**：本機工程文件檢索
- **JSON / JSONL**：本機記錄及跟進資料
- **ReportLab / pypdf**：PDF 報告及文件處理

## 本機設定（Local Setup）

在 Windows PowerShell 或 Command Prompt 執行：

```powershell
cd "C:\Users\user\Desktop\buildway AICOS"
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r streamlit-app\requirements.txt
pip install pytest
```

如 PowerShell 的執行政策阻止啟動虛擬環境，可使用：

```powershell
.venv\Scripts\Activate.ps1
```

## 環境變數（Environment Variables）

在專案根目錄建立本機 `.env`，只填入實際需要使用的供應商金鑰：

```dotenv
TAVILY_API_KEY=
BRAVE_SEARCH_API_KEY=
GEMINI_API_KEY=
DEEPSEEK_API_KEY=
ANTHROPIC_API_KEY=
```

- `.env` 只供本機使用，**切勿提交到 Git**。
- 不要把 API key 寫入程式碼、README、測試或截圖。
- 網上搜尋優先次序：**Tavily 第一，Brave 第二**。
- 如未設定網上搜尋 API key，Ask AICOS 會清楚顯示並使用 fallback mode；不會假裝已完成即時搜尋。

可參考 [`.env.example`](.env.example)，但請勿把真實金鑰寫入範例檔案。

## 執行應用程式（Running the App）

```powershell
cd "C:\Users\user\Desktop\buildway AICOS"
streamlit run streamlit-app\app.py
```

預設可於 `http://localhost:8501` 開啟。主要流程：

1. **上載分析**：上載地盤相片或工程文件。
2. **問 AICOS**：直接輸入安全、法例、施工或物料問題。
3. **地盤記錄**：查看及更新跟進狀態、優先級、備註和歷史。

## 測試（Testing）

Phase 5.6、5.7 及 runtime/navigation focused tests：

```powershell
python -m pytest streamlit-app/tests/test_phase56_hardening.py streamlit-app/tests/test_phase57_web_search.py streamlit-app/tests/test_phase57f_runtime_ui.py -q
```

完整測試：

```powershell
python -m pytest -q
```

測試不應呼叫真實搜尋 API；網絡請求必須使用 mock，並且不應產生可提交的 runtime/cache 檔案。

## 安全及法律聲明（Safety / Legal Disclaimer）

HK-AICOS 可協助建築安全、法例及規例資料研究，但輸出只供工作參考：

- 作出合規或法律決定前，必須核實香港官方來源的最新版本。
- 本系統及其回答不構成正式法律意見。
- 現場安全決定及控制措施仍須由合資格人士、安全主任及負責地盤管理人員作出及確認。
- 如發現即時危險，應先按現場安全程序停工、隔離風險及通知相關負責人。

## 階段歷史（Current Phase History）

| 階段 | 狀態 | 內容摘要 |
|---|---|---|
| Phase 2.0 | 歷史基礎 | Streamlit MVP、工程分析及文件骨架 |
| Phase 5.1–5.6 | 已完成 | OCR／Vision follow-up、Ask AICOS、本機知識搜尋、官方來源可信分類、引用強化、Records workflow |
| Phase 5.7A–E | 已完成 | Tavily／Brave provider layer、香港官方搜尋 query builder、Ask AICOS 網上搜尋整合、環境文件及測試 |
| Phase 5.7F | 當前基線 | Python 3.11 指引、tracked pycache 清理、Widget state 修正、雙語導覽及 runtime/UI hardening |

## GitHub About Metadata 建議

**Description**

> HK-AICOS — AI-powered construction site assistant for OCR, safety Q&A, official source search, and follow-up records.

**Topics**

```text
construction-ai
hong-kong
streamlit
ocr
site-safety
rag
tavily
aicos
buildway-tech
construction-management
```

---

Developed by **Buildway Tech (HK) Limited**.
