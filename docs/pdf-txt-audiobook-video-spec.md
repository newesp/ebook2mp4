# 首版規格：PDF／TXT 書籍校對、朗讀與影片製作

版本：1.1　日期：2026-10-25　狀態：已核定

## Problem Statement

使用者需要將中英文書籍製作成朗讀音訊、字幕與影片。來源可能是具有文字層的 PDF、掃描 PDF、文字／圖片混合 PDF，或已整理的 TXT。PDF 擷取與 OCR 都可能遺漏或誤認正文，直接接上語音合成會把錯誤讀進成品；分散在不同工具中的校對、配音與合併流程，也難以追蹤內容版本及中斷進度。

一本書往往需要分批製作，例如先處理第 21～50 頁，再處理第 51～80 頁。使用者需要保留同書各批次的校對稿與成果，逐步完成後再合併為總音訊，並可接續製作總影片。批次間必須有自然的停頓，字幕跟隨實際時間；修改一批文字或更換背景時，也不應重做其他仍有效的語音。

## Solution

交付可安裝的 Windows 本機桌面程式，提供繁體中文介面與「來源、校對、語音、影片」四個可返回的步驟，採 A 版校對工作台。首版即完整支援：PDF 讀取 → 選頁 → 文字擷取／本機 OCR 轉 TXT → 人工／Gemini 校對 → 確認朗讀稿 → Edge-TTS → 批次 MP3／SRT → 總 MP3／SRT → 加入全片圖片或背景影片 → 總 MP4；另保留批次 MP4 及其合併路徑。TXT 是同等入口，直接進入校對，不依賴 PDF 或 OCR。

一本書是一個專案，可包含多個製作批次。PDF 依頁碼範圍建立批次，每份匯入 TXT 也可成為同書的獨立批次；各批次以不同檔案保存校對稿、朗讀稿與成品。Gemini 在工具內設定並呼叫，僅提出忠於原文的候選校對稿，由使用者逐段確認。正式語音只能來自已明確確認的朗讀稿。

使用者在全書合併畫面共用批次選取、順序與交接停頓，選擇輸出總 MP3、總 MP4 或兩者，各自附對應實際時間軸的總 SRT。總 MP3 直接合併有效批次 MP3，不需要圖片、背景影片或批次 MP4。相鄰批次間預設額外補 0.5 秒靜音，可透過介面調整及預覽。合併與更換視覺素材均重用既有有效語音，不新增 TTS 請求。所有工作保存在本機，支援版本追蹤、取消、重試、續作及整個專案資料夾搬移；使用者也可只輸出音訊，無須提供視覺素材。

## User Stories

