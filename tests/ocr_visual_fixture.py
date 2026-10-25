"""Synthetic raster scan for reproducible T05 visual and real-download verification."""
from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow
from ebook2mp4.pdf_desktop import PdfDialog
from test_ocr import scanned_pdf

base = Path(__file__).resolve().parents[1] / '.scratch/t05-visual'
base.mkdir(parents=True, exist_ok=True)
os.environ['EBOOK2MP4_OCR_HOME'] = str(base / 'models')
source = base / '清晰掃描.pdf'
source.write_bytes(scanned_pdf(['繁體中文閱讀測試\nEnglish reading 123.', '']))
folder = base / '專案'
flow = ProjectWorkflow.open(folder) if (folder / 'project.json').exists() else ProjectWorkflow.create(folder, '掃描書籍 · OCR 驗證')
root, app = make_app()
root.geometry('1040x640+0+0')
app.flow = flow
app.refresh()

def preview():
    app.pdf_dialog = PdfDialog(app, path=source)
    app.pdf_dialog.geometry('740x570+20+20')
    def configure():
        dialog = app.pdf_dialog
        if not dialog.ready:
            root.after(50, configure)
            return
        dialog.mode.set('全部強制 OCR')
        dialog.ocr_changed()
    root.after(100, configure)

root.after(200, preview)
root.mainloop()
