# 每次辨識後可切換 OCR 設定

日期：2026-10-27。使用者回報：有些詞適合 `chi_sim+eng`，有些適合 `chi_tra+eng`，但第一次重辨後設定選項被鎖住。

## 修正

OCR 開始時原本會呼叫 `ocr_controls(False)`，完成結果轉成待保存修正後卻未恢復；失敗也走同一條路，因此停用狀態留到視窗關閉。

現在由 `update_actions` 統一根據 OCR／模型下載是否仍在執行決定設定狀態。完成、失敗或取消後，未關閉的視窗可再次選擇擷取方式、辨識語言與版面。切換語言會重新檢查模型，缺少時可下載；其他背景預覽／模型檢查尚在進行時不啟用下載按鈕，避免點擊沒有作用。

語言與版面用於下一次辨識，不改既有結果的設定記錄或先前已採用修正。流程可為：繁中＋英文／單一區塊 → 接受本次結果 → 簡中＋英文／單行標題 → 下一段。辨識中暫時鎖定，結束後恢復。

「擷取方式」仍用於依範圍重新擷取；本頁及框選重辨本身固定使用 OCR，不會因選文字層而改成其他流程。設定視窗明示此適用範圍。局部裁切依目前顯示的頁圖方向，旋轉設定用於整頁重辨。未改辨識模型、準確率策略、專案格式或候選採用規則。

## 驗證

- [修改前回歸](dynamic-ocr-red.txt)：新測試 2 項均失敗，4.626 秒，分別重現成功／失敗後語言與版面仍停用。命令：`python -B -m unittest test_pdf_refinement_desktop.PdfRefinementDesktop.test_settings_unlock_and_next_region_uses_new_language_and_layout test_pdf_refinement_desktop.PdfRefinementDesktop.test_failed_region_unlocks_settings_and_missing_model_can_be_installed -v`。
- [原生 GUI 回歸](dynamic-ocr-desktop-tests.txt)：**7 項通過，21.406 秒**。實際從繁中＋英文／block（PSM 6）切到簡中＋英文／line（PSM 7），新作業收到新設定，舊作業的語言／版面不變；執行中停用、完成後恢復，兩段修正最後保存且原批保留。另驗失敗後可換語言及缺模型時下載按鈕可用。
- [相關回歸](dynamic-ocr-related-tests.txt)：各模組獨立程序執行，避免已知測試 Tk interpreter 回收問題。候選服務 15 項、OCR GUI 1 項、PDF 視窗配置 3 項、真實 OCR 混合 GUI 1 項，**20 項通過、無跳過**。本次共 27 項相關測試通過；沒有重跑無關的 Gemini／全套回歸。
- [型別檢查](dynamic-ocr-typecheck.txt)：`mypy ebook2mp4 --check-untyped-defs`，12 個來源檔案通過。
- [封裝](dynamic-ocr-build.txt)：PyInstaller 成功。
- [封裝啟動](images/dynamic-ocr/packaged-startup.jpg)：新版 EXE 實際開啟空白工作台後正常退出，父程序回傳 0，未載入使用者專案。

新增動態切換案例使用真實 Tkinter、ProjectWorkflow、PDFium 與保存流程，只有 OCR 輸出及模型可用性受控；這是設定傳遞與狀態驗證，不是準確率基準。相關測試另有真實 Tesseract 辨識，未呼叫真實 Gemini、未上傳書稿。

## 原生畫面

以 `tests/pdf_refinement_visual_fixture.py --stage retained --narrow --settings` 建立合成專案，連續辨識三次後開啟設定；OCR 輸出為可控合成內容。設定視窗採最小 600×430 邏輯尺寸，目前 Windows 約 125% 縮放。

- [辨識後仍可選設定](images/dynamic-ocr/settings-after-retry.jpg)：三個下拉選單啟用，說明、模型狀態與完成按鈕完整顯示。
- [切換成簡中＋英文](images/dynamic-ocr/selected-simplified.jpg)：原生展開並選取，模型狀態同步為 `chi_sim+eng`。
- [切換語言與版面](images/dynamic-ocr/selected-language-layout.jpg)：可再改成單行標題，預覽中的既有結果保留。

其他 DPI、輔助科技及乾淨 Windows 安裝未額外驗證。

## 成品

`dist/T07-dynamic-ocr/ebook2mp4/ebook2mp4.exe`，需搬移整個 `ebook2mp4` 目錄。

SHA-256：`0746A8BA0C50DAFD39CA7FA42247A043F2712A074A308D87733D65C607106B6A`。

未提交、未推送；舊成品及使用者原視窗保留。收尾依 AGENTS.md 清理本次隔離依賴、建置快取、引擎副本及合成專案，保留正式成品與驗證證據。

已清除 **248,983,958 bytes（約 237.4 MiB）** 暫存。1,152 個新封裝檔案均能獨占開啟後釋放，失敗 0；本次測試、合成專案及新版啟動程序已退出，桌面自動化 kernel 已重設。使用者原本的 `T07-region-decisions` 書稿視窗保留。詳見 [清理紀錄](dynamic-ocr-cleanup.json)。
