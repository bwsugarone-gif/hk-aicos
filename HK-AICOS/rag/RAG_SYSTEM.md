# HK-AICOS RAG SYSTEM
## RAG Knowledge Layer - 企業級文件骨架

---

## 系統用途

RAG (Retrieval-Augmented Generation) 系統為 HK-AICOS 的**知識層**，儲存及管理所有工程相關文件。

### 核心功能

1. **文件儲存** - 儲存原始 PDF / Word / Excel 文件
2. **Metadata 管理** - 記錄文件資訊至 Database
3. **Vector Database** - 將文件內容轉換為 Vector（Phase 2）
4. **Agent 查詢** - Agent 根據任務查詢相關文件
5. **Context 提供** - 將相關內容提供給 Agent

---

## 重要原則

> ⚠️ **PDF / 公司 Reference / SOP / Specification 不應放在 agents/ 資料夾**
>
> - 原始文件放 `rag/` 對應資料夾
> - 文件 metadata 將來放 database
> - 文件內容將來做 vector database
> - Agent 透過 RAG 系統查詢文件，而非直接讀取

---

## RAG 資料夾結構

```
HK-AICOS/rag/
├── RAG_SYSTEM.md                    ← 本文件
├── company-reference/               ← 公司參考文件
│   └── README.md
├── technical-specification/         ← 技術規範
│   └── README.md
├── quality-management/              ← 質量管理文件
│   └── README.md
├── method-statement/                ← 施工方法
│   └── README.md
├── inspection-test-plan/            ← 檢驗測試計劃
│   └── README.md
├── contract-reference/              ← 合約參考
│   └── README.md
└── legal-reference/                 ← 法律參考
    └── README.md
```

---

## 各資料夾用途

### 1. company-reference/

**用途：** 公司內部參考文件

**儲存文件類型：**
- 公司質量管理手冊
- 公司 SOP
- 公司工作程序
- 公司質量指引
- 公司內部通知
- 公司管理文件

**使用 Agent：**
- 所有 Agent

**Phase 2 處理：**
- 掃描所有 PDF 文件
- 提取文字內容
- 建立 Vector Embeddings
- 儲存至 Vector Database

---

### 2. technical-specification/

**用途：** 技術規範文件

**儲存文件類型：**
- 工程技術規範
- 材料規格
- 施工標準
- 測試標準
- 政府部門技術要求
- 國際標準（如適用）

**使用 Agent：**
- Engineering Agent
- Material Agent
- QS Agent
- Surveying Agent

**Phase 2 處理：**
- 按工程類型分類
- 建立規格索引
- Vector Database 儲存

---

### 3. quality-management/

**用途：** 質量管理文件

**儲存文件類型：**
- 質量管理計劃
- 檢驗程序
- 測試程序
- 質量記錄表格
- 質量改善措施
- 內部審核記錄

**使用 Agent：**
- Engineering Agent
- Safety Agent
- PM Agent

**Phase 2 處理：**
- 按工程階段分類
- 建立質量檢查清單
- Vector Database 儲存

---

### 4. method-statement/

**用途：** 施工方法文件

**儲存文件類型：**
- 施工方法說明書
- 工序說明
- 安全措施
- 施工步驟
- 風險評估
- 應急措施

**使用 Agent：**
- Engineering Agent
- Safety Agent
- Foreman Agent

**Phase 2 處理：**
- 按工序類型分類
- 建立施工步驟索引
- Vector Database 儲存

---

### 5. inspection-test-plan/

**用途：** 檢驗測試計劃文件

**儲存文件類型：**
- ITP (Inspection and Test Plan)
- 檢驗程序
- 測試程序
- 檢驗記錄表格
- 測試標準
- 驗收標準

**使用 Agent：**
- Engineering Agent
- Material Agent
- QS Agent

**Phase 2 處理：**
- 按工序分類
- 建立檢驗點索引
- Vector Database 儲存

---

### 6. contract-reference/

**用途：** 合約參考文件

**儲存文件類型：**
- 工程合約
- 分判合約
- 合約條款
- 合約附件
- VO 記錄
- 合約通訊

**使用 Agent：**
- PM Agent
- Legal Agent
- QS Agent
- Accounting Agent

**Phase 2 處理：**
- 按工程分類
- 建立合約條款索引
- Vector Database 儲存
- **注意保密性**

---

