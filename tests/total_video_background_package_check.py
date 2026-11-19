"""Read-only packaged-source and bundled-tool verification for the fixed distribution."""
import hashlib
import json
from pathlib import Path
import subprocess
import types

from PyInstaller.archive.readers import CArchiveReader


def normalized(code):
    if not isinstance(code, types.CodeType):
        return code
    return (code.co_code, tuple(normalized(c) for c in code.co_consts), code.co_names, code.co_varnames,
            code.co_cellvars, code.co_freevars, code.co_argcount, code.co_posonlyargcount, code.co_kwonlyargcount,
            code.co_nlocals, code.co_stacksize, code.co_flags, code.co_firstlineno, code.co_linetable, code.co_exceptiontable)


def run():
    root = Path.cwd()
    exe = root/'dist/ebook2mp4/ebook2mp4.exe'
    archive = CArchiveReader(str(exe)).open_embedded_archive('PYZ.pyz')
    rows = []
    excluded = []
    for path in sorted((root/'ebook2mp4').glob('*.py')):
        name = 'ebook2mp4' if path.stem == '__init__' else 'ebook2mp4.'+path.stem
        if name not in archive.toc:
            assert path.stem in ('__main__', 'kokoro_worker', 'ui_mock'), name
            excluded.append(name)  # Separate CLI entry and independently packaged inference worker.
            continue
        compiled = compile(path.read_bytes(), str(path), 'exec', dont_inherit=True)
        same = normalized(compiled) == normalized(archive.extract(name))
        assert same, name
        rows.append(dict(module=name, matches=True))
    tools = []
    for name in ('ffmpeg', 'ffprobe'):
        path = exe.parent/'_internal/tools/ffmpeg'/(name+'.exe')
        version = subprocess.check_output([str(path), '-version'], creationflags=subprocess.CREATE_NO_WINDOW).decode().splitlines()[0]
        tools.append(dict(name=name, version=version, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    result = dict(path=str(exe), sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
                  files=sum(p.is_file() for p in exe.parent.rglob('*')), modules=rows, tools=tools, excluded=excluded)
    (root/'docs/verification/T17/package.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'All {len(rows)} packaged application modules match current sources; both media tools run.')


if __name__ == '__main__':
    run()
