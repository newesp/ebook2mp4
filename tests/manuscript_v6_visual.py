"""Isolated real-Tk v6 acceptance fixture; commands only drive test-owned data."""
from pathlib import Path
import json
import os
import time
from unittest.mock import patch

from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow
from test_pdf import pdf_bytes

BASE = Path('.scratch/v6-runtime')
EVIDENCE = Path('docs/verification/unified-manuscript-v6')


def main():
    BASE.mkdir(parents=True, exist_ok=True)
    source = BASE/'source.pdf'
    source.write_bytes(pdf_bytes(3))
    flow = ProjectWorkflow.create(BASE/'book', '第六版原生驗收')
    job = flow.start_pdf_extraction(flow.inspect_pdf(source), 1, 3)
    job.wait()
    batch = flow.finish_pdf_extraction(job)
    text = '\n\n'.join(f'第 {i} 段。清晨的陽光穿過窗簾，落在書桌上。保留原稿，檢查文稿。Hello original text.' for i in range(1, 401))
    flow.save_draft(batch, text)
    flow.save_reading_manuscript(batch, text)
    extra = BASE/'chapter.txt'
    extra.write_text('另一份文件。', encoding='utf-8')
    flow.import_txt(flow.inspect_txt(extra))
    flow.save_workspace(batch, text.replace('原稿', '人工稿'))

    def generate(key, model, parts):
        time.sleep(.15)
        return dict(paragraphs=[s.replace('original', 'corrected') for s in parts], notes=[])

    def measure(name):
        widgets = dict(client=root, body=app.body, list=app.batch_list, source=app.image_frame,
                       source_pane=app.source_frame, editor_pane=app.right_stack, editor=app.editor,
                       center=app.center, tool=app.tool_panel, next=app.next_button,
                       button=app.pdf_previous, entry=app.page_entry, combo=app.zoom_control)
        metrics = {k: dict(x=w.winfo_rootx(), y=w.winfo_rooty(), width=w.winfo_width(),
                          height=w.winfo_height(), mapped=bool(w.winfo_ismapped())) for k,w in widgets.items()}
        import tkinter.font as font
        import ctypes
        f = font.Font(root=root, font=app.editor.cget('font'))
        record = dict(name=name, tk_scaling=root.tk.call('tk','scaling'), dpi=root.winfo_fpixels('1i'),
                      windows_scale_percent=ctypes.windll.shcore.GetScaleFactorForDevice(0),
                      source_image_ready=app.source_image is not None, source_image_items=len(app.image_canvas.find_all()),
                      geometry=root.geometry(), pid=os.getpid(), font_linespace=f.metrics('linespace'),
                      visible_lines=app.editor.count('@0,0', f'@0,{app.editor.winfo_height()}', 'displaylines'),
                      characters=len(app.current_text), selection=tuple(map(str,app.editor.tag_ranges('sel'))),
                      cursor=app.editor.index('insert'), yview=app.editor.yview(),
                      panes=list(app.panes.panes()), source_ratio=app.source_sash,
                      tools_open=app.tools_open, reading_ready=app.reading_ready(), metrics=metrics)
        (EVIDENCE/(name+'.json')).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')

    with patch('ebook2mp4.gemini.load_settings', return_value=dict(key='controlled-fixture',model='gemini-test')), patch('ebook2mp4.gemini.generate', side_effect=generate):
        root, app = make_app()
        app.flow, app.batch_id = flow, batch
        app.refresh()
        root.report_callback_exception = lambda *args: (EVIDENCE/'callback-error.txt').write_text(str(args),encoding='utf-8')

        def commands():
            command = BASE/'command.json'
            if command.exists():
                data = json.loads(command.read_text(encoding='utf-8'))
                command.unlink()
                action = data['action']
                if action == 'measure':
                    measure(data['name'])
                elif action == 'size':
                    root.state('normal')
                    root.geometry(data['geometry'])
                elif action == 'maximize':
                    root.state('zoomed')
                elif action == 'font':
                    app.font_size.set(data['size'])
                    app.save_manuscript_settings()
                elif action == 'versions':
                    app.show_versions()
                elif action == 'source':
                    app.compare_pdf_pages()
                elif action == 'settings':
                    app.gemini_settings()
                elif action == 'diff_end':
                    app.version_diff.yview_moveto(1)
                elif action == 'preview':
                    app.cleanup_line_breaks()
                elif action == 'draft':
                    app.close_tools()
                elif action == 'close':
                    app.close()
                    return
            root.after(150, commands)
        root.after(150, commands)
        root.mainloop()


if __name__ == '__main__':
    main()
