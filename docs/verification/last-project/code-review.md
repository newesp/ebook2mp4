# 上次專案自動載入：雙軸審查

本輪起點：`0360e71ac2afbcb9decb068cc6c2a231b5c00640`。

工作區已有大量未提交修改，審查範圍只包含 `desktop-change.patch`（本輪 desktop 起點至本輪結果的精確差異）、`ebook2mp4/app_session.py` 與 `tests/test_last_project.py`。需求來源：使用者追加功能與 `docs/last-project-startup.md`。兩位獨立子代理各以全新上下文只讀審查，沒有修改檔案。

## Standards

未發現可行動問題。

- 沿用 Tkinter 與 ProjectWorkflow.open，符合 ADR 0005 的桌面架構及共用驗證流程。
- 設定採原子寫入，與書籍專案分離。
- 沿用既有工作台及狀態列，符合 AGENTS.md 第 2、3、11 項。
- 名稱與文件用語清楚，符合 GLOSSARY.md；未發現需要處理的 Fowler smells。

## Spec

未發現可確認的需求缺漏、範圍擴張或一般操作錯誤。

- 正式入口 run.pyw、ebook2mp4/__main__.py 與打包入口均呼叫 desktop.main，啟用還原。
- 還原沿用 ProjectWorkflow.open，先驗證內容，再載入第一個批次與已保存校對稿。
- 無記錄維持空白；無效專案及損壞設定顯示狀態提示，仍可手動開啟。
- 開啟／建立取消或失敗不更新記錄。保存設定失敗不撤銷已載入專案。
- 沒有 T20 版面修改。

驗證限制：新增測試尚未明確覆蓋「建立取消／失敗」與「未存編輯不還原」；審查未發現對應實作缺陷。正式入口另外以封裝版驗證，結果見本目錄驗收文件。

Standards：0 項；Spec：0 項。無待修正問題。
