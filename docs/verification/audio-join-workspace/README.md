# 檢查接點模組化 UI：實作與驗收

2026-11-12。使用者已指示「根據設計圖開始實作」，核准 [設計提案](../../ui-review/v2-audio-joins/README.md) 的範圍。依 [frontend-visual-qa](C:/Users/Administrator/.codex/skills/frontend-visual-qa/SKILL.md)、根目錄 [檢查清單](../../../check-list.md)、[元件規範](../../ui-components.md) 與 [捲動門檻](../../ui-scroll-qa.md) 實作與驗收。逐項結果見 [本輪檢查表](check-list.md)。

AudioJoinWorkspace／JoinTextPane 持有音訊接點頁的父層布局，JoinPage 保留工作及保存命令。左右校對位於各自標頭；設定與播放同列、依左右閱讀區的欄線對齊。警告詳情依閱讀預算內嵌或切換同宿主內容，文件列表在窄版切換同宿主；返回保留焦點及閱讀位置。全域 footer 由接點模組啟用，其他頁的操作不常駐，沒有重複返回或保存入口。

## 布局對照

| 核准布局／操作分組／空間 | 原生實作 | 可觀察驗收 |
|---|---|---|
| 接點選擇與等寬前後導航同列 | AudioJoinWorkspace 的 selection 列 | 選接點 → 確認左右來源同步變更 |
| 等寬對照文字，校對在各自標頭，與文字相距 8 | ReadonlyJoinPane；兩欄 uniform grid | 比較前後區 → 確認同高與齊頭 → 確認校對入口在區域標頭 |
| 停頓／長度／播放／停止同列、同尺寸角色 | 設定列與右欄播放群組共用欄線 | 量測同列外框 → 確認差 ≤2、動作間距 4 |
| 詳情依閱讀預算內嵌或切換內容頁 | 有界 details pane；比較區不重建 | 展開 → 縮小 → 收合 → 確認閱讀位置不變 |
| 窄版文件列表在同宿主切換 | 同宿主文件列表視圖及返回入口 | 開文件列表 → 返回 → 確認接點、欄位、確認及焦點保留 |
| 固定警告帶與返回／儲存底列 | JoinWorkspace footer；無外層捲動 | 捲動左右文字 → 確認主要操作不動 |
| 空／準備／播放／失敗／取消 | 同位置替換狀態與操作；準備鎖定衝突命令 | 準備 → 取消／離頁 → 確認不播放過期結果 |

## 功能契約（與布局分開）

保留音訊來源、接點 metadata、真實媒體預覽、全書停頓解析、逐接點確認、保存及校對返回。未確認警告可保存設定，但合併受阻擋。播放後的字幕內容種類與 playing 旗標分開。準備中取消／離頁不能產生過期覆寫；播放時修改停頓先停止舊片段。影片接點布局保持既有分支。更完整的保留契約見核准設計。

## 功能回歸

以下為不同層次的結果，不用測試數量代替 UI 驗收。

| 範圍 | 結果與證據 |
|---|---|
| 停頓、試聽、字幕時間軸、警告與來源版本 | [8 項媒體回歸通過](media-regressions.txt)，使用真實 FFmpeg、合成語音 fixture |
| 詳情／文件切換、閱讀位置、保存失敗與字幕標示 | [3 項針對性回歸通過](final-checks.txt)；未確認警告不自動勾選 |
| 文件選取接回原 Workbench 命令、原生尺寸、跨書返回 | [3 項回歸通過](final-layout-files.txt) |
| 最終尺寸與離頁取消 | [2 項回歸通過](final-layout.txt)，包括取消後不播放晚到結果 |
| 警告逐一確認、保存失敗、準備鎖定、既有影片接點及語音頁間距 | [7 項共用區域回歸通過](shared-busy-regressions.txt) |
| 捲動四種內容長度 | [原生四區回歸通過](scroll-regression.txt)，量測資料見 [native-scroll.json](native-scroll.json) |
| 最大化及三尺寸／兩字級 | [原生補驗通過](maximized-regression.txt) |
| 詳情展開後改選其他接點 | [接點識別回歸](join-identity-regression.txt)：前接點的捲動位置不套到新接點 |

