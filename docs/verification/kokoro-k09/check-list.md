# K09 本機 UI 根清單覆核

2026-11-19。對照根目錄 `check-list.md` 的 18 項。範圍為目前核准的語音設定、語音包管理、製作、接點及既有服務返回；本次沒有 UI 實作或設計變更。來源與 EXE 版本見 [README](README.md)，原生驗收與正式操作分開記錄。以下結果限本機，乾淨 Windows 測試依使用者決定不執行。

| 根項次 | 結果 | 操作／量測依據 |
| --- | --- | --- |
| 1 短文／空狀態 | 通過 | 空語音包不留詳情軌道；安裝後短試聽無正文捲軸。接點短文契約亦通過。[空狀態](exe-package-empty.jpg) · [短試聽](exe-voice-return-installed.jpg) · [契約](join-recheck/join/scroll-contract.json) |
| 2 溢出／比例／行程 | 通過 | 語音包 100 音色詳情在窄版溢出，末端可達；接點四種內容高度以實際 count／yview 量測。[詳情](exe-package-details-small.jpg) · [量測](join-recheck/join/native-scroll.json) |
| 3 首末與固定操作 | 通過 | 正式詳情滾輪、拖曳滑塊、Ctrl+End 到 `zm_100`；返回及導覽固定。[滾輪](exe-package-details-wheel-end.jpg) · [滑塊](exe-package-details-thumb-top.jpg) · [鍵盤](exe-details-keyboard-end.jpg) |
| 4 長短／空狀態轉換 | 通過 | 詳情 → 語音頁 → 移除 → 缺包，沒有正文殘留軌道；接點空狀態與返回回歸通過。[缺包](exe-voice-missing-after-remove.jpg) · [回歸](join-recheck/native-tests.txt) |
| 5 尺寸與展開收合 | 通過 | 正式最大化、還原／縮窄、詳情展開及安裝後空間回收。原生四尺寸及兩種字級通過。[操作](exe-actions.json) · [原生](voice-join/voice/native-layout-regression.json) |
| 6 元件風格 | 通過 | 語音、製作與服務返回沿用核准的共用元件，主要／次要及停用狀態可辨。[正式](exe-preview-running-maximized.jpg) · [同版全頁](../v2-ticket-13-close/native/measurements.json) |
| 7 同欄按鈕／輸入外框 | 不適用 | 本次沒有 OCR 等「同欄以按鈕取代 input」區域，也未新增此類元件。既有語音欄位的行對齊另見第 10 項。 |
| 8 同組按鈕 | 通過 | 試聽 10 pt：130×37／130×37；13 pt：162×42／162×42。接點同角色外框一致。[試聽](voice-join/voice/native-layout-regression.json) · [接點](join-recheck/join/native-layout-regression.json) |
| 9 焦點／忙碌／停用 | 未全數通過 | 匯入可取消，忙碌時停用衝突欄位，移除後停用新試聽。按「停止」後，畫面仍顯示正在播放。[匯入](exe-import-running.jpg) · [忙碌](exe-preview-running-maximized.jpg) · [缺包](exe-voice-missing-after-remove.jpg) · [停止後狀態](exe-preview-stopped.jpg) |
| 10 同列對齊 | 通過 | 試聽兩鈕 y／高一致；接點 peers 四尺寸角色外框一致。[逐對值](voice-join/voice/native-layout-regression.json) · [接點](join-recheck/join/native-layout-regression.json) |
| 11 同欄對齊 | 通過 | 同版固定 port 與表單邊界沿用；本批正式語音及服務返回已覆核。[語音](exe-voice-return-installed.jpg) · [Edge](exe-cloud-settings-without-kokoro.jpg) · [同版矩陣](../v2-ticket-13-close/native/measurements.json) |
| 12 水平淨距 | 通過 | 試聽兩鈕、儲存／下一步均為 4 Tk px；接點播放群組為 4。[試聽](voice-join/voice/native-layout-regression.json) · [接點](join-recheck/join/native-layout-regression.json) |
| 13 垂直淨距 | 通過 | 試聽帶入文字列至 Text 為 8 Tk px；接點正文前間距為 8。[試聽](voice-join/voice/native-layout-regression.json) · [接點](join-recheck/join/native-layout-regression.json) |
| 14 標頭／內容基準 | 通過 | 接點經實際外層布局後，標頭及內容起點差值≤2。[基準線](join-recheck/join/shell-anchors.json) |
| 15 尺寸／字級矩陣 | 未全數通過 | 原生最大化、1360×820、1280×720、900×640、10／13 pt 的按鈕及文字區量測通過。正式 1127 px 外框下仍可操作，服務下拉欄尾端的 CPU 顯示被截短。[試聽](voice-join/voice/native-layout-regression.json) · [接點](join-recheck/join/native-layout-regression.json) · [正式窄版](exe-voice-return-installed.jpg) |
| 16 分開記錄驗證層次 | 通過 | README 分列公開流程、七項回歸、原生量測與正式 EXE；乾淨 Windows 明確未測。[結果](README.md) |
| 17 本版證據與例外 | 通過 | 來源未變，正式 EXE SHA-256 與 #13 相同；本批另完成真實包及 EXE 操作。不把離線主機等同乾淨 Windows。[版本](package.json) · [退出](exe-launch.json) |
| 18 缺陷修正前後數值 | 不適用 | 本次未修改尺寸、間距或產品程式；沒有宣稱修復 UI 缺陷。原生回歸中的注入壞間距仍可攔住回歸。[回歸](join-recheck/join/native-layout-regression.json) |

本機功能驗證通過。正式 EXE 的停止提示與窄版服務欄仍有待修項，UI 驗收保持未完成。使用者確認 K09 人工聽感通過。自動清單保留原始測試結果。
