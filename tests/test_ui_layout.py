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


def destroy_root(root):
    try:
        root.destroy()
    except tk.TclError:
        pass


class WorkbenchLayout(unittest.TestCase):
    def setUp(self):
        base = Path('.scratch/test-runs')
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.root, self.app = make_app()
        self.addCleanup(destroy_root, self.root)
        source = self.folder / 'source.txt'
        source.write_bytes('第一行。\n第二行。\n\n第三段。'.encode('utf-8'))
        self.app.flow = ProjectWorkflow.create(self.folder / 'book', 'Layout')
        self.app.batch_id = self.app.flow.import_txt(self.app.flow.inspect_txt(source))
        self.app.refresh()
        self.root.state('normal')
        self.root.geometry('1040x640')
        self.root.update()

    def test_tools_fit_and_primary_action_stays_visible(self):
        self.root.state('normal')
        self.root.geometry('900x640')
        for index in range(3):
            self.app.open_tools(index)
            self.root.update()
            for control in (self.app.next_button, self.app.tool_back):
                self.assertTrue(control.winfo_ismapped())
                self.assertGreaterEqual(control.winfo_rootx(), self.root.winfo_rootx())
                self.assertLessEqual(control.winfo_rootx()+control.winfo_width(), self.root.winfo_rootx()+self.root.winfo_width())
                self.assertLessEqual(control.winfo_rooty()+control.winfo_height(), self.root.winfo_rooty()+self.root.winfo_height())
            self.assertGreater(self.app.tool_panel.winfo_height(), 300)

    def test_source_resizing_restores_two_columns_without_callback_failure(self):
        errors = []
        self.root.report_callback_exception = lambda *args: errors.append(args)
        if not self.app.source_visible:
            self.app.toggle_source()
        for width in (1400, 900, 1400):
            self.root.state('normal')
            self.root.geometry(f'{width}x740')
            self.root.update()
            self.app.layout_workspace()
            self.root.update()
            self.assertEqual(len(self.app.panes.panes()), 1 if width == 900 else 2)
            if width == 1400:
                self.assertGreater(self.app.editor.winfo_width(), 400)
                self.assertGreater(self.app.source_frame.winfo_width(), 200)
        self.assertFalse(errors)

    def test_selection_survives_tools_and_source_toggle(self):
        self.app.editor.tag_add('sel', '1.0', '1.3')
        for index in range(3):
            self.app.open_tools(index)
            self.root.update()
        self.app.toggle_source()
        self.root.update()
        self.app.toggle_source()
        self.root.update()
        self.assertEqual(self.app.editor.get('sel.first', 'sel.last'), '第一行')
        self.app.focus_search()
        self.assertEqual(self.app.editor.get('sel.first', 'sel.last'), '第一行')

    def test_menu_export_uses_displayed_full_text(self):
        export = self.folder/'export.txt'
        self.app.editor.insert('end', '人工修改')
        with patch('ebook2mp4.desktop.filedialog.asksaveasfilename', return_value=str(export)):
            self.app.export_button.invoke()
        self.assertEqual(export.read_bytes().decode('utf-8'), self.app.current_text)

    def test_line_cleanup_preview_apply_and_single_undo(self):
        original = self.app.current_text
        candidate = self.app.flow.preview_line_breaks(original)
        self.app.cleanup_line_breaks()
        self.assertEqual(self.app.current_text, original)
        self.app.cleanup_preview.apply()
        self.root.update()
        self.assertEqual(self.app.current_text, candidate)
        self.app.undo()
        self.root.update()
        self.assertEqual(self.app.current_text, original)

    def test_source_blockers_visible_in_every_tool(self):
        self.app.flow.record_source_issues(self.app.batch_id, ['尚未核對來源'])
        for index in range(3):
            self.app.open_tools(index)
            self.app.update_stats()
            self.assertIn('來源異常 1', self.app.stats.cget('text'))
            self.assertTrue(self.app.next_button.instate(['disabled']))
        self.app.source_tools.resolve('skipped')
        self.assertFalse(self.app.flow.confirmation_blockers(self.app.batch_id))
