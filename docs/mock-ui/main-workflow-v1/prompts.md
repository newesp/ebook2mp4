# 主介面草圖提示詞

使用內建 image_gen，兩張均為新產生的圖片；不涉及程式實作或影像後製。

## 校對畫面

Create a polished high-fidelity UI proposal image for the MAIN WINDOW of an existing Windows desktop audiobook manuscript workbench. This is not a website and not a TTS settings dialog. Flat straight-on full application screenshot-style illustration, landscape 1800x1150 or similar, all edges visible, no perspective or surrounding desk. All UI language Traditional Chinese (Taiwan), clear legible Microsoft JhengHei-style sans serif. Calm native productivity aesthetic: off-white canvas #f5f6f2, warm paper source #fffef9, white editable manuscript, dark forest ink #263d34, primary green #315d43, thin gray-green #dfe5dd dividers, near-square corners, no gradients/glass/hero marketing. Strong visual hierarchy through alignment and readable sizes. Small annotation in top bar "主介面提案 A｜示意資料". No application code, just a design image.

CRITICAL USER GOAL: intuitive LEFT-TO-RIGHT then TOP-TO-BOTTOM sequence. Show the proofreading stage of a four-step workflow. A clear full-width horizontal progress navigation near the top: "1 匯入來源" completed with check, arrow, "2 校對文字" active green, arrow, "3 確認朗讀稿" pending, arrow, "4 試聽與製作" pending. These are NAVIGATION STEPS, not four repeated large cards. Keep only step2 content visible. Steps3/4 visually quiet rather than marked as already completed.

Windows titlebar "書籍製作工作台 — ebook2mp4" with standard window controls. Header below titlebar: book title "靈性開悟" at left, small "書籍專案" descriptor, and small text menus aligned right "專案 ▾" "版本與匯出 ▾" "服務設定 ▾". Do NOT scatter primary save buttons in this global header.

Main content below progress navigation:
LEFT slim batch rail about17% width, separate from work area by fine divider. Header "製作批次". Prominent modest outline button "+ 新增 PDF／TXT 批次". Then three stacked batch rows, first selected in light green with green left line: "第 1 批 · 第 1–9 頁" with status "校對中"; second "第 2 批 · 第 10–18 頁" status "待校對"; third "第 3 批 · 第 19–27 頁" status "已確認". Small secondary "批次管理 ▾" at bottom of rail. No file tree clutter.
RIGHT large work area83% width. Header "第 1 批 · 校對文字". Under it, a compact toolbar ordered left-to-right: "PDF 原頁對照" "換行整理…" "AI 校對（選用）…" a flexible gap then "搜尋／取代…" and "字級 14 ▾". Tiny helper directly below "先看左側原文，再修改右側校對稿；AI 候選需審閱後採用。".
Under toolbar, TWO equal spacious manuscript panes side-by-side occupying most of window height. LEFT heading "擷取原文 · 唯讀". RIGHT heading "校對稿 · 可編輯" with subtle outlined text button "復原". Thin scrollbars at far right of each text pane. Render readable short ORIGINAL SYNTHETIC sample text, NOT a real book excerpt:
Left pane paragraphs:
"這是一個關於專注與覺 察的練習。"
"當我們把注意力放回呼吸，\n也開始注意到當下的感受。"
"不需要急著找到答案。先停下來，\n讓自己看清楚眼前的事情。"
Right pane matching corrected text:
"這是一個關於專注與覺察的練習。"
"當我們把注意力放回呼吸，也開始注意到當下的感受。"
"不需要急著找到答案。先停下來，讓自己看清楚眼前的事情。"
Subtle light green highlight only around corrected "覺察" and joined line. Generous text padding and line height; not giant empty cards.

Full-width bottom action area below panes but to the right of batch rail, separated by thin line. Read from LEFT to RIGHT: small status "來源異常：0 項未處理" with a check; amber dot "有未儲存的修改"; outline secondary "只儲存校對稿"; on far right a SINGLE strong primary dark green button "儲存並前往確認 →". Under status a muted helper "下一步會核對朗讀稿，不會直接產生音訊。". Do not show a confirmation checkbox in this stage. Bottom-most quiet application footer: "目前：第 1 批 · 校對稿 v3" left and text button "訊息記錄" right.

