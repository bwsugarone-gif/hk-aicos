# PHASE 2.0 OVERVIEW
## HK-AICOS 半自動 AI 工程助理系統

---

**版本：** v2.0.0
**日期：** 2026-05-13
**狀態：** Phase 2.0 文件骨架

---

## 系統定位

Phase 2.0 係 HK-AICOS 的**半自動 AI 工程助理**階段。

```
Phase 1.0  → 企業級文件骨架（已完成）
Phase 1.5  → 香港工程法規 RAG 文件結構（已完成）
Phase 2.0  → 半自動 AI 工程助理流程（現階段）  ← 你在這裡
Phase 2.5  → MCP / RAG / Memory / Dashboard 深度整合（之後）
Phase 3.0  → Full AI Construction Operating System（之後）
```

---

## Phase 2.0 目標

建立一個**人機協作**的工程助理流程：

1. **輸入** - 接收 WhatsApp / 手動輸入 / 圖片 / PDF / 地盤資料
2. **分類** - AI Agent 識別任務類型，觸發對應 Agent
3. **分析** - Agent 讀取 Markdown Prompt / Regulations / RAG 文件
4. **輸出** - 生成工程、安全、法規、成本、工期分析報告
5. **確認** - 由人類 PM 最終確認，AI 不作最終決定

---

## Phase 2.0 核心原則

### 半自動，非全自動

| 項目 | Phase 2.0 做法 |
|------|---------------|
| 輸入處理 | 人手輸入 + AI 分類 |
| 分析 | AI 輔助分析 |
| 決策 | 人類最終確認 |
| 記錄 | 手動記錄（無 Database） |
| 通訊 | 人手發送（AI 不自動發送） |

### 明確限制

Phase 2.0 **不包括**：

- ❌ 正式 Database（無 SQL / NoSQL）
- ❌ MCP 整合（Phase 2.5 才做）
- ❌ Dashboard（Phase 3 才做）
- ❌ Memory System（Phase 2.5 才做）
- ❌ Auto Decision（AI 不自動決定）
- ❌ 自動發送正式回覆
- ❌ AI 代表公司作最終決定
- ❌ 安裝 Package（除非另行確認）

---

## Phase 2.0 工作流程概覽

```
地盤輸入
（WhatsApp / 手動 / 圖片 / PDF）
        ↓
[STEP 1] 輸入格式化
        ↓
[STEP 2] AI Agent 分類
（識別任務類型，觸發對應 Agent）
        ↓
[STEP 3] Agent 讀取參考文件
（Markdown Prompt / Regulations / RAG）
        ↓
[STEP 4] AI 生成分析報告
（工程 / 安全 / 法規 / 成本 / 工期）
        ↓
[STEP 5] 風險評估
（低 / 中 / 高 / 極高）
        ↓
[STEP 6] 人工確認
（PM 確認 / Legal 確認 / 專業人士確認）
        ↓
[STEP 7] 輸出最終報告
（由人類 PM 簽發）
```

---

## Phase 2.0 文件索引

| 文件 | 用途 |
|------|------|
| `PHASE_2_0_OVERVIEW.md` | 本文件 - 系統總覽 |
| `SEMI_AI_WORKFLOW.md` | 半自動工作流程詳細說明 |
| `WHATSAPP_INPUT_TEMPLATE.md` | WhatsApp 輸入格式模板 |
| `AGENT_EXECUTION_TEMPLATE.md` | Agent 執行模板（10 個 Agent） |
| `HUMAN_APPROVAL_FLOW.md` | 人工確認流程 |
| `OUTPUT_REPORT_TEMPLATE.md` | AI 分析輸出報告模板 |
| `RISK_LEVEL_STANDARD.md` | 風險等級標準 |
| `PHASE_2_5_RESERVED.md` | Phase 2.5 預留文件 |

---

## 使用方式（Phase 2.0）

### 日常使用步驟

1. 地盤人員透過 WhatsApp 發送訊息（按 `WHATSAPP_INPUT_TEMPLATE.md` 格式）
2. 辦公室人員將訊息輸入 AI（Claude / ChatGPT）
3. AI 根據 `AGENT_EXECUTION_TEMPLATE.md` 分析
4. AI 輸出報告（按 `OUTPUT_REPORT_TEMPLATE.md` 格式）
5. PM 按 `HUMAN_APPROVAL_FLOW.md` 確認
6. 人手記錄及跟進

### 所需工具（Phase 2.0）

- Claude / ChatGPT（AI 分析）
- WhatsApp（輸入）
- Microsoft Word / Google Docs（報告輸出）
- 現有 Markdown 文件（Agent Prompt / Regulations）

---

## 與現有文件的關係

Phase 2.0 直接使用 Phase 1 建立的文件：

```
HK-AICOS/
├── agents/           ← Agent Prompt（直接使用）
├── regulations/      ← 法規參考（直接使用）
├── rag/              ← RAG 文件（手動查閱）
├── skills/           ← 技能庫（直接使用）
├── sop/              ← SOP（直接使用）
└── governance/       ← AI 治理原則（直接使用）
```

---

## 成功指標（Phase 2.0）

| 指標 | 目標 |
|------|------|
| 輸入格式化時間 | < 5 分鐘 |
| AI 分析時間 | < 10 分鐘 |
| 報告生成時間 | < 15 分鐘 |
| 人工確認時間 | < 30 分鐘 |
| 整體流程時間 | < 1 小時 |

---

## 下一步（Phase 2.5 預告）

Phase 2.5 將加入：
- MCP 整合（自動讀取 RAG 文件）
- RAG Ingestion Pipeline
- Memory System（記錄歷史案例）
- Dashboard（視覺化報告）
- 半自動通知系統

詳見 `PHASE_2_5_RESERVED.md`

---

## 版本記錄

- v2.0.0 - 2026-05-13 - Phase 2.0 文件骨架建立
