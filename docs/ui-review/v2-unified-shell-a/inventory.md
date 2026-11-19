# A：實際入口、狀態與責任盤點

2026-11-13。依工作區磁碟來源盤點；來源 SHA-256 見[基線](../../verification/v2-unified-shell-a/source-baseline.json)。GitHub #12／#13 已讀回，與本機階段及 20 列矩陣一致。本頁不是執行期驗收結果。

下表的 id 是**擬定路由 id**，不是聲稱產品已有同名 API。現有 `manuscript.line-break-preview`、`manuscript.versions`、`manuscript.ai-settings`、`manuscript.source` 已有穩定 id；其餘目前多靠物件身分、kind 或 tuple key 路由。圖檔使用短 id，B 應補明確 namespace，不能用顯示標題識別路由。

| #13 列／擬定 id | 實際入口與程式接點 | 現有父容器／內容擁有者 | 子狀態與返回 |
| --- | --- | --- | --- |
| 1 `manuscript` | `desktop.py:Workbench` → `show_step(1)`；`manuscript_desktop.py:_build/render_step` | shell.workspace；來源及同一 Text 編輯器由 ManuscriptWorkspace 持有 | PDF／TXT、原稿顯隱、窄版原稿／文稿、搜尋取代、AI 全文／選取、候選差異、局部還原、重試／部分完成／取消；返回保留 Text、undo、選取、插入點、yview、分隔比例 |
| 2 `cleanup` | 編輯 → 整理換行預覽 → `cleanup_line_breaks/open_tools(3)` | `InnerPageHost.content` → LineBreakPreview | 有變更／無變更、保存失敗、候選過期；`close_tools` 返回同一編輯器；apply 先保存備份，才改目前全文 |
| 3 `versions` | 直接「版本紀錄」→ `show_versions/open_tools(0)` | `InnerPageHost.content` → VersionPage | 文稿／朗讀版本／備份／歷史 AI 候選、唯讀差異、刪除確認、還原前備份；歷史候選沿用本入口，不另造重複入口 |
| 4 `ai` | AI 設定 → `gemini_settings/open_tools(1)` | `InnerPageHost.content` → AiSettingsPage | 偏好／本機連線展開、測試中／成功／失敗；偏好變更即保存，儲存設定另含連線；返回文稿 |
| 5 `pdf`／`pdf-region` | 匯入 PDF／來源處理／PDF 原頁對照 → `import_pdf/compare_pdf_pages/open_tools(2)` | `InnerPageHost.content` → SourcePage／SourceTools | 處理設定、文字層／OCR、模型安裝、全頁／框選原頁＋對應文字、擷取中／取消、預覽／採用／放棄、繼續修正；返回文稿並保留現稿 |
| 5 `txt` | 匯入 TXT／重新載入來源 → `import_txt(reload=...)` → `SourceTools.import_file/load_txt` | 同 SourcePage；來源、import_preview／pending 由 app 持有 | 編碼選單／手動選 Big5／CP950、解碼失敗／警告確認、預覽、現稿副本／取代／取消；返回文稿 |
| 6 `issues` | 來源異常 → `review_source_issues` → `open_issue_view` | 同 SourcePage；不是另一個來源物件 | 空／有異常、異常選取／定位、資訊／原頁切換、已處理／明確略過；返回恢復處理頁／文稿；空狀態不得留下舊 Canvas scrollregion |
| 7 `project-info` | 專案 → 專案位置與來源資訊 → `show_source_info` | **目前借來源頁** `open_tools(2)`，覆寫 `source_tools.detail` | 建議獨立唯讀 content port，複製路徑／來源資訊；記住來源入口，從製作頁開啟時返回原製作頁，而非固定跳文稿 |
| 8 `voice` | 2 試聽與製作／語音設定與試聽 → `Workbench.voice_settings` → `ProductionWorkspace.show('voice')` | `production.host` → VoiceDialog／VoiceWorkspaceLayout；底列另建於 app.actions | 本批／全書預設、歷史任務設定、服務／音色／模型／語速／節奏、固定範例／選取文字、同意、試聽載入／合成／播放／停止／失敗／取消；返回文稿，設定與試聽稿不重設 |
| 9 `narration` | 音訊製做 → `show('narration')` → NarrationDialog | `production.host`；actions 另建於 app.actions | 區塊清單、任務歷史、恢復原設定、尚未開始／檢查中／製作中／部分完成／失敗／中斷／取消中／已取消／等待保存／完成、重新開始；返回語音設定 |
| 10 `narration-detail` | 朗讀稿與任務設定／狀態詳情／選區塊錯誤 → `toggle_info/show_status/show_block_error` | NarrationDialog.info_frame／info_tabs | 朗讀快照＋設定、狀態＋錯誤 Text；內部頁籤可共宿主；返回區塊清單保留任務、選取、各 Text yview |
| 11 `assembly` | 全書合併 → `show('assembly')` → AssemblyPage(movie=False) | `production.host` → AudioAssemblyWorkspace；自有 footer 在 app.actions | 選有效批次、排序、停頓、來源檢查、接點確認、任務／來源詳情、保存失敗／重試、播放／另存／版本；只製作總 MP3／SRT，返回音訊製做 |
| 12 `joins`／`join-detail` | 合併 → 檢查接點 → `open_joins`／JoinPage(movie=False) | JoinPage 為 AssemblyPage 子元件；AudioJoinWorkspace 另建 footer 於 app.actions | 首次定位前批末行／後批開頭、接點選擇、校對前／後批、片段長度、試聽、警告詳情、文件列表暫切、勾確認、保存失敗；校對往返與同接點閱讀位置依簽章還原；返回合併 |
| 13 `video-batch` | 本批成品 → 製作 MP4／影片範圍本批 → `batch_video/show('batch_video')` | `production.host` → TotalVideoPage(batch_id)／VideoTabs | 畫面與素材、來源與順序、任務與成品、圖片／短背景重複或停格／長背景裁切、時間預覽、來源失效、取消／保存；返回原音訊頁 |
| 14 `video-book` | 影片製作 → 全書 → 統一素材 → `open_video/show('video')` | `production.host` → TotalVideoPage(batch_id=None) | 三頁籤同上、總音訊前置條件、成品來源／版本詳情；不新增 TTS；返回原合併／成品入口 |
| 15 `video-merge` | 全書影片 → 沿用各批影片 → `show('merge')` → AssemblyPage(movie=True) | `production.host`；VideoTabs、舊 OutputControls 仍參與此分支 | 影片選批／排序、解析度、既有來源與任務／成品、設定隔離；不因切換方式挪用 audio 草稿；返回原入口 |
| 15 `video-joins` | 沿用各批影片 → 檢查影音接點 → JoinPage(movie=True) | AssemblyPage 子元件；**不同於 AudioJoinWorkspace** | 前後畫面／文字、片段播放／停止、接點檢查、校對來源及返回；不能漏在音訊接點測試之外 |
| 16 `outputs`／`output-detail` | 成品版本／版本與來源比較／OutputControls.open → `show_versions/show('versions')` | `production.host` → OutputVersionsPage | audio／total-audio／batch-videos、missing／stale／error／ready、來源比較、技術參照展開、另存、前往正確來源／製作；return_page 保留來源物件 |
| 16 `movie-player` | 成品播放 → `OutputVersionsPage.play`、各製作頁 play／MoviePlayback | 播放 frame 嵌於既有內容；不是系統播放器 | 音訊播放、MoviePlayback 解碼／更新／停止／返回；離頁停止預覽並釋放播放資源；不停止原製作任務 |
| 17 `services` | 語音 → 新增／管理服務 → `manage_services/manage_current_service` | `production.host` → ServiceDialog；其 ScrollPage 目前一律建捲軸 | 新增／指定服務編輯、provider 差異、key 顯示／遮蔽／沿用、檢查、dirty 離開選擇、刪除確認／取消／失敗；返回試聽原稿與節奏，不自動試聽 |
| 18 `packages` | 本機語音 → 管理語音包 → `manage_local_packages` | `production.host` → PackagePage；獨立內容／操作列 | 未安裝／檢查／成功／缺包／損毀／不相容、路徑記憶、詳情／授權、匯入／移除／取消／失敗；返回 owner 並重讀包狀態；不要求 key |
| 19 `defaults` | 語音 → 全書預設 → 套用既有批次 → `open_defaults` | `production.host` → VoiceDefaultsPage；production.pages 的 defaults key | 空／選批、影響摘要、製作忙碌、全書預設已變更、某批未存設定、套用成功／失敗；返回原語音頁；不改未選批次 |
| 20 `create` | 專案 → 建立 → `create/choose_new_folder` | 目前 import_panel 為 workspace 的另一內容分支 | 無專案／既有專案建立、書名／資料夾、錯誤；may_leave 先保護現稿；空白資料夾契約保留 |
| 20 `imports` | 文件列表匯入／管理 → `import_txt/import_pdf/rename_batch/move_batch/remove_pdf` | DocumentList 命令 → Workbench／SourceTools | 檔案選擇、解碼／PDF 進入內容 port、重新命名、排序、移除確認；保留選取與未存稿保護，不另造無功能管理頁 |
| 20 `messages` | 訊息記錄 → `Workbench.show_messages` | **目前 Toplevel**，可複製唯讀 Text | 建議同窗唯讀頁；最近操作／空／長訊息／錯誤；返回原路由與原捲動位置 |
| 20 原生系統介面 | 專案開啟／選檔／另存／選資料夾、rename 輸入、不可逆操作確認；`filedialog/messagebox/simpledialog` | Windows 原生對話框，短暫的 owner-bound modal | 保留理由：選取 OS 資源與明確確認；不得把編輯／長文工作重放 Toplevel。開啟失敗回目前頁，不能丟草稿或清空選取 |

