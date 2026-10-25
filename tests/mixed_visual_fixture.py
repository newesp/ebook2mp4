"""Synthetic T06 visual fixture; runtime data is confined to .scratch/t06-visual."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow
from ebook2mp4.pdf_desktop import PdfDialog
from test_mixed_pdf import mixed_pdf

base = Path(__file__).resolve().parents[1] / '.scratch/t06-visual'
base.mkdir(parents=True, exist_ok=True)
source = base / '混合頁面.pdf'
source.write_bytes(mixed_pdf())
folder = base / 'book'
flow = ProjectWorkflow.open(folder) if (folder / 'project.json').exists() else ProjectWorkflow.create(folder, 'T06 混合 PDF')
if not flow.state['batches']:
    job = flow.start_pdf_extraction(flow.inspect_pdf(source), 1, 4, mode='auto', language='英文')
    job.wait()
    flow.finish_pdf_extraction(job)
root, app = make_app()
root.geometry('1040x640+0+0')
app.flow = flow
app.batch_id = flow.state['batches'][0]['id']
app.refresh()

def compare():
    app.pdf_dialog = PdfDialog(app, batch_id=app.batch_id)
    app.pdf_dialog.geometry('740x570+20+20')
    app.pdf_dialog.language.set('英文')
    def select():
        dialog = app.pdf_dialog
        if not dialog.ready:
            root.after(50, select)
            return
        dialog.page.set('3')
        dialog.view()
    root.after(100, select)

root.after(200, compare)
root.after(600000, root.destroy)
root.mainloop()
