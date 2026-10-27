# T09 語音依賴與工具

- `edge-tts==7.3.1`，LGPL-3.0，原始碼與版本：[rany2/edge-tts 7.3.1](https://github.com/rany2/edge-tts/tree/7.3.1)。授權原文隨包 `licenses/Edge-TTS-LICENSE.txt`。7.2.8 在 2026-10-27 真實測試收到 HTTP 403；7.3.1 通過。
- aiohttp、certifi、typing-extensions 與其他 Python 依賴由 PyInstaller 收錄；certifi CA bundle 明確收錄，不停用 HTTPS 憑證驗證。此版本不要求 Microsoft Edge 瀏覽器或 GPU。
- 試聽採 FFmpeg 8.1.1 `essentials_build-www.gyan.dev`，Windows x64，GPL version 3 or later。來源：[Gyan Windows builds](https://www.gyan.dev/ffmpeg/builds/)、[FFmpeg n8.1.1](https://github.com/FFmpeg/FFmpeg/tree/n8.1.1)。本次重用本機已安裝的相同工具，不執行安裝程式。`ffmpeg.exe` 大小 101,457,920 bytes，SHA-256 `228d7a8556258de907fdb55f36850078ebc7680b84ec30d84ea02e99bec1d1eb`。
- 執行 `python packaging/prepare_voice.py <ffmpeg.exe 的完整路徑>` 校驗後放入 `.scratch/voice-runtime`，PyInstaller 收錄為 `_internal/tools/ffmpeg/ffmpeg.exe`；授權全文為 `licenses/FFmpeg-LICENSE.txt`。不依賴系統 PATH 的 FFmpeg。
- 開發時可設 `EBOOK2MP4_FFMPEG` 明確指定工具、`EBOOK2MP4_VOICE_HOME` 指定音色快取目錄。一般使用者從完整封裝直接啟動。
- T23 仍需整理所有依賴及 FFmpeg build configuration 對應的完整源碼／交付義務與乾淨 Windows 安裝驗收；本開發成品及以上來源連結不等於已完成 T23 發布驗收。
