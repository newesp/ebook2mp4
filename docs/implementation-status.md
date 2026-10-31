# 實作交接

## 2026-11-01：T15 交接試聽與 PDF 頁碼銜接完成

新版 `dist/T15/ebook2mp4/ebook2mp4.exe`，搬移整個資料夾。SHA-256 `60c3d124402fb0ef279c805ac127e54692dd2bbc7984de2dba5fce5441956ae2`。使用者先看 HTML 並說 OK 後實作；沿用全書合併頁，新增同主視窗接點檢查。前批結尾在左、後批開頭在右，額外交接停頓 0～5 秒、預設 0.5 秒，全書共用。前後各播 3／5／10 秒，重用有效 MP3／SRT，不新增 TTS，保留來源頭尾靜音；播放後顯示實際片段字幕文字。預覽及正式總音訊共用新增靜音規則，新增靜音沒有字幕，末批不補。

PDF 初次各同來源依物理起始頁排序，保存／手動順序優先；TXT 保留名稱及順序、不造頁碼。同來源相鄰 PDF 接點顯示重疊、缺口或倒序及具體範圍，每個警告須明確確認；不去重、補頁、搬字或補半句。確認綁定順序、頁範圍及音訊／朗讀稿版本，保存重開保留，變更須重查。可到對應批次校對，再按底部入口返回，保留未存全書設定；改稿仍須重新確認及製作批次音訊。離頁停止並取消待播準備，關閉等待釋放。

公開入口：`inspect_assembly_joins`、`start_assembly_join_preview`／`finish_assembly_join_preview`／`discard_assembly_join_preview`；`save_assembly_settings` 新增 `accepted_joins` 關鍵字。預覽檔為工作暫存，停止播放器後捨棄工作釋放。舊版超過 5 秒的設定可讀，但須調整後才可保存及新合併。實作 `b5f7eee`，審查修正 `437b5b7`；收尾文件提交見 git log，不推送。

完整 43 模組、249 案例全過、0 跳過，含真實三語 OCR／原指定 PDF。審查新增不整毫秒字幕及跨書籍返回兩個重現，修正後 T15 相關 12 項重跑全過，共 251 個不同案例。28 來源完整函式型別檢查通過，兩軸原審查者複查均 0 項。真實 FFmpeg 預覽 0／500／5000 ms，實測 400／900／5400 ms；一至三批全組合及字幕偏移通過。音訊是合成音調服務替身，不是線上 TTS 或人工聽感驗收。

原生 1040×640／1360×800 控制項、正式封裝長檔名與還原視窗已驗。封裝選檔 → 開合成專案 → 逐個確認兩個 PDF 警告 → 設 5 秒試聽 → 返回後批校對 → 底部返回 → 保存 → 總 MP3／SRT → 正常退出；重開及全解碼為 10,600 ms，語音任務仍各 1，沒有預覽暫存或鎖。26 個載入來源模組與工作區編譯碼相同，1,301 個正式檔案。驗收路徑與證據見 [T15](verification/T15.md)、`verification/T15/final-summary.json`、`verification/T15/cleanup.json`。

本輪隔離依賴、建置、快取、合成測試專案及程序已清理，正式封裝檔獨占開啟／釋放通過，Computer Use kernel 已重設。原有 TTS 控制／冷卻／重試未提交變更及證據保留；T15 封裝包含目前工作區這些更新，但沒有將其原始碼提交為 T15。使用者資料、其他版本與正式 `voice-blocks` 不動。

**下一階段建議開新 session**，先讀本段及 T15 驗證，再依下一張票稿繼續。T15 只交付音訊接點；影片最後一格預覽仍待影片合併階段。其他 DPI、真書長時間聽感及線上 TTS 未驗。後續 UI 調整仍先給草圖取得確認，不沿用本次核准。

## 2026-10-31：T14 全書合併總 MP3／SRT 完成

新版 `dist/T14/ebook2mp4/ebook2mp4.exe`，搬移整個資料夾。SHA-256 `149b50c8352e4c1c182bc8d50dc1a09319d2612d680b2ad674fe203108f4f5c2`。使用者確認 HTML 後實作，延伸 T13 四步驟及主視窗內頁，新增「全書合併」：勾批次 → 上下排序 → 交接停頓 → 製作總 MP3／SRT。共用設定保存來源版本／順序／停頓，供後續總影片使用。純音訊不需圖片／MP4，不新增 TTS。預設 N−1 段各 500 ms，末批不補。

來源完整雜湊／解碼與字幕驗證、播放前檢查及另存皆在可取消背景工作。主執行緒保留索引發布與 Windows mutex 取得／釋放，同專案產出排他。依實際幀數位移字幕，新增靜音清空字幕；最終 MP3 再解碼量測，尾部樣本差超過 1 ms 拒絕發布。失敗／取消／磁碟不足／跨窗衝突保留舊成品及進度。已選來源／設定變更標待更新，未選及視覺變更不影響；損壞舊總成品也可重建。離頁取消待播驗證並停止播放器，通知接既有訊息記錄。

38 模組 223 案例全過，0 跳過，含真實三語 OCR／原指定 PDF；發布前檔案變更保護另 1 項過，共 224 個不同案例。沙箱首輪因 DPAPI 限制中止，日誌保留，改目前 Windows 使用者環境完整重跑。最終狀態回饋修正後 5 項 GUI 全過，25 來源完整函式型別通過，兩軸原審查者複查 0 項。FFmpeg 一／二／三批實測 200／900／1,600 ms，額外 0／500／1,000 ms、交接中段峰值 0、零 TTS；音訊是合成音調，不是真書人工聽感驗收。

原生 1040×640／1360×800／最大化與正式封裝操作通過；23 封裝來源模組一致。原生選檔 → 重開合成專案 → A、C、B 合併 → 播放結束 → 正常退出，再讀回資料及 1,600 ms 全解碼通過。使用者 T13 保留。其他 DPI／真書長時間聽感未驗；WAV 組裝上限約 23 小時，明確預檢阻擋。驗收路徑、媒體及清理見 [T14](verification/T14.md)、`verification/T14/final-summary.json`、`verification/T14/cleanup.json`。

公開入口為 `assembly_settings`／`save_assembly_settings`／`inspect_assembly`、`start_total_audio`／`finish_total_audio`／`discard_total_audio`、`total_audio_runs`／`total_audio`／`total_audio_path`／`export_total_audio`。實作 `6f116e0`，審查修正 `b9fd401`／`256f5a7`／`373ea7a`，最後回饋與保護測試 `0ea80a4`，收尾文件提交見 git log，不推送。

本次清除 502,775,978 bytes 暫存、隔離依賴、建置快取及合成測試書籍。1,299 個正式封裝檔獨占開啟／釋放全過，本次程序與暫存目標均 0，測試目錄為空，Computer Use kernel 已重設。使用者 T13 的 SHA-256 未變。需求、核准草圖、正式成品與最終證據保留。

**下一階段建議開新 session 接 T15**，先讀本段、T14 驗證與票稿 `.scratch/pdf-txt-audiobook-video/v1.1/issues/15-audio-join-preview-page-warnings.md`。T14 沒有實作交接試聽、原頁回查警告或影片。後續 UI 仍須先提供草圖取得確認；不要把本次 T14 核准當成後續改版核准。正式批次 `voice-blocks` 是續作資料，不當作暫存清除。

## 2026-10-30：T13 全書語音預設與局部改稿增量合成

新版 `dist/T13/ebook2mp4/ebook2mp4.exe`，搬移整個資料夾。SHA-256 `97c46454d500fedfdd25e9b091bcdff13bc6dd8fafeae3e8b5c4f8885c47af1e`。使用者更新指示為延伸目前版面、不重新設計；保留服務列、左右語音／試聽及既有底部操作列。選全書預設時底部提供「儲存全書預設」「套用到既有批次…」；選批次、檢查影響後明確套用，不送字、不改未選批次。套用頁同主視窗，返回保留選取，重開刷新摘要／影響；製作忙碌停用套用並保留跨視窗鎖。未存批次表單先阻擋，套用成功同步已載入設定。

