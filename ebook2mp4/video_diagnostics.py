"""Local video error classification and tolerant FFmpeg progress parsing."""


def progress_time(raw: str | None) -> int | None:
    try:
        return max(0, int(raw)//1000) if raw is not None else None
    except (ValueError, TypeError):
        # N/A is normal before the encoder emits its first packet.
        return None


def diagnose(detail: str, *, category: str | None = None) -> dict:
    text = detail.lower()
    if category is None:
        groups = (
            ('space', ('no space left', 'disk full', '磁碟空間不足', 'winerror 112', 'errno 28')),
            ('permission', ('permission denied', 'access is denied', '存取被拒', '拒絕存取', 'winerror 5', 'errno 13', 'used by another process', 'winerror 32')),
            ('memory', ('cannot allocate memory', 'out of memory', 'resource temporarily unavailable')),
            ('tool', ('unknown encoder', 'encoder not found', 'unrecognized option', 'no such filter', 'winerror 2', '找不到指定的檔案')),
            ('media', ('invalid data', 'error while decoding', 'corrupt', 'invalid nal', 'moov atom not found')),
        )
        category = next((name for name, terms in groups if any(term in text for term in terms)), 'encoding')
    messages = {
        'space': '製片空間不足。請清出專案所在磁碟的空間 → 按「重試製片」。',
        'permission': '影片檔案無法寫入或被占用。請關閉占用成品的播放器 → 確認專案資料夾可寫入 → 按「重試製片」。',
        'memory': '製片可用記憶體或系統資源不足。請關閉其他大型程式 → 改選 720p → 按「重試製片」。',
        'tool': '媒體工具缺少或版本不相容。請重新解壓完整 ebook2mp4 資料夾 → 開啟程式 → 重試製片。',
        'media': '素材無法完整解碼。請先用播放器檢查素材 → 重新匯出為 H.264 MP4 或改選另一個素材 → 重試製片。',
        'timeout': '媒體處理逾時。請改用較短或較低解析度的背景 → 重試製片。',
        'internal': '製片程式發生非預期錯誤。請查看「來源詳情」的失敗診斷，提供錯誤類型與步驟以便修正。',
        'encoding': '媒體編碼失敗。請查看「來源詳情」的失敗診斷 → 確認素材可播放 → 改選另一個素材後重試製片。',
    }
    return dict(category=category, message=messages[category], detail=detail[-16384:])