### 7. legal-reference/

**用途：** 法律參考文件

**儲存文件類型：**
- 香港法例
- 政府部門指引
- 法律意見書
- 判例參考
- 保險文件
- 法律通知

**使用 Agent：**
- Legal Agent
- PM Agent
- Safety Agent

**Phase 2 處理：**
- 按法例分類
- 建立法律條文索引
- Vector Database 儲存
- **注意保密性**

---

## RAG 使用流程

### Phase 1（現階段）

```
1. 原始文件放入對應資料夾
2. 手動記錄文件清單
3. Agent 手動參考文件位置
```

### Phase 2（未來）

```
1. 原始文件放入對應資料夾
    ↓
2. 系統自動掃描文件
    ↓
3. 提取文字內容
    ↓
4. 建立 Vector Embeddings
    ↓
5. 儲存至 Vector Database
    ↓
6. 記錄 Metadata 至 Database
    ↓
7. Agent 查詢時自動檢索
```

### Phase 3（未來）

```
Agent 任務輸入
    ↓
Agent 分析任務
    ↓
Agent 自動查詢 RAG
    ↓
RAG 返回相關文件片段
    ↓
Agent 整合資訊
    ↓
Agent 輸出結果
```

---

## 支援技術（Phase 2）

### Vector Database 選項

| 技術 | 優點 | 缺點 |
|------|------|------|
| Qdrant | 高效能、開源 | 需要自行架設 |
| Chroma | 簡單易用、開源 | 功能較少 |
| Supabase pgvector | 整合 PostgreSQL | 需要 Supabase |
| Pinecone | 雲端服務、易用 | 收費 |
| Weaviate | 功能強大 | 複雜 |

### Embeddings 選項

| 技術 | 優點 | 缺點 |
|------|------|------|
| OpenAI Embeddings | 高質量 | 收費、需 API |
| Anthropic Claude | 高質量 | 收費、需 API |
| Sentence Transformers | 開源、免費 | 需要自行運行 |
| Cohere | 高質量 | 收費 |

---

## 文件 Metadata 結構（Phase 2）

每個文件的 Metadata 應包括：

```json
{
  "file_id": "唯一識別碼",
  "file_name": "文件名稱",
  "file_type": "PDF / Word / Excel",
  "category": "company-reference / technical-specification / ...",
  "upload_date": "上傳日期",
  "project": "相關工程",
  "tags": ["標籤1", "標籤2"],
  "description": "文件描述",
  "version": "版本",
  "status": "active / archived",
  "access_level": "public / confidential / restricted",
  "related_agents": ["Engineering Agent", "Safety Agent"],
  "related_regulations": ["BD", "EMSD"]
}
```

---

## 文件管理

### 文件命名規範

建議格式：`[類別]_[工程]_[文件名稱]_[版本]_[日期].pdf`

例如：
- `MS_Project-A_Concrete-Pouring_v1.0_20260513.pdf`
- `ITP_Project-B_Rebar-Inspection_v2.1_20260513.pdf`
- `Contract_Project-C_Main-Contract_v1.0_20260101.pdf`

### 文件版本控制

- 每次更新文件，版本號碼遞增
- 保留舊版本文件（標示為 archived）
- 記錄版本更新原因

### 文件存取權限

| 權限等級 | 說明 | 適用文件 |
|---------|------|---------|
| Public | 所有 Agent 可存取 | 一般技術文件 |
| Confidential | 特定 Agent 可存取 | 合約、財務文件 |
| Restricted | 需要特別批准 | 法律意見、敏感文件 |

---

## 風險提醒

### 保密性

- 合約文件涉及商業機密
- 法律文件涉及法律特權
- 財務文件涉及公司機密
- 必須設定適當存取權限

### 準確性

- 確保文件為最新版本
- 過時文件必須標示
- 定期檢查文件有效性

### 合規性

- 確保文件符合法規要求
- 保留文件符合法定期限
- 文件處理符合私隱條例

---

## 未來擴展方向

### Phase 2
- 建立 Vector Database
- 自動文件掃描及索引
- 自動 Metadata 提取
- Agent 自動查詢 RAG

### Phase 3
- AI 自動文件分類
- AI 自動文件摘要
- AI 自動文件更新提醒
- 多語言文件支援

---

## 版本記錄

- v1.0.0 - 2026年5月 - Phase 1 文件骨架
