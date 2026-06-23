# HK-AICOS / Buildway AICOS

**AI-powered construction site assistant for Hong Kong site photo/document analysis, safety Q&A, memory, follow-up tracking, RAG knowledge search, and drawing/CAD-BIM handoff.**

HK-AICOS 是 Buildway Tech 為香港建造業而設的 AI 工程助理：分析地盤相片及文件、回答安全與法規問題、保存項目記憶（Memory）、追蹤跟進事項（Follow-up）、提供知識搜尋（RAG），並支援圖則分析與 CAD／BIM 交接（Drawing / CAD-BIM Handoff）。介面預設繁體中文，並標示常用 English 技術名稱。

## 目前狀態（Current Status）

- 當前 dev 基線：**Phase 5.10 — Drawing Analysis + CAD/BIM Handoff Core**
- 最新 dev 提交（Latest dev commit）：`95fcaed2e51af52c8d0d5627068ab06d86bee30c`
- `main` 分支可能落後於 `dev`，直至 Cloud smoke test 通過後才合併。
- 主要應用程式入口（Primary app entry）：`streamlit-app/app.py`
- 建議 Python 版本（Recommended Python）：**3.11.9**

## 功能總覽（Feature Overview）

現行模組（current modules）：

| 模組 | 頁面 | 說明 |
|---|---|---|
| AICOS Workspace | `/AICOS_Workspace` | 統一工作台，整合分析、問答與記錄入口 |
| Upload analysis | `/Upload` | 上載地盤相片或工程文件進行分析 |
| Ask AICOS | `/Ask_AICOS` | 安全、法例、施工方法文字問答 |
| Records | `/Records` | Memory／Follow-up／Knowledge／Drawing 記錄檢視 |
| Reports | `/Report` | 分析結果整理與報告輸出 |
| Project Dashboard | `/Project_Dashboard` | 項目概況與進度視圖 |
| Risk Center | `/Risk_Center` | 風險彙整與檢視 |
| Action Tracking | `/Action_Tracker` | 行動項目／跟進事項追蹤 |
| Drawing Analysis | `/Drawing_Analysis` | 圖則／PDF 分析與 CAD／BIM 交接 |

## 階段摘要（Phase Summary）

- **Phase 5.7**：Runtime／navigation hardening、OCR/Vision evidence gate、answer formatter、安全的 upload 分析（safe upload analysis）。
- **Phase 5.8**：Project Memory、Knowledge Pack、Follow-up Tracker、Records management。
- **Phase 5.9**：Provider health、Gemini Vision、RAG foundation、intent router、熱工序／高空工作答案路由（hot-work / high-work answer routing）。
- **Phase 5.10**：圖則／PDF 分析、標題欄擷取（title block extraction）、圖則分類（drawing classification）、問題擷取（issue extraction）、CAD／BIM 交接項目（handoff items）、Drawing Analysis 頁面、Ask AICOS 圖則內容情境（drawing context）。

## 核心能力（Core Capabilities）

### A. 地盤相片分析（Site photo analysis）

- OCR／文字偵測（text detection）
- 已設定供應商時使用 AI Vision
- 未設定時提供人手描述 fallback（manual description fallback）
- 證據追蹤（evidence trace）
- 風險等級與跟進事項生成（risk level and follow-up generation）

### B. Ask AICOS

- 安全問答（safety Q&A）
- 意圖路由（intent routing）
- 最近相片情境（recent image context）
- 圖則分析情境（drawing analysis context）
- 記憶／跟進／RAG 情境（memory / follow-up / RAG context）
- 正常 UI 不會外露供應商名稱或 API key（avoids exposing provider names / API keys in normal UI）

### C. 記憶／知識／跟進（Memory / Knowledge / Follow-up）

- Project Memory
- Knowledge Pack
- RAG index foundation
- Follow-up Tracker
- Records tabs

### D. 圖則分析／CAD-BIM 交接（Drawing Analysis / CAD-BIM Handoff）

- PDF／圖片圖則上載（PDF/image drawing upload）
- 標題欄擷取（title block extraction）
- 盡可能偵測圖號／標題／修訂／比例（sheet number / title / revision / scale detection where possible）
- 圖則頁面分類（drawing page classification）
- 專業範疇偵測（discipline detection）
- 問題／缺漏資訊擷取（issue / missing-info extraction）
- CAD／BIM 交接項目（CAD/BIM handoff items）
- Ask AICOS 可引用最近的圖則分析（reference recent drawing analysis）

## 執行期資料警告（Runtime Data Warning）

下列 runtime JSONL 檔案由應用程式在執行期產生，已被 `.gitignore` 忽略（`streamlit-app/data/*.jsonl`），在 Streamlit Cloud 上可能屬臨時性、隨時被清除：