1. As a Windows user, I want to start from either PDF or TXT, so that I can work with the source I already have.
2. As a Chinese-speaking user, I want a Traditional Chinese interface that accepts Traditional Chinese, Simplified Chinese and English content, so that I can work without changing the source language.
3. As a Windows user, I want an installable desktop application, so that normal use does not require a terminal or a manually started local web server.
4. As a book producer, I want one project to contain different production batches of the same book, so that selecting another page range does not require a separate project.
5. As a user, I want to see the source filename, size, readability, project location and required copy space, so that I can check the input and storage before importing.
6. As a user, I want inputs copied into my project without overwriting originals, so that I can move source files without losing my work.
7. As a book producer, I want different batches saved as separate files, so that producing later pages does not overwrite earlier batch outputs.
8. As a book producer, I want each imported TXT to create a separate batch even in a PDF project, so that I can combine independently prepared parts of the same book without invented page numbers.
9. As a proofreader, I want separate drafts and reading confirmations for each production batch, so that correcting one batch does not invalidate another batch's confirmed text.
10. As a book producer, I want book-wide voice defaults and independent batch voice settings, so that changing defaults does not unexpectedly regenerate existing narration.
11. As a PDF reader, I want to see the total page count and an inclusive start/end range, so that I can process only the pages I need.
12. As a PDF reader, I want invalid or non-integer page ranges rejected before extraction, so that I cannot accidentally start an incorrect job.
13. As a PDF reader, I want page previews with physical PDF page numbers distinguished from printed page numbers, so that I can choose the correct range.
14. As a PDF reader, I want selected pages extracted in their original order with their original page numbers, so that the transcript follows the book.
15. As a PDF reader, I want an explanation when a PDF is damaged, unreadable or password protected, so that I can replace the input.
16. As a PDF reader, I want usable text layers extracted before OCR, so that readable text is preserved efficiently.
17. As a proofreader, I want to preview and undo layout line-break cleanup, so that spaces, punctuation, numbers and abbreviations are not silently changed.
18. As a user of scanned PDFs, I want separate OCR choices for Traditional Chinese plus English, Simplified Chinese plus English, and English, so that recognition follows the document language.
19. As a user of mixed PDFs, I want automatic detection to operate page by page, so that scanned pages are not missed inside a text document.
20. As a user of mixed PDFs, I want pages with only a page number or sparse text flagged for inspection, so that image-based body text is not reported as fully extracted.
21. As a user of scanned PDFs, I want to force OCR for all pages or selected pages, so that I can recover content missed by automatic extraction.
22. As a user of rotated scans, I want to rotate a page by 90, 180 or 270 degrees before retrying OCR, so that I can correct its reading orientation.
23. As a proofreader, I want each page's image, extracted text, extraction method, status and error visible together, so that I can compare recognition with the source.
24. As a proofreader, I want successful, failed and blank/unconfirmed pages distinguished, so that missing content cannot pass unnoticed.
25. As a user, I want to retry only failed pages and review new OCR candidates before replacing corrected content, so that successful work and manual corrections survive retries.
26. As a proofreader, I want to explicitly retain or skip blank/unreadable pages, so that the reading draft is confirmed only after every anomaly is resolved or acknowledged.
27. As a TXT user, I want missing OCR executables or models to affect only OCR, so that I can still use the complete TXT workflow.
28. As a TXT user, I want strict loading of UTF-8, UTF-8 BOM and UTF-16 BOM with a manual Big5/CP950 option and preview, so that Chinese text is decoded correctly.
29. As a TXT user, I want decode failures and suspected garbled text to prompt another encoding choice, so that original characters are not silently replaced.
30. As a proofreader, I want full-text editing, search, replace, undo and save, so that I can correct the transcript within the tool.
31. As a proofreader, I want UTF-8 TXT export and external TXT reload, so that I can also use my preferred editor.
32. As a proofreader, I want to preserve a copy or explicitly replace unsaved edits during reload, so that external proofreading does not discard my work.
33. As a proofreader, I want extracted originals and corrected drafts stored separately, so that I can return to the original transcription.
34. As a proofreader, I want blank-line paragraphs, punctuation and original script preserved, so that the tool does not rewrite or convert my book automatically.
35. As a proofreader, I want save status, draft version, character count and nonempty paragraph count, so that I understand the current text state.
36. As a proofreader, I want artificial page labels excluded from the reading TXT while original page data remains available, so that narration does not read metadata aloud.
37. As a proofreader, I want precise text-to-page mapping marked unavailable after edits that invalidate it, so that the tool does not imply a false correspondence.
38. As a proofreader, I want built-in Gemini settings and proofreading calls, so that I can use LLM proofreading without manually copying text to an external website.
39. As a proofreader, I want to save a local Gemini API key, choose or adjust the model and test the connection, so that I can configure proofreading without putting credentials inside my book project.
40. As a proofreader, I want optional LLM proofreading for both imported TXT and PDF-derived TXT, so that I can review suggested transcription and punctuation corrections.
41. As a proofreader, I want the LLM service, model and outgoing text scope visible before I start cloud proofreading, so that I decide what text is sent.
42. As a proofreader, I want an LLM candidate and visible differences before applying changes, so that suggestions cannot silently rewrite the draft.
43. As a proofreader, I want to retain the pre-correction version and undo accepted LLM changes, so that I can recover from incorrect suggestions.
44. As a proofreader, I want LLM failures, cancellation or missing configuration to leave my draft intact and manual editing usable, so that proofreading remains possible.
45. As a proofreader, I want Gemini limited to transcription errors, punctuation and obvious line breaks while retaining uncertainty, so that proofreading stays faithful to the original book.
46. As a proofreader, I want whole-batch or selected-text Gemini proofreading with paragraph-level accept or reject and an accept-all option, so that I can adopt only the corrections I approve.
47. As a proofreader, I want successful candidate sections retained when a long Gemini job partially fails, so that I can retry failed parts without losing completed suggestions or silently changing my draft.
48. As a user, I want to confirm the exact reading text as an immutable snapshot, so that narration has an identifiable source version.
49. As a user, I want any draft edit or applied correction to invalidate the current reading confirmation, so that new speech cannot use unapproved text.
50. As a listener, I want available Taiwanese Mandarin, Mainland Mandarin and English voices with locale, name and supplied gender information, so that I can choose the narrator.
51. As a listener, I want voice-list refresh and cached results with a visible error for an unavailable voice, so that the tool never substitutes another narrator silently.
52. As a listener, I want rates of at least -20%, -10%, normal, +10% and +20%, so that I can choose a comfortable speed.
53. As a listener, I want a fixed example or selected draft passage previewed with the same processing and rhythm settings as production, so that preview predicts the final narration.
54. As a listener, I want one explicitly chosen voice per synthesis job even for mixed-language text, so that voice selection remains predictable.
55. As a listener, I want complete paragraph context preserved where possible and safe splitting where required, so that long text is read without missing, repeating or cutting words.
56. As a listener, I want normal punctuation and natural engine pauses preserved, so that technical chunk boundaries do not introduce arbitrary long pauses or clipped syllables.
57. As a listener, I want configurable extra sentence and paragraph pauses with natural and relaxed presets, so that I can compare and adjust the reading rhythm.
58. As a listener, I want coincident sentence/paragraph pauses to use the longer value and the final paragraph to add no trailing pause, so that silence is predictable.
59. As a user, I want synthesis progress, current chunk, completed count, failures and cancellation, so that I can manage long jobs.
60. As a user, I want bounded network retries and reuse of validated completed chunks after reopening, so that interruptions do not restart the entire book.
61. As a user, I want a playable, decodable MP3 only after every required chunk succeeds, so that a partial recording cannot appear complete.
62. As a subtitle user, I want UTF-8 SRT based on provider timings or actual complete-chunk durations, so that subtitles do not pretend to have unsupported word-level precision.
63. As a subtitle user, I want subtitle offsets to include inserted silence and clear during added paragraph gaps, so that subtitles follow the actual narration.
64. As a user, I want playback, save-as and open-folder actions for audio outputs, so that I can inspect and use the finished files.
65. As a user, I want local text edits to regenerate only invalid speech chunks and assembled outputs, so that unchanged speech can be reused.
66. As a video creator, I want one JPEG/PNG image or one decodable MP4 background, so that I can create a narrated video from simple visual material.
67. As a video creator, I want visual preview, preserved aspect ratio, black padding and a black default background for transparency, so that the result does not stretch or crop my material unexpectedly.
68. As a video creator, I want 1920×1080 or 1280×720 at 30 fps, so that I can produce a standard landscape video.
69. As a video creator, I want a still image to last for the narration and a long background video trimmed to it, so that narration determines the final duration.
70. As a video creator, I want short backgrounds to loop by default or hold their final frame, so that visuals can cover the entire narration without repeating or shortening audio.
71. As a video creator, I want background video sound excluded, so that only the narration is heard.
72. As a video creator, I want an MP4 with H.264 video, yuv420p pixels, AAC-LC stereo audio at 48 kHz and faststart, so that the output meets the chosen upload format.
73. As a video creator, I want MP4 output to reuse current valid audio and its SRT without another TTS request, so that changing visuals costs no new synthesis.
74. As a video creator, I want render progress, cancellation, retry, playback and open-folder actions, so that I can control and inspect video creation.
75. As a book producer, I want to combine my project's batch MP4 files into one total video, so that I can deliver the book as one video after producing it in parts.
76. As a book producer, I want to select and reorder batches for the total video with warnings for PDF page overlaps or gaps, so that I can deliberately control the included content.
77. As a listener, I want a reasonable pause at each batch join with a correctly offset total SRT, so that the next batch does not start immediately after the previous sentence.
78. As a book producer, I want total videos to track their selected source versions and accept current valid sources for regeneration, so that stale results remain visible without being mistaken for current work.
79. As a book producer, I want mixed batch resolutions normalized for the total video with voice differences reported, so that I can merge existing outputs without new narration requests.
80. As a listener, I want a default extra 0.5-second batch-join pause that I can adjust and preview, so that I can control the transition without clipping existing audio.
81. As a proofreader, I want to inspect the ending and beginning text at a batch join and return to proofreading, so that I can correct a sentence split across page ranges myself.
82. As a user, I want reopening or moving the entire project folder to retain sources, drafts, caches and outputs through relative paths, so that work can continue elsewhere on the machine.
83. As a user, I want old outputs marked with their source version and stale status, so that they cannot be mistaken for current results.
84. As a user, I want a running job to keep its initial text and settings snapshot when I edit the project, so that one result cannot mix versions.
85. As a user, I want only one output-generating job per project at a time, so that conflicting writes do not corrupt progress.
86. As a user, I want validated results retained after cancellation or interruption and partial files excluded from cache reuse, so that resume is trustworthy.
87. As a user, I want failed, cancelled or out-of-space output attempts to preserve the previous successful output, so that regeneration cannot destroy my deliverable.
88. As a user, I want stage-specific dependency checks and actionable installation errors, so that a missing tool blocks only the feature that needs it.
89. As an offline user, I want importing, manual proofreading, saving and rendering with existing audio to remain available, so that network loss affects only online services.
90. As a Windows user, I want Chinese filenames, spaces and common punctuation supported, so that I do not need to rename my files.
91. As a privacy-conscious user, I want local PDF/OCR/media processing, deliberate cloud text submission and logs that omit manuscript text by default, so that my document is not uploaded unnecessarily.
92. As a user of long documents, I want background processing with a responsive interface and cancellation, so that work on a large book does not freeze the tool.
93. As a user, I want permissions and free space checked before writes with actionable errors, so that storage problems are recoverable.
94. As a listener, I want representative Chinese, English and mixed-language recordings reviewed for naturalness, so that playable files are not the only measure of narration quality.
95. As a Windows user, I want bundled media and OCR tools with an in-app language model download, so that I can use the installed application without configuring command-line tools.
96. As a book producer, I want to combine production-batch narration into a total MP3, so that I can listen to the selected book content as one audio file.
97. As a book producer, I want total MP3 and MP4 exports to share selected batches, order and join pauses, so that I can choose either format or both without arranging the book twice.
98. As a listener, I want a total SRT that follows the actual merged MP3 timeline and added pauses, so that audio-only playback has matching subtitles.
99. As a book producer, I want visual-only changes to preserve a valid total MP3, so that audio is regenerated only when its selected narration or assembly changes.
100. As a book producer, I want each requested output format to keep its own successful result when another is missing or fails, so that retries do not repeat completed work.
101. As a book producer, I want to turn a completed total MP3 and its SRT into a total MP4 with visual material, so that I can finish audio first without producing batch videos.

