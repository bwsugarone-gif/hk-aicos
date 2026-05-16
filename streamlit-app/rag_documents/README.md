# HK-AICOS RAG 文件庫

## 用途

本資料夾為 HK-AICOS 系統的 RAG（Retrieval-Augmented Generation）文件庫基礎。
系統根據用戶問題及選擇的 Agent，自動搜尋相關文件，並將摘要注入 AI 分析提示。

## 資料夾結構

| 資料夾 | 用途 |
|--------|------|
| `regulations/` | 香港法規、條例、附屬法例（如勞工處、屋宇署、消防處等） |
| `codes_of_practice/` | 實務守則（Code of Practice） |
| `practice_notes/` | 實務備考（Practice Notes，如 BD、EMSD） |
| `technical_circulars/` | 技術通告（Technical Circulars） |
| `guidelines/` | 指引文件（Guidelines） |
| `forms_checklists/` | 表格及核查清單（Forms & Checklists） |
| `company_sop/` | 公司內部 SOP 及工作程序 |
| `project_docs/` | 項目專屬文件（合約、圖則、批文等） |

## 支援格式

- `.md` — Markdown（推薦，可直接搜尋文字）
- `.txt` — 純文字
- `.pdf` — PDF（只記錄 metadata，不做文字搜尋）

## 如何加入政府文件

1. 將文件放入對應資料夾（例如勞工處法規放入 `regulations/`）
2. 執行索引更新：
   ```bash
   python streamlit-app/utils/rag_manager.py
   ```
3. 系統會自動掃描並更新 `rag_index.json`
4. 如需補充 metadata（summary、version_date），直接編輯 `rag_index.json`

## rag_index.json 結構

```json
{
  "version": "2.5F",
  "updated_at": "2026-05-16T...",
  "documents": [
    {
      "file_name": "labour-ordinance-cap57.md",
      "file_type": "md",
      "category": "regulations",
      "source_department": "勞工處",
      "version_date": "2024-01-01",
      "uploaded_at": "2026-05-16T...",
      "language": "zh-Hant",
      "summary": "香港《僱傭條例》（第57章）主要條文摘要",
      "keywords": ["工資", "假期", "解僱", "勞工"],
      "path": "rag_documents/regulations/labour-ordinance-cap57.md"
    }
  ]
}
```

## 下一步升級至 Qdrant

Phase 3 升級路徑：

1. 安裝 `qdrant-client` 及 `sentence-transformers`
2. 在 `rag_manager.py` 的 `search()` 函數中，將 keyword match 替換為 Qdrant vector search
3. 建立 embedding pipeline，將文件向量化並存入 Qdrant collection
4. `build_rag_context()` 保持相同介面，只需更換底層搜尋引擎

現有 `rag_manager.py` 的 `search()` 函數已預留升級注釋：
```python
# Phase 3 upgrade: replace this function body with Qdrant vector search.
```

## 注意

- `project_docs/` 內的文件屬於項目機密，不應上傳至公開 repo
- 建議在 `.gitignore` 加入 `rag_documents/project_docs/*` 排除項目文件
- `rag_index.json` 可以 commit，但不包含文件全文
