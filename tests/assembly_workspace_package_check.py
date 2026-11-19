"""Launch only the official EXE with this task's isolated synthetic project."""
import hashlib
import json
import os
from pathlib import Path
import subprocess


def main():
    root=Path(__file__).resolve().parents[1]
    work=root/'.scratch/audio-assembly-review'
    evidence=root/'docs/verification/audio-assembly-workspace/package-startup.json'
    executable=root/'dist/ebook2mp4/ebook2mp4.exe'
    if not (work/'book/book.json').exists() and not (work/'book/project.json').exists():
        # The workflow validates the exact project manifest on opening.
        from ebook2mp4.workflow import ProjectWorkflow
        ProjectWorkflow.open(work/'book')
    env=dict(os.environ,EBOOK2MP4_APP_HOME=str(work/'app-home'),
             EBOOK2MP4_VOICE_HOME=str(work/'voice-home'),EBOOK2MP4_KOKORO_HOME=str(work/'kokoro-home'),
             LOCALAPPDATA=str(work/'local'),APPDATA=str(work/'roaming'),PATH=r'C:\Windows\System32;C:\Windows')
    for key in ('EBOOK2MP4_FFMPEG','EBOOK2MP4_FFPROBE','EBOOK2MP4_TESSERACT','PYTHONPATH'):env.pop(key,None)
    process=subprocess.Popen([str(executable)],cwd=root,env=env)
    result=dict(executable=str(executable),sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),
                pid=process.pid,isolated_project=True,started=True)
    evidence.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(f'Official EXE started: {process.pid}',flush=True)
    result['exit_code']=process.wait()
    result['closed']=True
    evidence.write_text(json.dumps(result,indent=2),encoding='utf-8')


if __name__=='__main__':main()
