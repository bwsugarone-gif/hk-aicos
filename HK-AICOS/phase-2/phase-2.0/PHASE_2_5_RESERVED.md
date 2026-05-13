# PHASE 2.5 RESERVED
## HK-AICOS Phase 2.5 預留文件

---

**版本：** v2.0.0
**日期：** 2026-05-13
**狀態：** 預留文件 - Phase 2.5 尚未開始

---

## 重要說明

> **本文件為 Phase 2.5 預留規劃文件。**
> **Phase 2.5 尚未開始，本文件只作規劃參考。**
> **所有內容待 Phase 2.0 完成後才正式設計。**

---

## Phase 2.5 定位

```
Phase 2.0  → 半自動 AI 工程助理（現階段）
Phase 2.5  → MCP / RAG / Memory / Dashboard 深度整合（下一階段）  ← 本文件
Phase 3.0  → Full AI Construction Operating System（之後）
```

Phase 2.5 係 Phase 2.0 的升級版，將現有的**手動半自動流程**升級為**自動化整合流程**。

---

## Phase 2.5 目標（規劃中）

### 核心升級

| 功能 | Phase 2.0 現況 | Phase 2.5 目標 |
|------|--------------|--------------|
| RAG 查詢 | 手動查閱文件 | 自動 RAG 查詢 |
| 文件輸入 | 手動複製貼上 | MCP 自動讀取 |
| 記錄 | 手動記錄 | 自動記錄至 Database |
| 報告 | 手動整理 | 自動生成 |
| 通知 | 手動發送 | 半自動通知 |
| 歷史查詢 | 無 | Memory System |
| 視覺化 | 無 | Dashboard |

---

## Phase 2.5 計劃功能（規劃中）

### 1. MCP 整合

**目標：** 讓 AI Agent 自動讀取 RAG 文件，無需人手複製

**規劃內容：**
- MCP Server 連接 RAG 文件庫
- Agent 自動查詢相關文件
- 自動提取相關法規條文
- 自動引用公司 SOP

**技術選項（待確認）：**
- Claude MCP（Anthropic）
- 自建 MCP Server
- 文件讀取 API

---

### 2. RAG Ingestion Pipeline

**目標：** 自動處理 PDF / Word 文件，建立可查詢的知識庫

**規劃內容：**
- PDF 自動解析
- 文件分塊（Chunking）
- 向量化（Embedding）
- 向量資料庫儲存

**技術選項（待確認）：**
- Qdrant（向量資料庫）
- Chroma（本地向量資料庫）
- Supabase pgvector（雲端）
- OpenAI Embeddings / Anthropic Embeddings

**文件來源：**
```
HK-AICOS/rag/
├── legal-regulation/     ← 香港法規（已建立）
├── company-reference/    ← 公司文件
├── technical-specification/
├── quality-management/
├── method-statement/
├── inspection-test-plan/
├── contract-reference/
└── legal-reference/
```

---

### 3. Database Schema

**目標：** 建立正式資料庫，記錄所有工程數據

**規劃資料表（來自 MASTER_SYSTEM.md）：**

```sql
-- 規劃中，Phase 2.5 才設計
projects          -- 工程項目
workers           -- 工人資料
attendance        -- 出勤記錄
payroll           -- 薪金
materials         -- 材料
suppliers         -- 供應商
quotations        -- 報價
invoices          -- 發票
contracts         -- 合約
vo_records        -- VO 記錄
safety_records    -- 安全記錄
inspection_records -- 檢驗記錄
drawings          -- 圖則
legal_reviews     -- 法律審查
ai_analysis_logs  -- AI 分析記錄（新增）
approval_records  -- 確認記錄（新增）
```

**技術選項（待確認）：**
- Supabase（PostgreSQL + 向量支援）
- PlanetScale（MySQL）
- MongoDB（文件型）

---

### 4. Memory System

**目標：** 記錄歷史案例，讓 AI 從過去學習

**規劃記錄內容（來自 MASTER_SYSTEM.md）：**
- 歷史工程案例（成功/失敗）
- 供應商表現記錄
- 工人表現記錄
- 常見安全問題
- 工程延誤原因
- 法律及合約風險案例

**使用方式：**
- Agent 查詢相似歷史案例
- 提供更準確的風險評估
- 優化建議方案

