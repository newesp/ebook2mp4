# 元件一致性修正（2026-11-10）

原因：任務 Combobox 使用預設樣式；Menubutton 標籤手加箭頭，與原生指示符重複。先前驗收只涵蓋空間及可達性，未量測同列尺寸或檢查指示符。

修正：沿用 Workspace.TCombobox；成品選單標籤改為「成品操作」。不改任務與保存行為。

跨 session：AGENTS.md 加入必讀入口 docs/ui-components.md，集中共用樣式來源、尺寸角色、原生指示符及封裝畫面驗收。已有的 frontend-visual-qa 一致性規則保留，專案細節不重複堆入通用 skill。

回歸：原缺陷版本在三個視窗尺寸被攔截（高度差14；標籤箭頭加原生指示符共2）。修正版10項音訊頁測試通過，包含1536×864、1280×720、900×640的實際尺寸與指示符檢查。完整紀錄 component-tests.txt。

主 agent 原生複查：1280×720、Tk scaling1.3346，任務選單與相鄰按鈕均高37、頂端137；成品標籤無手畫箭頭，原生指示符1個。清單仍有14個完整列。見 component-fixture.json、component-native.png。

封裝已完成。舊版程序 PID25212 占用 DLL、正常關閉未退出，經使用者明確授權後結束，再成功重建 dist/ebook2mp4。保留兩次失敗紀錄 component-build.txt、component-build-retry.txt；成功紀錄 component-build-final.txt。

正式 EXE 以隔離專案啟動，進入音訊頁，目視確認高度及單一箭頭，再正常關閉（exit code 0）。見 component-package.png、component-package.json；清理與資源檢查見 component-cleanup.json。

服務使用合成驗收資料，未呼叫真實雲端合成。未驗證其他主題及所有系統 DPI；新規範與測試降低重犯風險，不代表永久零缺陷。
