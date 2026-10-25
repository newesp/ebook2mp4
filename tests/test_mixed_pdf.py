"""T06 journeys through the agreed ProjectWorkflow and real PDF/OCR boundary."""
from io import BytesIO
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from reportlab.pdfgen import canvas
from ebook2mp4.workflow import ProjectWorkflow, ProjectError


def mixed_pdf():
    from PIL import Image, ImageDraw, ImageFont
    from reportlab.lib.utils import ImageReader
    output = BytesIO()
    doc = canvas.Canvas(output, pagesize=(600, 240))
    doc.drawString(40, 180, 'A complete text layer paragraph for the first page.')
    doc.showPage()
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 48)
    with Image.new('RGB', (1800, 720), 'white') as image:
        ImageDraw.Draw(image).text((100, 160), 'Scanned body reading test.', font=font, fill='black')
        for number in (None, '3'):
            doc.drawImage(ImageReader(image), 0, 0, width=600, height=240)
            if number:
                doc.drawString(20, 10, number)
            doc.showPage()
    doc.showPage()
    doc.save()
    return output.getvalue()


class MixedPdfJourney(unittest.TestCase):
    def setUp(self):
        base = Path('.scratch/test-runs')
        base.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.pdf = self.root / 'mixed.pdf'
        self.pdf.write_bytes(mixed_pdf())
        self.flow = ProjectWorkflow.create(self.root / 'project', 'Mixed book')
        self.preview = self.flow.inspect_pdf(self.pdf)

    def finish(self, job):
        self.addCleanup(lambda: (job.cancel(), job.wait()))
        self.assertTrue(job.wait(40))
        return self.flow.finish_pdf_extraction(job)

    def test_auto_without_models_preserves_text_and_flags_unread_pages(self):
        with patch.dict(os.environ, EBOOK2MP4_TESSERACT=str(self.root / 'missing.exe'),
                        EBOOK2MP4_OCR_HOME=str(self.root / 'missing-models')):
            batch = self.finish(self.flow.start_pdf_extraction(self.preview, 1, 4, mode='auto', language='英文'))
        pages = self.flow.pdf_pages(batch)
        self.assertEqual([p['method'] for p in pages], ['text-layer', 'ocr', 'text-layer', 'ocr'])
        self.assertEqual([p['status'] for p in pages], ['success', 'failed', 'pending', 'failed'])
        self.assertEqual(pages[2]['text'], '3')
        self.assertEqual(len(self.flow.confirmation_blockers(batch)), 3)
        with self.assertRaises(ProjectError):
            self.flow.confirm_reading(batch)

    @unittest.skipUnless(os.environ.get('EBOOK2MP4_REAL_OCR_HOME'), 'requires real models and engine')
    def test_auto_retry_selected_candidate_preserves_corrected_original_and_confirmations(self):
        with patch.dict(os.environ, EBOOK2MP4_OCR_HOME=os.environ['EBOOK2MP4_REAL_OCR_HOME']):
            batch = self.finish(self.flow.start_pdf_extraction(self.preview, 1, 4, mode='auto', language='英文'))
            pages = self.flow.pdf_pages(batch)
            self.assertEqual([p['status'] for p in pages], ['success', 'success', 'pending', 'pending'])
            self.assertIn('Scanned body reading test.', pages[1]['text'])
            self.flow.save_draft(batch, 'My manually corrected book.')
            for index in (0, 1):
                self.flow.resolve_source_issue(batch, index, 'skipped')
            snapshot = self.flow.confirm_reading(batch)
            retry = self.flow.start_pdf_retry(batch, pages=[3, 4], language='英文', rotation=180)
            self.assertTrue(retry.wait(40))
            candidates = self.flow.pdf_extraction_pages(retry)
            self.assertEqual(candidates[0], pages[0])
            self.assertEqual(candidates[1], pages[1])
            self.assertEqual(candidates[2]['settings']['rotation'], 180)
            # Reject page 3; explicitly accept only the blank-page retry.
            second = self.flow.finish_pdf_extraction(retry, accepted_pages=[4])
            reopened = ProjectWorkflow.open(self.flow.root)
            self.assertEqual(reopened.pdf_pages(second)[2], pages[2])
            self.assertEqual(reopened.reading_text(batch, snapshot['id']), 'My manually corrected book.')
            self.assertEqual(reopened.reading_text(batch), 'My manually corrected book.')
            self.assertEqual(len(reopened.confirmation_blockers(second)), 1)
            with self.assertRaises(ProjectError):
                reopened.confirm_reading(second)
            reopened.resolve_source_issue(second, 1, 'skipped')
            reopened.confirm_reading(second)

    def test_failed_only_retry_retains_untargeted_progress_and_cancelled_target(self):
        with patch.dict(os.environ, EBOOK2MP4_TESSERACT=str(self.root / 'missing.exe'),
                        EBOOK2MP4_OCR_HOME=str(self.root / 'missing-models')):
            batch = self.finish(self.flow.start_pdf_extraction(self.preview, 1, 4, mode='auto', language='英文'))
        before = self.flow.pdf_pages(batch)
        # Retrying needs real OCR models; invalid/no matching selections must fail first.
        for selection in ([], [0], [1, 1], [True], [5]):
            with self.assertRaises(ProjectError):
                self.flow.start_pdf_retry(batch, pages=selection, language='英文')
        if not os.environ.get('EBOOK2MP4_REAL_OCR_HOME'):
            return
        with patch.dict(os.environ, EBOOK2MP4_OCR_HOME=os.environ['EBOOK2MP4_REAL_OCR_HOME']):
            job = self.flow.start_pdf_retry(batch, failed_only=True, language='英文')
            job.cancel()
            self.assertTrue(job.wait(40))
            candidate = self.flow.pdf_extraction_pages(job)
            self.assertEqual(candidate[0], before[0])
            self.assertEqual(candidate[2], before[2])
            self.assertEqual(job.numbers, (2, 4))
            self.assertEqual(candidate[-1]['status'], 'cancelled')
            with self.assertRaises(ProjectError):
                self.flow.finish_pdf_extraction(job, accepted_pages=[1])
            self.flow.discard_pdf_extraction(job)
        self.assertEqual(ProjectWorkflow.open(self.flow.root).pdf_pages(batch), before)

    @unittest.skipUnless(os.environ.get('EBOOK2MP4_REAL_OCR_HOME'), 'requires real models and engine')
    def test_failed_only_recovers_and_publication_failure_keeps_candidate(self):
        with patch.dict(os.environ, EBOOK2MP4_TESSERACT=str(self.root / 'missing.exe')):
            batch = self.finish(self.flow.start_pdf_extraction(self.preview, 1, 4, mode='auto', language='英文'))
        before = self.flow.pdf_pages(batch)
        with patch.dict(os.environ, EBOOK2MP4_OCR_HOME=os.environ['EBOOK2MP4_REAL_OCR_HOME']):
            job = self.flow.start_pdf_retry(batch, failed_only=True, language='英文')
            self.addCleanup(lambda: (job.cancel(), job.wait()))
            self.assertTrue(job.wait(40))
            candidate = self.flow.pdf_extraction_pages(job)
            self.assertEqual(candidate[0], before[0])
            self.assertEqual(candidate[2], before[2])
            self.assertIn('Scanned body reading test.', candidate[1]['text'])
            self.assertEqual(candidate[-1]['status'], 'pending')
            with patch('ebook2mp4.workflow.os.replace', side_effect=OSError('disk full')):
                with self.assertRaises(ProjectError):
                    self.flow.finish_pdf_extraction(job)
            self.assertEqual(ProjectWorkflow.open(self.flow.root).pdf_pages(batch), before)
            self.assertEqual(self.flow.pdf_extraction_pages(job), candidate)
            second = self.flow.finish_pdf_extraction(job)
        self.assertEqual(ProjectWorkflow.open(self.flow.root).pdf_pages(second), candidate)

    @unittest.skipUnless(os.environ.get('EBOOK2MP4_REAL_OCR_HOME'), 'requires real models and engine')
    def test_all_three_rotations_recover_sideways_or_upside_down_scans(self):
        from PIL import Image, ImageDraw, ImageFont
        from reportlab.lib.utils import ImageReader
        font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 48)
        with patch.dict(os.environ, EBOOK2MP4_OCR_HOME=os.environ['EBOOK2MP4_REAL_OCR_HOME']):
            for rotation in (90, 180, 270):
                output = BytesIO()
                with Image.new('RGB', (1800, 720), 'white') as image:
                    ImageDraw.Draw(image).text((100, 160), 'Rotated scan reading test.', font=font, fill='black')
                    # PIL rotates counterclockwise; PDFium correction is clockwise.
                    with image.rotate(rotation, expand=True) as sideways:
                        doc = canvas.Canvas(output, pagesize=(sideways.width / 3, sideways.height / 3))
                        doc.drawImage(ImageReader(sideways), 0, 0, width=sideways.width / 3, height=sideways.height / 3)
                        doc.showPage()
                        doc.save()
                self.pdf.write_bytes(output.getvalue())
                batch = self.finish(self.flow.start_pdf_extraction(self.flow.inspect_pdf(self.pdf), 1, 1))
                for invalid in (-90, 45, True, '90'):
                    with self.assertRaises(ProjectError):
                        self.flow.start_pdf_retry(batch, pages=[1], rotation=invalid, language='英文')
                retry = self.flow.start_pdf_retry(batch, pages=[1], rotation=rotation, language='英文')
                second = self.finish(retry)
                page = self.flow.pdf_pages(second)[0]
                self.assertIn('Rotated scan reading test.', page['text'], f'rotation {rotation}')
                self.assertEqual(page['settings']['rotation'], rotation)

    @unittest.skipUnless(os.environ.get('EBOOK2MP4_REAL_OCR_HOME'), 'requires real models and engine')
    def test_retry_raw_draft_reopens_resolutions_that_depended_on_manual_corrections(self):
        with patch.dict(os.environ, EBOOK2MP4_OCR_HOME=os.environ['EBOOK2MP4_REAL_OCR_HOME']):
            batch = self.finish(self.flow.start_pdf_extraction(self.preview, 1, 4, mode='auto', language='英文'))
            self.flow.save_draft(batch, 'Corrected manuscript including the previously missing body.')
            self.flow.resolve_source_issue(batch, 0, 'resolved')
            self.flow.resolve_source_issue(batch, 1, 'skipped')
            self.flow.confirm_reading(batch)
            second = self.finish(self.flow.start_pdf_retry(batch, pages=[1], language='英文'))
        self.assertEqual(len(self.flow.confirmation_blockers(second)), 1)
        with self.assertRaises(ProjectError):
            self.flow.confirm_reading(second)
        self.assertEqual(self.flow.reading_text(batch), 'Corrected manuscript including the previously missing body.')

    @unittest.skipUnless(os.environ.get('EBOOK2MP4_REAL_OCR_HOME'), 'requires real models and engine')
    def test_auto_and_retry_digit_only_ocr_require_explicit_page_confirmation(self):
        from test_ocr import scanned_pdf
        self.pdf.write_bytes(scanned_pdf(['3']))
        with patch.dict(os.environ, EBOOK2MP4_OCR_HOME=os.environ['EBOOK2MP4_REAL_OCR_HOME']):
            batch = self.finish(self.flow.start_pdf_extraction(self.flow.inspect_pdf(self.pdf), 1, 1,
                                                              mode='auto', language='英文'))
            page = self.flow.pdf_pages(batch)[0]
            self.assertEqual(page['text'].strip(), '3')
            self.assertEqual(page['status'], 'pending')
            with self.assertRaises(ProjectError):
                self.flow.confirm_reading(batch)
            second = self.finish(self.flow.start_pdf_retry(batch, pages=[1], language='英文'))
            self.assertTrue(self.flow.confirmation_blockers(second))


if __name__ == '__main__':
    unittest.main()
