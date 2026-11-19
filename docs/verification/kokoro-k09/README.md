# K09：本機封裝與離線驗收

2026-11-19。完成現有主機的驗收。#11 已關閉。2026-11-20，使用者確認不執行乾淨 Windows 測試，並回報 K09 人工聽感已完成、沒有問題。本次驗收沒有修改產品程式或重新封裝；正式 EXE 沿用已完成 #13 驗收的同一版本。[環境與使用者決定](environment.json)

## 交付版本

主程式固定在 `dist/ebook2mp4/ebook2mp4.exe`，內附 Python **3.14.3**；完整目錄 1,908 個檔案、522,971,351 bytes，約 498.74 MiB。EXE SHA-256：`47d55fb73b17dbbabc1ad1dc97d9fb29e50dc26542d3a60117ad2ae2a00d843f`。[主程式清單](main-distribution.json)

選配包為 `dist/kokoro/kokoro-zh-cpu-78fb4b82d084294e.zip`，657,212,208 bytes，約 626.77 MiB；解壓 1,417,318,549 bytes。含 Python **3.12.15**、Kokoro／Misaki **0.9.4**、100 個中文音色及 notices 授權通知。模型固定修訂 `01e7505bd6a7a2ac4975463114c3a7650a9f7218`。ZIP、來源及正式 EXE 的版本清單完全相同，worker.py 與來源相同；匯入時逐檔 SHA-256 校驗通過。[語音包清單與 SHA-256](package.json)

舊 `kokoro-integration/package.json` 記錄的 8a1e… ZIP 已不是目前交付檔。本批以實際存在且與正式 EXE 相符的 78fb… ZIP 驗收，不改寫歷史紀錄。

## 公開工作流程的真實 CPU／離線結果

[完整紀錄](host-run.txt) · [量測、狀態與樣本雜湊](host-acceptance.json)

| 檢查 | 結果 |
| --- | --- |
| 全新測試目錄匯入 | 165.78 秒，28,966 個清單項目完成校驗；100 個音色均維持未經人工品質驗證 |
| 錯版／損毀 ZIP | 拒絕啟用；原有效安裝清單與識別保留 |
| 已安裝 worker 損毀後重新匯入 | 199.18 秒，修復後 SHA-256 與正式清單相符 |
| 首次離線試聽 | 373.64 秒，包含約 64 秒校驗、模型載入及首次推論；工作狀態為 CPU，載入次數 1 |
| 第一批正式 MP3／SRT | 約 0.74 秒，重用已驗證的試聽原音 |
| 第二批正式 MP3／SRT | 約 5.08 秒，進行新的真實 CPU 合成 |
| 反向排序後合併 | 203,400 個 24 kHz 解碼影格，即 8,475 ms；兩段字幕與來源加偏移完全一致 |
| 500 ms 批次交接停頓 | 中央 10 ms 的 PCM 峰值為 0，第二批字幕於 4,425 ms 開始 |
| 換圖製作兩版 720p MP4 | 無批次 MP4 也能完成；兩版 AAC 音軌 SHA-256 完全相同，總 MP3／SRT 未變，模型載入次數未增加 |
| 取消實際推論／正式製作 | 約 1.68 秒結束推論；取消後先前試聽及正式 MP3 保留 |
| 結束流程 | worker PID 為空，無 `.worker-*` 暫存 |

本次對專用語音 Python 設定 OS 對外封鎖，直接連線探測收到 Windows **10013**，之後才執行首次載入及正式製作。測試規則已移除。[規則](firewall.json) · [探測與工作狀態](host-acceptance.json) · [移除規則](firewall-cleanup.json)

首次載入期間可用記憶體很低，另有原生回歸在同機執行。這是實際工作耗時，**不是獨立效能基準**；不將慢載入歸因於單一因素。[主機記憶體樣本](host-load-memory.json)

## 正式 EXE 操作

使用另一份書籍副本及空語音包目錄。PATH 僅含 Windows／System32，沒有 PYTHONPATH、PYTHONHOME 或外部 FFmpeg 設定；使用內附媒體工具。主程式與專用語音 Python 均由 OS 封鎖對外網路，另一次 runtime 探測亦回傳 10013。**這不能取代未安裝 Python 的乾淨 Windows。**[啟動及正常退出](exe-launch.json) · [規則](exe-firewall.json) · [探測](exe-network-probe.json) · [規則清理](exe-firewall-cleanup.json)

