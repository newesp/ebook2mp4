"""Stage a verified local FFmpeg binary for the Windows preview distribution."""
import hashlib
from pathlib import Path
import shutil
import sys

SHA256 = '228d7a8556258de907fdb55f36850078ebc7680b84ec30d84ea02e99bec1d1eb'
root = Path(__file__).resolve().parents[1]
source = Path(sys.argv[1]) if len(sys.argv) == 2 else None
if source is None or not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != SHA256:
    raise SystemExit('Pass verified FFmpeg 8.1.1 essentials gyan.dev ffmpeg.exe (see VOICE-NOTICES.md).')
target = root / '.scratch/voice-runtime'
target.mkdir(parents=True, exist_ok=True)
shutil.copy2(source, target / 'ffmpeg.exe')
