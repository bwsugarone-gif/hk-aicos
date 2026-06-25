# Phase 6.6 — Client Trial Mode / Demo Workflow

讓客戶或內部團隊在**未啟用登入 / 權限**下試用 AICOS。權限、角色、多租戶與登入留待 Phase 6.2。

## 試用模式提示

- 目前為本機 / Cloud 暫存試用模式，未啟用登入或權限。
- 正式多人使用前需接入 Supabase / Google Drive / 權限。
- 資料可能因 Cloud redeploy 清空，請勿存放真實機密客戶資料。

## 試用流程（`utils/trial_mode.py`）

| 步驟 | 動作 | 頁面 |
| --- | --- | --- |
| A | 上載地盤相片 | 上載分析 |
| B | 問 AICOS 安全問題 | 問 AICOS |
| C | 上載圖紙 / PDF | 圖紙分析 |
| D | 產生 CAD/BIM 交接 | 圖紙分析 |
| E | 上載 Knowledge PDF | 知識匯入 |
| F | 去 Records 搜尋 | 記錄 |
| G | 問 AICOS 查返資料 | 問 AICOS |

## 試用進度檢查

相片分析已完成、圖紙分析已完成、CAD/BIM 交接已建立、知識來源已匯入、記錄可被搜尋、Ask AICOS 可引用已上載資料。

## Demo 試用資料（`utils/demo_project.py`）

於「發佈就緒 / 試用」頁按 **「建立 Demo 試用資料」** 才會建立示範項目 `AICOS-DEMO` 的安全樣本（工程記憶、跟進、圖紙、CAD/BIM 交接、檔案登記、知識來源）。

- 不會在每次開啟時自動建立。
- 可決定性、可重複（以固定 ID 避免重複建立）。
- 不需任何外部 API，亦不含真實機密客戶資料。

## Phase 6.2 預留（未實作）

記錄可預留下列欄位，方便日後加入權限 / 團隊 / 稽核，但本階段不強制執行：
`project_ref`、`team_id`、`role_hint`、`responsible_team`、`created_by`、`updated_by`、`visibility`、`trial_mode`。
