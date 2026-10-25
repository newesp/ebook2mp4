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
        self.assertIn('校對稿 v2', self.app.source_meta.cget('text'))
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

    def test_multiple_batches_encoding_recovery_switch_rename_reorder(self):
        self.create_import()
        first = self.app.batch_id
        self.app.editor.insert('end', '\n第一批的修改。')
        self.assertTrue(self.app.save())
        second_source = self.directory / '第二章 CP950.txt'
        second_source.write_bytes('第二章，碁。'.encode('cp950'))
        with patch('ebook2mp4.desktop.filedialog.askopenfilename', return_value=str(second_source)), \
             patch('ebook2mp4.desktop.messagebox.showerror'):
            self.app.import_txt()
        self.root.update()
        selector = next(w for w in descendants(self.root) if w.winfo_class() == 'TCombobox')
        confirm = next(w for w in descendants(self.root)
                       if w.winfo_class() == 'TButton' and w.cget('text') == '確認匯入')
        self.assertTrue(confirm.instate(['disabled']))
        self.assertEqual(len(self.app.flow.state['batches']), 1)
        selector.set('CP950')
        selector.event_generate('<<ComboboxSelected>>')
        self.root.update()
        self.assertFalse(confirm.instate(['disabled']))
        confirm.invoke()
        self.root.update()
        second = self.app.batch_id
        self.assertNotEqual(first, second)
        self.assertEqual(self.app.current_text, '第二章，碁。')
        with patch('ebook2mp4.desktop.simpledialog.askstring', return_value='第二章新名稱'):
            self.app.rename_button.invoke()
        self.assertIn('第二章新名稱 · 校對稿 v1', self.app.source_meta.cget('text'))
        self.app.up_button.invoke()
        self.assertEqual([b['id'] for b in self.app.flow.state['batches']], [second, first])
        self.app.batch_list.selection_set(first)
        self.app.batch_list.event_generate('<<TreeviewSelect>>')
        self.root.update()
        self.assertEqual(self.app.current_text, '第一章。\n\nHello!\n第一批的修改。')
        project = self.app.flow.root / 'project.json'
        with patch('ebook2mp4.desktop.filedialog.askopenfilename', return_value=str(project)):
            self.app.open()
        self.assertEqual(self.app.current_text, '第二章，碁。')
        self.assertEqual(self.app.flow.state['batches'][0]['name'], '第二章新名稱')

    def test_cancel_or_failed_save_during_batch_switch_keeps_unsaved_editor(self):
        self.create_import()
        first = self.app.batch_id
        self.source.write_bytes('另一批原文'.encode('utf-8'))
        second = self.app.flow.import_txt(self.app.flow.inspect_txt(self.source))
        self.app.refresh()
        self.app.editor.insert('end', '尚未儲存的修改')
        pending = self.app.current_text
        for answer in (None, True):
            with patch('ebook2mp4.desktop.messagebox.askyesnocancel', return_value=answer), \
                 patch('ebook2mp4.desktop.messagebox.showerror'), \
                 patch('ebook2mp4.workflow.os.replace', side_effect=PermissionError()):
                self.app.batch_list.selection_set(second)
                self.app.batch_list.event_generate('<<TreeviewSelect>>')
                self.root.update()
            self.assertEqual(self.app.batch_id, first)
            self.assertEqual(self.app.batch_list.selection(), (first,))
            self.assertEqual(self.app.current_text, pending)
        with patch('ebook2mp4.desktop.messagebox.askyesnocancel', return_value=True):
            self.app.batch_list.selection_set(second)
            self.app.batch_list.event_generate('<<TreeviewSelect>>')
            self.root.update()
        self.assertEqual(self.app.current_text, '另一批原文')
        self.assertEqual(self.app.flow.texts(first)[1], pending)


if __name__ == '__main__':
    unittest.main()
