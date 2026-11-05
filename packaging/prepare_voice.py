"""Stage a verified local FFmpeg binary for the Windows preview distribution."""
import hashlib
from pathlib import Path
import shutil
import sys

SHA256 = '228d7a8556258de907fdb55f36850078ebc7680b84ec30d84ea02e99bec1d1eb'
PROBE_SHA256 = '0fde260f5abd35c9cafd96f594cc76365a780c1b73a90e35b6a3409ea1db1bf0'
root = Path(__file__).resolve().parents[1]
source = Path(sys.argv[1]) if len(sys.argv) == 2 else None
if source is None or not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != SHA256:
    raise SystemExit('Pass verified FFmpeg 8.1.1 essentials gyan.dev ffmpeg.exe (see VOICE-NOTICES.md).')
probe = source.with_name('ffprobe.exe')
if not probe.is_file() or hashlib.sha256(probe.read_bytes()).hexdigest() != PROBE_SHA256:
    raise SystemExit('Place the matching verified FFprobe 8.1.1 next to ffmpeg.exe (see VOICE-NOTICES.md).')
target = root / '.scratch/voice-runtime'
target.mkdir(parents=True, exist_ok=True)
shutil.copy2(source, target / 'ffmpeg.exe')
shutil.copy2(probe, target / 'ffprobe.exe')
