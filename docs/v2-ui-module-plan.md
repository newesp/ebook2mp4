# v2 模組與功能遷移設計

> 狀態：CLOSED／SUPERSEDED（2026-11-13，舊執行計畫）。共用外框責任、全頁接入順序及完成判定由[新spec](v2-unified-shell-spec.md)／[新ticket](tickets/v2-unified-shell.md)取代。下文保留歷史功能／布局與當時交付；不是當前完整接入狀態，也不是新外框核准圖。

2026-11-12 追加「檢查接點」音訊內頁：使用者已核准設計並授權實作。AudioJoinWorkspace 管理選擇列、左右 JoinTextPane、設定／播放列、警告詳情、文件列表切換及共用 footer port；JoinPage 保留來源驗證、預覽工作、校對返回、確認與保存。資料內容種類獨立於播放旗標，隱藏頁停止重排；來源及媒體契約沒有移入布局模組。影片接點沿用既有分支。這是布局與控制器分離，並非全頁改成 ActionSpec。2026-11-13修正外層標頭／內容兩條基準線，並統一閱讀位置恢復與實際保存狀態；詳見[本批驗收](verification/audio-join-corrections/README.md)，前批驗收保留為歷史紀錄。

2026-11-12 追加「全書合併」音訊模組：使用者核准音訊專用設計並授權實作。AudioAssemblyWorkspace 持有父層布局、來源清單、兩列對齊控制及共用底列 port；AssemblyPage 保留來源、接點、任務與保存命令。音訊頁不建立 OutputControls，明確呼叫 start_total_audio。影片偏好不再重導音訊入口；所有影片功能仍由既有影片工作區持有。這是本頁的布局及呈現分離，並不代表其餘製作頁已全部遷移成 ActionSpec。詳見[功能／布局分開對照及驗收](verification/audio-assembly-workspace/README.md)。下文「本輪保留」指原始文稿階段；合併頁的現況以本段為準。

最新追加交付（2026-11-11）：已核准並完成「整理換行預覽」共用內頁。`WorkspaceFrame` 的 `InnerPageHost` 集中標頭、返回、文件範圍、內容port與區域ActionBar，內容頁提供呈現與命令；主步驟切換統一暫停／恢復命令。[本頁功能／布局分開對照與證據](tickets/v2-linebreak-preview.md)。其餘工具仍待逐頁遷移，不因宿主建立而視為完成。下文為原始主介面階段設計。

日期：2026-11-11。執行範圍：先建立共用模組並接入「1 文稿」。使用者指定沿用目前 v1 UI，只修正 PDF 控制列左右間距；此範圍已授權。其餘頁面先盤點及定義介面，不在本輪改版。

本輪附圖已保存為 [PDF 工具列間距參考](ui-review/v2-manuscript-spacing-reference.png)。全頁布局與狀態設計見 [v2 全頁布局](v2-page-layouts.md)。

## 功能盤點與保留契約

| 能力 | 現有來源／入口 | v2 入口與持有者 | 驗收 |
| --- | --- | --- | --- |
| 兩步驟、專案建立／開啟／資料夾／資訊、訊息紀錄 | manuscript_desktop._build、desktop.Workbench | NavigationBar；命令仍回到 Workbench | 切步驟 → 開訊息 → 返回；框架物件不重建 |
| TXT／PDF 匯入、編碼、OCR 模型、擷取預覽、採用新批次 | manuscript_source、workflow；匯入選單 | DocumentList 匯入選單，來源工作由既有服務持有 | 受控 TXT／PDF 匯入；來源原檔不變 |
| 文件選取、重新命名、排序、移除 PDF、收合 | manuscript_desktop、desktop | DocumentList；資料選取與未存稿保護仍由 Workbench | 收合 → 返回 → 選取／捲動保留；移除取消不改檔 |
| PDF 頁碼、上一／下頁、符合頁寬、自訂縮放、開來源 | manuscript_desktop、manuscript_source | 文稿內容模組；共用 ToolbarLayout 配置間隔 | 五個控制邊界有相同 4 Tk 單位間距；頁碼與總頁數為一個語意群組 |
| 全文編輯、搜尋取代、復原、匯出、重載、換行預覽 | manuscript_desktop、manuscript_cleanup | 保留編輯選單及同一 Text；工具留同窗 | 原有文稿回歸；保存失敗與返回不丟稿 |
| 全文 AI 校對、差異、單處還原、放棄、設定、自訂模型／安全金鑰 | manuscript、gemini、manuscript_desktop | 保留校對選單；工作生命週期仍屬文稿控制器 | 部分失敗／續作／取消／晚到結果；不新增同意框 |
| 版本預覽／還原／歷史候選、朗讀快照與草稿恢復 | manuscript、workflow、版本選單 | 既有版本與保存服務；ActionBar 呈現當前主要動作 | 版本先預覽；原子儲存；重複保存不建新版本 |
| PDF／TXT 來源工具、異常、旋轉、框選重辨、失敗頁重試 | manuscript_source、manuscript_desktop | 原有來源選單／同窗工具 | 受控 OCR 不覆寫人工稿；異常未解不能確認 |
| 語音設定、全書預設／本批、原任務設定、試聽、服務／本機套件 | voice_desktop、voice_defaults_desktop、service_desktop、kokoro_desktop | 本輪保留現行頁；後續接 PagePresentation | 同意取消切頁仍取消；本機不顯示雲端控制 |
| 音訊歷史任務、快照、重檢、開始／續作／取消／重新開始、錯誤、重試保存 | narration_desktop、narration | 本輪保留；後續輸出 ActionSpec | 原任務跨頁持續；重試保存不重合成；增量快取不變 |
| 全書音訊選批、排序、交接、MP3／SRT | assembly_desktop、assembly_workspace、assembly | AudioAssemblyWorkspace 管布局；AssemblyPage 保留任務及保存 | 影片偏好不能導向 MP4；取消／失敗保留舊音訊；重試保存不重做媒體 |
| 本批影片／全書統一素材／沿用各批影片、素材、預覽、製作、版本 | total_video_desktop、video_workspace、video_merge | 本輪保留三種來源契約；後續 WorkspaceFrame 內容頁 | 不新增 TTS；不重加交接；不同範圍不混設定 |
| 音訊／影片播放、停止、另存、資料夾、版本來源比較、回原入口 | narration／assembly／total_video／output_versions_desktop | 本輪保留；後續 ActionBar 與頁面內容 | 離頁停播放、製作不停；另一批結果不能改當前頁 |

