# 實作交接

T01 與 T02 已完成。T01 基線提交為 `c45a51d`，T02 初始實作為 `2eb1bba`；最終審查修正及證據提交可由 `git log -1` 查看。本機目前分支為 master，尚未設定或推送遠端。

下一張是 **T03 — 人工校對、外部重載與朗讀稿確認**，票稿位於 `.scratch/pdf-txt-audiobook-video/v1.1/issues/03-proofread-confirm-reading-draft.md`。建議在新 session 從此交接點開始，先讀 AGENTS.md、GLOSSARY.md、docs/adr、Spec v1.1、T03 票稿及 T02 驗證紀錄。

主要測試入口維持 UI 共用的 ProjectWorkflow；專案格式 v1 保存多 TXT 批次，來源記錄編碼與原始副本，校對稿為獨立 UTF-8 版本。切換／新增批次前需處理未存稿；命名及排序保留編輯器的未存文字。尚無朗讀稿快照，T03 必須明確區分校對稿與已確認朗讀稿。

最近完整驗證為 20 tests 全通過、mypy 通過及 Windows onedir 重建／啟動。詳見 docs/verification/T02.md。原生選檔對話框的封裝版完整人工補驗及 T23 安裝驗收尚未完成，不得宣稱已通過。

執行環境無第三方依賴；重建工具依 packaging/requirements-build.txt，型別檢查工具依 packaging/requirements-dev.txt，使用時安裝至專案隔離目錄。實作告一段落後依 AGENTS.md 清理暫存與測試程序，保留 dist 成品與驗證證據。

Windows 目錄擁有者使 Git 要求安全目錄設定，目前每次命令使用 `git -c safe.directory=E:/Leo/Projects/ebook2mp4 ...`，未修改全域設定。沙箱對 .git 寫入有限制，提交需使用已授權的提升權限命令。
