"""Verify the fixed distribution's application code and bundled media tools."""
import hashlib
import json
from pathlib import Path
import subprocess

from PyInstaller.archive.readers import CArchiveReader
from batch_video_package_check import normalized


root = Path(__file__).resolve().parents[1]
exe = root/'dist/ebook2mp4/ebook2mp4.exe'
archive = CArchiveReader(str(exe)).open_embedded_archive('PYZ.pyz')
rows = []
for path in sorted((root/'ebook2mp4').glob('*.py')):
    name = 'ebook2mp4' if path.stem == '__init__' else 'ebook2mp4.'+path.stem
    if name not in archive.toc:
        assert path.stem in ('__main__', 'kokoro_worker', 'ui_mock'), name
        continue
    same = normalized(compile(path.read_bytes(), str(path), 'exec', dont_inherit=True)) == normalized(archive.extract(name))
    rows.append(dict(module=name, matches=same))
assert all(r['matches'] for r in rows), [r for r in rows if not r['matches']]
assert {'ebook2mp4.outputs', 'ebook2mp4.outputs_desktop'} <= {r['module'] for r in rows}
tools = []
for name in ('ffmpeg', 'ffprobe'):
    path = exe.parent/'_internal/tools/ffmpeg'/(name+'.exe')
    version = subprocess.check_output([str(path), '-version'], creationflags=subprocess.CREATE_NO_WINDOW).decode().splitlines()[0]
    tools.append(dict(name=name, version=version, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
result = dict(path=str(exe), sha256=hashlib.sha256(exe.read_bytes()).hexdigest(), modules=rows, tools=tools,
              files=sum(p.is_file() for p in exe.parent.rglob('*')))
(root/'docs/verification/T21/package.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(f'All {len(rows)} packaged modules match; both bundled media tools run.')
