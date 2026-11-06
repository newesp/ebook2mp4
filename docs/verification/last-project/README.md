# 上次專案自動載入驗收

正式程式：`dist/ebook2mp4/ebook2mp4.exe`。搬移時保留整個目錄。需求見 `docs/last-project-startup.md`。

## 結果

- 已記住最後一次成功開啟或建立的專案；正式啟動入口自動恢復。取消或失敗不改記錄。
- 首次無記錄維持空白。專案不存在／損壞或本機設定損壞時，狀態列顯示原因，仍可手動開啟。設定無法寫入時不影響已載入專案。
- 記錄只保存位置，預設 `%LOCALAPPDATA%/ebook2mp4/session.json`。不恢復未存編輯或任務，不修改書籍資料或 T20 介面。

## 驗證

- 先跑新增案例取得紅燈，再實作；`red.txt`、`green-first.txt`。
- 新增 6 項真實 Tk 案例及原有最大化案例全部通過；`native-tests.txt`。
- 完整套件 333 項，926.792 秒。初輪 314 通過、1 錯誤、18 跳過；唯一錯誤為測試命令漏設 EBOOK2MP4_FFPROBE，補入包內 FFprobe 後該案例通過（33.358 秒）。最終 315 通過、18 跳過、0 未解決失敗；應用來源未為此補跑修改。見 `full-suite.txt`、`media-env-retry.txt`、`summary.json`。
- 跳過為缺少真實 OCR 模型／指定書稿及完整離線 Kokoro 語音包。沒有讀取私人書稿，沒有將跳過當作通過。媒體回歸使用真實包內 FFmpeg／FFprobe，語音服務以合成替身驗證，未呼叫線上 TTS。
- 舊批次影片 GUI 案例輸出視窗銷毀後的 poll 計時器 Tcl 警告，案例結果仍通過；原始警告完整保留，未宣稱全套無警告。
- 兩個變更來源以 mypy `--follow-imports=silent --check-untyped-defs` 通過。原分支 HEAD 加本次暫存差異的獨立副本，6 項啟動測試及同型別檢查亦通過，不依賴其他未提交變更；`isolated-native-tests.txt`、`typecheck-isolated.txt`。
- Standards／Spec 兩位獨立審查者各 0 項，見 `code-review.md`。
- 37 個正式封裝模組與工作區來源逐一核對通過，含 app_session；`package.json`、`package-check-official.txt`。正式封裝包含工作區既有變更，但本次提交只包含本功能。
- 正式 exe 在 PATH 無系統 Python／FFmpeg、隔離本機設定的環境，原生選檔開啟合成書籍 → 正常關閉 → 重啟。第二次不選檔即自動載入同一本書及已保存校對稿，狀態列「已自動載入上次專案。」。合成書籍全部檔案 SHA-256 未變，再正常退出。原生視窗／畫面已於本次對話觀察，結果見 `packaged-journey.json`、`launches.json`。

初次安裝依賴因沙箱 DNS 限制失敗，改使用提升權限安裝至專案隔離目錄後成功，沒有修改全域 Python 套件。封裝首次核對早於背景複製完成，因此當時讀到舊 exe 並失敗；複製完成後正式核對通過，保留 `package-check-during-copy.txt`。啟動檢查腳本的 SYSTEMROOT 大小寫問題已修正，未修改應用。

## 操作驗收

1. 啟動正式程式 → 專案 → 開啟專案 → 選取有效 project.json。
2. 關閉程式 → 再次啟動 → 確認書名與已保存的校對稿自動顯示。
3. 專案 → 開啟專案 → 取消選檔 → 重啟 → 確認仍載入上次成功專案。
4. 移走測試專案 → 啟動 → 確認顯示無法自動載入提示。
5. 專案 → 開啟專案 → 選另一個有效專案 → 確認可以正常工作。

本功能沒有調整版面；未新增其他 DPI 或乾淨機驗收。清理及程序／獨占讀取釋放結果見本目錄 cleanup.json、process-check-final.json、resource-check.json。既有使用者資料、模型、其他未提交變更及舊測試目錄保留。
