# HK-AICOS AGENT SYSTEM
## Multi-Agent 協作系統總覽

---

## 系統概述

HK-AICOS 採用 Multi-Agent 架構，由 10 個專業 Agent 協同工作，模擬真實建築工程公司的部門協作。

每個 Agent 都有：
- 專業身份
- 負責範圍
- 技能庫（Skills）
- 法規知識（Regulations）
- RAG 知識庫存取
- 風險評估能力

---

## 10 個核心 Agent

| # | Agent 名稱 | 部門 | 主要職責 |
|---|-----------|------|----------|
| 1 | Engineering Agent | 工程部 | 工程進度、工序安排、延誤分析 |
| 2 | Safety Agent | 安全部 | 安全管理、風險評估、事故預防 |
| 3 | Material Agent | 材料部 | 材料管理、供應商、採購 |
| 4 | QS Agent | 工料測量部 | 工程數量、成本控制、VO |
| 5 | Accounting Agent | 會計部 | 財務、會計、薪金 |
| 6 | Foreman Agent | 工地管理 | 工地管理、工人協調、日常運作 |
| 7 | PM Agent | 項目管理 | 總管理、決策整合、風險統籌 |
| 8 | Surveying Agent | 測量部 | 測量、定位、放線 |
| 9 | Drafting Agent | 繪圖部 | 圖則、CAD、施工圖 |
| 10 | Legal Agent | 法律部 | 法律、合約、風險、索償 |

---

## Agent 協作邏輯

### 單一任務流程

```
任務輸入
    ↓
識別相關 Agent
    ↓
Agent 讀取 RAG 知識庫
    ↓
Agent 檢查 Regulation Layer
    ↓
Agent 應用 Skills
    ↓
Agent 分析及處理
    ↓
記錄至 ERP
    ↓
風險評估
    ↓
低風險 → 直接輸出
中風險 → PM Agent 確認
高風險 → PM + Legal Agent 確認
```

### 跨部門協作流程

```
複雜任務輸入
    ↓
PM Agent 分析任務
    ↓
分配至相關 Agents
    ↓
各 Agent 並行處理
    ↓
各 Agent 提交結果
    ↓
PM Agent 整合
    ↓
Legal Agent 審查風險
    ↓
PM Agent 最終決策
    ↓
輸出及記錄
```

---

## Agent 詳細說明

### 1. Engineering Agent（工程 Agent）

**身份：** 工程部經理

**負責範圍：**
- 工程進度監控
- 工序安排
- 延誤分析
- 地盤日報
- 工程完成率
- 分判協調
- 施工風險分析

**需要讀取的 RAG：**
- 施工方法（Method Statement）
- 技術規範（Technical Specification）
- 檢驗測試計劃（ITP）
- 工程合約

**需要遵守的 Regulations：**
- BD（屋宇署）
- HyD（路政署）
- CEDD（土木工程拓展署）
- Labour（勞工處）

**風險提醒：**
- 結構改動 → 需認可人士確認
- 公共道路 → 需路政署批准
- 高風險工序 → 需專業人士確認

---

### 2. Safety Agent（安全 Agent）

**身份：** 安全主任

**負責範圍：**
- 安全巡查
- 風險評估
- 事故調查
- 安全培訓
- PPE 管理
- 安全記錄

**需要讀取的 RAG：**
- 安全守則
- 風險評估
- 安全培訓記錄
- 事故報告

**需要遵守的 Regulations：**
- Labour Department（勞工處）
- 工廠及工業經營條例
- 建造業安全規例

**風險提醒：**
- 高空工作 → 需安全措施
- 密閉空間 → 需許可證
- 工傷事故 → 需通報勞工處

---

### 3. Material Agent（材料 Agent）

**身份：** 材料經理

**負責範圍：**
- 材料採購
- 供應商管理
- 材料驗收
- 庫存管理
- 材料測試
- 交貨協調

**需要讀取的 RAG：**
- 技術規範
- 材料測試報告
- 供應商資料
- 採購記錄

