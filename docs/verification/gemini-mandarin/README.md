# Gemini 普通話朗讀設定

2026-11-05。更新 `dist/ebook2mp4/ebook2mp4.exe`。

每個 Gemini 合成請求的 speech_config 加入 language=cmn-CN；speech_metadata.style 明確要求所有中文（包含繁體、引文及對話）使用標準普通話。保留原稿逐字朗讀與原有語速；原稿英文按原文朗讀後接回普通話。設定不加入朗讀正文，不改寫校對稿或字幕。

Gemini 原音快取加入語言與 mandarin-verbatim-v1 策略識別。製作時不再將先前語言未限定的區塊視為有效新快取；既有正式成品保留。其他服務的快取不受這項識別變更影響。

官方參考：[Interactions API](https://ai.google.dev/api/interactions-api) 的 SpeechConfig.language 與 SpeechAnnotation.style；[語音生成指南](https://ai.google.dev/gemini-api/docs/speech-generation) 的逐段語音風格設定；[語言代碼說明](https://firebase.google.com/docs/ai-logic/generate-speech) 列出 Mandarin 的 cmn-CN。各入口能力可能不同；本次沒有使用真實金鑰驗證語言欄位或做聽感測試。

providers.txt：6 項通過，包含語言欄位、普通話指示、原文不變、Gemini 快取策略隔離及其他服務行為。recovery.txt：6 項通過，包含真實本機限速器與模擬 HTTP 的 36 塊恢復流程。合計 12 項。模擬請求通過不代表已證明遠端一定接受參數或完全避免語言偏移。

另有 resume.txt 的 6 項重開專案、快取損壞、取消與續作回歸通過，合計 18 項通過。build.txt 記錄封裝。package.json 記錄成品雜湊與正常啟閉（退出碼 0）。cleanup.json 記錄暫存與程序清理。

使用：關閉舊程式 → 開啟新版 → 選 Gemini 服務 → 產生新試聽 → 確認中文發音。新製作與未完成任務續作會套用新設定；既有 MP3 檔不會自動改寫。生成式 TTS 仍需要聽感驗收，沒有零語言偏移保證。
