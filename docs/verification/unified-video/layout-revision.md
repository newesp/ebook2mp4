# Mock 布局修正對照

沿用 unified-video-v2 與本次使用者核准的修正。功能契約沿用 capability-map.md。

| 設計要求 | 原生實作 | 驗收 |
| --- | --- | --- |
| 素材頂列、主要預覽 | 素材類型、選檔、檔名與解析度在預覽上方；窄版換列 | 載入相同圖片／背景影片，檢查控制項位置與預覽可用空間 |
| 集中狀態與操作 | 一列摘要；返回、保存與保存狀態在左，成品及製作在右 | 寬版同列，窄版合理換列；保存、取消與重試行為保留 |
| 紅線對齊 | 文件列表操作列與製作範圍列共用高度與上緣 | 量測上緣與高度，誤差 ≤2 Tk px |
| 綠線對齊 | 文件清單與 Notebook 上緣一致 | 展開列表量測上緣，誤差 ≤2 Tk px |
| 唯一列表開關 | 展開時用既有左側開關，收合時才顯示 > | 音訊／影片往返與 F6；確認欄寬回收與重開入口 |

原生差異：保留 ttk 的頁籤與控制項外觀；真實預覽不使用 mock 示意媒體或模擬功能。

## 驗證記錄

- 功能回歸：`layout-functional.txt` 的 3 項製片、取消、保存重試與部分輸出流程通過。
- 音訊頁：`revision-native-tests.txt` 的 14 項音訊回歸通過；背景影片的定位、無聲預覽與長短素材欄位通過。該輪捲動比例斷言因內容區增高失敗，改驗最後一行可達及滾輪確實移動；補驗見下一項。
- 尺寸與合併：`revision-geometry-merge.txt` 的 125% 文字、訊息捲動與 2 項全書沿用影片流程通過。
- 範圍切換：正式 EXE 發現新頁面初次量測仍套窄版，已改由 editor Configure 完成量測後重排。`revision-layout-final.txt` 的 2 項布局與背景預覽測試通過，含切換本批／全書後的寬版頂列。
- 上述共有 22 個不同測試案例通過；原始失敗與補驗記錄均保留。

`revised-metrics.json` 記錄實際 Tk client 尺寸：1536×864、1280×720、900×640。列表展開時，紅線兩側上緣差與綠線兩側上緣差均為 0 Tk px。`native-metrics.json` 另記錄 900×640 的較大文字驗收；對應畫面為 `native-900x640-125.png`。

修改檔案：`total_video_desktop.py`（素材、預覽、底部與重排）、`assembly_desktop.py`（全書影片底部）、`production_desktop.py`（唯一列表入口）、`narration_desktop.py`（窄版 >）、`manuscript_desktop.py`（左右列對齊），以及對應原生測試。

## 正式封裝驗收

正式成品位於 `dist/ebook2mp4`。`revision-final-prebuild.json` 確認程式已關閉，1905 個成品檔案均可獨占讀取；`revision-final-build.txt` 記錄最後一次成功建置。`package.json` 核對 45 個應用模組均符合目前原始碼，內附 FFmpeg／FFprobe 可執行。

使用 computer-use 操作隔離合成專案。音訊頁 >、影片列表展開／收合、紅綠線對齊、頁籤鍵盤切換與集中底部操作皆已檢查。最後修正版另確認全書統一素材初次顯示為寬版、切換沿用各批影片後底部保持集中、返回本批保留圖片及 720p；實際更新 MP4 後顯示已完成並保存。

正式視窗截圖含標題列為 1704×1066；先前同輪最大化檢查為 1920×1020。這些是實體截圖尺寸，不當作 Tk client 尺寸。最後修正版畫面：`exe-final-book-uniform.png`、`exe-final-book-merge.png`、`exe-final-batch.png`、`exe-final-completed.png`。音訊入口證據：`exe-audio-list-entry.png`。

`revision-media/` 保留正式 EXE 產生的 0.2 秒合成 MP4 與同版 SRT；雜湊見 `revision-media.json`。使用純色測試圖，不代替使用者素材或 mock 圖；本次未連線製作語音。背景影片與完整全書合併由原生測試驗證，正式 EXE 本輪的媒體製作驗收使用本批路徑。

驗收程式已正常關閉。本次暫存與程序清理結果見 `revision-cleanup.json`；正式成品、需求、mock、測試與驗證證據保留。
