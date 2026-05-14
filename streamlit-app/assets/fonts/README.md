# 繁體中文字型說明

## 用途

HK-AICOS PDF 報告需要繁體中文字型才能正確顯示中文字符。
如沒有安裝字型，PDF 中文字會顯示為亂碼或方格。

## 自動偵測順序

`report_generator.py` 會按以下順序自動偵測可用字型：

1. `assets/fonts/NotoSansTC-Regular.ttf` （本資料夾）
2. `assets/fonts/NotoSansCJKtc-Regular.ttf`
3. `assets/fonts/NotoSansCJK-Regular.ttc`
4. `assets/fonts/SourceHanSansTC-Regular.otf`
5. Windows 系統字型：`C:/Windows/Fonts/msjh.ttc`（微軟正黑體）
6. Windows 系統字型：`C:/Windows/Fonts/msyh.ttc`（微軟雅黑）
7. Windows 系統字型：`C:/Windows/Fonts/simsun.ttc`（新細明體）

## 本地開發（Windows）

Windows 系統通常已內建微軟正黑體（`msjh.ttc`），
`report_generator.py` 會自動偵測並使用，**無需額外安裝字型**。

## Streamlit Cloud 部署

Streamlit Cloud 為 Linux 環境，沒有 Windows 系統字型。
需要將字型檔放入此資料夾：

### 推薦字型：Noto Sans TC（思源黑體繁體中文）

下載地址：
- https://fonts.google.com/noto/specimen/Noto+Sans+TC
- 下載 `NotoSansTC-Regular.ttf`
- 放入此資料夾：`streamlit-app/assets/fonts/NotoSansTC-Regular.ttf`

### 注意事項

- 字型檔案較大（約 5-15 MB），建議加入 `.gitignore` 避免上傳到 GitHub
- 或使用 Git LFS 管理大型字型檔案
- Streamlit Cloud 可透過 `packages.txt` 安裝系統字型（見下方）

### 透過 packages.txt 安裝（Streamlit Cloud）

在 `streamlit-app/packages.txt` 加入：

```
fonts-noto-cjk
```

然後在 `report_generator.py` 的字型候選清單加入：

```python
("NotoSansCJK", Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")),
```

## 目前狀態

如 PDF 中文顯示正常 → 字型已成功載入。
如 PDF 中文顯示為方格 → 請按上方說明安裝字型。
