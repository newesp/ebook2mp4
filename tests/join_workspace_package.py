"""Launch the official EXE in this task's isolated, offline QA project."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import argparse


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--record',default='exe-start.json');args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    work=root/os.environ.get('JOIN_QA_WORK','.scratch/audio-join-review')
    target=root/'dist/ebook2mp4/ebook2mp4.exe'
    env=dict(os.environ,EBOOK2MP4_APP_HOME=str(work/'app-home'),EBOOK2MP4_VOICE_HOME=str(work/'voice-home'),
             EBOOK2MP4_KOKORO_HOME=str(work/'kokoro-home'),LOCALAPPDATA=str(work/'local'),APPDATA=str(work/'roaming'),PATH=r'C:\Windows\System32;C:\Windows')
    for key in ('PYTHONPATH','EBOOK2MP4_FFMPEG','EBOOK2MP4_FFPROBE','EBOOK2MP4_TESSERACT'):env.pop(key,None)
    p=subprocess.Popen([str(target)],cwd=root,env=env)
    evidence=root/os.environ.get('JOIN_QA_EVIDENCE','docs/verification/audio-join-workspace')/args.record
    data=dict(executable=str(target),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),pid=p.pid,isolated=True)
    evidence.write_text(json.dumps(data,indent=2),encoding='utf-8');print(f'Official EXE {p.pid}',flush=True)
    data['exit_code']=p.wait();data['closed']=True
    evidence.write_text(json.dumps(data,indent=2),encoding='utf-8')


if __name__=='__main__':main()
