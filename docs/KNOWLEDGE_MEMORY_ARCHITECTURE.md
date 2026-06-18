# AICOS Knowledge & Memory Architecture

## 定位

AICOS 的 Memory／Knowledge 架構借鑑 Personal AI OS 的概念，但不直接複製其程式碼。Personal AI OS 面向個人工作流；AICOS 面向企業建築項目，必須處理項目權限、地盤風險、跟進責任、官方來源及可稽核記錄。

- **Memory**：曾發生、曾提問或需要跟進的事件與關係，例如地盤問題、問答、負責角色及狀態。
- **Knowledge**：可供搜尋和引用的材料，例如 SOP、香港官方指引、PDF、CRM 文件及未來 RAG 索引來源。

Google Drive 只是檔案儲存層，並不是「記憶大腦」。AICOS 的記憶能力來自結構化 metadata、事件、項目關係、來源引用和檢索規則。

## 共用架構概念

同一個 AICOS-native knowledge core 可日後支援建築項目、Group Training CRM、SOP、RAG 及其他企業 AI 項目：

1. **Memory registry**：記錄 project、issue、source、follow-up 和 QA memory。
2. **Knowledge/source registry**：統一登記來源、檔案位置、摘要、標籤和索引狀態。
3. **Project context**：以 `project_id` 將事件與來源限定於相關項目。
4. **Adapter pattern**：業務層依賴 `StorageAdapter`，而非依賴某一個雲端供應商。
5. **Audit-friendly relationships**：利用 related record/source IDs 保留問答、記錄和引用之間的連結。

## 本階段實作

Phase 5.7I 使用本機 append-only JSONL adapter，並預留以下 metadata：

- `google_drive_file_id`
- `google_drive_url`
- `storage_provider`
- `indexed_status`
- `extracted_text_path`

`GoogleDriveStorageAdapter` 目前只是接口 placeholder，不載入 Google SDK、不要求登入，也不會發出 API 請求。

## 未來 Google Drive 流程

1. 由獲授權的企業 connector 將原始文件上載至 Google Drive。
2. 將 Drive file ID、URL、項目、標籤及來源 metadata 儲存在本機，日後遷移至 Supabase/Postgres。
3. 抽取文件文字並保留 `extracted_text_path`，供後續 RAG indexing。
4. 官方香港來源繼續保留文件名稱、章節、條款、頁碼及 trust level；不得由模型虛構引用。
5. CRM、SOP、培訓和建築項目共用 adapter contract，但以 project、tenant 及 access policy 分隔資料。

## 儲存演進

| 階段 | 儲存與檢索方式 |
| --- | --- |
| Phase 1 | 本機 JSONL：Memory 及 Knowledge metadata foundation |
| Phase 2 | Google Drive：企業檔案儲存，metadata 仍由 AICOS 管理 |
| Phase 3 | Supabase/Postgres：多項目 metadata、權限及稽核事件 |
| Phase 4 | Vector search／RAG index：語意檢索、文件分段及來源回溯 |

## 安全與合規原則

- 不把 API keys、`.env`、上載檔案或 runtime records 納入版本控制。
- 法例和安全答案必須顯示可核實來源；未能確認章節時要明確說明。
- Google Drive integration 必須日後另行加入 authentication、tenant isolation、retention policy 和 audit logging。
- Memory context 只提供輔助資料；現場安全決定仍由合資格人士、安全主任及負責管理人員作出。
