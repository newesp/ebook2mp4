"""Owned native baseline and acceptance for the existing v2 UI (no redesign)."""
from pathlib import Path
import argparse
import asyncio
import hashlib
import json
import os
import shutil
import sys
import time
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.scratch/v2-shell-refactor'
EVIDENCE = ROOT / 'docs/verification/v2-shell-refactor'
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'tests'))


def environment():
    WORK.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for key, folder in [('LOCALAPPDATA','local-data'), ('EBOOK2MP4_APP_HOME','app-home'),
                        ('EBOOK2MP4_VOICE_HOME','voice-home'), ('EBOOK2MP4_KOKORO_HOME','kokoro-home'),
                        ('EBOOK2MP4_OCR_HOME','ocr-home')]:
        os.environ[key] = str(WORK/folder)
    os.environ['EBOOK2MP4_FFMPEG'] = shutil.which('ffmpeg') or ''
    os.environ['EBOOK2MP4_FFPROBE'] = shutil.which('ffprobe') or ''


def seed():
    from test_total_audio import TotalAudioJourney
    from ebook2mp4.workflow import ProjectWorkflow
    if not (WORK/'seed-book').exists():
        case = TotalAudioJourney()
        case.setUp()
        try:
            ids = case.prepare(4)
            for i,batch in enumerate(ids):case.flow.rename_batch(batch, f'第 {i+1} 章')
            case.flow.save_assembly_settings(ids[:3])
            shutil.copytree(case.flow.root, WORK/'seed-book')
            shutil.copytree(case.path/'voice-cache', WORK/'voice-home', dirs_exist_ok=True)
        finally:case.doCleanups()
    return ProjectWorkflow.open(WORK/'seed-book')


def settle(root, seconds=.18):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        root.update()
        time.sleep(.008)


def prepare_media():
    """Real local products for native routes; no external speech request."""
    environment()
    flow=seed()
    from PIL import Image
    picture=WORK/'synthetic.png'
    Image.new('RGB',(96,128),'#315d43').save(picture)
    ids=[b['id'] for b in flow.state['batches']]
    for identity in ids:
        snapshot=flow._batch(identity)['readings'][-1]['id']
        text=flow.reading_text(identity,snapshot)
        flow.save_workspace(identity,text)
        flow.save_reading_manuscript(identity,text)
    for identity in ids[:3]:
        target=flow.batch_video_target(identity)
        if target.total_video() is None:
            target.save_total_video_settings(image=flow.inspect_total_video_image(picture),resolution='720p')
            job=target.start_total_video()
            if not job.wait(60):raise RuntimeError('Local synthetic video timed out')
            target.finish_total_video(job)
    flow.save_video_merge_settings(ids[:3],resolution='720p')
    flow.save_total_video_settings(image=flow.inspect_total_video_image(picture),resolution='720p')
    (EVIDENCE/'synthetic-media.json').write_text(json.dumps(dict(batches=ids[:3],
        real_ffmpeg=True,external_tts=False,private_text=False),indent=2),encoding='utf-8')


def auxiliary(app, name):
    if name in ('services','packages','defaults'):
        app.voice_settings();voice=app.voice_dialog
        if name=='services':voice.manage_services()
        elif name=='packages':voice.manage_local_packages()
        else:
            voice.scope.set('全書預設');voice.save(announce=False);voice.open_defaults()
    else:
        app.total_audio() if name=='joins' else app.production.show('merge')
        page=app.production.current
        end=time.monotonic()+15
        while page.check_job and time.monotonic()<end:settle(app.root,.04)
        page.open_joins()


