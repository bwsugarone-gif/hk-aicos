# HK-AICOS / Buildway AICOS

**AI-powered construction site assistant for Hong Kong site photo/document analysis, safety Q&A, memory, follow-up tracking, RAG knowledge search, and drawing/CAD-BIM handoff.**

HK-AICOS 是 Buildway Tech 為香港建造業而設的 AI 工程助理：分析地盤相片及文件、回答安全與法規問題、保存項目記憶（Memory）、追蹤跟進事項（Follow-up）、提供知識搜尋（RAG），並支援圖則分析與 CAD／BIM 交接（Drawing / CAD-BIM Handoff）。介面預設繁體中文，並標示常用 English 技術名稱。

## 目前狀態（Current Status）

- 當前 dev 基線：**Phase 6.6 — Client Trial Mode / Demo Workflow**（建基於 Phase 6.1 / 6.3 / 6.4 / 6.5）
- Phase 6.6 基線提交（baseline commit）：`39e8ac44d0c876a5d20fd98ed5599f663ce96e06`
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
| Records | `/Records` | 全部記錄統一搜尋：Memory／Follow-up／Knowledge／RAG／Drawing／CAD-BIM／檔案登記 |
| Reports | `/Report` | 分析結果整理與報告輸出 |
| Project Dashboard | `/Project_Dashboard` | 項目概況與進度視圖 |
| Risk Center | `/Risk_Center` | 風險彙整與檢視 |
| Action Tracking | `/Action_Tracker` | 行動項目／跟進事項追蹤 |
| Drawing Analysis | `/Drawing_Analysis` | 圖則／PDF 分析與 CAD／BIM 交接 |
| Knowledge Ingestion | `/Knowledge_Ingestion` | 上載 PDF／TXT／MD 文件，抽取文字並建立知識來源與 RAG 片段 |
| Release Readiness | `/Release_Readiness` | 發佈就緒檢查、雲端冒煙清單及客戶試用工作流程 |

## 階段摘要（Phase Summary）

- **Phase 5.7**：Runtime／navigation hardening、OCR/Vision evidence gate、answer formatter、安全的 upload 分析（safe upload analysis）。
- **Phase 5.8**：Project Memory、Knowledge Pack、Follow-up Tracker、Records management。
- **Phase 5.9**：Provider health、Gemini Vision、RAG foundation、intent router、熱工序／高空工作答案路由（hot-work / high-work answer routing）。
- **Phase 5.10**：圖則／PDF 分析、標題欄擷取（title block extraction）、圖則分類（drawing classification）、問題擷取（issue extraction）、CAD／BIM 交接項目（handoff items）、Drawing Analysis 頁面、Ask AICOS 圖則內容情境（drawing context）。
- **Phase 5.11**：圖紙分析實戰強化（Drawing Analysis Live Hardening）——更可靠的真實 PDF／圖片圖紙處理及安全頁數上限、更準確的標題欄擷取（EN／中文標籤、Drg/Dwg/Job No.、樓層）、更佳的圖紙頁面分類、更貼近實務的 CAD/BIM 交接用詞（負責團隊／所需成果／覆核人）、Records 圖紙與交接搜尋及狀態更新、Ask AICOS 圖紙查詢情境（未有分析時提示先上載圖紙）。
- **Phase 6.1**：上載檔案 metadata 層與檔案登記（File Registry），原檔儲存標示「本機暫存 / Drive-ready」，正常 UI 不顯示本機路徑。
- **Phase 6.3**：記錄統一搜尋（Records unified search），跨工程記憶／跟進／知識來源／RAG 片段／圖紙／CAD-BIM 交接／檔案登記。
- **Phase 6.4**：知識／PDF 匯入（Knowledge Ingestion）、頁碼級 RAG 片段持久化（RAG chunk persistence）、掃描 PDF 降級為 metadata-only，Ask AICOS 可引用文件知識。
- **Phase 6.5**：發佈就緒（Release Gate / Cloud QA / Admin Readiness）——就緒分數、阻塞項目、冒煙清單、金鑰只顯示已設定／未設定。
- **Phase 6.6**：客戶試用模式（Client Trial Mode / Demo Workflow）——試用流程卡、試用進度檢查、可重複建立的安全 Demo 試用資料（`AICOS-DEMO`）。

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

