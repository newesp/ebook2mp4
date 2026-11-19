# 整理換行預覽程式審查

主 agent 統整，共用介面由主 agent 實作；子 agent 僅修改指定測試及唯讀審查，沒有操作桌面或建置。

檢查 `desktop_shell.py`、`workspace_layout.py`、`manuscript_desktop.py`、`manuscript_cleanup.py` 與共用提示。對照已核准的本頁 ticket、AGENTS、frontend-visual-qa、元件規範及保存／返回契約。

已處理的發現：

1. 隱藏預覽的套用／返回回呼在切製作頁後仍有效：共用宿主及 ActionBar 現在依 active 狀態停用命令，返回才恢復，保留預覽內容。
2. 列表重開也須受相同規則管制：改用宿主 dispatcher；隱藏／暫停均停用，不能改製作頁的列表。
3. 重開圖示缺少可見說明：沿用 CellTooltip，加入 hover／focus 提示及 Unmap／Destroy 清理。其 widget 型別改為 tk.Misc，以正確反映既有共用用途。
4. 預覽開始讀取字級時，尚未儲存的無效輸入可能無法轉成整數：改回編輯器目前字型，不丟失輸入或阻斷預覽。

子 agent 最後靜態複查未發現本次修正範圍內其他問題；主 agent 已讀取所有測試修改與共用來源。回歸包含主步驟切換後舊按鈕／返回／重開不執行，回來後可以套用；備份失敗／保存失敗／過期／未完成 AI 保護、固定父容器與齊頭實測。

這份審查不是原生布局或正式 EXE 驗收；各項結果另見 README、測量 JSON、截圖與封裝證據。不宣稱未遷移的其他內頁已接入模組。
