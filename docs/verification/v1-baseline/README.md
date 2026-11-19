# v1 完整基準封存

2026-11-11。已保存 `archives/v1/source`、完整 `archives/v1/ebook2mp4` 與 `archives/v1/manifest.json`。4,052 個檔案、614,426,176 bytes；逐檔 SHA-256 全數一致。封存不覆寫、不作建置目錄、不加入 Git 二進位。Git HEAD、原工作區清單、固定依賴、啟動／重建方式與排除項在 manifest；原先未提交差異另保留 working-tree.patch。必要未追蹤 Python、測試、資源、建置設定與文件均由磁碟複製，沒有還原工作區。

封存前：沒有正式程式／Python／媒體程序；正式成品 1,905 檔均可獨占開啟及釋放。`package.json`：45 個封裝應用模組與當前來源逐一比對程式碼、常數及行號資料一致；包內 FFmpeg／FFprobe 實際啟動。

## 獨立執行與操作

| 路徑 | 可觀察結果 | 證據 |
| --- | --- | --- |
| 從封存來源 `python -m ebook2mp4`，cwd 為封存 source，PYTHONPATH 只有隔離依賴 | 自動開啟合成專案 → 編輯「封存來源編輯驗證。」→ 儲存朗讀稿 → 已儲存可朗讀 → 正常關閉，exit 0 | source-saved.jpg、v1-source-launch.json |
| 封存完整 EXE，cwd 在隔離專案，PATH 僅 Windows 系統目錄 | 文稿 → 語音 → 音訊 → 播放成功 → 全書合併 → 成品版本 → 播放 MP4 與字幕 → 正常關閉，exit 0 | package-audio.jpg、package-video.jpg |
| 重開封存 EXE | 載入同隔離專案 → Ctrl+S → 草稿已儲存 → 正常關閉，exit 0 | package-reopened-saved.jpg、v1-package-launch.json |
| 封存來源的公開工作流程，受控 TTS 與真實本機 FFmpeg | 兩份 3 秒音訊＋500 ms 交接 → 6.5 秒 MP3／MP4；完整解碼；H.264／AAC；另存成功 | media.json、synthetic.mp3、synthetic.mp4、synthetic.srt |

隔離 APP_HOME、VOICE_HOME、KOKORO_HOME、OCR_HOME、LOCALAPPDATA 與 APPDATA。未讀使用者書籍／金鑰，未新增付費／線上語音請求。音調替身驗證工作流程與媒體格式，不代表真實人聲聽感。EXE 沒有依賴開發目錄或系統 Python PATH；不是全新 Windows 安裝驗收。

第一輪沙箱測試背景等待超時；該自建程序已確認命令後停止。兩次匯出夾設定不合契約，修正驗證腳本後成功。未修改 v1 產品修飾失敗。最後來源、EXE 及媒體程序皆已退出，沒有製作鎖；測試臨時資料由本輪清理，最終雜湊與資源證據在 archive-verification.json 及 cleanup.json。

封存已完成，可開始 v2 產品程式開發。v2 交付後再重算所有雜湊並啟動 v1。未建立 Git 標籤；完整磁碟副本及清單為還原依據。
