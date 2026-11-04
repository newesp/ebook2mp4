"""Real public-flow acceptance. Keep outputs and evidence, remove runtime home later."""
import json
import os
from pathlib import Path
import shutil
import time

ROOT=Path(__file__).resolve().parents[1]
os.environ['EBOOK2MP4_KOKORO_HOME']=str(ROOT/'.scratch/kokoro-integration/real-home')
from ebook2mp4.workflow import ProjectWorkflow

OUT=ROOT/'outputs/kokoro-integration'
EVIDENCE=ROOT/'docs/verification/kokoro-integration'
measurements=[]


def wait(flow,job,timeout=900):
    start=time.monotonic();phase=None
    try:
        while not job.wait(.2):
            current=flow.local_voice_status()
            if current['phase']!=phase:
                phase=current['phase'];print(round(time.monotonic()-start,2),phase,flush=True)
            if time.monotonic()-start>timeout:raise TimeoutError(job.state)
        if job.state['status']!='completed':raise RuntimeError(dict(job.state,worker=flow.local_voice_status()))
        elapsed=time.monotonic()-start
        measurements.append(dict(seconds=elapsed,state=job.state,worker=flow.local_voice_status()))
        print('completed in',elapsed,flush=True)
    except BaseException:
        job.cancel();job.wait(30);raise


def main():
    OUT.mkdir(exist_ok=True)
    project=OUT/'book'
    flow=ProjectWorkflow.open(project) if (project/'project.json').exists() else ProjectWorkflow.create(project,'Kokoro 真實離線驗證')
    if not flow.local_voice_packages():
        archive=Path(json.loads((EVIDENCE/'package.json').read_bytes())['path'])
        print('Installing',archive,flush=True);wait(flow,flow.start_voice_package_import(archive))
    metadata=flow.local_voice_packages()[0]
    source=OUT/'source.txt';source.write_text('今天，歡迎閱讀。Hello world。',encoding='utf-8')
    batch=flow.state['batches'][0]['id'] if flow.state['batches'] else flow.import_txt(flow.inspect_txt(source))
    value=dict(flow.voice_settings(batch),provider='kokoro',voice='zf_001',package=metadata['id'],
               model=metadata['model'],processing='kokoro-t2s-v1')
    flow.save_voice_settings('zf_001',batch_id=batch,settings_override=value)
    try:
        text=source.read_text(encoding='utf-8')
        job=flow.start_voice_preview(batch,text=text,start=0,end=len(text));wait(flow,job)
        flow.finish_voice_preview(job)
        shutil.copyfile(flow.voice_preview_path(batch),EVIDENCE/'preview-zf_001.mp3')
        flow.confirm_reading(batch)
        job=flow.start_narration(batch,allow_network=False);wait(flow,job)
        product=flow.finish_narration(job)
        assert all(c['reused'] for c in product['chunks'])
        assert flow.narration_path(batch,'srt').read_text(encoding='utf-8-sig').find(text)>=0
        (EVIDENCE/'real-public-flow.json').write_text(json.dumps(measurements,ensure_ascii=False,indent=2),encoding='utf-8')
    finally:flow.unload_local_voice()


if __name__=='__main__':main()