局部改稿沿用取消該批確認；舊成品標待更新且保留可播。重新確認後檢查目前計畫，顯示可重用／需合成及區塊原因，內容相同但順序改變仍可重用。原音內容快取沿用 T11／T12；全快取新版本強制禁止網路，無音色目錄／憑證可本機組裝，掃描後缺塊不暗送。公開入口新增 `apply_voice_defaults(batch_ids)`、`inspect_narration(batch_id)`；`start_narration(..., allow_network=True)` 新增網路權限參數。相同版本中斷續作仍走 T12。

36 模組含真實三語 OCR／原指定 PDF，0 跳過；35 模組首輪通過，製作頁在審查修改中載入新舊模組而失敗，穩定來源原 3 項重跑全過；最終 T13 Tk 追加忙碌／離線保護案例後 3 項全過，共 207 個不同案例。23 來源完整函式型別通過。雙軸審查全部原審查者複查解除。真實 Edge 僅合成自寫短文：修改／插入後重用 2 塊、只新增 2 次請求；停頓重組 0 請求，實測 +900 ms，最終完整解碼 12,072 ms。人工聽感、其他 DPI、付費 Gemini／Fish 未驗。

原生 1040×640／最大化畫面已檢查。封裝七模組來源一致；已走原生選檔 → 開合成專案 → 無音色目錄全重用組裝 → 指定第二章套用 → 正常關閉，重開資料驗證通過。驗收路徑與證據見 [T13](verification/T13.md)、`verification/T13/final-summary.json`、`verification/T13/cleanup.json`。實作 `5abe23c`，審查修正 `efeb5d2`；收尾文件提交見 git log，不推送。

清除本次隔離依賴、測試、建置暫存與程序，保留正式封裝、需求、草圖及最終證據，使用者資料與其他成品不動。**下一階段建議開新 session 接 T14「總音訊與共用全書合併設定」**，票稿 `.scratch/pdf-txt-audiobook-video/v1.1/issues/14-total-audio-shared-assembly.md`；先讀本段及 T13 驗證。全書 MP3 合併及影片仍未實作。

## 2026-10-30：語音設定與試聽精簡版面

新版 `dist/T12-voice-compact/ebook2mp4/ebook2mp4.exe`，整個資料夾一起搬移。SHA-256 `6d88724a632b4cf65176bdf28dd80ca0fb770f892ade5d2b0fcbb4ad101904b4`。語音頁移除外層 Canvas，服務／模型收為上方一列，聲音／節奏與試聽左右配置，底部固定單列。只有試聽文字框捲動；書籍清單獨立捲動。Edge 專屬音色更新、Gemini 內建候選、Fish 聲音 ID 分別顯示；非 Edge 更新入口另加防護。模型保留下拉與手填，沿用既有服務型號驗證，不暗換模型。

34 模組／201 個不同案例已驗證，0 跳過；33 模組首輪通過，既有校對優化 GUI 測試在主窗首次 Map／最大化未完成前開子窗發生 access violation，測試夾具加 `root.update()` 後原兩項重跑通過。原失敗及重跑紀錄保留。型別、五模組封裝來源一致性、啟動最大化及正常退出通過；雙軸審查與增量複查均 0 項。原生 1040×640、1360×800 與最大化已驗，其他 DPI／付費 Gemini／Fish 合成未測。

實作 `9f5fc37`、面板換行修正 `33120b5`、測試啟動時序 `d691de5`；收尾提交見 git log。增量封裝曾未納入換行修正，已乾淨重建並比對通過。詳見 [驗收路徑與證據](verification/voice-compact.md)、`verification/voice-compact-summary.json` 及清理 JSON。保留使用者舊版、書籍／模型、正式成品與證據。**下一階段建議開新 session，先讀本段。**

## 2026-10-30：預設同意與啟動最大化

新版 `dist/T12-defaults/ebook2mp4/ebook2mp4.exe`，搬移整個資料夾。主介面啟動即最大化（保留標題列及還原／關閉）；試聽與製作的傳送同意預設勾選，切任務、核對目前版本、重新開始及重載設定後也恢復勾選。這項新要求取代較早「核對後取消勾選」的行為；手動取消勾選仍阻止送出，不會自動合成。

7項語音／製作及7項啟動／版面測試通過；小視窗測試先明確還原normal後驗證。Standards／Spec獨立審查0項。封裝來源比對、測試結果與清理見 `docs/verification/defaults-*`。保留舊成品與使用者書籍／模型，僅清本次暫存；下一階段建議新session。

## 2026-10-30：製作與成品精簡版面、移除雙層捲動

新版 `dist/T12-compact/ebook2mp4/ebook2mp4.exe`，整個資料夾搬移。SHA-256 `a25c7b3365623f72ed1c59c8b8ad533c943881d1c3b99208effd30852589a76b`。製作頁改固定ttk.Frame，沒有整頁Canvas／外層捲軸，朗讀稿Text與區塊Treeview各自捲動。標頭僅一列，任務／設定詳情取代預覽，不增加頁高；底部狀態／主要操作橫向排列，返回／同意／重新開始在下一列。進度與取消僅忙碌顯示。過期的舊成功成品也可核對新版本，但不自動合成，清除同意。失敗列可查看原因，顯示在既有狀態區。語音設定頁與後端續作／成品保存不變。

1040×640原生畫面與1360×800清單高度已驗，詳情切換、製作／取消／匯出／播放連接及過期核對／失敗原因3項原生測試通過，型別檢查通過。雙軸審查已由原審查者複查0項；封裝來源比對一致、啟動／正常退出通過。完整33模組198案例，0跳過；既有Gemini GUI首輪暫時停滯，停止後4項獨立重跑全過，其餘首輪通過。見 [驗證](verification/production-compact.md)，其他DPI未測。

清理紀錄 `verification/production-compact-cleanup.json`；保留正式成品、核准草圖與驗收證據，使用者舊版本、書籍與模型不動。下一階段建議新session。

## 2026-10-29：T12 單一主視窗與語音中斷續作

新版 `dist/T12/ebook2mp4/ebook2mp4.exe`，搬移整個資料夾。SHA-256 `27767d86130a58367e5032cdf9b6ef17d67b6e013164343c59c3c929f549381e`，封裝九模組來源比對全相同，見 `verification/T12-package-source.json`。「試聽與製作」改主視窗內頁：語音設定／試聽 → 製作與成品，服務管理也在同一內容區。返回保留輸入；正式任務切頁持續，底部可返回原批次任務；播放離頁停止，隱藏試聽完成不自動播放。窄版可捲動，底部主操作固定。

新增 `resume_narration(batch_id, run_id, allow_network=True)`；`narration_runs` 增可重用／待處理、stale、published。取消、失敗、硬中斷後保存原快照與有效區塊；續作驗 SHA-256、PCM 格式與完整資料長度，只重請無效塊，每塊每次最多3次，舊錯誤進度保留 resume_history。Windows OS mutex 可硬中斷恢復，尊重舊版活程序 PID，不必手動刪鎖。稿件／設定變更阻擋舊續作。全快取可無目錄／憑證離線組裝；allow_network=False 在實際服務邊界保護，掃描後缺塊也不暗送文字。取消及磁碟不足保護舊 MP3／SRT。`voice-blocks` 是正式續作資料，不要清除。

完整33模組196案例，首輪兩模組的舊彈窗假設修正後9項重跑通過，其餘首輪通過，0跳過；最後11項續作／Tk通過。另補實際媒體子程序組裝取消→確認退出→零TTS續作，最終6項續作全過，合計197個不同案例；內頁3項另驗跨批次服務返回。22來源一般型別及9來源完整函式檢查通過。Standards／Spec問題已由原審查者複查解除。真實Edge只送三段合成範例，成功1塊後取消→重開→重用1塊→續作完成3塊，16.096秒，無殘鎖；人工聽感、其他DPI及長篇操作待驗，Gemini／Fish無付費實測。

原生1040×640 Tk 操作／捲動邊界已驗；封裝原生選檔→開合成專案→主視窗語音／中斷任務頁已走過。新增測試的音色快取隔離疏漏已修正，正式Edge音色清單已重新取得，既有憑證與使用者專案未改。詳見 [驗收與證據](verification/T12.md)、[審查](verification/T12-review.md)、[清理](verification/T12-cleanup.json)。

