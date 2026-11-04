"""Check the unchanged 120-second production idle deadline with a real worker."""
import json
import time
from kokoro_real_check import OUT,EVIDENCE,wait
from kokoro_acceptance import wait_dead
from ebook2mp4.workflow import ProjectWorkflow

flow=ProjectWorkflow.open(OUT/'book');batch=flow.state['batches'][0]['id']
text='正式期限卸載測試，這段文字只在本機處理。'
try:
    job=flow.start_voice_preview(batch,text=text,start=0,end=len(text));wait(flow,job)
    flow.finish_voice_preview(job)
    status=flow.local_voice_status();assert status['idle_seconds']==120 and status['pid']
    started=time.monotonic()
    while flow.local_voice_status()['pid'] is not None:
        if time.monotonic()-started>150:raise TimeoutError('Production idle unload')
        time.sleep(.25)
    assert wait_dead(status['pid'])
    elapsed=time.monotonic()-started
    assert 118<=elapsed<=130,elapsed
    result=dict(production_seconds=120,elapsed=elapsed,pid=status['pid'],dead=True,device=status['device'])
    (EVIDENCE/'idle-production.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)
finally:flow.unload_local_voice()
