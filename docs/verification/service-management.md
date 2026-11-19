# 試聽與製作：服務新增、編輯與刪除

2026-11-05。依使用者確認的編輯頁 mock 實作。右側只保留原有「新增／管理服務…」入口，改為原生下拉選單。

## 完成內容

- 下拉第一項為「新增服務…」。第二項為「編輯目前服務…」。Edge-TTS 的第二項停用並標明內建服務不適用；Kokoro 的第二項改為「管理本機語音包…」。
- 編輯在原主視窗內完成，直接載入目前選定的服務。既有類型固定；名稱、金鑰與 Gemini 校對金鑰沿用選項可更新。留白保留既有金鑰。
- 儲存同一服務時保留模型、音色、語速、停頓與試聽文字。修改服務後要求重新試聽。
- 檢查連線使用尚未儲存的表單，不先寫入設定檔。檢查可取消，結束後釋放工作與計時器。
- 取消未儲存修改時提供頁內放棄確認。刪除也在頁內確認，刪除成功後才返回並切換至 Edge-TTS、清空音色。
- 只移除指定本機設定及其保存的金鑰，不刪除稿件、音訊、字幕、其他服務或共用校對金鑰。設定寫入失敗時保留原設定與編輯頁。
- 避免在語音任務使用金鑰時儲存或刪除設定。其他已開啟的語音頁同步更新服務清單；受影響的舊試聽操作停用。

版面修正採 3:1 的表單與說明欄配置，避免說明欄的內容寬度擠壓主表單。長表單獨立捲動；底部返回、刪除與儲存保持可見。

## 驗證

相關服務管理與回歸測試 26 項通過，含實際 Tk 控制項操作、模擬 API 與隔離本機設定。沒有傳送真實金鑰或文字到線上服務。

- [最終測試紀錄](service-management-final-tests.txt)：`python -m unittest` 執行 `test_service_form`、`test_service_management`、`test_voice_desktop`、`test_production_pages`、`test_tts_providers`、`test_kokoro_desktop`。
- [視覺檢查](service-management-visual.txt)：原生 1360×820、1040×640；HTML 1360×820、1040×640、390×844。
- [單一下拉入口](service-management-menu.png)
- [編輯頁](service-management-edit.png)
- [刪除確認](service-management-delete.png)
- [還原視窗](service-management-restored.png)
- [更新後 HTML mock](../mock-ui/service-management-v1/index.html)

五份相關 Python 檔案語法檢查及 `git diff --check` 通過。後續依使用者指示將正式主程式固定更新至 `dist\ebook2mp4`，並補做四個模組的型別檢查與封裝驗證。真實 API 權限及服務額度仍須以使用者的服務設定檢查。

## 固定目錄交付

唯一主程式路徑為 `E:\Leo\Projects\ebook2mp4\dist\ebook2mp4\ebook2mp4.exe`。其他既有版本目錄不更新。建置前先保留該目錄中的 Kokoro ZIP，建置後恢復並核對 SHA-256。

正式 EXE 已重新封裝。32 個封裝模組與目前來源完全一致；主視窗回應正常，可正常關閉，退出碼為 0。原有 Kokoro ZIP 雜湊一致。

型別檢查另修正服務清單更新對尚未建立編輯頁的處理。原有 26 項相關測試通過；本次再針對服務表單、管理與主視窗流程執行 14 項測試。

- [正式建置紀錄](service-management-release-build.txt)
- [四個模組型別檢查](service-management-release-typecheck.txt)
- [最後修正回歸測試](service-management-release-tests.txt)
- [封裝內容與來源核對](service-management-release-package.json)
- [固定路徑 EXE 啟動與正常關閉](service-management-release-startup.json)
- [語音包原始雜湊](service-management-release-resource.json)
- [建置資源清理](service-management-release-cleanup.json)

## 操作驗收

1. 前往「試聽與製作」 → 選擇自訂服務 → 展開「新增／管理服務…」。確認只使用原有的一個入口。
2. 選「編輯目前服務…」 → 修改顯示名稱 → 金鑰留白 → 按「儲存並返回試聽」。確認服務名稱更新。
3. 核對模型、音色、語速與試聽文字。確認原值保留。
4. 再開啟編輯頁 → 輸入新金鑰 → 按「檢查連線與音色」。確認檢查不隱性儲存。
5. 按「取消檢查」 → 按「取消並返回試聽」 → 按「放棄修改」。確認原設定保留。
6. 再開啟編輯頁 → 按「刪除此服務…」 → 按「保留服務」。確認沒有刪除。
7. 按「刪除此服務…」 → 按「確認刪除服務」。確認返回試聽頁並選用 Edge-TTS。
8. 展開服務清單。確認已刪除項目消失。確認試聽文字保留。
9. 選 Edge-TTS → 展開管理選單。確認編輯項目停用。
10. 選 Kokoro → 展開管理選單 → 選「管理本機語音包…」。確認進入原有語音包頁。
11. 還原至 1040×640 → 開啟編輯頁 → 捲動表單。確認底部操作列可見。

驗證用專案、截圖腳本與測試程序於完成後清除。保留正式截圖、測試紀錄與 HTML 提案。
