# AI 校對與 OCR 優化

2026-10-26，使用者核定實作先前兩份評估：`docs/proofreading-normalization-proposal.md`、`docs/ocr-mixed-font-evaluation.md`。起點 `41f79f6`。沿用 ProjectWorkflow／真實 Tk 核定測試邊界；T08 長稿分請求／部分續作不在此次範圍。

## 校對政策

- 預設本批全文在本機計算可區分繁／簡的字元次數，至少 4 票且一方占 80% 才自動統一；不足或接近則保留原字體。共用漢字不投票，網址／程式碼等保護片段不投票。可指定繁體、簡體、保留原樣；中文標點有獨立開關。
- 本機 OpenCC `s2t`／`t2s` 詞庫只處理候選，不替換地區用語。中文標點按中文相鄰字／成對引號括號處理；保護網址、Email、小數、版本／檔名、縮寫與程式碼，英文段落不全形化。繁體引號用「」／『』，簡體用“”／‘’。有歧義仍需人工確認。
- 共用／歧義字由 OpenCC ST／TS 字典的 self-alternative 排除，例如公里的「里」、皇后的「后」均不投票。英文詞內撇號不配對，中文省略號作整組處理。保護片段以佔位符跨越引號仍維持原樣；若雲端模型先改動受保護識別文字，拒絕該次候選而不覆寫稿件。
- `gemini_scope`／`start_gemini_review` 新增 script=`auto|traditional|simplified|preserve`、punctuation=bool。範圍、政策及證據數量在送出前顯示，政策附候選保存。雲端仍只收所選文字與校對規則；全文判斷不額外上傳選外內容。採用／拒絕／撤回、舊稿衝突及朗讀重新確認規則沿用。

## OCR 診斷與實作

- 原 PDF 第一頁用舊繁中＋英文／psm6 重現 **`1. FR Pu Al`**；簡中＋英文／psm6 能讀回 **`1. 再简单也不过了`**。原始原因之一是模型與原字形不一致，不是靠 AI 從字母猜書名。
- 新語言選項「自動中英」使用既有固定 SHA-256 的 chi_sim、chi_tra、eng 模型，總大小 8,948,886 bytes。兩組中英模型比較信心及可疑短行；選定模型／版面／信心指標附逐頁設定保存。
- layout=`auto|block|line` 對應自動版面／單區塊／單行標題。auto 比較 psm3／6；較弱的同位置文字行只有在另一版面信心高至少 10、且框重疊至少 65% 時才替換，保持閱讀順序，沒有跨模型擅自拼字體。信心指標不是正確率保證。
- 中文頁中的短拉丁字母串（如本例）標 pending；平均信心低於 60 也標 pending，仍須處理／明確保留才能確認朗讀稿。真正英文不被禁用或刪除。
- `start_pdf_retry` 新增 layout、region 正規化圖片座標、text_range 原逐頁文字半開範圍。必須單頁、有效框選與反白原文；先產生區域候選，只取代所選原文，其他逐頁文字不動。區域比較裁切與整頁上下文辨識，按實際區域信心挑選；整頁結果僅取框內字詞，不搬入其他區文字。UI 框選沿用目前顯示的旋轉方向，文字反白必須在「本次文字」。
- 沿用新批次採用，原批人工全文與歷史快照保持；區域失敗／取消保留原逐頁文字，不以空區域覆蓋。全頁重試與只重試失敗頁仍可用。
- 區域候選一律待整頁確認，不能因只修標題就宣稱原頁其他異常消失；合併後重新檢查可疑英文短行。Tesseract TSV 以 literal quoting=NONE 解析，英文字詞內引號不能吞入下一行的座標欄位。

## 實驗限制與資料

使用者 412×228 截圖單獨辨識仍有錯字；裁切／單行及額外 13,077,423-byte tessdata_best 簡中模型都未穩定恢復完整標題，因此未將額外模型納入產品。低解析圖的正確結果不可承諾，現在會保留低信心／可疑結果供檢查。原 PDF 的大標題與頁腳重複，正式案例檢查引文後、正文前的大標題或對應圖片區域，不能只查全頁含某字串。

預設使用者介面改自動中英＋自動版面；公開 API 預設仍 block 與既有語言，以保留原流程。自動比較增加辨識成本，單頁共用 120 秒期限、每個程序均可取消並 kill/communicate，暫存頁圖在 finally／TemporaryDirectory 釋放。所有圖片處理留本機。

