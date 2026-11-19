# 2026-11-13 spec／ticket 盤點及結案

新執行依據：[spec](../v2-unified-shell-spec.md)／[ticket](v2-unified-shell.md)。本輪為文件與現況盤點，不是重新進行UI或正式EXE驗收；既有證據的限制仍保留。關閉工作項目不刪除功能與資料契約。

## 本機原有12份 ticket

| 文件 | 本次狀態 | 理由／證據／後續 |
| --- | --- | --- |
| [v1-baseline](v1-baseline.md) | CLOSED：已完成 | [完整封存、雜湊、來源／EXE操作](../verification/v1-baseline/README.md)；新階段保留v1現狀，不另建置或驗證 |
| [unified-manuscript-workspace](unified-manuscript-workspace.md) | CLOSED：歷史範圍完成 | [第三版交付](../verification/unified-manuscript/README.md)；後由第六版修訂，不代表全APP v2完成 |
| [unified-manuscript-v6-handoff](unified-manuscript-v6-handoff.md) | CLOSED：歷史範圍完成 | [第六版交付](../verification/unified-manuscript-v6/README.md)；後續共用父層重驗移至新票 |
| [manuscript-cleanup-footer](manuscript-cleanup-footer.md) | CLOSED：歷史範圍完成 | [底列／換行修訂](../verification/manuscript-cleanup-footer/README.md)；保存保護保留 |
| [audio-production-ui](audio-production-ui.md) | CLOSED：歷史範圍完成 | [音訊工作區交付與限制](../verification/audio-production-ui/review.md)；原非全頁外框接入，後續由新票承接 |
| [unified-video-workspace](unified-video-workspace.md) | CLOSED：歷史範圍完成 | [原生／正式EXE修訂證據](../verification/unified-video/layout-revision.md)；全頁父層未統一，新票承接 |
| [T18-batch-video](T18-batch-video.md) | CLOSED：功能交付完成 | [T18功能、原生／封裝及限制](../verification/T18.md)、[素材故障修正](../verification/video-diagnostics.md)；非全APP v2驗收 |
| [v2-linebreak-preview](v2-linebreak-preview.md) | CLOSED：該頁交付完成 | [共用內頁／原生／EXE證據](../verification/v2-linebreak-preview/README.md)；新外框完成後仍回歸 |
| [ui-modularization](ui-modularization.md) | CLOSED：由新票取代，非全範圍完成 | 同樣處理共用四區，但舊順序逐頁遷移讓各頁保留布局控制；全部未完成範圍移入新票A～E與全頁矩陣 |
| [v2-inner-pages-handoff](v2-inner-pages-handoff.md) | CLOSED：由新票取代 | 「文稿工具優先、其他逐頁」及過時接入狀態不再用作排程；全頁外框先行與剩餘功能／驗收移入新票 |
| [v2-source-pages-migration](v2-source-pages-migration.md) | CLOSED：由新票取代，非驗收完成 | 已接宿主，完整人工矩陣仍未完；PDF／TXT處理與異常的布局、功能、保存及未測項全部移入新票對應兩列D／E |
| [v2-session-handoff](v2-session-handoff.md) | ACTIVE：保留入口 | 是持續交接入口而非待完成產品票，已改指新spec／ticket |

合計：8份按歷史交付結案、3份因取代關閉、1份交接入口保留。新票仍OPEN，不把接入部分元件當成新目標完成。

## 本機規格與設計文件

| 文件 | 狀態／處理 |
| --- | --- |
| [主產品spec v1.3](../pdf-txt-audiobook-video-spec.md) | 保留有效：產品功能／資料與發布需求；全APP v2、乾淨Windows與真實品質驗收尚不能宣稱全數完成。共用UI排程改由新spec管理 |
| [Gemini 429恢復spec](../gemini-tts-429-recovery-spec.md) | CLOSED：實作交付已於11-05完成；[33項、原生、正式封裝證據](../verification/gemini-tts-429/README.md)。真實長書服務壓測未驗，不將模擬通過說成真實服務通過 |
| [Kokoro整合spec](../kokoro-local-tts-spec.md) | OPEN：程式存在，但不足以證明完整無快取離線、CPU品質／效能、全部音色、乾淨Windows封裝及使用者聽感確認。UI設計併入新spec，後端／品質要求保留 |
| [v2-ui-module-plan](../v2-ui-module-plan.md)、[v2-page-layouts](../v2-page-layouts.md) | 舊執行計畫CLOSED：由新spec接替外框責任與順序；歷史已核准內容與量測仍供參考，未核准舊圖不升格為新核准 |
| [文稿提案](../unified-manuscript-proposal.md)、[UI修訂](../unified-manuscript-ui-revision.md) | 歷史設計工作CLOSED：已有第三／六版交付；保留未衝突功能契約 |
| 其他T12～T16、布局／校對／語音等proposal／評估 | 參考文件，不是本輪新增的未完成工單；保留歷史判斷。其現有入口全部受新票全頁矩陣約束，不能據此另開頁面外框 |