早期整批回歸的媒體錯誤來自未指定測試所需的 EBOOK2MP4_FFMPEG，已以固定工具路徑重跑媒體 8 項並通過；早期關閉階段的 Tk 回呼錯誤已加上存活／關閉檢查並針對返回與關閉重驗。舊失敗紀錄保留於 functional-regressions.txt，不作最終通過證據。新增測試以真實父層幾何與狀態契約攔截回歸，不只檢查控制項存在。

## 原生布局與 mock 對照

見 [七種原生狀態與外框量測](native-visual.json)、[逐尺寸數值與針對性缺陷](native-layout-regression.json)。原尺寸圖：

- [1360 正常](native-1360x820-10pt.png)、[1360 詳情展開](native-1360x820-10pt-expanded.png)。
- [1280 正常](native-1280x720-10pt.png)、[900 正常](native-900x640-10pt.png)、[900 詳情](native-900x640-10pt-expanded.png)。
- [900 放大文字](native-900x640-13pt.png)、[900 放大文字詳情](native-900x640-13pt-expanded.png)。
- [最大化](native-maximized.png)、[準備中](native-preparing.png)、[保存失敗](native-save-failed.png)。

原生設定／播放欄位皆 120px 寬；一般控制高 37、13pt 高 42，組內寬高差 0。校對同組 128px 寬；前後導航 112px；主保存 196px。原生邊框、內距與字型請求高度沿用共用主題，因此對應 mock 的 36／44px 高為 37／42px，沒有按頁面建立平行樣式。水平相鄰動作淨距 4、校對列至 Text 淨距 8。標籤欄最小 80px，播放群組與右文字區起點相同。

左右比較區等寬等高，標頭及文字起點相同。正常至少 4 行完整文字，內嵌詳情保留至少 6 行；13pt 的 900×640 仍達標。詳情在 900 切換內容頁，收合不重建文字區。來源頁原有較高的文件標頭會由接點頁重新分配父層列，文件清單與主面板齊頭。

原生差異：共用頂部導覽依實際字型請求寬度判斷換列，1280 的原生按鈕可以完整容納單列；mock 使用較寬的固定畫布按鈕而換列。原生沒有縮字、裁切或刪除入口，閱讀區取得較多高度。主體操作分組、左右欄線、固定 footer、窄版內容切換均照核准設計。測試使用三批 PDF／兩接點及額外未選 TXT；正文以 mock 相同三行文字對照，來源頁碼差異是受控 fixture 資料。

缺陷前後證據分開保存：[舊布局](before-1360x820.png) 的校對在文字下方、播放淨距 6；[baseline-layout.json](baseline-layout.json) 記錄失敗。修正版校對在標頭、淨距 4；同一原生測試再注入 6px 間距確認失敗，還原 4px 後通過，不能只憑 style 名稱通過。

## 捲動與真實輸入

[原生捲動契約](scroll-contract.json) 由原生 Text.count(ypixels)、pady、行高、Treeview 完整可見列及實際 yview 產生。Text 的 viewport／content 都排除內距；Treeview 以完整列作有效視口。四個 owner 各涵蓋短、剛好容納、溢出、長內容；短文不留軌道，溢出比例與 Tk 實際 fraction 相同。通用檢查結果見 [scroll-check.txt](scroll-check.txt)。

900 視窗實際操作「前批滾輪 → 拖曳滑塊到末行 180 → 點文字 → Ctrl+Home → Ctrl+End」，後批保持在首行、設定與 footer 不動。見 [滾輪](native-left-wheel.png)、[拖曳末端與 yview](native-left-drag-end.json)、[鍵盤末端](native-left-key-end.png)。文件列表及詳情的另外三種內容長度由原生元件操作回歸；没有把靜態圖當作輸入測試。

