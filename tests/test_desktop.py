"""Real Tk widgets and files; only native dialogs and storage faults are controlled."""
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from ebook2mp4.desktop import make_app


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


class DesktopJourney(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[1] / '.scratch' / 'test-runs'
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='UI T01 中文 ', dir=base)
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.source = self.directory / '第一章 原稿.txt'
        self.source.write_bytes(b'\xef\xbb\xbf' + '第一章。\n\nHello!'.encode('utf-8'))
        self.root, self.app = make_app()
        self.addCleanup(self.destroy)

    def destroy(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def create_import(self):
        with patch('ebook2mp4.desktop.simpledialog.askstring', side_effect=['測試書籍', '書籍 專案']), \
             patch('ebook2mp4.desktop.filedialog.askdirectory', return_value=str(self.directory)):
            self.app.create()
        with patch('ebook2mp4.desktop.filedialog.askopenfilename', return_value=str(self.source)):
            self.app.import_txt()
        self.root.update()
        self.assertFalse(self.app.flow.state['batches'], 'Preview must not import before confirmation')
        button = next(w for w in descendants(self.root)
                      if w.winfo_class() == 'TButton' and w.cget('text') == '確認匯入')
        button.invoke()
        self.root.update()

    def test_real_ui_create_preview_import_edit_save_close_reopen(self):
        original = self.source.read_bytes()
        self.create_import()
        self.assertEqual(self.app.source.get('1.0', 'end-1c'), '第一章。\n\nHello!')
        self.assertEqual(self.app.source.cget('state'), 'disabled')
        self.app.editor.insert('end', '\n校對完成。')
        self.root.update()
        self.assertTrue(self.app.dirty)
        for step in (3, 4, 1, 2):
            self.app.steps[step - 1].invoke()
            self.assertEqual(self.app.step, step)
            self.assertIn('校對完成', self.app.current_text)
        self.app.save_button.invoke()
        self.assertFalse(self.app.dirty)
        project = self.app.flow.root / 'project.json'
        self.app.close()
        self.root, self.app = make_app()
        with patch('ebook2mp4.desktop.filedialog.askopenfilename', return_value=str(project)):
            self.app.open()
        self.root.update()
        self.assertEqual(self.app.current_text, '第一章。\n\nHello!\n校對完成。')
        self.assertEqual(self.source.read_bytes(), original)
        self.assertIn('無 PDF 頁碼', self.app.source_meta.cget('text'))

    def test_ui_failure_retains_unsaved_text_and_cancel_close(self):
        self.create_import()
        self.app.editor.insert('end', '未存資料')
        self.root.update()
        with patch('ebook2mp4.workflow.os.replace', side_effect=PermissionError()), \
             patch('ebook2mp4.desktop.messagebox.showerror') as error:
            self.assertFalse(self.app.save())
            error.assert_called_once()
        self.assertTrue(self.app.dirty)
        self.assertIn('未存資料', self.app.current_text)
        with patch('ebook2mp4.desktop.messagebox.askyesnocancel', return_value=None):
            self.app.close()
        self.assertTrue(self.root.winfo_exists())
        self.assertTrue(self.app.save())


if __name__ == '__main__':
    unittest.main()
