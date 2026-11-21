"""Restore the optional distribution ZIP without rewriting historical evidence.

Use the existing trusted release manifest and the retained K01 source resources.
No downloads, source manifest changes, or inference are performed.
"""
import hashlib
import json
from pathlib import Path
import zipfile

root = Path.cwd()
release_path = root / 'ebook2mp4/kokoro_release.json'
manifest_bytes = release_path.read_bytes()
metadata = json.loads(manifest_bytes)
inventory = json.loads((root / 'docs/verification/kokoro-k01/resource-manifest.json').read_bytes())
sources = {}
for item in inventory:
    original = Path(item['path'])
    name = ('runtime/' + Path(*original.parts[2:]).as_posix()
            if original.parts[0] == 'python' else original.as_posix())
    sources[name] = root / 'outputs/kokoro-k01' / original
sources['worker.py'] = root / 'ebook2mp4/kokoro_worker.py'
archive = root / 'dist/kokoro' / (metadata['id'] + '.zip')
if archive.exists():
    raise SystemExit('Existing archive retained; refusing to overwrite.')
archive.parent.mkdir(parents=True, exist_ok=True)
temporary = archive.with_suffix('.partial')
try:
    with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=3) as output:
        output.writestr('package.json', manifest_bytes)
        for index, entry in enumerate(metadata['files']):
            source = sources[entry['path']]
            assert source.stat().st_size == entry['bytes'], entry['path']
            with source.open('rb') as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == entry['sha256'], entry['path']
            output.write(source, entry['path'])
            if index % 5000 == 0:
                print('Verified and archived', index, flush=True)
    with zipfile.ZipFile(temporary) as output:
        assert output.read('package.json') == manifest_bytes
        assert set(output.namelist()) == {'package.json', *(e['path'] for e in metadata['files'])}
        for entry in metadata['files']:
            with output.open(entry['path']) as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == entry['sha256'], entry['path']
    temporary.replace(archive)
finally:
    temporary.unlink(missing_ok=True)
with archive.open('rb') as stream:
    checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
result = dict(path=str(archive), bytes=archive.stat().st_size, sha256=checksum,
              identity=metadata['id'], verified_payload_files=len(metadata['files']),
              unchanged_release_manifest=release_path.read_bytes() == manifest_bytes,
              all_archive_payload_hashes_match=True)
(root / 'docs/verification/remaining-tickets/voice-archive.json').write_text(
    json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False), flush=True)
