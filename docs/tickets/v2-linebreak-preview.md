# v2 整理換行預覽：共用內頁與齊頭設計

> 狀態：CLOSED（2026-11-13整理，本頁共用內頁交付完成）。原生／EXE證據及限制保留；「其他頁等待逐頁指定」屬歷史範圍。新票要求先完成全頁外框，再整合內容，本頁仍納入新父層回歸。
> 後續：[新spec](../v2-unified-shell-spec.md)／[新ticket](v2-unified-shell.md)；[結案盤點](2026-11-13-tracking-audit.md)。

日期：2026-11-11。範圍僅「編輯 → 整理換行預覽」。其他文稿工具及製作頁等待使用者逐頁指定。

狀態：使用者於本 session 回覆「開始實作」，已核准下列設計。本頁共用模組接入、功能回歸、原生布局與正式 EXE 驗收完成。最終交付見 [本頁證據](../verification/v2-linebreak-preview/README.md)。

依據：[內頁交接](v2-inner-pages-handoff.md)、[AGENTS.md](../../AGENTS.md)、[frontend-visual-qa](C:/Users/Administrator/.codex/skills/frontend-visual-qa/SKILL.md)、[元件規範](../ui-components.md)、[共用 UI／保存契約](../pdf-txt-audiobook-video-spec.md)、[第六版交接](unified-manuscript-v6-handoff.md)、[換行預覽既有契約](manuscript-cleanup-footer.md)。

## 現況與根因

目前只有「1 文稿」主介面完成 v2 模組接入。`LineBreakPreview` 雖已獨立檔案，仍自行建立文件摘要、內容、區域狀態及取消／套用按鈕。`manuscript_desktop.py` 自建工具標頭／宿主；`update_stats()` 仍發送文稿主頁呈現，再特判隱藏全域朗讀動作。這些均不算內頁模組化完成。

`layout_workspace()` 用原稿與文稿標頭的請求高度設定左列表標頭高度，沒有採用目前工具標頭；右側工具標頭另有 12 單位下距。左右父容器缺少共同的標頭帶與內容起點，造成附圖紅線／綠線錯位。修正須落在共用父層，不能以預覽子元件位移補償。

已讀第六版完整 HTML/CSS/JS、配套 design-notes、交接與原生／封裝證據，並檢視使用者附圖及既有正式預覽畫面。瀏覽器政策拒絕本機 file URL，未繞過；本輪沒有新增第六版瀏覽器呈現驗證。以下為程式繪製且已逐張檢視的靜態設計，不是原生或正式 EXE 證據。

## 已核准設計

- [正常 1536×793](../ui-review/v2-linebreak-preview/normal.png)
- [縮小 900×640、18pt 內容](../ui-review/v2-linebreak-preview/reduced-18pt.png)
- [列表收合 900×640、18pt 內容](../ui-review/v2-linebreak-preview/collapsed-18pt.png)
- [無變更 1360×820](../ui-review/v2-linebreak-preview/unchanged.png)
- [保存失敗 900×640](../ui-review/v2-linebreak-preview/save-failure.png)
- [原始附圖](../ui-review/v2-linebreak-preview/reference.png)／[設計座標](../ui-review/v2-linebreak-preview/design-geometry.json)

左側收合／匯入／管理與右側返回／頁名採同一標頭帶，控制項上緣與高度差 ≤2 Tk 單位。左列表與右白色內容外框上緣差 ≤2。文件摘要位於白色區頂部；差異在其下，不把差異正文誤當內容外框起點。

只保留標頭「← 返回文稿」作為離開入口；離開不套用預覽。使用者已一併核准移除原底部重複的取消／返回按鈕。右下僅「套用換行整理」，區域提交與全域朗讀提交分開。全域底列保留文件與保存狀態，不顯示朗讀提交。右上訊息記錄沿用既有位置。

無變更：保留頁名、文件範圍與結果；不顯示差異框、捲軸或套用。失敗：在區域操作列顯示可讀錯誤；保留返回與重試套用。過期：顯示重新預覽，套用停用；不自動重算或覆寫。

列表收合後移除整欄與間距；重開入口在工具標頭左側。縮小仍保留列表，使用者自行收合；不改字級、不強制隱藏文件欄。差異採文字折行與唯一垂直捲動，列表自行垂直捲動，沒有整頁或水平捲動。

## 布局對照（與功能分開）

| 布局／操作分組／空間 | 原生實作方案 | 驗收 |
| --- | --- | --- |
| 左右標頭控制項同高、同上緣；左右內容齊頭 | 共用宿主回報目前標頭需求，框架統一設定標頭帶；不讀隱藏文稿標頭作為工具高度 | 各尺寸開預覽 → 量測 top／height → 差 ≤2；檢查所有祖先裁切 |
| 工具標頭：重開列表、返回、頁名 | `WorkspaceFrame` 的共用內頁宿主，固定父容器；返回為具名 `ActionSpec` | 收合列表 → 用鍵盤重開 → 選取及捲動保留；沒有空欄 |
| 白色區：文件摘要、比較標籤、主要差異 | 宿主持有摘要／內容 port，`LineBreakPreview` 僅建立自己的差異與空狀態 | 同資料／尺寸對照整張圖；最大化及1360×820差異視口 ≥430高，1280×720 ≥350，900×640 ≥280 |
| 長差異取得剩餘高度 | 單一 Text 與垂直 Scrollbar，不嵌表單 Canvas | 滾輪／捲軸／Ctrl+Home／Ctrl+End → 首末行可達 → 只有差異移動；900×640、18pt ≥8 display lines |
| 底部區域結果靠左，套用靠右，固定可達 | 重用 `ActionBar`／`ActionSpec` 的分派、角色、忙碌規則；補區域模式而非另建按鈕系統 | 長錯誤 → 結果折行、按鈕不裁切；反覆切頁及更新 → 只執行目前命令，dispatcher 不累積 |
| 全域摘要與步驟維持原位置 | `PagePresentation` 發布預覽頁適用呈現；不再發布文稿提交後特判隱藏 | 預覽 → 返回 → 主要動作恢復；預覽沒有朗讀提交或 AI 工作操作 |

