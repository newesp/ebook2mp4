"""Launch only the fixed release with isolated settings and a system-only PATH."""
from pathlib import Path
import json
import os
import subprocess
import hashlib

from ebook2mp4.workflow import ProjectWorkflow


def main():
    root = Path.cwd()
    book = root/'.scratch/v6-runtime/book'
    settings = root/'.scratch/v6-package-home'
    settings.mkdir(parents=True, exist_ok=True)
    (settings/'session.json').write_text(json.dumps({'last_project': str(book)}), encoding='utf-8')
    flow = ProjectWorkflow.open(book)
    batch = flow.state['batches'][0]['id']
    text = flow.workspace_state(batch)['text']
    assert flow.texts(batch)[1] == flow.reading_text(batch) == text
    evidence = root/'docs/verification/unified-manuscript-v6'
    (evidence/'native-equality.json').write_text(json.dumps(dict(characters=len(text),
        draft_reading_workspace_equal=True, sha256=hashlib.sha256(text.encode()).hexdigest()),indent=2),encoding='utf-8')
    env = dict(os.environ, PATH=r'C:\Windows\System32;C:\Windows',
        EBOOK2MP4_APP_HOME=str(settings), LOCALAPPDATA=str(settings/'local'), APPDATA=str(settings/'roaming'))
    executable = root/'dist/ebook2mp4/ebook2mp4.exe'
    child = subprocess.Popen([str(executable)], env=env, cwd=root)
    result = dict(executable=str(executable), pid=child.pid, path=env['PATH'],
                  isolated_settings=True, project=str(book), source_snapshot_equal=True)
    output = evidence/'package-startup.json'
    output.write_text(json.dumps(result, indent=2),encoding='utf-8')
    try:
        result['exit_code'] = child.wait(timeout=900)
    finally:
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=30)
            result['forced_timeout_stop'] = True
        result['closed'] = child.poll() is not None
        output.write_text(json.dumps(result, indent=2),encoding='utf-8')


if __name__ == '__main__':
    main()
