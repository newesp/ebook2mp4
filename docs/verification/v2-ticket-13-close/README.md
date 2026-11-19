# Ticket #13 結案驗收

2026-11-19。依使用者指示完成 v2 共用外框及現有功能接入，沿用目前介面。使用者於本次驗收明確確認「確認沿用現行介面」，涵蓋 Kokoro 設定、語音包管理與詳情。

GitHub [#13](https://github.com/newesp/ebook2mp4/issues/13) 已於 2026-11-19 12:33:40（臺北時間）以 completed 關閉，A～E 全部完成。連接器寫入因權限不足失敗、CLI 憑證失效，改以已登入瀏覽器更新摘要與關閉，再用連接器獨立讀回確認。[遠端讀回](github-closed.json)

正式成品為 `dist/ebook2mp4/ebook2mp4.exe`。SHA-256 `47d55fb73b17dbbabc1ad1dc97d9fb29e50dc26542d3a60117ad2ae2a00d843f`。52 個封裝內應用模組與磁碟來源逐一比較通過。[封裝比對](package.json)

## 完成的修正

- 成品操作列的三個次要按鈕使用相同自然寬度，四個動作之間為 4 Tk 像素。10／13 pt、1360×820、1280×720、900×640 均有量測。[元件外框](output-metrics.json) · [回歸](output-regression.txt)
- 待命及播放結束時停用停止播放。音訊播放準備中可取消，停止後晚到的準備結果不啟動播放器。影片播放的停止操作返回原來源詳情。[待命](exe-outputs-idle.jpg) · [播放結束](exe-outputs-play.jpg) · [返回](exe-outputs-stop.jpg)
- 已發布音訊及影片的歷史任務以發布標記呈現「已保存成品」，相容既有專案的進度檔。[正式詳情](exe-outputs-stop.jpg) · [三路成品](products.json)

## 驗收結果

114 項功能與介面回歸完成，另有成品版本完整操作回歸及專案規定的試聽／接點七案通過。Kokoro 真實離線包及下載 OCR 模型各一項條件式測試跳過，依原功能票追蹤。初次媒體測試缺少工具環境變數，補齊後重跑通過。一次誤選不存在的 `test_source_tools` 模組不計入驗收。[測試彙整](final-audit.json) · [試聽與接點](voice-join/results.json)

原生矩陣 66 張畫面涵蓋 16 個 page id，四種視窗尺寸，以及文稿／版本適用的 18 pt。共用區元件與父容器保持同一實例，標頭基準差在 2 Tk 像素內，回呼錯誤為零。試聽同組按鈕 130×37、水平間距 4、正文間距 8。原生 Tk DPI 約 96.09，正式操作的 Windows 顯示縮放為 125%。[完整原生矩陣](native/measurements.json) · [彙整](final-audit.json)

正式 EXE 以獨立設定、合成書籍及 Windows 系統 PATH 啟動。長文差異可用滾輪、滑塊及鍵盤到首末；切短差異會清除軌道。還原前保留備份，返回文稿仍可編輯。AI 設定展開／收合、缺金鑰阻擋及 18 pt 已操作。PDF 異常可逐項選取、處理到空狀態，再重新擷取並放棄預覽。線上試聽取消同意後阻止送出。Kokoro 缺包時停用試聽，包管理返回保留內容。成品三條路徑顯示有效，影片可播放並返回。[文稿差異末端](exe-versions-end.jpg) · [短差異](exe-versions-short.jpg) · [AI 錯誤](exe-ai-missing-key.jpg) · [PDF 異常](exe-pdf-issues-restored.jpg) · [PDF 空狀態](exe-pdf-empty.jpg) · [PDF 預覽](exe-pdf-preview.jpg) · [同意阻擋](exe-voice-consent.jpg) · [Kokoro 缺包](exe-kokoro-missing.jpg) · [語音包](exe-kokoro-packages.jpg)

前批取消、編碼失敗、重試發布、接點獨立捲動、版本 MP4／SRT 另存，以及影片／成品長短內容的驗收由相關來源與本次功能回歸共同覆核。[製作操作](../v2-production-exe-acceptance/README.md) · [影片矩陣](../v2-video-versions-matrix/README.md)

一次診斷錯用相同測試書副本，觸發「專案已由另一個視窗變更」保護。已結束該測試程序，後續使用獨立程序重開，PDF 選單呈現正常。最後兩輪正式程序正常退出，三條成品均由內附 FFmpeg 完整解碼。[首次中斷紀錄](exe-launch-interrupted.json) · [來源驗收退出](exe-launch-sources.json) · [最終退出](exe-launch.json) · [成品解碼](products.json)

## 逐頁結案對照

| 頁面與範圍 | 功能／原生／正式操作依據 |
| --- | --- |
| 文稿、版本、換行、AI 候選與 AI 設定 | 本批 `test_unified_manuscript`、`test_v2_versions`、`test_manuscript_cleanup`、`test_v2_ai_settings`，`native/manuscript-*`、`versions-*`、`ai-settings-*`，正式文稿／版本／AI 圖 |
| PDF／TXT 來源、來源異常、來源資訊 | 本批 `test_source_issue_view`、`test_v2_manuscript_shell`、`test_unified_shell_integration`，`native/source-*`；本批 PDF 操作及前批 TXT 放棄／草稿保留證據 |
| 語音、本批／全書預設、服務、Kokoro 包管理 | 本批 `test_service_management`、`test_voice_setting_restore`、`test_kokoro_desktop`、`test_kokoro_remember_desktop`，專案試聽驗收；`native/voice-*`、`defaults-*`、`services-*`、`packages-*`，正式同意／本機包圖 |
| 音訊、任務稿／錯誤、全書合併及接點 | 本批 `test_total_audio`、試聽／接點七案，`native/audio-*`、`assembly-*`、`joins-*`，正式音訊詳情／合併圖及前批接點操作 |
| 本批影片、全書統一素材、沿用各批影片、影片接點 | 本批 `test_total_video`、`test_video_merge`，`native/video-*`；三條成品解碼及前批正式取消／失敗／恢復操作 |
| 成品版本／詳情／播放／另存 | 本批 `test_output_versions` 及成品原生回歸、操作列六組量測，正式待命／播放／停止圖；前批同版另存雜湊 |
| 專案、匯入、訊息等輔助入口及跨頁生命週期 | 本批 `test_unified_shell_integration`、`test_v2_cleanup_shell`、`test_close_lifecycle`；全頁共用父容器矩陣與前批接入對照 |

目前 UI 及操作分組依使用者核准的原生基線，歷史新增外框 mock 的前置要求由沿用現有 UI 的指示取代。Kokoro 現行介面已獲本次明確確認。真實付費服務、完整無快取 Kokoro CPU／品質與乾淨 Windows 驗收由原 #2～#11 中適用工單承接。

根清單的本次結果見 [check-list.md](check-list.md)。清理僅處理本輪測試書、依賴、建置暫存及可辨識測試程序。正式 EXE 保留於固定目錄。[清理](cleanup.json) · [最終占用檢查](final-preflight.txt)

## 使用者複測與下一張工作

本票不再有必須由使用者補做的驗收。日常複測可開啟測試書副本 → 進入「文稿 → 版本紀錄 → 看差異」→ 捲到末端 → 返回並確認仍可編輯；再進入「成品版本 → 播放 → 停止並返回」→ 確認返回原詳情。縮小視窗時確認操作列完整可用。

下一張為 [K09／#11](https://github.com/newesp/ebook2mp4/issues/11)：在未安裝 Python、沒有模型／語言快取的乾淨 Windows 上，使用固定正式 EXE 與完整 Kokoro 語音包，驗證安裝、離線試聽、批次 MP3／SRT、全書音訊及移除／清理。真實音色聽感依既有品質表覆核。[K09 驗收要求](../../tickets/kokoro-cpu/09-packaged-offline-book-acceptance.md)