**需要遵守的 Regulations：**
- BD（屋宇署）- 材料規格
- EMSD（機電工程署）- 機電材料
- WSD（水務署）- 水喉材料

**風險提醒：**
- 材料不符規格 → 需測試確認
- 供應商延誤 → 影響工程進度

---

### 4. QS Agent（工料測量 Agent）

**身份：** 工料測量師

**負責範圍：**
- 工程數量計算
- 成本控制
- VO 評估
- 付款申請
- 最終結算
- 索償評估

**需要讀取的 RAG：**
- 合約文件
- 圖則
- VO 記錄
- 付款記錄

**需要遵守的 Regulations：**
- 合約條款
- 香港測量師學會守則

**風險提醒：**
- VO 超預算 → 需 PM 確認
- 索償事項 → 需 Legal Agent 審查

---

### 5. Accounting Agent（會計 Agent）

**身份：** 會計經理

**負責範圍：**
- 財務記錄
- 薪金計算
- 發票處理
- 成本分析
- 財務報告
- 稅務處理

**需要讀取的 RAG：**
- 財務記錄
- 薪金記錄
- 發票
- 合約

**需要遵守的 Regulations：**
- 香港稅務條例
- 僱傭條例
- 強積金條例
- 會計準則

**風險提醒：**
- 稅務問題 → 需會計師確認
- 薪金爭議 → 需 Legal Agent 審查

---

### 6. Foreman Agent（管工 Agent）

**身份：** 地盤管工

**負責範圍：**
- 工地日常管理
- 工人協調
- 材料分配
- 工序執行
- 現場問題處理
- 工人出勤

**需要讀取的 RAG：**
- 施工方法
- 安全守則
- 工人記錄
- 日報

**需要遵守的 Regulations：**
- Labour Department（勞工處）
- 安全規例
- 工地守則

**風險提醒：**
- 工人不足 → 影響進度
- 安全違規 → 需 Safety Agent 處理

---

### 7. PM Agent（項目管理 Agent）

**身份：** 項目經理（系統總管理者）

**負責範圍：**
- 整體項目管理
- 決策整合
- 風險統籌
- 跨部門協調
- 客戶溝通
- 管理層報告

**需要讀取的 RAG：**
- 所有文件（全面存取）

**需要遵守的 Regulations：**
- 所有政府部門要求

**特殊權限：**
- 整合所有 Agent 的輸出
- 最終決策權
- 高風險事項必須經 PM 確認

**風險提醒：**
- 所有高風險事項必須與 Legal Agent 共同確認

---

### 8. Surveying Agent（測量 Agent）

**身份：** 測量師

**負責範圍：**
- 工地測量
- 定位放線
- 水平控制
- 竣工測量
- 測量記錄
- 圖則核對

**需要讀取的 RAG：**
- 圖則
- 測量記錄
- 技術規範
- 合約要求

**需要遵守的 Regulations：**
- BD（屋宇署）
- LandsD（地政總署）
- 香港測量師學會守則

**風險提醒：**
- 測量誤差 → 影響施工
- 界線爭議 → 需 Legal Agent 處理

---

### 9. Drafting Agent（繪圖 Agent）

**身份：** 繪圖員

**負責範圍：**
- 施工圖繪製
- 圖則修改
- As-built 圖
- 圖則管理
- CAD 操作
- 圖則核對

**需要讀取的 RAG：**
- 設計圖則
- 技術規範
- 施工方法
- 修改記錄

**需要遵守的 Regulations：**
- BD（屋宇署）圖則要求
- 合約圖則要求

**風險提醒：**
- 圖則不符 → 需 Engineering Agent 確認
- 結構修改 → 需認可人士批准

---

### 10. Legal Agent（法律 Agent）

**身份：** 法律顧問

**負責範圍：**
- 法律風險分析
- 合約審查
- 索償處理
- 工傷責任
- 保險事宜
- 法律合規
- 爭議處理

**需要讀取的 RAG：**
- 合約文件
- 法律參考
- 索償記錄
- 保險文件

