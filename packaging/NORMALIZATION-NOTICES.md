# 中文校對詞庫

本機候選校對使用 `opencc-python-reimplemented==0.1.7`，Yichen Huang 維護的純 Python OpenCC 實作，使用 BYVoid OpenCC 詞庫。套件來源與操作說明：[PyPI](https://pypi.org/project/opencc-python-reimplemented/)、[原始碼](https://github.com/yichen0831/opencc-python)、[OpenCC](https://github.com/BYVoid/OpenCC)。

採 Apache License 2.0；完整套件授權保留於 `licenses/OpenCC-Python-LICENSE.txt`，PyInstaller 同時收錄套件詞庫、設定與 distribution metadata。使用 `s2t`／`t2s` 字體轉換，不使用地區慣用語替換設定。詞庫並非語言模型，轉換仍可能有歧義，所有結果進候選供人工確認。
