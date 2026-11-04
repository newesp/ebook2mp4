# K01 官方中文版 CPU 實驗

這是議題 [#3](https://github.com/newesp/ebook2mp4/issues/3) 的可重現驗證工具。父規格為 [#2](https://github.com/newesp/ebook2mp4/issues/2)。它不修改正式 UI、ProjectWorkflow、既有服務或系統 Python，不是 K04／K09 的正式安裝包。

## 已固定的來源

- Python：uv 提供的獨立 CPython 3.12.15，位於 `outputs/kokoro-k01/python`。主程式仍為 Python 3.14.3。
- 模型：`hexgrad/Kokoro-82M-v1.1-zh`，修訂 `01e7505bd6a7a2ac4975463114c3a7650a9f7218`。
- 權重 SHA-256：`b1d8410fa44dfb5c15471fd6c4225ea6b4e9ac7fa03c98e8bea47a9928476e2b`。
- 官方 Kokoro 0.9.4、Misaki 0.9.4；精確依賴見 `docs/verification/kokoro-k01/requirements-lock.txt`。
- 英文前處理：官方 Misaki 英文字典、spaCy `en_core_web_sm` 3.8.0、套件所附 eSpeak NG 程式庫與資料。不使用 transformer 英文模型。
- 103 個官方音色全部下載，其中中文 100 個。只取 `zf_001`、`zm_010` 做完整短樣本，長稿只測 `zf_001`。

## 重跑

所有命令從專案根目錄執行。以下為開發驗證命令，不是最終桌面使用者操作方式。

1. 下載專用 Python。將 `UV_CACHE_DIR` 指向專案 `.scratch/k01/uv-cache`；將 `UV_PYTHON_INSTALL_DIR` 指向 `outputs/kokoro-k01/python`。執行 `uv python install 3.12.15 --no-bin`。
2. 以該 Python 執行環境安裝 `requirements-lock.txt` 的版本。CPU 索引為 `https://download.pytorch.org/whl/cpu`；其他依賴來自 PyPI；spaCy 英文模型使用鎖定檔中的官方 URL。只對這個專用可攜目錄使用 uv 的 `--break-system-packages`。
3. 執行 `C:\Python314\python.exe tools/kokoro_k01/prepare.py`。核對官方模型修訂及每檔 SHA-256。
4. 確認 `.scratch/k01/runtime` 不存在。前次驗證產物須先另存；本工具會覆寫同名證據。
5. 在具備新增防火牆規則權限的 PowerShell 執行 `./tools/kokoro_k01/verify.ps1`。
6. 執行 `./tools/kokoro_k01/verify.ps1 -Extra`，補測權重載入中取消與相同文字暖試聽。
7. 執行 `outputs/kokoro-k01/python/cpython-3.12-windows-x86_64-none/python.exe -B tools/kokoro_k01/finalize.py`。
8. 依驗證報告檢查音檔與生命週期證據。結束驗證後執行 `./tools/kokoro_k01/cleanup.ps1`，清除本次 `.scratch/k01` 與 bytecode，檢查程序、規則與資源占用；保留證據與 `outputs/kokoro-k01` 實驗資源。資源清單排除 bytecode，不因清理而失效。

`verify.ps1` 先解析 Python 的實際路徑，再針對該執行檔建立 outbound block 規則。每個 worker 在安裝 Python audit guard **之前**，先對 `1.1.1.1:443` 執行真實連線探測；連線成功就停止，不會誤列離線通過。探測後，audit guard 額外拒絕 Python 連線、DNS 及 UDP 傳送，並設 Hugging Face／Transformers 離線模式。每個 worker 都使用新建且空白的 HOME、HF、Torch、XDG、TEMP 目錄。模型只以本地路徑載入，無需模型快取。

只允許本工具新增的單一防火牆規則；`finally` 移除規則。不變更整台電腦的連線或預設防火牆政策。若強制結束 PowerShell 而無法執行 `finally`，依 `firewall.json` 中的規則名稱移除殘留規則，再重跑。

## 推論與文字政策

模型及所有參數明確指定 CPU。PyTorch 使用 4 個 intra-op 執行緒、1 個 inter-op 執行緒，語速 1.0。量測包含 G2P、推論及 WAV 寫入／完整解碼；載入時間分列 import 與模型／前處理初始化。冷載入是新程序與新應用快取，**不是重新開機或清空 Windows 檔案頁快取**。RTF 是合成耗時除以音訊長度；小於 1 代表該次合成快於播放。

繁簡轉換只作用於合成副本；JSON 保留原文、SHA-256、合成文字、每塊音素及音訊時間範圍。長文先依句末切分，超過 510 音素時繼續分割，逐塊確認不超限，再呼叫官方 `generate_from_tokens`。這繞開官方 `__call__` 的靜默截斷路徑，未修改引擎或權重。所有合成文字必須被區塊連接完整還原。這可證明文字覆蓋與沒有音素截斷，不能取代人工檢查實際漏讀或重複。

本票只量測實驗 worker。5 秒閒置退出是**測試設定**，用來觀察資源釋放，尚未核定為桌面產品預設。worker 在同步合成時不檢查閒置計時。取消直接結束獨立推論程序；後續正式 UI 取消、父程序意外終止、安裝／移除及整本書流程屬後續工作票。

## 證據與授權

最終量測、人工驗收表及音檔位於 `docs/verification/kokoro-k01`。實驗 runtime／模型／音色與依賴授權位於 `outputs/kokoro-k01`。保留各套件原有授權與額外複製的 notices；這不是已完成再散布驗收的正式語音包。初次防火牆失敗證據保留，避免把未生效的規則當作離線證明。

不得將模型可產生音檔解讀為聽感通過。人工聽感、台灣用語讀音及效能可接受性需由使用者審閱；只有兩個音色的測試結果，不能推論其他 98 個中文音色的品質。
