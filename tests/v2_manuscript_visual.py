"""Native v2 acceptance surface with test-only sizing and measurement commands."""
from pathlib import Path
import ctypes
import hashlib
import json
import os
import tkinter.font as tkfont

from ebook2mp4.workflow import ProjectWorkflow
from ebook2mp4.desktop import make_app
from test_pdf import pdf_bytes

BASE = Path('.scratch/v2-work/visual').resolve()
EVIDENCE = Path('docs/verification/v2-manuscript').resolve()


def main():
    BASE.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    source = BASE/'source.pdf'
    source.write_bytes(pdf_bytes(3))
    book = BASE/'book'
    if not book.exists():
        flow = ProjectWorkflow.create(book, 'v2 合成文稿驗收')
        job = flow.start_pdf_extraction(flow.inspect_pdf(source), 1, 3)
        assert job.wait(10)
        batch = flow.finish_pdf_extraction(job)
        text = '\n\n'.join(f'第 {i} 段。清晨陽光照進書房。保留來源，檢查人工文稿與版本。Hello original text.' for i in range(1,401))
        flow.save_draft(batch, text)
        flow.save_reading_manuscript(batch, text)
        extra = BASE/'extra.txt'
        extra.write_text('另一份獨立文件。', encoding='utf-8')
        flow.import_txt(flow.inspect_txt(extra))
        flow.save_workspace(batch, text.replace('來源', '原稿'))
    else:
        flow = ProjectWorkflow.open(book)
        batch = flow.state['batches'][0]['id']
    root, app = make_app()
    app.flow, app.batch_id = flow, batch
    app.refresh()
    errors = []
    root.report_callback_exception = lambda kind, value, trace: errors.append(str(value))

    def measure(name):
        controls = dict(client=root, source=app.source_frame, editor_pane=app.right_stack,
            editor=app.editor, list=app.batch_list, center=app.center, body=app.body,
            next=app.next_button, source_menu=app.source_control,
            previous=app.pdf_previous, page=app.page_entry, total=app.page_total,
            next_page=app.pdf_next, zoom=app.zoom_control, tool=app.tool_host,
            tool_back=app.tool_back, project=app.project_menu.master, messages=app.message_button)
        metrics = {key: dict(x=w.winfo_rootx(),y=w.winfo_rooty(),width=w.winfo_width(),
            height=w.winfo_height(),mapped=bool(w.winfo_ismapped())) for key,w in controls.items()}
        pairs=(('previous','page'),('total','next_page'),('next_page','zoom'),('zoom','source_menu'))
        gaps=[metrics[b]['x']-metrics[a]['x']-metrics[a]['width'] for a,b in pairs]
        font=tkfont.Font(root=root,font=app.editor.cget('font'))
        record=dict(name=name,pid=os.getpid(),geometry=root.geometry(),
            tk_scaling=root.tk.call('tk','scaling'),dpi=root.winfo_fpixels('1i'),
            windows_scale_percent=ctypes.windll.shcore.GetScaleFactorForDevice(0),
            font_linespace=font.metrics('linespace'),
            visible_lines=app.editor.count('@0,0',f'@0,{app.editor.winfo_height()}','displaylines'),
            characters=len(app.current_text), text_sha256=hashlib.sha256(app.current_text.encode()).hexdigest(),
            cursor=app.editor.index('insert'),selection=list(map(str,app.editor.tag_ranges('sel'))),
            yview=app.editor.yview(),tools_open=app.tools_open,gaps=gaps,metrics=metrics,errors=errors)
        (EVIDENCE/(name+'.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')

    def poll():
        command=BASE/'command.json'
        if command.exists():
            data=json.loads(command.read_text(encoding='utf-8'))
            command.unlink()
            if data['action']=='measure':measure(data['name'])
            elif data['action']=='size':
                root.state('normal');root.geometry(data['geometry'])
            elif data['action']=='font':
                app.font_size.set(data['size']);app.save_manuscript_settings()
            elif data['action']=='maximize':root.state('zoomed')
            elif data['action']=='close':app.close();return
        root.after(100,poll)
    root.after(100,poll)
    root.mainloop()
    (EVIDENCE/'source-exit.json').write_text(json.dumps(dict(normal_exit=True,errors=errors)),encoding='utf-8')


if __name__=='__main__':main()
