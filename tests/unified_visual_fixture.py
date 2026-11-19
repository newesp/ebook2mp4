"""Launch the real Tk workspace with synthetic text and a controlled AI service."""
from pathlib import Path
import json
import sys
import time
from unittest.mock import patch

from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow
from test_pdf import pdf_bytes


def main():
    folder = Path('.scratch/unified-visual')
    folder.mkdir(parents=True, exist_ok=True)
    source = folder/'source.pdf'
    source.write_bytes(pdf_bytes(3))
    if not (folder/'book/project.json').exists():
        flow = ProjectWorkflow.create(folder/'book', '文稿原生驗收')
        job = flow.start_pdf_extraction(flow.inspect_pdf(source), 1, 3)
        job.wait()
        batch = flow.finish_pdf_extraction(job)
        flow.save_draft(batch, '第一章 出發\n\n清晨的陽光穿過窗簾，落在書桌上。\n\n我翻開筆記，重新讀了一遍昨天寫下的文字。\n\n每一次出發，都從一個簡單的決定開始。\n\nHello original text.\n\n' + '\n\n'.join(f'第 {i} 段。保留原稿，逐步完成文稿。' for i in range(1,16)))
    else:
        flow = ProjectWorkflow.open(folder/'book')
        batch = flow.state['batches'][0]['id']
    def generate(key, model, parts):
        time.sleep(.7)
        return dict(paragraphs=[s.replace('昨天', '昨日').replace('original', 'corrected') for s in parts], notes=[])
    with patch('ebook2mp4.gemini.load_settings', return_value=dict(key='controlled-fixture', model='gemini-test')), patch('ebook2mp4.gemini.generate', side_effect=generate):
        root, app = make_app()
        app.flow, app.batch_id = flow, batch
        app.refresh()
        if not app.source_visible:
            app.toggle_source()
        app.open_tools(1)
        def commands():
            command = folder/'command.txt'
            if command.exists():
                action = command.read_text().strip()
                command.unlink()
                if action == 'restore':
                    root.state('normal')
                    root.geometry('1100x760')
                elif action == 'narrow':
                    root.state('normal')
                    root.geometry('900x640')
                elif action == 'close':
                    app.close()
                    return
                elif action == 'evidence':
                    result = dict(text=app.current_text, reading_ready=app.reading_ready(),
                        steps=len(app.steps), page=app.page_number.get(),
                        geometry=root.geometry(), source_visible=app.source_visible,
                        right_height=app.right_stack.winfo_height(), tool_height=app.tool_panel.winfo_height(),
                        center_size=[app.center.winfo_width(),app.center.winfo_height()],
                        panes=list(app.panes.panes()), sash=app.panes.sashpos(0) if len(app.panes.panes()) > 1 else None,
                        windows=[w.title() for w in root.winfo_children() if w.winfo_class() == 'Toplevel'])
                    Path('docs/verification/unified-manuscript/native-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            root.after(200, commands)
        root.after(200, commands)
        root.mainloop()


if __name__ == '__main__':
    main()
