# Gemini TTS 模型選擇：官方來源核對

查核日期：2026-10-29。僅公開文件研究；未修改程式、未呼叫合成、未讀取金鑰，沒有產生測試暫存。

## 已確認的模型與定位

- `gemini-3.8-flash-tts` 與 `gemini-3.8-flash-lite-tts` 都有官方模型頁。兩者共用請求 schema 與 prompting 格式，可在同一支援入口以模型 ID 切換。Flash 偏有聲書、聲音細節與表演；Lite 偏大量生成、延遲與成本效率。此為官方產品定位，未替本專案做聽感或成本實測。[Flash 模型頁](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-8-flash-tts)、[Lite 模型頁](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-8-flash-lite-tts)
- 發布狀態文件存在落差：Cloud TTS 總覽仍把兩者稱 Preview；Flash 專頁（最後更新 2026-10-28）列 GA，Lite 專頁列 Preview。介面不宜把兩者永久硬標成同一狀態；實作時應依選定入口及模型專頁核對。[Cloud TTS 總覽](https://docs.cloud.google.com/text-to-speech/docs/gemini-tts)、[Flash 模型頁](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-8-flash-tts)、[Lite 模型頁](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-8-flash-lite-tts)

## 三種入口必須區分

| 入口 | 官方資訊 | 對介面／實作的影響 |
|---|---|---|
| Cloud Text-to-Speech API | 總覽明示 3.8 這兩模型不透過 Cloud Text-to-Speech API 提供。不能只把 ID 填入既有 `text:synthesize` 請求就認為可用。[官方總覽](https://docs.cloud.google.com/text-to-speech/docs/gemini-tts) | 傳統 Cloud TTS 與 Gemini TTS 需區分；不可只以模型名稱決定認證與請求格式。 |
| Google Cloud／Gemini Enterprise | 官方示例為 `aiplatform.googleapis.com/v1/projects/.../locations/.../publishers/google/models/...:generateContent`；使用 Bearer token、Cloud 專案與位置，內容／聲音設定透過 GenerateContent schema。[官方模型與REST範例](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-8-flash-tts) | 建議服務類型標示「Google Cloud／Gemini TTS」，保存入口類型、project、location、模型ID與音色；憑證另存本機。 |
| Gemini Developer API | 官方 speech-generation 文件也明確列兩個 3.8 模型，示例為 `generativelanguage.googleapis.com/v1beta/interactions`，`x-goog-api-key` 認證，使用 Interactions schema。[官方生成指南](https://ai.google.dev/gemini-api/docs/speech-generation) | 若要支援 AI Studio/Gemini API key，應作為另一個連線方式／adapter；不能把 Developer API key 表單直接套入 Cloud 的 Bearer 認證流程。 |

Cloud 總覽的「Enterprise API only」應在該 Cloud TTS 文件脈絡閱讀，不能用來推論兩模型完全不存在於 Developer API；Developer 官方頁提供了自己的入口與示例。兩種入口可提供同一模型，但其認證與請求 schema 不因此變成通用。

## 對「下拉選擇＋自行輸入」的設計推論

1. 模型使用可編輯的下拉欄，預填兩個已知 ID；清單用於建議，不是允許模型白名單。
2. 同時保留服務／API入口選擇；模型欄不能取代入口設定。先選入口，再選或輸入模型，再選音色及試聽。
3. 手填模型允許未收錄的新 ID，做基本字串檢查即可；再透過所選入口及帳戶檢查可用性，不能宣稱新 ID 一定可用。
4. 驗證成功只表示此入口、帳戶、地區與請求格式可工作；若只有填寫或列舉成功，狀態要標「尚未試聽」。真正產生測試語音可能計費，應由使用者按試聽觸發。
5. 新模型沿用目前支援協定、音訊格式及設定時，通常可直接填新 ID；若改入口、認證或 schema，仍需要程式更新。不得因模型 ID 合法就自動降回其他模型。
6. 快照、原音快取及成品記錄保存完整模型 ID與入口，避免更換模型後誤用舊聲音；切換模型後應重新確認音色與能力。


## 2026-10-29 修訂：優先採 Gemini Developer API＋API key

使用者提供 https://ai.google.dev/gemini-api/docs/speech-generation?hl=zh-tw#single-speaker，確認本案要採和一般Gemini模型類似的API key存取方式。官方此頁明列gemini-3.8-flash-tts及gemini-3.8-flash-lite-tts，REST示例使用generativelanguage.googleapis.com/v1beta/interactions與x-goog-api-key。因此**本案Google TTS的優先路線改為Gemini Developer API，不要求使用者設定Cloud專案、區域、ADC或服務帳戶**。先前「傳統Cloud TTS不支援」是特定端點的區別，不代表兩模型不能直接用Gemini API key，也不應因此強迫走企業入口。

擬定主畫面服務名為「Google Gemini TTS」，設定視窗以顯示名稱及API key為主，可明確選擇沿用既有Gemini校對金鑰或另外設定；是否可呼叫該模型、帳務與配額以實際帳號驗證，不假設一把可校對的key必然有所有TTS權限。Cloud／Enterprise路線保留為未來進階選項，非初次使用必要步驟。

主畫面順序保留：服務 → 模型（可下拉或直接輸入）→ 音色與節奏 → 編輯試聽文字 → 產生並播放 → 儲存／製作。預置兩個3.8 ID，允許同協定新模型手填；測試失敗不暗換模型。可選風格說明另欄輸入，與要逐字朗讀的正文分開。

接入認證比Cloud路線簡單；但「同樣以API存取」不表示請求與LLM校對完全相同：TTS需要音訊輸出設定、音色設定及音訊解碼。官方單次回應可輸出WAV，仍可接現有PCM停頓、實測字幕與MP3輸出。這是評估修訂，尚未付費試呼叫、未修改程式或圖面。下方較早的Cloud優先敘述屬前次方案，以上方本段為準。

