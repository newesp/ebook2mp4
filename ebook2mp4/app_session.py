"""Per-user startup project location, separate from portable book data."""
import json
import os
from pathlib import Path

from .workflow import ProjectError, ProjectWorkflow, encode


def session_path() -> Path:
    home = os.environ.get('EBOOK2MP4_APP_HOME')
    return (Path(home) if home else
            Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'ebook2mp4') / 'session.json'


def last_project() -> Path | None:
    try:
        data = json.loads(session_path().read_bytes())
        value = data.get('last_project') if isinstance(data, dict) else None
        if not isinstance(value, str) or not value or not Path(value).is_absolute():
            raise ValueError()
        return Path(value)
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        raise ProjectError('無法讀取上次專案記錄。請從「專案 → 開啟專案」重新選擇。') from None


def remember_project(root: Path) -> None:
    try:
        ProjectWorkflow._atomic(session_path(), encode({'last_project': str(root.resolve())}))
    except OSError:
        raise ProjectError('專案已載入，但無法記住專案位置。請檢查本機設定資料夾的寫入權限。') from None
