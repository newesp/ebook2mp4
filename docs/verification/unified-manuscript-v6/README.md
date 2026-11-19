# 第六版文稿工作區驗收

日期：2026-11-08。依據：第六版交接與 `docs/mock-ui/unified-manuscript-v6/index.html`。正式介面仍為原生 Tk。只更新 `dist/ebook2mp4`。

## 實作與原因

舊介面保留文件列表的網格欄，原稿比例約 35%，工具會擠壓編輯器。新版收合時釋放整欄及間距，預設原稿與文稿等寬，使用比例保存拖曳結果。左上保留兩步驟，專案靠右；匯入、管理與文件列表開關同列。三區共用標頭高度，正文上緣齊頭。

依 mock 分為編輯、校對、版本與來源。版本、AI 設定及來源處理取代對照區，返回保留同一編輯器、文字、選取、游標及捲動。長差異由 Text 獨自捲動，設定由表單 Canvas 獨自捲動。來源框選是 mock 未實作的正式功能，使用並列原頁預覽與文字區，各自負責捲動。差異預覽不再包在表單捲動區內。

原生 button、Entry、Combobox 使用同組字體及內距。依原生元件邊框補足高度差，最終實測三者均為 37 Tk 單位高。窄視窗依 mock 切換原稿／文稿，並以完整控制項分組重排。沒有縮小字體以塞入操作列。

## 功能逐項對照

以下使用原生 Tk 控制項 invoke、實際專案檔與持久化結果驗證。AI／OCR 回應及外部 PDF 開啟邊界使用受控替身；不是以按鈕存在作為通過依據。

| 新入口 | 操作與可觀察結果 | 證據 |
| --- | --- | --- |
| 編輯 → 搜尋與取代 | 開啟搜尋 → 取代 Hello → 復原 → 確認全文恢復。Ctrl+F／Ctrl+H 共用入口。 | `test_search_replace_export_reload_cleanup_new_edit_menu`、既有搜尋測試 |
| 編輯 → 整理換行預覽 | 開啟預覽 → 套用 → 復原 → 確認原文恢復，預覽不直接覆寫。 | `test_line_cleanup_preview_apply_and_single_undo` |
| 編輯 → 匯出目前全文 TXT | 修改全文 → 匯出 → 讀取 UTF-8 檔 → 確認與畫面全文相同。 | `test_menu_export_uses_displayed_full_text` |
| 編輯 → 重載外部稿 | 選 CP950 外稿 → 檢查差異 → 套用 → 確認現稿已備份。 | `test_search_replace_export_reload_cleanup_new_edit_menu`、TXT 重載測試 |
| 校對 → AI 全文校對 | 從選單首項執行 → 等待受控回應 → 確認真實候選及編輯器更新。 | `test_proof_menu_real_candidate_diff_restore_and_discard` |
| 校對 → AI 設定 | 保存自訂模型、文字及字級 → 重開專案 → 確認設定保留，金鑰不在專案。 | `test_settings_model_persisted_without_credentials`、核心 DPAPI 測試 |
| 校對 → 顯示／隱藏差異 | 切換兩次 → 確認精確改動標記消失及恢復。 | `test_proof_menu_real_candidate_diff_restore_and_discard` |
| 校對 → 還原游標處改動 | 定位 Fixed → 還原 → 確認恢復 Hello。 | 同上 |
| 校對 → 放棄本次 AI 結果 | 修改候選 → 放棄 → 確認送出前文字恢復，人工候選已備份。 | 同上 |
| 版本 → 版本紀錄 | 選版本 → 預覽 → 還原 → 確認現稿已備份，需再次儲存朗讀稿。 | `test_version_restore_previews_then_backs_up_current_draft` |
| 版本 → 開啟歷史 AI 候選 | 開啟歷史 → 確認真實 AI 候選出現在版本列，可預覽及還原。 | `test_proof_menu_real_candidate_diff_restore_and_discard` |
| 來源 → 開啟來源 PDF | 開啟 → 確認使用專案內保留的來源實體路徑；模擬缺檔 → 確認可行提示及文稿保留。 | `test_pdf_source_open_missing_zoom_rotate_and_region_coordinates` |
| 來源 → 來源處理 | 重擷取 → 預覽 → 套用 → 確認新批次成立，原人工稿保留。 | `test_pdf_reextract_preview_and_region_retry_keep_original_manuscript` |
| 來源 → 旋轉／框選／續修 | 設 90° → 框選及選文字 → 辨識 → 確認候選、座標與旋轉值正確；放棄 → 確認未發布。 | 同上、PDF candidate 核心回歸 |
| 來源 → 失敗頁重試 | 只重試失敗頁 → 保存／取消 → 確認先前成功頁及人工稿保留。 | 核心 PDF／candidate 回歸；真實 OCR 案例跳過 |
| 來源 → 來源異常 | 開啟異常 → 明確略過 → 確認阻擋解除；未處理時不能保存朗讀稿。 | `test_source_blockers_visible_in_every_tool`、核心來源阻擋測試 |

## 自動回歸

最終採每個完整測試名稱的最後結果；131 個不同案例，117 通過、14 跳過、未解決失敗 0。首輪失敗及修正紀錄保留，不以首輪日誌宣稱全數通過。

