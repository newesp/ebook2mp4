"""Build the fixed offline package from the already verified K01 resources."""
import hashlib
import json
from pathlib import Path
import zipfile
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
BUNDLE=ROOT/'outputs/kokoro-k01'
OUT=ROOT/'dist/kokoro'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    inventory=json.loads((ROOT/'docs/verification/kokoro-k01/resource-manifest.json').read_bytes())
    files=[];sources={}
    for entry in inventory:
        source=BUNDLE/entry['path']
        path=Path(entry['path'])
        name=('runtime/'+Path(*path.parts[2:]).as_posix()) if path.parts[0]=='python' else path.as_posix()
        files.append(dict(path=name,bytes=entry['bytes'],sha256=entry['sha256']))
        sources[name]=source
    worker=ROOT/'ebook2mp4/kokoro_worker.py'
    files.append(dict(path='worker.py',bytes=worker.stat().st_size,
                      sha256=hashlib.file_digest(worker.open('rb'),'sha256').hexdigest()))
    sources['worker.py']=worker
    revision=json.loads((ROOT/'docs/verification/kokoro-k01/model-manifest.json').read_bytes())['revision']
    voices=[dict(id=p.stem,gender='Female' if p.stem.startswith('zf_') else 'Male',verified=False)
            for p in sorted((BUNDLE/'model/voices').glob('z*.pt'))]
    assert len(voices)==100
    identity=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()[:16]
    metadata=dict(format=1,id='kokoro-zh-cpu-'+identity,model=revision,python='runtime/python.exe',
                  engine='kokoro-0.9.4-misaki-0.9.4',processing='kokoro-t2s-v1',voices=voices,files=files)
    data=json.dumps(metadata,ensure_ascii=False,sort_keys=True).encode()
    archive=OUT/(metadata['id']+'.zip')
    temporary=archive.with_suffix('.partial')
    receipt=ROOT/'ebook2mp4/kokoro_release.json'
    receipt_stage=receipt.with_suffix('.partial')
    try:
        if len(sys.argv)==3 and sys.argv[1]=='--reuse':
            old=Path(sys.argv[2])
            with zipfile.ZipFile(old) as previous:
                old_metadata=json.loads(previous.read('package.json'))
                assert [e for e in old_metadata['files'] if e['path']!='worker.py']==[e for e in files if e['path']!='worker.py']
            shutil.copyfile(old,temporary)
            with tempfile.TemporaryDirectory(dir=ROOT/'.scratch/kokoro-integration') as location:
                delta=Path(location);(delta/'package.json').write_bytes(data);shutil.copyfile(worker,delta/'worker.py')
                seven=shutil.which('7z') or 'C:/Program Files/7-Zip/7z.exe'
                subprocess.run([seven,'u','-tzip',str(temporary), 'package.json','worker.py'],cwd=delta,check=True)
        else:
            with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as target:
                target.writestr('package.json',data)
                for index,entry in enumerate(files):
                    target.write(sources[entry['path']],entry['path'])
                    if index%5000==0:print('packaged',index,flush=True)
        temporary.replace(archive)
        receipt_stage.write_bytes(data);receipt_stage.replace(receipt)
    finally:
        temporary.unlink(missing_ok=True)
        receipt_stage.unlink(missing_ok=True)
    result=dict(path=str(archive),bytes=archive.stat().st_size,
                sha256=hashlib.file_digest(archive.open('rb'),'sha256').hexdigest(),package=metadata['id'])
    (ROOT/'docs/verification/kokoro-integration/package.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
