# 首版 ticket 拆分提案

來源：[核定 Spec #1](https://github.com/newesp/ebook2mp4/issues/1)。狀態：既有 21 張拆分尚未核准、未發佈子 issue；使用者已選 A 版並新增首版總音訊 MP3，待本輪 grill-with-docs 完成後重整合併切片與阻擋關係。以下仍是舊範圍草稿，不能直接發佈。

## 拆分原則

- 共 21 張垂直切片，各自交付可在 UI 操作、保存及驗證的功能；每張含對應行為測試，非單獨的資料庫／API／UI 工作。
- 目前沒有既有程式碼，無需另開 prefactor。首張以可操作的桌面 TXT 專案完成必要基礎與技術選型，PDF／OCR、Gemini、語音與影片都仍須在首版完成。
- 阻擋只列直接必要前置，不重複傳遞依賴；分支不因無關功能被迫等待。所有節點均通向 T21 的首版驗收。
- 取消／有限重試／任務快照／安全暫存與舊成品保護，由各產出功能當下交付；T19／T21 為使用者跨功能情境，不是把安全行為延到最後才補。
- 目前僅 T01 無阻擋；完成後 T02 與 T03 可分支。T03 之後 Gemini 與語音不需等待 PDF／OCR 全部完成。

## Proposed tickets

1. **T01 — 桌面建立書籍專案，匯入 TXT 並儲存重開**
   - **Blocked by**：無，可立即開始。
   - **What it delivers**：啟動 Windows 桌面程式，建立一本書的專案，匯入 UTF-8 TXT 成為第一個製作批次，查看內容與儲存位置，關閉後重新開啟仍可繼續。
   - [完整 ticket 草稿](../issues/01-desktop-book-project.md)

2. **T02 — 同書多 TXT 批次與編碼預覽**
   - **Blocked by**：T01。
   - **What it delivers**：在同一本書加入不同 TXT，各自成為獨立批次；可切換編碼預覽並回到任何已保存批次。
   - [完整 ticket 草稿](../issues/02-multiple-txt-batches-encodings.md)

3. **T03 — 人工校對、外部重載與朗讀稿確認**
   - **Blocked by**：T01。
   - **What it delivers**：在批次內完成搜尋取代與校對，匯出／重載 TXT，確認一份不可變的朗讀稿，後續修改會清楚取消目前確認。
   - [完整 ticket 草稿](../issues/03-proofread-confirm-reading-draft.md)

4. **T04 — PDF 預覽選頁，擷取文字成為校對批次**
   - **Blocked by**：T02、T03。
   - **What it delivers**：在書籍專案載入文字型 PDF，預覽並選定頁碼，擷取成可校對的批次，且可與 TXT 批次並存。
   - [完整 ticket 草稿](../issues/04-text-pdf-range-to-draft.md)

5. **T05 — OCR 語言模型安裝與掃描 PDF 轉 TXT**
   - **Blocked by**：T04。
   - **What it delivers**：選擇辨識語言，在介面下載所需模型，將清晰掃描 PDF 逐頁辨識為可對照、可校對的 TXT。
   - [完整 ticket 草稿](../issues/05-scan-pdf-ocr-models.md)

6. **T06 — 混合 PDF 自動辨識、異常頁確認與旋轉重試**
   - **Blocked by**：T05。
   - **What it delivers**：混合 PDF 逐頁判斷文字層或 OCR，檢查疑似漏正文的頁面，旋轉或重試，確認異常後才允許朗讀。
   - [完整 ticket 草稿](../issues/06-mixed-pdf-anomalies-retry.md)

7. **T07 — Gemini 設定、指定範圍校對與差異採用**
   - **Blocked by**：T03。
   - **What it delivers**：在工具內設定 Gemini，對批次全文或所選文字提出忠於原文的校對候選，逐段採用或拒絕並保留原稿。
   - [完整 ticket 草稿](../issues/07-gemini-settings-review.md)

8. **T08 — Gemini 長稿分段、取消與部分失敗續作**
   - **Blocked by**：T07。
   - **What it delivers**：長稿分段校對時能看到完成與失敗範圍，取消或重開後保留已完成候選，只重試失敗部分。
   - [完整 ticket 草稿](../issues/08-gemini-long-draft-resume.md)

9. **T09 — Edge-TTS 音色、語速與短文試聽**
   - **Blocked by**：T03。
   - **What it delivers**：選擇實際可用音色及語速，播放固定範例或所選校對內容，清楚知道文字將送到線上語音服務。
   - [完整 ticket 草稿](../issues/09-edge-voice-preview.md)

10. **T10 — 已確認朗讀稿產生批次 MP3／SRT**
   - **Blocked by**：T09。
   - **What it delivers**：將已確認批次朗讀稿依自然節奏完整合成，顯示進度並輸出可播放的 MP3 與正確時間軸 SRT。
   - [完整 ticket 草稿](../issues/10-confirmed-draft-mp3-srt.md)

11. **T11 — 自然／舒緩節奏與自訂句尾、段落停頓**
   - **Blocked by**：T10。
   - **What it delivers**：由介面比較自然與舒緩節奏，調整句尾與段落額外停頓，試聽及正式 MP3／SRT 使用相同設定。
   - [完整 ticket 草稿](../issues/11-reading-rhythm-settings.md)

12. **T12 — 語音斷網、取消及重開後重用有效區塊**
   - **Blocked by**：T10。
   - **What it delivers**：長篇語音途中斷網或取消，重開專案能看到中斷狀態，續作只處理尚未成功的區塊。
   - [完整 ticket 草稿](../issues/12-audio-interruption-resume.md)

13. **T13 — 全書語音預設與局部改稿增量合成**
   - **Blocked by**：T02、T11、T12。
   - **What it delivers**：同書批次可沿用或覆寫語音預設，修改部分校對稿後只重做失效語音；舊成品清楚標待更新。
   - [完整 ticket 草稿](../issues/13-incremental-audio-book-defaults.md)

14. **T14 — 圖片預覽與批次 MP4 輸出**
   - **Blocked by**：T10。
   - **What it delivers**：選擇一張 JPEG／PNG，預覽畫面，以已有有效音訊輸出批次 MP4 與同時間軸 SRT。
   - [完整 ticket 草稿](../issues/14-image-to-batch-video.md)

15. **T15 — 背景 MP4 裁切、循環與最後一格定格**
   - **Blocked by**：T14。
   - **What it delivers**：以一支背景 MP4 製作批次影片，背景較長則裁切，較短可循環或停在最後一格，完整保留單次旁白。
   - [完整 ticket 草稿](../issues/15-background-video-duration.md)

16. **T16 — 選取批次合併總 MP4／SRT，預設交接 0.5 秒**
   - **Blocked by**：T02、T14。
   - **What it delivers**：選取同書多個有效批次 MP4，調整順序與總解析度，合併成帶總字幕及預設 0.5 秒交接停頓的總影片。
   - [完整 ticket 草稿](../issues/16-merge-batches-total-video.md)

17. **T17 — 交接停頓調整、接點預覽與頁碼銜接檢查**
   - **Blocked by**：T04、T16。
   - **What it delivers**：在合併畫面調整交接停頓並預覽接點，檢查 PDF 頁碼重疊／缺口及跨批半句，再決定排序或返回校對。
   - [完整 ticket 草稿](../issues/17-merge-join-preview-and-page-warnings.md)

18. **T18 — 批次更新後追蹤總影片待更新狀態**
   - **Blocked by**：T13、T16。
   - **What it delivers**：清楚辨識每份批次與總影片使用的文字及設定版本，只有實際選入內容變更才使相關總影片待更新。
   - [完整 ticket 草稿](../issues/18-output-version-dependencies.md)

19. **T19 — 搬移完整書籍專案後繼續製作**
   - **Blocked by**：T08、T15、T18。
   - **What it delivers**：完成多批次與總影片後，將整個專案資料夾搬到新位置，仍可檢查、校對、續作或重建成品；缺少檔案會被明確列出。
   - [完整 ticket 草稿](../issues/19-portable-book-project-resume.md)

20. **T20 — 乾淨 Windows 安裝與內附處理工具**
   - **Blocked by**：T05、T15。
   - **What it delivers**：在沒有開發環境、FFmpeg 或 OCR 引擎的 Windows 電腦安裝後，從介面準備模型並完成製作，不需輸入命令。
   - [完整 ticket 草稿](../issues/20-clean-windows-installer.md)

21. **T21 — 代表性長篇完整製作與首版驗收**
   - **Blocked by**：T06、T17、T19、T20。
   - **What it delivers**：用代表性中英文文件從雙入口完成分批製作及總影片，通過長篇規模、朗讀品質與故障恢復的首版驗收，修正阻止通過的問題。
   - [完整 ticket 草稿](../issues/21-first-release-long-book-acceptance.md)

## 覆蓋與檢核

- 核定 spec 的 95 則使用者故事全部有對應 ticket。
- AC-01～AC-35 均有功能 ticket 承接，不只依賴最終驗收張。
- 依賴圖無循環、無指向後續張、無重複傳遞阻擋邊；共 32 條直接阻擋邊。
- 詳細草稿各自保存為一份檔案，尚不代表已獲發佈同意。

## 待確認

1. 粒度是否合適，是否有過粗或過細的 ticket？
2. 阻擋是否只保留真正必要的前置，是否應刪除或補上任何邊？
3. 是否有要合併或再拆開的 ticket？

## 確認後的發佈方式

- 依依賴順序建立 GitHub 子 issue，套 ready-for-agent，Parent 指向 Spec #1。
- 優先使用 GitHub 原生 sub-issue 與 blocked-by 關係；原生能力確實不可用時，才使用 issue 本文引用作後備。
- 發佈時以實際建立後的 issue 編號與資料庫識別設定關係，不能把 T 編號當成 GitHub issue 編號。
- Spec #1 的標題、本文、標籤及開啟狀態均不改動；只建立所需子項關係。
- 實作依 frontier：僅開放所有 blockers 都完成的 ticket。
