"""Synthetic PDF/TXT book for reproducible visual QA; no private manuscript."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow
from ebook2mp4.pdf_desktop import PdfDialog
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

base = Path(__file__).resolve().parents[1] / '.scratch/t04-visual'
base.mkdir(parents=True, exist_ok=True)
source = base / '風與樹 PDF.pdf'
pdfmetrics.registerFont(UnicodeCIDFont('MSung-Light'))
doc = canvas.Canvas(str(source))
for number in range(1, 21):
    doc.setFont('MSung-Light', 16)
    doc.drawString(50, 780, f'第 {number} 章　風與樹')
    doc.setFont('MSung-Light', 12)
    doc.drawString(50, 740, '清晨，山谷裡的風帶著露水的氣息。')
    doc.drawString(50, 710, '他推開窗，看見樹影落在書頁上。')
    doc.drawString(50, 680, '繁體／简体與 English 3.14 U.S.A. 原文保留。')
    doc.drawString(50, 630, '這是合成測試書稿，供頁圖與文字對照。')
    doc.showPage()
doc.save()
folder = base / '書籍專案'
if (folder / 'project.json').exists():
    flow = ProjectWorkflow.open(folder)
else:
    flow = ProjectWorkflow.create(folder, '風與樹 · PDF／TXT')
    for start, end in ((3, 5), (6, 7)):
        job = flow.start_pdf_extraction(flow.inspect_pdf(source), start, end)
        job.wait()
        flow.finish_pdf_extraction(job)
    txt = base / '附錄.txt'
    txt.write_text('附錄。\n\n同書的 TXT 批次保留。', encoding='utf-8')
    flow.import_txt(flow.inspect_txt(txt))
root, app = make_app()
root.geometry('1040x640+0+0' if '--narrow' in sys.argv else '1360x780+0+0')
app.flow = flow
app.step = 2
app.refresh()
if '--preview' in sys.argv:
    root.after(200, lambda: setattr(app, 'pdf_dialog', PdfDialog(app, path=source)))
if '--compare' in sys.argv:
    root.after(200, app.compare_pdf_pages)
if '--cleanup' in sys.argv:
    root.after(200, app.cleanup_line_breaks)
root.mainloop()