基線 `49637900c831917553081f48bdd8f16fbb736fa2` 保存此前已存在的UI／TTS整合；T12另提交目前分支，不推送。其他原型、需求與歷史證據保留。**下一階段建議開新 session，接 T13 前先讀本段。**

實作 `70e7e18`、Tk 清理 `6d18b2a`。實際提交匯出乾淨副本9項流程通過，程序退出碼0且無Tk清理診斷；最終封裝啟動／正常退出通過。封裝完整續作及成品操作路徑亦已用合成專案走過；最後僅更新導覽選中狀態與背景參照清理，完整路徑與最終啟動的封裝雜湊分別記錄於驗證文件。

收尾清除400,052,001 bytes，本次暫存路徑與程序均0；正式封裝1,299檔獨占開啟／釋放全過。Computer Use kernel已重設。使用者專案、模型、outputs、其他版本與既有非本次文件保留。

## 2026-10-29：TTS 服務金鑰欄位連動

新版 `dist/SERVICE/ebook2mp4/ebook2mp4.exe`，搬移整個資料夾；SHA-256 `D0D905D2541E323089E61E3DABCCC6ACF1557BD99FF1A81A4B28B7E289AD3443`。選 Fish Audio 會更新顯示名稱並隱藏 Google 沿用選項；切換服務清除未保存的手填金鑰。Google 勾選沿用後，以遮罩、唯讀顯示目前校對金鑰；缺少金鑰時提示並取消勾選，取消沿用後恢復先前手填值。保存沿用選項不複製金鑰，正式請求仍讀取目前校對金鑰。切換時清除舊狀態提示。

3 項 Tk 服務表單測試、2 項服務視窗回歸、mypy 通過；乾淨重建後封裝模組與源碼位元碼比對一致。未測真實雲端金鑰及其他 DPI；原生視覺截圖未另執行。詳見 `verification/service-form-tests.txt`、`verification/service-ui-tests.txt`、`verification/service-ui-build-final.txt`。既有未提交工作保留；下一階段建議新 session。

## 2026-10-29：四步驟主介面與可編輯確認頁

新版 `dist/MAIN/ebook2mp4/ebook2mp4.exe`，搬移整個資料夾。SHA-256 `70873EE1718D06BE0D90EAD34172A73308BB90B32541C910C22894D30F7E6846`。上方「匯入來源 → 校對文字 → 確認朗讀稿 → 試聽與製作」；校對頁左右對照，搜尋／AI 工具按需展開。主要按鈕完整標示「儲存並前往確認朗讀稿 →」，保存成功才切頁。確認頁全文可直接編輯，與校對頁共用同一編輯器；切頁不重載、不丟未存文字或復原紀錄。「確認朗讀稿並前往語音設定 →」保存最後文字、建立快照後才開語音；改稿仍須重新確認，舊朗讀稿與成品保留。多 TTS 服務及正式 MP3／SRT 沿用前版；未確認仍可短文試聽，正式合成需已確認。影片未實作，不放主要導航。

30 模組185項完整回歸，無跳過；首輪兩項通知舊測試需先進校對頁，調整後8項重跑通過，其餘29模組首輪通過。mypy20來源及 desktop.py --check-untyped-defs 通過。雙軸審查問題原審查者複查解除。原生1040×640約125%縮放校對／確認頁已檢查，其他DPI未驗。封裝六模組與來源比對、啟動／選檔／正常退出通過；原生選檔輸入自動化未穩定，封裝完整開專案→編輯確認互動路徑未完成。未執行付費服務或保存測試內容到使用者專案。

詳見 [逐步驗收與畫面](verification/main-flow.md)、[完整結果](verification/main-flow-final-summary.json)、[審查](verification/main-flow-review.md)、[清理](verification/main-flow-cleanup.json)。既有未提交工作保留，本次未提交／推送；本次精確差異保留 `verification/main-flow-task.diff`。正式成品、使用者專案／模型與需求證據保留。

**下一階段建議開新 session。**

## 2026-10-29：多TTS服務及三欄操作流程

新版 `dist/TTS/ebook2mp4/ebook2mp4.exe`，搬移整個資料夾；SHA-256 `14C10F005FB974490B2C13211645C578BB57DCEC739F372540B80413137ACD3E`。語音窗左到右選服務／模型、選聲音與節奏、編輯試聽，下方儲存／前往製作。支援Edge、Google Gemini TTS API key（兩個3.8模型可下拉或手填未來ID）、Fish原生API（明確模型及手填reference_id）。服務管理可新增／編輯本機加密憑證、檢查連線／音色；檢查不合成，不代表模型已實測。Google可明確選擇沿用校對金鑰，無Cloud專案／ADC要求。試聽及正式共用provider/model/profile快取與原音組裝，不暗存設定、不改校對稿、不自動跨服務換聲。

最終8模組56項相關測試全過，20來源型別檢查通過。新服務驗證用HTTP替身與真實FFmpeg，Gemini／Fish真實金鑰及付費合成未測；帳號權限、額度、發音及長篇穩定待使用者驗收。原生主窗／服務表單已看，最小1100×740，其他DPI未驗；封裝來源比對、啟動／正常退出通過。尚無任意相容API、自訂端點、設定檔刪除、完整遠端音色瀏覽或模型歷史選單。服務錯誤分類、429／5xx退避及Retry-After、跨服務金鑰隔離均已審查修正，原審查者複查解除。

詳見[功能／驗收路徑](verification/tts-app.md)、[最終回歸](verification/tts-app-final-suite.txt)、[清理](verification/tts-app-cleanup.json)。本次未提交／推送，既有未提交工作保留。建議接T12或繼續擴充服務前開新session。

## 2026-10-29：可編輯試聽、自動播放與視窗位置

新版 `dist/T11-voice-edit/ebook2mp4/ebook2mp4.exe`，搬移整個資料夾。SHA-256 `335786545BBD13510972C646D10126E91D239971B2CE1AEDE6F3D7567646D087`。語音設定預設最大化，一般應用程式視窗首次顯示置中（通知／泡泡保持貼附）。Edge同意欄預設勾選。試聽區改可直接編輯的預填範例；「產生並播放試聽」按當下文字與設定合成、自動播放，不暗存設定、不改校對稿。「儲存設定」獨立保存。正式合成偵測稿件／設定改變仍要求重新核對。

20項相關流程、16模組67項桌面回歸、最終4項試聽／置中與18來源型別檢查通過。真實合成短稿的Edge→自動播放→停止通過。最大化原生畫面已檢查，其他DPI及聽感待人工驗收。詳見 [操作與證據](verification/voice-edit.md)。本次未提交、未推送；先前未提交工作保留。清理與程序／檔案釋放見 [紀錄](verification/voice-edit-cleanup.json)。下一張T12建議新session。

## 2026-10-28：T11 節奏設定實作完成，人工聽感待驗

新版 **`dist/T11/ebook2mp4/ebook2mp4.exe`**，請搬移整個 ebook2mp4 資料夾。SHA-256 `DC01895B43772FBAFDFC9543F93E3AAF5CAD1CA808D6E36B6C5737F6816A8E01`。

「語音試聽」新增自然 0／500、舒緩 200／800 與自訂句尾 0～1500／段落 0～3000 ms。試聽與正式輸出共用安全切分與原始 PCM；非零句尾逐安全句界合成、實際插入靜音、同邊界取 max、最後不補靜音，字幕依實測時間且新增停頓期間無字幕。成對引文內不拆句。相同文字／音色／語速的原始塊驗證 SHA-256 後重用；自然與非零互換若切分改變，只重合成必要失效塊。原稿不回寫。全書預設僅供新批次，既有批次設定獨立。

完整 **28 模組、175／175 通過、549.624 秒、無跳過**，含真實三語 OCR 與原指定 PDF；17 來源檔 mypy 通過。HEAD＋本次修改獨立副本另驗 **24 項流程／Tk 通過**，15來源檔型別通過，不依賴既有未提交 UI／OCR／通知工作。兩軸審查問題已由原審查者複查解除。真實 Edge 7.3.1 三語×三節奏完整解碼量測，自訂相較舒緩均精確 +600 ms；原音全重用、試聽／正式 MP3 位元組相同；Windows 播放／停止通過。

