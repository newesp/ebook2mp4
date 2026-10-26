# 實作交接

## 目前：T01～T07 已完成

2026-10-26，T07「Gemini 設定、指定範圍校對與差異採用」已實作。起點 `3226d3f`，主要實作 `7eae065`，審查修正 `acbd711`；最終文件提交見 `git log -1`。目前 master，無遠端推送。

正式新版 **`dist/T07/ebook2mp4/ebook2mp4.exe`**，SHA-256 `44A88303F30A45A8211F3BD1FA41D005952CF473A369D69D79F54890803C9828`；一起搬移整個 ebook2mp4 目錄。完整套件 **72／72 通過，206.612 秒，無跳過**，包含真實三語 OCR 及原指定 9 頁書稿；mypy 9 個來源檔案與 compileall 通過。雙軸審查原問題皆由原審查者確認解除。詳見 [T07 驗證](verification/T07.md)、[審查](verification/T07-code-review.md)、[清理](verification/T07-cleanup.json)。

本次清除 **246,553,970 bytes（約 235.1 MiB）**，隔離依賴與測試模型副本已刪；重跑請重新準備。正式成品、需求、outputs 及既有使用者 OCR 模型保留。最終本次測試／OCR／封裝程序 **0**，桌面自動化 kernel 已重設；封裝檔案以獨占讀取開啟後釋放，確認沒有殘留占用。桌面另有使用者操作，因此封裝驗證收尾只停止本次空白測試程序，未繼續搶占桌面。

下一張 **T08 — Gemini 長稿分段、取消與部分失敗續作**，票稿 `.scratch/pdf-txt-audiobook-video/v1.1/issues/08-gemini-long-draft-resume.md`。**建議開新 session 接 T08**，先讀 AGENTS、GLOSSARY、docs/adr、Spec v1.1、T07 驗證及 T08 票稿；沿用已核定 ProjectWorkflow／真實 Tk 測試邊界。TTS、音訊／影片及 T23 安裝仍未完成。

T07 入口及延伸注意：

- `gemini_settings`／`save_gemini_settings(key, model)`／`test_gemini_connection`。Windows DPAPI current-user 加密的金鑰在 `%LOCALAPPDATA%/ebook2mp4/gemini.json`，不進書籍專案，也支援 `GEMINI_API_KEY`。設定錯誤可由設定視窗重新保存；不要在日誌或文件記錄金鑰。
- 預設 `gemini-3.8-flash` 真實合成短文連線及指定範圍校對通過；舊 `gemini-2.5-flash` 雖列在服務清單，實際生成 404，不可僅靠列出模型宣稱可用。UI 可調模型 ID；不自動切換使用者模型。
- `gemini_scope(batch_id, start=0, end=None)` → `start_gemini_review(...)` → job `state/cancel/wait` → `finish_gemini_review(job)`；範圍為 Python 字元半開區間，UI 顯示 1-based 含尾。只傳所選文字與校對規則，未傳使用者書稿做真實驗證。T07 單次請求，需完整段落 JSON／STOP 才成功；T08 再做分請求、部分保存及重試，不把現有原子完整回應誤當長稿續作。
- `gemini_reviews(batch_id)` 回傳來源版本／範圍／模型、原文／候選／疑點、逐段決定及 before/expected/history 參照，另推導 stale。review JSON 每次不可變保存，索引保留原記錄順序，避免操作較舊候選後跳到另一筆。重開驗證內容檔及歷史 SHA-256；相對路徑可搬移。
- `decide_gemini(batch_id, review_id, paragraph, decision)`，decision 為 accepted/rejected，paragraph=None 只採用待確認段落，不覆蓋已拒絕段。`undo_gemini` 撤回本次全部採用。以 before 重建，保留選外與分隔符；先比對 expected 參照及 revision，舊候選不可覆蓋新稿。UI 未存人工稿也阻擋套用；採用改稿失效該批朗讀確認及 PDF mapping，舊快照保留。
- 請求在背景，取消不套用晚到結果，關閉等待停止與保存。若保存因跨視窗變更／原批移除而永久失敗，關閉須可明確捨棄；`discard_gemini_review(job)` 只釋放所屬已停止工作。不要移除該出口。新增非同步流程保留 after token 取消與連線 finally.close 規則。
- Tk UI 差異採可縮放獨立視窗、原文／候選左右等寬、字詞差異底色、疑點及分列操作；主視窗右側工具向下捲動可見 Gemini。已驗最小 1040×640 主窗／740×570 差異窗。封裝版啟動通過，原生選檔後完整校對路徑尚待人工補驗；其他 DPI／輔助工具與 T23 乾淨機安裝亦待驗。

