# 多 TTS 服務整合評估

2026-10-29。僅評估與文件記錄；未修改程式、未呼叫付費合成、未讀取金鑰。此處 Google TTS 指 Google Cloud Text-to-Speech；Google Translate/gTTS、Gemini TTS 是另外的整合範圍。

## 2026-10-29 修訂：優先採 Gemini Developer API＋API key

使用者提供 https://ai.google.dev/gemini-api/docs/speech-generation?hl=zh-tw#single-speaker，確認本案要採和一般Gemini模型類似的API key存取方式。官方此頁明列gemini-3.8-flash-tts及gemini-3.8-flash-lite-tts，REST示例使用generativelanguage.googleapis.com/v1beta/interactions與x-goog-api-key。因此**本案Google TTS的優先路線改為Gemini Developer API，不要求使用者設定Cloud專案、區域、ADC或服務帳戶**。先前「傳統Cloud TTS不支援」是特定端點的區別，不代表兩模型不能直接用Gemini API key，也不應因此強迫走企業入口。

擬定主畫面服務名為「Google Gemini TTS」，設定視窗以顯示名稱及API key為主，可明確選擇沿用既有Gemini校對金鑰或另外設定；是否可呼叫該模型、帳務與配額以實際帳號驗證，不假設一把可校對的key必然有所有TTS權限。Cloud／Enterprise路線保留為未來進階選項，非初次使用必要步驟。

主畫面順序保留：服務 → 模型（可下拉或直接輸入）→ 音色與節奏 → 編輯試聽文字 → 產生並播放 → 儲存／製作。預置兩個3.8 ID，允許同協定新模型手填；測試失敗不暗換模型。可選風格說明另欄輸入，與要逐字朗讀的正文分開。

接入認證比Cloud路線簡單；但「同樣以API存取」不表示請求與LLM校對完全相同：TTS需要音訊輸出設定、音色設定及音訊解碼。官方單次回應可輸出WAV，仍可接現有PCM停頓、實測字幕與MP3輸出。這是評估修訂，尚未付費試呼叫、未修改程式或圖面。下方較早的Cloud優先敘述屬前次方案，以上方本段為準。

## 2026-10-29 追加：Gemini 3.8 TTS 與可編輯模型選單

使用者指定將 `gemini-3.8-flash-lite-tts`、`gemini-3.8-flash-tts` 納入評估；模型欄必須同時能下拉選擇與直接輸入，支援未來同協定的新模型。此項更新先前「Gemini TTS 另列範圍」的評估範圍，尚未授權實作。

兩個ID皆有官方模型文件，且官方明示兩者共用請求schema／prompt格式。Flash偏有聲書、敘事與聲音表現；Flash-Lite偏大量處理、效率與成本。此為官方定位，非本專案的真實聽感或費用測量。[Flash](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-8-flash-tts)、[Flash-Lite](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-8-flash-lite-tts)

