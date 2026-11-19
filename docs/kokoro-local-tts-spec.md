# Kokoro 官方中文版本機 CPU 語音整合規格

> 2026-11-13盤點：OPEN。已有部分實作，原文「尚未」為立案時背景；完整CPU／無快取離線／品質／乾淨環境與聽感確認證據不足，不能整張結案。UI設計及外框整合改依[新spec](v2-unified-shell-spec.md)；Kokoro功能、品質及生命週期契約保留，見[盤點](tickets/2026-11-13-tracking-audit.md)。

日期：2026-11-04。需求與主要測試接點已確認；先完成可行性驗證，再依結果確認正式整合範圍。UI 版面須另提供設計圖確認後實作。本規格不代表已完成模型下載、合成測試或封裝驗收。

## Problem Statement

使用者需要在 Windows 桌面程式內，以官方開源的 Kokoro 中文版將已確認的朗讀稿製作成音訊、字幕及影片。朗讀必須限定 CPU，安裝完成後可離線使用，不需要雲端帳號、API key、終端機或手動啟動服務。

目前語音流程使用線上服務，設定、傳送同意、錯誤分類、切分及限時均有雲端服務的假設。直接加入同步模型推論，可能使取消無法結束工作，或在主程式關閉後留下程序及記憶體。官方套件目前宣告的 Python 版本範圍也不包含主程式使用的 3.14.3，需要避免將相容性成本直接轉成整個 Kokoro 的重寫工作。

使用者還需要知道繁體書稿的實際發音品質、CPU 製作速度、記憶體需求及語音包大小，才能判斷是否值得正式整合。能產生可播放音檔，並不足以證明中英夾讀或長篇朗讀可用。

## Solution

增加選配的 Kokoro 本機語音包。主程式保持 Python 3.14.3；語音包包含獨立 Python 3.12 執行環境、CPU 推論依賴、官方中文版模型、官方中文音色及完整前處理資源。主程式負責安裝檢查、啟動、工作進度、取消、閒置卸載與關閉清理。

使用者在主程式匯入已下載的離線語音包，檢查通過後，在現有語音流程選擇 Kokoro、音色及語速。先試聽，再以已確認朗讀稿製作批次 MP3／SRT，後續沿用總音訊與影片流程。合成失敗時顯示原因，由使用者重試或明確切換服務，不自動改用雲端。

工作分兩階段。第一階段以官方實作完成真實 CPU、完整離線啟動、中文品質及資源生命週期驗證，交付音檔與量測證據。依結果確認正式整合範圍後，第二階段完成語音包與桌面流程；UI 調整須先取得設計圖確認。不預先承諾 CPU 倍速、包體大小或台灣口音品質。

## User Stories