## 目前：T01～T06 已完成

2026-10-26，T06「混合 PDF 自動辨識、異常頁確認與旋轉重試」已實作。起點 `2ae4c03`，實作 `fbb225f`、審查修正 `a2a24f9`，最終文件提交見 `git log -1`。目前仍為 master，沒有設定或推送遠端。

正式新版 **`dist/T06/ebook2mp4/ebook2mp4.exe`**，SHA-256 `9D9F1AF9C4882A2427BB174CB0755A2077EDAA2F05E6F53073706DD94F3BA5A5`；請一起搬移整個 ebook2mp4 目錄。最終完整套件 **62／62 通過，151.130 秒，無跳過**，包含三語真實 OCR 及指定 9 頁書稿；mypy 7 個來源檔案及語法編譯通過。雙軸審查原三項 P2 均由原審查者確認解除，Standards／Spec 零項未解決。詳見 [T06 驗證](verification/T06.md)、[審查](verification/T06-code-review.md)。

下一張是 **T07 — Gemini 設定、指定範圍校對與差異採用**，票稿 `.scratch/pdf-txt-audiobook-video/v1.1/issues/07-gemini-settings-review.md`。**建議開新 session 再接 T07**。先讀 AGENTS、GLOSSARY、docs/adr、Spec v1.1、T07 票稿及本次驗證；沿用已核定的 ProjectWorkflow／真實 Tk 測試邊界。Gemini、TTS、音訊／影片及 T23 安裝仍未完成。

T06 入口與保存規則：

- `start_pdf_extraction(..., mode='auto', language=...)` 逐頁優先文字層，沒有可用文字才 OCR。公開 API 的預設仍是舊文字層，UI 預設自動。所有模式結果不足 20 個字母／數字／中文字元或含異常字元會列待檢查；僅頁碼不得報正文完整。這是保守啟發式，不保證判別所有圖片正文。
- `pdf_source_preview(batch_id)` 驗證並讀取專案內 PDF 副本；來源移走不影響重做。UI 背景讀取缺檔／損壞來源，顯示可行錯誤並可關閉釋放 grab／executor。
- `start_pdf_retry(batch_id, pages=[...], language=..., rotation=0|90|180|270)` 或 `failed_only=True`。只執行目標頁，順時針旋轉，未選頁保留原逐頁狀態；`job.numbers` 為本次實際處理頁次。取消後只補齊目標未完成頁，成功與失敗進度保留。
- `pdf_extraction_pages(job)` 提供整個批次範圍候選；`finish_pdf_extraction(job, accepted_pages=[...])` 針對重試逐頁採用，未採用／非目標頁沿用原逐頁原稿。每次採用建立新批次，**不搬入原批全文人工校對**；原校對稿及朗讀快照保持不變。原批已有人工改稿而 mapping_valid=False 時，其 `resolved` 異常在重建原稿的新批重新列 pending，避免人工補文消失卻通過確認；明確 `skipped` 可沿用。新採用異常頁重新確認，批次層級異常也保留。
- UI「逐頁原稿／頁圖」可選頁、旋轉／本頁 OCR／只重試失敗，切換原逐頁原稿與原批校對全文比較，勾選是否採用本頁候選；範圍／OCR 設定可展開，修改範圍／語言／模式後另建候選。採用前保護未存編輯；取消儲存提示仍保留編輯與候選。明確保留／略過來源異常後才可確認相關朗讀稿；略過不會自動刪文。
- 自動／OCR 取消按鈕先取消並保留候選供比較，必須明確採用才保存取消批次；再次關閉可捨棄候選。舊文字層匯入仍沿用 T04 直接發布新批次的行為。

正式封裝已用 Windows 原生選檔走過開啟合成專案→對照→包內 OCR→候選→明確採用→關閉及重開驗證，另有 1040×640／740×570 最小視窗截圖。原設定區擠壓圖文區，已改成收合設定及分列控制。其他 DPI、輔助工具及乾淨機安裝仍待驗收。

