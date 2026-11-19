# 草圖檢查紀錄

2026-11-06，執行 `node docs/mock-ui/t21-partial-output-v1/verify.cjs`，結束碼 0。12 個情境、腳本語法、元素參照及行為檢查全部通過。這是最小 DOM 替身，不代表瀏覽器或正式應用驗收。

內建瀏覽器開啟本機 HTML 遭 URL 安全政策拒絕，未繞過，未取得視覺截圖。仍需本機瀏覽器確認。

程序初查使用 CIM 遭環境拒絕存取，改用 `Get-Process -Name node -ErrorAction SilentlyContinue`，沒有 Node 程序。未啟動其他應用、建置或伺服器；驗證程式未建立子程序及暫存資料。

`index.html`、`README.md`、`verify.cjs` 均成功以 FileShare.None 獨占開啟並立即釋放。沒有測試快取或本輪背景服務需要清理。
