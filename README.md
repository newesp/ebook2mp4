# ebook2mp4

Windows 本機書籍校對與朗讀製作工具。規格為 [Spec v1.1](docs/pdf-txt-audiobook-video-spec.md)；目前實作 T01：建立一本書、匯入第一份 UTF-8 TXT、編輯校對稿並保存重開。

## 啟動

建置完成後，直接雙擊 `dist/ebook2mp4/ebook2mp4.exe`。搬移程式時請一起搬移整個 `dist/ebook2mp4`，其中 `_internal` 包含執行環境。此版本尚未完成 T23 的安裝與乾淨 Windows 驗收。

開發環境使用 Python 3.11 以上且含 Tkinter；本次驗證為 Windows 11／Python 3.14.3。雙擊 `run.pyw`，或執行：

```powershell
python -m ebook2mp4
```

## T01 操作

1. 按「建立書籍專案」，輸入書名、選擇上層資料夾，再指定新的空資料夾名稱。
2. 按「匯入第一份 TXT」。預覽來源文字、檔名、大小、可讀編碼、專案位置及副本所需空間後，按「確認匯入」。支援 UTF-8／UTF-8 BOM，不猜測其他編碼。
3. 中間左欄為唯讀來源原文，右欄為校對稿。編輯後按「儲存校對稿」或 Ctrl+S；Ctrl+Z 可復原未存編輯。
4. 關閉程式後，按「開啟專案」選擇專案內的 `project.json`。整個專案資料夾可搬移；來源外部原檔不再是重開的必要條件。

四步驟皆可返回，不會因切換遺失輸入。未實作的 PDF／OCR、Gemini、朗讀確認、語音及影片會列出原因；不提供模擬產出。TXT 不產生 PDF 頁碼。建立及人工校對不需任何外部服務或媒體工具。

儲存失敗時請保持視窗開啟、釋放空間或修正資料夾權限後重試；前次成功資料仍可重開。關閉、建立或開啟其他專案遇到未存文字時，可選擇先存、明確捨棄或取消。遇到另一個視窗已更新的提示，請先將未存文字複製到安全位置後重新開啟。若程序意外中斷留下 `.write.lock`，確認所有該專案視窗已關閉後，再移除該鎖檔。

## 保存格式

```text
書籍專案/
  project.json                       # format_version、書籍識別、時間、各批次參照
  sources/<批次識別>.txt              # 原始位元組副本（包含 BOM 與原換行）
  batches/<批次識別>/draft-<識別>.txt  # UTF-8 校對版本
```

來源與校對稿記錄 SHA-256。只在新內容完整寫入後原子替換索引；失敗或中斷留下的未參照內容不會被當成已儲存資料。歷史稿目前保留，不做自動清理。格式與桌面選型見 [ADR 0005](docs/adr/0005-python-tkinter-and-atomic-project-manifest.md)。

## 驗證與建置

```powershell
python -m unittest discover -s tests -v
python -m compileall -q ebook2mp4 tests
python packaging/build.py --install-tools
```

執行階段僅使用 Python 標準函式庫；PyInstaller 是專案內的隔離建置依賴。`packaging/installer.iss` 是供 T23 使用的 Inno Setup 安裝配方，本次沒有編譯或驗證安裝程式。完整證據與限制見 [T01 驗證紀錄](docs/verification/T01.md)。