1. As a Windows user, I want Kokoro available inside the existing desktop application, so that I can narrate books without switching tools.
2. As a user, I want the official Chinese Kokoro model and voices, so that the source of the narration engine is identifiable.
3. As an offline user, I want synthesis restricted to the CPU, so that I do not need a GPU or its drivers.
4. As an offline user, I want the installed voice package to contain every required runtime and language resource, so that the first synthesis works without internet access.
5. As a Windows user, I want Python and inference dependencies included in the voice package, so that I do not need to install or configure Python.
6. As a user, I want to import a downloaded voice package from the application, so that installation does not require terminal commands.
7. As a user, I want the application to check package integrity, version and compatibility before activating it, so that an incomplete installation cannot appear usable.
8. As a user, I want missing or damaged resources explained with a recovery action, so that I can repair the installation.
9. As a user, I want to remove an installed voice package from the application, so that I can recover disk space.
10. As a user, I want package removal to preserve my manuscripts and completed outputs, so that removing the engine does not delete my book.
11. As a listener, I want all official Chinese voices for the selected model available for selection, so that I can choose a suitable narrator.
12. As a listener, I want voices that passed project quality validation identified, so that I can distinguish tested voices from other available choices.
13. As a listener, I want to preview a fixed sample or a selected passage with my chosen voice and settings, so that I can assess narration before production.
14. As a listener, I want Traditional Chinese manuscripts supported, so that I can narrate my existing books.
15. As a listener, I want representative polyphonic words, numbers, dates and mixed Chinese and English evaluated, so that pronunciation limitations are known.
16. As a proofreader, I want synthesis preprocessing applied only to a temporary synthesis copy, so that my confirmed reading text remains unchanged.
17. As a subtitle user, I want subtitle text to retain the original confirmed wording and script, so that pronunciation normalization does not rewrite the displayed book.
18. As a book producer, I want book-wide voice defaults and independent batch voice settings, so that Kokoro follows the existing production-batch model.
19. As a user, I want saved model, voice and rate selections restored after reopening, so that the application does not silently change my narrator.
20. As a book producer, I want formal synthesis to use the confirmed reading snapshot, so that unconfirmed edits cannot enter a finished output.
21. As a listener, I want long passages split without missing, repeating or clipping content, so that complete books remain understandable.
22. As a book producer, I want Kokoro to reuse the existing pause, MP3 and subtitle workflow, so that local narration behaves consistently with other supported services.
23. As a user, I want loading, synthesis, completion, failure and cancellation shown clearly, so that I know the current work state.
24. As a user, I want the interface to remain responsive during CPU synthesis, so that I can monitor and cancel a job.
25. As a user, I want cancellation to end active inference and release its resources, so that a cancelled job does not continue consuming the CPU.
26. As a user, I want the model retained during consecutive previews or one production job, so that each passage does not require a cold load.
27. As a user, I want the model unloaded after inactivity, so that memory becomes available to other applications.
28. As a user, I want closing the main application to end its inference processes, so that no hidden worker remains running.
29. As a user, I want failed synthesis to stop with an actionable explanation, so that I can decide whether to retry or switch services.
30. As a privacy-conscious user, I want Kokoro failures to avoid automatic cloud fallback, so that my manuscript is not sent to another service unexpectedly.
31. As a user, I want successful audio blocks retained after interruption, so that resuming does not repeat valid completed synthesis.
32. As a user, I want changed models, voices or pronunciation processing to invalidate incompatible cached audio, so that old speech is not mistaken for the new selection.
33. As a user, I want failure or cancellation to preserve the previous successful output, so that an unsuccessful attempt cannot destroy my deliverable.
34. As a book producer, I want local batch audio to work with total MP3, total SRT and MP4 production, so that I can finish the existing book workflow offline.
35. As a user, I want rendering or changing visual materials to reuse valid audio, so that making a video does not trigger another synthesis job.
36. As a user moving a project, I want a clear missing-package message on another computer, so that I can reinstall the required engine without losing existing outputs.
37. As a user, I want existing cloud services and old projects to keep their documented behavior, so that adding Kokoro does not break earlier work.
38. As a user, I want measured loading time, synthesis time, memory use and cancellation time, so that I can assess CPU usability on the target computer.
39. As a listener, I want real recordings for manual quality review, so that a successful technical test is not confused with acceptable narration.
40. As a user, I want voice controls and package management inside the main window, so that related tasks preserve their state when I return.
41. As a user, I want necessary controls visible after restoring or resizing the window, so that I can complete operations without clipped buttons or overlapping text.
42. As a user, I want temporary installation, inference and test resources cleaned up, so that completed work does not leave locked files or test processes.

## Implementation Decisions

