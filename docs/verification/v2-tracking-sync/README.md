# v2 spec／ticket GitHub同步證據

日期：2026-11-13。使用者明確授權同步本機規格／工單至`newesp/ebook2mp4`，在#5寫取代理由後關閉，以及更新#2的UI工作入口；其餘原工單保留。

- [Spec #12](https://github.com/newesp/ebook2mp4/issues/12)：OPEN，與執行票雙向連結。
- [Ticket #13](https://github.com/newesp/ebook2mp4/issues/13)：OPEN，完整A～E順序及全頁接入矩陣；全部接入後才整合專屬UI／功能。
- [K03 #5](https://github.com/newesp/ebook2mp4/issues/5)：CLOSED／not_planned；[取代說明](https://github.com/newesp/ebook2mp4/issues/5#issuecomment-6831620763)明列條件移交及尚未驗收。
- [Kokoro spec #2](https://github.com/newesp/ebook2mp4/issues/2)：OPEN；完整原文保留，只追加#12／#13的UI工作入口。
- 原#1、#2、#3、#4、#6～#11維持OPEN；未將品質、離線或封裝驗收視為完成。

`before.json`保存#2／#5操作前的工單內容。`after.json`為GitHub REST API最後讀回的全部13份工單；`result.json`為狀態及網址摘要。驗證確認新票雙向連結、#5關閉原因、#2原文保留與其他原票狀態均符合預期。遠端body將本機Markdown連結轉成工作區文件路徑，避免在issue中產生無效的相對連結；未提交或推送來源檔案。

先前自動審核拒絕已由使用者明確授權解除。連接器寫入403後改用已恢復登入的CLI；受限環境的網路錯誤曾讓auth status誤報登入失效，在允許網路的執行環境核對登入成功後才寫入。本輪未變更GitHub權限或憑證。

本輪為文件／工單作業，未執行UI或產品驗收、建置或啟動應用；未改產品來源、v1封存及v2正式成品。工單傳送用的`.scratch/v2-tracking-sync`暫存已清理；本目錄保留最終證據，不含登入憑證。