封裝來源與最終6個改動模組逐一比對位元碼／常數相同；封裝啟動、原生選檔、取消與正常退出通過。選檔自動化未能穩定綁定欄位，**封裝完整開專案→合成流程本次未完成**；未送使用者書稿。原生語音窗740×650畫面與Tk範圍檢查通過；獨立設定列避免擠壓既有操作列，其他DPI待驗。

詳見 [T11驗證與逐步驗收](verification/T11.md)、[審查](verification/T11-code-review.md)、[真實服務](verification/T11-real.json)、[封裝](verification/T11-packaged.json)、[清理](verification/T11-cleanup.json)。三語人工聽感仍待使用者驗收，不以可播放代替品質通過。長篇／參考工具比較留首版完整驗收。依 implement 提交目前 master、不推送，保留既有未提交工作。正式成品與最終證據保留；本次測試、建置、隔離依賴及程序清理見紀錄。

**接 T12 前建議開新 session。** T11 本次可完成收尾。公開入口沿用 `save_voice_settings`（新增可選 `sentence_pause_ms`／`paragraph_pause_ms`）與試聽／正式工作流程。原始 `voice-blocks` 是後續可重用製作資料，不要當建置暫存刪除；T12 的跨次任務續作仍未實作。

## 2026-10-27：T10 已確認朗讀稿產生批次 MP3／SRT 完成

新版 **`dist/T10/ebook2mp4/ebook2mp4.exe`**，請搬移整個 ebook2mp4 資料夾。SHA-256 `412A9CEA32708B15350DB675E7CFA62D8FF621E28BF82C14938EE9FB59DEBF79`。

從「語音試聽」進入「批次 MP3／SRT…」。核對已確認全文、音色與語速並勾選同意後才送 Edge。未確認稿不能開始；開始固定文字／設定／規則；跨視窗排他成品任務鎖。可顯示階段、目前／總區塊及完成／失敗數，取消、播放、停止、另存與開啟資料夾。主窗換書／批後阻擋舊視窗啟動；改稿後保留既有成功成品。

長稿優先完整段落，必要時句尾→分句→詞間空白，保護段內成對引號／括號、縮寫、小數、網址與省略號；每請求上限3,000 escaped UTF-8 bytes，避免SDK再拆。無安全切點時送出前提示改稿，不硬切。精確保存原文字及段落分隔符、識別、順序、內容／設定／規則雜湊、狀態、嘗試及實測時長。網路／服務每塊最多3次，未全成功不報完成。自然句尾額外0／段落500 ms，末段不補；實測完整PCM區塊時間產生UTF-8 SRT，新增靜音無字幕，不虛構逐字。全解碼驗證後原子發布，失敗／取消與發布後清理失敗都保護成品。

公開入口 `start_narration`／`finish_narration`／`discard_narration`、`narration`／`narration_path`／`export_narration`／`narration_runs`。計畫及進度保存在批次下，音訊／字幕相對路徑與SHA-256進索引。硬中斷殘留 `.production.lock` 須先關閉所有視窗後移除再重開；T12續作尚未實作。

最終完整 **26模組、170／170通過、427.944秒、無跳過**，含真實三語OCR及原指定PDF。mypy17來源檔通過；最終提交內容的獨立副本另驗 **7項流程＋2項Tk全過**，mypy15來源檔通過，不依賴先前未提交UI／OCR工作。雙軸審查全部由原審查者複查解除。真實Edge7.3.1與最終封裝均只送合成三段範例，**19.048秒MP3／SRT**，FFmpeg完整解碼時間一致，原生選檔→合成→播放／停止→正常退出、重開及檔案釋放通過；700×580原生視窗無裁切。人工聽感、其他DPI及T23乾淨機仍待驗。

詳見 [T10驗證](verification/T10.md)、[審查](verification/T10-code-review.md)、[最終封裝](verification/T10-packaged.json)、[清理](verification/T10-cleanup.json)。本次依implement提交master、不推送。既有未提交UI／OCR／通知工作保留；舊通知測試的messagebox假設已改驗現行通知記錄，最小修正證據保存在驗證文件。移除 **414,853,708 bytes** 本次依賴、建置、測試資料與快取；1,299封裝檔獨占開啟／釋放全通過，本次殘留程序0、暫存路徑0、測試目錄內容0，Computer Use kernel已重設。保留正式成品、需求、證據、使用者模型／outputs及正在使用的T09-notifications舊版。

**接 T11「自然／舒緩節奏與自訂句尾、段落停頓」建議開新 session。** 票稿 `.scratch/pdf-txt-audiobook-video/v1.1/issues/11-reading-rhythm-settings.md`。先讀本段、T10驗證與新 `narration.py`／`narration_desktop.py`。T10只有自然0／500；T11還須實作非零句尾的實際語音／時間、試聽與正式共用、原始音訊可重用；不能把字幕位移當成新節奏完成。

以下為歷史紀錄，T10狀態以上方為準。

## 2026-10-27：T09 Edge-TTS 音色、語速與短文試聽完成

新版 **`dist/T09/ebook2mp4/ebook2mp4.exe`**，搬移整個 ebook2mp4 資料夾；SHA-256 `A0ED11FD92B2B9A4BC5E994B761B0468AF041EFB0A2E94869470937F42B0A8CC`。

主窗「語音試聽」可更新／快取服務音色，明選單一音色與 -20%／-10%／正常／+10%／+20%。全書預設只供新批次，既有批次設定獨立；固定範例或所選校對內容先明示並勾選同意才送線上。背景合成，固定文字／設定快照；失敗或取消保留舊成功結果，可播放。採自然句尾額外 0／段落 500 ms，末段不補；處理設定與音訊相對路徑／SHA-256 保存，供 T10 共用。未存校對稿可試聽，不暗存成校對稿。視窗固定所屬書籍／批次，主窗換批後阻擋新設定及試聽，須關閉重開。

完整 23 模組 **147 項通過、254.586 秒、無跳過**，含真實三語 OCR 及原指定 PDF；審查修正後 **7 項語音＋3 項 Tk** 通過，mypy15來源檔通過。乾淨提交另驗10項全過，不依賴先前未提交 UI／OCR 修改。Standards 初審2、Spec1項全部由原審查者複查解除。

真實 Edge-TTS 7.3.1：322 音色，台灣／中國華語／英文均有；只送合成短文，選取雙段 MP3 8.684秒，正式封裝固定範例8.808秒。FFmpeg全解碼、FFprobe、Windows MCI播放／停止／檔案釋放通過。原有7.2.8可列音色但合成403，不可沿用；隔離依賴已清理，重跑須安裝固定runtime/dev依賴並準備工具。最小740×650原生視窗（約125%縮放）及最終封裝原生選檔→試聽→播放→正常關閉通過；人工聽感、其他DPI及T23乾淨機仍待驗。

詳見 [T09驗證](verification/T09.md)、[審查](verification/T09-code-review.md)、[最終封裝](verification/T09-packaged.json)、[清理](verification/T09-cleanup.json)。本次依implement提交master、不推送，先前未提交 UI／OCR 修改保留。正式成品、驗證音訊／證據、需求、使用者模型／outputs與舊成品保留；本次測試／建置暫存與程序清理詳見清理證據。

**接 T10「已確認朗讀稿產生批次 MP3／SRT」建議開新 session。** 票稿 `.scratch/pdf-txt-audiobook-video/v1.1/issues/10-confirmed-draft-mp3-srt.md`。沿用 `voice_settings`／`start_voice_preview`／`finish_voice_preview`／`voice_preview`／`voice_preview_path` 及 `voice_media.synthesize`；T10仍須實作長稿切分、正式音訊／字幕、任務進度與輸出，不能將短文試聽當作完成正式合成。FFmpeg版本／準備／授權見 `packaging/VOICE-NOTICES.md`、`prepare_voice.py`，OCR仍可重用已驗包內引擎。

以下為歷史紀錄，T09狀態以上方為準。

## 2026-10-27：T08 長稿分段、取消與部分失敗續作完成

