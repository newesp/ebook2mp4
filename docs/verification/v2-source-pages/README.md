# 來源處理／來源異常 v2 交付

兩頁接入固定 InnerPageHost 內容port，SourcePage 透過 PagePresentation／ActionSpec 提供標題、範圍、返回及情境操作。SourceTools 保留原來源、任務及預覽保存契約。

來源處理：PDF／TXT 適用欄位、原頁縮放、框選與對應文字、預覽採用及續修。來源異常：獨立顯示狀態、選取定位、已處理與略過確認；無異常隱藏處置動作。寬版異常兩欄319／747約3：7；900寬改具名資訊／原頁切換。表單及原頁依實際yview範圍顯示捲軸，標頭與操作固定。

## 驗證

25項相關回歸通過（tests.txt）；最後匯入重疊修正另9項通過（final-source-tests.txt）。native.json和processing／issues圖片為1360×820與900×640原生合成資料。原生畫面以指定視窗擷取。

正式成品固定 dist/ebook2mp4/ebook2mp4.exe。build.txt建置成功；package.json確認48個應用模組與來源一致，FFmpeg／FFprobe啟動。exe-startup.json為隔離設定啟動、正常關閉、exit0。v1.json確認4,052檔雜湊不變。

## 驗收範圍

已完成上述兩尺寸的原生畫面、功能回歸、封裝一致性與EXE啟動檢查。最大化、1280×720、18pt、長內容各種輸入裝置，以及正式EXE逐頁完整人工流程尚無本輪證據，仍列待驗收；EXE啟動成功不代替這些項目。舊mock的其他頁尚未核准或遷移。

操作路徑：1文稿 → 選PDF → 來源 → 來源處理／來源異常。窄版按「顯示原頁」切換，按「顯示資訊」返回。來源異常 → 選項目 → 檢查原頁 → 已處理／明確略過。
