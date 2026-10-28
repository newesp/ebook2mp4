# T11 雙軸程式審查

基線 `0116f54`。先前工作目錄差異先保存，僅審查 T11 增量。依 code-review 技能委派 Standards 與 Spec 兩名獨立審查者；各自複查修正。

## Standards

初審 2 項 P2：儲存時全部 ProjectError 被數值提示蓋掉；兩個 StringVar trace 關閉後未解除。已分開處理 ValueError／ProjectError，並保存 trace token，在 release 移除。原審查者複查解除。公開 Tk 測試觀察跨視窗衝突原訊息及關閉後 trace_info 為空。

## Spec

初審 1 項 P1：中文閉引號後空白、連續句末標點會變成獨立請求，增加錯誤停頓。合併完整句末邊界後，複查再找到 1 項 P2：越過空白吸入下一句 ASCII 開引號。已先吸收緊鄰標點／閉引號，再吸收空白，新增公開工作流程回歸。原審查者再次確認全部解除。介面明示成對引文不拆句與切分變更可能重合成。

Standards：0 未解決。Spec：0 未解決。人工聽感待使用者驗收，不列為已通過。
