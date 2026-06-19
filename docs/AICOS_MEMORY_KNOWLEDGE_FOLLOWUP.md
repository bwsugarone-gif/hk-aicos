# AICOS Memory、Knowledge 與 Follow-up 架構

Phase 5.8 先使用本機 UTF-8 JSONL adapters，讓 AICOS 可以按工程整理記憶、知識來源及未完成跟進；目前不連接 Google Drive API 或 Supabase。

## 三種資料的分工

- **Project Memory**：記錄工程曾發生的事情，例如上載分析、Ask AICOS 問答、風險證據、使用者描述及處理狀態。
- **Knowledge Pack**：登記 SOP、官方指引、工程筆記及文件 metadata；回答時作資料來源，不代表事件已在地盤發生。
- **Follow-up**：把高風險、未確認事項或資料不足轉成可追蹤行動，保留負責角色、證據要求、狀態及更新歷史。

## 本機 runtime files

- `streamlit-app/data/aicos_memory.jsonl`
- `streamlit-app/data/knowledge_index.jsonl`
- `streamlit-app/data/followups.jsonl`

以上檔案由 `.gitignore` 的 `streamlit-app/data/*.jsonl` 規則排除，不應提交。Stores 會跳過損壞 JSONL 行；寫入前會移除常見 secret 欄位或值。

## Ask AICOS 流程

Ask AICOS 會按問題及 `project_ref` 擷取相關工程記憶、未完成跟進、Knowledge Pack、本機舊有知識及已選擇的網上來源，再交給既有回答 client。畫面只顯示命中數量、來源／限制及六段實務回答，不顯示 provider 名稱或 raw errors。啟用「儲存為記憶」後，問答摘要會寫入 Project Memory。

## 未來 adapters

- **Google Drive**：適合保存原始文件及團隊共享資料；未來 adapter 應沿用 `KnowledgeSource` metadata，不把 Drive 當成事件記憶資料庫。
- **Supabase**：適合集中式查詢、權限、關聯及多人更新；未來可替換 JSONL stores，但應保留現有 model/function contracts。

所有安全、法例及合規決定仍須核對最新香港官方文件，並由安全主任、合資格人士或負責地盤管理人員覆核。
