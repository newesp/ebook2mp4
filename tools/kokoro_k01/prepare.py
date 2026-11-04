"""Download immutable official model resources for the K01 experiment (online only)."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / 'outputs/kokoro-k01'
EVIDENCE = ROOT / 'docs/verification/kokoro-k01'
REPO = 'hexgrad/Kokoro-82M-v1.1-zh'
REVISION = '01e7505bd6a7a2ac4975463114c3a7650a9f7218'


def main():
    with urllib.request.urlopen(f'https://huggingface.co/api/models/{REPO}/revision/{REVISION}') as response:
        metadata = json.load(response)
    revision = metadata['sha']
    assert revision == REVISION
    names = [x['rfilename'] for x in metadata['siblings']]
    selected = [n for n in names if n in ('config.json', 'kokoro-v1_1-zh.pth', 'README.md', 'LICENSE')
                or n.startswith('voices/') and n.endswith('.pt')]
    assert 'kokoro-v1_1-zh.pth' in selected, names
    destination = BUNDLE / 'model'
    destination.mkdir(parents=True, exist_ok=True)

    def fetch(name):
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            temporary = target.with_suffix(target.suffix + '.partial')
            urllib.request.urlretrieve(f'https://huggingface.co/{REPO}/resolve/{revision}/{name}', temporary)
            temporary.replace(target)
        digest = hashlib.file_digest(target.open('rb'), 'sha256').hexdigest()
        print(name, target.stat().st_size, flush=True)
        return dict(path=name, bytes=target.stat().st_size, sha256=digest)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        files = list(pool.map(fetch, selected))
    weights = next(f for f in files if f['path'].endswith('.pth'))
    assert weights['sha256'] == 'b1d8410fa44dfb5c15471fd6c4225ea6b4e9ac7fa03c98e8bea47a9928476e2b'
    (EVIDENCE / 'model-manifest.json').write_text(json.dumps(dict(repo=REPO, revision=revision, files=files), indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