**入口必須區分。** Cloud Text-to-Speech官方Gemini頁註明3.8不能使用傳統Cloud Text-to-Speech API。Cloud/Enterprise提供GenerateContent入口，Gemini Developer另有自己的API key／Interactions入口，兩者不可共用同一請求schema或混用憑證。使用者若選Cloud帳戶，本案採Cloud Gemini TTS adapter；DeveloperAPI可另設設定檔類型。[Cloud TTS註記](https://docs.cloud.google.com/text-to-speech/docs/gemini-tts)、[Developer TTS](https://ai.google.dev/gemini-api/docs/speech-generation)

### 擬定 UI

主畫面第一區依由上而下操作：

1. 服務設定檔：Google Gemini TTS｜我的Cloud帳戶。
2. 模型（可選擇或直接輸入）：預置兩個完整ID；同一個可編輯下拉框，不另外要求先選「其他」才能打字。
3. 模型狀態：未測試／測試成功／不可用；小字說明「新模型可直接輸入ID，先以短文試聽確認」。
4. 再往右第二區選音色與節奏；第三區編輯文字並試聽；下方儲存並前往製作。

服務管理窗處理Cloud專案、區域與憑證；不把認證欄擠進日常主畫面。可保存預設模型，但主畫面可覆選，本批設定與正式工作快照保存實際使用的完整ID。傳統Google Cloud TTS與Google Gemini TTS採不同連線類型，避免使用者把3.8ID輸入不支援的入口卻只得到模糊錯誤。

### 行為規則

- 預置清單只是建議，不是模型白名單；未知ID不因未列入清單而拒絕。清除前後空白、檢查空值與不合法控制字元；不可悄悄改寫模型名稱或換成舊模型。
- 不要求新模型必須符合硬編碼的3.8版本格式；新ID若沿用已支援入口、請求與音訊回應協定，應可直接使用。未來協定、認證、能力或回應格式改變時，仍需更新adapter，不能承諾所有未來模型零更新。
- 模型清單更新若供應商支援可靠的列舉可使用；無列舉或清單過時仍允許手填。不能把所有通用Gemini模型都列成TTS模型。
- 成功使用過的自填ID可保存在該服務設定檔的最近使用清單，不污染其他API入口；刪除預置選項不會抹除已保存的自訂值。
- 輸入／選擇本身不連網、不合成、不計費測試。按「產生並播放試聽」才作真正能力驗證；顯示可能費用，不宣稱只查到模型名稱就代表能合成。
- 切換模型後刷新／重新驗證音色、語速及風格能力，將上次試聽明示為舊設定。若不支援既有音色就提示重選，不能默默換聲或忽略語速。
- 模型不存在、無權限、區域不支援、未啟用帳務與限流分別提示；保留使用者輸入及上次成功成品，不能把全部錯誤都當作ID拼錯。
- 原音快取加入實際API入口、模型ID、音色與生成設定。換模型重新合成並重建字幕時間；本機額外句尾／段落靜音規則沿用T11。
- Gemini TTS的風格提示與要朗讀的逐字稿分開，不將指示文字當稿件送讀；語速與風格不能保證和Edge的百分比參數等價，須依模型能力實測。

### 驗收方向（尚未執行）

下拉選Lite → 選音色 → 編輯短文 → 試聽 → 切到Flash → 再試聽 → 保存／重開核對模型。直接輸入一個有權限且同協定的新ID → 試聽成功 → 重開時保留在最近使用。另測無效ID、無權限、區域錯誤與429，確認提示正確且不自動換模型。核對換模型不誤用原音、字幕依新音訊重建、未改校對稿與金鑰不進專案。

[官方入口與模型詳細核對](gemini-tts-model-selection-sources.md)。本次只更新評估文字；既有兩張UI圖片仍是v1，尚未繪入可編輯模型欄，不可視為最新需求的完整圖面。

## 結論

可以在統一流程下接入 Edge、Fish Audio、Google Cloud TTS。使用者操作流程能保留，UI 屬小幅至中幅增補，後端屬中型改造。建議先支援「已知協定的服務設定檔」，再支援相容端點；任意未知服務只填網址與金鑰就能通用，目前不可承諾。

本次截圖僅能證明三次嘗試後失敗，不能判定網路、服務拒絕或音色有問題。現有 voice_media.speech_block 把 OSError、Timeout、ClientError、EdgeTTSException 合成同一錯誤；voice.VoiceJob 也有通用錯誤。應先補不含金鑰或書稿的 HTTP狀態、服務錯誤碼、request ID與重試分類，避免把所有失敗都引導成「更新音色」。edge-tts 是第三方專案對 Microsoft Edge 線上語音服務的存取，不能將它等同正式 Azure Speech API。[專案說明](https://github.com/rany2/edge-tts)

## UI 與流程影響

| 區域 | 改動 | 規模 |
|---|---|---|
| 語音設定與試聽 | 加「TTS服務設定檔」與「管理服務」；必要時顯示模型；音色清單隨服務切換 | 小至中 |
| 新增服務管理窗 | 新增／編輯／移除設定檔、憑證、連線檢查、音色列表或手填音色ID、測試語音 | 中 |
| 批次MP3／SRT窗 | 顯示本次服務、模型、音色、計費提示與傳送目的地；失敗訊息改依服務顯示 | 小 |
| 語速／節奏 | 保留共同控制，依模型能力限制或停用不支援項目；不能默默忽略 | 小至中 |
| 原文／OCR／校對 | 不需改使用流程 | 無直接改動 |
| 合成／保存／快取 | 抽出服務實作、設定格式遷移、能力與限制、錯誤分類、快取識別 | 中，主要工作量 |

建議操作：

設定 → TTS服務 → 新增設定檔 → 選服務類型 → 填憑證 → 檢查連線／音色 → 儲存。

語音試聽 → 選服務設定檔 → 選模型／音色 → 編輯短文 → 產生並播放 → 滿意後儲存本批設定 → 批次MP3／SRT。

「檢查連線」與「產生測試語音」分開，後者須顯示可能計費。換服務不自動送稿。不要沿用寫死 Microsoft 的同意文案；依本次快照顯示實際服務及目的地。

## 服務差異

**Fish Audio 雲端**：Bearer API key、模型與 reference_id 音色ID，TTS可用JSON請求並回音訊；可沿用現有FFmpeg解碼與組裝。API有MP3／WAV／PCM等格式與prosody控制。模型須明確選擇及驗證，官方文件指出未知模型名稱可能回退到預設模型，程式不應把這當成成功套用原選項。[官方TTS](https://docs.fish.audio/api-reference/endpoint/openapi-v1/text-to-speech)

Fish的 chunk_length 是內部分塊參數，不能解讀成單次請求文字上限。整段可接受長度及實際完整性必須另外驗證。官方目前依UTF-8 bytes計費，不能用中文字元數直接當成本。[計價與限流](https://docs.fish.audio/developer-guide/models-pricing/pricing-and-rate-limits)

**Google Cloud TTS**：有正式音色列舉、同步合成與MP3／LINEAR16等輸出，現有音色選擇和FFmpeg流程可接。設定需處理Cloud專案與憑證／ADC，不應把既有Gemini API key當可直接使用的TTS憑證。[認證](https://docs.cloud.google.com/text-to-speech/docs/authentication)、[音色列舉](https://docs.cloud.google.com/text-to-speech/docs/reference/rest/v1/voices/list)、[合成](https://docs.cloud.google.com/text-to-speech/docs/reference/rest/v1/text/synthesize)

Google一般請求內容上限為5000 bytes；不同模型能力不同，不能沿用Edge的XML escaped bytes作為所有服務的共同計數方式。[限制](https://docs.cloud.google.com/text-to-speech/quotas)

Chirp3專頁目前列出Preview語速與同步SSML功能，和總覽的舊限制說明不同；實作須依模型及端點核對。其markup停頓非固定毫秒，不能直接替代T11要求的精確額外停頓。台灣華語需核對實際音色，不能把所有中文模型都當台灣口音。[Chirp3專頁](https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd)、[語言／音色](https://docs.cloud.google.com/text-to-speech/docs/list-voices-and-types)

兩者語音自然度、台灣口音、中英混讀與長稿穩定性，本次沒有實測，不能據文件排名。詳細服務核對見 [來源研究](tts-provider-evaluation-sources.md)。

## 可共用的實作

將「列音色／描述能力／合成一塊」放在服務可替換的 seam，各服務提供 adapter。共用層繼續負責：文字快照、安全切分、取消、進度、PCM解碼、精確額外靜音、實測字幕、原子發布及失敗保護。不要把每個服務的條件分支散落到試聽與正式合成兩條流程。

本機修改面：

- voice.py：provider白名單、設定驗證、單一全域音色快取須改為各服務設定檔獨立；舊設定遷移為Edge。
- voice_media.py：Edge直接呼叫與例外分類抽成adapter；共用解碼／組裝保留。
- narration.py：3000 escaped UTF-8 bytes、重試與時間限制改由adapter能力提供；保留安全句界策略。先採共同逐塊合成，不必第一階段引入供應商長音訊工作、Cloud Storage或即時文字串流。
- workflow.py：現有試聽／正式入口保留，增加服務快照及憑證參照；不讓呼叫者各寫一套合成流程。
- voice_desktop.py／narration_desktop.py：服務選擇、模型能力、動態目的地與可行動錯誤。
- 設定與舊成品：現有settings()對欄位集合嚴格比對；新增欄位須有版本／遷移及舊試聽／成品讀取測試，不能直接破壞既有專案。

原音快取識別加入服務類型、設定檔命名空間、端點、模型／版本、音色、語速、實際送出文字與處理規則；不加入明文金鑰。換服務或模型不能誤用舊聲音，單改本機停頓仍可重用原音。不同服務的聲音與時長不能視為相同，字幕須以新音訊重建。

憑證放本機使用者設定，專案只存非秘密的設定檔參照及可重現合成設定。可抽出既有Gemini的Windows DPAPI保護能力作共用憑證模組；Google憑證依官方認證模式處理，不能把服務帳戶私鑰拷入書籍專案。專案搬到別台時提示重新連結憑證，不暗換服務或音色。

## 使用者自行新增的範圍

1. **第一階段，建議**：已支援的Edge／Fish／Google，使用者自行新增多個設定檔。可改名稱、帳號／憑證、模型及音色；不需寫程式。
2. **第二階段，可行**：提供「相容TTS API」類型，使用者填Base URL、API key、模型、音色；只支援明確定義且通過相容測試的協定。可以接部分代理與自架服務，不代表所有供應商。
3. **第三階段，暫緩**：任意HTTP模板、回應欄位抽取、動態簽章、OAuth更新、非同步輪詢或插件。這已是一個連接器平台，工作量與故障面顯著增加，不能靠一張通用表單完成所有服務。

不建議在一批稿內遇錯就自動切服務：會改音色、成本、傳送對象與時長。第一階段以明確提示使用者換服務、另開任務為宜。若未來加入備援，須先設定允許的服務／音色映射、付費規則與切換範圍；整批重做或混用必須在成品可辨識。

## 建議拆票與驗收

A. 統一服務設定與adapter、舊專案遷移、錯誤分類與安全憑證；保留Edge行為。
B. 接Fish，驗證可編輯試聽與完整MP3／SRT；只換服務，不重寫來源／校對流程。
C. 接Google Cloud TTS，補專案／認證與模型能力。
D. 相容端點與使用者自訂設定檔測試；最後再考慮任意插件。

若主要需求是生產可用性，A/B/C應包含重試政策：認證／設定／額度問題直接給修復指引；429遵循Retry-After及退避；可重試的暫時網路／5xx有界重試。付費請求逾時可能已被服務處理，不宣稱取消一定免計費。跨次只重試失敗區塊及續作仍需和T12協同實作；不因T11已有原音快取就宣稱T12完成。

驗收：新增設定檔 → 檢查憑證 → 列音色或手填ID → 三語短稿試聽 → 正式兩段稿MP3／SRT → 核對實測時長、字幕空白與偏移 → 只改停頓確認不重送語音 → 換服務確認原音不混用 → 模擬401／403／額度／429／5xx／逾時 → 檢查訊息與重試策略 → 關閉／取消後核對資源 → 重開舊專案及舊成品。

以上是結構與改動規模評估，不是已完成整合或穩定度保證；本次只新增評估文件，無測試／建置暫存與背景測試程序。