- `streamlit-app/data/aicos_memory.jsonl`
- `streamlit-app/data/followups.jsonl`
- `streamlit-app/data/knowledge_index.jsonl`
- `streamlit-app/data/rag_index.jsonl`
- `streamlit-app/data/drawing_analysis.jsonl`
- `streamlit-app/data/drawing_pages.jsonl`

> 這些檔案 **不會被提交（not committed）**，亦 **不是生產級持久化儲存（not production persistence）**。請勿依賴它們作長期資料保存。

## 環境變數與機密（Environment / Secrets）

需要或可選的機密（required or optional secrets）：

```dotenv
GEMINI_API_KEY=
DEEPSEEK_API_KEY=
TAVILY_API_KEY=
AICOS_ADMIN_DIAGNOSTICS=true
```

- `GEMINI_API_KEY`、`DEEPSEEK_API_KEY`、`TAVILY_API_KEY`：供應商金鑰，按需要設定。
- `AICOS_ADMIN_DIAGNOSTICS=true`：開啟管理員診斷（admin diagnostics）。
- 本機 `.env` **不會被提交（local .env is not committed）**。
- Streamlit Cloud 的 **Secrets 必須另行設定（configured separately）**，不會自動沿用本機 `.env`。
- 正常 UI **不得顯示任何機密值（normal UI must not display secret values）**。

## 本機開發（Local Development）

### Windows

```powershell
cd "C:\Users\user\Desktop\buildway AICOS"
python -m venv .venv
.venv\Scripts\activate
pip install -r streamlit-app\requirements.txt
pip install pytest
streamlit run streamlit-app\app.py
```

### Mac

```bash
cd ~/Desktop/"buildway AICOS"
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r streamlit-app/requirements.txt
pip install pytest
streamlit run streamlit-app/app.py
```

預設可於 `http://localhost:8501` 開啟。

## 開發流程（Development Workflow）

- 在 `dev` 分支上開發（work on dev）。
- 在 Cloud smoke test 通過前 **不要合併到 `main`**（do not merge to main until Cloud smoke test passes）。
- 不要提交 runtime JSONL、uploads、`.env`、cache、截圖（screenshots）、debug reports。
- 開發期間使用聚焦測試（focused tests），release gate 前才跑完整測試套件（full suite before release gates）。

聚焦測試示例（例如 Phase 5.10 圖則分析）：

```powershell
python -m pytest streamlit-app/tests/test_phase510_drawing.py -q
```

完整測試（full suite）：

```powershell
python -m pytest -q
```

測試不應呼叫真實外部 API；網絡請求須使用 mock，並且不應產生可提交的 runtime/cache 檔案。

## 目前 Cloud Smoke Checklist

部署到 Streamlit Cloud 後，逐項確認：

- [ ] `/AICOS_Workspace` 可開啟
- [ ] `/Upload` 可開啟
- [ ] `/Ask_AICOS` 能回答：
  - [ ] 熱工序定義？
  - [ ] 高空工作定義？
  - [ ] 這張相有咩問題？
- [ ] `/Records` 顯示 memory／follow-up／knowledge／drawing 記錄
- [ ] `/Drawing_Analysis` 可開啟
- [ ] 上載 PDF／圖片圖則後產生：
  - [ ] 文件概覽（document overview）
  - [ ] 頁面摘要（page summary）
  - [ ] 問題／缺漏資訊（issues / missing information）
  - [ ] CAD／BIM 交接清單（CAD/BIM handoff list）
- [ ] 正常 UI **不會** 顯示 API keys、原始供應商錯誤（raw provider errors）、Traceback、原始 JSON 或檔案系統路徑（filesystem paths）

## 尚未生產／延後項目（Not Yet Production / Deferred）

- Google Drive live OAuth
- Supabase persistence
- 使用者／租戶／項目權限（user / tenant / project permissions）
- 向量資料庫／嵌入（vector DB / embeddings）
- 掃描圖則的完整 PDF 文字擷取（full PDF text extraction for scanned drawings）
- 完整 CAD 製圖（full CAD authoring）
- BIM 模型生成（BIM model generation）
- 最終 PDF 報告匯出打磨（final PDF report export polish）

## 安全及法律聲明（Safety / Legal Disclaimer）

HK-AICOS 可協助建築安全、法例及規例資料研究，但輸出只供工作參考：

- 作出合規或法律決定前，必須核實香港官方來源的最新版本。
- 本系統及其回答不構成正式法律意見。
- 現場安全決定及控制措施仍須由合資格人士、安全主任及負責地盤管理人員作出及確認。
- 如發現即時危險，應先按現場安全程序停工、隔離風險及通知相關負責人。

---

Developed by **Buildway Tech (HK) Limited**.
