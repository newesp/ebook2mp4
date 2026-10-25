# ebook2mp4

Windows 本機書籍校對與朗讀製作工具。規格為 [Spec v1.1](docs/pdf-txt-audiobook-video-spec.md)；目前實作 T01～T05：同書多份 TXT／PDF 頁碼批次、本機掃描 OCR、人工校對、外部重載與朗讀稿確認。

## 啟動

本次新版為 `dist/T05/ebook2mp4/ebook2mp4.exe`（既有版本使用中，故另放目錄）。搬移時請一起搬移整個 `dist/T05/ebook2mp4`，其中 `_internal` 包含執行環境及 OCR 引擎。一般建置預設仍輸出 `dist/ebook2mp4`。此版本尚未完成 T23 的安裝與乾淨 Windows 驗收。

開發環境使用 Python 3.11 以上且含 Tkinter，PDF 另需 `packaging/requirements-runtime.txt` 的依賴；本次驗證為 Windows 11／Python 3.14.3。安裝依賴後雙擊 `run.pyw`，或執行：

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

「新增 PDF 範圍」會在背景檢查來源並顯示總頁數與頁圖。預設整份，第一頁為 1，起訖皆包含；實際 PDF 頁次可能與印刷頁碼不同。輸入起訖後按「擷取為新批次」，可取消並保留已完成頁；未完成、空白、文字稀少或失敗頁會阻擋朗讀確認，須先核對並處理或明確略過。損毀、不可讀與密碼來源可更換，不提供解密。新 PDF 批次預設按起始頁插入，既有校對稿不被覆寫。

「逐頁原稿／頁圖」可查看每頁原始文字、方法、狀態與錯誤，頁圖保留比例並可捲動。「預覽換行整理」提供原始／整理候選切換，確認套用後可一次復原；不刪頁首頁尾、不自動處理連字號。全文或外部編輯後明示「無精確對應」，原始逐頁資料仍保留；匯出正文不插入人工頁碼標籤。取消中的視窗會等目前頁完成並保存取消結果後關閉。

PDF 預覽可選「全部強制 OCR」，針對所選頁範圍逐頁辨識；語言為繁中＋英文、簡中＋英文或英文，獨立於 TTS。變更選單可看見缺模型的下載大小，按「下載／安裝模型」顯示下載、驗證與安裝進度；只在此時連網下載官方固定版模型，不上傳頁圖或書稿。預設保存於 `%LOCALAPPDATA%/ebook2mp4/ocr/<固定版本>`；已完整安裝的模型在取消後保留，未完成下載會清除。網路、磁碟／權限或校驗失敗可重試；缺 OCR 引擎可重裝完整程式，文字層及 TXT 仍可使用。

辨識完成後逐頁比較候選文字、頁圖、方法與狀態，再按「採用為新批次」或關閉捨棄。取消擷取會中止 OCR 子程序，保留完整頁成為獨立取消批次；未完成頁、辨識失敗及空白／無文字頁阻擋朗讀確認。重做 OCR 從「新增 PDF 範圍」再選來源，會產生新候選，不覆寫既有校對稿。清晰橫排單欄為品質範圍，仍須人工校對；混合頁自動判斷、旋轉及只重試失敗頁由 T06 提供。

四步驟皆可返回，不會因切換遺失輸入。Gemini、語音及影片尚未提供；TXT 不產生 PDF 頁碼。建立及人工校對不需任何外部服務或媒體工具。

儲存失敗時請保持視窗開啟、釋放空間或修正資料夾權限後重試；前次成功資料仍可重開。關閉、建立或開啟其他專案遇到未存文字時，可選擇先存、明確捨棄或取消。遇到另一個視窗已更新的提示，請先將未存文字複製到安全位置後重新開啟。若程序意外中斷留下 `.write.lock`，確認所有該專案視窗已關閉後，再移除該鎖檔。

## 保存格式

```text
書籍專案/
  project.json                       # format_version、書籍識別、時間、各批次參照
  sources/<批次識別>.txt              # 原始位元組副本（包含 BOM 與原換行）
  sources/<批次識別>.pdf              # PDF 原始位元組副本
  batches/<批次識別>/extracted.json    # 不可變逐頁擷取原稿、方法、設定、狀態與錯誤
  batches/<批次識別>/draft-<識別>.txt  # UTF-8 校對版本
  batches/<批次識別>/reading-<識別>.txt # 不可變朗讀快照
  batches/<批次識別>/copy-<識別>.txt    # 重載時保留的未存稿
```

來源與校對稿記錄 SHA-256。只在新內容完整寫入後原子替換索引；失敗或中斷留下的未參照內容不會被當成已儲存資料。歷史稿目前保留，不做自動清理。格式與桌面選型見 [ADR 0005](docs/adr/0005-python-tkinter-and-atomic-project-manifest.md)。

## 驗證與建置

```powershell
python -m unittest discover -s tests -v
python -m compileall -q ebook2mp4 tests
python -m pip install --target .scratch/build-tools -r packaging/requirements-dev.txt
$env:PYTHONPATH = "$PWD/.scratch/build-tools"
python packaging/prepare_ocr.py
python packaging/build.py --install-tools
```

型別檢查使用 `python -m mypy ebook2mp4 --check-untyped-defs`；開發工具可安裝至專案內的隔離目錄，參見 `packaging/requirements-dev.txt`。實作告一段落後依 AGENTS.md 清理暫存與測試程序。

PDF 使用 pypdfium2／PDFium 及 Pillow，版本固定於 `packaging/requirements-runtime.txt`，封裝包含原生 PDFium DLL 與授權資料；TXT 工作流程不需要 PDF 元件。ReportLab 僅用於產生合成測試 PDF。PyInstaller 是專案內的隔離建置依賴。建置 OCR 需要 7-Zip（僅開發／建置時）；prepare_ocr.py 下載固定 SHA-256 的 UB Mannheim Tesseract 5.4.0，解壓引擎及必要 DLL 至 `.scratch/ocr-runtime`，不執行安裝程式。第三方來源與授權交付待辦見 [OCR-NOTICES](packaging/OCR-NOTICES.md)。

開發／隔離驗證可設定 `EBOOK2MP4_TESSERACT` 為引擎完整路徑、`EBOOK2MP4_OCR_HOME` 為可寫模型目錄；一般封裝版不需設定。真實 OCR 測試另設 `EBOOK2MP4_REAL_OCR_HOME` 指向含三種已驗證模型的目錄，未設定時會明列跳過，不當成真實辨識通過。`packaging/installer.iss` 供 T23 使用，本次沒有編譯或驗證安裝程式。證據見 [T04](docs/verification/T04.md) 與 [T05](docs/verification/T05.md)。
