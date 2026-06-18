# HK-AICOS Streamlit MVP

**Hong Kong AI Construction Operating System**  
Phase 2.0 — Semi-Automated AI Assistant  
Developed by **Buildway Tech (HK) Limited**

---

## Quick Start

### 1. 建立建議的 Python 環境

建議使用 **Python 3.11.9**。Python 3.14 並非本專案的目標執行環境；請勿提交由其他 Python 版本產生的 bytecode/cache 檔案。

Windows（在專案根目錄執行）：

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install -r streamlit-app/requirements.txt
streamlit run streamlit-app/app.py
```

### 2. Install dependencies（現有環境）

```bash
cd streamlit-app
pip install -r requirements.txt
pip install anthropic
```

### 3. Set up API key (optional — app runs in demo mode without it)

Create a `.env` file in this directory:

```
ANTHROPIC_API_KEY=
```

### 4. Run the app

```bash
streamlit run app.py
```

Open your browser at `http://localhost:8501`

---

## 啟用 Ask AICOS 即時網上搜尋

在專案根目錄的 `.env` 加入其中一個供應商金鑰（切勿提交 `.env`）：

```dotenv
TAVILY_API_KEY=
BRAVE_SEARCH_API_KEY=
```

- 同時設定兩者時，系統會優先使用 Tavily；沒有 Tavily 才使用 Brave Search。
- 沒有設定金鑰或供應商暫時失敗時，系統不會假裝已完成網上搜尋，並會清楚顯示後備狀態；Ask AICOS 仍可使用本機知識庫及已儲存記錄。
- 搜尋結果會分類為香港官方來源、可信行業來源、一般網上來源或未分類來源。安全及法例問題會優先採用香港政府、勞工處、屋宇署、機電工程署、發展局、香港法例電子版及建造業議會相關資料。
- 安全及法例答案只供工作參考，必須以官方最新版本及合資格人士意見作最終核實，並不構成法律意見。

`.env.md` 並非標準 dotenv 檔案；應使用 `.env`。應用程式會在啟動時載入專案根目錄或 `streamlit-app/.env`（如適用），但不會覆寫現有檔案。

---

## Features

| Page | Description |
|------|-------------|
| 🏠 Home | System overview and feature guide |
| 🔍 Analysis | Upload files, ask questions, get AI analysis |
| 📋 History | Review past analyses and download reports |
| 📚 Knowledge Base | Browse HK regulations, agents, SOPs |
| ⚙️ Settings | API keys, system status, agent config |

## Analysis Types

- 安全風險分析 — Safety Risk Analysis
- 圖紙 / CAP / MIB 分析 — Drawing Analysis
- 工程進度分析 — Progress Analysis
- 法規 / 合規檢查 — Regulatory Compliance
- 臨時設施位置分析 — Temporary Works Analysis
- 成本 / 工期影響分析 — Cost & Programme Impact
- PM 綜合分析 — PM Comprehensive Analysis

## File Structure

```
streamlit-app/
├── app.py                  # Main page (home)
├── requirements.txt        # Python dependencies
├── pages/
│   ├── 1_Analysis.py       # AI analysis page
│   ├── 2_History.py        # Analysis history
│   ├── 3_Knowledge_Base.py # KB browser
│   └── 4_Settings.py       # Settings & system info
├── utils/
│   ├── agent_router.py     # Agent routing logic
│   ├── risk_classifier.py  # Risk level classification
│   ├── file_loader.py      # File upload & processing
│   ├── rag_reader.py       # Knowledge base reader
│   └── report_generator.py # PDF report generation
├── uploads/                # Uploaded files (auto-created)
└── reports/                # Generated PDF reports (auto-created)
```

## Knowledge Base

The app reads from `../HK-AICOS/` (Phase 1 document skeleton):

- `HK-AICOS/regulations/` — 12 HK government department layers
- `HK-AICOS/agents/` — 10 agent documentation files
- `HK-AICOS/sop/` — Standard operating procedures
- `HK-AICOS/governance/` — AI governance rules

## Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ Done | Document skeleton |
| Phase 2.0 | ✅ Done | Streamlit MVP |
| Phase 2.5 | 🔄 Next | Vector DB (Qdrant/Chroma) |
| Phase 3 | 📋 Planned | Full multi-agent system |

## Disclaimer

AI-assisted analysis only. All findings must be confirmed by qualified professionals.  
For structural, fire, electrical, legal, or public road matters — Hong Kong registered professionals (AP, RSE, REW, etc.) confirmation is mandatory.