### E. 檔案登記／知識匯入／統一搜尋（File Registry / Knowledge Ingestion / Unified Search）

- 檔案登記（File Registry）：上載相片／圖紙／PDF／知識檔案的 metadata 層；原檔儲存標示「本機暫存 / Drive-ready」，正常 UI 不顯示本機路徑。
- 知識匯入（Knowledge Ingestion）：上載 PDF／TXT／MD／DOCX，抽取可選取文字並建立知識來源；掃描／無文字 PDF 降級為 metadata-only 並提示改用 OCR／可選取文字版本。
- RAG 片段（RAG chunks）：頁碼級切片並持久化於獨立 store，避免被知識索引重建覆蓋。
- 記錄統一搜尋（Records unified search）：跨 8 類記錄的本地、可決定性關鍵字搜尋（無 embeddings）。

### F. 發佈就緒／客戶試用（Release Readiness / Client Trial）

- 發佈就緒（Release Readiness）：核心頁面與功能模組就緒檢查、就緒分數、阻塞項目、雲端冒煙清單；金鑰只顯示已設定／未設定，永不顯示金鑰值。
- 客戶試用模式（Client Trial Mode）：未啟用登入／權限下的試用流程卡（A–G）、試用進度檢查及試用提示。
- Demo 試用資料：使用者按「建立 Demo 試用資料」才會建立示範項目 `AICOS-DEMO` 的安全樣本（可重複、不含真實機密資料）。
- Google Drive：已預留欄位與 hook（ready-to-connect），尚未啟用 live OAuth。

## 執行期資料警告（Runtime Data Warning）

下列 runtime JSONL 檔案由應用程式在執行期產生，已被 `.gitignore` 忽略（`streamlit-app/data/*.jsonl`），在 Streamlit Cloud 上可能屬臨時性、隨時被清除：

- `streamlit-app/data/aicos_memory.jsonl`
- `streamlit-app/data/followups.jsonl`
- `streamlit-app/data/knowledge_index.jsonl`
- `streamlit-app/data/rag_index.jsonl`
- `streamlit-app/data/drawing_analysis.jsonl`
- `streamlit-app/data/drawing_pages.jsonl`
- `streamlit-app/data/file_registry.jsonl`
- `streamlit-app/data/ingested_knowledge.jsonl`
- `streamlit-app/data/ingested_rag_chunks.jsonl`

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
- [ ] `/Records` 全部記錄搜尋可找到 drawing／handoff／knowledge／file 記錄
- [ ] `/Knowledge_Ingestion` 上載 PDF／TXT／MD 後產生知識來源與 RAG 片段
- [ ] `/Release_Readiness` 顯示就緒分數、冒煙清單及客戶試用流程
- [ ] `/Drawing_Analysis` 可開啟
- [ ] 上載 PDF／圖片圖則後產生：
  - [ ] 文件概覽（document overview）
  - [ ] 頁面摘要（page summary）
  - [ ] 問題／缺漏資訊（issues / missing information）
  - [ ] CAD／BIM 交接清單（CAD/BIM handoff list）
- [ ] `/Ask_AICOS` 能引用已上載的 PDF／圖則／CAD-BIM 內容作答
- [ ] 正常 UI **不會** 顯示 API keys、原始供應商錯誤（raw provider errors）、Traceback、原始 JSON 或檔案系統路徑（filesystem paths）

## 尚未生產／延後項目（Not Yet Production / Deferred）

- Google Drive：已 ready-to-connect（欄位／hook 已預留），live OAuth 尚未啟用（Google Drive pending / ready-to-connect）
- Supabase persistence
- 使用者／團隊／項目權限與登入（user / team / project permissions & login）— 延後至 **Phase 6.2**（deferred to Phase 6.2）
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
