# TTS 服務接入：官方資料核對

查核日期：2026-10-29。僅查公開文件，沒有呼叫付費合成、讀取金鑰、安裝套件或改程式。以下分開記錄服務事實與整合建議；尚未驗證實際中文聽感、穩定度或帳戶配額。

## Fish Audio 雲端 API

| 項目 | 官方資料及接入影響 |
|---|---|
| 認證與請求 | `POST https://api.fish.audio/v1/tts`，Bearer API key；模型放在 `model` header，音色用 `reference_id`。支援 JSON；直接送參考音訊的做法須用 MessagePack。初版可用既有音色 ID，無須加入聲音複製流程。[TTS endpoint](https://docs.fish.audio/api-reference/endpoint/openapi-v1/text-to-speech) |
| 音色列舉 | `GET /model` 回傳 `_id`、標題、語言等資料及分頁資訊。這裡的 voice model ID 與 TTS 引擎模型 header 是兩個不同概念。[List Models](https://docs.fish.audio/api-reference/endpoint/model/list-models) |
| 速度與音訊 | `prosody.speed` 為倍率，官方 schema 說明範圍 0.5～2.0；可回 WAV、PCM、MP3、Opus。音訊須依格式辨識容器／取樣率後再統一解碼。[OpenAPI：ProsodyControl／TTSRequest](https://docs.fish.audio/api-reference/openapi.json) |
| 文字長度 | 查到的 TTSRequest `text` schema 沒有公開 `maxLength`，不能推定無上限。`chunk_length` 100～300 是服務內部文字切塊參數，不是整個請求的字數上限。正式接入仍須訂保守請求上限，並驗證模型實際行為。[TTS endpoint](https://docs.fish.audio/api-reference/endpoint/openapi-v1/text-to-speech) |
| 費用與配額 | 目前 TTS 按輸入 **UTF-8 bytes** 計費；`s2.1-pro` 為 US$15／百萬 bytes、`s2.1-pro-free` 為 US$0。中文與英文不能用相同字數直接比較費用。併發額度依帳戶級別；Starter 表列 5。不據此估整本書成本。[Pricing & Rate Limits](https://docs.fish.audio/developer-guide/models-pricing/pricing-and-rate-limits) |
| 模型選擇 | endpoint 文件表示 header 缺少或未知時會退回 `s2.1-pro`；因此 UI 應明確保存模型，拒絕未知值，不能把免費選項拼錯後交由遠端預設。免費模型缺少部分服務保證，不能視為穩定性承諾。[TTS endpoint](https://docs.fish.audio/api-reference/endpoint/openapi-v1/text-to-speech)、[Overview](https://docs.fish.audio/overview/capabilities) |
| 錯誤 | 400 參數／音色、401 金鑰、402 額度、403 權限、404 模型／音色，應提示修正；429／5xx 才依退避策略重試。錯誤不一定是 JSON。[Errors](https://docs.fish.audio/api-reference/errors) |

這些是 `api.fish.audio` 雲端服務的契約，沒有拿 `speech.fish.audio` 自架伺服器的權重、部署方式或參數行為代替雲端契約。

## Google Cloud Text-to-Speech

| 項目 | 官方資料及接入影響 |
|---|---|
| 啟用與認證 | 需 Google Cloud 專案、啟用服務與計費；官方 client library 使用 ADC，REST 也有對應認證方式。初版應選定一種桌面憑證流程，不能假設所有服務只貼同樣的 API key 就能用。[Get started](https://docs.cloud.google.com/text-to-speech/docs/get-started)、[Authentication](https://docs.cloud.google.com/text-to-speech/docs/authentication) |
| 音色清單 | `GET /v1/voices` 可依語言查詢，回傳唯一 voice name、語言、性別、自然取樣率。可以映射至既有音色清單。[voices.list](https://docs.cloud.google.com/text-to-speech/docs/reference/rest/v1/voices/list) |
| 長度與配額 | 一般合成內容限制 5,000 bytes／請求，不是 5,000 中文字；依模型有不同每分鐘額度。長音訊另有流程，初版可沿用本機分段，無須引入 Cloud Storage 長音訊任務。[Quotas & limits](https://docs.cloud.google.com/text-to-speech/quotas) |
| 輸出 | 一般合成可以取得 MP3／LINEAR16 等格式；Chirp 3 HD 的串流與非串流支援格式不同。初版可固定非串流回應，沿用本機量測、PCM 靜音及 SRT。[Basics](https://docs.cloud.google.com/text-to-speech/docs/basics)、[Chirp 3 HD](https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd) |
| 速度／SSML | 通用 `AudioConfig.speakingRate` 範圍 0.25～2.0。最新 Chirp 3 HD 專頁也列出 pace control，並標為 Preview；SSML 支援同樣標為 Preview，僅同步請求，串流不支援。**總覽頁仍有舊的「不支援」敘述，與專頁有落差**；接入須以所選模型、端點與實測能力為準。[AudioConfig](https://docs.cloud.google.com/text-to-speech/docs/reference/rest/v1/AudioConfig)、[Chirp 3 HD](https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd)、[總覽](https://docs.cloud.google.com/text-to-speech/docs/list-voices-and-types) |
| 停頓 | Chirp 3 HD 的 markup pause tags 並不保證精確時長，模型也可能忽略。現有「額外 200／800 ms」應維持本機實際插入靜音，不改成模型自由停頓。[Chirp 3 HD](https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd) |
| 費用 | Standard、WaveNet、Neural2、Chirp 3 HD 等按字元計費，費率及免費量依模型不同；Gemini-TTS 另按輸入／輸出 tokens 計費。本次評估的一般 Cloud TTS 不能與 Gemini-TTS 混成同一設定。須顯示所選模型及計價單位。[Pricing](https://cloud.google.com/text-to-speech/pricing) |

## 建議給共用流程的要求（設計推論）

1. 共用「選服務設定→選音色→編輯短稿→試聽→正式合成」，服務差異收在 adapter；初版分別提供 Fish 與 Google 設定表單。
2. 服務設定保存名稱、provider、模型、端點與憑證參照；製作快照和原音快取須包含會改變聲音的設定。憑證本身不放進可攜專案、成品或錯誤記錄。
3. 能力描述應包含語速範圍、請求大小計量方式、音色列舉、輸出格式。無法支援的控制項停用並說明，不暗中忽略。
4. 費用估算區分 Fish bytes 與 Google 字元；試聽及重試也可能產生服務用量，不能只算最終成品。
5. 不自動跨服務換聲重試。換服務須讓使用者明選並重新試聽；不同聲音混入書稿會破壞一致性。
6. 使用者可自行新增「已支援服務」的多組設定。未知協定的服務不能只填 URL／金鑰便自動相容；需另做 adapter，或日後明確支援有限的相容協定模板。
