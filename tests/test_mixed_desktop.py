"""Real Tk T06 flow: compare, rotate/retry, explicit acceptance, anomalies."""
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow
from test_mixed_pdf import mixed_pdf


@unittest.skipUnless(os.environ.get('EBOOK2MP4_REAL_OCR_HOME'), 'requires real OCR models and engine')
class MixedDesktopJourney(unittest.TestCase):
    def until(self, predicate):
        deadline = time.monotonic() + 40
        while not predicate() and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.01)
        self.assertTrue(predicate())

    def test_retry_compare_reject_and_preserve_unsaved_editor(self):
        with tempfile.TemporaryDirectory(dir='.scratch/test-runs') as directory, patch.dict(
                os.environ, EBOOK2MP4_OCR_HOME=os.environ['EBOOK2MP4_REAL_OCR_HOME']):
            path = Path(directory).resolve()
            self.root, app = make_app()
            try:
                app.flow = ProjectWorkflow.create(path / 'book', 'Mixed book')
                pdf = path / 'mixed.pdf'
                pdf.write_bytes(mixed_pdf())
                job = app.flow.start_pdf_extraction(app.flow.inspect_pdf(pdf), 1, 4, mode='auto', language='英文')
                self.assertTrue(job.wait(40))
                original = app.flow.finish_pdf_extraction(job)
                app.batch_id = original
                app.refresh()
                app.editor.insert('end', '\nUnsaved corrected body.')
                self.root.update()
                unsaved = app.current_text
                app.pages_button.invoke()
                dialog = app.pdf_dialog
                self.until(lambda: dialog.ready)
                dialog.language.set('英文')
                dialog.page.set('3')
                dialog.rotation.set('90')
                dialog.view()
                self.until(lambda: dialog.ready)
                dialog.retry_page_button.invoke()
                self.until(lambda: dialog.pending_job is not None and dialog.ready)
                self.assertEqual(app.current_text, unsaved)
                self.assertIn('3', dialog.previous_text.get('1.0', 'end-1c'))
                self.assertIn('Unsaved corrected body.', dialog.draft_text.get('1.0', 'end-1c'))
                dialog.adopt_page.set(False)
                dialog.choose_page()
                with patch('ebook2mp4.desktop.messagebox.askyesnocancel', return_value=None):
                    dialog.accept_button.invoke()
                self.assertEqual(app.current_text, unsaved)
                self.assertIsNotNone(dialog.pending_job)
                with patch('ebook2mp4.desktop.messagebox.askyesnocancel', return_value=True):
                    dialog.accept_button.invoke()
                self.until(lambda: app.batch_id != original)
                self.assertEqual(app.flow.pdf_pages(app.batch_id)[2]['text'], '3')
                self.assertEqual(app.flow.texts(original)[1], unsaved)
                app.pages_button.invoke()
                dialog = app.pdf_dialog
                self.until(lambda: dialog.ready)
                dialog.page.set('3')
                dialog.view()
                self.until(lambda: dialog.ready)
                dialog.retain_button.invoke()
                self.until(lambda: dialog.ready)
                dialog.page.set('4')
                dialog.view()
                self.until(lambda: dialog.ready)
                with patch('tkinter.messagebox.askyesno', return_value=True):
                    dialog.skip_button.invoke()
                self.until(lambda: dialog.ready)
                self.assertFalse(app.flow.confirmation_blockers(app.batch_id))
                app.flow.confirm_reading(app.batch_id)
                dialog.close()
                self.until(lambda: app.pdf_dialog is None)
                # Changing range/mode/language creates another candidate from the saved PDF.
                pdf.unlink()
                app.pages_button.invoke()
                dialog = app.pdf_dialog
                self.until(lambda: dialog.ready)
                before = app.flow.state
                dialog.settings_button.invoke()
                dialog.start.set('1')
                dialog.end.set('2')
                dialog.mode.set('文字層')
                dialog.language.set('簡中＋英文')
                dialog.extract_button.invoke()
                self.until(lambda: dialog.pending_job is not None and dialog.ready)
                self.assertEqual(app.flow.state, before)
                self.assertEqual([p['number'] for p in dialog.candidate_pages], [1, 2])
                self.assertEqual(dialog.candidate_pages[1]['status'], 'pending')
                dialog.close()
                self.until(lambda: app.pdf_dialog is None)
                self.assertEqual(ProjectWorkflow.open(app.flow.root).state, before)
            finally:
                self.root.destroy()
