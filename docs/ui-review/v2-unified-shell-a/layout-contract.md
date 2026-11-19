# A：布局／操作分組／空間分配對照

狀態：設計草案，待使用者確認。功能契約另見 [function-contract.md](function-contract.md)，不能用功能仍可呼叫代替布局符合。

## 共用父層

延伸 DesktopShell，不另建平行框架。唯一 shell 固定建立 NavigationBar、DocumentList、WorkspaceFrame、共用 header／tools／content／regional status、ActionBar。InnerPageHost 與 ProductionPageLayout 收斂到這組 port；頁面只建立 content 子元件、提供描述與 ActionSpec。任何內容 adapter 也沒有 app.actions 等幾何權限。

| 布局／分組／預算 | 原生實作責任 | 後續驗收方式 |
| --- | --- | --- |
| 導覽固定兩列。第一列「1 文稿／2 試聽與製作」、書名、專案、訊息。第二列是所選階段的工具／製作子流程 | 同一 NavigationBar；依 context 提供第二列項目，**不搬 tabs 進其他 parent**。主頁按鈕等寬，第二列以最長角色標籤算共寬 | 依同尺寸切 20 列 → 記錄 navigation rect／parent／instance → 確認同基準線。正常／busy／disabled 均不改尺寸 |
| 文稿第二列：編輯文稿／整理換行／版本紀錄／AI設定／來源處理；製作第二列：語音／音訊／全書合併／影片。直接版本入口只留一個 | shell 只選目前 context 的導覽集合。來源異常從來源處理入口；不在內容另複製同一返回／列表控制 | 按各入口 → 確認標題／selected 正確 → 返回原頁。核對沒有雙份版本、全書合併及影片入口 |
| 文件列表寬 216、欄距 12；收合後整個 228 軌道釋放。開關在展開時的文件工具列、收合時的共用工具列 | shell 持偏好與 narrow reflow；不由合併／接點頁直接 toggle app.focus_mode。匯入／管理兩個 menu 同尺寸；收合為不同的 icon 角色 | 展開 → 收合 → 返回 → 改尺寸。量測內容寬增加 228，左側無殘留軌道；列表捲動只在 list viewport |
| 標題帶 y100、工具列 y124／h36，內容 port y168；文件列表與工作區 header 同 y100／h60，底下淨距 8 | shell 在同一 row／column 規則計算兩條線，依整組已量測元件最大值適應 DPI。這些是 96dpi 設計值，**原生不得硬寫依頁名補償** | 文稿 → 音訊 → 內頁 → 合併 → 接點；走外層 Configure＋after → 量 list_header 與 workspace.header → 差≤2；量 batch_view 與 content port → 差≤2 |
| 共用工具列空間不足時，保留最前的範圍／選擇，其餘收進「本頁操作」具名選單；實際命令映射不得遺失 | shell 依工具 descriptor 的優先序與 measured reqwidth 決定；descriptor 含 enabled／value／選單內容。不能把內容截掉當作收合 | 逐項從窄版入口找回所有命令；鍵盤開選單並操作；明確比對命令 id 集合，禁止空選單 |
| 固定底列一列摘要＋一列動作，summary y=h−80、操作 y=h−52／h36；返回靠左、secondary／primary 靠右，相鄰淨距4 | ActionBar 唯一呈現。主頁文稿不造「返回」；各工具原入口返回一次。主／次提交同組取最長字串共寬；刪除獨立語意且須確認 | 同組 rect 寬高差≤2，逐對 gap=4；以最長真實狀態標籤重驗。busy 只出現可用取消，不能保留可重複啟動命令 |
| 局部操作列到內容淨距8，例如固定範例／選取文字→試聽 Text | 內容沿用 ToolbarLayout.equal_button_pair 與 TOOLBAR_GAP，不加平行 helper 或單頁 style | 量兩按鈕共同寬／高、gap4、Text 上緣−按鈕下緣8；同資料比原生與 mock |
| 長文／清單各自垂直捲動；表單沒有內部長文時，單一有界 form owner；內容 fit 時不顯示捲軸 | 延伸 ui_controls.AutoHideScrollbar；更新 scrollregion 時同時回收軌道／offset。shell 本身沒有整頁 scrollbar | 短→fit→overflow→long→空→返回；滾輪／拖滑塊／Home-End。確認末行可達且固定導覽、工具及 footer 不動 |
| 寬版雙欄讀稿，單欄至少 20 個目前字級中文字＋內距；不足時切原稿／文稿或前批／後批；頁籤狀態保留 | 內容 port 管比較面板，不改 shell 幾何。900 且列表展開的12pt比較區採內部切換，18pt 需更多寬度；收合列表可能恢復雙欄 | 相同內容、字級、列表狀態比 mock；點原稿／文稿 → 返回 → 確認選取／捲動各自保留。PDF 原頁保留頁碼／縮放／來源檢視入口 |
| 語音寬版聲音設定＋試聽正文；窄版切聲音設定／試聽文字，主要保存／下一步仍固定 | VoiceWorkspaceLayout 只排自己的設定及 Text；服務／scope／歷史放工具描述，提交移 ActionSpec；本機／雲端適用欄位維持 | 在兩頁籤間修改 → 切服務 → 返回 → 確認輸入／同意不重設。設定 overflow 時只 form 捲動，不以 outer Canvas 包 Text |
| 影片 fit 預覽；素材與播放列固定，來源／任務頁籤在內容內切換 | VideoTabs／MoviePlayback 保留內容行為；影片範圍／方式改 shell 工具，footer 不各頁自建 | 本批→全書統一→沿用各批 → 量共用區不變；預覽16:9不拉伸、縮放有界；來源及任務隔離另驗 |
| 專案資訊／訊息記錄同窗內容頁；系統選檔器與必要確認保留 OS modal | 以呼叫時 route/scope/generation 記 return target；不把全文複製進另一新 editor | 從文稿及製作各開一次 → 返回 → 確認原頁、任務、焦點與未存資料未變 |

