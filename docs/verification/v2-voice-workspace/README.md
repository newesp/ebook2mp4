# 語音設定與試聽 v2 模組化

依使用者核准的音訊製作外框mock及管理服務右側內距補充實作。正式EXE固定dist/ebook2mp4。

## 共用責任

VoiceWorkspaceLayout承載語音頁原生內容布局；VoiceDialog保留服務、音色、同意、文字、工作、播放及保存契約。ProductionPageLayout提供固定工具列／全域底部操作port、PagePresentation／ActionSpec資料及active-page命令隔離。ProductionWorkspace統一頂部製作流程、工具列齊頭與底部顯示；底部元件從建立即以app.actions為父層，不在切頁時改父層。離頁隱藏及阻止舊控制項提交，釋放頁面同步清理底部資源。

## 布局／功能對照

| mock | 原生實作 | 驗證 |
|---|---|---|
| 音訊製作同列流程、左列表與來源工具列齊頭 | ProductionWorkspace共享chrome及source toolbar port | native.json兩工具列y一致 |
| 管理服務按鈕右邊留白 | 服務列共用16內距加主題邊框 | 原生右側18 Tk單位 |
| 左聲音設定、右試聽文字 | 1：2並列，服務／語速／節奏依原能力保留 | native.png與語音／Kokoro回歸 |
| 固定範例與選取文字按鈕 | 同一outgoing Text，保留右鍵及Shift-F10入口 | 現有文字替換保護沿用 |
| 固定底部保存、範圍、下一步 | 共用ProductionPageLayout固定port | 保存／離頁隔離及相鄰頁恢復回歸 |
| 只有長試聽文字捲動 | Text自己的視口，依yview顯隱捲軸 | 短→長到末端→短，固定footer不動 |

保留線上同意預設勾選與取消阻擋、本機情境提示、載入歷史任務／設定、自訂模型／聲音ID、全書預設與套用既有批次、服務與語音包管理、取消／失敗保留上一份成功結果、重播停止及離頁停止。歷史來源不存在時工具列顯示空狀態且停用載入，避免移除工具列造成主區錯位。原生沿用LabelFrame邊框與字形，和mock平面邊框有主題差異；播放狀態及技術提示保留原資料契約。

## 證據與限制

targeted-native.txt：5項保存／恢復通過。final-regression.txt：23項語音、本機、保存、音訊頁回歸通過，均使用受控外部服務。首次沙箱測試背景工作逾時，改於原生權限重驗通過；初輪整合另抓出頁釋放後量測舊控制項，已修正。測試配合固定footer的父層更新邊界斷言；本機缺包案例隔離Kokoro目錄。

native.json／native.png：1360×820原生幾何與畫面。右內距18、工具列y一致、短文字無軌道、長文字末端可達、回短後軌道消失及footer不動。build.txt建置成功；package.json全部51模組一致，FFmpeg／FFprobe可啟動；exe-startup.json隔離啟動及正常退出。

完整最終EXE逐頁人工、所有DPI／18pt、不同尺寸全部狀態與實體播放裝置未在本輪完整覆蓋，不以封裝一致／啟動成功代替完整視覺與播放驗收。詳見check-list.md。
