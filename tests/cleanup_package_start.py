"""Start the fixed release against the isolated cleanup acceptance project."""
from pathlib import Path
import json
import os
import subprocess


def main():
    root = Path.cwd()
    settings = root/'.scratch/cleanup-package-home'
    settings.mkdir(parents=True, exist_ok=True)
    book = root/'.scratch/cleanup-visual/book'
    (settings/'session.json').write_text(json.dumps(dict(last_project=str(book))), encoding='utf-8')
    env = dict(os.environ, PATH=r'C:\Windows\System32;C:\Windows', EBOOK2MP4_APP_HOME=str(settings),
               LOCALAPPDATA=str(settings/'local'), APPDATA=str(settings/'roaming'))
    executable = root/'dist/ebook2mp4/ebook2mp4.exe'
    child = subprocess.Popen([str(executable)], cwd=root, env=env)
    path = root/'docs/verification/manuscript-cleanup-footer/package-startup.json'
    result = dict(executable=str(executable), pid=child.pid, isolated_settings=True, path=env['PATH'])
    path.write_text(json.dumps(result, indent=2),encoding='utf-8')
    try:
        result['exit_code'] = child.wait(timeout=900)
    finally:
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=30)
            result['forced_timeout_stop'] = True
        result['closed'] = child.poll() is not None
        path.write_text(json.dumps(result, indent=2),encoding='utf-8')


if __name__ == '__main__':
    main()