本次清除 **246,358,618 bytes（約 234.9 MiB）** 的測試模型副本、工具、建置資料、合成專案、測試資料及快取；正式成品、指定書稿 TXT、使用者既有模型、需求及最終證據保留。最終本次測試／OCR／建置／封裝程序 **0**，沒有未釋放資源；見 [清理紀錄](verification/T06-cleanup.json)。隔離依賴已清除，重跑請依驗證文件重新準備；目前版本的建置重用了已驗證 T05-ui 引擎／DLL，無需重新執行引擎安裝程式。

## T05 歷史交接（下方狀態以當時為準）

2026-10-26 UI 追加：基線 `75d37ea` 之後新增 `ProjectWorkflow.remove_pdf_batch` 及「移除 PDF 文件」，並將「新增 PDF 範圍」改為「新增 PDF 文件」。移除僅作用於所選 PDF 批次，確認後原子發布索引；取消或寫入失敗保留未存編輯與清單。外部原始 PDF、其他批次、匯出及專案內歷史檔案保留。最新成品改為 **`dist/T05-ui/ebook2mp4/ebook2mp4.exe`**，SHA-256 `A107E1E7D7A32A5DD35862F7624BDD4D5F740E955D1C169C350309D34CDE71BE`。完整套件 53 案例：48 通過、5 個需另設 OCR 環境的案例跳過，無失敗；mypy／編譯／重建及實際啟動通過，1040×640 真實 Tk 及確認提示可見。詳見 [PDF 文件操作驗證](verification/PDF-file-actions.md)，原 T05 的實際書稿輸出仍保留。本次追加驗證與建置暫存已於收尾清除，既有使用者程序不動；後續提交可由 git log -1 查看。

T01～T05 已實作。T05 起點 `df85a02`、主要實作 `09600e6`；模型狀態審查修正、實際書稿基本測試與最終交接見後續提交（`git log -1`）。目前分支 master，未設定或推送遠端。歷史 T04 詳見 docs/verification/T04.md。

當時下一張為 **T06 — 混合 PDF 自動辨識、異常頁確認與旋轉重試**，票稿 `.scratch/pdf-txt-audiobook-video/v1.1/issues/06-mixed-pdf-anomalies-retry.md`；現已完成，請以上方目前狀態為準。

主要測試邊界沿用已核定的 ProjectWorkflow 與真實 Tk UI。格式 v1 支援同書多 TXT／PDF 批次，來源、不可變逐頁原稿、校對版本、朗讀快照及重載副本各自保存並帶 SHA-256。任何人工編輯、改稿與重載取消該批目前朗讀確認；舊快照及其他批次不變。多視窗索引變更須重開，寫入鎖及原子發布規則沿用 T01～T04。

公開 PDF 流程：inspect_pdf → preview_pdf_page → start_pdf_extraction → pdf_extraction_pages → finish_pdf_extraction。start 新增 mode='text-layer'（預設）或 'ocr'，language='繁中＋英文'／'簡中＋英文'／'英文'；設定獨立於 TTS。每次 finish 建立新批次，不覆寫既有校對稿。pdf_extraction_pages 只接受所屬已停止候選，統一補齊取消頁，供 UI 比較及保存共用。PdfExtraction 的 pages 仍只回傳已完成頁副本，提供 status、cancel、wait。保存失敗保留候選供重試；discard_pdf_extraction 釋放已停止候選。

OCR 完成先顯示候選圖文對照，再明確「採用為新批次」或關閉捨棄；取消擷取並保留完整頁會建立取消批次。method 支援 text-layer／ocr；逐頁設定保留語言代碼、模型 commit、引擎、300 DPI、25M pixels 上限與 psm=6。狀態 success／pending／failed／cancelled，異常沿用 source_issues、resolve_source_issue、confirmation_blockers。全文編輯使 mapping_valid=False，不自動恢復；原始逐頁資料不改寫，正文不加人工頁碼標籤。

模型公開入口 ocr_models(language)、start_ocr_model_install(language)。安裝工作提供 state（status／downloaded／total／phase／error）、cancel、wait。模型為官方 tessdata_fast 4.1.0 commit `65727574dfcd264acbb0c3e07860e4e9e9b22185`，大小及 SHA-256 固定於 ebook2mp4/ocr.py；完整校驗後逐檔原子發布，取消保留已安裝模型，移除未完成下載及鎖。UI 首次查詢大小、忙碌期間語言變更補查，顯示與選擇一致前不准安裝。跨視窗採模型安裝鎖，中斷鎖需關閉視窗後移除。