Gemini 長稿自動分請求，先保存來源版本／範圍計畫，每個請求後原子保存進度；中段失敗繼續其他範圍，成功候選不自動改稿。可逐段採用成功候選、只重試失敗，或取消／重開後繼續未完成。直接中斷程序也保留最後成功進度；原稿變更後保留舊候選但阻擋續作／覆蓋。候選視窗顯示完成／失敗／未完成與字元範圍，較舊候選重試不跳記錄。十萬字中文／英文／數字送出前檢查已補效能回歸。

新版 **`dist/T08/ebook2mp4/ebook2mp4.exe`**，整個資料夾一起搬移；SHA-256 `44980C80AC28B939E9DDEEB0410F2F51F789451212F1C7F7754ED6B52F1E64F6`。139 項分模組完整回歸（134 首輪＋5 OCR 模型環境補驗）全部通過、無跳過；最後長稿9／正規化7／Tk2項追加驗證、mypy12來源檔、封裝建置及啟動／正常退出通過。真實 Gemini 僅送合成文，3個真實請求＋中段錯誤注入，重試 attempts `[1,2,1]`；採用／重開／撤回通過。兩軸審查無未解決問題。詳見 [T08 驗證](verification/T08.md)、[審查](verification/T08-code-review.md)、[清理](verification/T08-cleanup.json)。

目前 master，本次按 implement 要求提交、不推送。候選視窗既有版面相依納入提交，其他先前未提交 UI／OCR 修改保留；乾淨 HEAD＋提交內容另驗28項通過。本次暫存、依賴、引擎副本、快取及程序均清理；正式成品、需求、證據、使用者模型／outputs與舊成品保留。

**建議下一張 T09「Edge-TTS 音色、語速與短文試聽」開新 session。** 票稿 `.scratch/pdf-txt-audiobook-video/v1.1/issues/09-edge-voice-preview.md`。TTS、音訊／影片與T23乾淨Windows安裝仍未完成。以下為歷史紀錄，T08狀態以上方為準。

## 2026-10-27：批次狀態 hover 說明

在狀態欄停留約 0.4 秒：「未確認」顯示「確認朗讀稿」；「待檢查 N」顯示「有 N 項來源／OCR 異常尚未處理」。保持原批次選取與鍵盤焦點；離開、捲動、狀態更新及關閉時收起並取消計時器／事件綁定。

新版 `dist/T07-status-help/ebook2mp4/ebook2mp4.exe`，整個目錄搬移；SHA-256 `FB85EC90AA2A13971CAC6A8DE7CBC1A59340D476C99463D405C4B4B318A74996`。8 項相關 GUI 回歸通過（8.790 秒），原生浮動說明與封裝建置完成。見 [驗證紀錄](verification/status-help.md)。本次未提交、未推送，舊成品保留。以下為歷史紀錄。

封裝實際啟動與正常退出通過；已清理 176,385,150 bytes 暫存，1,152 個新封裝檔案獨占開啟／釋放通過，無本次殘留視窗、程序及占用。

## 2026-10-27：每次重辨後可動態切換 OCR 設定

修正第一次辨識後 OCR 選項一直停用：統一由目前作業狀態控制設定啟用，完成、失敗及取消後可重新選語言／版面，下一次辨識使用新設定，先前採用修正及舊結果設定保留。設定說明明示擷取方式只用於範圍擷取，本頁／框選重辨固定 OCR；新語言會重新檢查模型，缺少時可下載。

新版 `dist/T07-dynamic-ocr/ebook2mp4/ebook2mp4.exe`，整個目錄搬移；SHA-256 `0746A8BA0C50DAFD39CA7FA42247A043F2712A074A308D87733D65C607106B6A`。27 項相關回歸通過（含新增繁中→簡中／block→line 真實 GUI 設定傳遞及既有真實 OCR GUI），無跳過；mypy 12 個來源檔案及封裝通過。詳見 [動態設定驗證](verification/dynamic-ocr.md)。未提交、未推送，舊成品保留。以下為歷史版本紀錄。

最終封裝實際啟動／正常退出通過。已清理 248,983,958 bytes；1,152 個封裝檔案獨占開啟／釋放通過，無本次殘留程序及占用，使用者舊版書稿視窗保留。

## 2026-10-27：局部辨識只捨棄本次結果

修正接受框選 1、2，捨棄 3 後繼續 4，卻把前次修正全部還原的問題。局部選項改「本次框選辨識：採用本次結果／捨棄本次結果」，僅適用最後一次框選的頁面。區域作業以自己的輸入為還原基準，最初擷取原文仍獨立保留；繼續修正與直接保存均保留先前接受的修改。重疊區域重試、跨頁與切換整頁流程也有回歸案例；不改磁碟格式。

新版 `dist/T07-region-decisions/ebook2mp4/ebook2mp4.exe`，整個目錄搬移。SHA-256 `4E1D178E4B53DC21EF4040E3BB907EFE5EF77047FD69E1EF53EF4554815F91AF`。分模組 **122 項完整回歸通過，377.163 秒，無跳過**；最後追加來源核對狀態修正後，**28 項相關回歸通過，96.962 秒，無跳過**。mypy 12 個來源檔案及封裝啟動通過；保留同程序 Tk interpreter 回收崩潰紀錄，未算成通過。根因、畫面與收尾詳見 [局部辨識決定驗證](verification/region-decisions.md)。未提交、未推送，舊成品保留。下方為歷史版本紀錄。

收尾清除 249,002,717 bytes；新封裝 1,152 個檔案獨占開啟／釋放全數通過，本次程序與視窗已退出。使用者目前開啟的舊版書稿視窗保留，請另開上述新版使用。

## 2026-10-27：PDF 命名與同頁連續局部辨識

接續 UI 配置更新，將入口改為「PDF 原頁與文字對照」，以「目前頁面文字／本批次擷取原文／本批次校對稿」區分工作結果與基準。版本入口改「朗讀稿與重載備份」；刪除命令統一「移除 PDF 批次」。警告處理改「本頁已核對／略過本頁警告」，略過再次確認且保留文字。模型已齊時停用下載並明示不需下載，消除零位元組安裝完成的誤導。

區域辨識加入活動進度條、保存內容單選、保留選擇後繼續修正；新 `start_pdf_candidate_retry` 以保留中的文字為下一次選取基準，支持同頁逐段累積，最後只存一個新批次。原批次擷取原文／人工稿／朗讀快照保留；放棄該頁修正回原基準，下一段失敗／取消保留先前文字。局部辨識結果仍待整頁核對，原批人工全文不自動合併到新批。

新版 `dist/T07-pdf-refinement/ebook2mp4/ebook2mp4.exe`，整個資料夾搬移；SHA-256 `0C0911F0BC4DB19505B66029E316EA3825E17694E9DA626C684CE3F039E62E0B`。完整 **117／117，278.817 秒，無跳過**；mypy 加 `--check-untyped-defs` **12 個來源檔案通過**。另有最後配置的針對性回歸、合成 PDF＋真實 Tesseract 連續兩段驗證及原生畫面證據。詳見 [驗證與限制](verification/pdf-refinement.md)。

封裝版實際啟動及正常退出通過。收尾清除 249,070,889 bytes 暫存，1,152 個封裝檔案獨占開啟／釋放全部通過，無本次殘留程序或占用。本次未提交、未推送；舊成品及開啟中的使用者書稿視窗保留。T08、T23 未在本次範圍內。以下為先前版本紀錄。

## 2026-10-26：UI 配置更新

已依使用者核定的 native mock 與按鈕位置建議調整正式 UI：全域儲存、確認頁內朗讀確認、三個任務頁籤、具名選單、專注模式、字級、批次狀態獨立欄及集中訊息。PDF／換行預覽最大化、縮放與候選操作固定；Gemini 加入段落導航、下一待確認、決定計數與持續阻擋資訊。既有保存、OCR、候選採用及取消規則保留。

新版 `dist/T07-ui-layout/ebook2mp4/ebook2mp4.exe`，整個資料夾搬移；SHA-256 `3C969ED43627B9450EF2456AF466F137EF7640C27EB028AE0BAAD5F3B0C3C54F`。完整 **101／101 通過、253.696 秒、無跳過**，含三語真實 OCR、原指定 9 頁 PDF 與新增 UI 回歸。mypy 11 個來源檔案、PyInstaller 封裝及新封裝啟動通過；已檢視真實原生主窗最大化／1040×640、PDF 與換行比較。見 [UI 配置驗證](verification/ui-layout.md)。

