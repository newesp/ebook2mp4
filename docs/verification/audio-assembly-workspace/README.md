# 全書合併原生重作

使用者於 2026-11-12 授權依設計圖實作。核准圖為 `docs/ui-review/v2-book-merge-audio-only/1360-short.png`。本目錄分別記錄功能回歸、原生布局及正式 EXE；驗收結果以本目錄 check-list.md 為準。

## 布局／操作分組／空間 → 原生實作 → 驗收

| 核准布局 | 原生實作 | 操作與可觀察結果 |
|---|---|---|
| 共用導覽及獨立影片入口 | ProductionWorkspace 共用外框；移除依影片偏好重導音訊頁 | 保存各批影片偏好 → 開啟全書合併 → 確認仍為音訊頁 |
| 來源工具一列，工具與清單間距 8 | AudioAssemblyWorkspace.toolbar 與 bounded Treeview | 選批 → 上移 → 確認勾選及順序保留 |
| 下方兩列、共同欄線 | 同一 rows grid；標籤112、四欄144、淨距4 | 比較 pause/state、join/detail → 確認外框對齊 |
| 沒有輸出格式列及影片設定 | 音訊頁新父層，不建立 OutputControls；影片頁保留既有容器 | 開啟音訊頁 → 確認沒有 MP4 或素材元件 |
| 清單獨佔可捲區，設定與提交固定 | Treeview + AutoHideScrollbar；不使用整頁 Canvas | 捲至最後批次 → 確認停頓與製作按鈕不動 |
| 文件列收合釋放空間，可就近重開 | 窄視窗自動收合；標題旁具文字的顯示文件列表按鈕 | 縮至900 → 重開／收合 → 確認沒有空白軌道 |
| Footer 返回左、儲存及製作右 | 共用 app.actions 內單一模組 footer；次要及主要196等寬、間距4 | 改停頓 → 儲存 → 製作合併音訊 → 確認留在本頁 |
| 接點內頁保留上下文 | 沿用 JoinPage；前後文字各自捲動；相同文字不重置 yview | 開接點 → 返回 → 確認來源、停頓及清單位置保留 |

原生差異：Windows 主題控制項高度由實際 reqheight 統一，標準文字大小實測37而非繪圖36。保留共同外框與欄線。窄視窗手動展開文件時，依可用寬度縮減標籤欄與共同按鈕寬度；不改功能與操作順序。共用導覽依實際文字寬度換列。這些差異用於避免 DPI／視窗變化裁切。

## 功能契約

- AssemblyPage 保留來源、排序、停頓、接點、任務及成品生命週期；AudioAssemblyWorkspace 只負責音訊布局與呈現。
- 音訊直接使用 start_total_audio，不使用多格式 start_outputs。保存合併設定不改寫影片製作偏好。
- 不呼叫 TTS。不產生 MP4。產生 MP3 及時間軸調整後的 SRT。
- 保留來源版本驗證、舊成功成品、取消、失敗與媒體完成後的重試保存；重試不重做媒體。
- 成品操作整合播放、停止、另存與資料夾；版本入口指定 audio 路徑。
- 製作、儲存、重試及取消不加向右箭頭；切換頁面的詳情、接點及版本保留箭頭。

## 驗證紀錄

回歸：test_audio_assembly_workspace、test_assembly_joins_desktop、test_total_video_desktop、test_video_merge_desktop 及 test_total_audio。全部使用隔離專案與合成媒體。失敗版紀錄保留為 regression-red.txt、regression-route-transition.txt 及 regression-additional.txt。

本機套件安裝於本次 .scratch 暫存；不修改全域 Python。正式成品固定 dist/ebook2mp4。量測、畫面、封裝與清理結果在本目錄獨立檔案。

### 功能回歸