「警告詳情」實際滑鼠展開、Space 收合；[文件列表](native-files.png) → [返回](native-files-return.png) 保留原接點與設定。最後版本另將閱讀位置綁定接點 key，排除跨接點錯用位置，並在布局完成後恢復首末端。圖中端點與後續回歸均保留；先前返回截圖的像素偏移不是最後版本的通過依據。

## 正式 EXE

固定成品為 dist/ebook2mp4/ebook2mp4.exe。建置前確認正式程式已關閉，對 1905 個成品檔案作排他開啟檢查；[首次預檢](build-preflight.json)、[最後預檢](build-final-preflight.json) 均無占用。包內程式一致性、最終 SHA256 及工具版本以 [package.json](package.json) 為準；53 個程式模組匹配來源。

隔離專案中已實際從「文稿 → 選已確認批次 → 試聽與製作 → 全書合併 → 檢查接點」進入正式內頁。原稿未確認時步驟 2 保持停用，是既有流程契約。未呼叫 TTS 或傳送書稿。

1. [進入接點頁](exe-joins.png) → 展開詳情 → [縮小至窄版](exe-narrow-detail.png) → 確認專用詳情內容及固定操作。
2. 播放接點 → 正常結束 → [確認保留字幕標頭](exe-preview-stopped.png)。實際預覽為 10.5 秒。
3. 只確認第一接點 → 儲存並返回 → [確認合併仍停用](exe-save-warning-blocked.png)；[磁碟確認為 true／false](exe-save-warning.json)。
4. 重開接點 → 確認仍停在第二接點 → 確認第二警告 → 儲存並返回 → 確認可製作。
5. 按製作合併音訊 → [確認完成](exe-merge-complete.png) → 包內 FFmpeg 解碼通過。結果為三批、12.8 秒 MP3 及 SRT，沒有 MP4，沒有殘留 join-preview，見 [實際媒體結果](exe-result.json)。
6. 正常關閉 → [exit 0](exe-start.json) → 重新開啟 → 在任何前置／還原操作前查詢 [原生 IsZoomed=true](exe-startup-maximized.json) → 再次正常關閉，見 [重開紀錄](exe-reopen.json)。桌面工具的前置動作會還原最大化，因此以未操作前的原生狀態證明啟動最大化。

最後的接點識別修正另以最終封裝複驗：先把 [接點 A 捲到末端](exe-final-pair-a-end.png) → 展開詳情 → 下一接點 → 收合 → [接點 B 從 Chapter 8 首行顯示](exe-final-pair-b-start.png) → 上一接點 → [接點 A 恢復 Chapter 4～8 的末端位置](exe-final-pair-a-return.png)。最終 EXE 從接點頁正常關閉、exit 0，見 [最終執行紀錄](exe-final.json)。

完整主流程驗證版本 SHA256 為 62521b10c73e3f39932d9a5573045cb46d97a5931d79a868a0c833d2855f3e07，見 [該版封裝對照](package-primary-run.json)；最後版本為 **704ee5c16ee63da4c29c6d09dace827cf1c8caf78469bbfe0d1937bab09b5d56**，53 模組重新比對通過。兩版僅差閱讀位置恢復的接點識別檢查；最終版重開仍讀到已完成成品及兩個已確認警告。沒有把兩版的畫面混稱為同一版。

## 清理與版本

來源逐檔雜湊在 [source-manifest.json](source-manifest.json)。保留核准設計、原生畫面、量測、回歸、正式程式及合成媒體證據。刪除本次隔離專案、測試暫存、建置套件與工作目錄；不清除既有使用者資料或其他工作留下的資料。程序及檔案占用複驗見 [cleanup.json](cleanup.json)。本次範圍的功能、原生布局與正式程式驗收已完成，18 項清單均有對應證據；這不代表全專案所有頁面已完成模組化。
