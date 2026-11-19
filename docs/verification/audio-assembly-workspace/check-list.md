# 本次 UI 驗收檢查清單

依根目錄 `check-list.md` 逐項記錄。本次範圍為全書合併主頁、來源詳情、音訊接點及受影響的共用導覽／文件列表／底列。音訊、影片的媒體契約分開驗證。核准布局及原生實作對照見 README.md。

環境：Windows 11、Python 3.14.3、Tk clam。OS 顯示縮放125%；Tk 回報約96.09 DPI、scaling 1.33465，使用DPI虛擬化座標。控制項量測以Tk座標像素記錄。標準10pt，另以13pt（約130%，覆蓋125%需求）驗證文字放大，未修改系統設定。來源雜湊及正式EXE雜湊見 source-manifest.json／package.json。

| # | 根清單項目／操作與可觀察結果 | 狀態 | 依據 |
|---|---|---|---|
| 1 | 短內容／空狀態 → 檢查來源清單 → 確認捲軸隱藏、yview為0～1、空提示可見 | 通過 | native-fit／native-empty.json；layout-final.txt；regression-release.txt |
| 2 | 剛好容納、溢出及長內容 → 確認只有各自owner顯示捲軸 | 通過 | native-overflow／native-return-long.json；接點及文件列表量測；regression-release.txt |
| 3 | 用滾輪、滑塊及鍵盤到首末 → 確認最後批次／文字可達，提交操作固定 | 通過 | native-wheel-end／native-thumb-top／native-keyboard-end.json；native-join-wheel-end／native-join-thumb-top／native-join-keyboard-end.json及jpg |
| 4 | 長清單 → 空清單 → 返回長清單 → 確認沒有殘留前頁範圍 | 通過 | native-empty／native-return-long.json；主頁幾何回歸 |
| 5 | 縮放視窗、放大字級、重開文件列表 → 確認溢出重算，無整頁或水平捲動 | 通過 | 1360／1280／900原生量測；native-font125-folded／expanded.json及jpg；regression-release.txt |
| 6 | 比較同組Button、Combobox及狀態框 → 確認共用字型、尺寸與狀態角色 | 通過 | 標準兩列共享144寬、37高；窄版依可用寬度分配共同欄；放大字級依實際reqheight統一；measurements-summary.json |
| 7 | 比較同欄pause／state → 確認外框寬高差≤2 | 通過 | 主頁量測：x差0、width差0、height差0 |
| 8 | 比較同角色文字按鈕 → 確認外框等寬等高及文字完整 | 通過 | 來源四鈕144×37；下方動作144×37；footer兩鈕196×37；原生caption需52、缺陷8、修正52像素 |
| 9 | 檢查焦點、停用、忙碌及完成 → 確認尺寸穩定、下拉指示單一 | 通過 | exe-running.jpg；成品caption／indicator原生測試及最終EXE畫面；regression-release.txt |
| 10 | 比較同列上下邊界 → 確認差≤2 | 通過 | measurements-summary.json；來源列、兩設定列及footer同角色高度差0 |
| 11 | 比較上下同欄左右邊界 → 確認欄線一致 | 通過 | pause/state、join/detail/menu、來源工具列共享欄位；幾何回歸 |
| 12 | 比較每對相鄰動作 → 確認水平淨距4 | 通過 | 來源三對、詳情／版本、儲存／製作均4；逐對值見measurements-summary.json |
| 13 | 比較操作列與清單 → 確認垂直淨距8 | 通過 | table_frame.y − toolbar.bottom = 8；幾何回歸 |
| 14 | 比較文件列表與主頁內容 → 確認齊頭、底列無重複或祖先遮擋 | 通過 | 主頁強制layout後doc/main y差≤2回歸；最後齊頭畫面及量測；接點進出立即收回／恢復footer測試 |
| 15 | 最大化、1360×820、1280×720、900×640及列表收合／放大字級 → 重查可達性 | 通過 | 原生尺寸矩陣、regression-release.txt及正式EXE最大化／還原畫面 |
| 16 | 分別記錄功能、原生布局及正式EXE | 通過 | 回歸日誌、measurements-summary.json、final-native-*.jpg、exe-final.jpg、package.json及exe-result.json分開記錄 |
| 17 | 確認每個適用項目有本次證據 → 未解決落差不得算完成 | 通過 | 最終52模組一致、EXE退出0、原生callback錯誤0；cleanup.json記錄程序0與1905檔無占用。本表完成的是本次範圍，不代表此前整個專案所有頁面已驗收 |
| 18 | 尺寸／間距修正 → 保留失敗與修正量測 | 通過 | layout-red.txt、native-narrow-red.png、exe-menu-caption-red.jpg；caption原生8→52；齊頭回歸與成功量測 |

來源Treeview以完整列數計算yview與滑塊，部分可見列由Tk裁在視口底部。量測同時保存外框、列高及實際yview；不得把部分列當成已完整可讀的最後一列。接點Text依字元排版回報yview，前後各自捲動。文件列表使用同一AutoHideScrollbar；完整容納時回收軌道，長內容時滑塊跟隨該列表。

原生差異：圖面控制項高36，平台實測37；維持同組等高。回傳、主要提交及圖示／展開入口為不同尺寸角色。共用文件欄保留原生既有寬度，不把mock的示意欄寬當作字型縮小理由。

最終尺寸／狀態優先採用final-native-*.json與jpg，較早native-*資料保留作流程與缺陷追溯。來源空／fit／overflow的最後量測為final-native-empty／fit／overflow.json。文件列表父容器遮擋已修正，原生winfo_containing命中正確Treeview，內容實際可見；證據為native-sidebar-parent-red.jpg及final-native-1360.jpg、regression-sidebar-final.txt。

結論：本次範圍的所有適用項目通過。最後封裝SHA-256與source-manifest.json對應；正式EXE正常關閉，測試暫存已清理。

本次不適用：資料刪除確認、雲端送出同意、OCR影像操作及影片素材輸入。本頁只讀取既有音訊與字幕，不提供這些操作。既有語音頁的同意阻擋／保存重試、文字操作鈕／Text間距及底列回歸仍已執行。