## Implementation Decisions

1. **首版範圍與交付。** Windows 本機、單人操作、可安裝的桌面程式；日常使用不需終端機或自行啟動本機網頁服務。PDF／TXT 雙入口、PDF／OCR、人工／Gemini 校對、Edge-TTS、MP3／SRT、批次 MP4、總 MP3／SRT 與總 MP4／SRT 都是首版 P0。輸入支援繁體中文、簡體中文與英文，不自動轉換語言或繁簡體。四個步驟可返回，缺少必要輸入時顯示原因；TXT 批次不顯示必填 PDF／OCR 欄位。

2. **領域與模組邊界。** 專案代表一本書，製作批次代表一次選取內容進行製作的工作單位；校對稿是可編輯工作文字，候選校對稿是尚待採用的 Gemini 建議，朗讀稿是已確認且不可變的文字版本。建立供 UI 呼叫的「專案工作流程」公開介面，協調來源、校對與版本、語音、影片及專案保存；這也是已確認的主要測試邊界。PDF／OCR、Gemini、Edge-TTS、檔案與媒體程序由內部整合層處理，不要求各自另立一套對外工作流程。

3. **專案與批次。** 同書可分次建立 PDF 頁碼批次及 TXT 批次，不因新增範圍而另建書籍專案。每批獨立保存內容範圍、原稿、校對稿、校對進度、朗讀確認、語音設定、成品與狀態；修改一批不取消另一批的確認。每份新匯入 TXT 建立一批，重新載入既有批次 TXT 則更新該批的校對流程；TXT 以名稱與手動排序管理，不假造 PDF 頁碼。首版不自動分章拆檔。專案集中列出各批次檔案、狀態及成品來源版本。