參考：[Tesseract 官方品質指引](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html)、[OpenCC Python 套件](https://pypi.org/project/opencc-python-reimplemented/)。詞庫依賴固定 0.1.7，封裝含詞庫、設定、metadata 及 [授權](../../packaging/NORMALIZATION-NOTICES.md)。

## 真實驗收

[原始記錄](optimization-real.json)：Gemini `gemini-3.8-flash` 僅收到合成選取短文。自動繁體政策（56／5 票）產出「這裏有頭髮，請檢查（文字）。」，自動簡體政策（6／48 票）產出「这里有头发，请检查（文字）。」；各保留相同網址、數字及 `U.S.A.`，選外不變、明確採用與撤回通過。兩次分別 1.788、1.795 秒。

原 PDF 僅本機 OCR：舊模式大標題 `1. FR Pu Al` 現標待檢查；新自動中英＋自動版面取得 `1. 再 简单 也 不 过 了`（字詞正確，保留辨識分詞空格），選中 chi_sim+eng 並有 1 行版面回退。實測信心指標 88.59 是引擎比較資訊，不等於正確率。完整正文仍需人工校對，沒有宣稱全部無錯字。

## 雙軸審查

固定 `41f79f6f95d03ff149890f77c234b1b80aff4541`，實作 `e05c121`，修正 `9906504`，比較 `git diff 41f79f6...HEAD`。兩位獨立子代理依 code-review 技能分別審 Standards（AGENTS、GLOSSARY、ADR、README、Testing Decisions 與 Fowler 氣味基線）及 Spec（本次核定兩份提案、Spec v1.2 及本文政策）。

### Standards

初審四項 P2：TSV 預設引號誤解析、指定語言 block 區域跳過比較、中文檔名路徑保護不足、英文撇號被錯當引號。`9906504` 全數修正，原審查者獨立重跑公開工作流程 7／7 與真實 Tk 2／2，確認解除，沒有新增項目。

### Spec

初審三項 P2：共用漢字誤投票、英文撇號／中文省略號被誤改、區域合併未重查可疑行而錯報成功。原審查者複查修正並重跑 7／7 正規化案例，確認解除；模型擅改保護片段亦安全拒絕。

Standards：0 項未解決；Spec：0 項未解決。

## 最終結果與交付

- 完整套件 **90／90 通過，169.405 秒，無跳過**，含三語真實 OCR、指定 9 頁書稿、原頁大標題與區域重辨。[原始結果](optimization-tests.txt)。初次全套因舊 UI 測試誤選主視窗新增下拉選單而失敗，已將定位限定「匯入前預覽」並單測／完整重跑，沒有修改產品匯入邏輯。
- mypy 10 個來源檔案通過，[型別紀錄](optimization-typecheck.txt)；compileall 通過。新 normalizer 公開工作流程 7 案、真實 Tk 優化 2 案、真實 OCR 優化 5 案均包含於完整套件。
- 原生 Tk 在 740×570 差異／PDF 視窗驗證設定、拖曳框選、原文反白、候選與操作列界線。主視窗沿用可捲動工具區；新增設定不擠壓中間書稿。PDF 設定可收合，區域操作另起一列，左右圖文可捲動。未使用瀏覽器；其他 DPI、輔助工具及封裝版原生完整操作仍待人工補驗。
- [PyInstaller 建置](optimization-build.txt) 成功。新版 **`dist/T07-optimized/ebook2mp4/ebook2mp4.exe`**，SHA-256 **`39A1B3AA1E33ECD93F1B4A0592F2C4DB12AE701A7E0949E3850A1E216AD5B378`**，搬移需帶整個 ebook2mp4 目錄。從包內 `_internal/opencc` 實際載入轉換器，驗證「头发」→「頭髮」及證據字典存在；不是僅檢查檔案名稱。
- 本次不搶占使用者桌面啟動封裝 GUI。舊正式成品、outputs 與既有使用者 OCR 模型保留；清理與程序／檔案釋放見 [清理紀錄](optimization-cleanup.json)。

重跑需依固定 requirements 準備隔離工具，設 PYTHONPATH、可寫 TEMP／TMP、三語 EBOOK2MP4_REAL_OCR_HOME／EBOOK2MP4_OCR_HOME、包內 EBOOK2MP4_TESSERACT 及原指定 EBOOK2MP4_BOOK_PDF。`python -m unittest discover -s tests -v`；型別用 `python -m mypy ebook2mp4 --check-untyped-defs`。`tests/optimization_real_check.py` 為 opt-in，需明確設定金鑰才執行真實合成短文連線；不在預設測試中默默花用服務額度。
