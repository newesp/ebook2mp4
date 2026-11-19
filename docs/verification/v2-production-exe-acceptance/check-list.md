# 正式 EXE 製作補驗清單

2026-11-18。測試範圍為全書合併、檢查接點、總音訊製片與成品版本。EXE SHA-256 `bfdd98c705af4ebcc9e09af35d17d084ba05e1d52916184750a31d6cc656d7ac`。原生測試來源 SHA-256 `95c573eecefaa96a4fbc73d1f19916b62d08a8c662ed5928d0e5d8ec3815026a`。正式 EXE 的 Windows 顯示縮放為 125%，畫面擷取為 1920×1020 與 1127×1020 實體像素。原生量測為 96.09 DPI、Tk scaling 1.3346、10／13 pt。尺寸及間距以原生 Tk 座標像素記錄。

| 根清單項 | 結果 | 路徑、實測與證據 |
| --- | --- | --- |
| 1 短內容／空狀態 | 未測完 | 原生檢查接點兩欄短文高度 17、視口 196，捲軸隱藏、偏移 0。原生空狀態有回歸。正式 EXE 的接點空狀態待測。[原生捲動](join/join/scroll-contract.json) · [回歸](join/native-tests.txt) |
| 2 剛好容納、溢出及長內容 | 未測完 | 原生接點兩欄視口 196。內容 187 時無軸，204 時行程 8、滑塊比例 0.9608，3060 時行程 2864、比例 0.0641。正式 EXE 長文兩欄各有自己的軸。影片與成品版本的完整溢出量測待測。[捲動契約](join/join/scroll-contract.json) · [長文](exe-join-first.png) |
| 3 滾輪、滑塊與鍵盤 | 未測完 | 正式 EXE 開接點 → 捲右欄 → 拖左欄 → Ctrl+End。右欄到第 12 行，拖左欄時右欄停在同一處；左欄鍵盤回末行，導覽與儲存列維持可見。右欄的鍵盤末端及其餘頁面輸入矩陣待測。[滾輪](exe-join-wheel.png) · [拖曳](exe-join-thumb.png) · [鍵盤](exe-join-keyboard-end.png) |
| 4 長內容／空狀態往返 | 未測完 | 原生接點空狀態轉換已跑。正式 EXE 切換接點再返回保留雙欄位置，長文與空狀態往返待測。[回歸](join/native-tests.txt) · [返回接點](exe-join-return.png) |
| 5 尺寸、字級及展開／收合 | 未測完 | 正式 EXE 有接點與來源詳情窄版畫面，兩者保留固定操作；不同字級的正式頁面矩陣待測。[接點](exe-join-narrow.png) · [版本](exe-versions-narrow.png) |
| 6 共用風格 | 未測完 | 接點和版本畫面可辨識主要／次要按鈕；各頁完整 Button、Entry、Combobox 比對待測。[接點](exe-join-first.png) · [成品版本](exe-versions.png) |
| 7 表單輸入外框 | 不適用 | 本批操作路徑沒有 OCR 安裝表單，未涉及同欄位置互換的按鈕與輸入框。 |
| 8 同組同角色按鈕 | 未測完 | 原生接點四個同組按鈕同為 120×37（10 pt）及 120×42（13 pt）；其他頁同組外框待量測。語音試聽對照在前批紀錄。[接點數值](join/join/native-layout-regression.json) · [前批紀錄](../v2-shell-acceptance-2026-11-18/README.md) |
| 9 預設、焦點、停用及忙碌 | 未測完 | 正式 EXE 影片製作中，取消可用。未製作路徑停用播放與另存。各頁狀態切換尺寸及焦點矩陣待測。[製作中](exe-video-running.png) · [尚未製作](exe-versions-unmade.png) |
| 10 同列上下緣 | 未測完 | 接點左右標頭與內容的原生對應基準差 0。其餘同列控制項的原生外框量測待測。[接點基準](join/join/shell-anchors.json) |
| 11 同欄左右緣 | 未測完 | 兩個原生接點欄的布局已通過回歸；其餘頁面控件逐對量測待測。[布局回歸](join/join/native-layout-regression.json) |
| 12 相鄰動作水平淨距 | 未測完 | 接點原生播放／停止淨距 4，六組尺寸／字級相同。其他頁操作對待量測。語音底部儲存／下一步在前批。[原生淨距](join/join/native-layout-regression.json) · [前批紀錄](../v2-shell-acceptance-2026-11-18/README.md) |
| 13 操作列與內容垂直淨距 | 未測完 | 接點原生標題列至文字區淨距 8，六組尺寸／字級相同。其他頁操作列待量測。語音文字操作列在前批。[原生淨距](join/join/native-layout-regression.json) · [前批紀錄](../v2-shell-acceptance-2026-11-18/README.md) |
| 14 文件列表與接點基準 | 通過 | 原生從 PDF 校對返回接點。最大化及三組還原尺寸逐項切換字級和列表顯隱。24 組外框包含 16 組左右基準偏差量測，最大差值 0，門檻 2 像素。正式 EXE 的寬／窄畫面可讀且主要操作可達。[基準線](join/join/shell-anchors.json) · [寬版](exe-join-first.png) · [窄版](exe-join-narrow.png) |
| 15 視窗／字級矩陣 | 未測完 | 原生接點已量測最大化、1360×820、1280×720、900×640、10／13 pt 及列表顯隱。正式 EXE 已檢查最大化與 Windows 貼齊後窄版；其他正式尺寸、字級和頁面待測。[原生矩陣](join/join/shell-anchors.json) · [版本窄版](exe-versions-narrow.png) |
| 16 分別記錄各層結果 | 通過 | 功能回歸 1 項、原生布局及捲動 4 項、正式 EXE 實際操作各自記錄。[本次證據](README.md) |
| 17 所有適用項有證據 | 未測完 | 上列未測項留 Ticket #13 的 D／E。整體 UI 驗收未結案。 |
| 18 尺寸或間距缺陷修正 | 不適用 | 本次沿用既有產品與成品執行驗收，無尺寸或間距修正。 |