## 尺寸與文字量測

繪圖來源：[design_unified_shell_a.py](../../../tools/design_unified_shell_a.py)。Microsoft JhengHei，控制字型14px（96dpi 的10pt近似）、標題16px、正文12pt／18pt；每行高度與換行使用該字型實際 bbox／getlength。這不是 Windows DPI 或 Tk reqwidth 的實測替代品。

| client 設計尺寸 | 內容 port x（列表展開／收合） | 內容頂／底 | port 高度 | 固定底列頂 |
| --- | --- | --- | --- | --- |
| 1536×864 參考最大化 | 244／16 | 168／764 | 596 | 776 |
| 1360×820 | 244／16 | 168／720 | 552 | 732 |
| 1280×720 | 244／16 | 168／620 | 452 | 632 |
| 900×640 | 244／16 | 168／540 | 372 | 552 |

1536×864 是既有證據使用過的參考大小，非本輪量測的實際最大化 client。B／E 必須啟動當前原生／正式 EXE，記錄真實最大化 client、DPI及Tk scaling。本輪不修改 PRODUCT.md／DESIGN.md 的歷史描述；現行 min900×640 與兩主步驟以實際來源及新 spec 為準。

每張圖的 controls／regions／header／content rect 見 [layout-measurements.json](layout-measurements.json)。圖與資料由同一模型輸出。捲軸計算：`offset=max(0,content−viewport)`；可見比例 `viewport/content`；無溢出不繪 track，無水平捲動。原生平台最小滑塊長度待 B／E 記錄，不把設計畫素長度當原生最低值。

`scroll-contract.json` 分開記錄本張圖實際內容及 short／fit／overflow／long 行資料邊界 fixture。fixture 的 fit 使用恰為完整量測內容高度的 viewport，不能宣稱是該張完整畫面的另一個 runtime 狀態。實際表單短內容及展開、空狀態與長文另有原尺寸圖；互動捲動保持未測。

## 請確認的新增布局

1. 共用兩列導覽及固定兩行 header 預算，所有頁共用內容起點；各頁原有自由配置標頭與 footer 改交 shell。
2. 文稿工具直接放在第二列，版本保持單一直接入口；製作頁第二列保持現有四個子流程。窄版只重排 port 內容與工具命令。
3. 專案資訊與訊息記錄改同窗頁，返回呼叫時頁面。原生選檔／確認仍保留。
4. 窄版比較與試聽使用內容頁籤，列表偏好由 shell 保留；設定、來源、任務及成品不因切頁重建。

核准只涵蓋上述外框與路由承載。內容圖是既有能力的空間示意；B／C 先以 adapter 保留完整內容，不以圖中簡化樣本刪除功能。D 各頁專屬布局及全部未測矩陣仍須逐項整合、驗證；C 全表未通過前不開始 D。
