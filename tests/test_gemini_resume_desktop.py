"""Real Tk long-draft controls with a controlled external Gemini service."""
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow, ProjectError


class ResumeDesktop(unittest.TestCase):
    def setUp(self):
        base = Path('.scratch/test-runs')
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.root, self.app = make_app()
        self.addCleanup(self.root.destroy)
        folder = Path(self.temp.name)
        self.app.flow = ProjectWorkflow.create(folder / 'book', '長稿續作')
        source = folder / 'source.txt'
        source.write_bytes('\n\n'.join(c * 3500 + '。' for c in '甲乙丙').encode('utf-8'))
        self.app.batch_id = self.app.flow.import_txt(self.app.flow.inspect_txt(source))
        self.app.refresh()
        self.root.update()
        env = patch.dict('os.environ', GEMINI_API_KEY='fake')
        env.start()
        self.addCleanup(env.stop)

    def drain(self, dialog):
        deadline = time.monotonic() + 8
        while dialog.job is not None and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.02)
        self.assertIsNone(dialog.job)

    def test_partial_progress_ranges_adoption_and_retry_controls(self):
        with patch('ebook2mp4.gemini.generate', side_effect=[
                dict(paragraphs=['甲' * 3500 + '。'], notes=[]), ProjectError('合成失敗'),
                dict(paragraphs=['丙' * 3500 + '。'], notes=[])]), patch(
                    'ebook2mp4.desktop.messagebox.askyesno', return_value=True):
            self.app.gemini_review()
            dialog = self.app.gemini_dialog
            self.drain(dialog)
        dialog.geometry('740x570')
        self.root.update()
        self.assertIn('完成 2', dialog.progress.cget('text'))
        self.assertIn('失敗 1', dialog.progress.cget('text'))
        self.assertTrue(dialog.accept_button.instate(('!disabled',)))
        dialog.next_button.invoke()
        self.assertTrue(dialog.accept_button.instate(('disabled',)))
        self.assertIn('3504～7004', dialog.paragraph.get())
        self.assertIn('合成失敗', dialog.candidate.get('1.0', 'end-1c'))
        self.assertFalse(dialog.original.tag_ranges('diff'))
        first_id = dialog.review['id']
        # A newer review must not steal selection when this older review resumes.
        with patch('ebook2mp4.gemini.generate', return_value=dict(paragraphs=['甲'], notes=[])):
            newer = self.app.flow.start_gemini_review(self.app.batch_id, start=0, end=1)
            self.assertTrue(newer.wait(4))
            self.app.flow.finish_gemini_review(newer)
        for button in (dialog.retry_button, dialog.resume_button, dialog.cancel_button, dialog.close_button):
            self.assertTrue(button.winfo_ismapped())
            self.assertLessEqual(button.winfo_rootx() + button.winfo_width(), dialog.winfo_rootx() + dialog.winfo_width())
            self.assertLessEqual(button.winfo_rooty() + button.winfo_height(), dialog.winfo_rooty() + dialog.winfo_height())
        with patch('ebook2mp4.gemini.generate', return_value=dict(paragraphs=['乙' * 3500 + '。'], notes=[])) as service:
            dialog.retry_button.invoke()
            self.drain(dialog)
            self.assertEqual(service.call_count, 1)
        self.assertEqual(dialog.review['status'], 'completed')
        self.assertEqual(dialog.review['id'], first_id)
        self.assertEqual(dialog.paragraph.current(), 1)
        self.assertTrue(dialog.retry_button.instate(('disabled',)))
        dialog.close()

    def test_cancel_keeps_window_responsive_and_preserves_completed_range(self):
        entered, release = threading.Event(), threading.Event()
        def service(key, model, paragraphs):
            if paragraphs[0].startswith('乙'):
                entered.set()
                release.wait(5)
            return dict(paragraphs=paragraphs, notes=[])
        with patch('ebook2mp4.gemini.generate', side_effect=service), patch(
                'ebook2mp4.desktop.messagebox.askyesno', return_value=True):
            self.app.gemini_review()
            dialog = self.app.gemini_dialog
            try:
                self.assertTrue(entered.wait(4))
                self.root.update()
                self.assertIn('完成 1', dialog.progress.cget('text'))
                heartbeat = []
                self.root.after(0, lambda: heartbeat.append(True))
                dialog.cancel_button.invoke()
                self.root.update()
                self.assertEqual(heartbeat, [True])
            finally:
                release.set()
                self.drain(dialog)
        self.assertTrue(dialog.winfo_exists())
        self.assertEqual(dialog.review['status'], 'cancelled', dialog.review['error'])
        self.assertTrue(dialog.resume_button.instate(('!disabled',)))
        dialog.close()
