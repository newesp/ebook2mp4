"""Owned offline project and observable commands for native/EXE join QA."""
import argparse
import json
import os
from pathlib import Path
import shutil
import time
from unittest.mock import AsyncMock, patch

from ebook2mp4.workflow import ProjectWorkflow
from test_assembly_joins import AssemblyJoinJourney
import test_voice


ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/os.environ.get('JOIN_QA_WORK', '.scratch/audio-join-review')
EVIDENCE=ROOT/os.environ.get('JOIN_QA_EVIDENCE', 'docs/verification/audio-join-workspace')


def isolated_env():
    for key,folder in [('EBOOK2MP4_APP_HOME','app-home'),('EBOOK2MP4_VOICE_HOME','voice-home'),('EBOOK2MP4_KOKORO_HOME','kokoro-home')]:
        os.environ[key]=str(WORK/folder)


def seed():
    isolated_env()
    WORK.mkdir(parents=True,exist_ok=True)
    book=WORK/'book'
    if not book.exists():
        c=AssemblyJoinJourney();c.setUp()
        try:
            ids=c.pdf_batches()
            for i,b in enumerate(ids):c.flow.rename_batch(b,f'第 {i+1} 章')
            c.narrate(ids)
            c.flow.save_assembly_settings(ids)
            shutil.copytree(c.flow.root,book)
        finally:c.doCleanups()
    (WORK/'app-home').mkdir(exist_ok=True)
    (WORK/'app-home/session.json').write_text(json.dumps({'last_project':str(book)}),encoding='utf-8')
    return book


def bounds(w):
    return dict(x=w.winfo_rootx(),y=w.winfo_rooty(),width=w.winfo_width(),height=w.winfo_height(),mapped=bool(w.winfo_ismapped()))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seed-only',action='store_true');args=ap.parse_args()
    book=seed()
    if args.seed_only:print(book,flush=True);return
    from ebook2mp4.desktop import make_app
    from tkinter import ttk
    EVIDENCE.mkdir(exist_ok=True,parents=True)
    with patch('edge_tts.list_voices',new=AsyncMock(return_value=test_voice.VOICES)):
        root,app=make_app()
        app.flow=ProjectWorkflow.open(book);app.batch_id=app.flow.state['batches'][0]['id'];app.refresh();app.total_audio()
        p=app.production.current
        root.state('normal');root.geometry('1360x820+0+0')
        errors=[];root.report_callback_exception=lambda t,v,b:errors.append(str(v))
        ready=False
        def measure(name='live'):
            if p.join_page is None:return
            j=p.join_page;ws=j.workspace
            widgets={n:getattr(j,n) for n in ['left_text','right_text','left_edit','right_edit','pair_control','previous','next','pause_control','clip_control','play_button','stop_button','save_button','back_button']}
            widgets.update(footer=ws.footer,files=ws.files_button,detail=ws.detail_text,detail_scroll=ws.detail_scroll,
                           disclosure=ws.disclosure,left_scroll=ws.panes[0].scroll,right_scroll=ws.panes[1].scroll,
                           file_list=ws.file_list,file_scroll=ws.file_scroll,main=ws.main,body=ws.body,
                           left_header=app.list_header,right_header=ws.header,title=ws.title,left_content=app.shell.documents.batch_view)
            result=dict(geometry=root.geometry(),dpi=root.winfo_fpixels('1i'),tk_scaling=root.tk.call('tk','scaling'),
                        focus=str(root.focus_get()),pointer=root.winfo_pointerxy(),
                        widgets={k:bounds(w) for k,w in widgets.items()},left_yview=j.left_text.yview(),right_yview=j.right_text.yview(),
                        detail_yview=ws.detail_text.yview(),file_yview=ws.file_list.yview(),selected=p.selected,pause=p.pause.get(),
                        accepted=list(p.accepted_joins),details=ws.details_open,dedicated=ws.dedicated,files=ws.files_open,
                        content_kind=j.content_kind,status=j.status.cget('text'),saved=ws.saved.cget('text'),errors=errors)
            target=EVIDENCE/(name+'.json');temp=target.with_suffix('.tmp');temp.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(target)
        def commands():
            nonlocal ready
            if not ready and p.check_job is None:
                p.join_button.invoke();ready=True
            command=WORK/'command.json'
            if command.exists() and p.join_page and p.join_page.info_job is None:
                try:
                    data=json.loads(command.read_text(encoding='utf-8-sig'))
                except json.JSONDecodeError:
                    root.after(150,commands)
                    return
                command.unlink()
                j=p.join_page;ws=j.workspace;action=data['action']
                if action=='close':app.close();return
                if action=='size':root.state('normal');root.geometry(data['geometry'])
                elif action=='font':ttk.Style(root).configure('.',font=('Microsoft JhengHei',data['size']));ws.resized()
                elif action=='text':
                    for side,label in [('left','前批'),('right','後批')]:j.fill(getattr(j,side+'_text'),'\n'.join(f'{label}第 {i+1} 行：接點閱讀與捲動驗證。' for i in range(data.get('count',180))))
                elif action=='detailtext':j.fill(ws.detail_text,'\n'.join(f'警告詳情第 {i+1} 行：來源頁次與批次範圍。' for i in range(data['count'])));ws.resized()
                elif action=='capture':
                    from PIL import ImageGrab
                    root.update_idletasks();ImageGrab.grab(window=root.winfo_id()).save(EVIDENCE/(data['name']+'.png'));measure(data['name'])
                elif action=='measure':measure(data['name'])
                elif action=='restore':j._displayed_key=None;j.render()
            if root.winfo_exists():measure();root.after(150,commands)
        root.after(150,commands);print('Join fixture ready',flush=True);root.mainloop()
        (EVIDENCE/'native-close.json').write_text(json.dumps(dict(closed=True,errors=errors)),encoding='utf-8')


if __name__=='__main__':main()