1. 啟動 → 主視窗最大化。[畫面](exe-start-maximized.jpg)
2. 語音設定 → 管理本機語音包 → 空目錄、取消匯入、重新匯入 → 顯示 100 個中文音色及已就緒。[空狀態](exe-package-empty.jpg) · [取消](exe-import-cancelled.jpg) · [完成](exe-import-completed-small.jpg)
3. 展開版本詳情 → 用滾輪、滑塊及 Ctrl+End 到最後一個 `zm_100` → 固定操作保留。[滾輪](exe-package-details-wheel-end.jpg) · [滑塊](exe-package-details-thumb-top.jpg) · [鍵盤](exe-details-keyboard-end.jpg)
4. 返回語音設定 → 設定保留 → 執行 57 字固定範例 → 成功並播放。[返回](exe-voice-return-installed.jpg) · [試聽成功](exe-preview-status.jpg)
5. 前往音訊製做 → 續作未完成任務 → MP3／SRT 完成並保存。本次正式 EXE 續作用的是有效既有原音；新音訊推論另由上方真實流程及 EXE 固定範例證明。[保存](exe-formal-resume.jpg)
6. 移除語音包 → 試聽、批次 MP3／SRT、總 MP3／SRT 與 MP4 的 SHA-256 全部不變 → 返回後新本機試聽停用，提供管理入口。[移除](exe-package-removed.jpg) · [缺包](exe-voice-missing-after-remove.jpg) · [前後雜湊](exe-products-after-remove.json)
7. 開啟既有 Edge 設定格式的測試專案 → 服務／音色保留 → 原成品可播放。該相容案例使用合成媒體，不代表真實雲端服務驗收。[重開](exe-cloud-project-reopened.jpg) · [Edge 設定](exe-cloud-settings-without-kokoro.jpg) · [成品](exe-cloud-output-playback.jpg) · [相容資料](cloud-compatibility.json)
8. 正常關閉 → exit code 0。[退出](exe-launch.json)

最大化與還原／縮窄畫面已實際操作。畫面尺寸及操作時間見 [exe-actions.json](exe-actions.json)；Windows 顯示縮放為 125%。一次截圖逾時及一次 screenshotId 失效均重新取得視窗後繼續，沒有以失效座標重試。

兩項畫面問題留待修正。按下「停止」後，畫面仍顯示「正在播放上次成功試聽」。縮窄到 1127 px 外框時，服務下拉欄尾端的 CPU 顯示被截短，操作按鈕仍可用。[停止後畫面](exe-preview-stopped.jpg) · [窄版畫面](exe-voice-return-installed.jpg) · [根清單](check-list.md)

## 回歸、布局與根清單

七項針對性回歸通過，涵蓋缺包保存、Kokoro 服務切換、設定還原、總音訊製片及取消／失敗保護。[紀錄](regression.txt)

專案規定的試聽兩案通過；首次受限環境執行接點五案在測試資料建立時逾時，結果保留為失敗，該次寫出報告後仍未退出的測試程序已結束。改以原生桌面可用權限重跑五案，全部通過且正常退出。早期「七案已通過」的進度回報已更正；最終結果以這兩份紀錄為準。[試聽與首次失敗](voice-join/native-tests.txt) · [接點重跑](join-recheck/native-tests.txt)

試聽量測涵蓋最大化、1360×820、1280×720、900×640，10／13 pt。10 pt 兩個帶入文字按鈕均為 130×37，13 pt 均為 162×42；水平淨距 4、正文上方淨距 8。接點另驗短／fit／overflow／long、實際 yview 契約與外層正常布局後的兩條基準線。[試聽逐對數值](voice-join/voice/native-layout-regression.json) · [接點數值](join-recheck/join/native-layout-regression.json) · [捲動契約](join-recheck/join/scroll-contract.json) · [基準線](join-recheck/join/shell-anchors.json)

本次未改產品來源；其他已核准頁面可對照相同 EXE／來源版本的 [#13 原生全頁證據](../v2-ticket-13-close/README.md)。本批根目錄清單逐項結果見 [check-list.md](check-list.md)，不以自動產生的部分清單代替完整判讀。

## 實際樣本與限制

- [EXE 固定範例](products/exe-fixed-example.mp3)、[第一批](products/batch-1.mp3)、[第一批字幕](products/batch-1.srt)、[第二批](products/batch-2.mp3)、[第二批字幕](products/batch-2.srt)。
- [總音訊](products/total.mp3)、[總字幕](products/total.srt)、[第一張圖片影片](products/total-image-1.mp4)、[第二張圖片影片](products/total-image-2.mp4)。
- 這是兩個短批次的完整工作流程，沒有宣稱多小時整本書穩定性或 100 個音色品質通過。
- 使用者回報 K09 人工聽感測試已完成，沒有問題。個別音色的歷史品質紀錄保留於 [品質表](../kokoro-k01/quality-review.md)。
- 清除 PATH、獨立 HOME、空快取與程序防火牆，不能證明乾淨 Windows 無系統 DLL／開發依賴需求。這項測試依使用者決定不執行。

[乾淨 Windows 操作路徑](clean-windows-paths.md) 保留供日後參考。