4. **PDF 選頁與擷取。** 顯示總頁數、來源資訊及頁面預覽，實際 PDF 第一頁為 1，起訖皆包含，預設整份。必須驗證整數且 1 ≤ 起始頁 ≤ 結束頁 ≤ 總頁數，錯誤不得啟動。只處理選定頁並保留原順序與原始頁次，明示 PDF 頁次可能不同於印刷頁碼。逐頁保存擷取方式、原始文字、設定、狀態、錯誤及使用者略過確認。損毀、不可讀或密碼保護 PDF 顯示原因與更換入口，不提供解密。

5. **OCR 與品質範圍。** 清晰、橫排、單欄的文字型／掃描型／混合型 PDF 是首版品質驗收範圍。自動模式逐頁優先讀取可用文字層，無文字時轉圖 OCR；僅有頁碼、少量文字且正文疑似圖片的頁面必須標記待檢查，不能宣稱正文完整。提供繁中＋英文、簡中＋英文、英文，獨立於 TTS 音色。支援全部強制 OCR、指定頁強制 OCR、90°／180°／270° 旋轉重試與只重試失敗頁。新結果先成候選，不覆蓋校對稿；頁面圖與文字可對照。成功、失敗、空白／無文字待確認分開表示，異常須處理或明確略過才能確認相關批次朗讀稿。若選用 Tesseract，採 chi_tra、chi_sim、eng 的正確語言模型設定。

6. **TXT 與人工校對。** 嚴格支援 UTF-8、UTF-8 BOM、UTF-16 BOM，提供 Big5／CP950 手動選擇與載入預覽。解碼失敗或疑似亂碼可換編碼，不以替代字元靜默吞字。支援全文編輯、搜尋、取代、復原、儲存、UTF-8 TXT 匯出與外部稿重新載入；遇未存編輯，須保留副本或由使用者明確取代。顯示儲存狀態、版本、字元數與非空段落數。空白行代表段落，保留標點；原始換行與版面換行整理可預覽及撤回，不默默處理頁首頁尾、頁碼、跨行連字號或刪除英文空格、數字及縮寫標點。

7. **原稿與頁碼關係。** 擷取原稿、校對稿、候選校對稿及朗讀稿分開保存。原始 PDF 擷取保留逐頁關係；朗讀 TXT 預設不插入會被讀出的頁碼標籤。全文或外部編輯使精確對應失效時，明示無精確對應，原始逐頁資料仍可查閱。切句、TTS 與字幕生成不能反向改寫校對稿。

8. **Gemini 設定與行為。** 首版 LLM 僅使用 Gemini，提供本機 API Key 儲存、模型選擇／調整及連線測試；金鑰不進入可搬移書籍專案。可處理整份批次 TXT 或選取內容，啟動前顯示服務、模型與送出範圍，僅送出該範圍文字，不自動上傳 PDF／素材。僅修正轉錄／OCR 錯字、標點與明顯斷行，不潤飾文風、翻譯、摘要、刪減或轉繁簡；不確定處保留疑點。結果逐段顯示差異，支援採用、拒絕與全部採用，保存原版本以便撤回。未設定、失敗或取消不改原稿、不阻擋人工校對。

9. **Gemini 長稿與版本。** 長稿分段處理，保留成功候選，標明失敗及未完成範圍，可只重試失敗部分；部分結果不可標為整批完成，也不自動套用。候選記錄原校對稿版本與範圍；等待期間原稿變更時提示差異，不以舊候選覆蓋新編輯。採用任何修改後，仍須重新確認該批朗讀稿，不能由 LLM 自動確認。

