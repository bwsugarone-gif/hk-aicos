# HK-AICOS ERP STRUCTURE
## ERP / Database Layer - 企業級文件骨架

---

## 系統用途

ERP (Enterprise Resource Planning) / Database Layer 為 HK-AICOS 的**數據層**，儲存及管理所有工程數據。

### 核心功能

1. **數據儲存** - 儲存所有工程相關數據
2. **Agent 查詢** - Agent 查詢及更新數據
3. **數據分析** - 提供數據分析功能
4. **Dashboard 支援** - 提供 Dashboard 數據
5. **Memory 支援** - 支援 Memory Layer 學習

---

## 核心資料表（Phase 2 設計）

### 1. 工程管理

| 資料表 | 用途 | 主要欄位 |
|--------|------|---------|
| projects | 工程項目 | project_id, name, client, start_date, end_date, status, budget |
| contracts | 合約 | contract_id, project_id, type, value, start_date, end_date |
| vo_records | VO 記錄 | vo_id, project_id, description, value, status, approval_date |

### 2. 人力資源

| 資料表 | 用途 | 主要欄位 |
|--------|------|---------|
| workers | 工人資料 | worker_id, name, trade, license_no, contact, status |
| attendance | 出勤記錄 | attendance_id, worker_id, project_id, date, hours, overtime |
| payroll | 薪金 | payroll_id, worker_id, period, basic_pay, overtime_pay, deductions, net_pay |

### 3. 材料管理

| 資料表 | 用途 | 主要欄位 |
|--------|------|---------|
| materials | 材料 | material_id, name, specification, unit, unit_price |
| suppliers | 供應商 | supplier_id, name, contact, rating, payment_terms |
| quotations | 報價 | quotation_id, supplier_id, material_id, price, validity |
| purchase_orders | 採購單 | po_id, supplier_id, material_id, quantity, delivery_date |
| material_receipts | 材料收貨 | receipt_id, po_id, received_date, quantity, inspector |

### 4. 財務管理

| 資料表 | 用途 | 主要欄位 |
|--------|------|---------|
| invoices | 發票 | invoice_id, project_id, supplier_id, amount, due_date, status |
| payments | 付款 | payment_id, invoice_id, amount, payment_date, method |
| expenses | 支出 | expense_id, project_id, category, amount, date, description |

### 5. 安全管理

| 資料表 | 用途 | 主要欄位 |
|--------|------|---------|
| safety_records | 安全記錄 | record_id, project_id, date, inspector, findings, actions |
| accidents | 事故記錄 | accident_id, project_id, date, type, severity, injured_worker, description |
| safety_training | 安全培訓 | training_id, worker_id, course, date, expiry_date, certificate |

### 6. 質量管理

| 資料表 | 用途 | 主要欄位 |
|--------|------|---------|
| inspection_records | 檢驗記錄 | inspection_id, project_id, work_type, date, inspector, result |
| test_records | 測試記錄 | test_id, project_id, material, test_type, date, result |
| ncr_records | 不合格記錄 | ncr_id, project_id, description, date, corrective_action, status |

### 7. 圖則管理

| 資料表 | 用途 | 主要欄位 |
|--------|------|---------|
| drawings | 圖則 | drawing_id, project_id, drawing_no, title, version, date, status |
| drawing_revisions | 圖則修訂 | revision_id, drawing_id, revision_no, date, description |

### 8. 法律管理

| 資料表 | 用途 | 主要欄位 |
|--------|------|---------|
| legal_reviews | 法律審查 | review_id, project_id, document_type, date, reviewer, risk_level, findings |
| claims | 索償 | claim_id, project_id, type, amount, date, status, resolution |
| insurance | 保險 | insurance_id, project_id, type, insurer, coverage, premium, expiry_date |

### 9. Agent 記錄

| 資料表 | 用途 | 主要欄位 |
|--------|------|---------|
| agent_decisions | Agent 決策記錄 | decision_id, agent_name, task, decision, reasoning, timestamp |
| agent_queries | Agent 查詢記錄 | query_id, agent_name, query_type, result, timestamp |

---

## Database 架構（Phase 2）

### 技術選項

| 技術 | 優點 | 缺點 |
|------|------|------|
| PostgreSQL | 開源、功能強大、支援 pgvector | 需要自行管理 |
| MySQL | 開源、廣泛使用 | 功能較少 |
| Supabase | PostgreSQL + API + Auth | 雲端服務、收費 |
| MongoDB | NoSQL、靈活 | 不適合關聯數據 |
| SQLite | 輕量、簡單 | 不適合大型系統 |

### 建議架構

```
PostgreSQL Database
├── Schema: projects (工程數據)
├── Schema: hr (人力資源)
├── Schema: materials (材料管理)
├── Schema: finance (財務管理)
├── Schema: safety (安全管理)
├── Schema: quality (質量管理)
├── Schema: legal (法律管理)
└── Schema: ai (AI Agent 記錄)
```

---

## 數據流程

### Agent 寫入數據

```
Agent 執行任務
    ↓
生成數據
    ↓
驗證數據
    ↓
寫入 Database
    ↓
記錄 Agent 決策
    ↓
觸發相關通知
```

### Agent 查詢數據

```
Agent 接收任務
    ↓
識別需要的數據
    ↓
查詢 Database
    ↓
獲取數據
    ↓
分析數據
    ↓
執行任務
```

---

## 數據安全

### 存取控制

| 權限等級 | 說明 | 適用 Agent |
|---------|------|-----------|
| Read Only | 只能讀取 | 大部分 Agent |
| Read/Write | 可讀寫自己負責的數據 | 所有 Agent |
| Admin | 可讀寫所有數據 | PM Agent, System Admin |

### 數據加密

- 敏感數據（如薪金、合約金額）必須加密
- 個人資料必須符合私隱條例
- 法律文件必須加密儲存

### 數據備份

- 每日自動備份
- 異地備份
- 定期測試恢復

---

## 數據分析（Phase 3）

### 分析功能

1. **工程進度分析**
   - 進度完成率
   - 延誤分析
   - 預測完工日期

2. **成本分析**
   - 實際成本 vs 預算
   - 成本超支分析
   - 成本預測

3. **人力分析**
   - 工人出勤率
   - 工人效率
   - 人力需求預測

4. **材料分析**
   - 材料使用率
   - 供應商表現
   - 材料成本分析

5. **安全分析**
   - 事故率
   - 常見安全問題
   - 安全趨勢

6. **質量分析**
   - 不合格率
   - 常見質量問題
   - 質量趨勢

---

## 與其他系統的整合

### RAG 系統

- Database 儲存文件 Metadata
- Vector Database 儲存文件內容
- Agent 查詢時整合兩者

### Memory 系統

- Database 提供歷史數據
- Memory 系統學習及分析
- 提供預測及建議

### Dashboard 系統

- Database 提供實時數據
- Dashboard 顯示圖表及報告
- 支援數據下載

---

## 未來擴展方向

### Phase 2
- 設計完整 Database Schema
- 建立 Database
- 建立 API 接口
- Agent 連接 Database

### Phase 3
- 實時數據同步
- 數據分析及預測
- AI 自動數據清理
- 數據視覺化

---

## 版本記錄

- v1.0.0 - 2026年5月 - Phase 1 文件骨架