本次沒有提交或推送。T08 長稿續作與 T23 乾淨 Windows 安裝驗收仍未完成。下方成品資訊屬歷史，最新 UI 成品以上方為準。


## 原評估需求紀錄（已依後續授權實作）

**以下兩項已於本次使用者授權後實作**，原評估文字保留為歷史。現行規格已同步為 v1.2，詳見下節及 [驗證](verification/proofreading-ocr-optimization.md)。

2026-10-26 使用者追加 OCR 案例：「再簡單也不過了」被辨成 `FR Pu Al`，要求僅記錄與評估。已保留提供的截圖與 [OCR 優化評估](ocr-mixed-font-evaluation.md)。候選方向為標題／引文分區、模型與原圖字形對齊、原 PDF 渲染／前處理比較、可疑中英混淆提示與局部重試；尚未改程式或跑 OCR 實測。現行 Gemini 僅看文字，無法可靠從亂碼猜回原字；看圖備援若未來實作須明確選擇圖片送出。未排入 T08。

2026-10-26 使用者要求先記錄、評估但不實作：AI 校對時依文件主要繁／簡字體統一少數混入字，並將中文語境的半形標點改為全形。評估可行，需處理字體判斷不足、一簡對多繁及英文／網址／小數保護；詳見 [需求與評估](proofreading-normalization-proposal.md)。尚未核定細節或排入 T08；目前程式、成品與 Spec v1.1 的不自動轉繁簡規則均未變更。

## 目前：T01～T07 已完成

2026-10-26 追加 AI／OCR 優化：起點 `41f79f6`，實作 `e05c121`、審查修正 `9906504`。**目前新版 `dist/T07-optimized/ebook2mp4/ebook2mp4.exe`**，SHA-256 `39A1B3AA1E33ECD93F1B4A0592F2C4DB12AE701A7E0949E3850A1E216AD5B378`，整個目錄一起搬移；舊成品保留。

最終完整套件 **90／90 通過，169.405 秒，無跳過**，真實 Gemini 雙向繁簡／標點及原 PDF 大標題驗收通過；mypy 10 個來源檔案與 compileall 通過，包內 OpenCC 詞庫實際載入通過。舊 TXT 匯入測試因新增下拉選單誤定位，已限定匯入對話框並重跑全套。最後提交見 git log -1；完整結果、審查與清理見 [優化驗證](verification/proofreading-ocr-optimization.md)。

本次清除 **275,946,745 bytes（約 263.2 MiB）** 的模型副本、實驗圖片／專案、隔離工具、建置資料與快取；正式成品、提供的案例截圖及最終證據保留。最後本次程序 **0**；封裝 1,152 個檔案全部以獨占方式開啟後釋放，確認沒有殘留占用。重跑需重新準備隔離依賴；既有使用者模型及 outputs 未動。

- Gemini 送出前新增字體自動／繁體／簡體／保留及中文標點開關。`gemini_scope`／`start_gemini_review` 的 script／punctuation 參數隨候選保存；本批全文在本機判斷，至少 4 票及 80%，共用漢字不投票，證據不足保留。只傳選取文字；本機 OpenCC 0.1.7 詞庫在包內，不做地區詞替換。英文、網址、Email、數字、縮寫、中文檔名／路徑、程式碼受保護；模型擅改保護片段則拒絕候選。真實 Gemini 雙向統一與標點、選外保留、採用／撤回已通過，僅送合成短文。
- PDF UI 預設自動中英＋自動版面，需三語固定模型共 8,948,886 bytes；可選固定語言及 block／auto／line。公開 API 預設仍舊 block 語言以兼容。auto 比較版面及中英模型，存 selected_language、confidence、layout_fallbacks；信心不是正確率。原 PDF 的 `1. FR Pu Al` 大標題現在可讀回「再简单也不过了」，不依賴頁腳重複章名通過驗收。低解析附圖仍可能錯字，列待檢查。
- `start_pdf_retry(..., layout=..., region=(x0,y0,x1,y1), text_range=(start,end))`：正規化框選圖區＋原逐頁文字半開範圍，只能單頁。UI 左側拖曳框選、右側「本次文字」反白原文後，按區域重辨。按目前顯示的旋轉方向裁切，和整頁上下文候選比較，只替換選中原文字段；原批人工全文、其他文字／頁與歷史快照保留，新批仍以逐頁原稿重建。失敗／取消保留原頁文字。區域候選一律 pending，合併後也檢查可疑英文短行，不因只修一段就取消其他疑點。整頁對照後明確保留才能確認朗讀。
- TSV 用 literal QUOTE_NONE，禁止回到預設 CSV 引號解析；否則英文引號會把座標欄吞入正文。繁簡票數使用包內 ST／TS 字典 self-alternatives 排除里／后／干等共用字，禁止改回僅以單字轉換判斷。原雙軸審查 Standards 4、Spec 3 項 P2 已由原審查者複查解除。
- 新依賴及詞庫／授權均列 packaging/requirements-runtime.txt、NORMALIZATION-NOTICES.md、packaging/licenses；PyInstaller 收錄 OpenCC data／metadata。已從正式包內直接載入詞庫並驗證轉換與證據字典可用；本次未搶占使用者桌面啟動封裝 GUI，其他 DPI／原生整條操作仍待人工驗收。自動比較增加耗時，單頁仍共用 120 秒期限及取消 kill/communicate 規則。

T08 長稿分請求／部分成功續作尚未實作。**建議開新 session 接 T08**，先讀本交接最新追加及驗證；不要將此優化當成長稿續作或新增雲端看圖。下方較早資訊為歷史。

2026-10-26 T07 追加：已依使用者明確選擇，新增「已確認朗讀稿歷史版本」刪除，實作 `5c82ce4`。從「檢視保存版本與副本」選取朗讀稿後按「刪除所選朗讀稿」，確認後移除該版本；若是目前確認版本，同時清除確認。校對稿、來源、其他版本／批次及未存人工稿保留。先原子移除索引，再刪不再共用的快照檔；內容檔被占用時明確警告，索引儲存失敗不刪稿。Standards／Spec 獨立審查均零項。**目前新版為 `dist/T07-reading-delete/ebook2mp4/ebook2mp4.exe`**，SHA-256 `3BA969D9764D1D36AE3CB9590C5EC8C0E2FD4E81E663056C19C67264C63D9928`。詳見 [朗讀稿版本刪除驗證](verification/reading-history-delete.md)。下方原 T07 成品資訊保留為歷史。

追加完整回歸 **76／76 通過，126.002 秒，無跳過**；mypy 9 個來源檔案、compileall 及封裝建置通過。真實 Tk 測試檢查 600×420 版本窗控制可見與刪除流程；新封裝未啟動搶占桌面，實際操作請人工補驗。測試／建置暫存與模型副本收尾清除，清理紀錄見驗證文件。

2026-10-26，T07「Gemini 設定、指定範圍校對與差異採用」已實作。起點 `3226d3f`，主要實作 `7eae065`，審查修正 `acbd711`；最終文件提交見 `git log -1`。目前 master，無遠端推送。

正式新版 **`dist/T07/ebook2mp4/ebook2mp4.exe`**，SHA-256 `44A88303F30A45A8211F3BD1FA41D005952CF473A369D69D79F54890803C9828`；一起搬移整個 ebook2mp4 目錄。完整套件 **72／72 通過，206.612 秒，無跳過**，包含真實三語 OCR 及原指定 9 頁書稿；mypy 9 個來源檔案與 compileall 通過。雙軸審查原問題皆由原審查者確認解除。詳見 [T07 驗證](verification/T07.md)、[審查](verification/T07-code-review.md)、[清理](verification/T07-cleanup.json)。

