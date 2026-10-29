"""Synthetic native UI evidence; OCR output/delay controlled, no network.

The separate real OCR integration evidence is pdf-refinement-real.json.
Close the PDF window and then the main window to release the temporary project.
"""
import argparse
from contextlib import ExitStack
from io import BytesIO
from pathlib import Path
import sys
import tempfile
import threading
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow
from ui_layout_visual_fixture import TEXT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=('candidate', 'busy', 'models', 'continue', 'retained'), default='candidate')
    parser.add_argument('--narrow', action='store_true')
    parser.add_argument('--settings', action='store_true')
    args = parser.parse_args()
    base = Path('.scratch/pdf-refinement-visual')
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=base) as folder, ExitStack() as stack:
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        path = Path(folder)
        pdfmetrics.registerFont(TTFont('RefinementChinese', 'C:/Windows/Fonts/msjh.ttc', subfontIndex=0))
        output = BytesIO()
        pdf = canvas.Canvas(output, pagesize=(600, 800))
        pdf.setFont('RefinementChinese', 18)
        for index, line in enumerate(TEXT.splitlines()):
            pdf.drawString(45, 750-index*24, line)
        pdf.save()
        source = path / '風與樹.pdf'
        source.write_bytes(output.getvalue())
        flow = ProjectWorkflow.create(path / 'book', '風與樹：局部辨識驗證')
        job = flow.start_pdf_extraction(flow.inspect_pdf(source), 1, 1)
        job.wait()
        batch = flow.finish_pdf_extraction(job)
        root, app = make_app()
        app.flow, app.batch_id = flow, batch
        app.refresh()
        app.compare_pdf_pages()
        dialog = app.pdf_dialog
        def until(predicate):
            deadline = time.monotonic()+20
            while not predicate() and time.monotonic() < deadline:
                root.update()
                time.sleep(.01)
            if not predicate():
                raise RuntimeError('Synthetic fixture timed out')
        until(lambda: dialog.ready and dialog.image is not None and not dialog.ocr_info_pending)
        if args.narrow:
            dialog.state('normal')
            dialog.geometry('740x570+30+30')
        if args.stage == 'models':
            dialog.toggle_settings()
        else:
            release = threading.Event()
            if args.stage != 'busy':
                release.set()
            results = iter(('第一段修正，已採用。', '第二段修正，已採用。', '錯誤辨識，應捨棄。'))
            def recognize(*_args, **_kwargs):
                release.wait(90)
                text = next(results) if args.stage == 'retained' else '清晨，山谷裡的風帶著露水的氣息。'
                return dict(text=text, selected_language='chi_tra+eng', confidence=95)
            stack.enter_context(patch('ebook2mp4.pdf.PdfExtraction.ocr_settings', return_value={'language': 'chi_tra+eng'}))
            stack.enter_context(patch('ebook2mp4.ocr.recognize_page', side_effect=recognize))
            start = dialog.text.search('清晨', '1.0', exact=True)
            end = dialog.text.search('。', start, exact=True)
            dialog.text.tag_add('sel', start, f'{end}+1c')
            dialog.region = (.05, .09, .9, .16)
            dialog.retry_region()
            if args.stage != 'busy':
                until(lambda: dialog.pending_job is not None and dialog.ready)
                if args.stage == 'continue':
                    dialog.continue_button.invoke()
                    until(lambda: dialog.ready)
                elif args.stage == 'retained':
                    for needle in ('他推開窗', '「今天'):
                        dialog.continue_button.invoke()
                        until(lambda: dialog.ready)
                        dialog.text.tag_remove('sel', '1.0', 'end')
                        start = dialog.text.search(needle, '1.0', exact=True)
                        end = dialog.text.search('。', start, exact=True)
                        dialog.text.tag_add('sel', start, f'{end}+1c')
                        dialog.region = (.05, .09, .9, .16)
                        dialog.retry_region()
                        until(lambda: dialog.pending_job is not None and dialog.ready)
                    dialog.original_choice.invoke()
            root.bind('<Destroy>', lambda event: release.set() if event.widget is root else None, add='+')
            # Release the OCR boundary immediately before normal cancellation/close.
            original_close = dialog.close
            def close():
                release.set()
                original_close()
            dialog.protocol('WM_DELETE_WINDOW', close)
        if args.settings:
            dialog.toggle_settings()
            if args.narrow:
                dialog.settings_window.geometry('600x430')
        root.after(600000, root.destroy)
        root.mainloop()


if __name__ == '__main__':
    main()
