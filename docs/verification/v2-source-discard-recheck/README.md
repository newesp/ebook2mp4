# TXT 來源預覽與 #13 待驗項覆核

2026-11-18。現有正式 EXE 在窄版可顯示 TXT 差異，卻保留先前操作列。調整視窗尺寸後，「放棄預覽」及「套用預覽」才出現。原生回歸重現兩個原因：TXT 預覽完成時未主動刷新頁面操作，且共用操作列刷新會先取消映射仍適用的按鈕。見 [原 EXE 窄版](baseline-exe-narrow-preview.png)、[失敗回歸](red.txt)。

TXT 預覽完成後立即刷新操作，並保留仍適用的按鈕。放棄後清除候選、差異、捲軸及舊提示，回到原編碼表單。TXT 沒有 PDF 原頁操作，短差異完整容納時也沒有捲軸。既有套用、備份與草稿契約由回歸覆核。見 [綠燈回歸](green.txt)。

| 驗收 | 結果 |
| --- | --- |
| 功能 | 15 項回歸通過，包含 TXT 預覽／放棄／備份、OCR 忙碌提示、兩項共用路由、AI 設定及版本頁。見 [功能紀錄](regression.txt)。 |
| 原生 TXT | 最大化、1360×820、1280×720、900×640。滾輪、Page Down、捲軸到末端，底部按鈕位置固定；兩按鈕均為 114×37，水平淨距 4 Tk px。見 [原生量測](native-layout.json)、[900×640 末端](native-900x640-preview.png)及[放棄結果](native-900x640-discard.png)。 |
| 原生接點 | 五案通過，含保存失敗、捲動狀態與 24 筆基準線；最大差 0.5 Tk px。見 [執行紀錄](join/native-tests.txt)及[量測](join/join/shell-anchors.json)。 |
| 正式 EXE | 窄版載入預覽 → 兩按鈕立即顯示 → 拖滑塊到第 200 行 → 點「放棄預覽」→ 回編碼表單 → 返回同一草稿。獨立設定與系統 PATH 啟動，退出碼 0。見 [預覽](corrected-exe-narrow-preview.png)、[最後一行](corrected-exe-narrow-end.png)、[放棄](corrected-exe-narrow-discard.png)、[草稿](corrected-exe-draft.png)及[執行紀錄](corrected-exe-launch.json)。 |

固定成品為 `dist/ebook2mp4/ebook2mp4.exe`。53 個封裝應用模組與來源一致，內附 FFmpeg／FFprobe 可執行。見 [封裝](build.txt)、[來源比對](package.json)、[驗收清單](check-list.md)、[最後占用檢查](final-preflight.txt)及[清理](cleanup.json)。

#13 維持開啟。這一輪完成上次交接列出的 TXT、OCR、路由及原生接點補驗。下一批處理正式 EXE 的製作取消／失敗、接點與成品版本逐頁操作，再核對 D／E 的其他繼承情境。
