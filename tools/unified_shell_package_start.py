"""Launch only the fixed formal EXE against this work's isolated fixture."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'.scratch/v2-shell-refactor'
EVIDENCE=ROOT/'docs/verification/v2-shell-refactor'
book=WORK/'package-book'
if book.exists():
    if '--reuse' not in sys.argv:raise SystemExit('Owned package fixture already exists; pass --reuse to keep it.')
else:shutil.copytree(WORK/'seed-book',book)
home=WORK/'package-home';home.mkdir(exist_ok=True)
(home/'session.json').write_text(json.dumps(dict(last_project=str(book))),encoding='utf-8')
env=dict(os.environ,PATH=r'C:\Windows\System32;C:\Windows',
    EBOOK2MP4_APP_HOME=str(home),EBOOK2MP4_VOICE_HOME=str(WORK/'voice-home'),
    EBOOK2MP4_KOKORO_HOME=str(WORK/'kokoro-home'),EBOOK2MP4_OCR_HOME=str(WORK/'ocr-home'),
    LOCALAPPDATA=str(home/'local'),APPDATA=str(home/'roaming'))
for key in ('PYTHONPATH','PYTHONHOME','EBOOK2MP4_FFMPEG','EBOOK2MP4_FFPROBE'):env.pop(key,None)
exe=ROOT/'dist/ebook2mp4/ebook2mp4.exe'
process=subprocess.Popen([str(exe)],cwd=exe.parent,env=env)
(EVIDENCE/'package-launch.json').write_text(json.dumps(dict(pid=process.pid,executable=str(exe),
    isolated_book=str(book),no_python_path=True,path=env['PATH'],uses_bundled_media_tools=True),indent=2),encoding='utf-8')
print(process.pid,flush=True)
