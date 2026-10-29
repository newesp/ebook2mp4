"""Real Tk selection and candidate actions; only cloud/process boundaries controlled."""
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock

from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow


class OptimizationDesktop(unittest.TestCase):
    def setUp(self):
        base = Path('.scratch/test-runs')
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.root, self.app = make_app()
        self.addCleanup(self.root.destroy)
        self.app.flow = ProjectWorkflow.create(self.path/'book', '優化')

    def until(self, predicate):
        deadline = time.monotonic()+15
        while not predicate() and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.01)
        self.assertTrue(predicate())

    def test_normalization_controls_and_confirmation_connect_to_candidates(self):
        source = self.path/'source.txt'
        source.write_bytes('头发,文字.'.encode('utf-8'))
        self.app.batch_id = self.app.flow.import_txt(self.app.flow.inspect_txt(source))
        self.app.refresh()
        self.app.script.set('繁體')
        with patch('ebook2mp4.gemini.generate', return_value=dict(paragraphs=['头发,文字.'], notes=[])), \
                patch.dict(os.environ, GEMINI_API_KEY='fake'), \
                patch('ebook2mp4.desktop.messagebox.askyesno', return_value=True) as confirm:
            self.app.gemini_all_button.invoke()
            self.assertIn('本次採 繁體', confirm.call_args.args[1])
            dialog = self.app.gemini_dialog
            self.until(lambda: dialog.job is None)
            dialog.geometry('740x570')
            self.root.update()
            self.assertEqual(dialog.candidate.get('1.0', 'end-1c'), '頭髮，文字。')
            self.assertEqual(self.app.current_text, '头发,文字.')
            dialog.accept_button.invoke()
            self.assertEqual(self.app.current_text, '頭髮，文字。')
            dialog.close()

    @unittest.skipUnless(os.environ.get('EBOOK2MP4_REAL_OCR_HOME'), 'requires installed model files')
    def test_canvas_region_and_selected_raw_text_produce_partial_candidate(self):
        from test_pdf import pdf_bytes
        source = self.path/'source.pdf'
        source.write_bytes(pdf_bytes(1))
        flow = self.app.flow
        job = flow.start_pdf_extraction(flow.inspect_pdf(source), 1, 1)
        self.assertTrue(job.wait(5))
        batch = flow.finish_pdf_extraction(job)
        original = flow.pdf_pages(batch)[0]['text']
        self.app.batch_id = batch
        self.app.refresh()
        with patch.dict(os.environ, EBOOK2MP4_OCR_HOME=os.environ['EBOOK2MP4_REAL_OCR_HOME']):
            self.app.pages_button.invoke()
            dialog = self.app.pdf_dialog
            self.until(lambda: dialog.ready)
            dialog.state('normal')
            dialog.geometry('740x570')
            self.root.update()
            dialog.resize_image()
            dialog.region_button.invoke()
            self.assertIn('框選', dialog.progress.cget('text'))
            left, top = dialog.image_origin
            x0, y0 = int(left+5), int(top+5)
            x1 = int(left+min(dialog.image.width()-5, 170))
            y1 = int(top+min(dialog.image.height()-5, 95))
            dialog.canvas.event_generate('<ButtonPress-1>', x=x0, y=y0)
            dialog.canvas.event_generate('<B1-Motion>', x=x1, y=y1)
            dialog.canvas.event_generate('<ButtonRelease-1>', x=x1, y=y1)
            self.root.update()
            self.assertIsNotNone(dialog.region)
            dialog.text.tag_add('sel', '1.0', '1.7')
            dialog.language.set('英文')
            dialog.layout.set('單一區塊')
            process = MagicMock(returncode=0)
            process.poll.return_value = 0
            process.communicate.return_value = (b'level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n5\t1\t1\t1\t1\t1\t40\t40\t90\t20\t95\t"Recovered\n5\t1\t1\t1\t1\t2\t130\t40\t90\t20\t95\tworld"\n', b'')
            with patch('subprocess.Popen', return_value=process):
                dialog.region_button.invoke()
                self.until(lambda: dialog.pending_job is not None and dialog.ready)
            self.assertEqual(dialog.text.get('1.0', 'end-1c'), '"Recovered world"'+original[7:])
            self.assertIn('confidence', dialog.candidate_pages[0]['settings'])
            self.assertEqual(flow.pdf_pages(batch)[0]['text'], original)
            self.assertFalse(dialog.region_button.winfo_ismapped(), 'Recognition tools are hidden while a candidate awaits adoption')
            self.assertTrue(dialog.accept_button.winfo_ismapped())
            for button in (dialog.accept_button, dialog.cancel_button):
                self.assertLessEqual(button.winfo_rootx()+button.winfo_width(), dialog.winfo_rootx()+dialog.winfo_width())
                self.assertLessEqual(button.winfo_rooty()+button.winfo_height(), dialog.winfo_rooty()+dialog.winfo_height())
            dialog.close()
            self.until(lambda: self.app.pdf_dialog is None)
