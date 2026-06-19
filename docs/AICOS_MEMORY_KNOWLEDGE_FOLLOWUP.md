# AICOS Memory、Knowledge 與 Follow-up 架構

Phase 5.8–5.9 先使用本機 UTF-8 JSONL adapters，讓 AICOS 可以按工程整理記憶、知識來源及未完成跟進，並加入 provider health、Gemini Vision、Google Drive adapter 及本機 RAG 基礎。

## 三種資料的分工

- **Project Memory**：記錄工程曾發生的事情，例如上載分析、Ask AICOS 問答、風險證據、使用者描述及處理狀態。
- **Knowledge Pack**：登記 SOP、官方指引、工程筆記及文件 metadata；回答時作資料來源，不代表事件已在地盤發生。
- **Follow-up**：把高風險、未確認事項或資料不足轉成可追蹤行動，保留負責角色、證據要求、狀態及更新歷史。

## 本機 runtime files

- `streamlit-app/data/aicos_memory.jsonl`
- `streamlit-app/data/knowledge_index.jsonl`
- `streamlit-app/data/followups.jsonl`
- `streamlit-app/data/site_records.jsonl`
- `streamlit-app/data/rag_index.jsonl`

以上檔案由 `.gitignore` 的 `streamlit-app/data/*.jsonl` 規則排除，不應提交。Stores 會跳過損壞 JSONL 行；寫入前會移除常見 secret 欄位或值。

## Records 管理頁

Records 以「地盤記錄」、「AICOS 記憶」、「跟進事項」及「知識來源」四個分頁集中管理。使用者可篩選記錄、查看證據與標籤、更新跟進狀態及備註，以及重建本機知識／RAG 索引；更新跟進狀態會保留 history，不提供刪除操作。

## Cloud JSONL runtime warning

`runtime_storage_health.py` 會區分本機、Streamlit Cloud 類環境及未知 runtime，並檢查資料目錄是否可寫。雲端類環境會提示本機 JSONL 可能在重新部署後消失；此提示不代表資料已持久化，也不會在一般畫面顯示實體路徑。

## Provider health / LLM readiness

`provider_health.py` 只檢查能力是否已設定，不記錄或顯示 key。一般畫面只顯示文字回答、AI 視覺及網上搜尋是否啟用；Gemini、DeepSeek、Anthropic、Tavily 或 Brave 名稱只會在收合的技術狀態內顯示。沒有文字 provider 時，Ask AICOS 會保留安全的本機備用答案。

## Gemini Vision role

上載相片時，如已設定 `GEMINI_API_KEY`，Vision client 可透過輕量 REST request 擷取可見證據、分類及不確定性。Prompt 要求只回報相片可見內容；失敗時不會中止流程，而會改用現場描述、OCR evidence gate 及人工覆核。原有 Anthropic Vision 支援仍保留。

## Ask AICOS 流程

Ask AICOS 會按問題及 `project_ref` 擷取相關工程記憶、未完成跟進、Knowledge Pack、本機 SOP/RAG 片段、舊有知識及已選擇的網上來源，再交給既有回答 client。畫面只顯示命中數量、來源／限制及六段實務回答，不顯示 raw chunks、provider secrets 或 raw errors。啟用「儲存為記憶」後，問答摘要會寫入 Project Memory。

## Google Drive adapter skeleton

`google_drive_adapter.py` 定義 Drive file metadata 與 `KnowledgeSource` 的轉換邊界。未設定 `GOOGLE_DRIVE_FOLDER_ID` 時會明確回報未設定；目前不安裝 Google SDK、不執行 OAuth，也不作 live API call。

## SOP / RAG indexing pipeline

`rag_indexer.py` 把安全的 Markdown、TXT、RST、SQL 及 Python 文字分段寫入 `rag_index.jsonl`；PDF 在沒有既有 extracted text 時只索引 metadata。掃描會限制檔案大小，排除 `.git`、`.venv`、`node_modules`、`__pycache__`、uploads、runtime data、cache 及 `.env`。`rag_retriever.py` 使用簡單 keyword/BM25-like scoring 支援中英文查詢，現階段不使用 embeddings 或 vector database。

## Current limitations

- JSONL 適合單機／示範，不保證雲端重部署後仍存在，也不提供多人交易鎖定。
- Google Drive adapter 尚未連接 OAuth／service account。
- RAG 只使用關鍵字評分；PDF 不會即時抽取全文。
- Provider health 只表示已設定，並非主動探測外部服務 SLA。

## Future migration to Google Drive / Supabase / Vector DB

- **Google Drive**：適合保存原始文件及團隊共享資料；未來 adapter 應沿用 `KnowledgeSource` metadata，不把 Drive 當成事件記憶資料庫。
- **Supabase**：適合集中式查詢、權限、關聯及多人更新；未來可替換 JSONL stores，但應保留現有 model/function contracts。
- **Vector DB**：資料量及文件抽取流程穩定後，可在保留 `RagChunk`／retriever contract 下加入 embeddings、hybrid search 及版本化索引。

所有安全、法例及合規決定仍須核對最新香港官方文件，並由安全主任、合資格人士或負責地盤管理人員覆核。
