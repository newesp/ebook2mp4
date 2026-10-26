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
