# 書籍製作工具

使用者在 Windows 本機將一本書的 PDF／TXT 分批校對，確認朗讀稿，再製作批次及全書音訊、字幕與影片。產品事實以 docs/pdf-txt-audiobook-video-spec.md v1.1、GLOSSARY.md 與 docs/adr 為準。

正式介面已選定 A 版校對工作台。繁體中文操作，保留繁中、簡中、英文來源文字；一本書一個專案，各製作批次獨立。資料本機保存、來源不覆寫，只有明確使用線上文字服務時才送出指定內容。

T01／T02 已交付多份 TXT 的匯入、人工編輯、保存及重開，各批次可選取、命名及手動排序。支援 UTF-8／UTF-8 BOM／UTF-16 BOM，自動辨識限 UTF-8 與 BOM；Big5／CP950 由使用者手動選擇並核對預覽。PDF、Gemini、朗讀確認、音訊及影片由後續 tickets 接續；介面明示原因，不模擬成功。已提供的原型只是版面與互動參考。

桌面採 Python 標準函式庫 Tkinter；以 PyInstaller 附帶執行環境。完整安裝包與內附媒體／OCR 工具的乾淨 Windows 驗收屬 T23。
