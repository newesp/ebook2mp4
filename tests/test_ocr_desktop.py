"""Real Tk OCR selection, download failure, candidate acceptance and page comparison."""
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from io import BytesIO

from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow
from test_ocr import scanned_pdf


@unittest.skipUnless(os.environ.get('EBOOK2MP4_REAL_OCR_HOME'), 'requires real downloaded models and engine')
class OcrDesktopJourney(unittest.TestCase):
    def until(self, predicate):
        deadline = time.monotonic() + 40
        while not predicate() and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.01)
        self.assertTrue(predicate())

    def test_model_failure_retry_and_explicit_candidate_acceptance(self):
        with tempfile.TemporaryDirectory(dir='.scratch/test-runs') as directory:
            path = Path(directory).resolve()
            self.root, app = make_app()
            try:
                app.flow = ProjectWorkflow.create(path / 'book', 'OCR book')
                app.refresh()
                pdf = path / 'scan.pdf'
                pdf.write_bytes(scanned_pdf(['English reading test.']))
                with patch.dict(os.environ, EBOOK2MP4_OCR_HOME=str(path / 'models')):
                    with patch('ebook2mp4.desktop.filedialog.askopenfilename', return_value=str(pdf)):
                        app.import_pdf()
                    dialog = app.pdf_dialog
                    self.until(lambda: dialog.ready)
                    self.assertIn('6,479,730', dialog.model_info.cget('text'))
                    dialog.language.set('簡中＋英文')
                    dialog.ocr_changed()
                    dialog.language.set('英文')
                    dialog.ocr_changed()
                    self.until(lambda: dialog.ready)
                    self.assertIn('eng ·', dialog.model_info.cget('text'))
                    self.assertNotIn('chi_sim', dialog.model_info.cget('text'))
                    dialog.mode.set('全部強制 OCR')
                    dialog.language.set('英文')
                    dialog.ocr_changed()
                    self.until(lambda: dialog.ready)
                    self.assertIn('4,113,088', dialog.model_info.cget('text'))
                    with patch('urllib.request.urlopen', return_value=BytesIO(b'bad download')):
                        dialog.install_button.invoke()
                        self.until(lambda: dialog.model_job is None)
                    self.assertIn('重試', dialog.model_info.cget('text'))
                with patch.dict(os.environ, EBOOK2MP4_OCR_HOME=os.environ['EBOOK2MP4_REAL_OCR_HOME']):
                    dialog.ocr_changed()
                    self.until(lambda: dialog.ready)
                    dialog.extract_button.invoke()
                    self.until(lambda: dialog.pending_job is not None)
                    self.assertEqual(app.flow.state['batches'], [], 'OCR requires explicit candidate acceptance')
                    self.until(lambda: dialog.ready)
                    self.assertIn('English reading test.', dialog.text.get('1.0', 'end-1c'))
                    dialog.accept_button.invoke()
                    self.until(lambda: app.batch_id is not None)
                    self.assertIn('English reading test.', app.current_text)
                    app.pages_button.invoke()
                    dialog = app.pdf_dialog
                    self.until(lambda: dialog.ready)
                    self.assertIn('OCR', dialog.page_info.cget('text'))
                    self.assertTrue(dialog.canvas.find_all())
            finally:
                self.root.destroy()
