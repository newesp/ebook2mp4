"""Native layout regressions: global save, task tabs, selection and preview safety."""
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


class WorkbenchLayout(unittest.TestCase):
    def setUp(self):
        base = Path('.scratch/test-runs')
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.root, self.app = make_app()
        self.addCleanup(self.root.destroy)
        source = self.folder / 'source.txt'
        source.write_bytes('第一行。\n第二行。\n\n第三段。'.encode('utf-8'))
        self.app.flow = ProjectWorkflow.create(self.folder / 'book', 'Layout')
        self.app.batch_id = self.app.flow.import_txt(self.app.flow.inspect_txt(source))
        self.app.refresh()
        self.root.state('normal')
        self.root.geometry('1040x640')
        self.root.update()

    def test_save_is_global_confirmation_only_in_confirm_and_all_tools_fit(self):
        for index in range(3):
            self.app.show_step(3) if index == 2 else self.app.open_tools(index)
            self.root.update()
            self.assertTrue(self.app.save_button.winfo_ismapped())
            self.assertEqual(bool(self.app.confirm_button.winfo_ismapped()), index == 2)
            controls = (self.app.undo_button,) if index == 0 else (self.app.gemini_start_button, self.app.gemini_history_button) if index == 1 else (self.app.confirm_button, self.app.versions_button)
            for control in controls:
                self.assertTrue(control.winfo_ismapped())
                self.assertGreaterEqual(control.winfo_rootx(), self.root.winfo_rootx())
                self.assertLessEqual(control.winfo_rootx()+control.winfo_width(), self.root.winfo_rootx()+self.root.winfo_width())
                self.assertLessEqual(control.winfo_rooty()+control.winfo_height(), self.root.winfo_rooty()+self.root.winfo_height())

    def test_selection_survives_ai_tab_and_focus_mode(self):
        self.app.editor.tag_add('sel', '1.0', '1.3')
        self.app.open_tools(1)
        self.app.toggle_focus()
        self.root.update()
        self.assertTrue(self.app.save_button.winfo_ismapped())
        self.assertFalse(self.app.right_panel.winfo_ismapped())
        self.app.focus_search()
        self.root.update()
        self.assertEqual(self.app.tool_tabs.index('current'), 0)
        self.assertEqual(self.app.editor.get('sel.first', 'sel.last'), '第一行')

    def test_menu_disabled_state_and_real_export_action(self):
        self.assertTrue(self.app.remove_pdf_button.instate(['disabled']))
        export = self.folder / 'export.txt'
        with patch('ebook2mp4.desktop.filedialog.asksaveasfilename', return_value=str(export)):
            self.app.export_button.invoke()
        self.assertEqual(export.read_text(encoding='utf-8'), self.app.current_text)

    def test_preview_view_choice_does_not_change_candidate_and_undo(self):
        original = self.app.current_text
        candidate = self.app.flow.preview_line_breaks(original)
        self.app.cleanup_line_breaks()
        self.root.update()
        dialog = next(w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel)
                      and w.title().startswith('換行整理預覽'))
        selector = next(w for w in descendants(dialog) if w.winfo_class() == 'TCombobox')
        selector.set('只看候選')
        selector.event_generate('<<ComboboxSelected>>')
        self.root.update()
        apply = next(w for w in descendants(dialog) if w.winfo_class() == 'TButton' and w.cget('text') == '套用整理')
        apply.invoke()
        self.root.update()
        self.assertEqual(self.app.current_text, candidate)
        self.app.undo()
        self.root.update()
        self.assertEqual(self.app.current_text, original)

    def test_bulk_source_decisions_confirm_and_preserve_existing_statuses(self):
        for disposition, label in (('resolved', '全部已處理'), ('skipped', '全部略過')):
            with self.subTest(disposition=disposition):
                self.app.flow.record_source_issues(self.app.batch_id, ['先前異常', '待處理一', '待處理二'])
                batch = next(b for b in self.app.flow.state['batches'] if b['id'] == self.app.batch_id)
                start = len(batch['source_issues']) - 3
                self.app.flow.resolve_source_issue(self.app.batch_id, start, 'skipped')
                self.app.review_source_issues()
                dialog = next(w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel)
                              and w.title() == '來源異常檢查')
                dialog.geometry('600x400')
                self.root.update()
                buttons = [w for w in descendants(dialog) if w.winfo_class() == 'TButton']
                for button in buttons:
                    self.assertGreaterEqual(button.winfo_rootx(), dialog.winfo_rootx())
                    self.assertLessEqual(button.winfo_rootx() + button.winfo_width(),
                                         dialog.winfo_rootx() + dialog.winfo_width())
                bulk = next(w for w in buttons if w.cget('text') == label)
                with patch('ebook2mp4.desktop.messagebox.askyesno', return_value=False):
                    bulk.invoke()
                self.assertEqual(len(self.app.flow.confirmation_blockers(self.app.batch_id)), 2)
                with patch('ebook2mp4.desktop.messagebox.askyesno', return_value=True) as confirm:
                    bulk.invoke()
                self.assertIn('2', confirm.call_args.args[1])
                batch = next(b for b in self.app.flow.state['batches'] if b['id'] == self.app.batch_id)
                self.assertEqual([i['status'] for i in batch['source_issues'][start:]],
                                 ['skipped', disposition, disposition])
                self.assertFalse(self.app.flow.confirmation_blockers(self.app.batch_id))
                self.assertTrue(bulk.instate(['disabled']))
                dialog.destroy()

    def test_source_blockers_remain_visible_after_save_and_in_other_tab(self):
        self.app.flow.record_source_issues(self.app.batch_id, ['尚未核對來源'])
        self.app.refresh()
        self.app.open_tools(1)
        self.app.editor.insert('end', '未存')
        self.root.update()
        self.assertTrue(self.app.save())
        self.root.update()
        self.assertIn('來源異常 1', self.app.stats.cget('text'))
        self.assertTrue(self.app.confirm_button.instate(['disabled']))
        self.assertIn('1 項待檢查', self.app.steps[2].cget('text'))
        self.assertEqual(self.app.batch_list.item(self.app.batch_id, 'values'), ('待檢查 1',))
        self.app.review_source_issues()
        self.root.update()
        dialog = next(w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel)
                      and w.title() == '來源異常檢查')
        skip = next(w for w in descendants(dialog) if w.winfo_class() == 'TButton' and w.cget('text') == '明確略過')
        with patch('ebook2mp4.desktop.messagebox.askyesno', return_value=True):
            skip.invoke()
        self.root.update()
        self.assertFalse(self.app.flow.confirmation_blockers(self.app.batch_id))