10. **朗讀確認與任務快照。** 異常頁處理或明確略過後，使用者才可確認當前批次內容為朗讀稿，建立不可變文字快照與雜湊。後續編輯、重載或套用候選立即取消該批目前確認狀態，不改既有快照。新正式合成只能使用已確認稿。任務開始固定文字、設定與規則版本，進行中修改不得混入結果；可取消後用新快照開始。舊成品可播放，但顯示來源版本及待更新狀態。

11. **語音設定與試聽。** Edge-TTS 為首版語音提供者，需網路、不需 GPU。顯示可用音色名稱、語系及服務提供的性別資訊，包含可用的台灣華語、中國普通話及英文音色；清單可更新並快取，不以永久寫死名單判定有效。失效音色報錯，不暗換人聲。單次合成只用一個明選音色，中英混合不自行切聲。語速至少 -20%、-10%、正常、+10%、+20%，預設正常。全書語音預設供新批次沿用，各批可個別調整；改預設不改舊批次，須明確套用才更新。固定範例或所選稿件試聽，採與正式輸出相同的處理、語速與節奏。

12. **切分與朗讀停頓。** 優先保留段落上下文，受引擎限制才依句尾、其次合理分句切塊，不用固定短字數硬切。避免切開英文單字、姓名、縮寫、小數、網址、中文語詞，涵蓋引號、括號與省略號情境；內容不得漏字、重複或亂序。必要朗讀正規化須可查看，不能暗改校對稿。保留引擎標點韻律、呼吸與尾音，工程切塊不能一律加長停頓，不依賴任意自訂 SSML。

    句尾額外停頓預設 0 毫秒，可調 0～1,500；空白行分段的段落額外停頓預設 500 毫秒，可調 0～3,000。同邊界取較長值而不相加，末段不額外補段落尾靜音。「自然」預設 0／500，「舒緩」200／800，均可自訂；非零句尾停頓須有對應合成與時間資料，可能採逐句合成並需試聽確認語調。

13. **語音快取、音訊與字幕。** 區塊記錄穩定識別、順序、實際送出文字、內容／設定／處理規則雜湊、狀態、檔案及實測長度；快取不能只靠檔名。局部改稿只重做失效區塊與組裝成品；換音色／語速／提供者失效相關語音；改句尾／段落停頓重組音訊及字幕，切分改變才更新相關語音，保留一致的原始區塊。每區塊網路錯誤預設至多嘗試 3 次，耗盡保留進度並報錯。必要區塊全完成、音訊非空且可解碼才可成功。輸出 MP3 與 UTF-8 SRT，採提供者時間或實際完整區塊時長，不虛構逐字時間；偏移包含區塊與新增靜音，額外段落靜音不維持上一段字幕。提供播放、另存與開啟資料夾。

14. **批次影片。** 使用與該批目前文字／語音設定一致的完整音訊，不重新 TTS。每批選一張可解碼 JPEG／PNG 或一支以實際串流／解碼檢查通過的 MP4；預覽保持比例、黑邊補齊，透明圖片預設黑底，不拉伸或預設裁切。預設 1920×1080，可選 1280×720，16:9、30 fps。圖片全程顯示，長背景裁切，短背景可循環或最後一格定格、預設循環；背景原聲靜音，旁白不得重複、變速或截短。輸出實際 H.264／yuv420p 視訊與 AAC-LC／48 kHz／立體聲音訊的 MP4，具 faststart 並附同時間軸 SRT。換素材、循環模式或解析度只更新影片，不重做音訊／字幕。提供進度、取消、重試、播放與開啟資料夾。

15. **批次影片合併路徑。** 在同書專案選擇有效批次 MP4 與順序；PDF 批次預設依起始頁排序並可手動調整，重疊或缺口只提示，使用者可明確繼續，不自動去重或補頁。TXT 批次以名稱與手動排序。合併前顯示相鄰批次的結尾／開頭文字，可返回校對修正半句銜接，不自動跨批搬字。總影片可選 1080p／720p，將混合解析度批次保持比例統一尺寸；音色／語速差異提示而不重配音。總影片沿用批次音訊，另產總 SRT；不加片頭或轉場特效，不改批次原成品。

    相鄰批次之間預設額外加 500 毫秒靜音，介面可調 0～5,000 毫秒並預覽接點；保留原音訊頭尾，所以總間隔可能更長。新增靜音期間維持前一批最後一格、清空字幕，末批後不補交接停頓。N 個批次增加 N−1 個停頓；總長與字幕偏移依各批實測時間及新增停頓組成。只改交接停頓，僅重建總 MP4／SRT，不重做批次或 TTS。

16. **成品版本及更新。** 批次成品保存朗讀稿及語音／視覺設定來源；總音訊保存選入批次音訊版本與全書合併設定。總影片按來源方式記錄：批次影片合併保存選入 MP4 版本，總音訊製片保存來源總 MP3／SRT 版本與全片視覺設定。只有實際相關來源變更才標待更新，未選批次不影響，舊成果仍可播放。各路徑只接受與目前內容／設定一致的有效來源，不一律要求批次 MP4。共用批次選取／順序／交接停頓變更使相關總 MP3／SRT 及總 MP4／SRT 待更新，不失效批次；純背景／影片解析度變更只更新影片。

