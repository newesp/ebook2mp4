# Kokoro CPU 工作票與實作入口

2026-11-04。依使用者核准的九票拆分發布。父規格為 [#2](https://github.com/newesp/ebook2mp4/issues/2)。所有票均標記 ready-for-agent；標籤不表示可跳過阻擋關係、可行性結果審閱或 UI 設計圖確認。

| 工作票 | 交付 | 被哪些票阻擋 |
|---|---|---|
| [#3／K01](https://github.com/newesp/ebook2mp4/issues/3) | 官方中文版 CPU 可行性驗證 | 無 |
| [#4／K02](https://github.com/newesp/ebook2mp4/issues/4) | 共用語音服務能力與合成接點 | #3 |
| [#5／K03](https://github.com/newesp/ebook2mp4/issues/5) | 操作流程與介面設計圖確認 | #3 |
| [#6／K04](https://github.com/newesp/ebook2mp4/issues/6) | 安裝與移除離線語音包 | #5 |
| [#7／K05](https://github.com/newesp/ebook2mp4/issues/7) | 音色設定與本機試聽 | #4、#6 |
| [#8／K06](https://github.com/newesp/ebook2mp4/issues/8) | 模型重用、閒置卸載與清理 | #7 |
| [#9／K07](https://github.com/newesp/ebook2mp4/issues/9) | 批次 MP3／SRT | #7 |
| [#10／K08](https://github.com/newesp/ebook2mp4/issues/10) | 中斷續作與模型版本保護 | #9 |
| [#11／K09](https://github.com/newesp/ebook2mp4/issues/11) | 封裝與全書離線驗收 | #8、#10 |

## 從哪開始

先做 #3。先讀父規格與該票的完整內容及留言，再檢查目前工作區及專案指示。不要覆蓋工作前已存在的未提交變更。

第一階段使用官方中文版模型及獨立 Python 3.12，驗證純 CPU、首次完整離線、中文品質、效能及資源釋放。保留實際音檔及量測證據，清理測試暫存與程序。取得使用者對結果與正式整合範圍的決定後，才將 #3 視為完成。無須在這張票提前改正式 UI 或展開其他工作票。

## 發布驗證

已逐票核對正文、ready-for-agent 標籤、原生父子關係及原生阻擋關係，共九張子議題與十條阻擋邊。父議題的標題、正文、狀態及標籤未變動。各票的正式內容以 GitHub 為準；同目錄保留發布時的正文副本、核准拆分資料與發布驗證紀錄。
