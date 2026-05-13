# HK-AICOS WORKFLOW SYSTEM
## Workflow Layer - 企業級文件骨架

---

## 系統用途

Workflow 系統為 HK-AICOS 的**流程層**，定義及自動化工程作業流程。

### 核心功能

1. **流程定義** - 定義標準工作流程
2. **自動路由** - 自動分配任務至相關 Agent
3. **狀態追蹤** - 追蹤任務執行狀態
4. **通知提醒** - 自動通知相關人員
5. **流程優化** - 根據經驗優化流程

---

## 標準工作流程

### 總流程

```
輸入來源
    ↓
WhatsApp / Telegram / Form / Email
    ↓
AI Agent 接收
    ↓
RAG 查詢相關資料
    ↓
Regulation Layer 檢查合規
    ↓
Agent 分析及處理
    ↓
ERP 記錄數據
    ↓
高風險？ → Yes → PM Agent + Legal Agent 確認
    ↓ No
Memory Layer 學習
    ↓
Dashboard / Report 輸出
    ↓
通知相關人員
```

---

## 常見工作流程

### 1. 地盤日報流程

```
Foreman Agent 收集地盤資料
    ↓
Engineering Agent 整理日報
    ↓
檢查進度偏差
    ↓
偏差 > 閾值？ → Yes → PM Agent 確認
    ↓ No
記錄至 ERP
    ↓
生成日報
    ↓
發送至相關人員
```

---

### 2. 安全巡查流程

```
Safety Agent 進行巡查
    ↓
記錄巡查結果
    ↓
發現違規？ → Yes → 發出改善通知
    ↓              ↓
No              Foreman Agent 跟進
    ↓              ↓
記錄至 ERP      限期改善
    ↓              ↓
生成巡查報告    複檢
    ↓              ↓
發送至相關人員  記錄結果
```

---

### 3. 材料採購流程

```
Engineering Agent 提出材料需求
    ↓
Material Agent 檢查庫存
    ↓
需要採購？ → Yes → 查詢供應商
    ↓ No           ↓
安排使用        Memory 推薦供應商
                   ↓
                QS Agent 比較報價
                   ↓
                PM Agent 批准
                   ↓
                發出採購單
                   ↓
                追蹤交貨
                   ↓
                驗收
                   ↓
                記錄至 ERP
```

---

### 4. VO 處理流程

```
Engineering Agent 識別變更
    ↓
QS Agent 評估成本影響
    ↓
Engineering Agent 評估工期影響
    ↓
PM Agent 整合分析
    ↓
Legal Agent 審查合約條款
    ↓
超過閾值？ → Yes → 管理層批准
    ↓ No           ↓
PM Agent 批准    PM + Legal 確認
    ↓              ↓
提交客戶          提交客戶
    ↓              ↓
客戶批准          客戶批准
    ↓              ↓
記錄至 ERP        記錄至 ERP
    ↓              ↓
更新合約          更新合約
```

---

### 5. 工傷事故流程

```
Foreman Agent 通報事故
    ↓
Safety Agent 立即響應
    ↓
現場處理及急救
    ↓
Safety Agent 調查
    ↓
Legal Agent 評估責任
    ↓
PM Agent 整合報告
    ↓
嚴重事故？ → Yes → 通報勞工處
    ↓ No           ↓
記錄至 ERP      Legal Agent 確認程序
    ↓              ↓
Accounting Agent 處理保險
    ↓              ↓
Memory 學習      記錄至 ERP
    ↓              ↓
改善措施         改善措施
```

---

### 6. RFI/RISC 流程

```
Engineering Agent 提交 RFI/RISC
    ↓
檢查文件完整性
    ↓
Surveying Agent 測量（如需要）
    ↓
Safety Agent 檢查安全（如需要）
    ↓
通知顧問/客戶
    ↓
等待檢查
    ↓
記錄檢查結果
    ↓
合格？ → Yes → 繼續下一工序
    ↓ No        ↓
改善          記錄至 ERP
    ↓           ↓
複檢          通知相關人員
```

---

## Workflow 自動化（Phase 3）

### 自動化功能

| 功能 | 說明 | 效益 |
|------|------|------|
| 自動分配任務 | 根據任務類型自動分配至相關 Agent | 提升效率 |
| 自動提醒 | 自動提醒逾期任務 | 減少延誤 |
| 自動生成報告 | 自動生成日報、週報、月報 | 節省時間 |
| 自動風險預警 | 自動識別及預警風險 | 降低風險 |
| 自動合規檢查 | 自動檢查法規合規性 | 確保合規 |
| 自動通知 | 自動通知相關人員 | 改善溝通 |

---

## Workflow 觸發機制

### 時間觸發

| 觸發時間 | 觸發任務 |
|---------|---------|
| 每日 08:00 | 生成昨日地盤日報 |
| 每週一 09:00 | 生成上週週報 |
| 每月 1 日 | 生成上月月報 |
| 每日 17:00 | 提醒未完成任務 |

### 事件觸發

| 觸發事件 | 觸發任務 |
|---------|---------|
| 工傷事故 | 啟動工傷處理流程 |
| VO 申請 | 啟動 VO 處理流程 |
| 材料延誤 | 啟動延誤應對流程 |
| 安全違規 | 啟動改善流程 |
| 質量問題 | 啟動 NCR 流程 |

### 條件觸發

| 觸發條件 | 觸發任務 |
|---------|---------|
| 進度延誤 > 5% | 通知 PM Agent |
| 成本超支 > 10% | 通知 PM + QS Agent |
| 安全違規 > 3 次 | 通知 PM + Safety Agent |
| 材料庫存 < 安全水平 | 啟動採購流程 |

---

## Workflow 監控

### 監控指標

| 指標 | 目標 | 監控頻率 |
|------|------|---------|
| 任務完成率 | >95% | 每日 |
| 平均處理時間 | <24小時 | 每週 |
| 逾期任務數量 | <5% | 每日 |
| 流程瓶頸識別 | 持續監控 | 實時 |

### 流程優化

```
監控流程執行
    ↓
識別瓶頸
    ↓
分析原因
    ↓
提出改善方案
    ↓
測試新流程
    ↓
評估效果
    ↓
更新流程
```

---

## Workflow 與其他系統的整合

### 與 Agent 系統

- Workflow 自動分配任務至 Agent
- Agent 執行任務並更新狀態
- Workflow 追蹤任務進度

### 與 ERP 系統

- Workflow 記錄所有流程數據至 ERP
- ERP 提供數據支援 Workflow 決策

### 與 Memory 系統

- Memory 學習流程執行數據
- Memory 提供流程優化建議

### 與 Dashboard 系統

- Dashboard 顯示流程執行狀態
- Dashboard 提供流程分析報告

---

## 未來擴展方向

### Phase 2
- 定義所有核心流程
- 建立流程引擎
- Agent 連接 Workflow
- 基礎自動化

### Phase 3
- 完全自動化
- AI 流程優化
- 自適應流程
- 實時流程監控

---

## 版本記錄

- v1.0.0 - 2026年5月 - Phase 1 文件骨架
