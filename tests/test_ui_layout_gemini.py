"""Native candidate navigation and persistent safety status; no network requests."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow


class GeminiLayout(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[1] / '.scratch' / 'test-runs'
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.root, self.app = make_app()
        self.addCleanup(self.root.destroy)
        self.app.flow = ProjectWorkflow.create(self.path / 'book', '候選配置')
        source = self.path / 'source.txt'
        source.write_bytes('前文。\n\n錯宇。\n\n後文。'.encode('utf-8'))
        self.app.batch_id = self.app.flow.import_txt(self.app.flow.inspect_txt(source))
        self.app.refresh()
        with patch.dict('os.environ', GEMINI_API_KEY='fake'), patch(
                'ebook2mp4.gemini.generate', return_value=dict(
                    paragraphs=['前文。', '錯字。', '後文。'], notes=['請人工確認書中專名。'])):
            job = self.app.flow.start_gemini_review(self.app.batch_id)
            self.assertTrue(job.wait(3))
            self.app.flow.finish_gemini_review(job)
        self.editor_binding_before = self.app.editor.bind('<<Modified>>').strip()
        self.app.gemini_history()
        self.dialog = self.app.gemini_dialog
        self.dialog.geometry('740x570')
        self.root.update()
        self.addCleanup(self.close_dialog)

    def close_dialog(self):
        if self.app.gemini_dialog is not None:
            self.app.gemini_dialog.close()

    def test_navigation_decisions_and_batch_menu_preserve_candidate_scope(self):
        dialog = self.dialog
        dialog.next_button.invoke()
        self.assertEqual(dialog.paragraph.current(), 1)
        dialog.reject_button.invoke()
        self.assertIn('已拒絕 1', dialog.counts.cget('text'))
        dialog.pending_button.invoke()
        self.assertEqual(dialog.paragraph.current(), 2)
        dialog.previous_button.invoke()
        self.assertEqual(dialog.paragraph.current(), 1)
        dialog.batch_menu.invoke(0)
        self.assertIn('待確認 0', dialog.counts.cget('text'))
        self.assertIn('已採用 2', dialog.counts.cget('text'))
        self.assertEqual(self.app.current_text, '前文。\n\n錯宇。\n\n後文。')
        dialog.undo_button.invoke()
        self.assertIn('待確認 3', dialog.counts.cget('text'))
        self.assertEqual(dialog.paragraph.current(), 1)

    def test_edit_candidate_navigate_save_reopen_adopt_and_undo(self):
        dialog = self.dialog
        original = self.app.current_text
        self.assertEqual(str(dialog.original.cget('state')), 'disabled')
        self.assertEqual(str(dialog.candidate.cget('state')), 'normal')
        dialog.candidate.delete('1.0', 'end')
        dialog.candidate.insert('1.0', '人工修改第一段。')
        # Navigation must capture even before Tk delivers <<Modified>>.
        dialog.next_button.invoke()
        dialog.candidate.delete('1.0', 'end')
        dialog.candidate.insert('1.0', '人工修改第二段。\n加一行。')
        self.root.update()
        self.assertTrue(dialog.candidate.tag_ranges('diff'))
        dialog.previous_button.invoke()
        self.assertEqual(dialog.candidate.get('1.0', 'end-1c'), '人工修改第一段。')
        dialog.close()
        self.assertIsNone(self.app.gemini_dialog)
        reopened = ProjectWorkflow.open(self.app.flow.root)
        parts = reopened.gemini_reviews(self.app.batch_id)[0]['paragraphs']
        self.assertEqual(parts[0]['candidate'], '人工修改第一段。')
        self.assertEqual(parts[0]['ai_candidate'], '前文。')
        self.assertEqual(parts[1]['candidate'], '人工修改第二段。\n加一行。')
        self.assertEqual(reopened.texts(self.app.batch_id)[1], original)
        self.app.gemini_history()
        self.dialog = dialog = self.app.gemini_dialog
        dialog.all_button.invoke()
        self.assertEqual(self.app.current_text, '人工修改第一段。\n\n人工修改第二段。\n加一行。\n\n後文。')
        self.assertEqual(str(dialog.candidate.cget('state')), 'normal')
        dialog.undo_button.invoke()
        self.assertEqual(self.app.current_text, original)
        self.assertEqual(str(dialog.candidate.cget('state')), 'normal')

    def test_accepted_paragraph_can_be_edited_and_adopted_again(self):
        dialog = self.dialog
        dialog.candidate.insert('end', '第一次修正。')
        dialog.accept_button.invoke()
        self.root.update()
        self.assertIn('已儲存並採用本段', dialog.status.cget('text'))
        self.assertTrue(dialog.status.winfo_ismapped())
        self.assertEqual(str(dialog.candidate.cget('state')), 'normal')
        first = self.app.current_text
        dialog.candidate.insert('end', '第二次修正。')
        self.root.update()
        dialog.save_candidate_button.invoke()
        self.assertEqual(self.app.current_text, first)
        self.assertEqual(dialog.review['paragraphs'][0]['decision'], 'pending')
        dialog.close()
        saved = ProjectWorkflow.open(self.app.flow.root)
        self.assertEqual(saved.texts(self.app.batch_id)[1], first)
        self.assertEqual(saved.gemini_reviews(self.app.batch_id)[0]['paragraphs'][0]['decision'], 'pending')
        self.app.gemini_history()
        self.dialog = dialog = self.app.gemini_dialog
        dialog.next_button.invoke()
        dialog.accept_button.invoke()
        self.assertEqual(self.app.current_text, first.replace('錯宇', '錯字'))
        dialog.previous_button.invoke()
        dialog.accept_button.invoke()
        self.root.update()
        self.assertIn('已儲存並採用本段', dialog.status.cget('text'))
        self.assertIn('第一次修正。第二次修正。', self.app.current_text)
        expected = self.app.current_text
        dialog.close()
        reopened = ProjectWorkflow.open(self.app.flow.root)
        self.assertEqual(reopened.texts(self.app.batch_id)[1], expected)
        self.app.gemini_history()
        self.dialog = dialog = self.app.gemini_dialog
        self.assertEqual(str(dialog.candidate.cget('state')), 'normal')
        dialog.undo_button.invoke()
        self.assertEqual(self.app.current_text, '前文。\n\n錯宇。\n\n後文。')

    def test_adoption_has_one_notification_and_editing_does_not_emit_toasts(self):
        dialog = self.dialog
        with patch.object(self.app, 'notify', wraps=self.app.notify) as emit:
            dialog.candidate.insert('end', '人工修正。')
            self.root.update()
            emit.assert_not_called()
            dialog.accept_button.invoke()
            self.root.update()
            self.assertEqual(emit.call_count, 1)
            self.assertIn('採用第 1 段', emit.call_args.args[0])
            layer = dialog._notification_layer
            self.assertIsNotNone(layer.window)
            self.assertIn('採用第 1 段', layer.message.cget('text'))

    def test_empty_candidate_or_save_failure_keeps_edits_and_window(self):
        dialog = self.dialog
        dialog.candidate.delete('1.0', 'end')
        dialog.next_button.invoke()
        dialog.previous_button.invoke()
        self.assertEqual(dialog.candidate.get('1.0', 'end-1c'), '')
        with patch('ebook2mp4.gemini_desktop.messagebox.askyesno', return_value=False):
            dialog.close()
        self.assertIs(self.app.gemini_dialog, dialog)
        self.assertIn('不可空白', dialog.status.cget('text'))
        dialog.candidate.insert('1.0', '人工候選。')
        from ebook2mp4.workflow import ProjectError
        with patch.object(self.app.flow, '_commit', side_effect=ProjectError('磁碟無法保存')), patch(
                'ebook2mp4.gemini_desktop.messagebox.askyesno', return_value=False):
            dialog.accept_button.invoke()
            dialog.close()
        self.assertIs(self.app.gemini_dialog, dialog)
        self.assertEqual(dialog.candidate.get('1.0', 'end-1c'), '人工候選。')
        self.assertEqual(self.app.current_text, '前文。\n\n錯宇。\n\n後文。')
        self.assertTrue(dialog.save_candidate_edits())

    def test_dirty_and_stale_warnings_survive_success_messages(self):
        dialog = self.dialog
        self.app.editor.insert('end', '未存編輯')
        self.root.update()
        dialog.status.configure(text='已完成其他操作。')
        self.assertIn('未存編輯', dialog.blocking.cget('text'))
        self.assertTrue(dialog.accept_button.instate(('disabled',)))
        self.assertTrue(self.app.save())
        dialog.update_availability()
        dialog.status.configure(text='已儲存。')
        self.assertIn('原稿版本已變更', dialog.blocking.cget('text'))
        before = self.app.current_text
        dialog.all_button.invoke()
        self.assertEqual(self.app.current_text, before)

    def test_notes_and_primary_actions_remain_available_at_restored_size(self):
        dialog = self.dialog
        self.assertIn('請人工確認', dialog.notes_summary.cget('text'))
        self.assertFalse(dialog.notes_frame.winfo_ismapped())
        dialog.details_button.invoke()
        self.root.update()
        self.assertTrue(dialog.notes_frame.winfo_ismapped())
        self.assertIn('專名', dialog.notes.get('1.0', 'end-1c'))
        dialog.details_button.invoke()
        self.root.update()
        for button in (dialog.accept_button, dialog.reject_button, dialog.close_button,
                       dialog.batch_button, dialog.pending_button, dialog.save_candidate_button):
            self.assertTrue(button.winfo_ismapped())
            self.assertGreaterEqual(button.winfo_rootx(), dialog.winfo_rootx())
            self.assertLessEqual(button.winfo_rootx() + button.winfo_width(),
                                 dialog.winfo_rootx() + dialog.winfo_width())
            self.assertLessEqual(button.winfo_rooty() + button.winfo_height(),
                                 dialog.winfo_rooty() + dialog.winfo_height())
        self.assertTrue(dialog.bind('<Escape>'))
        dialog.close()
        self.assertIsNone(self.app.gemini_dialog)
        self.assertEqual(self.app.editor.bind('<<Modified>>').strip(), self.editor_binding_before)