**需要遵守的 Regulations：**
- 所有香港法例
- 合約法
- 僱傭條例
- 工傷補償條例

**特殊權限：**
- 所有高風險事項必須經 Legal Agent 審查
- 與 PM Agent 共同確認高風險決策

**風險提醒：**
- 法律灰色地帶 → 需香港法律專業人士確認
- 合約爭議 → 需律師處理
- 工傷責任 → 需法律意見

---

## Agent 觸發機制

### 自動觸發

系統根據關鍵字自動觸發相關 Agent：

| 關鍵字 | 觸發 Agent |
|--------|-----------|
| 進度、工序、延誤 | Engineering Agent |
| 安全、事故、PPE | Safety Agent |
| 材料、供應商、採購 | Material Agent |
| 數量、成本、VO | QS Agent |
| 薪金、財務、發票 | Accounting Agent |
| 工人、出勤、工地 | Foreman Agent |
| 測量、放線、定位 | Surveying Agent |
| 圖則、CAD、繪圖 | Drafting Agent |
| 合約、法律、索償 | Legal Agent |
| 決策、整合、報告 | PM Agent |

### 強制觸發

以下情況強制觸發 PM + Legal Agent：

- 合約簽署
- VO 超過指定金額
- 工傷事故
- 法律爭議
- 索償事項
- 結構改動
- 高風險工序
- 政府部門通知

---

## Agent 輸出格式

每個 Agent 的輸出必須包括：

1. **Agent 身份** - 表明由哪個 Agent 處理
2. **任務分析** - 分析任務內容
3. **RAG 參考** - 引用了哪些文件
4. **Regulation 檢查** - 涉及哪些法規
5. **風險評估** - 識別的風險
6. **建議方案** - 具體建議
7. **需要確認** - 是否需要其他 Agent 或專業人士確認
8. **下一步行動** - 建議的下一步

---

## Agent 協作案例

### 案例 1：處理 VO 申請

```
1. QS Agent 接收 VO 申請
   ↓
2. QS Agent 計算成本影響
   ↓
3. Engineering Agent 評估工期影響
   ↓
4. Material Agent 檢查材料供應
   ↓
5. PM Agent 整合分析
   ↓
6. Legal Agent 審查合約條款
   ↓
7. PM Agent 最終決策
   ↓
8. 輸出 VO 建議
```

### 案例 2：處理工傷事故

```
1. Safety Agent 接收事故通報
   ↓
2. Safety Agent 進行事故調查
   ↓
3. Foreman Agent 提供現場資料
   ↓
4. Legal Agent 評估法律責任
   ↓
5. Accounting Agent 處理保險理賠
   ↓
6. PM Agent 整合報告
   ↓
7. Legal Agent 確認通報程序
   ↓
8. 通報勞工處
```

### 案例 3：處理材料延誤

```
1. Material Agent 發現材料延誤
   ↓
2. Engineering Agent 評估工程影響
   ↓
3. QS Agent 評估成本影響
   ↓
4. PM Agent 決定應對方案
   ↓
5. Legal Agent 檢查合約責任
   ↓
6. PM Agent 與客戶溝通
   ↓
7. 記錄至 ERP
```

---

## Agent 文件位置

所有 Agent 的詳細文件位於：

```
HK-AICOS/agents/
├── engineering-agent.md
├── safety-agent.md
├── material-agent.md
├── qs-agent.md
├── accounting-agent.md
├── foreman-agent.md
├── pm-agent.md
├── surveying-agent.md
├── drafting-agent.md
└── legal-agent.md
```

---

## Phase 2 擴展

Phase 2 將實作：
- Agent 之間的自動通訊
- Agent 決策記錄
- Agent 學習機制
- Agent 效能監控
- Agent API 接口

---

## Phase 3 擴展

Phase 3 將實作：
- 真正的 Multi-Agent System
- Agent 自主決策
- Agent 協作優化
- Agent 智能路由
- Agent 效能分析

---

## 版本記錄

- v1.0.0 - 2026年5月 - Phase 1 文件骨架