- `core-tests.txt`：85 項，71 通過、14 跳過。涵蓋儲存、版本、來源、候選、取消、重試與資料保護。
- `final-native-tests.txt`：45 項，44 通過、1 個測試等待條件錯誤。該案例已在後續補驗通過。
- `final-confirmation-tests.txt`：15 項全部通過。包含新增還原視窗分組重排、PDF 框選等待、等寬、齊頭、操作高度、列表恢復、長差異及返回狀態。
- `typecheck-shipping.txt`：兩個文稿 UI 模組無型別錯誤；不是全專案型別檢查。
- `test-summary.json`：去重彙整及未解決失敗數。

資料保護測試涵蓋部分 AI 失敗與續作、明確保留原文、取消、晚到／過期結果拒絕、保存失敗回滾、草稿恢復、同稿重複保存不建新版本、朗讀快照一致、舊專案與既有製作步驟往返。

## 原生操作與尺寸

使用 `tests/manuscript_v6_visual.py`，內容為合成 PDF、兩份文件與 22,690 字元／400 段文稿；長版本差異超過 1,500 行。沒有使用私人書稿。

Windows 顯示縮放 125%。Tk 回報 DPI 96.095、scaling 1.33465，屬應用程式實際座標；截圖由 Windows 原生擷取，實體像素與 Tk 座標不能混算。12pt 與 18pt 文稿字級分別驗證。

| 狀態 | 實際 Tk 客戶區 | 編輯器高度 | 可見 display lines | 觀察 |
| --- | --- | --- | --- | --- |
| 最大化 | 1536×793 | 597 | 18 | 原稿／文稿各 639，三區齊頭。 |
| 列表收合 | 1536×793 | 597 | 20 | 原稿／文稿各 749，中心移至工作區左緣，空欄消失。 |
| 還原對照頁 | 1100×760 | 564 | 20 | 保留兩欄；操作群組重排，沒有裁切。 |
| 還原設定頁 | 1100×760 | 工具取代編輯區 | 不適用 | 標頭及保存操作固定。 |
| 窄設定頁 | 900×640 | 工具取代編輯區 | 不適用 | 內容捲動，返回及保存可達。 |
| 窄文稿、18pt | 900×640 | 444 | 11 | 可讀、主要操作可達。 |
| 窄文稿、列表恢復 | 900×640 | 444 | 11 | 文件選取保留，沒有空欄。 |

可見行數隨文字重排改變，不等於全文行數。工具頁隱藏編輯器，其舊 widget 尺寸不作為工具頁可用編輯高度。

原生操作路徑：

1. 按文件列表收合 → 檢查中心位置及兩欄寬度 → 確認空欄消失。
2. 開啟版本選單 → 按版本紀錄 → 點差異正文 → 按 Ctrl+End → 確認第 400 段可見，標頭與操作列不動。
3. 按返回文稿 → 檢查文稿與原頁 → 確認內容及位置保留。
4. 按儲存為朗讀稿 → 檢查底部 → 確認「已儲存，可朗讀」與下一步。
5. 開啟 AI 設定 → 還原為 1100×760 → 縮為 900×640 → 檢查內容與固定操作。
6. 將文稿改為 18pt → 返回文稿 → 展開文件列表 → 確認編輯區及主要操作仍可用。

`final-measurements.json` 是最終來源的尺寸與控制項高度；同名截圖 JSON 是先前操作輪次，保留當時數值。正式成品畫面以 `package-startup.png`、`package-collapsed.png`、`package-source-menu.png`、`package-production.png` 為準。`native-equality.json` 記錄保存後工作區、文稿與朗讀快照的全文一致性，不保存書稿正文。

## 封裝與清理

`shipping-build.txt`：最終建置完成，只有 `dist/ebook2mp4` 正式輸出。`package.json`：43 個封裝應用模組與目前來源一致，內附 FFmpeg／FFprobe 均可啟動。

`package-startup.json`：使用隔離設定、僅含 Windows 系統目錄的 PATH → 啟動正式 exe → 自動載入驗收專案 → 確認已儲存可朗讀 → 前往語音設定與試聽 → 正常退出，exit code 0。

來源選單確實啟動系統 Acrobat，並傳入專案內保留的 PDF。Acrobat 回報「保護模式中的 AppContainer 不相容」，檢查其視窗的應用程式授權逾時。未修改／繞過保護模式；外部 PDF 顯示未完整驗證。已關閉本次啟動的 Acrobat。

資源清理與獨占開啟結果見 `cleanup.json`。正式來源逐模組比對，不以 mock 語法檢查代替。

## 未驗證範圍

- 沒有呼叫真實 Gemini；雲端品質、配額、真實金鑰連線及網路故障品質未驗。
- 14 個真實 OCR／指定書稿案例跳過。受控 OCR 已驗旋轉、框選及資料保護，不能代替真實 OCR 品質與模型下載驗收。
- 未重跑全專案所有語音／影片媒體生成、安裝程式、乾淨 Windows 或其他系統 DPI；既有製作頁、批次切換與原稿返回回歸通過。
- 系統 Acrobat 的實際 PDF 顯示受上述 AppContainer 相容性及應用程式授權逾時阻擋。程式實體來源路徑及缺檔保護測試通過。
- 原生 Tk 的形狀、選單箭頭與文字繪製依平台呈現。HTML 僅作核准布局與互動依據，未改成網頁應用。
