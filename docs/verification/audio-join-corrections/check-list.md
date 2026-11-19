# 本批UI驗收

依根目錄check-list.md的18項逐項記錄。範圍為全書合併／檢查接點及其文件列表、固定底列；其餘製作頁的表單內部未修改。尺寸均為Tk座標；正式EXE畫面另為125%DPI的實體截圖。

| 項目 | 操作與可觀察結果 | 結果 | 本批依據 |
| --- | --- | --- | --- |
| 1 短文／空狀態 | 載入短文或清空接點 → 無捲軸、無空軌道，提示可見 | 通過 | native-scroll.json、scroll-contract.json、原生回歸 |
| 2 剛好／溢出／長文 | 前批、後批、詳情、文件列表分別載入四種長度 → 依實際溢出顯示捲軸 | 通過 | native-scroll.json及16筆scroll-contract.json |
| 3 首末可達 | 用滾輪、滑塊及鍵盤捲動前批 → 最後一行可達；後批及固定區域不動。原生回歸分別測前後批 | 通過 | exe-actions.json的6張首末圖、native-scroll.json |
| 4 長→空→返回 | 長來源 → 無接點 → 返回 → 無殘留範圍 | 通過 | final-reading-transition-tests.txt |
| 5 縮放／展開 | 1360／1280／900、10／13pt及詳情／文件切換 → 獨立捲動，無水平／整頁捲動 | 通過 | native-visual.json、native-layout-regression.json、原尺寸PNG |
| 6 元件風格 | 比較接點選擇、停頓、片段長度、播放／停止與保存 → 共用Workspace／Primary樣式 | 通過 | 原尺寸PNG與native-layout-regression.json |
| 7 同欄欄位 | 停頓、片段長度、播放、停止 → 10pt皆120×37；13pt皆120×42 | 通過 | native-layout-regression.json |
| 8 同角色按鈕 | 前／後批校對、上一個／下一個及播放／停止各自同尺寸，文字完整 | 通過 | native-visual.json；長標籤校對與選擇導覽為不同尺寸角色 |
| 9 狀態尺寸 | 預設、停用、焦點、準備／停止、保存失敗 → 控制項尺寸不變，單一下拉指示 | 通過 | 原生預覽／失敗／準備回歸與PNG |
| 10 同列邊界 | 左右讀者標頭／Text及設定列 → 上下緣、高度一致 | 通過 | native-visual.json、native-layout-regression.json |
| 11 同欄邊界 | 左讀者／停頓欄及右讀者／播放群 → 欄線一致 | 通過 | native-visual.json |
| 12 水平淨距 | 播放／停止及同組動作 → 實測4Tk | 通過 | native-layout-regression.json；注入6Tk缺陷可被攔住 |
| 13 垂直淨距 | 校對控制項下緣 → Text上緣 → 實測8Tk | 通過 | native-layout-regression.json |
| 14 相鄰區塊 | PDF文稿 → 檢查接點 → 外層布局後分別量測標頭帶／內容起點；文件收合再展開 | 通過 | shell-anchors-before.json與shell-anchors.json；外框差0Tk，中心差≤0.5Tk |
| 15 視窗／字級 | 最大化、1360×820、1280×720、900×640，10／13pt、列表收合 → 控制項可達 | 通過 | shell-anchors.json、native-layout-regression.json；900文件列表在內頁開啟 |
| 16 三種驗收 | 功能、原生mock對照、正式EXE分開記錄 | 通過 | README.md的三種結果；14項回歸、布局數值及最終EXE的實際操作分列 |
| 17 本次證據 | 每項適用項目連結本批版本結果 | 通過 | package.json與exe-actions.json使用相同最終EXE雜湊；exe-start.json正常結束；資源清理另見cleanup.json |
| 18 缺陷對照 | 保存兩條基準線及末行定位的失敗／通過量測 | 通過 | shell-anchors-before.json、first-load-red.txt、first-load-endpoints-before.json、first-load-endpoints.json |

三項文稿試聽按鈕案例的內部布局未受本次更動影響，依元件規範按修改範圍選擇案例。本批以相同原生Button／Combobox角色與實際外框驗證，不拿樣式名稱替代數值。
