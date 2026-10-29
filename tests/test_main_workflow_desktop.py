"""Main workflow tested through real Tk actions and persisted project text."""
from unittest.mock import patch

import unittest
import test_ui_layout as layout
from ebook2mp4.workflow import ProjectError, ProjectWorkflow


class MainWorkflow(unittest.TestCase):
    setUp = layout.WorkbenchLayout.setUp

    def test_ai_tools_exit_focus_mode_without_losing_selection(self):
        self.app.editor.tag_add('sel', '1.0', '1.3')
        self.app.toggle_focus()
        self.app.ai_tools_button.invoke()
        self.root.update()
        self.assertFalse(self.app.focus_mode)
        self.assertTrue(self.app.right_panel.winfo_ismapped())
        self.assertEqual(self.app.tool_tabs.index('current'), 1)
        self.assertEqual(self.app.editor.get('sel.first', 'sel.last'), '第一行')

    def test_save_next_edit_confirm_and_reconfirm(self):
        original = self.app.current_text
        self.app.editor.insert('end', '\n校對新增。')
        self.root.update()
        self.assertEqual(self.app.next_button.cget('text'), '儲存並前往確認朗讀稿 →')
        self.app.next_button.invoke()
        self.root.update()
        self.assertEqual(self.app.step, 3)
        self.assertFalse(self.app.dirty)
        self.assertEqual(str(self.app.editor.cget('state')), 'normal')
        self.app.editor.insert('end', '\n確認頁新增。')
        self.root.update()
        expected = original + '\n校對新增。\n確認頁新增。'
        with patch('ebook2mp4.desktop.messagebox.askyesno', return_value=True), \
                patch.object(self.app, 'voice_settings') as voice:
            self.app.confirm_button.invoke()
        voice.assert_called_once()
        reopened = ProjectWorkflow.open(self.app.flow.root)
        self.assertEqual(reopened.reading_text(self.app.batch_id), expected)
        self.app.editor.insert('end', '重新修改')
        self.root.update()
        with self.assertRaises(ProjectError):
            self.app.flow.reading_text(self.app.batch_id)
        self.app.show_step(2)
        self.app.show_step(3)
        self.assertEqual(self.app.current_text, expected + '重新修改')

    def test_failed_save_does_not_advance_or_lose_text(self):
        self.app.editor.insert('end', '磁碟失敗時保留')
        self.root.update()
        expected = self.app.current_text
        with patch('ebook2mp4.workflow.os.replace', side_effect=PermissionError()), \
                patch('ebook2mp4.desktop.messagebox.showerror'):
            self.app.next_button.invoke()
        self.assertEqual(self.app.step, 2)
        self.assertEqual(self.app.current_text, expected)
        self.assertTrue(self.app.dirty)


if __name__ == '__main__':
    import unittest
    unittest.main()
