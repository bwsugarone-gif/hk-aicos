# Phase 6.5 — Release Gate / Cloud QA / Admin Readiness

AICOS 釋出前的自我檢查與雲端冒煙測試指引。本階段只做**就緒檢查與冒煙清單**，不實作登入、權限或多租戶存取控制（留待 Phase 6.2）。

## 釋出閘門（`utils/release_gate.py`）

`evaluate_release_gate()` 會回傳一份可決定性的 `ReleaseGateReport`：

- **核心頁面**：工作台、上載、問 AICOS、記錄、圖紙分析、知識匯入 — 檢查檔案存在並可編譯。
- **功能模組就緒**：執行儲存警告、檔案登記、知識匯入、圖紙分析、CAD/BIM 交接、記錄統一搜尋 — 檢查模組可載入且具備所需介面。
- **就緒分數**：核心檢查通過比例（0–100，決定性）。
- **阻塞項目 / 提示 / 下一步建議 / 冒煙測試流程**。
- **金鑰設定狀態**：`GEMINI_API_KEY`、`DEEPSEEK_API_KEY`、`TAVILY_API_KEY`、`AICOS_ADMIN_DIAGNOSTICS` — **只顯示已設定 / 未設定，永不顯示金鑰值**。

`pages/14_Release_Readiness.py` 以繁體中文呈現上述報告，管理員診斷收於 expander，正常介面不顯示金鑰、供應商錯誤、traceback、原始 JSON 或本機路徑。

## 雲端冒煙測試清單

1. 開啟 `/AICOS_Workspace` 工作台。
2. 開啟 `/Upload` 上載地盤相片並完成分析。
3. 於 `/Drawing_Analysis` 上載圖紙或 PDF。
4. 確認已產生 CAD/BIM 交接事項。
5. 於 `/Knowledge_Ingestion` 上載 PDF / TXT / MD。
6. 確認已產生 RAG 片段。
7. 於 `/Records` 搜尋圖紙 / 交接 / 知識 / 檔案記錄。
8. 於 `/Ask_AICOS` 提問 PDF / 圖紙 / CAD-BIM 問題並取得引用。

## 正常介面安全原則

正常介面不得顯示 API 金鑰、原始供應商錯誤、traceback、原始 JSON 或本機檔案路徑；管理員診斷只顯示「已設定 / 未設定」狀態。