- regression-final.txt：21項整合回歸通過，含既有音訊、接點警告／返回、總音訊製片與各批影片合併。匯入基底類別的5項亦執行，不能把此數量當成21個新增案例。
- regression-release.txt：最後17項針對性與既有音訊UI回歸通過。原生選單label需52像素，缺陷值8、修正值52，外框144；實際元素命中量測，可攔住只有外框夠寬的錯誤。
- regression-sidebar-final.txt：最後文件父容器、原生命中區、長短捲軸及收合返回2項通過。regression-join-navigation-final.txt驗證不需先縮放就立即收回／恢復底列。
- regression-additional.txt中的12項核心音訊合併案例全數通過；該輪另有1項舊文稿步驟編號斷言失敗，已更新為現行文稿步驟並於後續接點回歸通過。初期缺依賴／過渡路由的失敗日誌保留供追溯，不當作最終通過紀錄。
- typecheck.txt：4個來源檔通過目前專案mypy模式；未宣稱檢查所有未註記函式內容。

### 原生布局與操作

最終主頁原尺寸：[1360](final-native-1360.jpg)、[1280](final-native-1280.jpg)、[900](final-native-900.jpg)、[13pt](final-native-font130.jpg)、[13pt展開文件](final-native-font130-expanded.jpg)。Tk實測與逐對值在 measurements-summary.json；相對欄線、間距與來源空間皆由原生widget邊界取得。

1360來源清單高447、1280高347、900高222；13pt仍高187。標準工具鈕144×37，保存／製作196×37。來源三對、成品操作／版本、保存／製作淨距均4；工具列到清單8；pause／state外框差0、join／menu x差0、文件列表與主內容y差0。13pt約130%，用以覆蓋125%文字放大需求；OS125%顯示縮放、Tk約96.09DPI的虛擬化座標分開記錄。

來源長／短／空／返回量測見 final-native-900／fit／overflow／empty.json。實際首末操作見 native-wheel-end、native-thumb-top、native-keyboard-end；文件列表首末及鍵盤見 final-native-documents-*.jpg／json；接點180行的獨立捲動見 native-join-*.jpg／json。Treeview按完整列計算scroll fraction；部分可見列不算完整可讀列。接點兩側Text各自捲動，固定底列不隨文字移動。

### 正式EXE

最終SHA-256：`8eb94f5e4239bab1d9ed4a9bb329a745bc2450ba34bd51617608c5a229064814`。package.json／package-verification.txt記錄52個模組一致及包內FFmpeg／FFprobe；build-delivery.txt為最後建置，prebuild-locks-delivery.json記錄建置前1905檔無占用。package-startup.json記錄最後獨立啟動與正常退出0。

實際操作：開啟隔離專案 → 全書合併 → 檢查接點 → 儲存並返回 → 製作合併音訊 → 成品操作播放 → 音訊版本 → 既有影片入口 → 正常關閉。原始合成批次各200ms，四批加三次500ms停頓，成品時間軸2300ms。exe-result.json及synthetic-merged.mp3／srt保留解碼及雜湊證據。未產生MP4，原有mp4／batch-videos偏好保留。

畫面：exe-running.jpg、exe-joins.jpg、exe-playback.jpg、exe-audio-versions.jpg、exe-video-route.jpg記錄功能操作；exe-final-checking.jpg／[exe-final.jpg](exe-final.jpg)為最後封裝複驗。最終檢查中只顯示檢查提示，不把等待驗證誤報成沒有批次；完成後成品操作文字完整、兩個清單各自有有效捲軸、左右內容齊頭。

已修正的缺陷證據包括 native-narrow-red.png、exe-menu-caption-red.jpg、exe-1360-before-alignment-fix.jpg及native-sidebar-parent-red.jpg。較早native-*.png部分使用PrintWindow，在改尺寸／字級時有重繪殘影；不作為最終整頁視覺通過依據。最終視覺採上述final-native-*.jpg及exe-final.jpg，幾何採相應JSON。

### 文件與收尾

README、規格、v2模組計畫、核准設計索引及實作狀態均已更新。根清單逐項結果見 [check-list.md](check-list.md)。cleanup.json記錄本次暫存與程序清理，以及正式成品最後獨占開啟確認；正式成品、需求及本目錄最終證據保留。未執行提交或推送，也未改動v1封存與使用者書籍。

本次共清除495,894,567 bytes（約473MiB）；最後測試／媒體程序0，正式成品1905檔全部獨占開啟後釋放。兩個11月2日既有測試資料夾保留。隔離依賴已刪，重跑須依packaging鎖定需求重新準備；不需要改動全域Python。
