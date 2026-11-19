# 語音頁三處尺寸與間距修正

依使用者指定與docs/ui-components.md修正，不新增設計分歧。

- 上方兩個文字帶入按鈕改為共用等寬grid欄位，寬度依較長標籤自然需求決定。
- 底部保存與下一步／套用既有批次改用相同等寬群組與獨立4像素間距欄。
- 文字操作列與Text容器之間固定8像素外距。

ToolbarLayout.equal_button_pair是共用布局入口，間距來源唯一為TOOLBAR_GAP；沒有以字元寬度猜測像素或空白文字造間距。

驗證：缺陷版red-tests.txt三項失敗；修正版green-tests.txt三項通過。原生尺寸及逐項值見check-list.md與native.json。23項語音／本機／保存／相鄰音訊回歸通過（regression.txt）。建置與來源一致性見build.txt／package.json，正式EXE畫面觀察見exe-ui.md。資料與任務契約、文字帶入及傳送同意行為保留。

正式成品固定dist/ebook2mp4；本次依賴與建置暫存清理結果另記cleanup.json。原始來源與v1封存未修改。
