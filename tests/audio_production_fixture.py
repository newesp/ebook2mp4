"""Isolated native audio workspace; synthetic media and no cloud calls.

Launch from the repository with PYTHONPATH including its pinned runtime deps.
Close the window to remove the owned project, cache, jobs and temporary media.
"""
from __future__ import annotations
import argparse
import asyncio
from contextlib import ExitStack
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
from unittest.mock import AsyncMock, patch

from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow
import test_voice


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--geometry',default='1536x864+0+0')
    parser.add_argument('--scenario',choices=('cancelled','failed','ready','running','stale'),default='failed')
    parser.add_argument('--metrics',type=Path)
    parser.add_argument('--audio-duration',type=float,default=0.2)
    parser.add_argument('--package-fixture',type=Path)
    args=parser.parse_args()
    base=Path('.scratch/test-runs').resolve()
    base.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='audio-ui-',dir=base) as temporary, ExitStack() as stack:
        folder=Path(temporary)
        stack.enter_context(patch.dict(os.environ,EBOOK2MP4_VOICE_HOME=str(folder/'voice-cache'),
            EBOOK2MP4_APP_HOME=str(folder/'app-home'),EBOOK2MP4_KOKORO_HOME=str(folder/'kokoro-home')))
        stack.enter_context(patch('edge_tts.list_voices',new=AsyncMock(return_value=test_voice.VOICES)))
        # Even accidental service-management actions cannot issue HTTP requests.
        stack.enter_context(patch('aiohttp.ClientSession',side_effect=RuntimeError('此驗收程式不允許網路請求。')))
        flow=ProjectWorkflow.create(folder/'book','音訊製做 · 隔離驗收資料')
        source=folder/'source.txt'
        source.write_text('上一版已成功的朗讀稿。',encoding='utf-8')
        batch=flow.import_txt(flow.inspect_txt(source))
        job=flow.start_voice_refresh()
        if not job.wait(10):
            raise RuntimeError('Local asyncio setup stalled; run outside filesystem sandbox.')
        job.result
        flow.save_voice_settings('zh-TW-TestNeural',batch_id=batch)
        flow.confirm_reading(batch)
        audio_file=folder/'synthetic.mp3'
        subprocess.run([shutil.which('ffmpeg'),'-v','error','-f','lavfi','-i',
            f'sine=frequency=440:duration={args.audio_duration}','-y',str(audio_file)],check=True)
        audio=audio_file.read_bytes()
        waiting=threading.Event()
        class Service:
            hold=False
            def __init__(self,text,*a,**k): self.text=text
            async def stream(self):
                if self.hold and not self.text.startswith('第 001'):
                    waiting.set()
                    await asyncio.sleep(3600)
                yield dict(type='audio',data=audio)
        stack.enter_context(patch('edge_tts.Communicate',Service))
        product_job=flow.start_narration(batch)
        if not product_job.wait(20):
            product_job.cancel();product_job.wait(10)
            flow.discard_narration(product_job)
            raise RuntimeError('Synthetic product did not finish.')
        flow.finish_narration(product_job)
        flow.save_draft(batch,'\n\n'.join(f'第 {index:03d} 段。這是原生介面驗收稿件，可核對任務快照、區塊狀態及捲動位置。' for index in range(1,174)))
        flow.confirm_reading(batch)
        Service.hold=True
        partial=flow.start_narration(batch)
        if not waiting.wait(15):
            partial.cancel();partial.wait(10);flow.discard_narration(partial)
            raise RuntimeError('Synthetic partial run did not reach its waiting block.')
        partial.cancel()
        if not partial.wait(10):
            raise RuntimeError('Synthetic cancellation did not stop.')
        flow.discard_narration(partial)
        if args.scenario=='failed':
            record=flow.state['batches'][0]['narration_runs'][-1]
            path=flow.root/record['progress_path']
            progress=json.loads(path.read_text(encoding='utf-8'))
            error='模擬 HTTP 429：服務用量暫時受限。\n請保留已完成區塊，稍後繼續。此訊息只有驗收資料。'
            progress.update(status='failed',error=error)
            progress['chunks'][1].update(status='failed',attempts=3,error=error)
            path.write_text(json.dumps(progress,ensure_ascii=False),encoding='utf-8')
        elif args.scenario=='stale':
            flow.save_voice_settings('en-US-TestNeural','+10%',batch_id=batch)
        if args.package_fixture:
            shutil.copytree(flow.root,args.package_fixture)
        root,app=make_app()
        app.flow,app.batch_id=flow,batch
        app.refresh()
        root.update()
        root.state('normal')
        root.geometry(args.geometry)
        app.narration()
        page=app.narration_dialog
        deadline=time.monotonic()+15
        while page.check_job is not None and time.monotonic()<deadline:
            root.update();time.sleep(.02)
        if page.check_job is not None:
            raise RuntimeError('Inspection did not finish.')
        if args.scenario=='ready':
            page.recheck()
        elif args.scenario=='running':
            page.start_button.invoke()
        root.update()
        def metrics():
            root.update_idletasks()
            rows=page.details.get_children()
            visible=[row for row in rows if page.details.bbox(row)
                     and page.details.bbox(row)[1]+page.details.bbox(row)[3]<=page.details.winfo_height()]
            indicator=['indicator' in str(page.output_button.identify(x,page.output_button.winfo_height()//2)).lower()
                       for x in range(page.output_button.winfo_width())]
            native_indicators=sum(value and (index==0 or not indicator[index-1])
                                  for index,value in enumerate(indicator))
            value=dict(pid=os.getpid(),scenario=args.scenario,geometry=root.geometry(),
                tk_scaling=float(root.tk.call('tk','scaling')),rows=len(rows),visible_rows=len(visible),
                page_width=page.winfo_width(),page_height=page.winfo_height(),
                table_height=page.details.winfo_height(),fixture_root=str(folder),
                task_choice_height=page.run_control.winfo_height(),task_info_height=page.info_button.winfo_height(),
                task_choice_top=page.run_control.winfo_rooty(),task_info_top=page.info_button.winfo_rooty(),
                product_menu_label=str(page.output_button.cget('text')),native_menu_indicators=native_indicators)
            print(json.dumps(value,ensure_ascii=False),flush=True)
            if args.metrics:
                args.metrics.parent.mkdir(parents=True,exist_ok=True)
                args.metrics.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
        def close():
            deadline=time.monotonic()+15
            while app.production.shutdown()!='complete' and time.monotonic()<deadline:
                root.update();time.sleep(.02)
            root.destroy()
        root.protocol('WM_DELETE_WINDOW',close)
        root.after(500,metrics)
        root.mainloop()
    print('Fixture closed: owned project, caches, media and tasks removed.',flush=True)


if __name__=='__main__':
    main()
