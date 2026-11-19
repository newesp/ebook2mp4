# v2 共用外框重構：沿用現有 UI

2026-11-13。B／C 共用父層及全頁接入完成；本輪既有內容回接、受影響回歸、原生與正式 EXE 驗證完成。Ticket #13 保持開啟，完整 D／E 繼承人工矩陣及原後端票沒有因此結案。

使用者已明確指示以目前 UI 排版與對應功能直接改版，禁止重新設計並免提供設計圖；已確認開始。本輪以 `baseline/` 原生畫面／量測與磁碟來源作比對，不採前輪未核准 A 外框草圖。布局及資料／任務契約分開記錄。

實作結果及逐頁責任見 [接入矩陣](integration.md)。shell 集中共用區配置；FooterPort、ActionSpec 及固定 Tcl dispatcher 統一操作建立與路由，阻擋隱藏頁、停用狀態與舊專案命令。切頁保留既有控制項、內容及操作分組。保留來源／草稿／朗讀快照、同意、任務、過期結果及失敗保存保護。

另修正影片返回後殘留標頭列、服務側欄換行、表單縮短後殘留捲動範圍，以及聲音設定在小視窗裁切。聲音設定仍是原左右分組，只讓左側實際溢出時獨立捲動，窄版音色選單／更新按鈕換列，底部操作固定。PDF PhotoImage 明確綁定自己的 Canvas。

基線／驗收入口：`tools/unified_shell_acceptance.py`。使用本輪 `.scratch/v2-shell-refactor` 隔離設定及合成書籍；受控服務產生測試音訊，真實 FFmpeg 本機處理，不傳私人書稿或發計費請求。v1封存不讀取、不執行、不重驗雜湊。正式封裝仍固定 `dist/ebook2mp4`，封裝前須正常關閉正式程式並確認無占用。

## 分開的驗證結果

功能：`final-regression.txt` 20 項、`tools-lifecycle-video.txt` 16 項、`header-track-final.txt` 13 項、`ownership-verified.txt` 14 項，以及最後聲音設定修正的 `voice-scroll-verified.txt` 10 項均通過。組合有重複案例，不加總成不同測試數。`join-anchors-final.txt` 再次重驗最後來源的接點基準線。初輪缺 reportlab 及錯誤 parent 假設已處理；測試曾因未等視窗正常關閉而留下 Tk interpreter，已修正測試清理並重跑通過。保留早期失敗及診斷紀錄，不把它們當最後結果。

原生：[根清單逐項結果](check-list.md)、[72 張畫面／量測](native-final/measurements.json)、[彙整](native-audit.json)、[OCR／旋轉欄位三尺寸](components/measurements.json)。涵蓋最大化、1360×820、1280×720、900×640、適用 18pt 及文件列表狀態。Tk DPI 約 96.09、scaling 約 1.33465；電腦操作工具畫面另有 Windows 縮放，不把實體像素直接當 Tk 座標。68 組可見標頭沒有超過 2 Tk 像素的偏移，前版 18 組失敗保留於 `before-track-fix/`。接點另有 24 組展開／收合及字級量測。試聽按鈕均為 130×37，水平淨距 4、Text 淨距 8。

全書預設的早期採樣誤取隱藏的本批次按鈕；`native-audit.json` 依同筆原生 controls 量測目前可見套用按鈕，保留 raw_footer_gap 與正確目前淨距 4，未修改原始紀錄。

正式 EXE：固定 `dist/ebook2mp4/ebook2mp4.exe`。[封裝比對](package.json)確認 53 個應用模組與目前來源一致，內附 FFmpeg／FFprobe 可執行；5 個排除模組是獨立 CLI／worker、mock 及舊彈窗。`build-current.txt` 是最後建置。`exe/` 記錄快取音訊重組、總音訊、接點、成品版本／詳情、統一素材總影片及批次影片合併。最後只再改聲音設定兩模組，已於最後 EXE 重驗窄版滾輪／滑塊／鍵盤、放大無捲軸、保存前往音訊、返回保留輸入與取消同意。`exe/26` 保留聲音裁切失敗；`exe/29`～`36` 是修正版。

[三條成品路徑解碼證據](exe-products.json)與 [MP3／MP4／SRT 合成樣本](products/)保留。刻意更改來源選取後，先前成品標記待更新且保留檔案，符合原契約。EXE 使用隔離書籍／設定、移除 PYTHONPATH／PYTHONHOME，PATH 只有 Windows 系統目錄，媒體工作使用內附工具；見 `package-launch.json`。沒有傳私人書稿或發出付費語音請求，最後正常關閉。

## 限制及清理

本輪沒有新增視覺設計。Kokoro 真實包安裝／CPU 離線推論／品質、真實付費服務端到端及繼承的完整人工矩陣仍未測，留在原票及 Ticket #13；沒有用受控測試宣稱它們通過。

相關 16 檔案型別檢查通過（`typecheck-focused.txt`，follow-imports=skip）。首次全專案檢查包含 `voice_media.py` 的既有 union 型別及獨立 `kokoro_worker.py` 缺推論依賴等問題；未宣告全專案型別通過，兩檔與本輪基線相同，見 `source-change-summary.json`。

清理結果見 `cleanup.json`。只移除本輪依賴、建置暫存、隔離書籍、快取及可確認歸屬的失敗測試資料；保留成品、需求、來源與最後證據。一次清理申請因自動核准額度不足未執行，續作時舊程序已不存在，沒有強制結束使用者程序。v1 未建置、執行或專門重驗雜湊，既有未提交／未追蹤工作保留。
