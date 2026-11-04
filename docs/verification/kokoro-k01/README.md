# K01 官方中文版 CPU 可行性結果

日期：2026-11-04（Asia/Taipei）。來源：[工作票 #3](https://github.com/newesp/ebook2mp4/issues/3)、[父規格 #2](https://github.com/newesp/ebook2mp4/issues/2)。執行前已讀取兩票正文及全部留言；當時兩票留言均為 0。

**結果：官方 Python 推論在本機 CPU 可行，首次離線合成成功。使用者已同意以此結果繼續整合，決定見 [整合授權](integration-decision.md)。** 發音前處理的已知偏差保留；此次授權不代表全部音色通過人工品質驗收。正式 UI、安裝包、ProjectWorkflow、MP3／SRT 及影片整合由後續工作票執行。

## 測試條件

- Windows 11 家用版，10.0.26200，64-bit。
- Intel Core i5-1035G1，4 核心／8 執行緒，實體 RAM 12,633,956,352 bytes。
- 獨立 CPython 3.12.15；主程式仍為 3.14.3。
- 官方 Kokoro 0.9.4、Misaki 0.9.4，PyTorch 2.15.0+cpu。推論指定 CPU、4 個 intra-op 執行緒、1 個 inter-op 執行緒，語速 1.0。沒有 CUDA runtime 或 NVIDIA 推論依賴。
- 官方模型 `hexgrad/Kokoro-82M-v1.1-zh`，修訂 `01e7505bd6a7a2ac4975463114c3a7650a9f7218`。權重 SHA-256 與[官方模型頁](https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh) 公布值一致。
- 備齊 103 個官方音色，其中中文 100 個。短文測 `zf_001`、`zm_010`；1,109 字元的長文只測 `zf_001`。

硬體與依賴證據：[cpu.json](cpu.json)、[environment.json](environment.json)、[requirements-lock.txt](requirements-lock.txt)、[model-manifest.json](model-manifest.json)。

## 實測數據

| 項目 | 實測結果 |
|---|---:|
| 第一個隔離程序冷載入 | 62.97 秒 |
| 其中 import／模型與語言前處理初始化 | 29.30／33.68 秒 |
| 首次短文：45 字元，輸出 12.125 秒 | 合成 13.45 秒，RTF 1.109 |
| 同一短文連續試聽第 1／2 次 | 9.47／6.88 秒；音長均 12.125 秒 |
| 同一短文第 2 次暖試聽 | RTF 0.568 |
| 長稿：1,109 字元 | 合成 177.46 秒，音長 260.75 秒，RTF 0.681 |
| 第一輪模型程序峰值工作集 | 2,015,682,560 bytes，約 1.88 GiB |
| 匯入期間取消，從 kill 到程序結束 | 0.018 秒 |
| 實際權重載入期間取消 | 0.050 秒 |
| 推論期間取消 | 0.123 秒 |
| 閒置後退出 | 5.00 秒觸發；退出另需 3.39 秒；合計約 8.39 秒 |
| 主動關閉 worker | 2.69 秒；補測 2.47 秒 |

RTF＝合成耗時／音訊長度，包含前處理、推論、寫 WAV 與完整解碼。以上為單機單次實測，沒有預設通過門檻。冷載入是新程序與空應用快取，Windows 檔案頁快取未清空，不是重開機冷碟量測。5 秒閒置為實驗設定，尚未核定為產品預設。長稿執行超過 5 秒，未被閒置機制中止。

完整資源為 **1,417,314,476 bytes（約 1.32 GiB）**、28,965 個檔案；其中模型與音色為 381,160,391 bytes。已排除並清除 bytecode，也不重複計算 uv 的版本目錄連結。逐檔雜湊見 [resource-size.json](resource-size.json)、[resource-manifest.json](resource-manifest.json)。這是未裁剪的實驗資源解壓大小，不是正式壓縮語音包大小；未製作正式安裝包。runtime、模型及依賴授權保留於專案 `outputs/kokoro-k01`。

## CPU 與離線證據

6 個 worker 各使用新建且空白的 HOME、Hugging Face、Torch、XDG 及 TEMP 目錄。模型與音色使用已備妥的本地明確路徑。Windows 防火牆只封鎖該專用 Python 的 outbound 網路；每個 worker 先對 `1.1.1.1:443` 探測，實際收到 Windows 10013 存取拒絕，再開始載入。Python audit guard 額外攔截 DNS、connect 與 UDP；正式測試沒有任何額外網路嘗試。暫存只產生 Jieba 分詞快取，沒有新增模型或語言下載。

第一次防火牆測試因 uv 的 `3.12` 目錄連結而未生效，測試已立即失敗。改用實體 `3.12.15` 執行檔路徑後，探測才確實遭拒。保留 [initial-firewall-probe.json](initial-firewall-probe.json) 與 [initial-firewall-probe-failure.txt](initial-firewall-probe-failure.txt)，不把初次失敗當作離線通過。

成功證據：[first-offline.json](first-offline.json)、[lifecycle.json](lifecycle.json)、[extra-lifecycle.json](extra-lifecycle.json)、[firewall-active.json](firewall-active.json)、[extra-firewall-active.json](extra-firewall-active.json)。所有成功載入事件皆記錄 `devices=["cpu"]`、`cuda=null`。

## 品質結果與試聽

保留 17 份 WAV，包括兩音色的 6 類短文、女聲長稿、繁體未轉換對照，以及首次／重啟／暖試聽紀錄。音檔為 24 kHz、單聲道、16-bit PCM；全部完整解碼，原文與固定語料一致。沒有樣本達到數位削波上限，沒有未知音素；每塊最多 136 個音素。區塊完整覆蓋合成副本，未使用官方長文流程的 510 音素靜默截斷路徑。這些數據不代表沒有可聽見的錯讀或裁尾。

**已確認的前處理問題**：`1,280` 的千位逗號被錯誤處理、`007` 失去前導零、電話分機 `1234` 被當作數量，以及「這件事得好好處理」的「得」音素不正確。`MP3／MP4` 的數字轉為中文；是否可接受須由使用者決定。

直接試聽：[女聲中英夾讀](audio/mixed-zf_001-t2s.wav)、[男聲中英夾讀](audio/mixed-zm_010-t2s.wav)、[數字偏差](audio/numbers-zf_001-t2s.wav)、[4 分 20.75 秒長稿](audio/long-zf_001-t2s.wav)。

[固定原文](corpus.md)、[完整試聽與品質表](quality-review.md)、[音檔驗證](audio-validation.json)、[原文驗證](original-text-validation.json)、[驗證摘要](validation-summary.json)。每個 WAV 同名 JSON 提供每塊音素與起訖秒數。

誤讀偏差已列出；實際漏句、重複、裁尾、語速異常、自然度及台灣口音均待人工試聽。沒有以自動語音辨識替代人工聆聽。兩個受測音色不代表其餘 98 個中文音色通過。長稿測試不代表整本書穩定性已驗收。

## 相容性與實作成本

官方引擎及 Misaki 來源修改 **0 行**，依套件 RECORD 核對：[official-package-integrity.json](official-package-integrity.json)。官方 Kokoro 宣告 Python `>=3.10,<3.13`；本票透過獨立 3.12 解決相容性，不升降主程式 Python。

新增的是隔離驗證工具：CPU 子程序、生命週期控制、Windows 防火牆測試、固定樣本、資源清單與量測。合成副本可用 OpenCC t2s，另接官方英文 G2P；原文不變。句末分塊後檢查音素上限，再呼叫官方 `generate_from_tokens`；未重寫模型。已知數字與詞語問題尚未加特例修補。

下一階段的成本主要是前處理政策與回歸語料、包體裁剪及授權審查、正式 worker 管理、設定／快取身分、UI 設計及 ProjectWorkflow 整合。這些不能由本次 CPU 合成成功直接視為完成。工具與重跑路徑見 [tools/kokoro_k01/README.md](../../../tools/kokoro_k01/README.md)。

## 清理與既有變更

保留實驗 runtime／模型、需求文件、錄音與最終證據，包括工作前差異快照 `preexisting.patch`。刪除本次下載／建置快取、隔離 HOME／語言快取與 bytecode；不刪除工作前資料。所有測試 worker 已退出；權重、音色、執行檔及 CPU 推論 DLL 以獨占讀取確認可解除占用。兩輪防火牆規則均移除。

證據：[cleanup.json](cleanup.json)、[file-release.json](file-release.json)、[firewall-cleanup.json](firewall-cleanup.json)、[extra-firewall-cleanup.json](extra-firewall-cleanup.json)、[workspace-preserved.json](workspace-preserved.json)。工作前已修改的四個正式程式檔 SHA-256 保持一致，既有未追蹤檔案保留。

## 使用者驗收路徑（ASD-STE100 風格）

| 項目 | 操作路徑與可觀察結果 |
|---|---|
| 女聲 | 開啟女聲音檔 → 按下「播放」 → 對照固定原文 → 記錄錯音與時間。 |
| 男聲 | 開啟男聲音檔 → 按下「播放」 → 對照同一原文 → 選出偏好音色。 |
| 數字 | 開啟數字音檔 → 按下「播放」 → 檢查金額與編號 → 確認已知偏差。 |
| 長稿 | 開啟長稿音檔 → 按下「播放」 → 逐節對照原文 → 檢查漏句與重複 → 確認最後聽見「晚安」。 |
| CPU | 開啟 `first-offline.json` → 找到 `ready` → 確認 `devices` 為 `cpu` → 確認 `cuda` 為 `null`。 |
| 離線 | 開啟 `first-offline.json` → 找到 `os_network_probe` → 確認 `blocked=true` → 找到後續 `completed`。 |
| 效能 | 開啟本報告的實測表 → 檢查冷載入與長稿耗時 → 決定等待時間是否可接受。 |
| 取消 | 開啟 `cancel-model-load.json` → 確認 `pid_alive=false` → 開啟 `cancel-inference.json` → 確認 `pid_alive=false`。 |
| 釋放 | 開啟 `cleanup.json` → 確認 `remainingProcesses=0` → 確認 `scratchExists=false` → 確認規則不在 → 確認獨占讀取成功。 |
| 保留變更 | 開啟 `workspace-preserved.json` → 檢查四個檔案 → 確認各列 `unchanged=true`。 |

## 審閱決定

使用者已確認「可以繼續整合」。可行性審閱已接受，不要求先選偏好音色；詳見 [整合決定](integration-decision.md)。全部 100 種中文音色將在 UI 讓使用者自行選擇與試聽。數字與多音字政策仍需隨後續整合明確保存；UI 設計圖另行確認。未在 GitHub 發布留言或更改議題狀態。
