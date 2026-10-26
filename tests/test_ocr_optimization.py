"""Real OCR optimization through ProjectWorkflow, including the reported book title."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ebook2mp4.workflow import ProjectWorkflow, ProjectError


@unittest.skipUnless(os.environ.get('EBOOK2MP4_BOOK_PDF'), 'requires supplied book and real models')
class OcrOptimization(unittest.TestCase):
    def setUp(self):
        base = Path('.scratch/test-runs')
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.flow = ProjectWorkflow.create(Path(self.temp.name)/'book', '原稿優化')
        self.preview = self.flow.inspect_pdf(os.environ['EBOOK2MP4_BOOK_PDF'])

    def test_auto_language_recovers_reported_title_without_script_conversion(self):
        job = self.flow.start_pdf_extraction(self.preview, 1, 1, mode='ocr', language='自動中英', layout='auto')
        self.addCleanup(lambda: (job.cancel(), job.wait()))
        self.assertTrue(job.wait(120))
        batch = self.flow.finish_pdf_extraction(job)
        page = self.flow.pdf_pages(batch)[0]
        compact = ''.join(page['text'].split())
        self.assertIn('再简单也不过了', compact.split('今日今夜')[0], 'must recover large title, not just repeated footer')
        self.assertEqual(page['settings']['selected_language'], 'chi_sim+eng')
        self.assertIn('confidence', page['settings'])

    def test_region_retry_replaces_only_selected_raw_text_and_keeps_manual_draft(self):
        job = self.flow.start_pdf_extraction(self.preview, 1, 1, mode='ocr', language='繁中＋英文')
        self.addCleanup(lambda: (job.cancel(), job.wait()))
        self.assertTrue(job.wait(60))
        batch = self.flow.finish_pdf_extraction(job)
        original = self.flow.pdf_pages(batch)[0]['text']
        self.assertIn('FR Pu Al', original)
        self.assertEqual(self.flow.pdf_pages(batch)[0]['status'], 'pending')
        start = original.index('1. FR')
        end = start+len('1. FR Pu Al')
        self.flow.save_draft(batch, '人工校對全文保留。')
        job = self.flow.start_pdf_retry(batch, pages=[1], language='自動中英', layout='line',
                 region=(.53, .325, .80, .36), text_range=(start,end))
        self.addCleanup(lambda: (job.cancel(), job.wait()))
        self.assertTrue(job.wait(60))
        page = self.flow.pdf_extraction_pages(job)[0]
        self.assertIn('再简单也不过了', ''.join(page['text'].split()))
        self.assertTrue(page['text'].startswith(original[:start]))
        self.assertTrue(page['text'].endswith(original[end:]))
        new = self.flow.finish_pdf_extraction(job, accepted_pages=[1])
        self.assertEqual(self.flow.texts(batch)[1], '人工校對全文保留。')
        self.assertEqual(ProjectWorkflow.open(self.flow.root).pdf_pages(new)[0]['text'], page['text'])

    def test_region_validation_and_cancellation_preserve_original_page_text(self):
        job = self.flow.start_pdf_extraction(self.preview, 1, 1)
        self.assertTrue(job.wait(10))
        batch = self.flow.finish_pdf_extraction(job)
        # Use a nonempty OCR original, because the supplied page has no text layer.
        job = self.flow.start_pdf_retry(batch, pages=[1], language='簡中＋英文')
        self.assertTrue(job.wait(30))
        batch = self.flow.finish_pdf_extraction(job)
        original = self.flow.pdf_pages(batch)[0]['text']
        for region in ((0,0,0,1), (0,0,2,1), (0,float('nan'),1,1)):
            with self.assertRaises(ProjectError):
                self.flow.start_pdf_retry(batch, pages=[1], region=region, text_range=(0,1))
        job = self.flow.start_pdf_retry(batch, pages=[1], language='自動中英', layout='line',
                                       region=(.53,.325,.8,.36), text_range=(0,1))
        job.cancel()
        self.assertTrue(job.wait(20))
        self.assertEqual(self.flow.pdf_extraction_pages(job)[0]['text'], original)
        self.flow.discard_pdf_extraction(job)

    def test_small_screenshot_stays_pending_when_confidence_is_low(self):
        from io import BytesIO
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        output = BytesIO()
        doc = canvas.Canvas(output, pagesize=(412,228))
        doc.drawImage(ImageReader('docs/examples/ocr-mixed-font-title.png'),0,0,width=412,height=228)
        doc.save()
        source = Path(self.temp.name)/'screenshot.pdf'
        source.write_bytes(output.getvalue())
        job = self.flow.start_pdf_extraction(self.flow.inspect_pdf(source),1,1,mode='ocr',language='自動中英',layout='auto')
        self.addCleanup(lambda: (job.cancel(),job.wait()))
        self.assertTrue(job.wait(60))
        batch = self.flow.finish_pdf_extraction(job)
        self.assertEqual(self.flow.pdf_pages(batch)[0]['status'], 'pending')
        self.assertTrue(self.flow.confirmation_blockers(batch))

    def test_high_confidence_bad_region_still_needs_check_in_chinese_context(self):
        from unittest.mock import MagicMock
        job = self.flow.start_pdf_extraction(self.preview,1,1,mode='ocr',language='繁中＋英文')
        self.assertTrue(job.wait(40))
        batch = self.flow.finish_pdf_extraction(job)
        original = self.flow.pdf_pages(batch)[0]['text']
        start = original.index('FR Pu Al')
        process = MagicMock(returncode=0)
        process.poll.return_value = 0
        process.communicate.return_value = (b'level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n5\t1\t1\t1\t1\t1\t10\t10\t50\t20\t95\tFR\n5\t1\t1\t1\t1\t2\t60\t10\t50\t20\t95\tPu\n5\t1\t1\t1\t1\t3\t110\t10\t50\t20\t95\tAl\n', b'')
        with patch('subprocess.Popen', return_value=process):
            job = self.flow.start_pdf_retry(batch,pages=[1],language='繁中＋英文',layout='block',
                  region=(.53,.325,.8,.36),text_range=(start,start+8))
            self.assertTrue(job.wait(10))
        page = self.flow.pdf_extraction_pages(job)[0]
        self.assertEqual(page['status'], 'pending')
        self.assertTrue(page['settings']['suspicious_lines'])
        self.flow.discard_pdf_extraction(job)
