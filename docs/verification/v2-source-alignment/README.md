# OCR按鈕對齊及返回空白修正

OCR按鈕原本直接置於包含標籤和input的外層格子，導致寬高及上緣不齊。現在與其他欄位共用同型容器，標籤row0、按鈕row1，沿用Workspace樣式、等寬欄位。

無異常頁隱藏表單Canvas，返回處理頁時僅恢復欄位而未恢復Canvas。open_processing_view現在在離開異常情境時明確恢復表單並清除過期異常提示。

驗證依根目錄check-list.md；逐項狀態及限制見本目錄check-list.md。targeted.txt為3項針對性回歸；regression.txt為文稿、來源及共用宿主回歸。native.json記四尺寸、DPI及元件外框。圖片為指定原生視窗合成PDF畫面。

build.txt為正式建置記錄；package.json核對封裝與來源；exe-startup.json為隔離啟動與正常退出。成功封裝與啟動不代替完整EXE逐頁人工驗收。
