# 局部辨識：捨棄本次結果而保留先前修正

日期：2026-10-27。接續 `T07-pdf-refinement`，處理使用者回報：接受框選 1、2，捨棄框選 3，再辨識框選 4 時，前兩次修正也被還原。

## 本次行為

局部辨識的選項列改為 **本次框選辨識：採用本次結果／捨棄本次結果**。按「保留選擇，繼續修正」後，依本次決定繼續框下一段；最後才存成一個新批次。選項只對最後一次局部辨識的頁面啟用。

| 操作 | 繼續時的文字 |
| --- | --- |
| 採用框選 1 | 保留修正 1 |
| 採用框選 2 | 保留修正 1、2 |
| 捨棄框選 3 | 保留修正 1、2；框選 3 恢復到這一次辨識前 |
| 採用框選 4 | 保留修正 1、2、4 |

如果框選 3 與已修正的段落重疊，捨棄後也會恢復該段先前接受的修正，而非最初擷取文字。捨棄後直接「存成新批次」具有相同效果。切換其他頁／整頁辨識時，先前已保留的局部修正仍會帶入；整頁重辨本身的「保留擷取原文」仍明確以整頁為單位。

原批次擷取原文仍留在比較分頁，原 PDF、人工校對稿與朗讀快照沿用既有保留規則。局部修正不自動完成整頁來源核對，原有警告與朗讀確認阻擋保留。

## 根因與修正

原本 `publication_baseline` 同時負責不可變的來源對照與捨棄時的還原；後者因此一律回到整頁最初擷取文字。三個新增回歸案例在修改前全部失敗，包含原生 GUI 的四次操作、捨棄後直接保存，以及重疊區域重辨。另有跨頁／整頁切換案例在修改前失敗。

`PdfExtraction.decision_baseline` 現在區分兩者：區域辨識使用該次作業的 `base_pages`；來源比較仍使用原始 `publication_baseline`。繼續辨識前的文字、下次選取位置及正式保存使用同一個決定基準，避免畫面正確但保存又還原。候選頁次累積保存，防止切換到整頁工作後遺失已接受的修正。這是記憶體中工作流程調整，未改專案檔案格式。

## 驗證證據

- [修改前失敗](region-decisions-red.txt)：3 項，9.294 秒，全部正確重現問題。命令：`python -B -m unittest test_pdf_refinement_desktop.PdfRefinementDesktop.test_reject_third_region_keeps_first_two_when_recognizing_fourth test_pdf_candidate_refinement.PdfCandidateRefinement.test_reject_latest_region_then_publish_preserves_earlier_regions test_pdf_candidate_refinement.PdfCandidateRefinement.test_reject_overlapping_retry_restores_previous_accepted_correction -v`。
- [跨頁／整頁失敗案例](region-decisions-mixed-red.txt)：捨棄局部重辨後改辨另一整頁，也須保留先前修正。
- [針對性回歸](region-decisions-targeted.txt)：18 項通過，25.687 秒，包含四次框選與直接保存。跨頁／整頁追加案例及最終來源另由完整回歸涵蓋。
- [完整回歸](region-decisions-tests.txt)：18 個模組以獨立 Python 程序執行 `python -B -m unittest <模組名> -v`，**122 項通過，377.163 秒，無跳過**。涵蓋新增操作、三語真實 OCR、原指定 9 頁 PDF、取消／失敗、來源保護及既有 UI 工作流程。[彙總](region-decisions-test-summary.json) 記錄測試數與模組結果。
- [警告狀態追加案例](region-decisions-warning-red.txt)：捨棄最後一次結果但保留先前局部修正時，不能誤沿用最初頁面的已核對狀態。修改前重現誤放行；現在只有完整保留最初來源記錄才沿用舊處理狀態，保留較新的局部修正仍需整頁核對。完整 122 項套件執行於此追加修正前，最終來源狀態另由 [28 項相關回歸](region-decisions-final-targeted.txt) 驗證，涵蓋 PDF 候選、原生 GUI、混合 PDF 與真實 OCR GUI。
- 最終針對性回歸：**28 項通過，96.962 秒，無跳過**，包含新增的警告狀態案例。
- [型別檢查](region-decisions-typecheck.txt)：`mypy ebook2mp4 --check-untyped-defs`，12 個來源檔案通過。
- [封裝建置](region-decisions-build.txt)：PyInstaller 成功。
- [封裝啟動](images/region-decisions/packaged-startup.jpg)：新版 EXE 實際開啟空白工作台並正常關閉，父程序退出碼 0；未載入使用者專案。

流程回歸使用真實 ProjectWorkflow、PDFium、Tkinter 與原子保存，只有新測試的 OCR 輸出使用可控內容，以固定觸發第三次辨識錯誤；並非聲稱測得 OCR 準確率。完整回歸另執行既有真實 OCR 案例。本次未呼叫真實 Gemini，未上傳書稿。

最初同程序 discovery 在反覆建立／銷毀 Tk interpreter 後，於新進度條測試中發生 `Variable.__del__: main thread is not in main loop` 與 `Tcl_AsyncDelete`，程序退出碼 -2147483645；保留 [該次失敗紀錄](region-decisions-single-process.txt)，不算通過。各模組以新程序隔離重跑，避免已關閉的測試 interpreter 被後續模組的背景執行緒回收；未為此修改正式程式或停用測試。

## 原生畫面

以 `tests/pdf_refinement_visual_fixture.py --stage retained --narrow` 建立合成圖頁，真實 UI／工作流程依序採用兩段、產生第三段錯誤結果。OCR 輸出為可控合成文字，未連線。

- [捨棄第三次](images/region-decisions/reject-third-narrow.jpg)：740×570 邏輯尺寸，選項明示只捨棄本次，文字與操作不溢出。
- [繼續後保留第一、二段](images/region-decisions/kept-first-two-narrow.jpg)：原生點選「保留選擇，繼續修正」後，第一、二段修正仍在，第三段回到本次辨識前，可再框下一段。
- [最大化](images/region-decisions/kept-first-two-max.jpg)：相同內容及選項完整，閱讀區隨視窗擴張。

目前 Windows 約 125% 縮放；其他 DPI、輔助科技及乾淨機安裝未額外驗證。

## 成品與收尾

新版 `dist/T07-region-decisions/ebook2mp4/ebook2mp4.exe`，需搬移整個 `ebook2mp4` 目錄。舊成品保留。

SHA-256：`4E1D178E4B53DC21EF4040E3BB907EFE5EF77047FD69E1EF53EF4554815F91AF`。

本次未提交、未推送。依 AGENTS.md 清理隔離依賴、建置／型別快取、引擎副本與合成專案，保留正式成品與本驗證證據。T08 與 T23 仍非本次範圍。

收尾已清除 **249,002,717 bytes（約 237.5 MiB）**，包含單程序崩潰遺留的合成專案。全部 **1,152** 個新封裝檔案可獨占開啟並已釋放，失敗 0；本次測試／新版驗證程序及原生視窗已退出，桌面自動化 kernel 已重設。使用者原本開啟的 `T07-pdf-refinement` 書稿視窗、模型與舊成品保留。詳見 [清理紀錄](region-decisions-cleanup.json)。
