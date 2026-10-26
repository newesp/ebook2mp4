"""Synthetic T07 candidate at minimum native window sizes; no network calls."""
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow
from ebook2mp4.gemini_desktop import ReviewDialog

base = Path('.scratch/t07-visual').resolve()
base.mkdir(parents=True, exist_ok=True)
source = base / 'synthetic.txt'
original = '這是一段轉錄錯宇。\n\nHe said, “Hello world!”\n\n第三段保持原文。'
source.write_bytes(original.encode('utf-8'))
flow = ProjectWorkflow.create(base / 'book', 'T07 合成校對驗證')
batch = flow.import_txt(flow.inspect_txt(source))
with patch('ebook2mp4.gemini.generate', return_value=dict(paragraphs=[
        '這是一段轉錄錯字。', 'He said, “Hello, world!”', '第三段保持原文。'], notes=['不確定詞語應保留原字，請對照來源。'])), patch.dict('os.environ', GEMINI_API_KEY='fixture'):
    job = flow.start_gemini_review(batch)
    job.wait()
    flow.finish_gemini_review(job)
root, app = make_app()
root.geometry('1040x640+0+0')
app.flow, app.batch_id = flow, batch
app.refresh()
app.gemini_dialog = ReviewDialog(app)
app.gemini_dialog.geometry('740x570+30+30')
root.mainloop()
