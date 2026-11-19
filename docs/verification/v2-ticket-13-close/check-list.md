# Ticket #13 根清單結案覆核

2026-11-19。EXE、來源版本、操作路徑與限制見 [驗收紀錄](README.md)。本表對照根目錄 18 項，沿用已核准的現行 UI。當次未改動的既有介面，以本次回歸及原生全頁矩陣覆核歷史操作證據。

| 項次 | 結果 | 量測與操作證據 |
| --- | --- | --- |
| 1 短文／空狀態 | 通過 | PDF 異常兩筆處理完，空狀態不留表單軌道。短版本差異無軌道。試聽／接點短文與空狀態有原生契約。[PDF](exe-pdf-empty.jpg) · [版本](exe-versions-short.jpg) · [接點](voice-join/join/scroll-contract.json) |
| 2 溢出及滑塊比例 | 通過 | 接點短／fit／overflow／long 實際 Text.count 與 yview 契約。影片及成品的 30 組長短契約在前批，修正沿用且成品回歸通過。[接點量測](voice-join/join/scroll-contract.json) · [影片量測](../v2-video-versions-matrix/scroll-contract.json) |
| 3 首末與固定操作 | 通過 | 版本長差異已用滾輪、拖曳至 180 段、Ctrl+Home 返回首行，固定還原動作可達。影片及接點的各種輸入見前批正式操作。[滾輪](exe-versions-wheel.jpg) · [末端](exe-versions-end.jpg) · [鍵盤](exe-versions-keyboard.jpg) · [前批操作](../v2-production-exe-acceptance/README.md) |
| 4 長短／空狀態轉換 | 通過 | 長差異切朗讀版本只剩少量差異，軌道消失；PDF 完成異常到空頁。接點原生空狀態轉換通過。[短差異](exe-versions-short.jpg) · [空頁](exe-pdf-empty.jpg) · [原生案例](voice-join/native-tests.txt) |
| 5 尺寸與展開收合 | 通過 | 全頁四尺寸矩陣、試聽及接點 10／13 pt、文稿／版本 18 pt。AI 連線、Kokoro 詳情按需展開。正式最大化與還原 PDF 雙欄可達。[矩陣](native/measurements.json) · [PDF 還原](exe-pdf-issues-restored.jpg) |
| 6 元件風格 | 通過 | 四尺寸原生 controls 含樣式、外框及狀態。主要／次要操作使用現有共用風格，正式播放／停止狀態可辨。[controls](native/measurements.json) · [成品](exe-outputs-idle.jpg) |
| 7 同欄輸入外框 | 通過 | 本批 PDF 兩欄回歸逐對比對 OCR 安裝按鈕與旋轉輸入的上緣、寬、高，誤差≤2。[回歸](test_source_issue_view.txt) · [正式表單](exe-pdf-processing.jpg) |
| 8 同組按鈕 | 通過 | 試聽兩鈕 130×37；成品次要三鈕各字級同寬高，10 pt 114×37，13 pt 見逐對數值。[試聽](voice-join/voice/native-layout-regression.json) · [成品](output-metrics.json) |
| 9 焦點、停用與忙碌 | 通過 | 取消同意阻止試聽。Kokoro 缺包停用試聽。成品待命／播放結束停用停止。忙碌與隱藏頁命令守衛回歸。[同意](exe-voice-consent.jpg) · [停止](exe-outputs-play.jpg) · [守衛](test_unified_shell_integration.txt) |
| 10 同列對齊 | 通過 | 成品次要按鈕六組 y 與高相同。PDF 旋轉／OCR 同列上緣誤差≤2。[成品](output-metrics.json) · [PDF 回歸](test_source_issue_view.txt) |
| 11 同欄對齊 | 通過 | PDF 兩欄與 AI 表單原生矩陣。共用區元件固定實例，頁面切換保持邊界。[矩陣](native/measurements.json) · [回歸](test_v2_ai_settings.txt) |
| 12 水平淨距 | 通過 | 試聽按鈕及底部儲存／下一步為 4。成品四動作三個淨距均為 4，六組尺寸字級逐對核對。[成品數值](output-metrics.json) · [試聽數值](native/measurements.json) |
| 13 垂直淨距 | 通過 | 試聽文字操作列至 Text 為 8，四尺寸一致。共用標頭帶對照無超過 2 的偏移。[試聽數值](native/measurements.json) · [基準彙整](final-audit.json) |
| 14 標頭與內容基準 | 通過 | 全頁標頭差≤2，接點另有實際外層布局後的基準線驗收。[全頁](final-audit.json) · [接點](voice-join/join/shell-anchors.json) |
| 15 四尺寸與字級矩陣 | 通過 | 66 張全頁原生畫面，最大化、1360×820、1280×720、900×640；試聽與接點含字級／列表狀態，成品另六組外框。[矩陣](native/measurements.json) · [專項](voice-join/results.json) · [成品](output-metrics.json) |
| 16 分開記錄驗證層次 | 通過 | 功能回歸、原生矩陣及正式 EXE 操作均在 README 各段記錄。[交付](README.md) |
| 17 本版證據與例外 | 通過 | 沿用現有 UI 已授權，Kokoro 現行介面獲本次明確確認。真實離線 CPU、付費服務及模型安裝保留原功能票的驗收條件。[範圍與對照](README.md) |
| 18 缺陷及修正版數值 | 通過 | 前批成品淨距為 6，13 pt 次要鈕寬差 6。修正版同寬、淨距 4，新增原生斷言。[缺陷數值](../v2-video-versions-matrix/native-matrix.json) · [修正數值](output-metrics.json) · [針對回歸](output-regression.txt) |