## GitHub核對與同步完成

已於使用者明確授權後透過登入的GitHub CLI完成同步：[新Spec #12](https://github.com/newesp/ebook2mp4/issues/12)及[新Ticket #13](https://github.com/newesp/ebook2mp4/issues/13)皆OPEN並雙向連結。原#1～#11已讀回核對，只有#5因取代關閉，其餘10票保持OPEN。

| GitHub項目 | 處置判斷與理由 |
| --- | --- |
| [#1 首版產品spec](https://github.com/newesp/ebook2mp4/issues/1) | 保留；產品規格未完成全部品質／乾淨環境驗收，不能因局部UI重疊整張關閉 |
| [#2 Kokoro spec](https://github.com/newesp/ebook2mp4/issues/2) | OPEN；已追加#12／#13的UI工作入口，完整原文保留。CPU、離線、品質與包生命週期不由共用外框票取代 |
| [#3 K01可行性](https://github.com/newesp/ebook2mp4/issues/3) | 保留；缺完整無快取離線、效能／品質及使用者審閱證據 |
| [#4 K02共用語音接點](https://github.com/newesp/ebook2mp4/issues/4) | 保留；已有程式與部分回歸不足以逐項證明原票全部契約，本輪不補做產品驗收 |
| [#5 K03介面設計](https://github.com/newesp/ebook2mp4/issues/5) | CLOSED／not_planned：已在[關票說明](https://github.com/newesp/ebook2mp4/issues/5#issuecomment-6831620763)寫明取代理由；全部8項設計條件納入#12／#13。原因：先統一全頁外框，避免另設Kokoro布局。不是已實作或驗收完成 |
| [#6 K04包管理](https://github.com/newesp/ebook2mp4/issues/6) | 保留；安裝／移除／完整性／資源與公開流程驗證仍屬原票；UI整合依新票順序 |
| [#7 K05試聽](https://github.com/newesp/ebook2mp4/issues/7) | 保留；無快取離線CPU試聽、快取／前處理與品質證據不足；UI依新票 |
| [#8 K06程序清理](https://github.com/newesp/ebook2mp4/issues/8) | 保留；需真實程序／記憶體／卸載及取消量測，不是UI重疊可免除 |
| [#9 K07批次製作](https://github.com/newesp/ebook2mp4/issues/9) | 保留；完整離線長稿、混讀聽感與正式工作流驗收證據不足 |
| [#10 K08續作](https://github.com/newesp/ebook2mp4/issues/10) | 保留；真實程序中斷、模型版本變更與損毀快取矩陣未證明完成 |
| [#11 K09封裝](https://github.com/newesp/ebook2mp4/issues/11) | 保留；乾淨Windows、無模型／語言快取、完整離線流程未證明完成 |

先前建票曾遭自動審核以未明確授權外傳為由拒絕；使用者其後已明確授權同步並整理newesp/ebook2mp4工單。連接器寫入403，改用使用者恢復登入的GitHub CLI；在允許網路的執行環境確認登入後完成上述變更。未修改GitHub權限、未新增憑證、未提交或推送程式碼。最終讀回驗證新票雙向連結、#5關閉原因為not_planned、#2完整原文仍在及其他原票保持開啟；見[同步證據](../verification/v2-tracking-sync/README.md)。

## 本輪文件檢查

23份相關文件、269個本機檔案連結檢查通過；新spec／ticket階段與狀態核對通過，主spec及implementation-status的`git diff --check`通過。這些是文件檢查，不是UI合規或產品回歸證據。本輪未啟動應用、建置或測試程序，未產生測試資料／建置快取；既有來源、成品及封存保留。