設計圖尺寸為設計座標，尚非原生實測。Tk 字形、邊框與系統選單依平台呈現；此差異不允許父布局、分組或空間分配偏離。原生須另記實際客戶區、DPI、祖先 bounds 與可用高度。各尺寸包括最大化、1360×820、1280×720、900×640，適用18pt與列表收合／重開。

## 功能對照

| 能力 | 現入口 → 遷移後入口 | 資料／狀態持有者 | 驗證 |
| --- | --- | --- | --- |
| 開啟、計算差異 | 編輯 → 整理換行預覽；入口不變，命令接共用宿主 | app 持 flow／batch／同一編輯器；頁面持 identity／base／candidate／change_count；計算仍用 workflow.preview_line_breaks | 畫面全文含未存稿 → 預覽 → 原稿未改；無文件／busy／source_pending 拒絕開啟 |
| 返回 | 原標頭及底部取消 → 唯一標頭返回 | app 保留 editor_view；宿主管顯隱／焦點 | 未存稿及長文 → 選取／游標／捲動 → 返回 → 全部保留；clear 清除預覽身分 |
| 無變更 | 同一預覽入口 | workflow 不寫入 | 狀態及版本前後完全相同；無備份／朗讀失效／差異／捲軸／套用 |
| 套用 | 原頁面按鈕 → 共用區域 `ActionSpec` | workflow 先 backup_manuscript 再 save_workspace；app 成功後更新 editor | 備份與工作區持久化一致；原稿來源不變；一次 Ctrl+Z 回復原稿 |
| 保存失敗 | 區域結果；位置與入口不變 | 頁面錯誤狀態透過宿主呈現 | 分別注入備份失敗、工作區保存失敗 → 留頁、現稿及朗讀狀態保留 → 排除後可重試 |
| 過期、範圍與忙碌 | 仍由 apply 驗證固定快照 | identity 比對 flow／batch；app 提供目前全文／busy／source_pending | 改稿、換文件、換專案、開始衝突工作 → 舊套用拒絕，無跨範圍寫入 |
| AI 未完成／來源阻擋 | 套用後回文稿既有處理選項 | app workspace_review／allow_partial；workflow 既有就緒規則 | 套用不自動視為全文完成；保留原文須明選；來源異常仍阻擋朗讀 |

適用回歸起點：`test_v2_manuscript_shell.py`、`test_manuscript_cleanup.py`、`test_manuscript_v6.py`、`test_unified_manuscript.py`。既有案例保留，新增上述齊頭、真正宿主接入、過期分支與返回捲動案例；不能只驗元件存在或樣式名稱。

## 共用介面與分工

主 agent 在 `desktop_shell.py`／`workspace_layout.py` 定義共用內頁宿主及標頭同步，負責 `manuscript_desktop.py` 整合。宿主持有固定的標頭、內容 port、區域結果及動作容器；頁面提供穩定 page id、title、context、back、summary、actions、busy。沿用 `DesktopShell`、`WorkspaceFrame`、`PagePresentation`、`ActionSpec`、`ActionBar`，必要時向後相容擴充；不以新樣式名稱或 Frame 包裝宣稱完成。

`LineBreakPreview` 管理預覽快照、差異、空狀態與 apply 命令，不取得共用控制項後改 grid。其他工具保留舊宿主的過渡入口，不宣稱已遷移；也不在本頁實作時改造它們。審查子 agent 可唯讀對照功能／共用責任；主 agent 完成整合、原生目視與正式 EXE 驗收。

## 逐頁完成狀態

| 頁面 | 盤點 | 共用介面 | 設計 | 模組接入 | 功能回歸 | 原生布局 | 正式 EXE |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 整理換行預覽 | 完成 | 共用宿主／ActionSpec／呈現介面已接入 | 本 session 已確認 | 完成 | 62項相關案例最後通過 | 指定尺寸／18pt／收合／長差異通過 | 固定路徑建置、實際操作／重開／退出通過 |
| 其他文稿工具／製作內頁 | 未納入本輪實作 | 待逐頁接入 | 待逐頁確認 | 未完成 | 不以舊結果代替 | 未驗收 | 未驗收 |

確認設計後，先完成原生主布局與對照，再整合完整功能；回歸與視覺都通過才封裝。建置前正常關閉正式程式並檢查占用；只更新 `dist/ebook2mp4`。正式 EXE 使用隔離合成專案及設定，完成原入口 → 預覽 → 返回／套用 → 一次復原 → 重開；再重驗 v1 封存雜湊與獨立啟動。不得對使用者程序未經授權強制結束。

保留 v1、既有必要來源及原先未提交工作。清理僅限本次測試、暫存、快取與自建程序；保留需求、設計與最終證據。設計階段磁碟／清理結果另見 `docs/verification/v2-linebreak-preview/design-baseline.json`。
