# HK-AICOS MASTER SYSTEM
## 香港 AI 建築工程作業系統 - 總系統架構

---

## 系統總目標

建立一套企業級 AI 建築工程作業系統，整合：
- 香港工程知識
- 香港法規要求
- Multi-Agent 協作
- RAG 知識庫
- ERP 系統
- Memory 學習
- Workflow 自動化
- AI Decision System

目標：提升工程效率、降低風險、確保合規。

---

## 系統總架構

```
┌─────────────────────────────────────────────────────────────┐
│                     HK-AICOS 總系統                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Multi-Agent  │  │ Regulation   │  │ RAG Knowledge│      │
│  │   System     │←→│    Layer     │←→│    Layer     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         ↕                  ↕                  ↕              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ ERP/Database │  │   Memory     │  │   Workflow   │      │
│  │    Layer     │←→│    Layer     │←→│    Layer     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         ↕                  ↕                  ↕              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Dashboard   │  │   Contract   │  │ AI Governance│      │
│  │    Layer     │  │    Layer     │  │    Layer     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Multi-Agent 協作邏輯

### 10 個核心 Agent

1. **Engineering Agent** - 工程進度、工序安排
2. **Safety Agent** - 安全管理、風險評估
3. **Material Agent** - 材料管理、供應商
4. **QS Agent** - 工程數量、成本控制
5. **Accounting Agent** - 會計、財務
6. **Foreman Agent** - 工地管理、工人協調
7. **PM Agent** - 項目總管理、決策整合
8. **Surveying Agent** - 測量、定位
9. **Drafting Agent** - 圖則、CAD
10. **Legal Agent** - 法律、合約、風險

### Agent 協作流程

```
輸入（WhatsApp / Telegram / Form / Email）
    ↓
相關 Agent 接收
    ↓
讀取 RAG 知識庫
    ↓
檢查 Regulation Layer
    ↓
分析及處理
    ↓
記錄至 ERP / Database
    ↓
高風險事項 → PM Agent + Legal Agent 確認
    ↓
