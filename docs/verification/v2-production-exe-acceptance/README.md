# Ticket #13 正式 EXE 製作與成品補驗

2026-11-18。使用 `dist/ebook2mp4/ebook2mp4.exe`，SHA-256 `bfdd98c705af4ebcc9e09af35d17d084ba05e1d52916184750a31d6cc656d7ac`。使用同一份隔離書籍，包含三批長 TXT、合成測試音與靜態素材。固定成品沿用上一批封裝。

## 正式 EXE 操作

| 操作路徑 | 觀察結果 | 證據 |
| --- | --- | --- |
| 影片製作 → 總音訊製片 → 開始 → 取消任務 | 介面顯示已取消，原 MP4／SRT 與目前成品指向保留，製作鎖釋放。 | [執行中](exe-video-running.png) · [取消畫面](exe-video-cancelled.png) · [比較](cancel-result.json) |
| 影片製作 → 重試製作 → 遇到受控編碼錯誤 | 介面顯示編碼錯誤及重試入口，原 MP4／SRT 雜湊相同，製作鎖釋放。 | [失敗畫面](exe-video-failed.png) · [比較與診斷](failure-result.json) |
| 重開同一本測試書 → 影片製作 → 重試 | 失敗狀態跨重開保留。直接使用內附 FFmpeg 重試，發布第 2 版。新舊影片都完整解碼，第 2 版為 13 秒 H.264／AAC。 | [重開](exe-video-after-restart.png) · [發布](exe-video-bundled-success.png) · [成品及工作紀錄](products.json) · [啟動資料](exe-bundled.json) |
| 全書合併 → 檢查接點 → 捲動、切換、試聽 → 儲存並返回 | 左欄先呈現前批末行，右欄呈現後批首行。用右欄滾輪或拖左欄滑塊時，另一欄原位保留。Ctrl+End 回到左欄末行。切換再返回保留兩欄位置。試聽操作可停止，儲存後保留三批原順序。 | [開啟](exe-join-first.png) · [滾輪](exe-join-wheel.png) · [滑塊](exe-join-thumb.png) · [鍵盤](exe-join-keyboard-end.png) · [切換](exe-join-next.png) · [返回](exe-join-return.png) · [停止試聽](exe-join-stop.png) · [儲存](exe-join-save-back.png) |
| 全書合併 → 成品版本 → 選擇總音訊或總影片 → 查看來源與版本 | 總音訊與總影片顯示來源一致。總影片詳情顯示第 2 版、13 秒及三批來源。尚未製作的批次影片合併停用播放與另存。 | [成品清單](exe-versions.png) · [第 2 版詳情](exe-versions-detail.png) · [尚未製作](exe-versions-unmade.png) |
| 選第 2 版總影片 → 播放成品 → 停止播放 → 另存成品 / SRT | 播放器顯示影片畫格，操作列可停止並返回詳情。另存的 MP4 與 SRT 分別以 SHA-256 比對，兩檔都與第 2 版一致。 | [播放](exe-versions-play.png) · [停止](exe-versions-stop.png) · [另存成功](exe-versions-export-success.png) · [雜湊](products.json) |

取消和編碼失敗使用測試版 FFmpeg 入口控制時機及錯誤。其轉交模式有一次音訊時長校驗失敗，仍保留舊成品。成功發布使用獨立重開的正式 EXE、內附 FFmpeg 及僅含 Windows 系統目錄的 PATH。這輪評估試聽與播放器的介面狀態，聽感、真實雲端與 Kokoro 留待實測。[受控啟動](exe-injected.json) · [轉交校驗失敗畫面](exe-video-fixture-validation-failed.png)

## 原生回歸與交付判定

- 功能回歸一項通過，包含接點試聽、儲存失敗及重試。
- 原生布局與捲動四項通過。24 組外框量測涵蓋最大化及三個指定還原尺寸、10／13 pt 字級與文件列表顯隱。16 組有左右可比的標頭與內容基準線，最大差值 0 個 Tk 座標像素。[測試輸出](join/native-tests.txt) · [基準線](join/join/shell-anchors.json) · [比例與行程](join/join/scroll-contract.json)
- 正式 EXE 保留 1920×1020 與 1127×1020 畫面。接點與成品詳情在窄版仍能找到操作。[接點窄版](exe-join-narrow.png) · [版本詳情窄版](exe-versions-narrow.png)
- 測試 EXE 正常結束。驗收專案、另存複本、依賴與暫存已清理。[清理結果](cleanup.json)

Ticket #13 保持開啟。下一批補完 D／E 的逐頁尺寸、字級與空／長狀態，由影片製作和成品版本開始，接著核對文稿版本、AI 設定、來源與語音的剩餘情境。跨環境離線 Kokoro 驗收仍由 K09／#11 追蹤。[根清單逐項結果](check-list.md) · [本機工作票](../../tickets/v2-unified-shell.md)
