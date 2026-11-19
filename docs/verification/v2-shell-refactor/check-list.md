# 本輪根 check-list.md 結果

2026-11-13。範圍：沿用現有 UI 的共用外框接入與本輪溢出修正。來源／成品：`native-final/source-hashes.json`、`source-change-summary.json`、`package.json`。以下尺寸與量測為 Tk 座標；EXE 圖像另有 Windows 縮放。

| 根清單項目 | 結果 | 操作、預期／實測與證據 |
| --- | --- | --- |
| 1 短內容／空狀態 | 通過 | 長稿 → 短文 → 檢查 yview=(0,1)，無軌道。`native-visible/short-editor.png`；最後短內容見 `native-final/`；EXE `06`、`18`、`33`。 |
| 2 剛好容納／溢出／長內容 | 通過 | 聲音設定 Canvas：內容 406、viewport 242、offset 164，可見比例 0.596059；寬版 viewport 467、yview=(0,1)。`native-final/measurements.json` voice-settings-*、`voice-scroll-verified.txt`。 |
| 3 滾輪／滑塊／鍵盤首末 | 通過 | 主稿、聲音設定、成品詳情各自操作；末端 fraction=1，開頭=0，固定區不動。`native-visible/manual-*`、`native-final/voice-settings-*`、EXE `11`～`13`、`30`～`32`。 |
| 4 長 → 空／短 → 返回 | 通過 | 表單移除長內容 → 等待重算 → 確認無殘留範圍；異常空狀態 → 返回來源。`voice-scroll-verified.txt`、`tools-lifecycle-video.txt`、`native-visible/short-editor.png`。 |
| 5 尺寸／字級／展開 | 通過 | 四尺寸、列表及適用 18pt → 檢查 viewport、換列及固定動作。`native-final` 72 筆、`join-tests` 24 筆、EXE `25`、`29`～`33`。平行區域各自捲動，沒有整頁包內部正文。 |
| 6 同組控制項風格／角色 | 通過 | 原共用 Workspace 樣式；同列 Button／Entry／Combobox 高度 37。`final-regression.txt`、`native-final/measurements.json` controls。 |
| 7 同欄按鈕／輸入外框 | 通過 | PDF 旋轉／OCR：1360 寬 157／158；1280 寬 138／137；900 寬 280／280；高均 37、y 差 0。寬差最多 1≤2。`components/measurements.json` 與完整畫面。 |
| 8 同角色文字按鈕尺寸 | 通過 | 固定範例／帶入選取文字，每組 130×37／130×37。`native-audit.json`、`voice-scroll-verified.txt`、EXE `28`～`33`。 |
| 9 預設／焦點／停用／忙碌 | 通過 | 固定 dispatcher → 切換 disabled／忙碌 → 確認阻擋、進度及取消。`final-regression.txt`、`ownership-verified.txt`、EXE `04`、`08`、`15`、`19`、`34`。Menubutton 只保留主題箭頭。 |
| 10 左右同列對齊 | 通過 | 共用標頭上緣／高度差≤2，最終 68 組無失敗；PDF 欄位 y 差 0。`native-audit.json`、`components/measurements.json`。 |
| 11 上下同欄／列距 | 通過 | PDF 四列維持 0／1 欄；OCR／旋轉寬差≤1；聲音設定窄版欄名換行、選單／更新完整可達。`components/`、`voice-scroll-verified.txt`、EXE `30`。 |
| 12 相鄰動作淨距 | 通過 | 試聽兩文字按鈕=4；保存／目前下一步=4。全書預設量目前可見套用按鈕，隱藏按鈕原始值保留。`native-audit.json` 逐筆列值與 label。 |
| 13 操作列與內容淨距 | 通過 | 帶入文字按鈕底 → Text 上緣=8。`native-audit.json` 每組 text_gap=8、`voice-scroll-verified.txt`。 |
| 14 標頭／內容兩條線 | 通過 | 影片 → 返回 → 確認舊 row minsize 釋放；接點經正常外層 Configure。前版 18 組失敗 → 最後 0 組；24 組接點 delta 最大 0.5≤2。`before-track-fix/`、`native-audit.json`、`join-tests`、`header-track-final.txt`。 |
| 15 四尺寸／字級／收合重查 | 通過 | 最大化、1360×820、1280×720、900×640；主稿／版本 18pt，接點共用字級 10／13；共用實例及 parent 不變。`native-final`、`join-tests`、EXE `29`～`33`。來源字級不套用至固定設定表單，沒有額外 18pt 表單模式。 |
| 16 三種驗證分開記錄 | 通過 | 功能 stdout、原生幾何／畫面、EXE 操作／解碼分開保存。見 README；未以封裝或數量代替操作。 |
| 17 適用項有本輪證據 | 通過（上述範圍） | 本輪外框及溢出皆有證據；真實服務、Kokoro 品質／推論及繼承完整人工矩陣仍未測，不屬此次通過範圍，未關閉 Ticket #13。 |
| 18 缺陷版／修正版保留 | 通過 | 影片列偏移原生 red → green；聲音裁切 EXE `26` → `29`～`33`；表單 stale extent stdout → 最後測試。數值見 README、native-audit、voice-scroll-verified。 |

啟動最大化另見 `startup-state.txt`（state=zoomed，1536×793）；正式最大化見 EXE `33`。原生及 EXE 測試均正常關閉，清理及占用另存 `cleanup.json`。
