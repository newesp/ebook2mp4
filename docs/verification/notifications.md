# 共用上方中央通知浮層

2026-10-27。成品：`dist/T09-notifications/ebook2mp4/ebook2mp4.exe`，需保留整個 ebook2mp4 資料夾。

## 實作

原先各介面的成功訊息分散在左下狀態列，與右側操作缺乏視覺關聯。現在 `ui_controls.NotificationLayer` 統一在所屬視窗內容區上方中央顯示，頂端邊距 16 邏輯像素、最大寬 400，移動與縮放會重新置中。

成功／一般提示約 3 秒後以 250ms ease-out 淡出，提供 × 關閉，懸停或通知取得鍵盤焦點時暫停。每個視窗只顯示一則，新訊息替換舊訊息並清除舊計時器。警告／錯誤不自動倒數；切換、隱藏或關閉所屬視窗時清除浮層，不使用全域置頂，避免蓋在其他程式上。

`Workbench.notify` 同時把完整訊息記入既有「訊息記錄」，包含子視窗來源；長文以摘要顯示，完整內容仍可複製查閱。原有底部文字保留為狀態／回饋補充。

已套用：

- Gemini 採用本段／全部、拒絕、撤回、手動保存候選、候選完成、設定保存與連線測試。採用時短文包含段次；內部候選保存不重複通知。
- 主工作台保存、建立／開啟專案、TXT 匯入／重載、批次改名、移除 PDF 批次、匯出、朗讀確認、換行整理、全部取代、搜尋無結果、無可復原內容、來源異常處理、版本刪除及版本空狀態。
- PDF/OCR 修正選擇保留、頁面核對／略過、模型就緒、辨識結束預覽及儲存新批次。儲存／匯入後關閉子視窗的結果交由主窗顯示。
- 語音設定保存、音色清單更新、試聽完成、取消完成及工作失敗。試聽前內部保存不另跳成功提示。

保留原生確認對話框、持續工作進度、欄位驗證、未存文字、來源異常及過期版本阻擋；不以文字內容攔截所有 Label 更新。後端保存／採用語意與編輯狀態未因通知改變。

## 驗證

最終相關結果：56 項通過；1 項真實 OCR 混合流程因未設定模型環境而跳過。各 Tk 模組分開執行；語音測試在允許本機通訊的環境使用模擬服務執行。沙箱原先卡在 Python asyncio 建立本機 socketpair，不涉及本次通知邏輯；卡住的測試程序已停止。

- `notifications-core-tests.txt`：8 項共用元件測試及 7 項 Gemini UI 測試。包含自動淡出、×、替換舊計時器、懸停暫停、編輯焦點、定位、長文、owner 銷毀／隱藏／切換、完整記錄，以及逐字編輯不彈通知、一次採用只通知一次。
- `notifications-control-layout-tests.txt`：共用元件初輪與 5 項主窗配置測試。舊測試原先將新增通知誤認成第一個 Toplevel，已改為按真實視窗名稱定位。
- `notifications-desktop-tests.txt`：14 項主工作台回歸。
- `notifications-voice-tests.txt`：3 項語音回歸，使用模擬線上服務及音訊裝置。
- `notifications-related-tests.txt`：其餘 Gemini 桌面 4、續作桌面 2、PDF 配置 3、PDF 修正 7、狀態說明 3 項通過，以及真實 OCR 1 項跳過。此檔亦保留初輪失敗；上列最終檔案為修正後結果。
- `notifications-typecheck.txt`：mypy --check-untyped-defs 檢查 5 個修改的 UI 模組通過。

使用 Windows Computer Use 檢查主工作台 1040×640、Gemini/PDF 740×570、語音及 Gemini 設定視窗（約 125% DPI）。通知皆位於上方中央，文字與 × 可見，底部操作不受影響；最後另確認 Gemini 在非全域置頂下仍可清楚顯示。視覺 fixture 以 F9 重新觸發、暫停自動關閉供檢查；實際倒數與淡出由自動測試驗證。未覆蓋所有系統 DPI、多螢幕或讀屏軟體；未送出真實 Gemini／語音請求。

封裝快取曾帶入較早的浮層實作，已清除 PYZ／EXE 對應快取重新封裝。`notifications-package-check.json` 核對正式 EXE 內 5 個 UI 模組的編譯內容，與最終原始碼一致，並保存 EXE SHA-256。封裝、啟動關閉與清理證據分別保留於同目錄 notifications-build.txt、notifications-smoke.json、notifications-cleanup.json。
