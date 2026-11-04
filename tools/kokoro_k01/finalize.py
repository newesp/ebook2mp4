"""Validate retained audio, inventory experiment resources and preserve license notices."""
import ctypes
import base64
from ctypes import wintypes
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import sys
import wave

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT/'docs/verification/kokoro-k01'
BUNDLE = ROOT/'outputs/kokoro-k01'


def exclusive_open(path):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                                  wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateFileW(str(path), 0x80000000, 0, None, 3, 0x80, None)
    if handle == wintypes.HANDLE(-1).value:
        return dict(path=str(path.relative_to(BUNDLE)), exclusive_read=False, winerror=ctypes.get_last_error())
    kernel.CloseHandle(handle)
    return dict(path=str(path.relative_to(BUNDLE)), exclusive_read=True)


def main():
    environment = json.loads((EVIDENCE/'environment.json').read_text(encoding='utf-8'))
    assert environment['dependencies']['torch'].endswith('+cpu')
    assert not any(name.lower().startswith('nvidia-') for name in environment['dependencies'])
    requirements = [
        'https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl'
        if k.lower().replace('_','-') == 'en-core-web-sm' else f'{k}=={v}'
        for k,v in sorted(environment['dependencies'].items())
    ]
    (EVIDENCE/'requirements-lock.txt').write_text('\n'.join(requirements)+'\n',encoding='utf-8')
    audio_rows = []
    originals = []
    samples = {s['id']:s['text'] for s in json.loads(Path(__file__).with_name('samples.json').read_text(encoding='utf-8'))}
    for path in sorted((EVIDENCE/'audio').glob('*.wav')):
        data = json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
        sample_id = 'traditional' if data['id'].startswith('warm-repeat-') else data['id']
        assert data['original'] == samples[sample_id]
        assert hashlib.sha256(data['original'].encode()).hexdigest() == data['original_sha256']
        originals.append(dict(file=path.with_suffix('.json').name,original_matches_corpus=True))
        with wave.open(str(path)) as wav:
            assert (wav.getnchannels(),wav.getsampwidth(),wav.getframerate()) == (1,2,24000)
            assert len(wav.readframes(wav.getnframes())) == wav.getnframes()*2
            assert abs(wav.getnframes()/24000-data['audio_seconds']) < .001
        assert hashlib.file_digest(path.open('rb'),'sha256').hexdigest() == data['sha256']
        assert ''.join(s['text'] for s in data['segments']) == data['synthesis']
        assert all(len(s['phonemes']) <= 510 for s in data['segments'])
        unknown = sorted({p for s in data['segments'] for p in s.get('unknown_characters',[])})
        audio_rows.append(dict(file=path.name, sha256=data['sha256'], characters=len(data['original']),
                               audio_seconds=data['audio_seconds'], synthesis_seconds=data['seconds'],
                               rtf=data['real_time_factor'], segments=len(data['segments']),
                               unknown_phoneme_symbols=unknown, clipped_samples=data['clipped_samples']))
    assert len(audio_rows) == 17, f'Expected 17 retained recordings, got {len(audio_rows)}'
    (EVIDENCE/'audio-validation.json').write_text(json.dumps(audio_rows, ensure_ascii=False, indent=2), encoding='utf-8')
    (EVIDENCE/'original-text-validation.json').write_text(json.dumps(originals,indent=2),encoding='utf-8')
    lifecycle = json.loads((EVIDENCE/'lifecycle.json').read_text())
    assert len(lifecycle)==4 and all(not x['pid_alive'] for x in lifecycle)
    assert all(any(e['event']=='os_network_probe' and e['blocked'] for e in x['events']) for x in lifecycle)
    assert all(not any(e['event']=='network_denied' for e in x['events']) for x in lifecycle)
    extra = json.loads((EVIDENCE/'extra-lifecycle.json').read_text())
    assert len(extra)==2 and all(not x['pid_alive'] for x in extra)
    assert all(any(e['event']=='os_network_probe' and e['blocked'] for e in x['events']) for x in extra)
    assert all(not any(e['event']=='network_denied' for e in x['events']) for x in extra)
    # A real shared-library runtime is still active in this finalizer. Check model/voices only.
    locks = [exclusive_open(p) for p in (BUNDLE/'model').rglob('*') if p.suffix in ('.pth','.pt')]
    assert all(x['exclusive_read'] for x in locks)
    (EVIDENCE/'file-release.json').write_text(json.dumps(locks,indent=2),encoding='utf-8')
    notices = BUNDLE/'notices'
    notices.mkdir(exist_ok=True)
    licenses = []
    for distribution in importlib.metadata.distributions():
        name = distribution.metadata['Name']
        copied = []
        for entry in distribution.files or []:
            if any(part.lower().startswith(('license','copying','notice','authors')) for part in entry.parts):
                source = Path(distribution.locate_file(entry))
                if source.is_file():
                    target = notices/name/str(entry).replace('../','')
                    target.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copyfile(source,target)
                    copied.append(str(target.relative_to(BUNDLE)))
        licenses.append(dict(name=name,version=distribution.version,
            license=distribution.metadata.get('License-Expression') or distribution.metadata.get('License'),
            notices=copied))
    (notices/'dependency-licenses.json').write_text(json.dumps(licenses,indent=2),encoding='utf-8')
    resources = []
    # Enumerate the physical runtime once; do not double count uv's minor-version junction.
    for directory in (Path(sys.executable).resolve().parent, BUNDLE/'model', notices):
        for path in directory.rglob('*'):
            if path.is_file():
                if '__pycache__' in path.parts or path.suffix == '.pyc':
                    continue
                resources.append(dict(path=str(path.relative_to(BUNDLE)),bytes=path.stat().st_size,
                                      sha256=hashlib.file_digest(path.open('rb'),'sha256').hexdigest()))
    (EVIDENCE/'resource-manifest.json').write_text(json.dumps(resources,indent=2),encoding='utf-8')
    size = dict(files=len(resources), bytes=sum(p['bytes'] for p in resources),
                model_bytes=sum(p['bytes'] for p in resources if p['path'].startswith('model')))
    (EVIDENCE/'resource-size.json').write_text(json.dumps(size,indent=2),encoding='utf-8')
    existing = json.loads((EVIDENCE/'preexisting-hashes.json').read_text(encoding='utf-8-sig'))
    preserved = []
    for item in existing:
        path = Path(item['Path'])
        unchanged = hashlib.file_digest(path.open('rb'),'sha256').hexdigest().upper()==item['Hash']
        assert unchanged, f'Existing modification changed: {path}'
        preserved.append(dict(path=str(path.relative_to(ROOT)),unchanged=unchanged))
    (EVIDENCE/'workspace-preserved.json').write_text(json.dumps(preserved,indent=2),encoding='utf-8')
    integrity = []
    for name in ('kokoro','misaki'):
        distribution = importlib.metadata.distribution(name)
        checked = 0
        for entry in distribution.files or []:
            if entry.hash and entry.hash.mode == 'sha256':
                source = Path(distribution.locate_file(entry))
                actual = hashlib.file_digest(source.open('rb'),'sha256').digest()
                assert actual == base64.urlsafe_b64decode(entry.hash.value + '==='), str(source)
                checked += 1
        integrity.append(dict(name=name,version=distribution.version,
                              requires_python=distribution.metadata.get('Requires-Python'),
                              verified_record_hashes=checked, engine_changes=0))
    (EVIDENCE/'official-package-integrity.json').write_text(json.dumps(integrity,indent=2),encoding='utf-8')
    (EVIDENCE/'validation-summary.json').write_text(json.dumps(dict(
        audio_recordings=len(audio_rows), fully_decoded=True, text_coverage=True,
        max_phoneme_length=max(len(s['phonemes']) for p in (EVIDENCE/'audio').glob('*.json')
                              for s in json.loads(p.read_text(encoding='utf-8'))['segments']),
        zero_clipped_samples=all(x['clipped_samples']==0 for x in audio_rows),
        zero_unknown_phoneme_symbols=all(not x['unknown_phoneme_symbols'] for x in audio_rows),
        offline_worker_count=len(lifecycle)+len(extra),
        no_unexpected_python_network_attempts=True, stopped_pids=[x['pid'] for x in lifecycle+extra],
        manual_listening='pending user review', issue_status='pending user decision'),indent=2),encoding='utf-8')
    print(json.dumps(dict(audio_samples=len(audio_rows),released_model_files=len(locks),resources=size),indent=2))


if __name__ == '__main__':
    main()
