# Ticket #13 A：全頁外框設計審閱

> 歷史草案，未核准、不採用。使用者後續已要求以目前 UI 排版及功能直接改版，禁止重新設計並免提供設計圖。本批保留盤點與歷史證據；本輪執行改見 [現有 UI 重構證據](../../verification/v2-shell-refactor/README.md)，下方待確認文字為前輪紀錄。

2026-11-13。**盤點與設計稿已備妥；新增布局待使用者確認。A 未勾選，B～E 未開始。** 依 [Spec #12](https://github.com/newesp/ebook2mp4/issues/12)／[Ticket #13](https://github.com/newesp/ebook2mp4/issues/13)，不再按舊票逐頁先做專屬改版。

開啟 [設計檢閱器](index.html)，可選擇所有原尺寸畫面。這是本機靜態圖檢閱器，不是可操作產品原型；圖外的瀏覽器捲動只是檢閱圖片。正式 app 不使用整頁捲動包住內部 Text。

## 先看這幾張

| 目的 | 原尺寸設計 |
| --- | --- |
| 寬版文稿，共用導覽／文件／標頭／底列 | [1360×820](manuscript--normal.png) |
| 窄版與文件收合後回收空間 | [900×640 展開](manuscript--reduced.png)／[收合](manuscript--collapsed.png) |
| 語音設定及窄版試聽，同組等寬與固定操作 | [寬版](voice--normal.png)／[窄版設定](voice--reduced.png)／[窄版試聽](voice--reduced-preview.png) |
| 合併、接點與影片採同一外框 | [合併](assembly--normal.png)／[接點](joins--normal.png)／[影片](video-book--normal.png) |
| 完整容納設定不畫捲軸；真實長內容才有 | [偏好](ai--reduced.png)／[連線展開](ai--expanded.png)／[長錯誤訊息](ai--connection-error.png) |
| 空狀態不殘留捲軸或不適用操作 | [無異常](issues--empty.png)／[無換行變更](cleanup--empty.png) |
| 18pt 正文、處理中、失敗及取消 | [18pt 文稿](manuscript--18pt.png)／[處理中](narration--busy.png)／[保存失敗](assembly--failed.png)／[取消匯入](packages--cancelled.png) |

## 確認範圍

沿用現有綠色／紙面及 Microsoft JhengHei。新增布局是：兩列共用導覽；同一標題／工具帶與內容起點；唯一固定底列；列表收合整欄回收；專案資訊及訊息記錄同窗承載、返回原入口。詳細決策及「布局 → 原生責任 → 驗收」見 [布局對照](layout-contract.md)。

本批 80 張圖覆蓋 ticket 的 20 列，以及 28 組畫面／子狀態示例。`imports` 是文稿內文件管理選單的展開狀態，不新增另一張重複文件清單頁；搜尋列、頁籤與播放可共宿主。完整 [入口與越界盤點](inventory.md) 保留子路由及回呼／釋放責任。圖使用合成書稿，部分內容以代表資料說明空間；核准外框不授權省略未畫出的既有功能，也不視為 D 各頁專屬內容的完整核准。

最大化用 1536×864 作參考；正常1360×820、縮小1280×720／900×640、列表收合、適用18pt、展開、空／長文及工作狀態各有圖。正文放大不宣稱整套控制字型也已放大。真正最大化 client、Windows DPI、Tk scaling、控制字型壓力及所有原生互動保持未測。

## 分開保存的證據

- [功能／資料／K03 八項契約](function-contract.md)：來源、草稿、快照、版本、同意、失敗保存、任務、成品與生命週期。這是保留清單，不是已通過功能回歸。
- [布局量測](layout-measurements.json)：80 張圖的 header／port／footer、控制項及表單欄位外框、164 個實際區域的 owner／viewport／完整內容高度。
- [捲動契約](scroll-contract.json)：164 個畫面區域，加每區 short／fit／overflow／long 的邊界 fixture，共820筆。fixture 明列自己的量測來源及獨立 viewport，不能把 fixture 算成已操作整頁。
- [根清單逐項結果](../../verification/v2-unified-shell-a/check-list.md)／[驗證與限制](../../verification/v2-unified-shell-a/README.md)：設計幾何、畫面、功能、原生、EXE分開記錄。**未宣告 UI 驗收完成。**
- [繪圖來源](../../../tools/design_unified_shell_a.py) 只讀取目前 app 的 Python 來源以記雜湊及 AST 候選，不 import／啟動產品，不讀使用者書稿或金鑰。檔案指紋與清理見本批證據。

舊 `v2-manuscript-tools-design` 的固定滑塊／依頁型畫捲軸批次仍為失敗歷史，本批未把它升格為核准依據。現在的內容、字型換行、extent、offset、滑塊與圖來自同一繪圖模型；原生平台最小滑塊及輸入操作仍須後續量測。

依 [AGENTS.md](../../../AGENTS.md) 第12點：「版面調整先提供設計圖，取得使用者確認後才實作」。確認本批外框後，B 先收斂唯一父層與代表頁原生結構；C 全表接入並通過後，才展開 D。
