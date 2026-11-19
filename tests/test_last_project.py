"""Startup restores only the last successfully loaded book."""
import os
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow


class LastProjectJourney(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[1] / '.scratch' / 'test-runs'
        base.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(prefix='last-project-', dir=base)
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.home = self.directory / 'app-settings'
        env = patch.dict(os.environ, {'EBOOK2MP4_APP_HOME': str(self.home)})
        env.start()
        self.addCleanup(env.stop)

    def launch(self):
        root, app = make_app(restore_last_project=True)
        self.addCleanup(lambda: self.destroy(root))
        root.update()
        return root, app

    @staticmethod
    def destroy(root):
        try:
            root.destroy()
        except tk.TclError:
            pass

    def open_book(self, app, path):
        with patch('ebook2mp4.desktop.filedialog.askopenfilename', return_value=str(path)):
            app.open()

    def test_relaunch_loads_last_successfully_opened_book_and_saved_draft(self):
        flow = ProjectWorkflow.create(self.directory / '中文 書籍', '晨間隨筆')
        source = self.directory / 'source.txt'
        source.write_text('清晨出發。', encoding='utf-8')
        batch = flow.import_txt(flow.inspect_txt(source))
        flow.save_draft(batch, '已保存的校對內容。')
        root, app = self.launch()
        self.open_book(app, flow.root / 'project.json')
        self.destroy(root)
        _, reopened = self.launch()
        self.assertEqual(reopened.book.cget('text'), '晨間隨筆')
        self.assertEqual(reopened.current_text, '已保存的校對內容。')
        self.assertFalse(reopened.dirty)

    def test_cancelled_or_failed_open_keeps_last_successful_project(self):
        first = ProjectWorkflow.create(self.directory / 'first', '第一本')
        second = ProjectWorkflow.create(self.directory / 'second', '第二本')
        root, app = self.launch()
        self.open_book(app, first.root)
        self.open_book(app, second.root / 'project.json')
        self.open_book(app, '')
        with patch('ebook2mp4.desktop.messagebox.showerror'):
            self.open_book(app, self.directory / 'missing' / 'project.json')
        self.destroy(root)
        _, reopened = self.launch()
        self.assertEqual(reopened.book.cget('text'), '第二本')

    def test_missing_or_corrupt_book_leaves_usable_empty_workbench(self):
        flow = ProjectWorkflow.create(self.directory / 'book', 'Book')
        root, app = self.launch()
        self.open_book(app, flow.root)
        self.destroy(root)
        manifest = flow.root / 'project.json'
        manifest.rename(flow.root / 'backup.json')
        for data in (None, b'{}', b'not json'):
            if data is not None:
                manifest.write_bytes(data)
            root, reopened = self.launch()
            self.assertIsNone(reopened.flow)
            self.assertIn('無法自動載入', reopened.status.cget('text'))
            self.assertEqual(reopened.current_text, '')
            self.destroy(root)
        recovered = ProjectWorkflow.create(self.directory / 'recovered', '另一本書')
        root, app = self.launch()
        self.open_book(app, recovered.root)
        self.assertEqual(app.book.cget('text'), '另一本書')
        self.destroy(root)
        _, reopened = self.launch()
        self.assertEqual(reopened.book.cget('text'), '另一本書')

    def test_create_is_remembered_and_no_record_starts_empty(self):
        root, app = self.launch()
        self.assertIsNone(app.flow)
        app.new_name.set('新書')
        app.new_folder.set(str(self.directory / 'new-book'))
        app.create()
        self.destroy(root)
        _, reopened = self.launch()
        self.assertEqual(reopened.book.cget('text'), '新書')
        self.assertEqual(reopened.step, 1)

    def test_bad_session_record_does_not_block_manual_open(self):
        self.home.mkdir()
        (self.home / 'session.json').write_bytes(b'{broken')
        root, app = self.launch()
        self.assertIsNone(app.flow)
        self.assertIn('上次專案記錄', app.status.cget('text'))
        flow = ProjectWorkflow.create(self.directory / 'book', '可恢復')
        self.open_book(app, flow.root)
        self.destroy(root)
        _, reopened = self.launch()
        self.assertEqual(reopened.book.cget('text'), '可恢復')

    def test_unwritable_settings_does_not_fail_project_open(self):
        self.home.write_text('This path is a file.', encoding='utf-8')
        _, app = self.launch()
        flow = ProjectWorkflow.create(self.directory / 'book', '仍可工作')
        self.open_book(app, flow.root)
        self.assertEqual(app.book.cget('text'), '仍可工作')
        self.assertIn('無法記住專案位置', app.status.cget('text'))


if __name__ == '__main__':
    unittest.main()
