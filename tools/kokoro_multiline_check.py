"""Real public-flow regression for multiline Chinese preview and subtitles."""
import json
import os
from pathlib import Path
import shutil
import time

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'docs/verification/kokoro-text-fix'
os.environ['EBOOK2MP4_KOKORO_HOME']=str(ROOT/'.scratch/kokoro-text-fix/home')
from ebook2mp4.workflow import ProjectWorkflow

TEXT='開悟比你的皮膚還要接近你，\n比你的下一口氣出現得還要快，\n然而，它又是你永遠無法觸及的。\n2. 矛盾'
records=[]

def wait(job):
    start=time.monotonic()
    try:
        assert job.wait(900),job.state
        assert job.state['status']=='completed',job.state
        records.append(dict(seconds=time.monotonic()-start,state=job.state))
    finally:
        job.cancel();assert job.wait(30)

def main():
    flow=ProjectWorkflow.create(ROOT/'.scratch/kokoro-text-fix/book','換行試聽回歸')
    package=json.loads((EVIDENCE/'package.json').read_bytes())
    try:
        wait(flow.start_voice_package_import(Path(package['path'])))
        metadata=flow.local_voice_packages()[0]
        source=ROOT/'.scratch/kokoro-text-fix/source.txt';source.write_text(TEXT,encoding='utf-8')
        batch=flow.import_txt(flow.inspect_txt(source))
        for voice,text,label in [('zf_001',TEXT,'female-lf'),('zm_010',TEXT,'male-lf'),
                                 ('zf_002',TEXT.replace('\n','\r\n'),'female-crlf'),
                                 ('zf_001',TEXT.replace('\n','\t'),'female-tab')]:
            settings=dict(flow.voice_settings(batch),provider='kokoro',voice=voice,package=metadata['id'],
                          model=metadata['model'],processing=metadata['processing'] if 'processing' in metadata else 'kokoro-t2s-v1')
            flow.save_voice_settings(voice,batch_id=batch,settings_override=settings)
            job=flow.start_voice_preview(batch,text=text,start=0,end=len(text));wait(job)
            result=flow.finish_voice_preview(job);assert result['text']==text
            shutil.copyfile(flow.voice_preview_path(batch),EVIDENCE/(label+'.mp3'))
            print(label,'passed',flush=True)
        flow.confirm_reading(batch)
        job=flow.start_narration(batch,allow_network=False);wait(job)
        product=flow.finish_narration(job)
        assert product['text']==flow.reading_text(batch)
        assert product['text'].replace('\r\n','\n')==TEXT
        shutil.copyfile(flow.narration_path(batch),EVIDENCE/'formal.mp3')
        shutil.copyfile(flow.narration_path(batch,'srt'),EVIDENCE/'formal.srt')
        assert TEXT in flow.narration_path(batch,'srt').read_text(encoding='utf-8-sig')
        (EVIDENCE/'results.json').write_text(json.dumps(dict(records=records,status=flow.local_voice_status(),original=TEXT),ensure_ascii=False,indent=2),encoding='utf-8')
    finally:flow.unload_local_voice()

if __name__=='__main__':main()