Tesseract 5.4.0.20240606 隨包提供，預設 `_internal/tools/tesseract/tesseract.exe`。模型預設 `%LOCALAPPDATA%/ebook2mp4/ocr/<commit>`，只在介面明確操作時連網下載，不上傳書稿或頁圖。開發可設 EBOOK2MP4_TESSERACT／EBOOK2MP4_OCR_HOME。OCR 每頁 subprocess，不經 shell、無主控台、120 秒上限；取消 kill 並 communicate 等待，刪頁圖暫存。PDFium 共用鎖及逐頁資源關閉規則不變，TXT 仍惰性載入 PDF/OCR 元件。

**T05 交接當時 T06 尚未實作（現已完成，見上方）**：當時的自動模式逐頁判斷、指定頁／旋轉、只重試失敗頁、候選逐頁採用等仍待 T06；不能把 T05 的全部強制 OCR 及新批次採用當成這些功能的驗收。不要直接用 OCR 重試覆寫校對稿。

固定 Python 依賴見 packaging/requirements-runtime.txt／requirements-dev.txt。建置先安裝隔離工具至 `.scratch/build-tools` 並設 PYTHONPATH，再執行 packaging/prepare_ocr.py（建置時需 7-Zip，固定來源及雜湊，解壓而不執行安裝程式），最後 packaging/build.py。OCR 準備會放 27 個引擎／必要 DLL 至 `.scratch/ocr-runtime`；PyInstaller spec 必須有此目錄。Tesseract／模型及 DLL 授權來源見 packaging/OCR-NOTICES.md；T23 仍須完成授權／源碼交付與乾淨 Windows 安裝。

2026-10-26 最終完整驗證 **50／50 tests 通過，74.073 秒，無跳過**；mypy 檢查 7 個來源檔案及語法編譯通過，修正後 onedir 重建及實際啟動通過。Standards／Spec 初審 P2 均由原審查者確認解除，兩軸零項未解決。原始結果、真實工具／替身範圍、視覺及審查證據見 docs/verification/T05*。

使用者追加基本測試：`E:/Leo/assets/ebooks/靈性開悟/book1-ch1.pdf`，9 頁均無文字層。以簡中＋英文真實 OCR 9／9 成功，30.619 秒，首頁標題與正文開頭對照通過。正式輸出 **`outputs/book1-ch1.txt`**，UTF-8、16,605 bytes、6,239 字元（含原生換行），SHA-256 `2bb7a9eb6f5b3c6061e5a1badc9551d2cd7e86b4d1921b82af4a2fa20828b925`；專案重開與匯出解碼相同。outputs 排除 Git，保留本機成品而不提交書稿全文。報告 docs/verification/T05-real-book.json 不含全文。另有真實三語引擎搭配合成掃描頁及模型網路下載驗證，不能宣稱所有實體掃描零錯字。

可重跑測試：設 EBOOK2MP4_REAL_OCR_HOME 指向含 eng／chi_tra／chi_sim 的模型目錄，EBOOK2MP4_TESSERACT 指向包內引擎，EBOOK2MP4_BOOK_PDF 指向使用者檔案。未提供環境變數會明列跳過相關實際測試，不能當全套 OCR 通過。Windows 沙箱 TEMP 有寫入限制時，將 TEMP／TMP 指向專案內可寫測試目錄。

正式新版在 **`dist/T05/ebook2mp4/ebook2mp4.exe`**，SHA-256 `4A9A568A3598A551E78977FD614B1F356E463FE266C838D96B072C73FD72EFED`。因使用者開著舊 dist/ebook2mp4，這次未覆寫舊版或關閉使用者程序。包內引擎已用完整測試驗證辨識，主程式已實際啟動；完整封裝原生選檔→匯入→下載→OCR 尚待人工補驗，其他 DPI／輔助工具及 T23 安裝也未驗收。

已依 AGENTS.md 清除本次測試專案、下載副本、模型測試資料、合成書稿、隔離工具、建置暫存與快取，共 **560,798,951 bytes（約 534.8 MiB）**。清理目標先確認位於專案內；保留正式成品、指定書稿 TXT、需求及最終證據。最後本次測試／建置／OCR／封裝驗證程序為 **0**；詳見 docs/verification/T05-cleanup.json。桌面自動化階段在收尾重設，既有使用者舊版及 prototype-qa 未動。

Windows 目錄擁有者使 Git 要求安全目錄設定，每次使用 `git -c safe.directory=E:/Leo/Projects/ebook2mp4 ...`；未改全域設定。沙箱限制 .git 寫入，提交使用提升權限命令。
