# v2 全頁外框 A：盤點與設計證據

日期2026-11-13。工作區 `E:/Leo/Projects/ebook2mp4`。主agent完成，未派子agent。入口：[本批設計](../../ui-review/v2-unified-shell-a/README.md)／[工單](../../tickets/v2-unified-shell.md)。

## 已完成的工作

讀交接／現行規範、GitHub #12／#13及本機規格／矩陣，確認皆OPEN且A未完成。讀目前來源、既有合併／接點／語音／影片證據及舊繪圖配套；舊單頁核准及失敗捲動圖未升格成全頁新核准。

盤點20列主範圍與實際子入口、狀態、父容器、資料／任務持有者、返回及釋放；區分無主線呼叫者的歷史PDF／Gemini彈窗。機械搜尋50個共享／跨容器幾何候選，人工按責任歸類；不把候選數當缺陷數。58個目前app Python檔的SHA-256見 [source-baseline.json](source-baseline.json)，不含v1封存或成品。

提供80張靜態設計圖與本機選圖檢閱器；布局／功能契約分開。以同份Pillow文字／布局資料保存164個畫面區域及四種邊界fixture，共820筆捲動幾何；所有圖的按鈕bounds、同組尺寸、淨距及區域計算由[design-checks.json](design-checks.json)記錄。

原尺寸畫面逐組檢視，修正後重查受影響family／狀態：窄版頁籤標籤、文件管理重複清單、成品播放誤帶素材工具、本機服務與狀態不符、空異常頁殘留命令、忙碌時恢復設定、刪除確認、接點停頓／播放與校對入口。AI連線展開曾多算尾端留白；改以實際最後glyph底部計extent，現在fit無scroll，另有真實長錯誤文字overflow反例。這些是草圖修正，不冒充產品缺陷版原生red/green。

## 驗證結果與實際限制

| 檢查 | 結果 |
| --- | --- |
| 繪圖與設計幾何 | 通過；命令 `python -B tools/design_unified_shell_a.py`；80 frames、0 layout failures。這是靜態模型檢查 |
| 捲動幾何 | 通過；`python -B tools/check_ui_scroll_contract.py docs/ui-review/v2-unified-shell-a/scroll-contract.json`。完整容納的偏好及連線圖無scroll；長錯誤／長稿有正確owner、比例與行程 |
| 圖與布局對照 | 已檢閱；詳見設計及[根清單](check-list.md)。核准仍待使用者；內容樣本不代替D完整功能UI |
| 功能回歸 | 未執行。本輪未改／import產品，未發服務／計費請求 |
| 原生布局與操作 | 未執行。真實client／DPI、focus、滾輪／拖滑塊／鍵盤、跨頁資料與任務、舊回呼隔離均待B～E |
| 正式EXE | 未執行、未封裝；`dist/ebook2mp4`沒有本輪更新 |
| v1 | 依指示保留；未建置／執行／測試／重驗雜湊，未讀取封存內容 |
| Impeccable context | 未執行成功：引擎未安裝且cache目錄不可寫。按技能fallback直接讀PRODUCT.md／DESIGN.md及實際來源，未繞過權限或安裝依賴 |

根清單有未測項，不能標UI驗收完成。1536×864只是最大化參考畫布，非目前電腦實際max client；設計DPI96非Windows實測。控制字型未作18pt全字型壓力；本批18pt是正文。表單／原頁、Text及清單在內容port，無outer shell scrollbar；原生最小滑塊長度、OS選檔器、所有狀態轉換仍須實際驗證。

## 保護與清理

本輪只新增設計繪圖來源／設計與證據文件，更新本機進度／交接／ticket入口。既有未提交／未追蹤產品來源保留，不以HEAD還原。未提交、推送或修改遠端工單。

沒有建立書籍測試專案、下載模型、啟動app／media／OCR／server／瀏覽器或建置程序。Python均用 `-B`；保留設計圖、繪圖程式、需求及最終驗證證據。最終檔案指紋、app來源一致與本輪程序／檔案占用檢查見 `artifact-manifest.json`／`cleanup.json`。不把非本輪程序當清理對象。

## 接續

使用者確認本批新外框後才開始B。B由單一整合者處理固定port、描述與activation generation，保留原資料／任務物件；代表頁原生結構比對後進C，全20列及新增子路由真正接入。全C未通過前不開始D。正式封裝固定dist/ebook2mp4，先正常關閉正式程式並確認無占用；強制結束使用者程序須另獲授權。
