"""Native T08 minimum-size visual fixture, synthetic text and controlled service."""
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ebook2mp4.desktop import make_app
from ebook2mp4.gemini_desktop import ReviewDialog
from ebook2mp4.workflow import ProjectWorkflow, ProjectError

base = Path('.scratch/t08/visual').resolve()
base.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(dir=base) as temp:
    folder = Path(temp)
    source = folder / 'synthetic.txt'
    source.write_bytes('\n\n'.join((title + '這是合成驗證內容。' * 390) for title in ('第一段。', '第二段。', '第三段。')).encode('utf-8'))
    flow = ProjectWorkflow.create(folder / 'book', 'T08 合成長稿驗證')
    batch = flow.import_txt(flow.inspect_txt(source))
    def service(key, model, paragraphs):
        if paragraphs[0].startswith('第二段'):
            raise ProjectError('中段網路錯誤（合成驗證）；可只重試此範圍。')
        return dict(paragraphs=paragraphs, notes=['請人工對照原文。'])
    with patch.dict('os.environ', GEMINI_API_KEY='fixture'), patch('ebook2mp4.gemini.generate', side_effect=service):
        job = flow.start_gemini_review(batch)
        job.wait()
        flow.finish_gemini_review(job)
    root, app = make_app()
    try:
        root.geometry('1040x640+0+0')
        app.flow, app.batch_id = flow, batch
        app.refresh()
        app.gemini_dialog = ReviewDialog(app)
        dialog = app.gemini_dialog
        dialog.title('T08 合成長稿驗證 · 部分成功')
        dialog.geometry('740x570+40+40')
        dialog.paragraph.current(1)
        dialog.show_paragraph()
        root.withdraw()
        dialog.deiconify()
        dialog.lift()
        def check_stop():
            if (base.parent / 'visual-stop').exists():
                dialog.close()
                root.quit()
            else:
                root.after(300, check_stop)
        root.after(300, check_stop)
        root.mainloop()
    finally:
        root.destroy()
