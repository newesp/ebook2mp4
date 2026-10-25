# 實作交接

2026-10-26 UI 追加：基線 `75d37ea` 之後新增 `ProjectWorkflow.remove_pdf_batch` 及「移除 PDF 文件」，並將「新增 PDF 範圍」改為「新增 PDF 文件」。移除僅作用於所選 PDF 批次，確認後原子發布索引；取消或寫入失敗保留未存編輯與清單。外部原始 PDF、其他批次、匯出及專案內歷史檔案保留。最新成品改為 **`dist/T05-ui/ebook2mp4/ebook2mp4.exe`**，SHA-256 `A107E1E7D7A32A5DD35862F7624BDD4D5F740E955D1C169C350309D34CDE71BE`。完整套件 53 案例：48 通過、5 個需另設 OCR 環境的案例跳過，無失敗；mypy／編譯／重建及實際啟動通過，1040×640 真實 Tk 及確認提示可見。詳見 [PDF 文件操作驗證](verification/PDF-file-actions.md)，原 T05 的實際書稿輸出仍保留。本次追加驗證與建置暫存已於收尾清除，既有使用者程序不動；後續提交可由 git log -1 查看。

T01～T05 已實作。T05 起點 `df85a02`、主要實作 `09600e6`；模型狀態審查修正、實際書稿基本測試與最終交接見後續提交（`git log -1`）。目前分支 master，未設定或推送遠端。歷史 T04 詳見 docs/verification/T04.md。

下一張 **T06 — 混合 PDF 自動辨識、異常頁確認與旋轉重試**，票稿 `.scratch/pdf-txt-audiobook-video/v1.1/issues/06-mixed-pdf-anomalies-retry.md`。**建議開新 session 再接 T06**；先讀 AGENTS.md、GLOSSARY.md、docs/adr、Spec v1.1、T06 票稿及 [T05 驗證](verification/T05.md)。

主要測試邊界沿用已核定的 ProjectWorkflow 與真實 Tk UI。格式 v1 支援同書多 TXT／PDF 批次，來源、不可變逐頁原稿、校對版本、朗讀快照及重載副本各自保存並帶 SHA-256。任何人工編輯、改稿與重載取消該批目前朗讀確認；舊快照及其他批次不變。多視窗索引變更須重開，寫入鎖及原子發布規則沿用 T01～T04。

公開 PDF 流程：inspect_pdf → preview_pdf_page → start_pdf_extraction → pdf_extraction_pages → finish_pdf_extraction。start 新增 mode='text-layer'（預設）或 'ocr'，language='繁中＋英文'／'簡中＋英文'／'英文'；設定獨立於 TTS。每次 finish 建立新批次，不覆寫既有校對稿。pdf_extraction_pages 只接受所屬已停止候選，統一補齊取消頁，供 UI 比較及保存共用。PdfExtraction 的 pages 仍只回傳已完成頁副本，提供 status、cancel、wait。保存失敗保留候選供重試；discard_pdf_extraction 釋放已停止候選。

OCR 完成先顯示候選圖文對照，再明確「採用為新批次」或關閉捨棄；取消擷取並保留完整頁會建立取消批次。method 支援 text-layer／ocr；逐頁設定保留語言代碼、模型 commit、引擎、300 DPI、25M pixels 上限與 psm=6。狀態 success／pending／failed／cancelled，異常沿用 source_issues、resolve_source_issue、confirmation_blockers。全文編輯使 mapping_valid=False，不自動恢復；原始逐頁資料不改寫，正文不加人工頁碼標籤。

模型公開入口 ocr_models(language)、start_ocr_model_install(language)。安裝工作提供 state（status／downloaded／total／phase／error）、cancel、wait。模型為官方 tessdata_fast 4.1.0 commit `65727574dfcd264acbb0c3e07860e4e9e9b22185`，大小及 SHA-256 固定於 ebook2mp4/ocr.py；完整校驗後逐檔原子發布，取消保留已安裝模型，移除未完成下載及鎖。UI 首次查詢大小、忙碌期間語言變更補查，顯示與選擇一致前不准安裝。跨視窗採模型安裝鎖，中斷鎖需關閉視窗後移除。

