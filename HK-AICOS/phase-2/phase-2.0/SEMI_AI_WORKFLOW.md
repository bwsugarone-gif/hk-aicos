# SEMI AI WORKFLOW
## HK-AICOS 半自動 AI 工程助理工作流程

---

**版本：** v2.0.0
**日期：** 2026-05-13
**狀態：** Phase 2.0 文件骨架

---

## 流程總覽

```
┌─────────────────────────────────────────────────────────────────┐
│                  HK-AICOS Phase 2.0 半自動流程                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  [輸入層]                                                         │
│  WhatsApp / 手動輸入 / 圖片 / PDF / 地盤資料                       │
│         ↓                                                         │
│  [格式化層]                                                        │
│  辦公室人員按模板格式化輸入                                          │
│         ↓                                                         │
│  [AI 分類層]                                                       │
│  AI 識別任務類型 → 觸發對應 Agent                                   │
│         ↓                                                         │
│  [Agent 分析層]                                                    │
│  Agent 讀取 Regulations + RAG + Skills                            │
│         ↓                                                         │
│  [風險評估層]                                                       │
│  AI 評估風險等級（低/中/高/極高）                                    │
│         ↓                                                         │
│  [人工確認層]                                                       │
│  PM 確認 → Legal 確認 → 專業人士確認（視風險等級）                   │
│         ↓                                                         │
│  [輸出層]                                                          │
│  最終報告由人類 PM 簽發                                             │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## STEP 1：輸入接收

### 輸入來源

| 來源 | 格式 | 處理方式 |
|------|------|----------|
| WhatsApp 文字 | 按 `WHATSAPP_INPUT_TEMPLATE.md` | 直接複製輸入 AI |
| WhatsApp 圖片 | 地盤照片 / 文件照片 | 描述圖片內容後輸入 AI |
| PDF 文件 | 合約 / 報告 / 圖則 | 摘要關鍵內容後輸入 AI |
| 手動輸入 | 辦公室人員直接輸入 | 按模板格式輸入 AI |
| 電話記錄 | 電話溝通內容 | 整理成文字後輸入 AI |

### 輸入格式要求

每次輸入必須包括：

```
[任務類型] 安全事故 / 工程進度 / 材料問題 / VO申請 / 法律問題 / 其他
[項目編號] PROJ-XXXX
[日期時間] YYYY-MM-DD HH:MM
[地點]     地盤位置 / 樓層 / 區域
[描述]     詳細描述（盡量詳細）
[附件]     有/無（如有，描述附件內容）
[緊急程度] 緊急 / 一般 / 低優先
```

---

## STEP 2：AI Agent 分類

### 分類邏輯

AI 根據輸入內容，自動識別任務類型並觸發對應 Agent：

| 關鍵字 / 情況 | 觸發 Agent | 說明 |
|--------------|-----------|------|
| 安全、事故、受傷、PPE、高空、密閉空間 | Safety Agent | 安全相關 |
| 進度、工序、延誤、完成率、分判 | Engineering Agent | 工程進度 |
| 材料、供應商、採購、交貨、庫存 | Material Agent | 材料管理 |
| 數量、成本、VO、付款、結算、索償 | QS Agent | 工料測量 |
| 薪金、財務、發票、稅務、MPF | Accounting Agent | 財務會計 |
| 工人、出勤、工地日常、工序執行 | Foreman Agent | 工地管理 |
| 測量、放線、定位、水平、竣工 | Surveying Agent | 測量 |
| 圖則、CAD、施工圖、As-built | Drafting Agent | 繪圖 |
| 合約、法律、索償、爭議、保險 | Legal Agent | 法律 |
| 複雜任務 / 多部門 / 決策 | PM Agent | 項目管理 |

### 多 Agent 觸發

一個任務可以觸發多個 Agent：

**例子：工傷事故**
- Safety Agent（主要）
- Legal Agent（法律責任）
- Accounting Agent（保險理賠）
- PM Agent（整合報告）

**例子：VO 申請**
- QS Agent（主要）
- Engineering Agent（工期影響）
- Material Agent（材料影響）
- Legal Agent（合約條款）
- PM Agent（最終決策）

---

## STEP 3：Agent 讀取參考文件

### Agent 讀取順序

每個 Agent 處理任務時，按以下順序讀取文件：

```
1. Agent 自身 Prompt 文件
   （HK-AICOS/agents/[agent-name].md）
        ↓
2. 相關 Regulation Layer 文件
   （HK-AICOS/regulations/hk-[dept]-layer.md）
        ↓
3. 相關 Skills 文件
   （HK-AICOS/skills/[skill-name].md）
        ↓
4. 相關 SOP 文件
   （HK-AICOS/sop/[sop-name].md）
        ↓
5. RAG 文件（手動查閱）
   （HK-AICOS/rag/[category]/）
        ↓
6. AI Governance 原則
   （HK-AICOS/governance/AI_GOVERNANCE.md）
