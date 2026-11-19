"""Launch the official build against an isolated synthetic project for UI review."""
import hashlib
import json
import os
from pathlib import Path
import subprocess


def main():
    root = Path(__file__).resolve().parents[1]
    temporary = root / '.scratch/audio-production-package'
    home = temporary / 'app-home'
    home.mkdir(parents=True, exist_ok=True)
    book = temporary / 'book'
    if not book.is_dir():
        raise RuntimeError('Copy an isolated fixture book before running this check.')
    (home / 'session.json').write_text(json.dumps({'last_project': str(book)}), encoding='utf-8')
    executable = root / 'dist/ebook2mp4/ebook2mp4.exe'
    env = dict(os.environ, EBOOK2MP4_APP_HOME=str(home),
               EBOOK2MP4_VOICE_HOME=str(temporary/'voice-home'),
               EBOOK2MP4_KOKORO_HOME=str(temporary/'kokoro-home'),
               LOCALAPPDATA=str(temporary/'local'), APPDATA=str(temporary/'roaming'),
               PATH=r'C:\Windows\System32;C:\Windows')
    process = subprocess.Popen([str(executable)], cwd=root, env=env)
    evidence = root / 'docs/verification/audio-production-ui/package-check.json'
    result = dict(executable=str(executable), pid=process.pid, isolated_project=True,
                  sha256=hashlib.sha256(executable.read_bytes()).hexdigest(), started=True)
    evidence.write_text(json.dumps(result, indent=2), encoding='utf-8')
    try:
        result['exit_code'] = process.wait(timeout=600)
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=30)
            result['forced_timeout_stop'] = True
        result['closed'] = process.poll() is not None
        evidence.write_text(json.dumps(result, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
