"""Build-time only: fetch and verify Windows OCR runtime, never run its installer."""
from pathlib import Path
import argparse
import hashlib
import shutil
import subprocess
import tempfile
import urllib.request

import pefile

ROOT = Path(__file__).resolve().parents[1]
URL = ('https://github.com/UB-Mannheim/tesseract/releases/download/'
       'v5.4.0.20240606/tesseract-ocr-w64-setup-5.4.0.20240606.exe')
SHA256 = 'c885fff6998e0608ba4bb8ab51436e1c6775c2bafc2559a19b423e18678b60c9'


def prepare(archive_path: Path | None = None):
    seven = shutil.which('7z') or 'C:/Program Files/7-Zip/7z.exe'
    target = ROOT / '.scratch/ocr-runtime'
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target) as directory:
        base = Path(directory)
        archive = base / 'engine.exe'
        if archive_path:
            shutil.copy2(archive_path, archive)
        else:
            with urllib.request.urlopen(URL, timeout=60) as response, archive.open('wb') as output:
                shutil.copyfileobj(response, output)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
            raise RuntimeError('Tesseract archive SHA-256 mismatch')
        extracted = base / 'engine'
        result = subprocess.run([seven, 'x', str(archive), f'-o{extracted}', '-y'],
                                capture_output=True, check=False)
        if result.returncode not in (0, 1) or not (extracted / 'tesseract.exe').is_file():
            raise RuntimeError('Cannot extract verified Tesseract archive; install build-time 7-Zip')
        # Only ship the recursive runtime dependency closure, no training executables/models.
        pending, seen = ['tesseract.exe'], set()
        files = {p.name.lower(): p for p in extracted.iterdir() if p.is_file()}
        while pending:
            name = pending.pop().lower()
            if name in seen:
                continue
            seen.add(name)
            source = files[name]
            with pefile.PE(str(source)) as image:
                pending.extend(e.dll.decode().lower() for e in image.DIRECTORY_ENTRY_IMPORT
                               if e.dll.decode().lower() in files)
            shutil.copy2(source, target / source.name)
        shutil.copytree(extracted / 'doc', target / 'doc', dirs_exist_ok=True)
    shutil.copy2(ROOT / 'packaging/OCR-NOTICES.md', target / 'OCR-NOTICES.md')
    print(f'Prepared {len(seen)} OCR runtime files at {target}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, help='Existing archive; SHA-256 is always verified')
    prepare(parser.parse_args().archive)
