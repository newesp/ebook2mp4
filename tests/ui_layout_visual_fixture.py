"""Real UI visual fixture with synthetic PDF/TXT and memory-only cloud substitute.

Run with PYTHONPATH including the locked PDF/test dependencies.
Every project created by this fixture is removed when its window closes.
"""
import argparse
from io import BytesIO
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow

TEXT = '''第一章　風與樹

清晨，山谷裡的風帶著露水的氣息。
他推開窗，看見樹影落在書頁上。

「今天就從這一頁開始吧。」她說。

他把書放在桌上，沿著文字慢慢往下讀。
窗外的樹葉輕輕晃動，陽光停在紙上。

校對時，先看清楚原文。
遇到不確定的地方，再回到原頁，核對字形與上下文。

有些斷行，只是排版留下的痕跡。
風仍然吹著，書頁也仍然攤開。

這是合成書稿，用於驗證原生介面的配置與可讀性。'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--screen', choices=('main', 'ai', 'confirm', 'pdf', 'breaks', 'review'), default='main')
    parser.add_argument('--narrow', action='store_true')
    args = parser.parse_args()
    base = Path('.scratch/ui-layout-visual')
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=base) as folder:
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        path = Path(folder)
        pdfmetrics.registerFont(TTFont('LayoutChinese', 'C:/Windows/Fonts/msjh.ttc', subfontIndex=0))
        output = BytesIO()
        pdf = canvas.Canvas(output, pagesize=(600, 800))
        for page in range(1, 4):
            pdf.setFont('LayoutChinese', 18)
            pdf.drawString(55, 735, '第一章　風與樹')
            pdf.setFont('LayoutChinese', 13)
            for index, line in enumerate(TEXT.splitlines()[2:]):
                pdf.drawString(55, 675-index*25, line)
            pdf.drawCentredString(300, 35, str(page))
            pdf.showPage()
        pdf.save()
        source = path / '風與樹 第一章.pdf'
        source.write_bytes(output.getvalue())
        flow = ProjectWorkflow.create(path / 'book', '風與樹')
        job = flow.start_pdf_extraction(flow.inspect_pdf(source), 1, 3)
        job.wait()
        first = flow.finish_pdf_extraction(job)
        flow.save_draft(first, TEXT)
        for index in range(2, 4):
            txt = path / f'第{index}章.txt'
            txt.write_bytes(TEXT.replace('第一章', f'第{index}章').encode('utf-8'))
            batch = flow.import_txt(flow.inspect_txt(txt))
            if index == 2:
                flow.record_source_issues(batch, ['請核對本章的來源字形。'])
            else:
                flow.confirm_reading(batch)
        root, app = make_app()
        root.geometry('1040x640+20+20' if args.narrow else '1360x820+20+20')
        app.flow, app.batch_id, app.step = flow, first, 2
        app.refresh()
        if not args.narrow:
            root.state('zoomed')
        if args.screen in ('ai', 'confirm'):
            app.open_tools(1) if args.screen == 'ai' else app.show_step(3)
        elif args.screen == 'pdf':
            app.compare_pdf_pages()
            if args.narrow:
                app.pdf_dialog.state('normal')
                app.pdf_dialog.geometry('740x570+20+20')
        elif args.screen == 'breaks':
            app.cleanup_line_breaks()
        elif args.screen == 'review':
            paragraphs = [part for part in TEXT.split('\n\n') if part.strip()]
            with patch('ebook2mp4.gemini.generate', return_value=dict(paragraphs=paragraphs, notes=['請對照來源核對文字，合成示例未連線。'])), patch.dict('os.environ', GEMINI_API_KEY='synthetic-only'):
                job = flow.start_gemini_review(first)
                job.wait()
                flow.finish_gemini_review(job)
            app.gemini_history()
        root.after(600000, root.destroy)
        root.mainloop()


if __name__ == '__main__':
    main()
