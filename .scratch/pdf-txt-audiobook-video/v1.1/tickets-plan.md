# Spec v1.1：首版 tickets 更新提案

來源：[核定 Spec #1](https://github.com/newesp/ebook2mp4/issues/1)，版本 1.1；需求驗收 AC-01～AC-40。狀態：**24 張草稿，待使用者確認拆分，尚未發佈 GitHub 子 issues**。本提案取代原本未核准的 21 張；原 issues 目錄只保留歷史，新票稿唯一來源為 v1.1/issues 及目前 tickets.json。

## 拆分與依賴原則

- 每張交付可由 UI 操作、保存／重開並驗證的完整使用者流程，包含必要行為測試；不另開純資料層／API／畫面票。
- 首版包含 PDF／OCR 與 TXT 雙入口、Gemini、語音及兩種影片路徑，票號只表示開發相依順序，不表示分期縮減首版。
- 沿用 A 版校對工作台；原型只作參考。當前無正式應用程式，無需先做 prefactor；必要選型隨 T01 落實。
- 總音訊 T14 不被任何影片功能阻擋；T16／T17 可用既有總 MP3／SRT 直接製片，開發依賴與執行時需要的成品分別列清楚。
- T18 重用已驗證的圖片／背景製片能力，但執行時只要批次音訊，不需總音訊。T19 是可切換的批次影片合併，不是預設製片前置。
- 每種產出在首次交付時即包含必要來源版本、快照、錯誤、取消及安全發布；T20 完成跨路徑連動，T21 完成逐格式協調，不將基本保護延到最後。
- 只列真正必要的直接 blockers，不重複傳遞邊；T24 是安裝版完整情境交付及缺陷修正。

## Proposed tickets

1. **T01 — 桌面建立書籍專案，匯入 TXT 並儲存重開**
   - **Blocked by**：無，可立即開始。
   - **What it delivers**：啟動 Windows 桌面程式，建立一本書的專案，匯入 UTF-8 TXT 成為第一個製作批次，查看內容與儲存位置，關閉後重新開啟仍可繼續。
   - [完整票稿](issues/01-desktop-book-project.md)

2. **T02 — 同書多 TXT 批次與編碼預覽**
   - **Blocked by**：T01。
   - **What it delivers**：在同一本書加入不同 TXT，各自成為獨立批次；可切換編碼預覽並回到任何已保存批次。
   - [完整票稿](issues/02-multiple-txt-batches-encodings.md)

3. **T03 — 人工校對、外部重載與朗讀稿確認**
   - **Blocked by**：T01。
   - **What it delivers**：在批次內完成搜尋取代與校對，匯出／重載 TXT，確認一份不可變的朗讀稿，後續修改會清楚取消目前確認。
   - [完整票稿](issues/03-proofread-confirm-reading-draft.md)

4. **T04 — PDF 預覽選頁，擷取文字成為校對批次**
   - **Blocked by**：T02、T03。
   - **What it delivers**：在書籍專案載入文字型 PDF，預覽並選定頁碼，擷取成可校對的批次，且可與 TXT 批次並存。
   - [完整票稿](issues/04-text-pdf-range-to-draft.md)

5. **T05 — OCR 語言模型安裝與掃描 PDF 轉 TXT**
   - **Blocked by**：T04。
   - **What it delivers**：選擇辨識語言，在介面下載所需模型，將清晰掃描 PDF 逐頁辨識為可對照、可校對的 TXT。
   - [完整票稿](issues/05-scan-pdf-ocr-models.md)

6. **T06 — 混合 PDF 自動辨識、異常頁確認與旋轉重試**
   - **Blocked by**：T05。
   - **What it delivers**：混合 PDF 逐頁判斷文字層或 OCR，檢查疑似漏正文的頁面，旋轉或重試，確認異常後才允許朗讀。
   - [完整票稿](issues/06-mixed-pdf-anomalies-retry.md)

7. **T07 — Gemini 設定、指定範圍校對與差異採用**
   - **Blocked by**：T03。
   - **What it delivers**：在工具內設定 Gemini，對批次全文或所選文字提出忠於原文的校對候選，逐段採用或拒絕並保留原稿。
   - [完整票稿](issues/07-gemini-settings-review.md)

8. **T08 — Gemini 長稿分段、取消與部分失敗續作**
   - **Blocked by**：T07。
   - **What it delivers**：長稿分段校對時能看到完成與失敗範圍，取消或重開後保留已完成候選，只重試失敗部分。
   - [完整票稿](issues/08-gemini-long-draft-resume.md)

9. **T09 — Edge-TTS 音色、語速與短文試聽**
   - **Blocked by**：T03。
   - **What it delivers**：選擇實際可用音色及語速，播放固定範例或所選校對內容，清楚知道文字將送到線上語音服務。
   - [完整票稿](issues/09-edge-voice-preview.md)

10. **T10 — 已確認朗讀稿產生批次 MP3／SRT**
   - **Blocked by**：T09。
   - **What it delivers**：將已確認批次朗讀稿依自然節奏完整合成，顯示進度並輸出可播放的 MP3 與正確時間軸 SRT。
   - [完整票稿](issues/10-confirmed-draft-mp3-srt.md)

11. **T11 — 自然／舒緩節奏與自訂句尾、段落停頓**
   - **Blocked by**：T10。
   - **What it delivers**：由介面比較自然與舒緩節奏，調整句尾與段落額外停頓，試聽及正式 MP3／SRT 使用相同設定。
   - [完整票稿](issues/11-reading-rhythm-settings.md)

12. **T12 — 語音斷網、取消及重開後重用有效區塊**
   - **Blocked by**：T10。
   - **What it delivers**：長篇語音途中斷網或取消，重開專案能看到中斷狀態，續作只處理尚未成功的區塊。
   - [完整票稿](issues/12-audio-interruption-resume.md)

13. **T13 — 全書語音預設與局部改稿增量合成**
   - **Blocked by**：T02、T11、T12。
   - **What it delivers**：同書批次可沿用或覆寫語音預設，修改部分校對稿後只重做失效語音；舊成品清楚標待更新。
   - [完整票稿](issues/13-incremental-audio-book-defaults.md)

14. **T14 — 共用全書合併設定，產生總 MP3／SRT**
   - **Blocked by**：T02、T10。
   - **What it delivers**：選取同書有效批次 MP3，保存共用選取與順序，以預設額外交接 0.5 秒合併總 MP3／SRT；沒有圖片或批次 MP4 也能完成。
   - [完整票稿](issues/14-total-audio-shared-assembly.md)

15. **T15 — 調整交接停頓、試聽接點及檢查頁碼銜接**
   - **Blocked by**：T04、T14。
   - **What it delivers**：將交接額外停頓調為 0～5 秒，試聽前後批次並對照文字；遇 PDF 重疊、缺頁或半句銜接時可自行決定或返回校對。
   - [完整票稿](issues/15-audio-join-preview-page-warnings.md)

16. **T16 — 從總 MP3／SRT 加圖片直接製作總 MP4**
   - **Blocked by**：T14。
   - **What it delivers**：在有效總音訊成品按「製作 MP4」，加入一張圖片並預覽，直接產生總 MP4；不必先有任何批次影片。
   - [完整票稿](issues/16-total-audio-image-to-video.md)

17. **T17 — 總音訊搭配背景影片的裁切、循環與定格**
   - **Blocked by**：T16。
   - **What it delivers**：把總影片的全片素材換成一支背景 MP4，較長時裁切、較短時循環或定格，保留總音訊及其時間軸。
   - [完整票稿](issues/17-total-audio-background-video.md)

18. **T18 — 以批次 MP3／SRT 製作批次 MP4**
   - **Blocked by**：T17。
   - **What it delivers**：每個批次也可使用自己的圖片或背景影片製作 MP4，沿用已完成的媒體行為，無須先合併總音訊。
   - [完整票稿](issues/18-batch-audio-to-video.md)

19. **T19 — 切換合併既有批次影片，產生總 MP4／SRT**
   - **Blocked by**：T15、T18。
   - **What it delivers**：切換到「合併既有批次影片」，沿用全書合併設定，將含不同畫面的有效批次 MP4 接成總影片。
   - [完整票稿](issues/19-merge-existing-batch-videos.md)

20. **T20 — 依來源路徑追蹤總音訊與總影片版本**
   - **Blocked by**：T13、T19。
   - **What it delivers**：針對總 MP3、總音訊製片及批次影片合併分別標示來源版本與待更新狀態，避免無關修改使有效成果失效。
   - [完整票稿](issues/20-route-specific-output-versions.md)

21. **T21 — 逐格式完成、列缺項與只重試未完成輸出**
   - **Blocked by**：T19。
   - **What it delivers**：選擇總 MP3、總 MP4 或兩者；一種缺項或失敗時保留另一種成功成果，整體顯示部分完成並只重試未完成格式。
   - [完整票稿](issues/21-per-format-partial-success-retry.md)

22. **T22 — 搬移書籍專案後保留校對、進度與各路徑成果**
   - **Blocked by**：T08、T20、T21。
   - **What it delivers**：將整個專案資料夾搬移後，繼續校對、合併總音訊或從既有總 MP3 製片，仍保留版本關係與逐格式進度。
   - [完整票稿](issues/22-portable-book-project-all-outputs.md)

23. **T23 — 乾淨 Windows 安裝與內附媒體、OCR 工具**
   - **Blocked by**：T05、T18。
   - **What it delivers**：在沒有開發工具的 Windows 安裝後，從介面準備 OCR 模型並完成音訊與影片製作，不需輸入命令。
   - [完整票稿](issues/23-clean-windows-installer.md)

24. **T24 — 代表性長篇雙入口完整製作與首版交付**
   - **Blocked by**：T06、T22、T23。
   - **What it delivers**：交付經真實長篇及故障情境驗證的 Windows 首版，從 PDF／OCR 或 TXT 完成校對、音訊及兩種總影片路徑，修正阻擋驗收的問題。
   - [完整票稿](issues/24-first-release-long-book-acceptance.md)

## 覆蓋與檢核

- 共 24 張、35 條直接阻擋邊，無循環、無後向錯序依賴、無重複傳遞邊。
- Spec 的 101 則故事與 AC-01～AC-40 都有功能票承接，不僅列在 T24；所有前置節點都通向首版交付。
- [逐項對應與依賴檢核](coverage.md)。這是文件／依賴檢核，尚非產品功能驗收結果。

## 待確認

1. 這 24 張的粒度是否合適，有沒有過粗或過細？
2. Blockers 是否只保留真正必要前置，有沒有要增減的相依？
3. 是否有要合併或再拆開的票？

## 核准後的發佈方式

- 使用目前 tickets.json 中的 v1.1 票稿，依依賴順序建立 GitHub 子 issue，套 ready-for-agent，Parent 指向 Spec #1。
- 優先建立原生 sub-issue 及 blocked-by 關係；僅原生阻擋關係不可用時退回本文引用。
- 以實際新 issue 編號／資料庫識別設定關係；T 編號僅是此提案的代號。
- 不關閉或改寫 Spec #1 的標題、本文、標籤或狀態；只建立核准所需的子項關係。
- 執行 frontier：僅拿所有 blockers 已完成的票。依 skill「Iterate until the user approves the breakdown.」，拆分未核准前不發佈。