輸出（Dashboard / Report / 通知）
```

---

## 香港政府部門法規 Layer

所有 Agent 必須參考以下香港政府部門要求：

| 部門 | 英文簡稱 | 負責範圍 |
|------|----------|----------|
| 機電工程署 | EMSD | 電力、機電、升降機、冷氣 |
| 屋宇署 | BD | 結構、建築物、小型工程 |
| 環保署 | EPD | 環境、噪音、廢物 |
| 勞工處 | Labour Dept | 勞工安全、工傷 |
| 消防處 | FSD | 消防系統、火警 |
| 水務署 | WSD | 食水、水管 |
| 地政總署 | LandsD | 土地、地契 |
| 路政署 | HyD | 道路、掘路 |
| 土木工程拓展署 | CEDD | 土木工程、斜坡 |
| 渠務署 | DSD | 渠務、排水 |
| 運輸署 | TD | 交通、運輸 |
| 法律層 | Legal Layer | 香港法例、合約 |

### 法規檢查流程

每個 Agent 處理任務時：
1. 自動識別涉及哪些政府部門
2. 讀取相關 Regulation Layer 文件
3. 分析合規要求
4. 標示風險等級
5. 高風險事項提交 PM + Legal Agent

---

## RAG Knowledge Layer

### RAG 文件庫結構

```
rag/
├── company-reference/        ← 公司參考文件
├── technical-specification/  ← 技術規範
├── quality-management/       ← 質量管理文件
├── method-statement/         ← 施工方法
├── inspection-test-plan/     ← 檢驗測試計劃
├── contract-reference/       ← 合約參考
└── legal-reference/          ← 法律參考
```

### RAG 使用邏輯

1. **文件儲存** - 原始 PDF / Word 文件放入對應資料夾
2. **Metadata 記錄** - 文件資訊記錄至 Database
3. **Vector Database** - 文件內容轉換為 Vector（Phase 2）
4. **Agent 查詢** - Agent 根據任務查詢相關文件
5. **Context 提供** - 將相關內容提供給 Agent

### 支援技術（Phase 2）

- Qdrant
- Chroma
- Supabase pgvector
- OpenAI Embeddings
- Anthropic Claude

---

## ERP / Database Layer

### 核心資料表（Phase 2 設計）

| 資料表 | 用途 |
|--------|------|
| projects | 工程項目 |
| workers | 工人資料 |
| attendance | 出勤記錄 |
| payroll | 薪金 |
| materials | 材料 |
| suppliers | 供應商 |
| quotations | 報價 |
| invoices | 發票 |
| contracts | 合約 |
| vo_records | VO 記錄 |
| safety_records | 安全記錄 |
| inspection_records | 檢驗記錄 |
| drawings | 圖則 |
| legal_reviews | 法律審查 |

### Database 功能

- 記錄所有工程數據
- 支援 Agent 查詢
- 提供 Dashboard 數據
- 記錄 AI 決策歷史
- 支援 Memory Layer 學習

---

## Memory Layer

### 學習內容

系統會學習及記錄：

1. **歷史工程案例**
   - 成功案例
   - 失敗案例
   - 延誤原因
   - 成本超支原因

2. **供應商表現**
   - 準時交貨率
   - 質量問題
   - 價格競爭力
   - 合作問題

3. **工人表現**
   - 出勤率
   - 工作質量
   - 安全記錄
   - 技能水平

4. **常見安全問題**
   - 高風險工序
   - 常見違規
   - 事故類型
   - 預防措施

5. **工程延誤原因**
   - 天氣影響
   - 材料延誤
   - 人手不足
   - 設計變更

6. **法律及合約風險案例**
   - 合約爭議
   - 索償案例
   - 法律問題
   - 保險理賠

### Memory 應用

- 提供 Agent 決策參考
- 預測風險
- 優化流程
- 改善效率

---

## Workflow Layer

### 標準工作流程

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

### Workflow 自動化（Phase 3）

- 自動分配任務
- 自動提醒
- 自動生成報告
- 自動風險預警
- 自動合規檢查

---

## Dashboard Layer

### Dashboard 功能（Phase 3）

1. **工程總覽**
   - 進度
   - 成本
   - 人力
   - 材料

2. **風險監控**
   - 安全風險
   - 工期風險
   - 成本風險
   - 法律風險

3. **合規狀態**
   - 政府部門要求
   - 法例合規
   - 牌照狀態
   - 檢驗記錄

4. **AI 決策記錄**
   - Agent 建議
   - 決策歷史
   - 風險評估
   - 專業確認

---

## AI Decision Layer

### 決策邏輯

1. **數據收集** - 從 ERP、RAG、Memory 收集數據
2. **風險分析** - 分析各類風險
3. **法規檢查** - 檢查合規要求
4. **Agent 協作** - 多 Agent 協同分析
5. **PM 整合** - PM Agent 整合建議
6. **Legal 審查** - Legal Agent 審查法律風險
7. **決策輸出** - 提供決策建議
8. **專業確認** - 高風險事項提示專業人士確認

### 決策分級

| 風險等級 | 處理方式 |
|----------|----------|
| 低風險 | Agent 自動處理 |
| 中風險 | PM Agent 確認 |
| 高風險 | PM + Legal Agent 確認 |
| 極高風險 | PM + Legal + 專業人士確認 |

---

## Legal Agent 的角色

Legal Agent 係系統中的關鍵角色，負責：

### 主要職責

1. **法律風險分析**
   - 香港法例合規
   - 合約條款審查
   - 法律責任評估

2. **合約管理**
   - 合約審查
   - 分判合約
   - VO 法律影響
   - 索償風險

3. **工傷及保險**
   - 工傷責任
   - 保險覆蓋
   - 理賠程序

4. **合規監控**
   - 法定簽署
   - 牌照要求
   - 政府部門要求

### Legal Agent 觸發條件

以下情況必須觸發 Legal Agent：

- 合約簽署
- VO 超過指定金額
- 工傷事故
- 法律爭議
- 政府部門通知
- 索償事項
- 保險理賠
- 分判合約

---

## 高風險事項處理

### 必須由 PM Agent + Legal Agent 確認的事項

1. **法律責任**
   - 合約爭議
   - 法律訴訟
   - 工傷責任

2. **結構安全**
   - 結構改動
   - 承重牆
   - 樓板加固

3. **消防系統**
   - 消防設計
   - 火警系統
   - 逃生路線

4. **電力工程**
   - 高壓電力
   - 配電系統
   - 臨時電力

5. **水務工程**
   - 食水系統
   - 水管安裝
   - 水質測試

6. **公共道路**
   - 掘路工程
   - 交通管理
   - 路政署申請

7. **高風險工序**
   - 高空工作
   - 密閉空間
   - 吊運作業
   - 深開挖

### 專業人士確認要求

以下事項必須提示「需要由香港合資格專業人士確認」：

- 認可人士（AP）- 結構、建築
- 註冊結構工程師（RSE）- 結構設計
- 註冊電業工程人員（REW）- 電力工程
- 註冊消防工程師 - 消防系統
- 註冊測量師 - 測量、工料
- 法律專業人士 - 法律、合約

---

## AI Governance Layer

### 核心原則

所有 AI Agent 必須：

1. **根據香港法例運作**
   - 不可違反香港法例
   - 不可提供違法建議
   - 主動識別法律風險

2. **根據香港工程制度執行**
   - 遵守工程專業守則
   - 尊重專業人士法定責任
   - 不可取代持牌專業人士

3. **根據香港政府部門要求分析**
   - 識別涉及政府部門
   - 檢查合規要求
   - 提示申請程序

4. **主動分析風險**
   - 法律風險
   - 安全責任
   - 工程責任
   - 合規風險
   - 牌照風險
   - 合約風險

5. **透明及可追溯**
   - 記錄所有決策
   - 記錄風險評估
   - 記錄專業確認
   - 可審計

### 禁止事項

AI Agent **不可**：

- 提供違反香港法例的建議
- 提供危險施工建議
- 忽略安全責任
- 忽略合約風險
- 假設缺失資料
- 取代專業人士法定責任

### 缺資料處理

當資料不足時，Agent 必須：

1. 明確列出缺失資料
2. 說明為何需要該資料
3. 建議如何取得資料
4. 不可假設或猜測

---

## 系統擴展方向

### Phase 2（待開始）

- RAG ingestion pipeline
- Database schema 設計
- Workflow automation
- API connection
- MCP integration
- Vector database 建立

### Phase 3（待開始）

- Multi-Agent System 實作
- Dashboard 開發
- Memory learning 實作
- AI Decision System 實作
- ERP integration
- Mobile App

---

## 版本記錄

- v1.0.0 - 2026年5月 - Phase 1 文件骨架