- **官方來源與相容性政策**：採 hexgrad 官方 Kokoro 中文版模型、音色及推論程式。允許必要且可追蹤的少量相容性修改；修改版標示為基於官方版本的相容版，不宣稱由官方發布。不預設重寫模型或整個推論堆疊。
- **雙執行環境**：主程式維持 Python 3.14.3。語音包附帶獨立 Python 3.12，使用明確的包內執行環境，不依賴系統 Python、使用者 PATH 或手動啟用虛擬環境。先驗證官方套件與依賴在 Windows 的實際組合，再固定版本。
- **CPU 與程序邊界**：所有 Kokoro 推論指定 CPU。推論在主程式管理的獨立程序中執行，不以 UI 工作執行緒取消等同模型已停止。一般操作無可見終端機，無須使用者管理本機網頁服務。
- **共同合成接點**：在既有試聽與正式製作共用的單塊語音合成邊界加入本機服務。共用層仍負責安全切分、原音快取、音訊解碼、停頓、字幕及原子發布。避免為 Kokoro 另寫整套試聽與製作流程；不要求第一階段建立通用插件平台。
- **服務能力與設定**：語音設定需能表達本機服務，不要求雲端金鑰或雲端設定檔。全書語音預設、批次語音設定與製作快照保存可重現的模型版本、音色、語速及處理政策。舊設定與舊成品提供相容讀取及遷移；變更全書預設不回寫既有批次。
- **模型身分與安裝位置分離**：書籍專案保存可重現的非秘密模型／語音包識別；包內執行環境與模型安裝由本機管理。搬移專案後能辨識缺少的版本，禁止默默改用其他模型、音色或服務。完整語音包不因每本書而重複複製。
- **語音包管理**：在主程式匯入已下載的離線語音包，檢查完整性、版本與相容性後才啟用。包內包含 CPU 依賴、模型、全部官方中文音色及中文／英文前處理所需資源。使用安裝暫存區；失敗不可留下看似已完成的安裝。移除只作用於所選語音包，保留書籍資料、有效快取及成品；使用中的資源不得直接刪除。
- **完整離線**：安裝完成後，首次試聽與製作皆不需網路，不在缺少資源時偷偷下載。依本機能力判斷是否可合成，不能把既有「不允許網路」直接解讀成「不能產生新音訊」。雲端傳送同意維持原有規則；本機介面清楚表明文字在本機處理。
- **音色**：提供固定官方中文模型版本內的全部中文音色，只有通過實測的音色可標示已驗證。少數代表性音色先完成完整品質驗收，不把其結果外推為全部音色已驗證。保存後保留明確選擇，不靜默替代。
- **文字副本與字幕**：必要的繁簡或數字讀法處理只作用於合成副本；不改寫來源文件、校對稿、朗讀稿及字幕用原文。保留原文區塊與合成區塊的對應，字幕時長以實際音訊為準。繁體字支援不等於台灣口音保證。
- **切分與限時**：CPU 冷啟動與推論不能直接沿用雲端請求大小、90 秒限時及網路重試策略。依實測制定切分、載入／合成限時與進度；所有區塊須覆蓋原文一次，超長內容不能靜默截斷。具體門檻尚未量測，不在本規格捏造數值。
- **合成結果契約**：接入既有單聲道、16-bit PCM、24 kHz 的共用音訊處理流程，驗證音訊非空且可完整解碼。正式批次 MP3／SRT 必須在必要區塊全部完成且驗證成功後發布。停頓、全書合併與影片處理維持既有時間軸規則。
- **快取與續作**：原音身分涵蓋模型內容／版本、引擎與前處理版本、實際合成文字、音色、語速及影響聲音的設定。改模型或處理規則不可誤用舊音訊；只改額外停頓仍可重用有效原音。取消或中斷後只重用完整驗證的區塊，不把部分輸出宣告成功。
- **資源生命週期**：連續試聽與同一次製作保留模型，工作進行中不得因閒置計時卸載。閒置後自動卸載；確切時長依量測制定並記錄。取消、工作失敗、安裝／移除及主程式關閉均有明確釋放路徑，確認程序已結束且檔案可解除占用。
- **錯誤與重試**：缺包、損毀、版本不相容、載入失敗、記憶體不足、合成失敗、逾時及取消須可區分。顯示可執行的恢復操作，保留先前成功結果；不套用雲端退避或無限重試，不自動切服務。續作及重試由使用者明確啟動。
- **UI 約束**：服務選擇、音色、試聽與語音包管理使用同一主視窗的內頁或面板。依操作順序配置，技術細節按需展開；主要操作保持可見，避免水平及巢狀整頁捲動。忙碌時停用衝突操作。啟動最大化，還原視窗後仍可操作。所有版面調整先提供設計圖，確認後實作。
- **交付階段**：先交真實可行性結果，包括官方相容性差異、樣本音檔、離線啟動、CPU／記憶體數據、語音包大小及程序清理證據。量測後再確認效能是否可接受及正式整合範圍。需求核定與 ready-for-agent 標籤不代表 UI 設計圖或聽感已驗收。

