# 實作交接

T01～T04 已完成。T01 基線 c45a51d、T02 ea10026、T03 c6d2a4b／a2b41b1；T04 實作 `579ccf6`、審查修正 `b487034`，最後視窗尺寸／封裝授權及驗證交接提交可由 `git log -1` 查看。目前分支 master，未設定或推送遠端。

下一張是 **T05 — 掃描 PDF OCR 與語言模型安裝**，票稿 `.scratch/pdf-txt-audiobook-video/v1.1/issues/05-scan-pdf-ocr-models.md`。**建議開新 session 再接 T05**，先讀 AGENTS.md、GLOSSARY.md、docs/adr、Spec v1.1、T05 票稿及 [T04 驗證紀錄](verification/T04.md)。

主要測試邊界沿用已核定的 `ProjectWorkflow` 與真實 Tk UI。格式 v1 目前支援多 TXT／PDF 批次；來源副本、校對版本、歷史朗讀快照與重載副本各自成檔並帶 SHA-256。可選欄位 readings、current_reading、draft_copies、source_issues 保留 T03 行為：任何人工編輯、改稿及重載都取消目前朗讀確認，舊快照不可變，批次互不影響；reading_text 不傳 snapshot_id 時只接受有效目前確認，多視窗索引變更須重開。

T04 新增 kind=pdf 與 pdf 欄位：start／end／page_count、extraction_status、mapping_valid、extracted 參照。`batches/<id>/extracted.json` 保存不可變逐頁 number、method、text、settings、status、error；原始 PDF 在 sources。專案應使用 T04 或更新版本續作。

公開 PDF 流程為 inspect_pdf → preview_pdf_page → start_pdf_extraction → finish_pdf_extraction。PdfExtraction 背景執行，提供 status、pages（副本）、cancel、wait；finish 只能發布此工作流程的完成候選，總是建立新批次，不覆寫既有校對稿。取消保留完整頁，未處理頁標 cancelled；若保存失敗，UI 保留候選供重試或明確捨棄。discard_pdf_extraction 取消並釋放已停止候選。原生 PDFium 呼叫有共用鎖，每頁操作明確關閉資源。

pdf_pages／pdf_page_image 供逐頁原稿與頁圖對照。預覽換頁前清空舊圖；失敗不得沿用上一頁圖片。編輯時立即持久化 mapping_valid=False，全文／外部重載後明示無精確對應；保守失效不因 Undo 自動恢復，原始逐頁資料始終保留。preview_line_breaks 是無副作用候選預覽；UI 明確套用後可一次復原，不刪頁首頁尾或改連字號，正文不加人工頁碼標籤。

PDF 無文字、文字稀少、異常字元或失敗透過 source_issues 阻擋確認；每項異常包含 page／reason／status，可沿用 record_source_issues、resolve_source_issue、confirmation_blockers。T04 **尚未 OCR**，只提供文字層方法，頁面驗證目前接受 method=text-layer；T05 需擴充方法／設定與逐頁 OCR 判斷、模型交付、失敗重試與候選採用，不能把稀少文字門檻當 OCR 已驗收。逐頁原稿不可用 OCR 重試直接覆蓋已校對稿。

執行依賴固定於 packaging/requirements-runtime.txt：pypdfium2 5.14.0、Pillow 13.0.0；TXT 惰性載入 PDF 元件，缺元件不阻擋 TXT。建置／開發工具見 requirements-build.txt／requirements-dev.txt，ReportLab 僅供合成測試。工具可安裝至 `.scratch/build-tools`，命令先設定 PYTHONPATH 指向該目錄。PyInstaller spec 包含 PDFium DLL／授權與 Pillow 授權，排除未使用的 NumPy adapter。

最近完整驗證為 **42 tests 全通過（70.922 秒）**、mypy 檢查 6 個來源檔案通過、語法編譯與 Windows onedir 重建通過。真實 PDFium／Tk 與替身／故障注入分開記錄，見 docs/verification/T04.md、T04-tests.txt、T04-code-review.md 及 images/T04-*.png。Standards／Spec 初審問題均修正並由原審查者確認解除，兩軸零項未解決。

封裝版已實際啟動並開啟／取消原生選檔視窗；完整原生選檔輸入與 PDF 匯入流程因自動化焦點／輸入不可靠，**仍待人工補驗**，不得宣稱已通過。其他 DPI／輔助工具及 T23 乾淨 Windows 安裝也未驗收。正式 dist 保留；最終 exe SHA-256 為 `857A5620945852C27E7E0C7625E571E5639655D320776069A3AF4556ABEFB83C`。

已清理本次測試資料、合成書稿、隔離工具、建置暫存與快取，約 110.0 MiB；本次測試／建置／封裝驗證程序最後檢查為 0，桌面自動化階段已重設。需求、正式成品及最終驗證證據保留。

Windows 目錄擁有者使 Git 要求安全目錄設定，每次命令使用 `git -c safe.directory=E:/Leo/Projects/ebook2mp4 ...`，未修改全域設定。沙箱限制 .git 寫入，提交使用提升權限命令。
