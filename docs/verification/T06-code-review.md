# T06 code-review

依 implement 要求執行 code-review 技能，分開派出 Standards 與 Spec 兩軸審查。固定點為本次起點 `2ae4c03165c474210bd02a604b8bb343420c666b`；比較命令 `git -c safe.directory=E:/Leo/Projects/ebook2mp4 diff 2ae4c03165c474210bd02a604b8bb343420c666b...HEAD`，已先確認固定點可解析、差異非空。實作提交 `fbb225f`，審查修正提交 `a2a24f9`。規範來源為 AGENTS、GLOSSARY、ADRs、README 與 Spec 的技術／驗證規則；不存在 CODING_STANDARDS.md／CONTRIBUTING.md。規範軸亦帶入技能完整十二項 smell baseline，僅作判斷依據，不當硬性規範。

## Standards

初審 1 項 P2，已修正並複查解除：原本同步讀取專案來源失敗會留下未追蹤、持有 grab 的對話框，違反 AGENTS.md 的資源釋放指示及 Spec 第 17 條「缺檔明列」。

來源驗證現已移入背景工作。原審查者以真實 Tk 分別驗證來源缺檔及損壞：錯誤可見、對話框可追蹤且可關閉；關閉後無 grab、無殘留 Toplevel。測試暫存與視窗已清除。

未解決規範問題：0；無須阻擋交付的程式碼異味。

## Spec

原兩項 P2 已於 `a2a24f9` 解除：

- 原批有人工改稿時，重試新批會將繼承的 `resolved` 異常恢復為 `pending`；明確 `skipped` 保留，原批朗讀快照不變。
- OCR 與文字層共用品質檢查，僅頁碼／稀少文字不再直接報成功。

原審查者複查程式與兩項真實工作流程 regression，2／2 通過，5.626 秒，未跑完整套件。測試暫存自動清除。

Spec：0 項未解決。

兩軸最終未解決：Standards 0、Spec 0；各軸原最高 P2 均已解除。