17. **保存與續作。** 保存專案格式版本、識別、名稱與時間；來源副本、原名及雜湊；各批內容範圍、逐頁擷取、原稿／校對稿／候選／朗讀稿版本；Gemini 範圍／模型／採用狀態；全書與批次語音設定；區塊快取；視覺素材副本／雜湊；成品來源及任務狀態／錯誤／進度。匯入前顯示檔案資訊、專案位置與複製所需空間，不覆寫來源。專案內用相對路徑，整個資料夾搬移後可開啟，缺檔明列；成品可另存指定位置，API Key 留本機設定。

18. **任務、失敗與原子輸出。** 同專案一次一個產生成品任務，狀態至少包含等待、執行中、取消中、已取消、失敗、完成。背景執行、保持介面可回應與接受取消，未知時長顯示階段及完成數，不捏造百分比／ETA。重開可辨識中斷並續作或重來，僅完整且驗證通過的中間檔可重用。新成品寫暫存、驗證後才發布正式檔，失敗／取消／空間不足不能破壞上一份成功成品，不得把半成品標成功。

19. **工具交付與本機限制。** 安裝包包含 FFmpeg／FFprobe、OCR 引擎等必要工具及其執行需求；OCR 語言模型首次使用時顯示下載大小並由介面安裝，不要求命令列。依階段檢查工具、模型、Gemini 與語音服務，只阻擋受影響功能。離線仍可匯入、人工校對、保存，以及用已有完整音訊製作影片。OCR 逐頁、媒體用串流／外部程序，不整本載入頁圖或整支影片。程序以參數傳值，支援中文、空白及常用標點的 Windows 路徑，不拼接執行使用者文字的 shell 命令。寫入前檢查權限與空間，日誌預設不記錄全文書稿；除主動使用的雲端文字服務及安裝／更新外，資料處理留本機。

20. **技術選型。** 現階段無應用程式與既有測試框架可沿用，先遵守已核定的書籍／批次領域及桌面交付決策。具體 UI／桌面框架、程式語言、PDF 函式庫、OCR 引擎、資料格式、Gemini 預設模型與打包細節在技術設計時決定，不能因此縮減首版功能。novel-generator 僅作 Edge-TTS、Gemini 設定及 FFmpeg 行為參考，不成為執行依賴，也不引入漫畫／小說生成領域。

21. **總音訊與共用合併設定。** 直接以與目前朗讀稿／語音設定一致的有效批次 MP3 合併總 MP3，不要求批次 MP4 或視覺素材，不新增 TTS 請求。與總影片共用批次選取、順序及交接停頓；同一全書合併畫面可選 MP3、MP4 或兩者。MP3 也另附總 SRT，依實際音訊與新增停頓計算，新增靜音期間不維持前批字幕。兩格式共用內容安排，但各自字幕須對應實際成品時間，不能忽略編碼時長差。總音訊沿用預設額外 0.5 秒、可調 0～5 秒、不裁原頭尾、不加末批尾停頓的已核定規則。

22. **各格式獨立失效與 A 版方向。** 總音訊追蹤選入批次的朗讀稿／音訊／語音設定及合併選取／順序／停頓；圖片、背景影片與影片解析度不影響有效總 MP3，未選批次修改也不影響。相關音訊或合併設定變更標待更新，舊檔保留可播；總影片仍追蹤其視覺及影片版本。正式介面採 A 版校對工作台，保留左側書籍／批次、中間原頁／校對稿、右側校對／確認工具。兩格式各自檢查必要輸入，可用者先完成，缺項／失敗明列且整體顯示部分完成，不回滾成功成果，重試只處理未完成格式。必要輸入依影片來源方式區分，不能一律要求批次 MP4。

23. **總音訊直接製片。** 已完成且與目前內容／語音及全書合併設定一致的總 MP3，可直接搭配視覺素材製作總 MP4，沿用總 SRT 的時間基準，不需要先產生批次 MP4，不重新呼叫 TTS。既有總音訊已包含交接停頓，製片不得重複添加、重排朗讀或重新偏移整個批次時間軸；仍需驗證實際媒體與字幕時間。保存總 MP3／SRT 來源版本及視覺設定，來源失效或更新使對應影片待更新，純視覺修改不失效音訊。預設影片方式採總音訊製片，總音訊成品提供「製作 MP4」，整支使用一張圖片或一支背景影片；保持比例補邊、透明黑底、解析度／編碼、長背景裁切、短背景循環／最後一格定格及原聲靜音，沿用既定影片規則。另可切換「合併既有批次影片」，供保留各批不同畫面使用；不增加多素材時間軸。

## Testing Decisions

1. **主要邊界與品質標準。** 使用者已確認以 UI 呼叫的專案工作流程為主要測試入口，從暫存書籍專案驅動雙入口匯入、校對、朗讀確認、批次輸出、總影片合併、取消及重開續作。透過公開狀態、版本、錯誤、進度與實際成品驗證來源處理、校對／版本、語音、影片、專案保存各模組；不綁定內部類別、函式、檔案切法或非必要呼叫順序。少量 UI 端到端測試驗證四步驟、編輯／差異／確認、取消及成品操作的連接。