Do NOT include an always-visible right sidebar of edit/AI/confirmation tabs. Do NOT include video creation features that are unimplemented. Do NOT hide key next actions in menus. Keep main proofreading path clear: left batch selection, center source, right draft, down to explicit save-and-next. Accurate Chinese text and no overlapping/clipping.

## 朗讀稿確認

Create a second high-fidelity Windows desktop main-workbench UI proposal, as a follow-on state to a manuscript proofreading screen. Flat straight-on complete app window, landscape 1800x1150 or similar. Traditional Chinese Taiwan text, crisp legible Microsoft JhengHei-like sans serif. Calm native productivity styling: #f5f6f2 off-white canvas, #fffef9 warm read-only paper, #ffffff surfaces, dark green #315d43, ink #263d34, fine #dfe5dd dividers, nearly square corners. No perspective, photography, gradients, glass, dashboard charts or marketing imagery. This is a static proposal, not an implemented app; small top annotation "主介面提案 A｜確認步驟示意".

Windows titlebar "書籍製作工作台 — ebook2mp4" with standard window buttons. Application header left "靈性開悟" with muted "書籍專案"; right small menus "專案 ▾", "版本與匯出 ▾", "服務設定 ▾".
Below a full-width four-step navigation bar left-to-right: "1 匯入來源" completed check, arrow, "2 校對文字" completed check, arrow, "3 確認朗讀稿" selected dark green, arrow, "4 試聽與製作" quiet pending. This is a navigation strip, not giant cards.

Main body LEFT batch rail 17% width: heading "製作批次", outline button "+ 新增 PDF／TXT 批次", three batch entries. First selected light green: "第 1 批 · 第 1–9 頁" with amber dot "待確認". Second "第 2 批 · 第 10–18 頁" "待校對". Third "第 3 批 · 第 19–27 頁" "已確認". Bottom of rail "批次管理 ▾".

Remaining83% is the confirmation workspace. Heading "確認這份內容可以用於朗讀". Helper directly below "核對內容與版本後，再確認朗讀稿；這一步不會傳送文字或產生音訊。".
Under this, LEFT large paper preview 68% of workspace width and RIGHT tidy review summary32%, separated by a simple divider. No always-visible AI or edit toolbox here.
Preview header "待確認內容 · 校對稿 v3" and small badge "唯讀預覽". Large readable text with generous padding and line height:
"這是一個關於專注與覺察的練習。"
"當我們把注意力放回呼吸，也開始注意到當下的感受。"
"不需要急著找到答案。先停下來，讓自己看清楚眼前的事情。"
Thin vertical scrollbar. No green correction highlights in this preview because it is a clean final reading preview.
Right summary heading "確認前檢查". Three simple separated check rows:
green check "校對稿已儲存", secondary "目前版本：v3"
green check "來源異常已處理", secondary "0 項未處理"
outlined neutral clock circle "朗讀稿尚未確認", secondary "按下確認後，才建立本次朗讀稿"
Below a restrained pale-paper note "之後若修改校對稿，需重新確認朗讀稿。". Below it small text "內容需要調整？" and an outline secondary button "返回校對文字".
Do NOT include an extra acknowledgement checkbox. Confirmation is a deliberate clearly named primary action, not an additional repetitive consent gate.

Bottom of workspace is a fixed full-width action band separated by line. Left helper "下一步：選擇 TTS 服務與聲音，先用短文試聽。". Right SINGLE strong dark green primary button with accurate text "確認朗讀稿並前往語音設定 →". Enough width for the text without cropping. Small secondary note below the left helper "可先試聽；正式製作需有已確認的朗讀稿。". Application bottom footer "目前：第 1 批 · 待確認" on left and "訊息記錄" on right.

Keep typography consistent, controls aligned and spacious but not wastefully huge. Readable entire screen with all actions visible, no clipping or overlapping. The visual must make step3 an understandable review step between proofreading and voice testing, preserving the clear left-to-right top-to-bottom journey.

