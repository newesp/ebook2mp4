# 檢查接點：根 UI 清單逐項結果

2026-11-12。範圍：音訊接點頁、受影響的共用導覽／footer、既有影片接點與語音間距。依根目錄 [check-list.md](../../../check-list.md) 的原順序記錄。來源及正式程式版本以 [source-manifest.json](source-manifest.json)、[package.json](package.json) 為準；設計稿的通過紀錄沒有拿來代替本表。

原生尺寸：最大化、1360×820、1280×720、900×640；10pt／13pt；Tk DPI 96.09、scaling 1.33465。正式桌面圖的 scale_factor 為 1.25，原生量測以 Tk 座標為單位。Native Text 使用實際字型行高；靜態設計的 px 不冒充原生 DPI。

| # | 根清單項目與操作路徑 | 結果 | 本輪數值／畫面／操作證據 |
|---:|---|---|---|
| 1 | 開短內容／空狀態 → 確認無捲軸、無空軌道、提示可見 | 通過 | native-scroll.json 四區 short；final-checks 的空接點切換，空頁隱藏無效設定及保存 |
| 2 | 剛好容納／溢出／長文 → 比較所屬捲軸、比例及行程 | 通過 | scroll-contract.json 共 16 區；Text 有效視口 167，fit 153 無軌、overflow 170 有軌，實際 fraction=167/170；其他區同源原生量測 |
| 3 | 滾輪／滑塊／鍵盤到首末 → 確認固定工具及最後一行 | 通過 | native-left-wheel、native-left-drag-end、native-left-key-end；末行 180 可達，後批保持首行；原生回歸逐區到 yview[1]=1 |
| 4 | 長文 → 空 → 返回 → 確認無殘留範圍 | 通過 | final-checks 的長文、短文、空 joins、恢復 joins；短文 yview=(0,1)，軌道移除 |
| 5 | 改尺寸／字級／展開收合 → 確認重算、無水平或巢狀整頁捲動 | 通過 | native-visual 七狀態；900 詳情改為專用內容；整頁不捲動、左右各有 owner；正式 exe-narrow-detail |
| 6 | 比較同組 Button／Entry／Combobox → 核對樣式與狀態 | 通過 | Workspace 共用主題；設定與播放外框 120×37／120×42；主操作 Primary；下拉各一指示 |
| 7 | 比較同欄按鈕與輸入 → 核對外框同寬同高 | 通過 | native-layout-regression：停頓／長度／播放／停止每組寬高差 0，低於 2 Tk 像素門檻 |
| 8 | 比較同組同角色文字按鈕 → 逐對記錄外框 | 通過 | 校對 128 寬、前後導航 112、播放 120；組內同高；共用流程同寬。語音帶入文字等寬以 shared-busy-regressions 重驗 |
| 9 | 預設／焦點／停用／忙碌 → 確認尺寸不變與文字完整 | 通過 | 原生 preparing 圖、取消與晚到預覽回歸；pause／edit／save／import 停用；實際 Space 收合詳情、文件列表焦點可見；13pt 標籤完整 |
| 10 | 比較左右同列控制項上下緣 | 通過 | 原生四個設定／播放元件 120×37 或 120×42；左右 Text 上緣及高度差 0 |
| 11 | 比較上下同欄左右邊界 | 通過 | 原生播放 x=右 Text x；標頭及各自 Text 齊頭；標籤欄最小 80；native-visual.json |
| 12 | 計算每對相鄰動作的水平淨距 | 通過 | 播放／停止、上一／下一均 4；原生注入 6 確認失敗、還原 4 通過。語音保存／下一步由 shared-busy-regressions 驗 4 |
| 13 | 計算操作列到內容區的垂直淨距 | 通過 | 左右校對列到 Text 皆 8；語音操作列／Text 必要案例重驗通過 |
| 14 | 相鄰區塊齊頭 → 確認固定列無重疊、裁切或父容器遮擋 | 通過 | native-visual 原尺寸圖與量測；文件清單／主面板同起點；固定 footer 全窗配置；校對按鈕上移，舊底部工具列移除 |
| 15 | 最大化／1360／1280／900／字級／列表收合重查 | 通過 | maximized-regression、native-layout-regression、native-visual；最低 4 完整行、內嵌詳情至少 6 行。EXE 啟動前置操作前 IsZoomed=true；900 窄版正式頁可操作 |
| 16 | 功能、原生 mock 對照、正式 EXE 分開記錄 | 通過 | README 三層分列；媒體 8、原生針對性批次、package53模組及正式操作證據分開；EXE 未以封裝數量代替操作 |
| 17 | 每項有本次版本證據；未解決落差列未完成 | 通過本次範圍 | 核准設計已實作。原生主題 37／42 高與導覽按實際字寬換列的差異已在 README 說明；主體布局與閱讀預算符合。最後 key 修正以最終封裝補驗；早期失敗記錄不作通過證據 |
| 18 | 缺陷前後保留針對性原生量測／回歸 | 通過 | baseline-layout：校對位於文字下方、播放間距 6；修正版為標頭及 4；native-layout-regression 另注入 6 → 失敗 → 還原 4 → 通過 |

實際保存契約另以 exe-save-warning.json 證明：僅第一警告確認時，保存後為 true／false，製作保持停用；第二警告確認後才可製作。最終 EXE 的版本、補驗與正常關閉結果見 README 及 exe-final.json。清理與成品占用以 cleanup.json 為準。