2. **替身、真實整合與先例。** 在整合層控制 Gemini／TTS／OCR 回應及故障，重現失敗、取消、有限重試與續作；只有產品契約需要時才觀察請求，例如合併或換背景為零次 TTS。相同工作流程另使用真實 PDF／OCR、FFmpeg／FFprobe 驗證成品，並執行真實 Gemini／Edge-TTS 連線驗收與人工試聽；不對線上模型輸出作固定文字或音訊位元組快照。專案目前沒有程式碼或同類測試先例，既有需求驗收情境是依據；不得把模擬通過當作真實工具通過。

3. **PDF 與 OCR。** 20 頁 PDF 選第 3～5 頁，只取得三頁且頁次／順序為 3、4、5；0、超界、反向、非整數範圍不能啟動。測繁中、簡中、英文清晰掃描及文字／混合 PDF，語言設定正確；僅頁碼是文字而正文為圖時不能報完整。驗證全頁／指定頁強制 OCR、旋轉、只重試失敗、候選不覆蓋校對；空白及失敗阻擋朗讀確認直到處理或明確略過。損毀、密碼、缺工具／模型提供可行錯誤；沒有 OCR 時 TXT 全流程仍可用。

4. **TXT 與人工校對。** 各支援編碼正確載入，錯編碼可換選且不吞字；涵蓋預覽、搜尋、取代、復原、保存、UTF-8 匯出、外部重載、未存稿衝突及原檔不變。驗證原稿／校對稿分離、空白行段落與標點保留、換行清理可撤回、無朗讀頁碼標籤及失效頁碼對照提示。兩份 TXT 及 PDF 專案加入 TXT 都產生獨立批次、不假造頁碼、不覆蓋其他批次。

5. **Gemini。** 本機金鑰／模型設定與連線測試可用，專案搬移不帶金鑰，缺設定仍可人工完成流程。整批與所選範圍只送出對應文字，結果有差異、逐段採用／拒絕及全部採用；拒絕或未選內容不變，採用可撤回且取消該批朗讀確認。長稿單段失敗時成功候選保留、未完成明示、只重試失敗可用，不自動套用或宣告全部完成。等待期間改稿，舊候選不能直接覆蓋新稿。取消、網路錯誤與不可用模型不破壞原稿；人工檢查校對忠實度與不確定處理。

6. **確認與版本隔離。** 未確認文字及未處理異常頁不能正式合成。確認快照內容與當時稿一致，之後改稿不改舊快照；修改第 21～50 頁批次，不改第 51～80 頁批次的內容與確認。改全書語音預設只影響新批次，指定套用才更新舊批。執行中編輯不混入任務快照；舊成品顯示正確來源與待更新狀態。

7. **人聲、切分與快取。** 音色／語速與試聽及正式請求一致，無效音色不得替換。樣稿含繁中、英文、混合、對話、問句、姓名、數字、小數、縮寫、網址、引號、括號、省略號及長句；切分前後內容守恆、不漏不重不亂序、不切開詞或裁尾音。自然／舒緩與自訂句尾／段落停頓符合數值，同邊界取最大、末段無額外段落尾靜音。修改一段只重做失效語音，換人聲／語速不混快取；停頓調整保留仍有效原始語音，換背景／合併不新增 TTS 請求。網路錯誤每塊最多 3 次嘗試，必要區塊不全不能報成功。

8. **媒體與時間軸。** MP3 非空且可解碼，SRT 為 UTF-8、時間非負、依序、不重疊、反映新增靜音，額外段落／交接靜音不持續上一段字幕。以真實成品檢查 H.264、yuv420p、AAC-LC、48 kHz、立體聲、30 fps、指定解析度、faststart 與實際雙串流，不只看副檔名或程序結束碼。圖片全程顯示、比例／透明黑底正確；短片循環／定格及長片裁切都保留完整單次旁白、排除背景原聲。批次 MP4 與朗讀音訊時長差不超過 200 毫秒；SRT 不超出對應成品結尾 200 毫秒。

9. **批次影片合併。** 驗證批次選取、預設 PDF 頁序、手動排序、重疊／缺頁提示與明確繼續，不去重補頁；TXT 可手排。混合 720p／1080p 正確統一尺寸且保持比例，音色／語速差異提示但不重配音。總影片選入 A／B、未選 C：A 改稿或更新 MP4 使它待更新，C 修改不影響；重新合併拒絕失效成品，舊總影片與原批次保留。總 MP4／SRT 有全部選入內容與正確順序，且不新增 TTS 請求。

10. **交接停頓與預覽。** 分別合併 1／2／3 批，預設新增 0／500／1,000 毫秒，末批無尾部交接停頓；總影片相對批次實測時長加停頓的差不超過 200 毫秒。介面調整 0～5 秒可預覽，只重建總影片／總字幕。新增靜音維持前批最後一格且無字幕，後批字幕偏移正確，原音訊頭尾完整。相鄰結尾／開頭文字可檢查並返回校對，不自動跨批搬字；人工試聽預設 0.5 秒及調整值，不能把額外 0.5 秒誤報成總間隔恰為 0.5 秒。

