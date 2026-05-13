# HK-AICOS SOP SYSTEM
## Standard Operating Procedure Layer - 企業級文件骨架

---

## 系統用途

SOP (Standard Operating Procedure) 系統為 HK-AICOS 的**標準作業程序層**，定義所有常見工程作業的標準流程。

### 核心功能

1. **標準化流程** - 定義標準作業程序
2. **Agent 參考** - Agent 根據 SOP 執行任務
3. **質量保證** - 確保作業符合標準
4. **風險控制** - 識別及控制風險
5. **持續改善** - 根據經驗更新 SOP

---

## SOP 資料夾結構

```
HK-AICOS/sop/
├── SOP_SYSTEM.md                    ← 本文件
├── daily-site-report-sop.md         ← 地盤日報 SOP
├── safety-inspection-sop.md         ← 安全巡查 SOP
├── material-control-sop.md          ← 材料管理 SOP
├── rfi-risc-sop.md                  ← RFI/RISC 管理 SOP
├── vo-management-sop.md             ← VO 管理 SOP
└── legal-review-sop.md              ← 法律審查 SOP
```

---

## 核心 SOP 清單

| SOP 名稱 | 負責 Agent | 用途 |
|---------|-----------|------|
| 地盤日報 SOP | Engineering Agent | 每日工程記錄 |
| 安全巡查 SOP | Safety Agent | 安全檢查流程 |
| 材料管理 SOP | Material Agent | 材料採購及驗收 |
| RFI/RISC 管理 SOP | Engineering Agent | 檢查申請流程 |
| VO 管理 SOP | QS Agent + Legal Agent | VO 處理流程 |
| 法律審查 SOP | Legal Agent | 法律文件審查 |

---

## SOP 標準格式

每個 SOP 文件應包括：

### 1. SOP 基本資訊
- SOP 編號
- SOP 名稱
- 版本
- 生效日期
- 負責部門/Agent
- 審批人

### 2. 目的
- 說明 SOP 的目的

### 3. 適用範圍
- 說明 SOP 適用的情況

### 4. 職責
- 列出相關人員/Agent 的職責

### 5. 流程圖
- 提供流程圖

### 6. 詳細步驟
- 逐步說明作業程序

### 7. 相關文件
- 列出相關表格、文件

### 8. 風險提醒
- 列出常見風險及注意事項

### 9. 記錄
- 說明需要記錄的內容

### 10. 附件
- 相關表格、範本

---

## SOP 與 Agent 的關係

### Agent 使用 SOP 的流程

```
Agent 接收任務
    ↓
識別任務類型
    ↓
讀取相關 SOP
    ↓
按 SOP 步驟執行
    ↓
記錄執行結果
    ↓
識別偏離 SOP 的情況
    ↓
上報 PM Agent（如需要）
```

### SOP 覆蓋範圍

| 工程階段 | 相關 SOP |
|---------|---------|
| 投標階段 | 投標管理 SOP |
| 合約簽署 | 合約管理 SOP、法律審查 SOP |
| 施工準備 | 地盤設立 SOP、安全管理 SOP |
| 施工階段 | 地盤日報 SOP、RFI/RISC SOP、材料管理 SOP、安全巡查 SOP |
| 變更管理 | VO 管理 SOP |
| 完工階段 | 完工驗收 SOP、交樓 SOP |
| 結算階段 | 結算管理 SOP |

---

## SOP 更新機制

### 更新觸發條件

1. **法規更新** - 政府部門法規變更
2. **公司政策更新** - 公司內部政策變更
3. **經驗學習** - 從工程經驗中學習
4. **事故教訓** - 從事故中吸取教訓
5. **持續改善** - 定期檢討及改善

### 更新流程

```
識別更新需要
    ↓
草擬更新內容
    ↓
相關部門審查
    ↓
PM Agent 批准
    ↓
Legal Agent 審查（如涉及法律）
    ↓
發布新版本 SOP
    ↓
培訓相關人員/Agent
    ↓
舊版本 SOP 存檔
```

---

## SOP 與 RAG 的關係

- SOP 文件儲存在 `rag/company-reference/`
- Agent 透過 RAG 系統查詢 SOP
- Phase 2 將 SOP 轉換為 Vector Database
- Agent 可以快速檢索相關 SOP 內容

---

## SOP 與 Regulation 的關係

- SOP 必須符合香港政府部門法規
- SOP 必須參考 `regulations/` 內的法規文件
- SOP 更新時必須檢查法規合規性
- Legal Agent 負責審查 SOP 的法律合規性

---

## 未來擴展方向

### Phase 2
- 將所有 SOP 數碼化
- 建立 SOP 資料庫
- Agent 自動查詢 SOP
- SOP 執行記錄自動化

### Phase 3
- AI 自動建議 SOP 改善
- AI 自動檢查 SOP 合規性
- AI 自動生成 SOP 報告
- SOP 執行監控及分析

---

## 版本記錄

- v1.0.0 - 2026年5月 - Phase 1 文件骨架
