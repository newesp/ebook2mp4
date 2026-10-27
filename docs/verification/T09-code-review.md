# T09 雙軸審查

起點 `4c34479eda3e48bff304898d4da72f3522d7d26d`；初次實作 `6b18960`，修正 `b5f1426`。指令 `git -c safe.directory=E:/Leo/Projects/ebook2mp4 diff 4c34479...HEAD`。依 implement／code-review 技能，Standards 與 Spec 由兩個獨立 sub-agent 平行檢查；其他先前未提交 UI／OCR 修改不列入本次 diff。

## Standards

初審兩項：

- P2，`voice.py`：重複取消再次發送 `task.cancel()`，會中斷 finally 的資源釋放；違反 AGENTS.md 的釋放要求。已改為只接受第一次取消。公開流程測試以外部服務替身的非同步 finally 重現先紅後綠，見 [紅燈](T09-cancel-red.txt) 及 [最後語音回歸](T09-final-workflow.txt)。
- P3，播放測試檢查內部 MCI alias，違反 Testing Decisions 的可觀察行為原則。已改觀察外部音訊裝置邊界的 play／close 效果；另以真實 Windows MCI 播放及獨占開啟音訊驗證資源釋放。

原審查者複查：兩項均解除；沒有其他值得提出的 documented-standard 違規或基線 smell。

## Spec

初審一項：

- P2，`voice_desktop.py`：主窗換到 B 批次後，舊語音視窗的「本批次」仍修改 A。違反 §11「各批可個別調整……須明確套用才更新」。已在視窗明示所屬書籍／批次，並於儲存及試聽前阻擋與主窗不符的上下文。真實 Tk A／B 切換回歸先紅後綠，見 [紅燈](T09-context-red.txt) 與 [最後 Tk 回歸](T09-final-desktop.txt)。原視窗仍可播放其成功結果；回目前批次須關閉重開。

原審查者複查通過，原 P2 解除。其餘 T09 音色、語速、單一明選音色、試聽快照、取消與錯誤隔離未發現缺漏或範圍擴張。

Standards：0 項未解決；Spec：0 項未解決。
