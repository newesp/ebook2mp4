"""Real Tk widgets and files; only native dialogs and storage faults are controlled."""
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
import time
from unittest.mock import patch

from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectError, ProjectWorkflow


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

    def test_pdf_remove_cancel_failure_success_and_empty_state(self):
        from test_pdf import pdf_bytes
        self.assertEqual(self.app.pdf_button.cget('text'), '新增 PDF 文件')
        self.assertTrue(self.app.remove_pdf_button.instate(['disabled']))
        flow = ProjectWorkflow.create(self.directory / 'remove-pdf', 'Book')
        pdf = self.directory / 'book.pdf'
        pdf.write_bytes(pdf_bytes(1))
        for _ in range(2):
            job = flow.start_pdf_extraction(flow.inspect_pdf(pdf), 1, 1)
            job.wait()
            flow.finish_pdf_extraction(job)
        first, second = [b['id'] for b in flow.state['batches']]
        self.app.flow, self.app.batch_id = flow, first
        self.app.refresh()
        self.app.editor.insert('end', 'Unsaved correction')
        self.root.update()
        pending = self.app.current_text
        with patch('ebook2mp4.desktop.messagebox.askyesno', return_value=False):
            self.app.remove_pdf_button.invoke()
        self.assertEqual(self.app.current_text, pending)
        with patch('ebook2mp4.desktop.messagebox.askyesno', return_value=True), \
             patch('ebook2mp4.workflow.os.replace', side_effect=OSError('disk full')), \
             patch('ebook2mp4.desktop.messagebox.showerror'):
            self.app.remove_pdf_button.invoke()
        self.assertEqual(self.app.current_text, pending)
        self.assertEqual(self.app.batch_id, first)
        with patch('ebook2mp4.desktop.messagebox.askyesno', return_value=True):
            self.app.remove_pdf_button.invoke()
        self.root.update()
        self.assertEqual(self.app.batch_id, second)
        self.assertEqual(list(self.app.batch_list.get_children()), [second])
        with patch('ebook2mp4.desktop.messagebox.askyesno', return_value=True):
            self.app.remove_pdf_button.invoke()
        self.root.update()
        self.assertIsNone(self.app.batch_id)
        self.assertEqual(self.app.current_text, '')
        self.assertTrue(self.app.remove_pdf_button.instate(['disabled']))
        self.assertEqual(ProjectWorkflow.open(flow.root).state['batches'], [])

    def test_pdf_ui_select_extract_compare_edit_mapping_and_cleanup_undo(self):
        from test_pdf import pdf_bytes
        self.app.flow = ProjectWorkflow.create(self.directory / 'PDF project', 'PDF Book')
        self.app.refresh()
        pdf = self.directory / 'book.pdf'
        pdf.write_bytes(pdf_bytes())
        with patch('ebook2mp4.desktop.filedialog.askopenfilename', return_value=str(pdf)):
            self.app.import_pdf()
        dialog = self.app.pdf_dialog
        def until(predicate):
            end = time.monotonic() + 15
            while not predicate() and time.monotonic() < end:
                self.root.update()
                time.sleep(.01)
            self.assertTrue(predicate())
        until(lambda: dialog.ready)
        self.assertEqual((dialog.start.get(), dialog.end.get()), ('1', '20'))
        dialog.start.set('3')
        dialog.end.set('5')
        dialog.extract_button.invoke()
        until(lambda: self.app.batch_id is not None)
        self.assertIn('Chapter 3:', self.app.current_text)
        self.assertNotIn('Chapter 6:', self.app.current_text)
        self.assertIn('· 精確對應原始頁次', self.app.source_meta.cget('text'))
        self.app.editor.insert('end', '\nsecond line')
        self.root.update()
        self.assertIn('無精確對應', self.app.source_meta.cget('text'))
        before = self.app.current_text
        self.app.cleanup_line_breaks()
        preview_dialog = next(w for w in self.root.winfo_children()
                              if w.winfo_class() == 'Toplevel')
        apply = next(w for w in descendants(preview_dialog)
                     if w.winfo_class() == 'TButton' and w.cget('text') == '套用整理')
        apply.invoke()
        self.root.update()
        self.assertNotEqual(self.app.current_text, before)
        self.app.undo()
        self.root.update()
        self.assertEqual(self.app.current_text, before)

    def test_cancelled_pdf_save_failure_keeps_candidate_for_retry(self):
        from test_pdf import pdf_bytes
        self.app.flow = ProjectWorkflow.create(self.directory / 'PDF retry', 'PDF Book')
        self.app.refresh()
        pdf = self.directory / 'book.pdf'
        pdf.write_bytes(pdf_bytes())
        with patch('ebook2mp4.desktop.filedialog.askopenfilename', return_value=str(pdf)):
            self.app.import_pdf()
        dialog = self.app.pdf_dialog
        deadline = time.monotonic() + 10
        while not dialog.ready and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.01)
        self.assertTrue(dialog.ready)
        dialog.extract_button.invoke()
        job = dialog.job
        deadline = time.monotonic() + 5
        while not job.pages and time.monotonic() < deadline:
            time.sleep(.002)
        with patch('ebook2mp4.workflow.os.replace', side_effect=OSError('disk full')):
            dialog.close()
            self.assertTrue(job.wait(10))
            deadline = time.monotonic() + 5
            while dialog.winfo_exists() and dialog.job is not None and time.monotonic() < deadline:
                self.root.update()
                time.sleep(.01)
        self.assertTrue(dialog.winfo_exists(), 'Failed publication must retain completed page results for retry')
        self.assertEqual(self.app.flow.state['batches'], [])
        dialog.retry_button.invoke()
        deadline = time.monotonic() + 5
        while self.app.batch_id is None and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.01)
        self.assertIsNotNone(self.app.batch_id)
        self.assertEqual(self.app.flow.pdf_pages(self.app.batch_id)[0]['status'], 'success')

    def test_failed_pdf_page_preview_does_not_show_previous_page_image(self):
        import pypdfium2
        from test_pdf import pdf_bytes
        flow = ProjectWorkflow.create(self.directory / 'PDF compare', 'Book')
        pdf = self.directory / 'book.pdf'
        pdf.write_bytes(pdf_bytes())
        job = flow.start_pdf_extraction(flow.inspect_pdf(pdf), 3, 5)
        job.wait()
        self.app.flow = flow
        self.app.batch_id = flow.finish_pdf_extraction(job)
        self.app.refresh()
        self.app.pages_button.invoke()
        dialog = self.app.pdf_dialog
        deadline = time.monotonic() + 10
        while not dialog.ready and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.01)
        self.assertTrue(dialog.canvas.find_all())
        with patch.object(pypdfium2.PdfPage, 'render', side_effect=RuntimeError('native failure')):
            dialog.page.set('4')
            dialog.view_button.invoke()
            deadline = time.monotonic() + 10
            while not dialog.ready and time.monotonic() < deadline:
                self.root.update()
                time.sleep(.01)
        self.assertIn('Chapter 4:', dialog.text.get('1.0', 'end-1c'))
        self.assertIn('無法', dialog.progress.cget('text'))
        self.assertFalse(dialog.canvas.find_all(), 'A failed page must never retain the previous page image')

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

    def test_proofread_search_replace_undo_confirm_and_unsaved_edit_invalidation(self):
        self.create_import()
        self.app.find_text.set('第一章')
        self.app.replace_text.set('序章')
        self.app.find_button.invoke()
        self.assertEqual(self.app.editor.get('sel.first', 'sel.last'), '第一章')
        self.app.replace_button.invoke()
        self.root.update()
        self.assertEqual(self.app.current_text, '序章。\n\nHello!')
        self.app.undo_button.invoke()
        self.root.update()
        self.assertEqual(self.app.current_text, '第一章。\n\nHello!')
        with patch('ebook2mp4.desktop.messagebox.askyesno', return_value=True):
            self.app.confirm_button.invoke()
        self.root.update()
        self.assertIn('已確認', self.app.reading_status.cget('text'))
        self.app.editor.insert('end', '新增')
        self.root.update()
        self.assertIn('尚未確認', self.app.reading_status.cget('text'))
        with self.assertRaisesRegex(ProjectError, '確認'):
            self.app.flow.reading_text(self.app.batch_id)
        self.app.undo_button.invoke()
        self.root.update()
        self.assertIn('尚未確認', self.app.reading_status.cget('text'))

    def test_external_reload_cancel_failure_copy_versions_and_explicit_replace(self):
        self.create_import()
        self.app.editor.insert('end', '未存編輯')
        self.root.update()
        pending = self.app.current_text
        external = self.directory / '外部稿.txt'
        external.write_bytes('外部校對內容'.encode('utf-8'))
        with patch('ebook2mp4.desktop.filedialog.askopenfilename', return_value=str(external)):
            self.app.reload_button.invoke()
        self.root.update()
        reload_button = next(w for w in descendants(self.root)
                             if w.winfo_class() == 'TButton' and w.cget('text') == '確認重載')
        with patch('ebook2mp4.desktop.messagebox.askyesnocancel', return_value=None):
            reload_button.invoke()
        self.assertEqual(self.app.current_text, pending)
        with patch('ebook2mp4.desktop.messagebox.askyesnocancel', return_value=True), \
             patch('ebook2mp4.workflow.os.replace', side_effect=PermissionError()), \
             patch('ebook2mp4.desktop.messagebox.showerror'):
            reload_button.invoke()
        self.assertEqual(self.app.current_text, pending)
        self.assertEqual(ProjectWorkflow.open(self.app.flow.root).texts(self.app.batch_id)[1], '第一章。\n\nHello!')
        with patch('ebook2mp4.desktop.messagebox.askyesnocancel', return_value=True):
            reload_button.invoke()
        self.assertEqual(self.app.current_text, '外部校對內容')
        self.app.versions_button.invoke()
        self.root.update()
        copies = [w for w in descendants(self.root) if w.winfo_class() == 'Text'
                  and '未存編輯' in w.get('1.0', 'end-1c')]
        self.assertEqual(len(copies), 1)
        self.app.editor.insert('end', '明確取代這段')
        self.root.update()
        with patch('ebook2mp4.desktop.filedialog.askopenfilename', return_value=str(external)):
            self.app.reload_button.invoke()
        reload_button = next(w for w in descendants(self.root)
                             if w.winfo_class() == 'TButton' and w.cget('text') == '確認重載')
        with patch('ebook2mp4.desktop.messagebox.askyesnocancel', return_value=False):
            reload_button.invoke()
        self.assertEqual(self.app.current_text, '外部校對內容')
        self.assertEqual(len(self.app.flow.state['batches'][0]['draft_copies']), 1)

    def test_replace_all_is_single_undo_and_export_includes_unsaved_text(self):
        self.create_import()
        self.app.find_text.set('l')
        self.app.replace_text.set('L')
        self.app.replace_all_button.invoke()
        self.assertEqual(self.app.current_text, '第一章。\n\nHeLLo!')
        export = self.directory / '輸出稿.txt'
        with patch('ebook2mp4.desktop.filedialog.asksaveasfilename', return_value=str(export)):
            self.app.export_button.invoke()
        self.assertEqual(export.read_bytes(), '第一章。\n\nHeLLo!'.encode('utf-8'))
        self.assertTrue(self.app.dirty)
        self.app.undo_button.invoke()
        self.assertEqual(self.app.current_text, '第一章。\n\nHello!')

    def test_tool_panel_mousewheel_reveals_versions_at_minimum_window(self):
        self.create_import()
        self.root.geometry('1040x640')
        self.root.update()
        before = self.app.versions_button.winfo_rooty()
        self.app.find_entry.event_generate('<MouseWheel>', delta=-1200)
        self.root.update()
        after = self.app.versions_button.winfo_rooty()
        self.assertLess(after, before)
        self.assertLess(after + self.app.versions_button.winfo_height(),
                        self.root.winfo_rooty() + self.root.winfo_height())

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
