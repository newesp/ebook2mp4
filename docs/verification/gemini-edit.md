# Gemini 候選文字人工編輯

日期：2026-10-27

原先候選使用與原文相同的唯讀填入流程，採用時直接使用已保存的 AI 文字。現在右側成功候選（包含已採用段落）可編輯，原文保持唯讀。保留既有左右 Panedwindow 與可伸縮 footer grid，在剩餘欄位加入「保存候選修改」。

修改以校對記錄、段落識別暫存，切換段落與記錄不遺失；保存、採用、拒絕、撤回、續作與關閉前保存候選。保存候選不修改校對稿，明確採用時才套用人工修正結果。首次 AI 候選另保存在 ai_candidate。差異標色隨修改更新，支援 Tk 文字復原／重做。採用後可繼續編輯，再次保存候選會回到待確認，校對稿保留上次採用內容；再次採用才更新。成功後明示「已儲存並採用本段」。執行中、無候選、未存主稿及版本過期等原有阻擋條件保留。

空白候選不可保存；切段後仍保留空白，不轉成錯誤提示文字。保存失敗保留視窗與修改，關閉失敗時可明確選擇捨棄未存修改。

## 驗證

- 原生 Tk：候選編輯、差異標色、連續切段、空白切段、保存重開、採用全部、撤回、儲存失敗保留、按鈕範圍檢查。
- 原生 Tk：切換校對記錄後，人工編輯仍位於原記錄的原段落。
- 27 項相關測試：test_ui_layout_gemini（6）、test_gemini_desktop（4）、test_gemini（6）、test_gemini_resume（9）、test_gemini_resume_desktop（2）。各模組分開執行以隔離 Tk interpreter。
- 型別：mypy --check-untyped-defs --follow-imports=silent --ignore-missing-imports，檢查 gemini_desktop.py 與 workflow.py。
- 使用 Windows Computer Use 目視檢查合成候選，740×570 邏輯視窗（125% DPI）：左右文字、差異標色、保存、採用與關閉按鈕均可見，無重疊或裁切。
- 本次沒有送出真實 Gemini 請求，測試使用合成資料及替代回應；未測試所有系統 DPI。

最終測試、型別及封裝輸出保留於同目錄 gemini-edit-*.txt。新版成品位於 dist/T09-gemini-edit/ebook2mp4/ebook2mp4.exe；需保留整個 ebook2mp4 資料夾。
