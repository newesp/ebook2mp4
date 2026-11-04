"""Real CPU acceptance through public workflows, including recovery and MP4 reuse."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from kokoro_real_check import ROOT,OUT,EVIDENCE,wait,measurements
from ebook2mp4.workflow import ProjectWorkflow
from ebook2mp4.voice import EXAMPLE
from ebook2mp4 import kokoro_runtime

START_SECONDS=2*kokoro_runtime.LOAD_SECONDS+kokoro_runtime.SYNTHESIS_SECONDS+30


def dead(pid):
    api=ctypes.WinDLL('kernel32',use_last_error=True)
    api.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    api.OpenProcess.restype=wintypes.HANDLE
    api.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
    api.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=api.OpenProcess(0x100000,False,pid)
    if not handle:
        error=ctypes.get_last_error()
        if error!=87:print('process probe failed',pid,error,flush=True)
        return error==87
    try:
        result=api.WaitForSingleObject(handle,0)
        if result!=0:print('process probe still active',pid,result,flush=True)
        return result==0
    finally:api.CloseHandle(handle)


def wait_dead(pid):
    deadline=time.monotonic()+10
    while not dead(pid):
        if time.monotonic()>=deadline:return False
        time.sleep(.1)
    return True


def preview(flow,batch,text=None):
    job=flow.start_voice_preview(batch) if text is None else flow.start_voice_preview(batch,text=text,start=0,end=len(text))
    wait(flow,job);result=flow.finish_voice_preview(job);return result


def main():
    flow=ProjectWorkflow.open(OUT/'book');batch=flow.state['batches'][0]['id']
    settings=flow.voice_settings(batch)
    if '--crash-child' in sys.argv:
        text='非正常關閉測試，這段文字不會發布。'*20
        job=flow.start_voice_preview(batch,text=text,start=0,end=len(text))
        deadline=time.monotonic()+START_SECONDS
        while time.monotonic()<deadline:
            status=flow.local_voice_status()
            if status['phase']=='本機合成' and status['pid']:
                (EVIDENCE/'hard-exit-worker.json').write_text(json.dumps(status),encoding='utf-8')
                os._exit(23)
            if job.wait(.1):raise RuntimeError(job.state)
        raise TimeoutError('child did not begin inference')
    # Each acceptance starts with a cold speech cache in this synthetic book.
    # Preserve the already published short product, but force real new inference.
    speech_cache=flow.root/'batches'/batch/'voice-blocks'
    assert speech_cache.resolve().is_relative_to((OUT/'book').resolve())
    if speech_cache.exists():shutil.rmtree(speech_cache)
    kokoro_runtime.IDLE_SECONDS=10  # Same real lifecycle, accelerated clock for acceptance only.
    records={}
    try:
        flow.save_voice_settings('zf_001',batch_id=batch,settings_override=dict(settings,voice='zf_001',rate='+0%'))
        fixed=preview(flow,batch)
        assert fixed['text']==EXAMPLE
        shutil.copyfile(flow.voice_preview_path(batch),EVIDENCE/'fixed-example-zf_001.mp3')
        loads=flow.local_voice_status()['loads']
        assert loads>=1
        male=dict(flow.voice_settings(batch),voice='zm_010',rate='+10%')
        flow.save_voice_settings('zm_010','+10%',batch_id=batch,settings_override=male)
        selected=preview(flow,batch,'第二次試聽，使用男聲。Hello world。')
        shutil.copyfile(flow.voice_preview_path(batch),EVIDENCE/'preview-zm_010.mp3')
        records['warm_reuse']=dict(before_loads=loads,after_loads=flow.local_voice_status()['loads'])
        assert loads==flow.local_voice_status()['loads']
        old=selected['id']
        text='取消測試，這是一段新的長文字。'*30
        job=flow.start_voice_preview(batch,text=text,start=0,end=len(text))
        deadline=time.monotonic()+START_SECONDS
        while flow.local_voice_status()['phase']!='本機合成':
            if job.wait(.05) or time.monotonic()>deadline:raise RuntimeError(job.state)
        time.sleep(.3);start=time.monotonic();job.cancel();assert job.wait(30)
        flow.discard_voice_preview(job)
        assert flow.voice_preview(batch)['id']==old
        assert flow.local_voice_status()['pid'] is None
        records['cancel_inference']=dict(seconds=time.monotonic()-start,state=job.state)
        job=flow.start_voice_preview(batch,text='重新載入測試。',start=0,end=7)
        deadline=time.monotonic()+START_SECONDS
        while flow.local_voice_status()['phase']!='載入本機模型':
            if job.wait(.05) or time.monotonic()>deadline:raise RuntimeError(job.state)
        pid=flow.local_voice_status()['pid'];time.sleep(.3);start=time.monotonic();job.cancel();assert job.wait(30)
        flow.discard_voice_preview(job);assert wait_dead(pid),(pid,job.state,flow.local_voice_status())
        records['cancel_load']=dict(seconds=time.monotonic()-start,pid=pid,dead=True)
        preview(flow,batch,'取消後可以重新合成。')
        pid=flow.local_voice_status()['pid'];start=time.monotonic()
        while flow.local_voice_status()['pid'] is not None:
            if time.monotonic()-start>15:raise TimeoutError('idle unload')
            time.sleep(.1)
        assert wait_dead(pid)
        records['idle']=dict(test_seconds=10,production_seconds=120,elapsed=time.monotonic()-start,pid=pid,dead=True)
        flow.save_voice_settings('zf_001',batch_id=batch,settings_override=dict(settings,voice='zf_001',rate='+0%'))
        # Real confirmed long manuscript, interrupted then reopened/resumed.
        corpus=json.loads((ROOT/'tools/kokoro_k01/samples.json').read_text(encoding='utf-8'))[-1]['text']
        source=OUT/'long-source.txt';source.write_text(corpus,encoding='utf-8')
        long_batch=flow.import_txt(flow.inspect_txt(source))
        flow.save_voice_settings('zf_001',batch_id=long_batch,settings_override=dict(settings,voice='zf_001',rate='+0%'))
        flow.confirm_reading(long_batch)
        job=flow.start_narration(long_batch,allow_network=False)
        deadline=time.monotonic()+START_SECONDS
        while job.state.get('completed',0)<1:
            if job.wait(.1) or time.monotonic()>deadline:raise RuntimeError(job.state)
        assert flow.local_voice_status()['pid'] is not None
        job.cancel();assert job.wait(30);flow.discard_narration(job)
        reopened=ProjectWorkflow.open(flow.root)
        run=reopened.narration_runs(long_batch)[-1];assert run['reusable']>=1
        print('resume retains',run['reusable'],'blocks',flush=True)
        job=reopened.resume_narration(long_batch,run['snapshot']['id'],allow_network=False);wait(reopened,job)
        long_product=reopened.finish_narration(job)
        assert long_product['text']==reopened.reading_text(long_batch)
        assert long_product['text'].replace('\r\n','\n')==corpus
        assert sum(c['reused'] for c in long_product['chunks'])>=run['reusable']
        shutil.copyfile(reopened.narration_path(long_batch),EVIDENCE/'integrated-long-zf_001.mp3')
        shutil.copyfile(reopened.narration_path(long_batch,'srt'),EVIDENCE/'integrated-long-zf_001.srt')
        records['long_resume']=dict(reused=run['reusable'],chunks=len(long_product['chunks']),duration_ms=long_product['duration_ms'])
        reopened.save_voice_settings('zm_010',batch_id=long_batch,settings_override=dict(settings,voice='zm_010'))
        assert reopened.narration_runs(long_batch)[-1]['stale']
        reopened.save_voice_settings('zf_001',batch_id=long_batch,settings_override=dict(settings,voice='zf_001',rate='+0%'))
        records['changed_voice_blocks_resume']=True
        flow=reopened
        flow.save_assembly_settings([batch,long_batch],500)
        load_count=flow.local_voice_status()['loads']
        job=flow.start_total_audio();wait(flow,job);flow.finish_total_audio(job)
        from PIL import Image
        image=OUT/'cover.png';Image.new('RGB',(320,180),'#315d43').save(image)
        flow.save_total_video_settings(image=flow.inspect_total_video_image(image),resolution='720p')
        job=flow.start_total_video();wait(flow,job);flow.finish_total_video(job)
        assert flow.local_voice_status()['loads']==load_count
        delivery=OUT/'delivery';delivery.mkdir(exist_ok=True)
        for kind in ('mp3','srt'):shutil.copyfile(flow.total_audio_path(kind),delivery/('kokoro-total.'+kind))
        shutil.copyfile(flow.total_video_path(),delivery/'kokoro-total.mp4')
        Image.new('RGB',(320,180),'#795b35').save(image)
        flow.save_total_video_settings(image=flow.inspect_total_video_image(image),resolution='720p')
        job=flow.start_total_video();wait(flow,job);flow.finish_total_video(job)
        assert flow.local_voice_status()['loads']==load_count
        shutil.copyfile(flow.total_video_path(),delivery/'kokoro-total-second-image.mp4')
        records['total']=dict(audio=str(delivery/'kokoro-total.mp3'),video=str(delivery/'kokoro-total.mp4'),
                              second_image=str(delivery/'kokoro-total-second-image.mp4'),no_new_model_loads=True)
        flow.unload_local_voice()
        child=subprocess.run([sys.executable,'-B',str(Path(__file__)),'--crash-child'],timeout=START_SECONDS+30)
        assert child.returncode==23,child.returncode
        crashed=json.loads((EVIDENCE/'hard-exit-worker.json').read_bytes())
        deadline=time.monotonic()+10
        while not dead(crashed['pid']) and time.monotonic()<deadline:time.sleep(.1)
        assert dead(crashed['pid'])
        records['parent_hard_exit']=dict(pid=crashed['pid'],dead=True)
        records['measurements']=measurements
        (EVIDENCE/'acceptance.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    finally:flow.unload_local_voice()


if __name__=='__main__':main()
