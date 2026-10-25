"""OCR journeys at ProjectWorkflow; real engine cases are explicitly opt-in."""
from io import BytesIO
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from ebook2mp4.workflow import ProjectWorkflow, ProjectError


def scanned_pdf(texts):
    """Raster-only pages, so there is no hidden text layer to pass OCR tests."""
    from PIL import Image, ImageDraw, ImageFont
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    output = BytesIO()
    doc = canvas.Canvas(output, pagesize=(600, 240))
    font = ImageFont.truetype('C:/Windows/Fonts/msjh.ttc', 48)
    for text in texts:
        with Image.new('RGB', (1800, 720), 'white') as image:
            draw = ImageDraw.Draw(image)
            draw.text((100, 160), text, font=font, fill='black', spacing=24)
            doc.drawImage(ImageReader(image), 0, 0, width=600, height=240)
        doc.showPage()
    doc.save()
    return output.getvalue()


class OcrAvailability(unittest.TestCase):
    def setUp(self):
        base = Path('.scratch/test-runs')
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.env = patch.dict(os.environ, EBOOK2MP4_OCR_HOME=str(self.root / 'models'),
                              EBOOK2MP4_TESSERACT=str(self.root / 'missing.exe'))
        self.env.start()
        self.addCleanup(self.env.stop)
        self.flow = ProjectWorkflow.create(self.root / 'book', 'OCR book')

    def test_missing_ocr_lists_correct_languages_sizes_and_txt_still_works(self):
        for language, codes, size in [('繁中＋英文', 'chi_tra+eng', 6479730),
                                      ('簡中＋英文', 'chi_sim+eng', 6582244),
                                      ('英文', 'eng', 4113088)]:
            info = self.flow.ocr_models(language)
            self.assertEqual(info['codes'], codes)
            self.assertEqual(info['download_bytes'], size)
            self.assertFalse(info['ready'])
            self.assertIn('重新安裝', info['engine_error'])
        txt = self.root / 'source.txt'
        txt.write_text('人工校對仍可使用。', encoding='utf-8')
        batch = self.flow.import_txt(self.flow.inspect_txt(txt))
        self.flow.confirm_reading(batch)
        self.assertEqual(ProjectWorkflow.open(self.flow.root).reading_text(batch), '人工校對仍可使用。')

    def test_bad_download_is_not_installed_and_retry_is_possible(self):
        for data in (b'broken download', b''):
            with patch('urllib.request.urlopen', return_value=BytesIO(data)):
                job = self.flow.start_ocr_model_install('英文')
                self.assertTrue(job.wait(5))
            self.assertEqual(job.state['status'], 'failed')
            self.assertIn('重試', job.state['error'])
            self.assertFalse(self.flow.ocr_models('英文')['ready'])
            self.assertEqual(list((self.root / 'models').iterdir()), [])

    def test_missing_engine_blocks_only_forced_ocr_not_text_layer(self):
        from test_pdf import pdf_bytes
        pdf = self.root / 'book.pdf'
        pdf.write_bytes(pdf_bytes(1))
        preview = self.flow.inspect_pdf(pdf)
        with self.assertRaisesRegex(ProjectError, '重新安裝'):
            self.flow.start_pdf_extraction(preview, 1, 1, mode='ocr', language='英文')
        job = self.flow.start_pdf_extraction(preview, 1, 1)
        self.assertTrue(job.wait(10))
        self.assertIn('Chapter 1', self.flow.texts(self.flow.finish_pdf_extraction(job))[1])


