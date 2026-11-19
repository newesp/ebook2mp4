# 本輪根 check-list 逐項結果

2026-11-13；階段 A，靜態設計／盤點。已重新讀根 [check-list.md](../../../check-list.md)、AGENTS.md、frontend-visual-qa、元件及捲動規範。本表與根清單18項一一對應。

來源：本批 `artifact-manifest.json`、[app來源基線](source-baseline.json)、[圖及同份布局量測](../../ui-review/v2-unified-shell-a/layout-measurements.json)、[機械檢查](design-checks.json)。96dpi 是繪圖座標假設；控制字型14px、標題16px、正文12pt／18pt。非Windows／Tk實測值。

通過只指本欄明列的**靜態設計範圍**；原生操作與正式EXE另列未測。不能以這張表宣告整體 UI 驗收完成。1280及參考最大化使用共用外框代表頁，不宣稱已覆蓋每頁所有尺寸／狀態的笛卡兒積；完整原生矩陣由B～E執行。

| 根項目 | 靜態設計結果／路徑及依據 | 原生／正式 EXE |
| --- | --- | --- |
| 1.1 短／空無多餘捲軸 | 通過（所交付圖）：選 `ai--reduced`／`ai--expanded`、issues／cleanup empty → 核對 owner 的 content≤viewport、offset0、無 track；短反例不是只把捲軸隱藏 | 未測：須實際長→空→返回 |
| 1.2 fit／overflow／long 比例與行程 | 通過（幾何）：820筆契約檢查；畫面實際區域與四種邊界fixture分開標示；voice長文、AI長錯誤與完整容納圖核對；滑塊按 view/content 算 | 未測：原生最小滑塊及真實行程 |
| 1.3 滾輪／滑塊／鍵盤首末，固定區不動 | 未測：PNG不能執行輸入。圖有固定導覽／工具／footer及有界owner；不將幾何通過冒充操作 | 未測 |
| 1.4 長→空→返回無殘留 | 未測（操作）；靜態長及空圖均已核對，空圖無舊軌道／offset | 未測 |
| 1.5 改尺寸／字級／收合重算，無裁切／水平／巢狀 | 通過（本批圖）：四種尺寸、正文18pt與代表列表收合，依相同模型重算；shell無outer scroller；form與Text不巢狀 | 未測：實際Configure、字級改動、返回 |
| 2.1 同組 Button／Entry／Combobox 樣式 | 通過（靜態規格及已畫角色）：共同字型、h36、同角色按鈕等寬；表單field與readonly分列，不拿readonly當input | 未測：native theme、padding、互動狀態 |
| 2.2 同欄按鈕與input等寬同高 | 通過（設計模型）：PDF normal OCR模型動作與旋轉欄位皆524×36，reduced皆294×36；x分欄、y370相同，role明記於fields | 未測：原生reqwidth／外框 |
| 2.3 同角色文字按鈕共尺寸 | 通過（靜態）：voice兩個帶入文字按鈕140×36；主／次提交共用該組最長標籤寬度。量測逐顆保留在controls | 未測：原生文字完整與長狀態標籤 |
| 2.4 預設／焦點／停用／忙碌及單一下拉指示 | 部分未測：PNG預設／selected／busy／disabled已核對尺寸；單一繪圖下拉箭頭。未交互動focus／hover，不能標全通過 | 未測 |
| 3.1 同列元件上下緣與高度 | 通過（設計模型）：同組h36、y相同；欄位標籤在控制項上方；PDF模型／旋轉y370、h36，差0 | 未測：原生外框差≤2 |
| 3.2 同欄左右邊界及欄列距 | 通過（設計模型）：表單同colw與x；長label按該列最大行數決定input y；fields rect可逐對復算 | 未測：真正Tk標籤換列／DPI |
| 3.3 相鄰動作水平淨距 | 通過（設計模型）：voice normal footer兩鈕 `[1080,768,130,36]`、`[1214,768,130,36]`，gap4；文字帶入 `[616,168,140,36]`、`[760,168,140,36]`，gap4 | 未測：原生及EXE逐對 |
| 3.4 操作列到Text垂直淨距 | 通過（設計模型）：voice normal Text top212−buttons bottom204=8；reduced preview256−248=8 | 未測：原生及EXE逐對 |
| 3.5 相鄰標頭／內容基準線與固定操作可達 | 通過（靜態共用port）：文件／workspace標頭y100、h60，port top168，差0；頁面內Text的再下一層header不冒充共用內容起點。footer不與內容重疊 | 未測：正常外層Configure＋after、隱藏頁回呼、instance及parent |
| 3.6 最大化／1360／1280／900、大字／列表狀態 | 通過（本批設計圖範圍）：參考1536×864、1360×820、1280×720、900×640，適用18pt與列表收合；逐圖尺寸見索引 | 未測：真正最大化client、Windows DPI／Tk scaling、全頁原生矩陣 |
| 交付1 功能／原生／EXE分開 | 通過（記錄）：功能未跑、原生未跑、EXE未跑；只驗設計與來源盤點 | 未測：B～E |
| 交付2 每項有本版本證據、落差不冒充完成 | 通過（記錄）：保留未測與核准邊界。A待確認，C全表仍待驗；未稱全APP v2／UI完成 | 未測：完整產品驗收 |
| 交付3 修正缺陷版失敗→修正版原生量測 | 不適用於本輪產品：未改任何產品程式／尺寸／間距。草圖修正有繪圖量測；不能當native red/green | 不適用於A；B／D若修產品缺陷須另留red/green |

本批額外核對：來源處理保留原頁適應大小與定位入口；窄版頁籤與內容標籤一致；文件管理僅展開menu，沒有另造重複清單；成品播放不顯示素材編輯控制；本機Kokoro示例不顯示雲端同意或key；尚未安裝時移除停用。K03依賴與未知政策在功能契約明列，不在產品圖填猜測時間或品質結論。

**交付判定：設計草案可供確認；UI驗收未完成。** A尚缺使用者新增布局確認；B／C／D／E保持未完成。未測項不因80張圖、820筆數值或檢查腳本成功而消失。