## 目前可到達與歷史程式的區別

- 現行主線 `_build` 建 SourceTools／AiSettingsPage／VersionPage／LineBreakPreview；PDF 與 AI 工作在 ManuscriptWorkspace 內執行。
- `pdf_desktop.PdfDialog`（含設定與資訊 Toplevel）、`gemini_desktop.SettingsDialog/ReviewDialog` 仍有來源與歷史測試，但在目前 `ebook2mp4` 主程式路由搜尋中未找到呼叫者。`desktop._legacy_source_info` 同樣無現行入口。列為相容性來源；不能把這些檔名當作仍開放的主路由，也不能在 C 無意恢復舊彈窗。B/C 應加現行入口測試防回歸。
- `ui_mock.py` 是舊展示程式，不屬現行產品路由。tooltip 與通知的短暫 Toplevel 是共用行為，不當成獨立工作頁；仍須正確綁 owner、清 timer。

## 共享布局越界與處理

[機械候選清單](../../verification/v2-unified-shell-a/source-baseline.json)含 50 個 shared／跨容器呼叫。這是搜尋候選數，**不是 50 個確認缺陷**。以下按父層責任人工分類；不能只禁用一組字串就宣稱 C 通過。

| 來源接點 | 現況 | B／C 的處理與攔截 |
| --- | --- | --- |
| manuscript_desktop.render_step／layout_workspace／update_stats | 隱藏 workspace、顯示 production；依 audio／video／inner 分支算 DocumentList 軌道；更新 footer | shell 持有唯一內容宿主與軌道；頁面只發描述。Configure／after 回呼經 shell 的 activation token，不可隱藏頁重寫標頭 |
| production_desktop.sync_chrome／sync_summary／refresh_task_banner | 修改 app.actions／stats／status／list_header、跨容器 grid tabs／page.actions，另造全域 task_bar | 改為頁面呈現＋任務摘要資料；shell 自己排同一導覽／底列，禁止 `grid(in_=app.actions)`；背景任務只更新自己的 task store |
| workspace_layout.ProductionPageLayout.set_active | 改 footer 顯隱；footer 雖固定 parent，但並非唯一共用 ActionBar | 融入 shell 命令生命週期；保留 VoiceDialog 的域狀態，移除 layout 對全域 footer 的權限 |
| voice_workspace 的 voice_footer | 在 app.actions 建另一套範圍、保存、下一步與返回 | 範圍移交共用工具描述，動作移交 ActionSpec；試聽文字／播放屬局部 content port |
| narration_desktop.actions／layout_actions／layout_status | 自有 footer，讀 app.actions 寬，production 再配置；另有列表開關 | 移交 shell，保留塊清單／詳情、歷史、進度資料；只保留一個文件開關入口 |
| assembly_workspace.set_active／resized | 自有 footer，改 list_header.padding／documents.rowconfigure，窄版排程 toggle_focus | 同上；自動窄版行為不得覆蓋使用者列表偏好。shell 計算可見範圍，頁面不能寫其他區域 |
| assembly_join_workspace.set_active／resized | 共用列表／header 軌道與 app.actions 仍由接點頁配置，窄版文件／詳情切換 | 保留閱讀位置／簽章與 source token；拿掉共用區配置權。左右 JoinTextPane 仍各自擁有 Text 捲動 |
| outputs_desktop.OutputControls.refresh | 可 pack production.method_control；把成品頁／內容 action 重排 | 描述影片適用範圍／動作；禁止更新其他頁工具；音訊專用路徑不重新出現 MP4 勾選 |
| total_video_desktop／assembly_desktop 的 grid(in_=...) | 有些是頁面自有 content 內部，但依賴共同祖先跨子容器顯示；局部 footer 自排 | 不全部判成外框越界；B/C 將內容建立在最終 port 父容器。局部頁籤可保留，但全域標頭／底列移交 shell |
| desktop_shell 內部 geometry | shell 本身的合法責任，兼有 install_legacy_handles 別名 | 保留既有類別作基礎；移除別名的布局用途。不能加第二套 shell 或保留舊 controller 與新 shell 搶軌道 |

