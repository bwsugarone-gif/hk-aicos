# 繁體中文字型說明

## 用途

HK-AICOS PDF 報告使用 **Noto Sans TC**（思源黑體繁體中文）作為唯一中文字型。
字型會強制嵌入（embed）至每份 PDF，確保在 iPhone、Android 及所有平台正確顯示。

## 目前狀態

✅ `NotoSansTC-Regular.ttf` 已放入此資料夾，為主要字型（靜態 TTF，最佳跨平台相容性）。
PDF 生成時會自動使用此字型並嵌入，**無需額外安裝**。

## 字型偵測順序

`report_generator.py` 按以下順序自動偵測可用字型（全部使用 TTFont 嵌入，不使用 CID 字型）：

1. `assets/fonts/NotoSansTC-Regular.ttf` ← **主要字型（已內置，靜態 TTF）**
2. `assets/fonts/NotoSansCJKtc-Regular.otf` ← OTF 備用
3. `assets/fonts/NotoSansTC-VF.ttf` ← Variable Font 備用
4. Streamlit Cloud / Ubuntu：`/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc`
5. Streamlit Cloud / Ubuntu：`/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc`
6. Windows 系統字型：`C:/Windows/Fonts/msjh.ttc`（微軟正黑體）
7. Windows 系統字型：`C:/Windows/Fonts/msyh.ttc`（微軟雅黑）
8. Windows 系統字型：`C:/Windows/Fonts/mingliu.ttc`
9. Windows 系統字型：`C:/Windows/Fonts/simsun.ttc`

## 字型嵌入驗證（已確認）

執行 `python verify_pdf.py` 後確認：

- ✅ FontDescriptor: YES
- ✅ FontFile embed: YES（字型資料已嵌入 PDF）
- ✅ NotoSansTC name: YES
- ✅ ToUnicode map: YES（確保手機正確解碼中文字符）

## Streamlit Cloud 部署

`packages.txt` 已加入 `fonts-noto-cjk` 作為系統備用字型。
但由於 `NotoSansTC-Regular.ttf` 已內置於 repo，Streamlit Cloud 會直接使用此檔案，
無需依賴系統字型。

## 重要：不可使用 CID 字型

`MSung-Light`、`STSong-Light` 等 CID 字型**不會嵌入 PDF**，
在 iPhone / Android / 非 CJK 系統上會顯示亂碼或方格。
本專案已全面改用 TTFont 嵌入方式。

`Helvetica`、`Times-Roman` 等英文 base font **不可用於顯示中文**。
