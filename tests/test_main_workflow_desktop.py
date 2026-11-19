"""Two-step navigation and atomic publication through the native main window."""
import unittest
from unittest.mock import patch
import test_ui_layout as layout
from ebook2mp4.workflow import ProjectWorkflow

class MainWorkflow(unittest.TestCase):
    setUp = layout.WorkbenchLayout.setUp

    def test_save_stays_in_manuscript_then_continue_and_return_keeps_editor(self):
        original = str(self.app.editor)
        self.app.editor.insert('end', '人工新增。')
        self.root.update()
        self.app.next_button.invoke()
        self.assertEqual(self.app.step, 1)
        self.assertTrue(self.app.reading_ready())
        self.app.next_button.invoke()
        self.assertEqual(self.app.step, 4)
        self.app.steps[0].invoke()
        self.assertEqual(self.app.step, 1)
        self.assertEqual(str(self.app.editor), original)
        opened = ProjectWorkflow.open(self.app.flow.root)
        self.assertEqual(opened.reading_text(self.app.batch_id), self.app.current_text)

    def test_failed_save_does_not_advance_or_lose_text(self):
        self.app.editor.insert('end', '保存失敗時保留')
        self.root.update()
        expected = self.app.current_text
        with patch('ebook2mp4.workflow.os.replace', side_effect=PermissionError()):
            self.app.next_button.invoke()
        self.assertEqual(self.app.step, 1)
        self.assertEqual(self.app.current_text, expected)
        self.assertFalse(self.app.reading_ready())
