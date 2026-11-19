# 影片工作區：實作前盤點

以目前工作目錄內容為基線。需求與 mock v2 已核准實作；mock 的記憶體狀態與模擬成功不進入產品。

| 既有能力 | 新入口 | 保留的契約與驗證方式 |
| --- | --- | --- |
| 音訊製做的本批 MP4 | 影片製作／本批／畫面與素材 | TotalVideoPage + batch_video_target。完整批次 MP3/SRT；不加全書停頓。實際 FFmpeg 製作、另存及不同批次設定往返。 |
| 全書統一素材製片 | 影片製作／全書／統一素材 | TotalVideoPage + total-audio route。總音訊缺少時仍可選素材；開始受有效性阻擋。實測缺項、保存、真實預覽與製作。 |
| 全書沿用各批影片 | 影片製作／全書／沿用各批影片 | AssemblyPage(movie=True) + OutputJob。有效 MP4/SRT、選批排序、接點確認；不要求總 MP3。實測原生與 video_merge 回歸。 |
| 全書音訊與獨立格式 | 全書合併 | 保留 OutputControls / OutputJob、部分完成、續作與只重試未完成格式。沿用 outputs 回歸。 |
| 不同來源的成功成品 | 任務與成品／版本與來源比較 | output_versions route 獨立。播放、停止、同版 SRT 另存、資料夾、來源比較與回製作。 |
| 真實圖片與背景影片 | 畫面與素材 | 沿用 inspect_background、background_frame、stream_frames；靜音、循環／末格、長片裁切及專案內保存。 |
| 任務與恢復 | 任務與成品 + 固定狀態／動作 | 頁面快取不重建任務。來源啟動快照、production lock、失敗／取消保留舊版、保存失敗顯式重試。 |
| 文件列表與返回 | 範圍列窄圖示、底部返回 | 沿用全域文件列表；釋放實際欄寬。各路徑快取保存輸入、選取及頁籤。 |

呈現採共用原生 Notebook 與範圍列；不合併三種底層 job、product route 或視覺設定。語音、文稿及音訊版面不重排。
