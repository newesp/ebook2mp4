# K02 共用語音服務接點驗證

2026-11-04。使用者已在 K01 結果交付後確認「可以繼續整合」；記錄見 [整合決定](../kokoro-k01/integration-decision.md)。本次已讀取 [#4](https://github.com/newesp/ebook2mp4/issues/4)、[#5](https://github.com/newesp/ebook2mp4/issues/5) 正文與留言，兩票留言均為 0。

## 已完成

- 新增 `ebook2mp4/tts_backend.py`，集中內建服務的執行位置、音色來源、escaped UTF-8 位元組上限、載入／合成限時及重試次數。
- 試聽與正式製作沿用 `ProjectWorkflow`，共同走 `speech_block` → `write_speech`。快取、解碼、停頓、字幕、續作及原子發布維持共用流程，沒有第二套製作入口。
- Edge、Gemini、Fish 維持雲端、3,000 escaped UTF-8 bytes／塊、90 秒／請求、最多 3 次嘗試；現有 Retry-After、總等待上限、配額及冷卻政策保留。
- 本機／雲端差異以能力契約表達，禁止網路時僅對需要網路的服務阻擋。這不表示 Kokoro 已可用；尚未註冊本機服務或修改正式 UI。
- 三種現有服務的設定格式、原音快取身分及規則雜湊保持相容。舊 PCM fixture 可在禁止連線時完成 MP3／SRT。
- 保留工作前未提交的重試、冷卻與桌面變更。`preexisting.patch` 保存進場差異快照，不回滾、不覆蓋。

## 驗證結果

**46 個不同測試案例通過**：既有 43 個、補充 3 個。服務端請求使用測試替身；媒體解碼、MP3、字幕、檔案、重開及中斷程序驗證使用真實本機流程。未將模擬 HTTP 解讀為本機 Kokoro 或線上服務品質驗收。

| 測試 | 結果與證據 |
|---|---|
| Voice、Narration、Rhythm、Resume、Incremental、Retry、Control、Providers | [core-tests.txt](core-tests.txt)：42 項通過；1 項僅缺測試環境變數。 |
| 該項音訊／字幕重開測試 | 設定明確 `EBOOK2MP4_FFMPEG` 後通過：[recovered-narration-test.txt](recovered-narration-test.txt)。 |
| 三雲端服務禁止未同意傳送；舊 PCM／rules 身分沿用；未安裝本機服務不可用 | 全部通過：[capability-tests.txt](capability-tests.txt)。 |
| 語法及差異格式 | [final-checks.json](final-checks.json)。 |
| 工作資料與程序清理 | [cleanup.json](cleanup.json)。 |

首輪沙箱測試在 `start_voice_refresh` 的 Windows 非同步事件迴圈逾時，同一案例在原生 Windows 通過；沙箱失敗證據見 [sandbox-tests.txt](sandbox-tests.txt)。本次沒有修改事件迴圈或放寬測試限時來掩蓋環境差異。原生回歸只有一個測試直接讀取 `EBOOK2MP4_FFMPEG` 而未設定，補上既有 FFmpeg 路徑後單獨重跑通過，沒有不必要地重跑已成功的其餘案例。

主要命令：

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONPATH='tests;.'
$env:EBOOK2MP4_FFMPEG=(Get-Command ffmpeg).Source
C:\Python314\python.exe -m unittest test_voice test_narration test_rhythm test_narration_resume test_incremental_narration test_tts_retry test_tts_control test_tts_providers test_tts_capabilities -v
```

在原生 Windows 執行，使用專案既有 Python 3.14.3 與 FFmpeg。未安裝新的主程式依賴；本機 CPU 實驗 runtime 保持獨立。

## 可觀察的驗收路徑

1. 開啟既有雲端專案 → 進入「語音設定與試聽」→ 檢查服務、音色與語速 → 確認原選值保留。
2. 選擇一種既有服務 → 產生試聽 → 儲存本批次設定 → 前往製作 → 確認有效原音沿用。
3. 取消「同意傳送文字」→ 嘗試製作未快取區塊 → 確認阻止送出。
4. 製作完成一個區塊 → 取消 → 重開專案 → 續作 → 確認已完成區塊不重做。
5. 保留上一份成品 → 模擬服務失敗 → 檢查原 MP3／SRT → 確認原檔案保留。
6. 對照上列測試證據 → 檢查公開狀態、音訊、字幕與請求數 → 確認沒有依賴私有呼叫順序作為主要驗收。

以上既有雲端 UI 的實際線上試聽仍需使用者設定金鑰／同意傳送；自動驗證以固定替身避免計費或傳送書稿。

## 下一個必要確認

[#5 設計提案](../../mock-ui/kokoro-v1/README.md) 已交付 1440 × 900 與 1040 × 760 的聲音設定、語音包管理及正式製作圖，另有完整狀態圖。全部 100 種官方中文音色可選且可搜尋，圖中單一音色只是示例。

依 AGENTS.md 第 12 點「版面調整先提供設計圖，取得使用者確認後才實作」，正式 UI 尚未修改。取得圖面確認後，才能繼續依阻擋關係實作 #6 語音包、#7 設定／試聽及後續正式製作。K02 完成不表示 Kokoro 現已出現在 UI，也沒有產生聲稱已整合的 EXE。