## Testing Decisions

- **主要接點已確認**：沿用既有 ProjectWorkflow 公開操作流程，測試設定、語音包操作、試聽、正式製作、取消、重開與續作。共同單塊合成邊界是內部實作接點，不新增第二套對外測試 API。
- **好測試的判準**：觀察使用者可見狀態、保存後重開的內容、實際音訊／字幕、有效快取重用、舊成品保護與資源釋放。不要依賴內部呼叫順序、私有欄位或複製演算法的斷言。模擬合成只能證明流程，不能證明 CPU、發音或離線可用。
- **既有先例**：既有語音流程測試已覆蓋音色清單、全書預設與批次獨立設定、試聽快照及保存；多服務測試已覆蓋服務選擇、試聽與正式製作重用及失敗保留舊結果；朗讀恢復測試已透過真實子程序驗證中斷後重開及有效區塊續作。沿用這些測試形式，擴充本機服務情境。
- **測試模組範圍**：以公開流程覆蓋語音包管理、本機服務設定與能力、試聽與朗讀製作、快取與原子發布、總音訊／影片沿用，以及桌面服務切換。程序生命週期與真實封裝另以整合驗證補足，只有無法由高層觀察的重要契約才加局部測試。
- **設定與版本驗收**：選取 Kokoro／音色／語速 → 保存 → 重開專案 → 確認選值保留。更換模型或前處理版本 → 續作 → 確認不重用不相容音訊。開啟既有雲端專案 → 確認原設定及舊成品可讀。
- **離線驗收**：在無既有模型與語言資源快取的乾淨 Windows 環境安裝完整語音包 → 封鎖網路 → 第一次試聽 → 確認無下載及雲端請求。確認朗讀稿 → 製作 MP3／SRT → 確認成功。缺少資源 → 重試 → 確認提示修復且無自動下載或替代服務。
- **文字與品質驗收**：以繁中、多音字、數字、日期、中英夾讀、標點及長段落建立固定樣本。合成 → 比對原朗讀稿及字幕 → 確認文字未被前處理改寫。逐段聆聽 → 記錄誤讀、漏句、重複、裁尾與長段落語速異常。只有經人工確認的音色標示品質已驗證。
- **真實 CPU 量測**：記錄 Windows、CPU、核心／執行緒、RAM、引擎／依賴／模型版本、音色、語速與樣本內容識別。分別量測冷載入、暖試聽及長稿製作時間、實際輸出長度、記憶體峰值、取消與閒置卸載耗時及包體大小。CPU 推論與無 GPU 依賴須以實際套件與執行證據確認；不先填入未測得的門檻。
- **取消與程序驗收**：開始載入或合成 → 按取消 → 確認工作停止。關閉主程式 → 檢查其子程序 → 確認全部結束。完成閒置卸載 → 檢查模型檔占用及程序記憶體 → 確認資源已釋放。驗證在工作執行中不觸發閒置卸載。
- **失敗與續作驗收**：完成第一個區塊 → 中斷後重開 → 續作 → 確認已驗證區塊未重做。模擬損毀音訊、推論失敗、逾時、空間不足及發布失敗 → 確認狀態可辨識、舊成品保留、無雲端備援。不得以縮短測試稿掩蓋長書失敗。
- **成品驗收**：製作批次 MP3／SRT → 完整解碼 → 確認字幕文字、音訊時長及停頓偏移一致。全書合併 → 製作 MP4 → 確認沿用有效音訊，不新增 TTS 或重複交接停頓。
- **安裝與移除驗收**：匯入損毀／不相容包 → 確認未啟用。移除可移除的語音包 → 確認程序及檔案釋放、書稿與成品仍在。重開仍引用已移除包的專案 → 確認明確提示重新安裝，不改選其他服務。
- **桌面驗收**：依核准設計圖操作語音包管理及語音設定 → 切換內頁再返回 → 確認輸入保留。還原及縮小視窗 → 確認必要操作可見、文字不重疊、按鈕不裁切。忙碌時 → 檢查衝突操作 → 確認停用，取消操作仍可用。
- **清理**：驗證後刪除本次測試資料、建置暫存與非成品快取，結束測試程序並釋放占用。保留正式語音包／程式成品、需求文件、最終音檔樣本與量測及驗收證據。不得刪除工作前既有資料。