```

### Phase 2.0 RAG 使用方式

Phase 2.0 暫時以**手動查閱**方式使用 RAG：

1. AI 識別需要查閱的文件類型
2. 辦公室人員手動查閱對應 RAG 資料夾
3. 將相關內容複製提供給 AI
4. AI 整合分析

> Phase 2.5 將實作自動 RAG 查詢

---

## STEP 4：AI 生成分析報告

### 分析維度

每個 Agent 必須分析以下維度（視乎任務類型）：

| 維度 | 說明 | 適用 Agent |
|------|------|-----------|
| 工程分析 | 工序、進度、技術要求 | Engineering, Foreman |
| 安全分析 | 風險、PPE、法規要求 | Safety |
| 法規合規 | 香港法例、政府部門要求 | Legal, 所有 Agent |
| 成本分析 | 費用、VO、預算影響 | QS, Accounting |
| 工期分析 | 時間表、延誤影響 | Engineering, PM |
| 合約分析 | 合約條款、責任 | Legal, QS |
| 資源分析 | 人力、材料、設備 | Material, Foreman |

### 輸出格式

詳見 `OUTPUT_REPORT_TEMPLATE.md`

---

## STEP 5：風險評估

### 風險等級

詳見 `RISK_LEVEL_STANDARD.md`

### 快速參考

| 風險等級 | 顏色 | 處理方式 |
|----------|------|----------|
| 低風險 | 🟢 綠色 | AI 分析後直接輸出 |
| 中風險 | 🟡 黃色 | PM Agent 確認 |
| 高風險 | 🔴 紅色 | PM + Legal Agent 確認 |
| 極高風險 | ⚫ 黑色 | PM + Legal + 專業人士確認 |

---

## STEP 6：人工確認

### 確認流程

詳見 `HUMAN_APPROVAL_FLOW.md`

### 快速參考

```
低風險
  → PM 審閱 → 直接輸出

中風險
  → PM 確認 → 輸出

高風險
  → PM 確認
  → Legal Agent 審查
  → 輸出（附風險提示）

極高風險
  → PM 確認
  → Legal Agent 審查
  → 提示需要香港合資格專業人士確認
  → 人類專業人士確認後才輸出
```

---

## STEP 7：輸出最終報告

### 輸出原則

1. **AI 不簽發報告** - 所有正式報告由人類 PM 簽發
2. **AI 只提供草稿** - PM 審閱後修改及簽發
3. **風險提示必須保留** - 不可刪除 AI 識別的風險提示
4. **專業確認提示必須保留** - 不可刪除需要專業人士確認的提示

### 輸出格式

詳見 `OUTPUT_REPORT_TEMPLATE.md`

---

## 流程案例

### 案例 1：地盤安全事故

```
輸入：
[任務類型] 安全事故
[項目編號] PROJ-2026-001
[日期時間] 2026-05-13 14:30
[地點] 3樓 A區
[描述] 工人從腳手架跌落，輕傷，已送院
[緊急程度] 緊急

        ↓ STEP 2：分類

觸發：Safety Agent（主）+ Legal Agent + PM Agent

        ↓ STEP 3：讀取文件

Safety Agent 讀取：
- hk-labour-layer.md（勞工處要求）
- safety-inspection-sop.md（安全巡查 SOP）
- safety-skill.md（安全技能）

Legal Agent 讀取：
- hk-legal-layer.md（法律要求）
- 工傷補償條例（Cap. 282）

        ↓ STEP 4：分析

Safety Agent 分析：
- 事故原因分析
- 法定通報要求（24小時內通報勞工處）
- 現場保護措施
- 後續調查步驟

Legal Agent 分析：
- 工傷補償責任
- 保險通知要求
- 法律風險評估

        ↓ STEP 5：風險評估

風險等級：⚫ 極高風險（工傷事故）

        ↓ STEP 6：人工確認

PM 確認 → Legal Agent 確認 → 提示需要律師確認

        ↓ STEP 7：輸出

事故報告草稿（由 PM 簽發）
```

### 案例 2：材料延誤

```
輸入：
[任務類型] 材料問題
[項目編號] PROJ-2026-001
[日期時間] 2026-05-13 09:00
[地點] 辦公室
[描述] 鋼筋供應商通知延誤2週，影響3樓結構工程
[緊急程度] 一般

        ↓ STEP 2：分類

觸發：Material Agent（主）+ Engineering Agent + QS Agent + PM Agent

        ↓ STEP 3：讀取文件

Material Agent 讀取：
- material-control-sop.md
- material-skill.md

Engineering Agent 讀取：
- engineering-skill.md
- hk-bd-layer.md

QS Agent 讀取：
- qs-skill.md
- vo-management-sop.md

        ↓ STEP 4：分析

Material Agent：替代供應商選項
Engineering Agent：工期影響分析
QS Agent：成本影響、VO 可能性

        ↓ STEP 5：風險評估

風險等級：🟡 中風險（工期延誤）

        ↓ STEP 6：人工確認

PM 確認應對方案

        ↓ STEP 7：輸出

材料延誤分析報告 + 應對方案建議
```

---

## 注意事項

⚠️ **AI 分析僅供參考，不可取代專業判斷**

⚠️ **所有法律、結構、消防、電力、水務相關事項必須由香港合資格專業人士確認**

⚠️ **緊急安全事故必須立即通報，不可等待 AI 分析**

⚠️ **AI 不可代表公司作任何正式承諾或決定**

---

## 版本記錄

- v2.0.0 - 2026-05-13 - Phase 2.0 文件骨架建立
