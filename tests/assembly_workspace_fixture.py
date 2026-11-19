"""Owned synthetic audio workspace for native/EXE comparison and manual input QA."""
import argparse
import json
import os
from pathlib import Path
import shutil
import time
from unittest.mock import AsyncMock, patch

from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow
from test_total_audio import TotalAudioJourney
import test_voice


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--geometry',default='1360x820+0+0');ap.add_argument('--seed-only',action='store_true')
    args=ap.parse_args()
    work=Path('.scratch/audio-assembly-review').resolve();work.mkdir(parents=True,exist_ok=True)
    evidence=Path('docs/verification/audio-assembly-workspace').resolve();evidence.mkdir(parents=True,exist_ok=True)
    for key,sub in [('EBOOK2MP4_APP_HOME','app-home'),('EBOOK2MP4_VOICE_HOME','voice-home'),('EBOOK2MP4_KOKORO_HOME','kokoro-home')]:os.environ[key]=str(work/sub)
    book=work/'book'
    if not book.exists():
        case=TotalAudioJourney();case.setUp()
        try:
            ids=case.prepare(16)
            for i,identity in enumerate(ids):case.flow.rename_batch(identity,f'第 {i+1} 章')
            case.flow.save_assembly_settings(ids[:4])
            case.flow.save_output_formats(['mp4']);case.flow.save_total_video_method('batch-videos')
            shutil.copytree(case.flow.root,book)
        finally:case.doCleanups()
    (work/'app-home').mkdir(exist_ok=True)
    (work/'app-home/session.json').write_text(json.dumps({'last_project':str(book)}),encoding='utf-8')
    if args.seed_only:print(book,flush=True);return
    flow=ProjectWorkflow.open(book)
    with patch('edge_tts.list_voices',new=AsyncMock(return_value=test_voice.VOICES)),patch('aiohttp.ClientSession',side_effect=AssertionError('offline fixture')):
        root,app=make_app();app.flow,app.batch_id=flow,flow.state['batches'][0]['id'];app.refresh()
        app.total_audio();page=app.production.current
        root.state('normal');root.geometry(args.geometry)
        errors=[];root.report_callback_exception=lambda typ,value,tb:errors.append(str(value))
        def measure(name='live'):
            root.update_idletasks()
            ws=page.assembly_workspace
            widgets=dict(root=root,page=page,main=page.main,toolbar=ws.toolbar,table=page.table,table_frame=page.table_frame,
                pause=page.pause_control,state=ws.result_state,join=page.join_button,detail=ws.detail_button,
                versions=page.versions_button,save=page.save_button,start=page.start_button,back=page.back_button,
                scrollbar=ws.table_scroll,files=app.left_panel,header=ws.header,documents=app.batch_list,
                document_scrollbar=app.shell.documents.batch_scroll,output_menu=page.outputs_button)
            widgets.update({f'source{i}':v for i,v in enumerate(ws.source_buttons)})
            metrics={k:dict(x=v.winfo_rootx(),y=v.winfo_rooty(),width=v.winfo_width(),height=v.winfo_height(),mapped=bool(v.winfo_ismapped())) for k,v in widgets.items()}
            result=dict(geometry=root.geometry(),tk_scaling=root.tk.call('tk','scaling'),dpi=root.winfo_fpixels('1i'),
                widgets=metrics,yview=page.table.yview(),rows=len(page.table.get_children()),selected=page.selected,pause=page.pause.get(),
                status=page.status.full_text,errors=errors,only_audio=page.output_controls is None and not page.movie,
                source_scrollbar=bool(ws.table_scroll.winfo_ismapped()),progress=page.job.state if page.job else None,
                pause_display=ws.pause_display.get(),empty_hint=bool(ws.empty_label.winfo_ismapped()),
                rowheight=int(__import__('tkinter').ttk.Style(root).lookup('Workspace.Treeview','rowheight')))
            if page.join_page is not None:
                j=page.join_page
                result['join_view']={k:{'yview':w.yview(),'text':w.get('1.0','end-1c')} for k,w in [('left',j.left_text),('right',j.right_text)]}
            target=evidence/(name+'.json');pending=target.with_suffix('.tmp')
            pending.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');pending.replace(target)
        all_rows=[];initial_selection=list(page.selected)
        def commands():
            root.after(200,commands)
            if len(page.rows)==16:all_rows[:]=page.rows
            command=work/'command.json'
            if command.exists():
                try:data=json.loads(command.read_text(encoding='utf-8'))
                except json.JSONDecodeError:return
                command.unlink()
                action=data['action']
                if action=='close':app.close();return
                if action=='size':
                    root.state('normal');root.geometry(data['geometry'])
                    if data.get('fold') is not None and app.focus_mode!=data['fold']:app.toggle_focus()
                elif action=='short':page.rows=page.rows[:4];page.render_rows()
                elif action=='empty':page.selected=[];page.rows=[];page.render_rows();page.update_controls()
                elif action=='count':
                    page.rows=[dict(r) for r in all_rows[:data['count']]];page.render_rows();page.update_controls()
                elif action=='jointext':
                    j=page.join_page
                    for name,w in [('前批',j.left_text),('後批',j.right_text)]:j.fill(w,'\n'.join(f'{name}第 {i+1} 行：接點文字捲動驗證。' for i in range(data.get('count',180))))
                elif action=='font':
                    from tkinter import ttk
                    ttk.Style(root).configure('.',font=('Microsoft JhengHei',data['size']))
                    ttk.Style(root).configure('Heading.TLabel',font=('Microsoft JhengHei',int(data['size']*1.1),'bold'))
                    page.assembly_workspace._geometry=None;page.assembly_workspace.resized()
                elif action=='long':page.selected=list(initial_selection);page.recheck()
                elif action=='measure':measure(data['name'])
                elif action=='capture':
                    from PIL import ImageGrab
                    import ctypes
                    root.update_idletasks()
                    hwnd=root.winfo_id()
                    ImageGrab.grab(window=hwnd).save(evidence/(data['name']+'.png'))
                    measure(data['name'])
            if root.winfo_exists():
                if app.production.current is page:measure()
        root.after(200,commands);print('fixture ready',flush=True);root.mainloop()
        (evidence/'native-close.json').write_text(json.dumps({'closed':True,'errors':errors}),encoding='utf-8')


if __name__=='__main__':main()