## 模組介面與狀態持有者

- `desktop_shell.py`：`DesktopShell` 擁有導覽、文件欄、內容承載區及底列。固定父容器，只建立一次。`NavigationBar` 接收命令；`DocumentList` 接收匯入／管理命令及選取事件；`WorkspaceFrame` 提供內容宿主；`ActionBar` 接收 `ActionSpec`，依穩定 ID 更新標籤、角色、回呼及 enabled，移除上頁不適用動作。
- `workspace_layout.py`：`ToolbarLayout` 提供相同水平間距與群組換列；`ManuscriptLayout` 配置文稿標頭、正文齊頭與原稿／文稿比例，不持有書稿、任務或保存資料。
- 文稿控制器保留編輯器、來源、工具頁、AI 任務及未存稿保護。快照／版本／原子發布仍由 workflow 及領域模組負責。框架不直接提交資料。
- `ProductionWorkspace` 繼續持有按專案物件／批次／頁型區分的頁面快取；服務設定是本機共用資料。切頁不銷毀內容。全書頁以批次 `None` 區分，不混入本批設定。
- 本輪以相容屬性保留舊頁入口。尚未遷移的 production／narration 仍有直接 chrome 操作及 `grid(in_=...)`，明列為後續工作，不能宣稱所有頁面完成模組化。文稿路徑只呼叫框架與布局介面。
- `ActionSpec`：`id`、`label`、`role`（back／secondary／destructive／primary）、`command`、`enabled`、`available_while_busy`（例如取消）。`PagePresentation`：`step`、`title`、`summary`、`busy`、`actions`。隱藏頁不得發布當前呈現；背景結果先更新自己的模型。
- 保存格式不變。文稿已保存的列表收合／原稿比例契約保留；不新增其餘視覺狀態磁碟保存。設定隔離使用既有環境變數及 LOCALAPPDATA，不改 v1。

## 布局對照（獨立於功能契約）

設計圖：`ui-review/v2-manuscript-normal.png`、`v2-manuscript-reduced.png`、`v2-manuscript-tools.png`。是本次沿用 v1 的結構設計圖；不是 runtime 證據。圖內合成內容不進正式程式。

| 布局／分組／空間 | 原生實作 | 驗收方式 |
| --- | --- | --- |
| 上方兩步驟靠左，書名／專案／訊息靠右 | NavigationBar，沿用 v1 欄位與字體 | 各頁往返 → 比較順序 → 確認沒有重複入口 |
| 文件匯入／管理與收合同列，正文三區齊頭 | DocumentList；隱藏釋放整欄與 12 單位內距 | 收合 → 量測中心 x=0 → 展開 → 選取不變 |
| 正常原稿／文稿 1:1，拖曳比例保留 | 既有 Panedwindow，ManuscriptLayout 管理標頭與群組 | 最大化／1360×820／1280×720 → 預設欄差 ≤2；正文 y 差 ≤2 |
| 粉紅區改為與右側工具相同左右間距 | ToolbarLayout 間距 4；頁碼與 /總頁數群組不拆 | 測量上一頁／頁碼群／下一頁／縮放／來源，間距皆 4；高度差 ≤2 |
| 寬度不足依既有規則把整組工具移至下一列 | source／editor 工具列使用實際 reqwidth，保留原字級 | 1100×760 及 1280×720 → 來源不越界；必要時工具群換列 |
| 900×640 使用原稿／文稿切換 | 沿用 v1 小於 950 的分頁式呈現；列表可還原 | 900×640、18pt → 編輯器 ≥360 高、≥8 display lines；主要動作完整可見 |
| 工具展開取代對照區，固定標頭／操作 | 既有 tool_host；版本差異由 Text、設定由 Canvas 各自捲動 | 長版本 → Ctrl+End → 末行可見；返回 → 游標／選取／捲動不變 |
| 全域摘要底列、主要動作靠右 | ActionBar 沿用 v1 外觀與操作順序 | 文稿保存前後 → 主要動作與就緒狀態一致；無舊頁回呼 |

正常畫面編輯器目標：最大化／1360×820 ≥480 高；1280×720 ≥400 高。工具頁目標：900×640 內容 ≥300 高且固定操作可達。OS 限制最大高度時回報實際客戶區；不把設計尺寸當實測。長文僅 editor／source 各自捲動；文件列表垂直捲動；不增加整頁捲動。

## 後續頁面設計

語音／音訊／合併／影片／成品版本沿用目前 v1 頁面的功能分區及各票有效設計，框架外緣一致；窄版導覽換列、操作分組重排，內容取得剩餘高度。新增布局須先提供各頁正常／縮小／工具展開圖並取得確認。這些頁面的完整遷移與新布局不屬本輪「先實作 1 文稿」完成範圍。