Tesseract 5.4.0.20240606 隨包提供，預設 `_internal/tools/tesseract/tesseract.exe`。模型預設 `%LOCALAPPDATA%/ebook2mp4/ocr/<commit>`，只在介面明確操作時連網下載，不上傳書稿或頁圖。開發可設 EBOOK2MP4_TESSERACT／EBOOK2MP4_OCR_HOME。OCR 每頁 subprocess，不經 shell、無主控台、120 秒上限；取消 kill 並 communicate 等待，刪頁圖暫存。PDFium 共用鎖及逐頁資源關閉規則不變，TXT 仍惰性載入 PDF/OCR 元件。

**T06 尚未實作**：自動模式逐頁判斷、指定頁／旋轉、只重試失敗頁、候選逐頁採用等須依票稿完成，不能把 T05 的全部強制 OCR 及新批次採用當成這些功能已驗收。不要直接用 OCR 重試覆寫校對稿。

固定 Python 依賴見 packaging/requirements-runtime.txt／requirements-dev.txt。建置先安裝隔離工具至 `.scratch/build-tools` 並設 PYTHONPATH，再執行 packaging/prepare_ocr.py（建置時需 7-Zip，固定來源及雜湊，解壓而不執行安裝程式），最後 packaging/build.py。OCR 準備會放 27 個引擎／必要 DLL 至 `.scratch/ocr-runtime`；PyInstaller spec 必須有此目錄。Tesseract／模型及 DLL 授權來源見 packaging/OCR-NOTICES.md；T23 仍須完成授權／源碼交付與乾淨 Windows 安裝。

2026-10-26 最終完整驗證 **50／50 tests 通過，74.073 秒，無跳過**；mypy 檢查 7 個來源檔案及語法編譯通過，修正後 onedir 重建及實際啟動通過。Standards／Spec 初審 P2 均由原審查者確認解除，兩軸零項未解決。原始結果、真實工具／替身範圍、視覺及審查證據見 docs/verification/T05*。

使用者追加基本測試：`E:/Leo/assets/ebooks/靈性開悟/book1-ch1.pdf`，9 頁均無文字層。以簡中＋英文真實 OCR 9／9 成功，30.619 秒，首頁標題與正文開頭對照通過。正式輸出 **`outputs/book1-ch1.txt`**，UTF-8、16,605 bytes、6,239 字元（含原生換行），SHA-256 `2bb7a9eb6f5b3c6061e5a1badc9551d2cd7e86b4d1921b82af4a2fa20828b925`；專案重開與匯出解碼相同。outputs 排除 Git，保留本機成品而不提交書稿全文。報告 docs/verification/T05-real-book.json 不含全文。另有真實三語引擎搭配合成掃描頁及模型網路下載驗證，不能宣稱所有實體掃描零錯字。

可重跑測試：設 EBOOK2MP4_REAL_OCR_HOME 指向含 eng／chi_tra／chi_sim 的模型目錄，EBOOK2MP4_TESSERACT 指向包內引擎，EBOOK2MP4_BOOK_PDF 指向使用者檔案。未提供環境變數會明列跳過相關實際測試，不能當全套 OCR 通過。Windows 沙箱 TEMP 有寫入限制時，將 TEMP／TMP 指向專案內可寫測試目錄。

正式新版在 **`dist/T05/ebook2mp4/ebook2mp4.exe`**，SHA-256 `4A9A568A3598A551E78977FD614B1F356E463FE266C838D96B072C73FD72EFED`。因使用者開著舊 dist/ebook2mp4，這次未覆寫舊版或關閉使用者程序。包內引擎已用完整測試驗證辨識，主程式已實際啟動；完整封裝原生選檔→匯入→下載→OCR 尚待人工補驗，其他 DPI／輔助工具及 T23 安裝也未驗收。

已依 AGENTS.md 清除本次測試專案、下載副本、模型測試資料、合成書稿、隔離工具、建置暫存與快取，共 **560,798,951 bytes（約 534.8 MiB）**。清理目標先確認位於專案內；保留正式成品、指定書稿 TXT、需求及最終證據。最後本次測試／建置／OCR／封裝驗證程序為 **0**；詳見 docs/verification/T05-cleanup.json。桌面自動化階段在收尾重設，既有使用者舊版及 prototype-qa 未動。

Windows 目錄擁有者使 Git 要求安全目錄設定，每次使用 `git -c safe.directory=E:/Leo/Projects/ebook2mp4 ...`；未改全域設定。沙箱限制 .git 寫入，提交使用提升權限命令。
