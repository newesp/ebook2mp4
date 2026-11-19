"""Create once, then verify the immutable v1 source and complete onedir copy."""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'archives/v1'
EVIDENCE = ROOT / 'docs/verification/v1-baseline'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inventory(base):
    return [dict(path=p.relative_to(base).as_posix(), bytes=p.stat().st_size, sha256=sha(p))
            for p in sorted(base.rglob('*')) if p.is_file() and '__pycache__' not in p.parts]


def git(*args):
    return subprocess.check_output(['git', '-c', f'safe.directory={ROOT.as_posix()}', *args],
                                   cwd=ROOT).decode('utf-8')


def capture():
    if ARCHIVE.exists() and any(ARCHIVE.iterdir()):
        raise RuntimeError('Nonempty archive: verify it; never overwrite it.')
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    package = json.loads((EVIDENCE/'package.json').read_text(encoding='utf-8'))
    assert all(row['matches'] for row in package['modules'])
    source = ARCHIVE/'source'
    source.mkdir(parents=True)
    directories = ('ebook2mp4', 'tests', 'packaging', 'tools', 'docs', '.impeccable',
                   '.scratch/pdf-txt-audiobook-video')
    for name in directories:
        path = ROOT/name
        if path.is_dir():
            shutil.copytree(path, source/name,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.mypy_cache'))
    for path in ROOT.iterdir():
        if path.is_file():
            shutil.copy2(path, source/path.name)
    shutil.copytree(ROOT/'dist/ebook2mp4', ARCHIVE/'ebook2mp4')
    # Runtime tools are retained verbatim with the complete distribution. The
    # source build spec expects copies in .scratch; do not include build caches.
    files = inventory(ARCHIVE)
    versions = {p: importlib.metadata.version(p) for p in
                ('pyinstaller', 'edge-tts', 'pypdfium2', 'pillow', 'opencc-python-reimplemented')}
    manifest = dict(product='ebook2mp4 v1', captured_utc=datetime.now(timezone.utc).isoformat(),
        git_head=git('rev-parse', 'HEAD').strip(), git_status=git('status', '--porcelain'),
        source_identity='complete working tree snapshot including necessary untracked sources',
        python=sys.version, dependencies=versions, package=package,
        source_command='python -m ebook2mp4 (cwd=archives/v1/source; install packaging/requirements-runtime.txt)',
        executable='ebook2mp4/ebook2mp4.exe',
        rebuild='Copy ebook2mp4/_internal/tools/{ffmpeg,tesseract} to source/.scratch/{voice-runtime,ocr-runtime}; build.py outputs source/dist/ebook2mp4.',
        excluded=['.git', 'archives', 'dist (copied separately)', 'outputs',
                  'user books/settings/keys/models', 'build dependencies/caches', 'test temporaries'],
        limitations=['No clean Windows installation or real paid cloud service acceptance.',
                     'Optional OCR models and Kokoro packages are user-installed; see packaging notices.'],
        files=files)
    (ARCHIVE/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    (EVIDENCE/'working-tree.patch').write_bytes(subprocess.check_output(
        ['git', '-c', f'safe.directory={ROOT.as_posix()}', 'diff', '--binary'], cwd=ROOT))
    verify('capture-verification.json')


def verify(name='archive-verification.json'):
    manifest = json.loads((ARCHIVE/'manifest.json').read_text(encoding='utf-8'))
    expected = manifest['files']
    actual = inventory(ARCHIVE)
    actual = [row for row in actual if row['path'] != 'manifest.json']
    assert expected == actual, 'Archive changed or has extra/missing files'
    result = dict(verified_utc=datetime.now(timezone.utc).isoformat(), files=len(actual),
                  bytes=sum(row['bytes'] for row in actual), all_hashes_match=True,
                  manifest_sha256=sha(ARCHIVE/'manifest.json'))
    (EVIDENCE/name).write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('capture', 'verify'))
    args = parser.parse_args()
    capture() if args.action == 'capture' else verify()