本次清除 **246,553,970 bytes（約 235.1 MiB）**，隔離依賴與測試模型副本已刪；重跑請重新準備。正式成品、需求、outputs 及既有使用者 OCR 模型保留。最終本次測試／OCR／封裝程序 **0**，桌面自動化 kernel 已重設；封裝檔案以獨占讀取開啟後釋放，確認沒有殘留占用。桌面另有使用者操作，因此封裝驗證收尾只停止本次空白測試程序，未繼續搶占桌面。

下一張 **T08 — Gemini 長稿分段、取消與部分失敗續作**，票稿 `.scratch/pdf-txt-audiobook-video/v1.1/issues/08-gemini-long-draft-resume.md`。**建議開新 session 接 T08**，先讀 AGENTS、GLOSSARY、docs/adr、Spec v1.1、T07 驗證及 T08 票稿；沿用已核定 ProjectWorkflow／真實 Tk 測試邊界。TTS、音訊／影片及 T23 安裝仍未完成。

T07 入口及延伸注意：

- `gemini_settings`／`save_gemini_settings(key, model)`／`test_gemini_connection`。Windows DPAPI current-user 加密的金鑰在 `%LOCALAPPDATA%/ebook2mp4/gemini.json`，不進書籍專案，也支援 `GEMINI_API_KEY`。設定錯誤可由設定視窗重新保存；不要在日誌或文件記錄金鑰。
- 預設 `gemini-3.8-flash` 真實合成短文連線及指定範圍校對通過；舊 `gemini-2.5-flash` 雖列在服務清單，實際生成 404，不可僅靠列出模型宣稱可用。UI 可調模型 ID；不自動切換使用者模型。
- `gemini_scope(batch_id, start=0, end=None)` → `start_gemini_review(...)` → job `state/cancel/wait` → `finish_gemini_review(job)`；範圍為 Python 字元半開區間，UI 顯示 1-based 含尾。只傳所選文字與校對規則，未傳使用者書稿做真實驗證。T07 單次請求，需完整段落 JSON／STOP 才成功；T08 再做分請求、部分保存及重試，不把現有原子完整回應誤當長稿續作。
- `gemini_reviews(batch_id)` 回傳來源版本／範圍／模型、原文／候選／疑點、逐段決定及 before/expected/history 參照，另推導 stale。review JSON 每次不可變保存，索引保留原記錄順序，避免操作較舊候選後跳到另一筆。重開驗證內容檔及歷史 SHA-256；相對路徑可搬移。
- `decide_gemini(batch_id, review_id, paragraph, decision)`，decision 為 accepted/rejected，paragraph=None 只採用待確認段落，不覆蓋已拒絕段。`undo_gemini` 撤回本次全部採用。以 before 重建，保留選外與分隔符；先比對 expected 參照及 revision，舊候選不可覆蓋新稿。UI 未存人工稿也阻擋套用；採用改稿失效該批朗讀確認及 PDF mapping，舊快照保留。
- 請求在背景，取消不套用晚到結果，關閉等待停止與保存。若保存因跨視窗變更／原批移除而永久失敗，關閉須可明確捨棄；`discard_gemini_review(job)` 只釋放所屬已停止工作。不要移除該出口。新增非同步流程保留 after token 取消與連線 finally.close 規則。
- Tk UI 差異採可縮放獨立視窗、原文／候選左右等寬、字詞差異底色、疑點及分列操作；主視窗右側工具向下捲動可見 Gemini。已驗最小 1040×640 主窗／740×570 差異窗。封裝版啟動通過，原生選檔後完整校對路徑尚待人工補驗；其他 DPI／輔助工具與 T23 乾淨機安裝亦待驗。

## 目前：T01～T06 已完成

2026-10-26，T06「混合 PDF 自動辨識、異常頁確認與旋轉重試」已實作。起點 `2ae4c03`，實作 `fbb225f`、審查修正 `a2a24f9`，最終文件提交見 `git log -1`。目前仍為 master，沒有設定或推送遠端。

正式新版 **`dist/T06/ebook2mp4/ebook2mp4.exe`**，SHA-256 `9D9F1AF9C4882A2427BB174CB0755A2077EDAA2F05E6F53073706DD94F3BA5A5`；請一起搬移整個 ebook2mp4 目錄。最終完整套件 **62／62 通過，151.130 秒，無跳過**，包含三語真實 OCR 及指定 9 頁書稿；mypy 7 個來源檔案及語法編譯通過。雙軸審查原三項 P2 均由原審查者確認解除，Standards／Spec 零項未解決。詳見 [T06 驗證](verification/T06.md)、[審查](verification/T06-code-review.md)。

下一張是 **T07 — Gemini 設定、指定範圍校對與差異採用**，票稿 `.scratch/pdf-txt-audiobook-video/v1.1/issues/07-gemini-settings-review.md`。**建議開新 session 再接 T07**。先讀 AGENTS、GLOSSARY、docs/adr、Spec v1.1、T07 票稿及本次驗證；沿用已核定的 ProjectWorkflow／真實 Tk 測試邊界。Gemini、TTS、音訊／影片及 T23 安裝仍未完成。

T06 入口與保存規則：

- `start_pdf_extraction(..., mode='auto', language=...)` 逐頁優先文字層，沒有可用文字才 OCR。公開 API 的預設仍是舊文字層，UI 預設自動。所有模式結果不足 20 個字母／數字／中文字元或含異常字元會列待檢查；僅頁碼不得報正文完整。這是保守啟發式，不保證判別所有圖片正文。
- `pdf_source_preview(batch_id)` 驗證並讀取專案內 PDF 副本；來源移走不影響重做。UI 背景讀取缺檔／損壞來源，顯示可行錯誤並可關閉釋放 grab／executor。
- `start_pdf_retry(batch_id, pages=[...], language=..., rotation=0|90|180|270)` 或 `failed_only=True`。只執行目標頁，順時針旋轉，未選頁保留原逐頁狀態；`job.numbers` 為本次實際處理頁次。取消後只補齊目標未完成頁，成功與失敗進度保留。
- `pdf_extraction_pages(job)` 提供整個批次範圍候選；`finish_pdf_extraction(job, accepted_pages=[...])` 針對重試逐頁採用，未採用／非目標頁沿用原逐頁原稿。每次採用建立新批次，**不搬入原批全文人工校對**；原校對稿及朗讀快照保持不變。原批已有人工改稿而 mapping_valid=False 時，其 `resolved` 異常在重建原稿的新批重新列 pending，避免人工補文消失卻通過確認；明確 `skipped` 可沿用。新採用異常頁重新確認，批次層級異常也保留。
- UI「逐頁原稿／頁圖」可選頁、旋轉／本頁 OCR／只重試失敗，切換原逐頁原稿與原批校對全文比較，勾選是否採用本頁候選；範圍／OCR 設定可展開，修改範圍／語言／模式後另建候選。採用前保護未存編輯；取消儲存提示仍保留編輯與候選。明確保留／略過來源異常後才可確認相關朗讀稿；略過不會自動刪文。
- 自動／OCR 取消按鈕先取消並保留候選供比較，必須明確採用才保存取消批次；再次關閉可捨棄候選。舊文字層匯入仍沿用 T04 直接發布新批次的行為。

正式封裝已用 Windows 原生選檔走過開啟合成專案→對照→包內 OCR→候選→明確採用→關閉及重開驗證，另有 1040×640／740×570 最小視窗截圖。原設定區擠壓圖文區，已改成收合設定及分列控制。其他 DPI、輔助工具及乾淨機安裝仍待驗收。

本次清除 **246,358,618 bytes（約 234.9 MiB）** 的測試模型副本、工具、建置資料、合成專案、測試資料及快取；正式成品、指定書稿 TXT、使用者既有模型、需求及最終證據保留。最終本次測試／OCR／建置／封裝程序 **0**，沒有未釋放資源；見 [清理紀錄](verification/T06-cleanup.json)。隔離依賴已清除，重跑請依驗證文件重新準備；目前版本的建置重用了已驗證 T05-ui 引擎／DLL，無需重新執行引擎安裝程式。

## T05 歷史交接（下方狀態以當時為準）

