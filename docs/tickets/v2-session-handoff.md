# v2 新 session 交接入口

更新：2026-11-13。工作目錄：`E:\Leo\Projects\ebook2mp4`。狀態：ACTIVE，持續交接入口。

## 目前工作

使用者最新確認：**依目前 UI 排版及對應功能改版，不重新設計 UI，也不用提供設計圖；已授權開始。** 保留 A 的入口／布局越界及功能契約盤點，原未核准[外框草案](../ui-review/v2-unified-shell-a/README.md)改列歷史，不作實作依據。本輪已完成 B 集中父層及 C 全頁接入，保留目前控制項分組、位置、操作與狀態；D 限既有內容／功能接回及驗收。進度及本輪原生基線見[實作證據](../verification/v2-shell-refactor/README.md)。

本輪 B／C 已完成：共用區幾何由 DesktopShell 持有，所有實際主頁／內頁均經固定內容 port 與共用操作呈現。已完成本輪功能回歸、72 筆原生畫面／量測、24 組接點基準線、正式 EXE 操作及三條成品路徑解碼。正式程式固定更新至 `dist/ebook2mp4`。逐頁責任與證據見[本輪接入矩陣](../verification/v2-shell-refactor/integration.md)、[根清單結果](../verification/v2-shell-refactor/check-list.md)。

接續維護 D／E 的繼承人工矩陣與原票依賴，不能把本輪外框通過擴張為真實雲端／Kokoro 推論品質通過；Ticket #13 保持開啟。繼續沿用目前 UI，不要求新增設計圖或重複核准。舊模組化票不再作排程入口。

## 必讀順序

1. [AGENTS.md](../../AGENTS.md)。
2. [frontend-visual-qa](C:/Users/Administrator/.codex/skills/frontend-visual-qa/SKILL.md)、[元件規範](../ui-components.md)、[捲動門檻](../ui-scroll-qa.md)、根[check-list.md](../../check-list.md)。
3. [新全頁外框spec](../v2-unified-shell-spec.md)，再讀[執行ticket及全頁矩陣](v2-unified-shell.md)。
4. [結案盤點與遠端同步狀態](2026-11-13-tracking-audit.md)。
5. [主產品spec](../pdf-txt-audiobook-video-spec.md)相關保存／任務／成品與雙版本契約、[v1封存](v1-baseline.md)。
6. [implementation-status](../implementation-status.md)最新段落、將要修改頁面的最新證據及實際來源。歷史票與設計只依新spec指向按需閱讀。

讀完簡述限制與未完成項目，再從新票第一個未完成階段接續。以本輪保存的實際 UI／來源及原生量測作基線，直接實作；不再要求新設計圖確認，不採未核准 A 草案。所有頁面 C 門檻通過前，不開始 D 的功能整合；本輪全程沿用現有 UI。

## 保護與交付

- v1已完整封存於`archives/v1/source`、`archives/v1/ebook2mp4`及`archives/v1/manifest.json`，不可覆寫或當暫存刪除；[證據](../verification/v1-baseline/README.md)。本階段保留現狀，不建置、執行、測試或重驗雜湊。
- v2來源在目前工作目錄，正式建置固定`dist/ebook2mp4`。保留既有必要未提交／未追蹤來源及使用者資料，不以Git HEAD還原磁碟現況。
- 保留來源／草稿／朗讀快照、任務快取與範圍隔離、同意及失敗保存契約。切頁不重啟製作、不讓舊回呼覆寫目前頁。
- 每批逐項完成根check-list，保留量測／畫面／實際操作證據；功能回歸、mock符合度、原生及正式EXE驗收分開報告。未測不算完成。
- 封裝前確認正式程式正常關閉且未占用，強制結束使用者程序須另獲授權；清理本次資料／暫存／快取／程序，保留成品、文件、核准設計與證據。
- 先由主agent統一介面與整合。需要派工時按實際授權執行，避免多人同改共用父層；交接須附上述UI必讀入口、適用清單、範圍與證據要求。

本機spec／ticket已同步至GitHub：[Spec #12](https://github.com/newesp/ebook2mp4/issues/12)／[Ticket #13](https://github.com/newesp/ebook2mp4/issues/13)，皆OPEN。使用者已明確授權同步及整理；#5已因取代關閉，#2已更新UI入口，其餘原遠端票保留。結果與歷史限制見[盤點](2026-11-13-tracking-audit.md)。
