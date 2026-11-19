"""Isolated native acceptance: cleanup states and footer state transitions."""
from pathlib import Path
import hashlib
import json
import time
from unittest.mock import patch

from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectError, ProjectWorkflow

BASE = Path('.scratch/cleanup-visual')
EVIDENCE = Path('docs/verification/manuscript-cleanup-footer')


def main():
    BASE.mkdir(parents=True, exist_ok=True)
    flow = ProjectWorkflow.create(BASE/'book', '換行預覽與底列驗收')
    values = [
        ('換行整理範例', '\n\n'.join(f'第 {i} 段。清晨的陽光穿過窗簾，落在書桌上。\n保留原稿，檢查文稿。' for i in range(1, 201))),
        ('無須整理範例', '第一段保留原文。\n\n第二段沒有版面換行。'),
        ('未完成校對範例', '第一行。\n第二行。\n\n保留未完成校對的原文。')]
    batches = []
    for name, text in values:
        source = BASE/(name+'.txt')
        source.write_text(text, encoding='utf-8')
        batches.append(flow.import_txt(flow.inspect_txt(source)))
    flow.save_reading_manuscript(batches[1], values[1][1])

    def failed_service(*_args):
        time.sleep(.5)
        raise ProjectError('受控服務失敗；可繼續校對或保留原文。')

    with patch('ebook2mp4.gemini.load_settings', return_value=dict(key='controlled', model='gemini-test')), patch('ebook2mp4.gemini.generate', side_effect=failed_service):
        root, app = make_app()
        app.flow, app.batch_id = flow, batches[0]
        app.refresh()
        app.focus_mode = True
        app.render_step()
        root.report_callback_exception = lambda *args: (EVIDENCE/'callback-errors.txt').write_text(str(args), encoding='utf-8')

        def measure(name):
            controls = dict(next=app.next_button, message=app.message_button, retry=app.retry_button,
                keep=app.keep_partial_button, job=app.job_bar, status=app.job_status,
                cancel=app.cleanup_preview.cancel_button, apply=app.cleanup_preview.apply_button,
                result=app.cleanup_preview.result, diff=app.cleanup_preview.diff,
                empty=app.cleanup_preview.empty, source_run=app.source_tools.run_button,
                source_settings=app.source_tools.form_button)
            record = dict(geometry=root.geometry(), dpi=root.winfo_fpixels('1i'),
                active_tool=app.active_tool, title=app.tool_title.cget('text'),
                text_sha256=hashlib.sha256(app.current_text.encode()).hexdigest(),
                cursor=app.editor.index('insert'), yview=app.editor.yview(),
                selected=list(map(str,app.editor.tag_ranges('sel'))), reading_ready=app.reading_ready(),
                allow_partial=app.allow_partial, preview_changes=app.cleanup_preview.change_count,
                diff_yview=app.cleanup_preview.diff.yview(),
                controls={k:dict(x=w.winfo_rootx(),y=w.winfo_rooty(),width=w.winfo_width(),height=w.winfo_height(),
                    mapped=bool(w.winfo_ismapped()), text=w.cget('text') if 'text' in w.keys() else '',
                    disabled=w.instate(['disabled']) if hasattr(w,'instate') else False) for k,w in controls.items()})
            (EVIDENCE/(name+'.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')

        def commands():
            path = BASE/'command.json'
            if path.exists():
                data = json.loads(path.read_text(encoding='utf-8'))
                path.unlink()
                action = data['action']
                if action in ('changed', 'unchanged', 'partial'):
                    app.close_tools()
                    app.batch_id = batches[{'changed':0,'unchanged':1,'partial':2}[action]]
                    app.refresh()
                    if action == 'partial':
                        app.gemini_review()
                    else:
                        app.cleanup_button.invoke()
                elif action == 'measure':
                    measure(data['name'])
                elif action == 'size':
                    root.state('normal')
                    root.geometry(data['geometry'])
                elif action == 'max':
                    root.state('zoomed')
                elif action == 'failure':
                    with patch.object(app.flow, 'save_workspace', side_effect=ProjectError('受控保存失敗，請重試；原稿保留。')):
                        app.cleanup_preview.apply()
                elif action == 'close':
                    app.close()
                    return
            root.after(150, commands)
        root.after(150, commands)
        root.mainloop()


if __name__ == '__main__':
    main()