2026-10-26 UI 追加：基線 `75d37ea` 之後新增 `ProjectWorkflow.remove_pdf_batch` 及「移除 PDF 文件」，並將「新增 PDF 範圍」改為「新增 PDF 文件」。移除僅作用於所選 PDF 批次，確認後原子發布索引；取消或寫入失敗保留未存編輯與清單。外部原始 PDF、其他批次、匯出及專案內歷史檔案保留。最新成品改為 **`dist/T05-ui/ebook2mp4/ebook2mp4.exe`**，SHA-256 `A107E1E7D7A32A5DD35862F7624BDD4D5F740E955D1C169C350309D34CDE71BE`。完整套件 53 案例：48 通過、5 個需另設 OCR 環境的案例跳過，無失敗；mypy／編譯／重建及實際啟動通過，1040×640 真實 Tk 及確認提示可見。詳見 [PDF 文件操作驗證](verification/PDF-file-actions.md)，原 T05 的實際書稿輸出仍保留。本次追加驗證與建置暫存已於收尾清除，既有使用者程序不動；後續提交可由 git log -1 查看。

T01～T05 已實作。T05 起點 `df85a02`、主要實作 `09600e6`；模型狀態審查修正、實際書稿基本測試與最終交接見後續提交（`git log -1`）。目前分支 master，未設定或推送遠端。歷史 T04 詳見 docs/verification/T04.md。

當時下一張為 **T06 — 混合 PDF 自動辨識、異常頁確認與旋轉重試**，票稿 `.scratch/pdf-txt-audiobook-video/v1.1/issues/06-mixed-pdf-anomalies-retry.md`；現已完成，請以上方目前狀態為準。

主要測試邊界沿用已核定的 ProjectWorkflow 與真實 Tk UI。格式 v1 支援同書多 TXT／PDF 批次，來源、不可變逐頁原稿、校對版本、朗讀快照及重載副本各自保存並帶 SHA-256。任何人工編輯、改稿與重載取消該批目前朗讀確認；舊快照及其他批次不變。多視窗索引變更須重開，寫入鎖及原子發布規則沿用 T01～T04。

公開 PDF 流程：inspect_pdf → preview_pdf_page → start_pdf_extraction → pdf_extraction_pages → finish_pdf_extraction。start 新增 mode='text-layer'（預設）或 'ocr'，language='繁中＋英文'／'簡中＋英文'／'英文'；設定獨立於 TTS。每次 finish 建立新批次，不覆寫既有校對稿。pdf_extraction_pages 只接受所屬已停止候選，統一補齊取消頁，供 UI 比較及保存共用。PdfExtraction 的 pages 仍只回傳已完成頁副本，提供 status、cancel、wait。保存失敗保留候選供重試；discard_pdf_extraction 釋放已停止候選。

OCR 完成先顯示候選圖文對照，再明確「採用為新批次」或關閉捨棄；取消擷取並保留完整頁會建立取消批次。method 支援 text-layer／ocr；逐頁設定保留語言代碼、模型 commit、引擎、300 DPI、25M pixels 上限與 psm=6。狀態 success／pending／failed／cancelled，異常沿用 source_issues、resolve_source_issue、confirmation_blockers。全文編輯使 mapping_valid=False，不自動恢復；原始逐頁資料不改寫，正文不加人工頁碼標籤。

模型公開入口 ocr_models(language)、start_ocr_model_install(language)。安裝工作提供 state（status／downloaded／total／phase／error）、cancel、wait。模型為官方 tessdata_fast 4.1.0 commit `65727574dfcd264acbb0c3e07860e4e9e9b22185`，大小及 SHA-256 固定於 ebook2mp4/ocr.py；完整校驗後逐檔原子發布，取消保留已安裝模型，移除未完成下載及鎖。UI 首次查詢大小、忙碌期間語言變更補查，顯示與選擇一致前不准安裝。跨視窗採模型安裝鎖，中斷鎖需關閉視窗後移除。

Tesseract 5.4.0.20240606 隨包提供，預設 `_internal/tools/tesseract/tesseract.exe`。模型預設 `%LOCALAPPDATA%/ebook2mp4/ocr/<commit>`，只在介面明確操作時連網下載，不上傳書稿或頁圖。開發可設 EBOOK2MP4_TESSERACT／EBOOK2MP4_OCR_HOME。OCR 每頁 subprocess，不經 shell、無主控台、120 秒上限；取消 kill 並 communicate 等待，刪頁圖暫存。PDFium 共用鎖及逐頁資源關閉規則不變，TXT 仍惰性載入 PDF/OCR 元件。

**T05 交接當時 T06 尚未實作（現已完成，見上方）**：當時的自動模式逐頁判斷、指定頁／旋轉、只重試失敗頁、候選逐頁採用等仍待 T06；不能把 T05 的全部強制 OCR 及新批次採用當成這些功能的驗收。不要直接用 OCR 重試覆寫校對稿。

固定 Python 依賴見 packaging/requirements-runtime.txt／requirements-dev.txt。建置先安裝隔離工具至 `.scratch/build-tools` 並設 PYTHONPATH，再執行 packaging/prepare_ocr.py（建置時需 7-Zip，固定來源及雜湊，解壓而不執行安裝程式），最後 packaging/build.py。OCR 準備會放 27 個引擎／必要 DLL 至 `.scratch/ocr-runtime`；PyInstaller spec 必須有此目錄。Tesseract／模型及 DLL 授權來源見 packaging/OCR-NOTICES.md；T23 仍須完成授權／源碼交付與乾淨 Windows 安裝。

2026-10-26 最終完整驗證 **50／50 tests 通過，74.073 秒，無跳過**；mypy 檢查 7 個來源檔案及語法編譯通過，修正後 onedir 重建及實際啟動通過。Standards／Spec 初審 P2 均由原審查者確認解除，兩軸零項未解決。原始結果、真實工具／替身範圍、視覺及審查證據見 docs/verification/T05*。

使用者追加基本測試：`E:/Leo/assets/ebooks/靈性開悟/book1-ch1.pdf`，9 頁均無文字層。以簡中＋英文真實 OCR 9／9 成功，30.619 秒，首頁標題與正文開頭對照通過。正式輸出 **`outputs/book1-ch1.txt`**，UTF-8、16,605 bytes、6,239 字元（含原生換行），SHA-256 `2bb7a9eb6f5b3c6061e5a1badc9551d2cd7e86b4d1921b82af4a2fa20828b925`；專案重開與匯出解碼相同。outputs 排除 Git，保留本機成品而不提交書稿全文。報告 docs/verification/T05-real-book.json 不含全文。另有真實三語引擎搭配合成掃描頁及模型網路下載驗證，不能宣稱所有實體掃描零錯字。

可重跑測試：設 EBOOK2MP4_REAL_OCR_HOME 指向含 eng／chi_tra／chi_sim 的模型目錄，EBOOK2MP4_TESSERACT 指向包內引擎，EBOOK2MP4_BOOK_PDF 指向使用者檔案。未提供環境變數會明列跳過相關實際測試，不能當全套 OCR 通過。Windows 沙箱 TEMP 有寫入限制時，將 TEMP／TMP 指向專案內可寫測試目錄。

正式新版在 **`dist/T05/ebook2mp4/ebook2mp4.exe`**，SHA-256 `4A9A568A3598A551E78977FD614B1F356E463FE266C838D96B072C73FD72EFED`。因使用者開著舊 dist/ebook2mp4，這次未覆寫舊版或關閉使用者程序。包內引擎已用完整測試驗證辨識，主程式已實際啟動；完整封裝原生選檔→匯入→下載→OCR 尚待人工補驗，其他 DPI／輔助工具及 T23 安裝也未驗收。

已依 AGENTS.md 清除本次測試專案、下載副本、模型測試資料、合成書稿、隔離工具、建置暫存與快取，共 **560,798,951 bytes（約 534.8 MiB）**。清理目標先確認位於專案內；保留正式成品、指定書稿 TXT、需求及最終證據。最後本次測試／建置／OCR／封裝驗證程序為 **0**；詳見 docs/verification/T05-cleanup.json。桌面自動化階段在收尾重設，既有使用者舊版及 prototype-qa 未動。

Windows 目錄擁有者使 Git 要求安全目錄設定，每次使用 `git -c safe.directory=E:/Leo/Projects/ebook2mp4 ...`；未改全域設定。沙箱限制 .git 寫入，提交使用提升權限命令。
