# 批次狀態滑鼠停留說明

日期：2026-10-27。

依使用者指定，在批次清單的狀態欄加入約 400 ms 延遲的浮動說明：

- 「未確認」→「確認朗讀稿」。
- 「待檢查 N」→「有 N 項來源／OCR 異常尚未處理」，數量取自該列目前顯示的未處理數。

既有狀態含義與排序保留。批次名稱、空白處、已確認狀態不顯示本次說明。浮動視窗不取走鍵盤焦點或變更批次；離開、點擊、捲動、鍵盤操作、更新狀態、移動主窗及關閉時收起，取消尚未觸發的計時器並解除主窗事件綁定。位置限制在螢幕範圍內。

## 驗證

- [測試](status-help-tests.txt)：`python -B -m unittest test_status_help test_ui_layout -v`，**8 項通過，8.790 秒**。涵蓋兩種說明、2→1 項即時數量、非狀態欄不顯示、保持選取／焦點，以及離開、捲動、銷毀時的視窗／計時器釋放；既有工作台配置回歸也通過。
- [封裝](status-help-build.txt)：PyInstaller 成功；沿用既有已驗證 Tesseract 引擎。本次僅準備隔離封裝依賴，未修改全域套件。
- [封裝啟動](images/status-help/packaged-startup.jpg)：新版實際開啟空白工作台並正常關閉，父程序退出碼 0。
- 原生畫面使用合成 TXT 專案、1040×640 邏輯尺寸與目前約 125% Windows 縮放。`tests/status_help_visual_fixture.py --hover unconfirmed|pending` 以合成 Motion 事件觸發浮動說明，再用原生擷取檢查外觀：[未確認](images/status-help/unconfirmed.jpg)、[待檢查 1](images/status-help/pending.jpg)。這些截圖是實際 Tk 元件，不是繪製 mock。

本次範圍為狀態說明，未重跑 OCR／Gemini 全套。其他 DPI、輔助科技及乾淨 Windows 安裝未新增驗收。

## 成品

`dist/T07-status-help/ebook2mp4/ebook2mp4.exe`，整個 `ebook2mp4` 目錄一起搬移。

SHA-256：`FB85EC90AA2A13971CAC6A8DE7CBC1A59340D476C99463D405C4B4B318A74996`。

未提交、未推送。舊成品、使用者書稿與模型保留；依 AGENTS.md 清理本次暫存，保留正式成品與驗證證據。

已清除 **176,385,150 bytes（約 168.2 MiB）**。新封裝 1,152 個檔案均可獨占開啟後釋放，失敗 0；本次合成專案、測試與新版驗證視窗已退出，桌面自動化 kernel 已重設。詳見 [清理紀錄](status-help-cleanup.json)。
