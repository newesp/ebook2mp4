# Kokoro 本機 CPU 整合證據

日期：2026-11-05（Asia/Taipei）。

來源：[父規格 #2](https://github.com/newesp/ebook2mp4/issues/2)、[K01 #3](https://github.com/newesp/ebook2mp4/issues/3) 及 K04–K09 工作票。已讀取父規格與議題留言。使用者已核准繼續整合，並要求沿用既有 UI 版面。原有工作區變更另存 [preexisting.patch](preexisting.patch)，未覆寫。

主程式以含有既有使用者修改的工作區封裝。本次 Git 提交只收 Kokoro 變更；原本四個檔案的冷卻／重試修改及使用者新增檔案繼續保留為未提交狀態。重疊檔案的最終保留差異見 [preserved-user-changes.patch](preserved-user-changes.patch)。

## 交付範圍

- 主程式沿用 Python 3.14.3；模型在獨立 Python 3.12.15 CPU 程序執行。
- 固定官方中文模型修訂、引擎與套件資源。ZIP 逐檔校驗後才發布安裝；損毀安裝可重新匯入修復。
- 100 個中文音色使用既有音色欄位選取，沒有新增常駐偏好設定。所有音色均標示尚無人工品質驗證。
- 管理語音包使用主視窗內頁。試聽、正式 MP3／SRT、區塊快取、取消與續作使用既有流程。
- 正式稿及字幕保留繁體原文。OpenCC t2s 僅用於合成副本；包版本及合成文字納入本機快取身分。
- 模型在閒置 120 秒後卸載。忙碌工作不觸發閒置卸載。Windows Job Object 管理工作程序與後代程序。
- 不開啟服務埠，不自動下載模型，不自動改用雲端或其他模型。

## 已取得的證據

[package.json](package.json) 記錄正式語音 ZIP 的路徑、大小與 SHA-256。模型、依賴、授權及完整逐檔清單見 [K01](../kokoro-k01/README.md) 與主程式內建 `kokoro_release.json`。

[real-public-flow.json](real-public-flow.json)：未加入診斷程式的公開 ProjectWorkflow 流程。試聽約 55.11 秒；接續正式製作約 0.84 秒，音訊區塊全部重用。工作狀態記錄 `device=cpu`、模型載入次數 1。該次校驗約 8 秒，模型載入約 43 秒，合成及封裝約 4 秒。這是新程序、空應用快取、已暖的 Windows 檔案快取，並非重開機冷碟量測。

先前首次匯入約 117.46 秒，另一次首次校驗約 132 秒，且發生過 180 秒模型載入逾時。失敗紀錄保留於 `real-public-flow-run.txt` 等檔案。後續成功不能消除這項冷啟動限制；依新安裝路徑的實測，校驗及載入上限調整為各 300 秒，每區塊合成仍為 180 秒。超過上限會停止，不會改用雲端。

另有可重現的暫存格式錯誤：PCM 寫入 `.mp3` 導致 SoundFile 拒絕編碼。已改為本機 `.wav` 暫存，再由共用 FFmpeg 產生正式 MP3。重現證據見 [red-local-output-format.txt](red-local-output-format.txt)，修正後結果見 [real-public-flow-fixed.txt](real-public-flow-fixed.txt)。

UI 已檢查還原與最大化尺寸：[還原視窗](ui-restored.png)、[最大化視窗](ui-maximized.png)、[管理內頁](ui-package.png)。既有服務列、左右欄及底部操作列保留。後續文字選單只增加右鍵／Shift-F10 命令；取代編輯文字前會詢問取代、保留或取消。

## 離線整合結果

[acceptance.json](acceptance.json)、[完整執行紀錄](offline-run-validated.txt) 記錄實際 Windows 程序結果：

| 項目 | 結果 |
|---|---|
| 連續女聲／男聲試聽 | 模型載入次數 1 → 1；參數各自保存 |
| 取消推論／取消載入 | 約 0.34／0.11 秒；上一份試聽保留，程序結束 |
| 閒置卸載 | 加速期限 10 秒，約 10.21 秒卸載；未加速的產品 120 秒期限亦於 120.26 秒卸載 |
| 工作超過閒置期限 | 長稿持續合成，沒有被卸載 |
| 中斷、重開、續作 | 重用 1 塊，完成 18 塊，音長 230.075 秒 |
| 改音色後續作保護 | 舊執行紀錄標為過期 |
| 總音訊與兩版換圖影片 | 完成，沒有新增模型載入 |
| 主程序 `os._exit(23)` | 工作程序確實結束，沒有殘留推論程序 |

該輪部分時間與主程式建置／打包重疊，不能視為獨立效能基準；獨立量測使用前述公開流程及 K01。未加速的期限另以真實 CPU 程序通過：[120 秒證據](idle-production.json)、[執行紀錄](idle-production-run.txt)。

防火牆先對 `1.1.1.1:443` 探測，收到 Windows 10013，才執行首次載入及正式工作：[封鎖證據](offline-firewall.json)。規則已由 finally 移除：[清理證據](offline-firewall-cleanup.json)。每個工作程序使用新建 HOME／HF／Torch／TEMP，模型及語言資源從包內讀取。

[獨立媒體核對](decoded-products.json)：總音訊 234.150 秒、19 個字幕段；逐段起訖與來源加上解碼音長的偏移完全一致。500 ms 交接中央 10 ms 的 PCM 峰值為 0。兩版 720p MP4 各含一條影音串流；更換圖片後，抽出的 AAC 音訊 SHA-256 完全相同，沒有重複加入停頓。

試聽：[女聲固定範例](fixed-example-zf_001.mp3)、[男聲](preview-zm_010.mp3)、[長稿](integrated-long-zf_001.mp3)、[長稿字幕](integrated-long-zf_001.srt)。總成品保留於專案 `outputs/kokoro-integration/delivery`。

## 封裝與審查

- 主程式 ZIP：約 183.29 MiB；解壓約 401.46 MiB。精確大小與版本以 [清單與 SHA-256](main-package.json) 為準。保留完整 `ebook2mp4` 目錄後執行 EXE，不需另裝 Python。
- 選配語音 ZIP：657,212,068 bytes，約 626.77 MiB。[清單與 SHA-256](package.json)。從管理內頁匯入，不需手動啟動服務。
- [主程式 ZIP 完整性](main-package-validation.txt) 通過，內建語音包清單與來源相同；主程式未包含 Torch／NumPy／Misaki 推論套件。
- 封裝 EXE 已在 PATH 僅含 Windows／System32、清空 PYTHONPATH／PYTHONHOME 的環境啟動。[啟動截圖](packaged-startup.png)。原生 UI 工具因偵測使用者輸入而阻擋後續兩次點擊，因此不宣稱封裝版互動試聽或完整 UI 狀態已實測。
- 最後版本已再次完成 [獨立啟動檢查](final-startup.json)，並結束測試程序。[封裝來源核對](frozen-source-validation.json) 確認 EXE 內 11 個核心模組與工作區來源一致，實際含載入 300 秒、合成 180 秒及閒置 120 秒設定。
- [最終型別檢查](typecheck-verified.txt)：35 個來源檔通過。[兩軸與 UI 審查](review.md)：發現均已修正並複查。

## 回歸測試結果

[依測試 ID 彙整](test-summary.json)：共發現 266 個案例，249 通過，17 因未提供真實 OCR 資源或指定書籍 PDF 而跳過；沒有遺漏或未解決的失敗案例。真實 Kokoro 安裝與輸出案例已執行，沒有跳過。

原始全套執行遇到 600 秒修復上限，已停止仍執行的工作並保留 [原始紀錄](full-suite.txt) 與 [中止說明](full-suite-interruption.json)。工作程序入口改為優先校驗，沒有省略其餘完整校驗；測試逾時會先取消並等待工作結束，再還原環境及移除目錄。接續只跑失敗及未完成案例，保留 [續跑紀錄](full-suite-resumed.txt)。

[獨立新安裝案例](cold-package-retest.txt) 通過：匯入 155.14 秒、損毀修復 201.24 秒、首次試聽 207.74 秒、接續正式製作 0.64 秒。首次試聽包含資源校驗、模型載入、合成與 MP3 封裝，不能當成純載入耗時。案例亦驗證重開保存值、100 音色、區塊重用、移除後保留成品。初版 180 秒載入上限曾在並行建置／測試期間失敗；上限校準及負載減少後單獨通過，未認定上限調整是唯一原因。

續跑期間另有一次總影片媒體處理失敗，同期有語音包安裝／修復。未取得該次 FFmpeg 的詳細原因；[單獨重跑與原生 UI 檢查](final-targeted.txt) 的 5 個案例全部通過。此結果不代表已通過並行壓力測試。最終型別結果見 [交付檢查](typecheck-delivery.txt)。

## 清理

[最終清理核對](cleanup.json)：本次開發依賴、建置暫存、UV／Mypy／模型快取、測試安裝、失敗測試目錄、合成測試書籍及中間 ZIP 已清除。沒有本次測試程序或防火牆規則殘留。原有兩個測試目錄與全部既有修改保留。

正式主程式、語音 ZIP、試聽與總成品、K01 原始正式語音資源、需求文件及驗證證據保留。所有 `preexisting.patch` 快照均保留，沒有刪除。

## 人工品質與環境限制

可播放不等於品質通過。數字、電話前導零、千位逗號與「得」的既知偏差見 [品質表](../kokoro-k01/quality-review.md)。尚未宣稱 100 個音色或台灣口音通過人工聽感驗收。

本機有系統 Python 與開發工具。空應用快取、獨立語音 Python、封裝主程式及防火牆驗證，不能取代「未安裝 Python 的全新 Windows」驗收；乾淨虛擬機仍須另驗。

## 操作與重跑

使用者操作見 [短句驗收路徑](acceptance-paths.md)。原始 CPU 品質及效能語料見 [K01 重跑工具](../../../tools/kokoro_k01/README.md)。整合腳本為 `tools/kokoro_real_check.py`、`tools/kokoro_acceptance.py` 及 `tools/verify_kokoro_offline.ps1`。防火牆腳本以 finally 移除本次建立的唯一規則。
