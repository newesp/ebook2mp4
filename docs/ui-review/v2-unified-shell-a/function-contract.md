# A：功能與資料保留契約

此表獨立於 [布局對照](layout-contract.md)。A 沒有修改或執行產品；下列全部是 B～E 的保留及驗收責任，不宣稱功能回歸通過。

| 契約 | 現行持有者／入口 | 後續可觀察驗收 |
| --- | --- | --- |
| 原始來源不覆寫；人工稿、草稿、來源擷取及朗讀快照分開 | ProjectWorkflow、ManuscriptWorkspace、SourceTools | 修改人工稿 → 暫存 → 重開／來源重載預覽 → 確認原始來源未變、快照仍不可變；不擴大 UI 狀態磁碟保存 |
| 保存須原子、失敗不前進，舊稿先備份 | workflow 提交、cleanup.apply、restore_version、source.apply | 令保存失敗 → 按主操作 → 確認留在原頁且輸入／ready不提前變更 → 重試 → 確認新版本／備份正確 |
| 過期結果拒絕、AI 部分完成不冒充全文成功 | workspace job/review、source pending、preview identity | AI／來源工作開始 → 修改基線／切批／切專案 → 舊結果返回 → 確認只更新原工作，不覆寫目前稿及 shell |
| 文稿無重複同意框；雲端 TTS 同意預設勾選且取消後禁止送出 | AI workspace 命令；VoiceDialog.consent／NarrationDialog consent | 取消同意 → 切頁 → 返回 → 發送 → 確認零請求；改本機 → 確認不顯示 key／無關同意；測試採受控服務，不新增私人內容或計費請求 |
| 設定可選或輸入，保存／重載保留自訂值 | AiSettingsPage、VoiceDialog、ServiceDialog、影片設定 | 輸入自訂模型／voice → 保存 → 切頁／重載 → 確認值相同；readonly 選項仍用下拉 |
| 偏好／連線／本批／全書保存語意不同 | manuscript.save_manuscript_settings/save_connection；VoiceDialog scope；VoiceDefaultsPage | 改偏好 → 確認即保存；只改連線未提交 → 返回／重開 → 依既有策略；存全書預設 → 確認不回寫舊批次，只有明確選批套用才更動 |
| 任務按 project／batch／route 隔離 | production.pages、flow、production lock、每頁 job/check_job | 開任務 → 切頁／批／專案 → 返回任務 → 確認同一 job；audio、total-audio、batch-videos 與本批影片不共用錯誤快取或成品 |
| 續作／增量／部分完成／取消／重試保存及上一份成功成品 | narration／assembly／video job state 與 result | 中斷／取消／部分失敗 → 返回 → 續作／重試保存 → 確認只重用匹配區塊、舊成功成品仍可播放 |
| 全書合併音訊專用，不被 MP4 偏好改導 | AssemblyPage(movie=False)／AudioAssemblyWorkspace | 儲存影片偏好 → 開全書合併 → 確認只有 MP3／SRT，按製作只叫 start_total_audio；無 MP4 勾選、無額外 TTS |
| 影片三路徑保持設定／來源／任務／版本隔離 | BatchVideoTarget、TotalVideoPage、AssemblyPage(movie=True) | 本批→全書統一素材→沿用各批影片 → 保存不同素材 → 返回 → 確認各自值與來源相符；停頓不重複加入 |
| 接點定位／閱讀／保存狀態不倒退 | JoinPage signature、reading_positions、AudioJoinWorkspace saved_state | 首次開接點 → 確認前批末行／後批開頭；開詳情／列表／校對再返 → 確認閱讀位置；改停頓 → 保存失敗／重試 → 確認真實 dirty／saved |
| 版本／成品歸屬、來源比較、播放／另存／返回 | VersionPage、OutputVersionsPage、MoviePlayback | 開各路徑成品 → 比來源 → 播放／另存 → 返回原入口；失效版本仍可辨認，未授權還原不覆蓋現稿 |
| 離頁停止播放、任務正常繼續；關閉完整清理 | 每頁 close/release/stop、production.shutdown、executor／timer | 播放／製作 → 切頁 → 確認播放停止而同 job 繼續；正常退出 → 確認自己建立的 process／timer／lock 釋放，不強殺使用者程序 |

## K03 八項設計條件承接

原票 #5 因 UI 工作移交而關閉，沒有免除下表。包管理在 packages，服務／音色／語速、固定範例／選取文字試聽、正式製作仍走 voice／narration，共用同一 shell。

| 條件 | A 設計及後續限制 |
| --- | --- |
| 1 安裝／移除及試聽／製作路徑 | 語音頁 → 管理語音包 → 選本機 ZIP → 檢查並匯入 → 返回選音色 → 固定範例／選取文字 → 前往音訊製做；移除獨立 destructive 確認，保留書稿、有效快取及成品 |
| 2 未安裝／檢查／成功／缺包／損毀／不相容 | 同一包摘要與區域狀態；未就緒停用正式試聽／製作，保留路徑和可行的選包／重試入口；不因顯示錯誤重設使用者輸入 |
| 3 載入／合成／失敗／取消 | voice 的進度及取消只在工作中顯示；失敗保留試聽稿、設定與前次有效結果；取消中等資源釋放才報已取消 |
| 4 本機／音色品質／不需 key | 本機標示 CPU 與「文字不傳送雲端」，隱藏雲端 key／同意；音色僅標示已有實際證據的品質。現有「人工品質驗證：尚無」保留，不造推薦音色 |
| 5 細節按需展開 | 包版本／引擎／前處理／授權／音色清單有界詳情 owner；摘要一列；不常駐技術 id 或整頁授權長文 |
| 6 輸入與窄版 | 同窗返回保留 ZIP 路徑、選服務／音色／語速、試聽全文及 scope；聲音設定／試聽文字頁籤避免巢狀捲動，保存／下一步固定 |
| 7 忙碌／取消／刪除語意 | 安裝中停用衝突更改／移除；取消不是移除，移除不是刪書稿或成品。確認移除與保留並列；busy 可用性由真實狀態提供 |
| 8 閒置卸載／限時及設計確認 | 數值待 K01 CPU／程序／記憶體／品質實測決定。A 不填猜測 timeout，不改後端政策；新外框須使用者確認；K01／K02／K04～K09 的離線、品質、生命週期、乾淨 Windows 封裝驗收留原票 |

## 分批驗收責任

B：代表頁結構、父容器、描述／命令及回呼隔離。C：全 20 列及本盤點所有子路由實際接入，逐列查 identity／正常外層布局／active 命令；無空占位頁。D：內容整合及繼承未測矩陣。E：跨頁與正式 `dist/ebook2mp4` 獨立操作、清理。每階段分別記功能、mock布局、原生與正式 EXE；A 靜態圖與幾何檢查不抵任一 runtime 驗收。
