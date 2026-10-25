# 實作交接

T01～T03 已完成。T01 基線 c45a51d、T02 最終基線 ea10026；T03 實作 c6d2a4b，多視窗審查修正 a2b41b1。最終證據／交接提交可由 `git log -1` 查看。目前分支 master，尚未設定或推送遠端。

下一張是 **T04 — PDF 預覽選頁，擷取文字成為校對批次**，票稿位於 `.scratch/pdf-txt-audiobook-video/v1.1/issues/04-text-pdf-range-to-draft.md`。建議開新 session，先讀 AGENTS.md、GLOSSARY.md、docs/adr、Spec v1.1、T04 票稿及 [T03 驗證紀錄](verification/T03.md)。

主要測試入口維持 UI 共用的 ProjectWorkflow，另有真實 Tk UI 連接測試。專案格式 v1 保留多 TXT 批次，來源記錄編碼與原始副本，校對稿為獨立 UTF-8 版本。T03 以可選欄位 readings、current_reading、draft_copies、source_issues 增補快照、目前確認、未存稿副本與來源異常；舊專案缺省為無。T03 專案應使用 T03 或更新程式續作。

人工編輯事件立即保存取消目前朗讀確認；保存改稿及外部重載同樣取消。舊快照不可變，批次相互獨立。`reading_text(batch_id)` 檢查目前索引一致性，只能取得有效目前確認；明確傳入 snapshot_id 是歷史查閱，後續正式合成不得用此模式繞過目前確認。另一視窗更新索引後須重開。

重載沿用編碼預覽，未存稿可保留副本、明確取代或取消；副本與新稿同次原子發布。匯出包含目前未存文字，但只允許新檔名，不覆寫來源／既有檔案，不改專案儲存狀態。歷史快照及重載副本可由 UI 唯讀檢視並複製。

T04 請沿用 record_source_issues、resolve_source_issue、confirmation_blockers 及確認阻擋規則接入 PDF 異常。目前開啟流程仍僅接受 txt kind，尚無 PDF 模型、逐頁對應或背景任務。T04 需完整加入 PDF／TXT 共存、頁圖對照、選頁、文字擷取、換行整理預覽撤回、精確對應失效提示及背景取消；不可將本張 TXT 狀態視為 PDF 已驗收。

最近完整驗證為 **31 tests 全通過**、mypy 通過及 Windows onedir 重建／實際啟動。兩軸審查零項未解決，詳見 docs/verification/T03*.md。原生選檔對話框的封裝版完整人工補驗及 T23 安裝驗收尚未完成，不得宣稱已通過。

執行階段無第三方依賴；重建工具依 packaging/requirements-build.txt，型別檢查依 packaging/requirements-dev.txt，使用時安裝至專案隔離目錄。T04 PDF 工具選型及封裝需另行落實。

已依 AGENTS.md 清理本次測試資料、建置工具與快取，關閉測試／封裝啟動程序並重設桌面自動化階段；正式 dist、需求及最終驗證證據保留。

Windows 目錄擁有者使 Git 要求安全目錄設定，每次命令使用 `git -c safe.directory=E:/Leo/Projects/ebook2mp4 ...`，未修改全域設定。沙箱限制 .git 寫入，提交使用提升權限命令。
