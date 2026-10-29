"""Native status-cell hover help and its lifecycle; no OCR/cloud dependencies."""
from pathlib import Path
import tempfile
import time
import unittest

from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow


class StatusHelp(unittest.TestCase):
    def setUp(self):
        base = Path('.scratch/test-runs')
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        folder = Path(self.temp.name)
        self.root, self.app = make_app()
        self.addCleanup(self.root.destroy)
        self.errors = []
        self.root.report_callback_exception = lambda *error: self.errors.append(error)
        self.app.flow = ProjectWorkflow.create(folder / 'project', 'Hover help')
        source = folder / 'source.txt'
        source.write_text('來源文字。', encoding='utf-8')
        self.ids = [self.app.flow.import_txt(self.app.flow.inspect_txt(source)) for _ in range(3)]
        self.app.flow.record_source_issues(self.ids[1], ['檢查來源一', '檢查來源二'])
        self.app.flow.confirm_reading(self.ids[2])
        self.app.batch_id = self.ids[0]
        self.app.refresh()
        self.root.geometry('1040x640+20+20')
        self.root.update()
        self.help = self.app.batch_tooltip
        self.help.delay = 5

    def hover(self, row, column='status'):
        x, y, width, height = self.app.batch_list.bbox(row, column)
        self.app.batch_list.event_generate('<Motion>', x=x+width//2, y=y+height//2)
        deadline = time.monotonic()+1
        while self.help.timer is not None and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.01)
        self.root.update()

    def message(self):
        self.assertIsNotNone(self.help.window)
        return self.help.window.winfo_children()[0].cget('text')

    def test_help_matches_hovered_row_without_changing_selection_or_focus(self):
        selection = self.app.batch_list.selection()
        self.app.editor.focus_force()
        self.root.update()
        self.hover(self.ids[0])
        self.assertEqual(self.message(), '確認朗讀稿')
        self.hover(self.ids[1])
        self.assertEqual(self.message(), '有 2 項來源／OCR 異常尚未處理')
        self.assertEqual(self.app.batch_list.selection(), selection)
        self.assertIs(self.root.focus_get(), self.app.editor)
        self.assertFalse(self.errors)

    def test_help_is_only_for_status_and_uses_current_unresolved_count(self):
        self.hover(self.ids[1])
        self.assertIn('2 項', self.message())
        self.app.flow.resolve_source_issue(self.ids[1], 0, 'resolved')
        self.app.update_stats()
        self.assertIsNone(self.help.window)
        self.hover(self.ids[1])
        self.assertEqual(self.message(), '有 1 項來源／OCR 異常尚未處理')
        self.hover(self.ids[1], '#0')
        self.assertIsNone(self.help.window)
        self.hover(self.ids[2])
        self.assertIsNone(self.help.window)

    def test_leave_scroll_and_destroy_release_popup_and_delayed_callback(self):
        self.help.delay = 100
        x, y, width, height = self.app.batch_list.bbox(self.ids[0], 'status')
        self.app.batch_list.event_generate('<Motion>', x=x+width//2, y=y+height//2)
        self.assertIsNotNone(self.help.timer)
        self.app.batch_list.event_generate('<Leave>')
        self.assertIsNone(self.help.timer)
        self.help.delay = 5
        self.hover(self.ids[0])
        self.app.batch_list.event_generate('<MouseWheel>', delta=-120)
        self.assertIsNone(self.help.window)
        self.hover(self.ids[0])
        self.app.batch_list.destroy()
        self.root.update()
        self.assertIsNone(self.help.window)
        self.assertIsNone(self.help.timer)
        self.assertFalse(self.errors)
