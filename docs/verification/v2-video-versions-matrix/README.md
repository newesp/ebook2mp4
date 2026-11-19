# Ticket #13 影片製作與成品版本補驗

2026-11-18。使用無成品書籍及含 14 批來源的隔離書籍。多批書籍的 MP3／SRT、總影片使用合成測試音及正式附帶的 FFmpeg 建立。

## 修正與原生結果

- 舊版「影片製作 → 來源與順序」和「任務與成品」即使文字完全容納，也會顯示零行程的捲軸。兩個分頁改用共用 `AutoHideScrollbar`。回歸分別測短文、300 行、捲到末行、切回短文。[來源舊版](exe-empty-source-before.jpg) · [任務舊版](exe-empty-task-before.jpg) · [修正前測試](native-red.txt) · [修正後測試](native-scroll-regression.txt)
- 原生兩頁共 192 組畫面狀態。最大化的 Tk 客戶區為 1536×793。另量測 1360×820、1280×720、900×640、10／13 pt 與文件列表顯隱。受量測的操作均在客戶區內。捲動另取 30 組測量，三個文字區的短文、剛好容納、溢出、長文和返回短文均符合幾何契約。[原生尺寸](native-matrix.json) · [捲動量測](native-scroll.json) · [捲動契約](scroll-contract.json)
- 於 900×640、13 pt 且列表展開時，影片「來源與順序」空書的內容高度 110、視口 207，無軌道。14 批來源的內容高度 594、視口 228，最大行程 366。成品詳情在同尺寸的空書收合技術資訊時內容高 132、視口 193，無軌道。展開成品的技術資訊後內容高 25,696、視口 193，可抵達末行。[影片原生畫面](native-long-video-900x640-13-tab1.png) · [成品原生畫面](native-long-versions-900x640-13.png)
- 成品版本原生操作回歸通過，涵蓋三條成品路徑的詳情、返回、播放及另存。[回歸輸出](native-versions-regression.txt)

## 正式 EXE 操作

固定成品更新至 `dist/ebook2mp4/ebook2mp4.exe`，SHA-256 `c4cb7917937813f519f8b66307c74c3f00a57fdf63a335959fb22237b63e8f4c`。封裝內的 `ebook2mp4.video_workspace` 與來源相符。內附 FFmpeg／FFprobe 及 Tesseract 套件檔案的雜湊與更新前一致。實體畫面尺寸為 1920×1020、1702×1065、1127×840，Windows 顯示縮放 125%。13 pt 在原生矩陣量測。[封裝比對](package.json) · [來源雜湊](source-digests.json)

| 操作 | 結果 | 證據 |
| --- | --- | --- |
| 空書 → 影片製作 → 來源與順序、任務與成品 | 1702×1065 下比對同一本書。新版兩區均顯示缺少成品提示且不留捲軸。 | [短來源](exe-empty-source-after.jpg) · [短任務](exe-empty-task-after.jpg) |
| 空書 → 版本與來源比較 → 查看來源與版本 | 三條路徑均顯示尚未製作。播放與另存停用。短詳情無空軌道。 | [版本清單](exe-empty-versions-after.jpg) · [短詳情](exe-empty-details-after.jpg) |
| 多批書 → 來源與順序 → 最大化再縮至 1127×840 | 最大化可看到整段，無捲軸。縮小後才顯示軌道。用滾輪到末行、拖滑塊回首行、按 Ctrl+End 回末行。 | [最大化](exe-long-source-max.jpg) · [縮小](exe-long-source-narrow.jpg) · [滾輪](exe-long-source-wheel.jpg) · [拖曳](exe-long-source-thumb.jpg) · [鍵盤](exe-long-source-keyboard.jpg) |
| 來源與順序 → 任務與成品 → 返回 → 展開文件列表 | 短任務無軌道，返回來源保留閱讀位置。文件列表與來源各有捲軸，標頭和製作按鈕留在原位。 | [短任務](exe-long-task-fit.jpg) · [返回](exe-long-source-tab-return.jpg) · [展開文件列表](exe-long-source-files-expanded.jpg) |
| 版本與來源比較 → 總影片 → 來源與版本 | 用滾輪移到中段、滑塊拖到末行、按 Ctrl+Home 回首行。文件列表、導覽和底部操作列固定。展開技術資料後 Ctrl+End 到最後一列。 | [窄版清單](exe-long-versions-table.jpg) · [滾輪](exe-long-details-wheel.jpg) · [拖曳](exe-long-details-thumb.jpg) · [鍵盤](exe-long-details-keyboard-home.jpg) · [技術末行](exe-long-details-technical-end.jpg) |
| 收合技術資料 → 回版本清單 → 切尚未製作 → 返回已製作詳情 | 短詳情清除軌道，返回長詳情重新顯示有效捲軸。 | [收合](exe-long-details-collapsed.jpg) · [長轉短](exe-long-to-short-details.jpg) · [短轉長](exe-short-to-long-details.jpg) |

兩次新版啟動都正常結束。本輪測試專案、安裝依賴及建置暫存已清理。正式成品通過占用檢查。[清理紀錄](cleanup.json) · [最終占用檢查](final-preflight.txt)

## 尚待修正的版面落差

成品版本底部「播放／停止／另存／前往」三處相鄰淨距皆為 6 Tk 像素，規範值為 4。13 pt 時，同組的播放、停止為 136×42，另存為 142×42，寬度差 6，超過 2 像素門檻。這兩項留 Ticket #13，待版面調整確認。[原生外框](native-matrix.json)

成品空狀態仍可按「停止播放」。已有有效成品的任務摘要仍顯示「已完成 · 等待保存」。這兩項狀態落差納入後續回歸。Ticket #13 的 D／E 保持開啟，仍須核對文稿版本、AI 設定、來源與語音的剩餘正式操作。[空狀態](exe-empty-versions-after.jpg) · [任務摘要](exe-long-details-thumb.jpg) · [驗收清單](check-list.md)