def run(phase, interactive=False):
    environment()
    flow=seed()
    from ebook2mp4.desktop import make_app
    from PIL import ImageGrab
    from test_voice import VOICES
    target=EVIDENCE/phase
    target.mkdir(parents=True,exist_ok=True)
    (target/'source-hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (ROOT/'ebook2mp4').glob('*.py')},indent=2),encoding='utf-8')
    if phase=='baseline':
        source_copy=WORK/'source-before'
        source_copy.mkdir(exist_ok=True)
        for file in (ROOT/'ebook2mp4').glob('*.py'):shutil.copy2(file, source_copy/file.name)
        (target/'source-hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest()
            for p in source_copy.glob('*.py')},indent=2),encoding='utf-8')
    records=[]
    with patch('edge_tts.list_voices', new=AsyncMock(return_value=VOICES)), \
            patch('aiohttp.ClientSession',side_effect=AssertionError('offline native fixture')):
        root,app=make_app()
        errors=[]
        root.report_callback_exception=lambda kind,error,trace:errors.append(str(error))
        app.flow,app.batch_id=flow,flow.state['batches'][0]['id']
        app.refresh()
        app.focus_mode=False
        app.remember_project=lambda:None
        settle(root)
        root.state('normal');root.geometry('1360x820+0+0');settle(root)

        def capture(name):
            settle(root)
            page=app.production.current if app.step==4 else None
            if page:
                end=time.monotonic()+10
                while getattr(page,'check_job',None) is not None and time.monotonic()<end:settle(root,.04)
            widgets=dict(client=root,navigation=app.shell.navigation,documents=app.shell.documents,
                list_header=app.list_header,list_content=app.shell.documents.batch_view,
                workspace=app.shell.workspace,footer=app.shell.footer,editor=app.editor)
            current=getattr(app.shell,'current',None)
            if current:
                widgets['active_owner']=current.owner
                layout=getattr(current.owner,'workspace',None)
                if hasattr(layout,'main'):widgets['active_content']=layout.main
                if current.footer is not None:widgets['active_footer']=current.footer
                for i,band in enumerate(current.bands):
                    for j,control in enumerate(band.controls):widgets[f'header-{i}-{j}']=control
            if page:
                widgets['page']=page
                for key in ('toolbar','sources_panel','table','details','actions','back_button','save_button','start_button'):
                    widget=getattr(page,key,None)
                    if hasattr(widget,'winfo_exists'):widgets[key]=widget
                layout=getattr(page,'assembly_workspace',None)
                if layout:widgets.update(header=layout.header,content=page.main)
            boxes={k:dict(x=v.winfo_rootx(),y=v.winfo_rooty(),width=v.winfo_width(),height=v.winfo_height(),
                mapped=bool(v.winfo_ismapped()),widget=str(v),parent=str(v.master)) for k,v in widgets.items() if v.winfo_exists()}
            record=dict(name=name,geometry=root.geometry(),dpi=root.winfo_fpixels('1i'),
                tk_scaling=root.tk.call('tk','scaling'),step=app.step,kind=getattr(page,'kind',None),
                files=not app.focus_mode,boxes=boxes,errors=list(errors))
            def descendants(widget):
                for child in widget.winfo_children():
                    yield child
                    yield from descendants(child)
            scrolls=[]
            controls=[]
            for widget in descendants(app):
                if not widget.winfo_ismapped():continue
                if widget.winfo_class() in ('TButton','TEntry','TCombobox','TMenubutton'):
                    controls.append(dict(widget=str(widget),kind=widget.winfo_class(),
                        text=str(widget.cget('text')) if 'text' in widget.keys() else '',
                        x=widget.winfo_rootx(),y=widget.winfo_rooty(),width=widget.winfo_width(),height=widget.winfo_height(),
                        state=str(widget.cget('state')),style=str(widget.cget('style'))))
                if widget.winfo_class() in ('Text','Treeview','Canvas') and hasattr(widget,'yview'):
                    region=dict(widget=str(widget),kind=widget.winfo_class(),
                        parent=str(widget.master),viewport=widget.winfo_height(),fractions=widget.yview(),
                        first=widget.index('@0,0') if widget.winfo_class()=='Text' else None,
                        last=widget.index('@0,%d'%widget.winfo_height()) if widget.winfo_class()=='Text' else None)
                    if widget.winfo_class()=='Canvas':
                        region['scrollregion']=str(widget.cget('scrollregion'))
                        region['bbox']=widget.bbox('all')
                    if widget.winfo_class()=='Text':region['content_ypixels']=widget.count('1.0','end','ypixels')
                    scrolls.append(region)
            record['scrolls']=scrolls
            record['controls']=controls
            if current:
                record['page_id']=current.page_id
                record['actions']=[dict(id=a.id,label=a.label,enabled=a.enabled) for a in current.footer.describe()] if current.footer else []
            if page is app.voice_dialog and page is not None:
                def gap(a,b):return b.winfo_rootx()-a.winfo_rootx()-a.winfo_width()
                next_action=page.produce_button if page.produce_button.winfo_ismapped() else page.apply_defaults_button
                record['voice_spacing']=dict(pair=[[w.winfo_width(),w.winfo_height()] for w in (page.sample_text_button,page.selected_text_button)],
                    pair_gap=gap(page.sample_text_button,page.selected_text_button),footer_gap=gap(page.save_button,next_action),
                    text_gap=page.outgoing.winfo_rooty()-page.sample_text_button.winfo_rooty()-page.sample_text_button.winfo_height())
            records.append(record)
            ImageGrab.grab(window=root.winfo_id()).save(target/(name+'.png'))
            (target/'measurements.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')

        views=[('manuscript',lambda:app.show_step(1)),('versions',app.show_versions),
               ('ai-settings',app.gemini_settings),('source',app.compare_pdf_pages),
               ('voice',app.voice_settings),('audio',app.narration),
               ('assembly',app.total_audio),('video-batch',app.batch_video),
               ('video-book',app.total_video),('video-merge',lambda:app.production.show('merge')),
               ('outputs',app.production.show_versions)]
        views.extend((name,lambda name=name:auxiliary(app,name)) for name in
                     ('services','packages','defaults','joins','video-joins'))
        for name,command in views:
            if app.step!=4 and app.tools_open:app.close_tools()
            app.focus_mode=False
            command();settle(root,.3)
            for geometry in ('1360x820','1280x720','900x640'):
                root.state('normal');root.geometry(geometry+'+0+0');settle(root)
                app.layout_workspace();capture(name+'-'+geometry)
            root.state('zoomed');settle(root);app.layout_workspace();capture(name+'-maximized')
        app.show_step(1)
        if app.tools_open:app.close_tools()
        app.font_size.set('18');app.save_manuscript_settings();settle(root)
        capture('manuscript-18pt')
        app.show_versions();settle(root);capture('versions-18pt')
        app.close_tools();app.font_size.set('12');app.save_manuscript_settings()
        if interactive:
            root.title('v2 外框驗收 · 隔離測試專案')
            def poll():
                file=WORK/'command.json'
                if file.exists():
                    command=json.loads(file.read_text(encoding='utf-8-sig'));file.unlink()
                    if command['action']=='close':app.close();return
                    if command['action']=='capture':capture(command['name'])
                    if command['action']=='route':
                        if app.step!=4 and app.tools_open:app.close_tools()
                        dict(views)[command['name']]();settle(root);capture('route-'+command['name'])
                    if command['action']=='size':
                        root.state('normal');root.geometry(command['geometry']);settle(root);app.layout_workspace()
                    if command['action']=='long-editor':
                        app.show_step(1)
                        if app.tools_open:app.close_tools()
                        app.set_editor('\n'.join(f'第 {i:03} 行：原生捲動驗收合成文字。' for i in range(1,241))+'\n最後一行 END。')
                        app.editor.yview_moveto(0);settle(root);capture('long-editor-start')
                    if command['action']=='short-editor':
                        app.set_editor('短文 END。');settle(root);capture('short-editor')
                root.after(100,poll)
            root.after(100,poll)
            root.mainloop()
        else:
            with patch('tkinter.messagebox.askyesnocancel',return_value=False):app.close()
            end=time.monotonic()+10
            while time.monotonic()<end:
                try:
                    if not root.winfo_exists():break
                    settle(root,.05)
                except Exception:break
        (target/'closed.json').write_text(json.dumps(dict(normal_exit=True,errors=errors),ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(dict(phase=phase,frames=len(records),errors=errors)),flush=True)
        if errors:raise SystemExit(1)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',default='native')
    parser.add_argument('--interactive',action='store_true')
    parser.add_argument('--prepare-media',action='store_true')
    args=parser.parse_args()
    if args.prepare_media:prepare_media()
    else:run(args.phase,args.interactive)
