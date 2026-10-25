# ebook2mp4

Windows 本機書籍校對與朗讀製作工具。規格為 [Spec v1.1](docs/pdf-txt-audiobook-video-spec.md)；目前實作 T01～T03：建立一本書、匯入多份 TXT 成為獨立批次、人工校對、外部重載與朗讀稿確認。

## 啟動

建置完成後，直接雙擊 `dist/ebook2mp4/ebook2mp4.exe`。搬移程式時請一起搬移整個 `dist/ebook2mp4`，其中 `_internal` 包含執行環境。此版本尚未完成 T23 的安裝與乾淨 Windows 驗收。

開發環境使用 Python 3.11 以上且含 Tkinter；本次驗證為 Windows 11／Python 3.14.3。雙擊 `run.pyw`，或執行：

```powershell
python -m ebook2mp4
```

## 書籍與 TXT 批次操作

1. 按「建立書籍專案」，輸入書名、選擇上層資料夾，再指定新的空資料夾名稱。
2. 按「新增 TXT 批次」。預覽來源文字、檔名、大小、可讀編碼、專案位置及副本所需空間後，按「確認匯入」。自動讀取 UTF-8／UTF-8 BOM／UTF-16 BOM；Big5／CP950 請在編碼下拉清單手動選擇。解碼失敗時留在預覽視窗切換編碼，不會保存失敗結果。疑似亂碼需更換編碼或核對並勾選確認後才可匯入。
3. 中間左欄為唯讀來源原文，右欄為校對稿。編輯後按「儲存校對稿」或 Ctrl+S；Ctrl+Z 可復原未存編輯。
4. 關閉程式後，按「開啟專案」選擇專案內的 `project.json`。整個專案資料夾可搬移；來源外部原檔不再是重開的必要條件。
5. 左側清單切換批次；「命名」「上移」「下移」會立即保存名稱與順序，各批校對稿互不覆蓋。切換或新增批次時若有未存文字，須先保存、明確捨棄或取消；命名及排序保留目前未存的文字。
6. 右側可搜尋完全相符的文字（Ctrl+F）、取代一處或全部取代，並以「復原」或 Ctrl+Z 撤回。字元數、以空白行分隔的非空段落數、校對版本與儲存狀態顯示在書稿下方。
7. 「匯出目前校對稿 TXT」包含未存編輯，以 UTF-8 保存到新檔名，不覆寫來源或既有檔案，也不改變專案儲存狀態。「重載外部校對稿」提供相同編碼預覽；未存編輯可保留專案內副本、明確取代或取消。重載失敗保留目前編輯。
8. 「確認朗讀稿」明確確認後，先保存目前校對稿，再建立獨立文字快照及 SHA-256。後續編輯（包含復原）或重載取消該批目前確認，舊快照與其他批次的確認保留；名稱及排序不影響確認。空稿或未處理來源異常不能確認。
9. 右側工具區支援滑鼠滾輪與捲軸。「檢視保存版本與副本」可選取歷次朗讀稿與重載保留的未存稿，唯讀查閱完整文字、版本、時間及雜湊，並選取複製。

四步驟皆可返回，不會因切換遺失輸入。未實作的 PDF／OCR、Gemini、語音及影片會列出原因；不提供模擬產出。TXT 不產生 PDF 頁碼。建立及人工校對不需任何外部服務或媒體工具。

儲存失敗時請保持視窗開啟、釋放空間或修正資料夾權限後重試；前次成功資料仍可重開。關閉、建立或開啟其他專案遇到未存文字時，可選擇先存、明確捨棄或取消。遇到另一個視窗已更新的提示，請先將未存文字複製到安全位置後重新開啟。若程序意外中斷留下 `.write.lock`，確認所有該專案視窗已關閉後，再移除該鎖檔。

## 保存格式

```text
書籍專案/
  project.json                       # format_version、書籍識別、時間、各批次參照
  sources/<批次識別>.txt              # 原始位元組副本（包含 BOM 與原換行）
  batches/<批次識別>/draft-<識別>.txt  # UTF-8 校對版本
  batches/<批次識別>/reading-<識別>.txt # 不可變朗讀快照
  batches/<批次識別>/copy-<識別>.txt    # 重載時保留的未存稿
```

來源與校對稿記錄 SHA-256。只在新內容完整寫入後原子替換索引；失敗或中斷留下的未參照內容不會被當成已儲存資料。歷史稿目前保留，不做自動清理。格式與桌面選型見 [ADR 0005](docs/adr/0005-python-tkinter-and-atomic-project-manifest.md)。

## 驗證與建置

```powershell
python -m unittest discover -s tests -v
python -m compileall -q ebook2mp4 tests
python packaging/build.py --install-tools
```

型別檢查使用 `python -m mypy ebook2mp4 --check-untyped-defs`；開發工具可安裝至專案內的隔離目錄，參見 `packaging/requirements-dev.txt`。實作告一段落後依 AGENTS.md 清理暫存與測試程序。

執行階段僅使用 Python 標準函式庫；PyInstaller 是專案內的隔離建置依賴。`packaging/installer.iss` 是供 T23 使用的 Inno Setup 安裝配方，本次沒有編譯或驗證安裝程式。完整證據與限制見 [T01](docs/verification/T01.md)、[T02](docs/verification/T02.md) 與 [T03 驗證紀錄](docs/verification/T03.md)。
