"""Real Tk Gemini actions with controlled external service and native prompts."""
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow


class GeminiDesktop(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[1] / '.scratch' / 'test-runs'
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        source = self.path / 'source.txt'
        source.write_bytes('前文。\n\n錯宇。\n\n後文。'.encode('utf-8'))
        self.root, self.app = make_app()
        self.addCleanup(self.root.destroy)
        self.app.flow = ProjectWorkflow.create(self.path / 'book', 'Gemini 校對')
        self.app.batch_id = self.app.flow.import_txt(self.app.flow.inspect_txt(source))
        self.app.refresh()
        self.root.update()

    def test_selected_text_preview_adopt_and_undo(self):
        self.app.editor.tag_add('sel', '3.0', '3.end')
        with patch('ebook2mp4.gemini.generate', return_value=dict(paragraphs=['錯字。'], notes=['保留疑點'])), patch.dict(
                'os.environ', GEMINI_API_KEY='fake'), patch('ebook2mp4.desktop.messagebox.askyesno', return_value=True):
            self.app.gemini_review(selected=True)
            dialog = self.app.gemini_dialog
            deadline = time.monotonic() + 4
            while dialog.job is not None and time.monotonic() < deadline:
                self.root.update()
                time.sleep(.02)
            self.assertIsNone(dialog.job)
            self.assertEqual(dialog.original.get('1.0', 'end-1c'), '錯宇。')
            self.assertEqual(dialog.candidate.get('1.0', 'end-1c'), '錯字。')
            dialog.accept_button.invoke()
            self.assertEqual(self.app.current_text, '前文。\n\n錯字。\n\n後文。')
            dialog.undo_button.invoke()
            self.assertEqual(self.app.current_text, '前文。\n\n錯宇。\n\n後文。')
            dialog.close()
            self.assertIsNone(self.app.gemini_dialog)

    def test_finished_candidate_can_be_discarded_when_another_window_changed_project(self):
        with patch('ebook2mp4.gemini.generate', return_value=dict(paragraphs=['前文。', '錯字。', '後文。'], notes=[])), patch.dict(
                'os.environ', GEMINI_API_KEY='fake'), patch('ebook2mp4.desktop.messagebox.askyesno', return_value=True):
            self.app.gemini_review()
            dialog = self.app.gemini_dialog
            self.assertTrue(dialog.job.wait(3))
            other = ProjectWorkflow.open(self.app.flow.root)
            other.rename_batch(self.app.batch_id, '另一視窗已變更')
            dialog.poll()
            self.assertIsNotNone(dialog.job)
            with patch('ebook2mp4.gemini_desktop.messagebox.askyesno', return_value=True):
                dialog.close()
            self.assertIsNone(self.app.gemini_dialog)
            self.assertEqual(other.texts(self.app.batch_id)[1], self.app.current_text)

    def test_deciding_older_candidate_keeps_same_candidate_selected(self):
        with patch('ebook2mp4.gemini.generate', return_value=dict(paragraphs=['A 前文。', 'A 錯字。', 'A 後文。'], notes=[])), patch.dict('os.environ', GEMINI_API_KEY='fake'):
            job = self.app.flow.start_gemini_review(self.app.batch_id)
            self.assertTrue(job.wait(3))
            first = self.app.flow.finish_gemini_review(job)
            job = self.app.flow.start_gemini_review(self.app.batch_id, start=5, end=8)
            self.assertTrue(job.wait(3))
            self.app.flow.finish_gemini_review(job)
        self.app.gemini_history()
        dialog = self.app.gemini_dialog
        dialog.selector.current(0)
        dialog.load()
        dialog.paragraph.current(2)
        dialog.show_paragraph()
        dialog.reject_button.invoke()
        self.assertEqual(dialog.review['id'], first)
        self.assertEqual(dialog.paragraph.current(), 2)
        self.assertEqual(dialog.candidate.get('1.0', 'end-1c'), 'A 後文。')
        dialog.close()

    def test_malformed_local_settings_can_be_replaced_in_settings_dialog(self):
        with patch.dict('os.environ', LOCALAPPDATA=str(self.path), GEMINI_API_KEY=''):
            settings = self.path / 'ebook2mp4/gemini.json'
            settings.parent.mkdir()
            settings.write_text('[]', encoding='utf-8')
            self.app.gemini_settings()
            dialog = self.app.gemini_settings_dialog
            self.assertIn('無法讀取', dialog.status.cget('text'))
            dialog.key.set('replacement-key')
            self.assertTrue(dialog.save())
            self.assertEqual(self.app.flow.gemini_settings()['key'], 'replacement-key')
            dialog.close()
