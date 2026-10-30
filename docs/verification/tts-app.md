# 多 TTS 服務更新

2026-10-29。依模擬圖與Gemini Developer API修訂需求實作。本次未提交／推送，保留其他未提交工作。

## 成品與操作

新版 `dist/TTS/ebook2mp4/ebook2mp4.exe`；請搬移整個資料夾。SHA-256見 [封裝來源比對](tts-app-package-source.json)。

語音窗預設最大化，最小1100×740，左到右：1選服務與模型 → 2選音色／語速／停頓 → 3編輯文字與試聽，下方4儲存並前往製作。沿用原生Tk米白／深綠樣式；三欄按父層grid伸展，明確的下方操作區避免原本入口散落。其他DPI與小螢幕待人工確認。[主窗畫面](images/tts-app/workflow.jpg)、[服務表單](images/tts-app/service.jpg)。表單證據攝於服務類型改用友善名稱前，最後版本顯示Google Gemini TTS／Fish Audio。

支援Edge、Google Gemini TTS與Fish Audio原生API。Google模型可下拉選兩個3.8模型或直接填新ID，同協定新模型不以清單白名單拒絕；Edge無模型欄、Fish目前只允許s2.1-pro／s2.1-pro-free，避免未知模型被服務回退到付費預設。服務設定可新增／編輯，提供不產生語音的憑證／音色端點檢查；模型能力仍須短文試聽驗證。預置Gemini音色為6個候選，亦可自行輸入官方音色ID；Fish需自行填reference_id。尚未提供完整遠端音色瀏覽、任意相容API、自訂端點、設定檔刪除及模型歷史清單，不宣稱模擬圖所有進階規劃均已完成。

Google採generativelanguage.googleapis.com/v1beta/interactions、API key與音訊回應解碼，不需Cloud專案／區域／ADC；可明確勾選沿用本機Gemini校對金鑰。Fish採api.fish.audio/v1/tts、Bearer key與model header。金鑰以Windows DPAPI存於本機voice資料夾services.json，不進書籍專案。既有設定檔不可跨服務換類型，須新增並另填金鑰，避免向另一家傳原服務金鑰。搬機缺設定檔時阻擋，不默默換Edge。

試聽使用畫面設定，不暗存批次語音設定、不改校對稿；按只儲存才保存。儲存並前往製作先檢查已確認稿，未確認會顯示原因。正式窗顯示服務／模型／音色。語音快取加入provider／profile／model，換模型不誤用舊音，單改本機停頓可重用。既有Edge專案與成功成品仍可讀。Gemini語速透過風格指示，不宣稱與Edge百分比精確等價；T11額外停頓繼續用PCM實際靜音與實測字幕。

HTTP401/403/402/404與請求錯誤提示修復，不自動換模型／音色；429/5xx與暫時網路錯誤最多3次有界重試，尊重Retry-After，要求超過60秒則提示稍後重試。取消等待連線與FFmpeg釋放，失敗保留上次成功成品。

## 驗證

[20項既有語音／正式／桌面回歸](tts-app-regression.txt)、[31項專案／節奏相容](tts-app-workflow-tests.txt)、[5項新增服務及Tk](tts-app-providers.txt)通過；[20來源型別檢查](tts-app-typecheck.txt)通過。[審查修正回歸](tts-app-review-tests.txt)。未重跑與本次無關的全套OCR／PDF測試；不能稱全部測試套件通過。

新增測試在公開ProjectWorkflow與真實Tk操作，外部HTTP以替身控制、組裝／解碼使用真實FFmpeg：Gemini未知模型ID實際進JSON、試聽及正式原音重用、專案重開／金鑰不入專案、Fish請求與401不重試且保留成品、服務類型不可跨換金鑰、Fish未知模型拒絕、Edge→Gemini→Edge模型啟用狀態、分包音色JSON檢查。沒有使用使用者金鑰或呼叫付費API；真實Gemini與Fish帳號、額度、模型權限、發音與長篇穩定性仍待使用者驗收。Edge既有流程回歸不能替代兩家真實服務驗收。

程式審查發現跨服務沿用金鑰、Fish未知模型回退、限流未重試、缺服務檢查、Edge模型誤導、分包JSON與表單重疊；均已修正，原審查者複查解除。本次視覺以原生computer-use檢視，不用瀏覽器。無多DPI／乾淨機驗證。

## 人工驗收（短句與單步結果）

1. 開啟新版 → 選批次 → 按語音試聽 → 檢查三欄及下方操作列。
2. 按新增／管理服務 → 選Google Gemini TTS → 填名稱與API key，或明確勾選沿用校對金鑰 → 按檢查連線與音色 → 核對結果 → 儲存並返回。
3. 下拉選gemini-3.8-flash-lite-tts → 選Kore等音色 → 編輯短文 → 按產生並播放試聽 → 確認語音內容 → 停止。
4. 換gemini-3.8-flash-tts → 再試聽 → 比較品質。手填可用的新模型ID → 試聽 → 確認無自動替換。
5. 按只儲存設定 → 重開專案 → 檢查服務／模型／音色保留。
6. 確認朗讀稿 → 儲存並前往製作 → 核對服務／模型 → 產生MP3／SRT → 播放並檢查字幕在新增停頓期間清空、後段無累積偏移。
7. 新增Fish服務 → 填該服務金鑰 → 選已支援模型 → 手填音色reference_id → 重做短文試聽與正式輸出。
8. 撤除同意勾選 → 按試聽 → 確認不送出。輸入無效模型／錯誤金鑰 → 確認提示及上次結果保留。

[清理證據](tts-app-cleanup.json)：保留正式成品、需求及驗證紀錄，移除本次測試／依賴／建置與快取。真實服務測試請只先用合成短文，不以可播放取代人工品質檢查。若繼續T12，建議開新session。

最終成品SHA-256：`14C10F005FB974490B2C13211645C578BB57DCEC739F372540B80413137ACD3E`。最終來源逐模組重跑 [8模組56項相關測試](tts-app-final-suite.txt)，全部通過；見[摘要](tts-app-final-summary.json)。包內7個修改模組與最終來源位元碼／常數一致，成品啟動與正常退出通過。未執行封裝內真實付費合成；真實帳號驗收待使用者。