## 資料、背景任務與釋放持有者

- ProjectWorkflow 持有磁碟資料、來源／草稿／朗讀快照、版本、任務／成品路徑及原子提交。Workbench 持目前 flow／batch；shell 不接手保存，不新建「切頁即保存全部」契約。
- ManuscriptWorkspace 持編輯器與 undo、AI job／review、SourceTools 預覽、executor／source_future、autosave／poll／resize token。C 的 adapter 要保留這些物件，不用換容器重建 Text 消除狀態問題。
- ProductionWorkspace.pages 目前以 `(id(flow), batch_id 或 None, kind)` 保存頁面，另有 service_page／package_page。VoiceDialog、NarrationDialog、AssemblyPage、TotalVideoPage 各持自己的 job／check_job／timer／player；flow／底層鎖是任務與專案隔離依據。切頁保持任務，只停止所屬播放。
- JoinPage 持接點／source signature／閱讀位置／restore token；OutputVersionsPage 持 return_page／requested_route、播放與檢查。返回目標應保存 route＋project generation＋scope，不能只憑目前全域 batch 推算。
- B 擬定生命週期：activate → describe／command；deactivate → 收回共用呈現與命令權、停局部播放／tooltip；dispose → 解除 binding、cancel 自己的 timer、等待已發出的 job 正常清理。晚到 job 回傳可以保存原任務結果，但需要相同 activation token 才可刷新共用外框。切專案另遞增 project generation。
- 不用 `after_cancel` 取消尚在執行的計費／製作任務。沿用 job.cancel／close／release；釋放等待、失敗及尚未保存結果須呈現真實狀態。

## B／C 不可漏掉的操作路徑

1. 文稿 → 語音 → 音訊 → 合併 → 接點 → 校對 → 返回接點 → 影片三種範圍 → 成品 → 返回。確認同一 shell、同一 DocumentList 及父容器；列出 widget identity 與正常 Configure 後基準線。
2. 留下未存輸入 → 開服務／資訊／訊息／版本 → 返回。確認輸入、選取、捲動、頁籤、列表偏好保留。
3. 開任務 → 切頁／批次／專案 → 舊回呼到達。確認原工作正常保存，目前頁標頭與命令不被覆寫。
4. 取消雲端 TTS 同意 → 切頁並返回 → 按試聽／製作。確認不送出且不重勾。改本機 → 確認隱藏雲端欄位。
5. 保存失敗 → 查看錯誤 → 重試。確認未提前前進、未清掉輸入、舊成功成品可用。

上述是後續可觀察驗收路徑；A 沒有執行這些產品操作，C／D／E 均保持待驗。