## Out of Scope

- GPU、CUDA、其他硬體加速，以及要求使用者自行管理 Python 或本機服務。
- 要求 Kokoro 及所有依賴改用 Python 3.14.3；沒有實測依據的完整重寫。
- 社群修改權重、社群 ONNX 成品、重新訓練、微調、聲音複製及任意使用者模型匯入。官方 ONNX 匯出可另案評估，本案不以此取代已選定的官方 Python 推論路徑。
- 保證台灣口音、全部音色同等自然、所有中英夾讀與多音字零誤讀。
- 自動雲端備援、未經明確選擇混用服務或音色、背景自動下載及自動模型升級。
- 通用 TTS 插件平台、任意 HTTP 模板與多角色配音。
- 改寫原書、校對稿、已確認朗讀稿或字幕以迎合語音引擎。
- 尚未量測的速度、記憶體、語音包大小及閒置秒數承諾；未經確認的 UI 版面實作。

## Further Notes

- 本規格彙整本次對話已確認的 Q1～Q10；使用者亦確認主要測試沿用 ProjectWorkflow，並以真實整合驗證補足 CPU、離線及程序釋放。選擇先產出規格，不視為已授權跳過可行性結果審閱或 UI 設計圖確認。
- 沿用專案既有「一本書一個專案、製作批次獨立保存」、「可安裝 Windows 桌面」、「Python／Tkinter 與原子發布」、「總音訊獨立製作與共用全書合併設定」的架構決策。新增本機 TTS 取代舊首版規格對本機離線 TTS 的排除，其他資料保護與成品規則繼續適用。
- 官方中文版為 [hexgrad/Kokoro-82M-v1.1-zh](https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh)，模型頁標示 Apache-2.0。程式與前處理各自的授權及包內依賴通知須隨交付保留：[Kokoro LICENSE](https://github.com/hexgrad/kokoro/blob/main/LICENSE)、[Misaki LICENSE](https://github.com/hexgrad/misaki/blob/main/LICENSE)。
- 前次第一手來源查核顯示，PyPI [Kokoro 0.9.4](https://pypi.org/project/kokoro/0.9.4/) 與 [Misaki 0.9.4](https://pypi.org/project/misaki/0.9.4/) 的 Python 上限為 <3.13；官方主分支當時為 <3.14。這證明套件宣告排除 3.14.3，不能證明完整重寫有必要，也不能證明 Python 3.12 的整套 Windows 依賴已實測通過。落實時記錄確切版本與來源修訂。
- 官方 [KPipeline](https://github.com/hexgrad/kokoro/blob/main/kokoro/pipeline.py) 支援指定 CPU；官方 [中文前處理](https://github.com/hexgrad/misaki/blob/main/misaki/zh.py) 明記中英夾讀仍有弱點。這些是選型依據，不能替代本專案的實機品質或速度證據。
- 可行性結果必須明列已通過、未通過及尚未驗證項目。若官方依賴、完整離線、可取消性或聽感未達可用程度，先報告具體阻礙及修改成本，再確認正式整合範圍。