@unittest.skipUnless(os.environ.get('EBOOK2MP4_REAL_OCR_HOME'), 'requires real downloaded models and engine')
class RealOcrJourney(unittest.TestCase):
    def setUp(self):
        base = Path('.scratch/test-runs')
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.env = patch.dict(os.environ, EBOOK2MP4_OCR_HOME=os.environ['EBOOK2MP4_REAL_OCR_HOME'])
        self.env.start()
        self.addCleanup(self.env.stop)
        self.flow = ProjectWorkflow.create(self.root / 'book', 'Scanned book')

    def test_verified_model_install_and_cancel_release_download_resources(self):
        model = (Path(os.environ['EBOOK2MP4_REAL_OCR_HOME']) / 'eng.traineddata').read_bytes()
        home = self.root / 'installed-models'
        with patch.dict(os.environ, EBOOK2MP4_OCR_HOME=str(home)):
            with patch('urllib.request.urlopen', return_value=BytesIO(model)):
                job = self.flow.start_ocr_model_install('英文')
                self.assertTrue(job.wait(10))
            self.assertEqual(job.state['status'], 'completed')
            self.assertEqual(job.state['downloaded'], 4113088)
            self.assertTrue(self.flow.ocr_models('英文')['ready'])
            self.assertEqual(sorted(p.name for p in home.iterdir()), ['eng.traineddata'])
            class SlowResponse(BytesIO):
                def read(self, size=-1):
                    time.sleep(.05)
                    return super().read(size)
            with patch('urllib.request.urlopen', return_value=SlowResponse(model)):
                job = self.flow.start_ocr_model_install('繁中＋英文')
                job.cancel()
                self.assertTrue(job.wait(10))
            self.assertEqual(job.state['status'], 'cancelled')
            self.assertTrue(self.flow.ocr_models('英文')['ready'])
            self.assertEqual(sorted(p.name for p in home.iterdir()), ['eng.traineddata'])

    def test_real_cancellation_keeps_complete_pages_and_failed_engine_is_not_success(self):
        pdf = self.root / 'scan.pdf'
        pdf.write_bytes(scanned_pdf(['English reading test.'] * 12))
        preview = self.flow.inspect_pdf(pdf)
        job = self.flow.start_pdf_extraction(preview, 1, 12, mode='ocr', language='英文')
        self.addCleanup(lambda: (job.cancel(), job.wait()))
        deadline = time.monotonic() + 20
        while not job.pages and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(job.pages)
        job.cancel()
        self.assertTrue(job.wait(10))
        batch = self.flow.finish_pdf_extraction(job)
        pages = self.flow.pdf_pages(batch)
        self.assertEqual(pages[0]['status'], 'success')
        self.assertEqual(pages[-1]['status'], 'cancelled')
        self.assertTrue(all(p['method'] == 'ocr' for p in pages))
        self.assertTrue(self.flow.confirmation_blockers(batch))
        with patch('subprocess.Popen', side_effect=OSError('cannot start')):
            job = self.flow.start_pdf_extraction(preview, 1, 1, mode='ocr', language='英文')
            self.assertTrue(job.wait(10))
        failed = self.flow.finish_pdf_extraction(job)
        self.assertEqual(self.flow.pdf_pages(failed)[0]['status'], 'failed')
        self.assertIn('重新安裝', self.flow.pdf_pages(failed)[0]['error'])
        self.assertTrue(self.flow.confirmation_blockers(failed))

    def test_three_real_scripts_blank_page_and_retry_preserve_corrected_snapshot(self):
        for language, text, expected, code in [
                ('繁中＋英文', '繁體中文閱讀測試\nEnglish reading 123.', '繁體中文', 'chi_tra+eng'),
                ('簡中＋英文', '简体中文阅读测试\nEnglish reading 123.', '简体中文', 'chi_sim+eng'),
                ('英文', 'English reading test.\nNumbers 123 and punctuation!', 'English reading test.', 'eng')]:
            with self.subTest(language=language):
                pdf = self.root / 'scan.pdf'
                pdf.write_bytes(scanned_pdf([text, '']))
                preview = self.flow.inspect_pdf(pdf)
                job = self.flow.start_pdf_extraction(preview, 1, 2, mode='ocr', language=language)
                self.addCleanup(lambda: (job.cancel(), job.wait()))
                self.assertTrue(job.wait(60))
                batch = self.flow.finish_pdf_extraction(job)
                pages = self.flow.pdf_pages(batch)
                self.assertIn(expected, pages[0]['text'].replace(' ', '') if language != '英文' else pages[0]['text'])
                self.assertEqual([p['status'] for p in pages], ['success', 'pending'])
                self.assertEqual(pages[0]['method'], 'ocr')
                self.assertEqual(pages[0]['settings']['language'], code)
                self.assertEqual(len(self.flow.confirmation_blockers(batch)), 1)
                self.flow.resolve_source_issue(batch, 0, 'skipped')
                self.flow.save_draft(batch, '人工校對版本')
                snapshot = self.flow.confirm_reading(batch)
                retry = self.flow.start_pdf_extraction(preview, 1, 1, mode='ocr', language=language)
                self.assertTrue(retry.wait(60))
                second = self.flow.finish_pdf_extraction(retry)
                reopened = ProjectWorkflow.open(self.flow.root)
                self.assertNotEqual(batch, second)
                self.assertEqual(reopened.reading_text(batch, snapshot['id']), '人工校對版本')
                self.assertEqual(reopened.reading_text(batch), '人工校對版本')
                self.assertTrue(reopened.pdf_page_image(second, 1).startswith(b'\x89PNG'))


if __name__ == '__main__':
    unittest.main()