11. **故障與資料完整性。** 涵蓋斷網、Gemini 分段失敗、OCR 單頁失敗、TTS 重試耗盡、合成／渲染／合併取消、程序中斷、重開、缺檔、不可寫目錄與空間不足。有效進度可續，不完整檔不可重用或報成功，前一份成功成品不能被破壞。整個專案搬移後可找回來源、校對稿、候選、快取及成品，缺項明列。驗證中文／空白／標點路徑、離線人工流程及離線以既有音訊製片。

12. **安裝與規模。** 在無開發環境、FFmpeg、OCR 引擎的新 Windows 環境，安裝後能啟動並使用內附工具，語言模型可見下載大小並於介面安裝；未裝模型不阻擋 TXT。至少測 100 頁選取範圍、10 萬字元 TXT、30 分鐘成品，記錄硬體、工具版本、實際耗時與記憶體觀察；不整批載入掃描頁圖或影片，長工作介面可回應並接受取消，不預先承諾固定倍速或未核定的效能門檻。

13. **人工朗讀品質。** 固定稿包含繁中敘述、對話、問句、英文、縮寫、數字及混合語言，與 novel-generator 以相同文字、同一仍可用人聲與語速比較，分辨工具切分及停頓影響。試聽 30～60 秒短稿、5 分鐘多段稿、長篇開頭／中段／結尾與批次接點；無工具造成的漏句、重複、裁尾音、不合理詞中切斷或字幕累積錯位。自然／舒緩差異可辨，最終預設待使用者以真實試聽確認；分開記錄 OCR 錯字、人聲發音與工具切分問題，不宣稱補靜音能解決所有品質問題。

14. **總音訊與各格式失效。** 沒有任何圖片或 MP4 的專案，只要選入批次 MP3 有效即可完成總 MP3／SRT，且零新增 TTS 請求。驗證 MP3／MP4 共用選取、順序及預設 0.5 秒／可調交接設定；各自字幕反映實際成品及新增靜音，保留原頭尾，不增加末批尾停頓。總音訊選 A／B、不選 C，更換視覺／影片解析度或修改 C 不失效總 MP3；A 文字／語音設定及合併順序／停頓變更才使相關總音訊待更新，舊成品保留。同時要求兩格式時，注入缺項或單格式失敗，驗證可用格式先完成、狀態不冒充全部成功、不回滾成功檔，重試不重做成功格式；缺項依影片來源方式判斷。

15. **總音訊製片。** 沒有任何批次 MP4、只有有效總 MP3／SRT 的專案，搭配視覺素材可完成總 MP4，零新增 TTS 請求；聲音內容順序與總音訊一致，原交接只出現一次。輸出有實際影音串流、字幕對應來源總音訊且符合既有時長容許差；取消／失敗保留成功總 MP3／SRT 及舊總影片，更新總音訊後對應影片待更新。驗證預設從總音訊按「製作 MP4」，整支使用一張圖片或一支背景影片，包含長短背景、靜音、比例與編碼情境，並能切換既有批次影片合併。

## Out of Scope

- EPUB 及其他電子書格式、小說／漫畫生成、聲音複製、語音模型訓練。
- YouTube 自動上傳、帳號權限、平台內容審核。
- 多使用者、雲端協作、手機與非 Windows 平台的首版交付。
- 手寫、嚴重模糊／破損、直排、多欄、複雜表格的辨識品質保證；仍可嘗試 OCR 並人工校對。自動去歪斜與複雜版面順序處理留後續。
- 自動移除重複頁首頁尾、智慧斷行／連字號清理的獨立功能；Gemini 對明顯錯誤提出需確認的校對建議仍在首版。
- Gemini 以外的 LLM、自動雙語切聲、角色／逐段配音、本機離線 TTS、其他語音提供者、WAV、逐字時間保證。
- 多本書自動排程、TXT 自動分章拆檔、單批次多背景素材時間軸、片頭／轉場特效、圖片平移縮放、背景原聲混音、字幕燒錄／樣式、9:16 輸出。同書多批次、交接停頓、總音訊／總字幕及兩種總影片製作路徑屬首版。

## Further Notes

- 本規格整合已核定的首版需求、A 版校對工作台原型選擇，以及總音訊與直接製片增補，對應需求規格 v0.7，遵守專案術語表及書籍批次、Windows 桌面、校對工作台與總音訊獨立製作的決策。
- 首版涵蓋 AC-01～AC-40。預設完整路徑為 PDF／TXT → 校對 → 批次 MP3／SRT → 總 MP3／SRT → 全片圖片／背景影片 → 總 MP4，另保留批次 MP4 合併。垂直切片是開發順序，不能將 PDF／OCR、Gemini、總音訊或任一影片路徑延至後續版本。
- 主要測試邊界沿用已確認的專案工作流程；總音訊、直接製片、按格式部分完成與版本失效均由同一公開操作流程驗證，不另增加對外測試入口。
- PDF／OCR 與語音品質需以代表性文件及實際試聽驗收；清晰橫排單欄不承諾所有掃描文件零錯字。音色以實際服務清單及試聽為準，中英混合單音色不保證雙語母語品質。
- 技術選型需符合本機保存、可取消續作、安全程序參數等已核定約束。語音節奏預設的最終人工試聽確認屬實作後驗收，不阻擋本規格作為開發依據。
