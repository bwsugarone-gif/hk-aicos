# HK-AICOS Streamlit MVP

**Hong Kong AI Construction Operating System**  
Phase 2.0 — Semi-Automated AI Assistant  
Developed by **Buildway Tech (HK) Limited**

---

## Quick Start

### 1. Install dependencies

```bash
cd streamlit-app
pip install -r requirements.txt
pip install anthropic
```

### 2. Set up API key (optional — app runs in demo mode without it)

Create a `.env` file in this directory:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 3. Run the app

```bash
streamlit run app.py
```

Open your browser at `http://localhost:8501`

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
