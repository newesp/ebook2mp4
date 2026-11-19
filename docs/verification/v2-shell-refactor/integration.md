# 全頁外框接入及功能保留

本輪沿用目前 UI。沒有套用前輪未核准的設計圖。`baseline/` 是重構前原生畫面；`before-track-fix/` 保留跨頁空列失敗；`native-final/` 是最後來源的原生驗收。

## 父層及命令責任

`DesktopShell` 唯一持有 NavigationBar、DocumentList、WorkspaceFrame、ActionBar 的外框配置。文稿、InnerPageHost、ProductionWorkspace 都在同一個 WorkspaceFrame 建立。製作分頁在固定 host 建立；共用導覽不再跨父容器配置。切頁只切換既有內容，不重建編輯器。

控制器交付 `ShellPresentation`、`HeaderBand` 及 FooterPort。shell 統一配置標頭帶、文件列表、換列、內容根、固定操作列與任務提示。切頁會清除上一標頭帶的 minsize，避免影片列在返回後殘留。頁面只保留 port 內既有內容及操作分組；FooterPort 的父容器、位置、顯隱與按鈕建立由共用程式持有。`describe()` 提供穩定 ActionSpec；PageActionButton 使用固定 Tcl dispatcher，動態變更 command 也不能繞過目前頁／專案／停用檢查。

InnerPageHost 繼續持有工具內頁的返回、區域摘要與 ActionBar。主頁不因內頁而重建。ProductionPageLayout 改為局部內容 adapter，沒有外框顯隱權。舊 app 別名保留供控制器讀取及資料／狀態相容，不再作共用容器布局入口。

## 接入矩陣

| #13 範圍 | 路由／內容 port | 動作與狀態持有者 | 本輪證據 |
| --- | --- | --- | --- |
| 文稿 PDF／TXT、搜尋、候選 | `manuscript` → WorkspaceFrame／panes | 原 ManuscriptWorkspace；同一 Text、undo、選取及 draft | final-regression、native-final/manuscript-* |
| 整理換行預覽 | `manuscript.line-break-preview` → InnerPageHost.content | LineBreakPreview；區域 ActionSpec、備份及過期保護 | regression-final／test_v2_cleanup_shell |
| 版本／備份／歷史候選／差異 | `manuscript.versions` → 同上 | VersionPage；原保存及刪除契約 | tools-lifecycle-video、native-final/versions-* |
| AI 偏好／本機連線 | `manuscript.ai-settings` → 同上 | AiSettingsPage；原連線任務 | tools-lifecycle-video、native-final/ai-settings-* |
| 來源處理／異常／PDF 表單 | `manuscript.source` → 同上 | SourcePage／SourceTools；原異常處理及 OCR | tools-lifecycle-video、final-regression、native-final/source-* |
| 語音服務／音色／節奏／試聽 | `voice.preview.batch` → ProductionWorkspace.host | VoiceDialog；FooterPort、原 consent／job／player | ownership-verified、header-track-final、native-final/voice-* |
| 試聽文字及設定來源 | 同上，局部狀態 | 保留輸入、游標、節奏、同意及保存範圍 | ownership-verified、regression-final |
| 音訊區塊／歷史任務 | `audio.production.batch` → 同上 | NarrationDialog；FooterPort、原任務快照 | affected-final、final-regression、native-final/audio-* |
| 音訊來源／設定／錯誤詳情 | 同上，局部內容切換 | 同一 selection／scroll／task；全域動作仍在固定 port | final-regression、affected-final |
| 全書音訊 | `audio.assembly.book` → 同上 | AudioAssemblyWorkspace／AssemblyPage；原來源及保存 | affected-final、native-final/assembly-* |
| 音訊接點／詳情／文件選擇 | `audio.joins.book` → AssemblyPage 內容 | AudioJoinWorkspace／JoinPage；FooterPort、閱讀位置及保存 | final-regression、ownership-verified、join-tests、native-final/joins-* |
| 本批影片／各頁籤 | `video.uniform.batch` → ProductionWorkspace.host | TotalVideoPage／VideoWorkspace；FooterPort、獨立 batch target | regression-final、native-final/video-batch-* |
| 全書統一素材影片 | `video.uniform.book` → 同上 | TotalVideoPage；原總音訊及素材契約 | regression-final、native-final/video-book-* |
| 沿用各批影片／排序／任務 | `video.merge.book` → 同上 | AssemblyPage(movie=True)；原合併路徑 | tools-lifecycle-video、final-regression、native-final/video-merge-* |
| 影片接點 | `video.joins.book` → AssemblyPage 內容 | JoinPage(movie=True)；FooterPort、原幀／字幕及試聽 | final-regression、native-final/video-joins-* |
| 成品版本／來源比較 | `outputs.versions.book` → ProductionWorkspace.host | OutputVersionsPage；FooterPort、原 route／player／export | regression-final、final-regression、native-final/outputs-* |
| 服務新增／編輯／刪除 | `voice.services.book` → 同上 | ServiceDialog；FooterPort、原本機加密設定 | ownership-verified、header-track-final、native-final/services-* |
| Kokoro 包管理 | `voice.packages.book` → 同上 | PackagePage；FooterPort、原匯入／移除任務 | final-regression、native-final/packages-* |
| 全書語音預設／套用批次 | `voice.defaults.book` → 同上 | VoiceDefaultsPage；FooterPort、原批次選擇／套用 | native-final/defaults-*、既有語音回歸 |
| 專案建立、匯入、訊息／資訊 | `project.create` → WorkspaceFrame／import_panel；其他沿用既有選單及輔助視窗 | shell 持有主導覽、文件工具及主操作列；原生選檔／確認與既有唯讀訊息視窗沿用 | final-regression、tools-lifecycle-video；本輪未新增替代頁面 |

表中的局部搜尋、頁籤、詳情與歷史狀態沿用同一內容 port，沒有為達成矩陣數量新增頁面。原生選檔／確認及既有輔助視窗依使用者「保留目前 UI」指示保留，不改成新的設計。

## 布局與資料契約分開判定

布局：主要區域、操作分組與順序保留。共用標頭使用同一自然高度與 8 Tk 像素內容淨距；沒有逐頁補償高度。原先工具列的 12 像素改用元件規範的 8 像素。原設定頁外層的 6／8／12 像素 inset 收回至內容，讓共用標頭齊頭。服務側欄依實際可用寬度換行。既有一列／窄版換列與成品頁雙列操作是內容角色差異，未改成新的操作形式。

資料：來源、草稿、朗讀快照、版本、金鑰、同意、任務、成品及播放仍由原模組持有。切頁不取消製作、不重勾同意、不重新送出語音；保存失敗與過期結果仍由原契約阻擋。PDF PhotoImage 明確綁定自己的 Canvas，避免多個測試視窗的 Tcl interpreter 混用。

Kokoro 真實 CPU／離線推論、品質與完整包生命週期仍屬原後端票；本輪以未安裝狀態驗證外框及既有管理入口，不把共用外框驗收當成那些項目通過。