---

### 5. Dashboard

**目標：** 視覺化工程數據，提供管理層概覽

**規劃功能：**
- 工程進度總覽
- 風險監控面板
- 成本追蹤
- 安全記錄
- AI 分析歷史
- 合規狀態

**技術選項（待確認）：**
- Next.js + Tailwind CSS
- Streamlit（快速原型）
- Retool（低代碼）

---

### 6. 半自動通知系統

**目標：** 自動發送通知，減少人手操作

**規劃功能：**
- 風險等級升級自動通知 PM
- 法定通報提醒
- 工程進度提醒
- 材料到期提醒

**技術選項（待確認）：**
- WhatsApp Business API
- Telegram Bot
- Email（SMTP）
- 內部通知系統

---

## Phase 2.5 與 Phase 2.0 的接口

### 現有 Phase 2.0 文件將升級

| Phase 2.0 文件 | Phase 2.5 升級 |
|--------------|--------------|
| `WHATSAPP_INPUT_TEMPLATE.md` | 自動解析 WhatsApp 輸入 |
| `AGENT_EXECUTION_TEMPLATE.md` | Agent 自動執行，無需手動輸入 |
| `HUMAN_APPROVAL_FLOW.md` | 自動生成確認清單，人類只需點擊確認 |
| `OUTPUT_REPORT_TEMPLATE.md` | 自動生成並存檔報告 |
| `RISK_LEVEL_STANDARD.md` | 自動風險評估，自動觸發確認流程 |

### 數據遷移

Phase 2.0 的手動記錄將遷移至 Phase 2.5 的 Database：
- 確認記錄 → approval_records 表
- AI 分析報告 → ai_analysis_logs 表
- 風險記錄 → safety_records / legal_reviews 表

---

## Phase 2.5 前置條件

在開始 Phase 2.5 之前，必須完成：

### Phase 2.0 完成確認
- [ ] Phase 2.0 文件骨架建立完成
- [ ] 半自動流程已在實際工程中測試
- [ ] 收集 Phase 2.0 使用反饋
- [ ] 識別需要自動化的痛點

### 技術決策
- [ ] 確認 AI 模型選擇（Claude / GPT / 其他）
- [ ] 確認向量資料庫選擇
- [ ] 確認主資料庫選擇
- [ ] 確認 MCP 整合方式
- [ ] 確認 Dashboard 技術棧
- [ ] 確認通知系統方式

### 資源準備
- [ ] 確認開發預算
- [ ] 確認開發人員
- [ ] 確認伺服器 / 雲端資源
- [ ] 確認數據安全要求

---

## Phase 2.5 預計時間表（草稿）

> ⚠️ **以下時間表為初步估算，待 Phase 2.0 完成後才正式規劃**

| 階段 | 內容 | 預計時間 |
|------|------|---------|
| 2.5.1 | Database Schema 設計 | 2-4 週 |
| 2.5.2 | RAG Ingestion Pipeline | 4-6 週 |
| 2.5.3 | MCP 整合 | 2-4 週 |
| 2.5.4 | Memory System | 3-4 週 |
| 2.5.5 | Dashboard 基礎版 | 4-6 週 |
| 2.5.6 | 通知系統 | 2-3 週 |
| 2.5.7 | 測試及優化 | 4-6 週 |
| **總計** | | **21-33 週** |

---

## 與 Phase 3 的關係

Phase 2.5 完成後，Phase 3 將在此基礎上建立：

```
Phase 2.5 基礎設施
（Database + RAG + MCP + Memory + Dashboard）
        ↓
Phase 3 升級
- Multi-Agent 自主協作
- AI 自動決策（低風險）
- 完整 ERP 整合
- Mobile App
- 進階 AI 學習
```

---

## 注意事項

⚠️ **Phase 2.5 涉及正式程式開發，需要專業開發人員**

⚠️ **Database 設計需要仔細規劃，避免日後重構**

⚠️ **RAG 系統需要定期更新法規文件**

⚠️ **所有 AI 自動化功能仍需保留人工確認機制**

⚠️ **數據安全及私隱保護必須符合香港法例**

---

## 版本記錄

- v2.0.0 - 2026-05-13 - Phase 2.5 預留文件建立（Phase 2.0 階段）
