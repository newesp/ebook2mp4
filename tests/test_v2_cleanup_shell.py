"""Shared cleanup host ownership, aligned bands, and guarded commit contracts."""
import tkinter.font as tkfont
import unittest
from unittest.mock import PropertyMock, patch

import test_unified_manuscript as unified
from ebook2mp4.desktop_shell import ActionBar, ActionSpec, PagePresentation
from ebook2mp4.workflow import ProjectError, ProjectWorkflow


APPLY = 'manuscript.cleanup.apply'


class CleanupShellTests(unittest.TestCase):
    setUp = unified.ManuscriptTests.setUp
    app = unified.ManuscriptTests.app
    spin = unified.ManuscriptTests.spin

    def changed(self, paragraphs=200):
        self.flow.save_draft(self.batch, '\n\n'.join(
            f'第 {i} 段。第一行。\n第二行。保留空白與標點。' for i in range(paragraphs)))
        return self.app()

    def settle(self, root, app, size=None):
        if size:
            root.state('normal')
            root.geometry(size)
        for _ in range(3):
            root.update()
            app.layout_workspace()
        root.update()

    def assert_inside_ancestors(self, widget, root):
        self.assertTrue(widget.winfo_ismapped(), str(widget))
        x, y = widget.winfo_rootx(), widget.winfo_rooty()
        right, bottom = x + widget.winfo_width(), y + widget.winfo_height()
        ancestor = widget.master
        while ancestor is not None:
            ax, ay = ancestor.winfo_rootx(), ancestor.winfo_rooty()
            self.assertGreaterEqual(x, ax-2, str(ancestor))
            self.assertGreaterEqual(y, ay-2, str(ancestor))
            self.assertLessEqual(right, ax+ancestor.winfo_width()+2, str(ancestor))
            self.assertLessEqual(bottom, ay+ancestor.winfo_height()+2, str(ancestor))
            if ancestor is root:
                break
            ancestor = ancestor.master

    def assert_aligned(self, root, app, min_diff_height):
        host = app.inner_host
        controls = (app.focus_button, app.import_control,
                    app.shell.documents.management, host.back)
        self.assertLessEqual(max(w.winfo_rooty() for w in controls)-
                             min(w.winfo_rooty() for w in controls), 2)
        self.assertLessEqual(max(w.winfo_height() for w in controls)-
                             min(w.winfo_height() for w in controls), 2)
        self.assertLessEqual(abs(app.list_header.winfo_rooty()-host.header.winfo_rooty()), 2)
        self.assertLessEqual(abs(app.batch_list.winfo_rooty()-host.panel.winfo_rooty()), 2)
        self.assertGreaterEqual(app.cleanup_preview.diff.winfo_height(), min_diff_height)
        for control in (*controls, host.title, host.context, host.actions.stats,
                        host.actions.buttons[APPLY], app.cleanup_preview.diff):
            self.assert_inside_ancestors(control, root)

    def test_cleanup_uses_fixed_shared_ports_and_only_current_actions(self):
        root, app = self.changed()
        host = app.inner_host
        self.assertIs(host.master, app.shell.workspace)
        self.assertIs(app.cleanup_preview.master, host.content)
        self.assertIsInstance(host.actions, ActionBar)
        parents = (host.master, host.header.master, host.panel.master,
                   host.content.master, host.actions.master)
        app.cleanup_button.invoke()
        self.settle(root, app, '1360x820')
        self.assertEqual(host.active_id, app.cleanup_preview.page_id)
        self.assertEqual(host.presentation.title, '整理換行預覽')
        self.assertEqual(host.actions.visible_ids, {APPLY})
        self.assertEqual(set(app.shell.footer.callbacks), set())
        self.assertNotIn('manuscript.next', app.shell.footer.visible_ids)
        self.assertFalse(app.tool_panel.winfo_ismapped())
        self.assertFalse(app.tool_back.winfo_ismapped())
        self.assertFalse(app.next_button.winfo_ismapped())
        self.assertFalse(app.job_bar.winfo_ismapped())
        self.assertEqual(host.actions.stats.cget('text'), app.cleanup_preview.message)
        host.back.invoke()
        self.settle(root, app)
        self.assertIsNone(host.active_id)
        self.assertFalse(host.actions.callbacks)
        self.assertTrue(app.next_button.winfo_ismapped())
        app.cleanup_button.invoke()
        self.assertEqual(parents, (host.master, host.header.master, host.panel.master,
                                   host.content.master, host.actions.master))

    def test_shared_header_and_content_origins_at_supported_sizes_and_18pt(self):
        root, app = self.changed()
        for font_size in (12, 18):
            app.font_size.set(str(font_size))
            app.cleanup_button.invoke()
            for size, minimum in (('1360x820', 430), ('1280x720', 350), ('900x640', 280)):
                with self.subTest(size=size, font_size=font_size):
                    self.settle(root, app, size)
                    self.assert_aligned(root, app, minimum)
                    if font_size == 18 and size == '900x640':
                        font = tkfont.Font(root=root, font=app.cleanup_preview.diff.cget('font'))
                        self.assertGreaterEqual(app.cleanup_preview.diff.winfo_height() //
                                                font.metrics('linespace'), 8)
            app.inner_host.back.invoke()
        app.cleanup_button.invoke()
        root.state('zoomed')
        self.settle(root, app)
        self.assert_aligned(root, app, 430)

    def test_list_collapse_reclaims_track_and_reopen_restores_aligned_edges(self):
        root, app = self.changed()
        app.cleanup_button.invoke()
        self.settle(root, app, '900x640')
        selection = app.batch_list.selection()
        list_view = app.batch_list.yview()
        width = app.inner_host.winfo_width()
        app.focus_button.invoke()
        self.settle(root, app)
        self.assertFalse(app.left_panel.winfo_ismapped())
        self.assertEqual(app.center.winfo_x(), 0)
        self.assertEqual(app.center.winfo_width(), app.body.winfo_width())
        self.assertGreater(app.inner_host.winfo_width(), width)
        self.assert_inside_ancestors(app.inner_host.reopen, root)
        app.inner_host.reopen.invoke()
        self.settle(root, app)
        self.assertEqual(app.batch_list.selection(), selection)
        self.assertEqual(app.batch_list.yview(), list_view)
        self.assertFalse(app.inner_host.reopen.winfo_ismapped())
        self.assert_aligned(root, app, 280)

    def test_long_save_error_wraps_without_clipping_actions_or_ancestors(self):
        root, app = self.changed()
        app.cleanup_button.invoke()
        self.settle(root, app, '900x640')
        message = '受控保存失敗：請確認專案資料夾可寫入，排除問題後重試。' * 4
        before = app.current_text
        with patch.object(app.flow, 'save_workspace', side_effect=ProjectError(message)):
            app.inner_host.actions.buttons[APPLY].invoke()
        self.settle(root, app)
        self.assertEqual(app.inner_host.actions.stats.cget('text'), message)
        self.assertEqual(app.current_text, before)
        for widget in (app.inner_host.actions.stats, app.inner_host.actions.buttons[APPLY],
                       app.inner_host.back, app.cleanup_preview.diff):
            self.assert_inside_ancestors(widget, root)
        self.assertGreater(int(app.inner_host.actions.stats.cget('wraplength')), 0)
        self.assertGreaterEqual(app.inner_host.actions.stats.winfo_height(),
                                app.inner_host.actions.stats.winfo_reqheight()-2)
        self.assertTrue(app.cleanup_preview.apply())

    def test_return_keeps_unsaved_text_search_selection_cursor_and_scroll(self):
        root, app = self.changed(500)
        self.settle(root, app, '1280x720')
        app.editor.insert('end', '\n尚未儲存的人工補充。')
        app.editor.mark_set('insert', '250.3')
        app.editor.tag_add('sel', '250.0', '250.5')
        app.editor.yview_moveto(.45)
        app.find_text.set('人工')
        root.update()
        before = (app.current_text, app.editor.index('insert'),
                  app.editor.get('sel.first', 'sel.last'), app.editor.yview()[0])
        app.cleanup_button.invoke()
        self.settle(root, app)
        app.cleanup_preview.diff.yview_moveto(1)
        app.inner_host.back.invoke()
        self.settle(root, app)
        self.assertEqual((app.current_text, app.editor.index('insert'),
                          app.editor.get('sel.first', 'sel.last')), before[:3])
        self.assertAlmostEqual(app.editor.yview()[0], before[3], places=2)
        self.assertEqual(app.find_text.get(), '人工')
        self.assertIsNone(app.cleanup_preview.identity)

    def test_backup_failure_prevents_workspace_save_and_preserves_readiness(self):
        root, app = self.changed()
        app.confirm_reading()
        before = app.current_text
        app.cleanup_button.invoke()
        state = app.flow.state
        with patch.object(app.flow, 'backup_manuscript', side_effect=ProjectError('備份失敗')), \
                patch.object(app.flow, 'save_workspace') as save:
            self.assertFalse(app.cleanup_preview.apply())
            save.assert_not_called()
        self.assertEqual(app.flow.state, state)
        self.assertEqual(app.current_text, before)
        self.assertTrue(app.reading_ready())
        self.assertTrue(app.tools_open)
        self.assertIn('備份失敗', app.inner_host.actions.stats.cget('text'))
        self.assertTrue(app.cleanup_preview.apply())

    def test_stale_flow_batch_and_busy_source_guards_never_write(self):
        root, app = self.changed()
        other_batch = self.flow.import_txt(self.flow.inspect_txt(self.source))
        other_flow = ProjectWorkflow.open(self.flow.root)
        scenarios = (
            ('flow', lambda: patch.object(app, 'flow', other_flow)),
            ('batch', lambda: patch.object(app, 'batch_id', other_batch)),
            ('busy', lambda: patch.object(type(app), 'workspace_busy',
                                          new_callable=PropertyMock, return_value=True)),
            ('source', lambda: patch.object(app, 'source_pending', True)),
        )
        for name, guard in scenarios:
            with self.subTest(guard=name):
                app.cleanup_button.invoke()
                before = app.current_text
                state = app.flow.state
                with patch.object(ProjectWorkflow, 'backup_manuscript') as backup, \
                        patch.object(ProjectWorkflow, 'save_workspace') as save, guard():
                    self.assertFalse(app.cleanup_preview.apply())
                    backup.assert_not_called()
                    save.assert_not_called()
                self.assertEqual(app.flow.state, state)
                self.assertEqual(app.current_text, before)
                self.assertTrue(app.cleanup_preview.stale)
                self.assertIn('重新預覽', app.inner_host.actions.stats.cget('text'))
                self.assertTrue(app.inner_host.actions.buttons[APPLY].instate(['disabled']))
                app.close_tools()

    def test_dispatchers_are_reused_and_hidden_page_callbacks_cannot_commit(self):
        root, app = self.changed()
        app.cleanup_button.invoke()
        host = app.inner_host
        button = host.actions.buttons[APPLY]
        dispatcher = button.cget('command')
        back_dispatcher = host.back.cget('command')
        for _ in range(60):
            host.refresh(app.cleanup_preview.page_id)
        self.assertEqual(button.cget('command'), dispatcher)
        self.assertEqual(host.back.cget('command'), back_dispatcher)
        calls = []
        with patch.object(app.flow, 'backup_manuscript') as backup:
            app.open_tools(0)
            button.invoke()
            backup.assert_not_called()
            self.assertTrue(app.tools_open)
            self.assertEqual(app.active_tool, 0)
            self.assertEqual(host.active_id, app.version_page.page_id)
            host.back.invoke()
            self.assertFalse(app.tools_open)
        app.close_tools()
        app.cleanup_button.invoke()
        host.active_id = 'controlled.other'
        host.present('controlled.other', PagePresentation(1, '另一內頁', '待處理', (
            ActionSpec('controlled.back', '返回', 'back', lambda: calls.append('back')),
            ActionSpec('controlled.apply', '另一動作', 'primary', lambda: calls.append('current')),
        )), '合成內容')
        self.assertFalse(host.refresh(app.cleanup_preview.page_id))
        button.invoke()
        host.actions.buttons['controlled.apply'].invoke()
        self.assertEqual(calls, ['current'])
        host.hide()

    def test_main_step_suspends_hidden_preview_commands_and_resumes_on_return(self):
        root, app = self.changed()
        self.assertTrue(app.confirm_reading())
        app.cleanup_button.invoke()
        host = app.inner_host
        button = host.actions.buttons[APPLY]
        original = app.current_text
        app.focus_button.invoke()
        self.settle(root, app)
        self.assertTrue(app.focus_mode)
        app.show_step(4)
        self.settle(root, app)
        self.assertFalse(host.winfo_ismapped())
        self.assertFalse(host.actions.callbacks)
        with patch.object(app.flow, 'backup_manuscript') as backup:
            button.invoke()
            host.back.invoke()
            host.reopen.invoke()
            backup.assert_not_called()
        self.assertTrue(app.focus_mode)
        self.assertTrue(app.tools_open)
        self.assertEqual(app.current_text, original)
        app.show_step(1)
        self.settle(root, app)
        self.assertTrue(host.winfo_ismapped())
        self.assertIn(APPLY, host.actions.callbacks)
        button.invoke()
        self.assertFalse(app.tools_open)
        self.assertNotEqual(app.current_text, original)

    def test_unsaved_invalid_font_setting_does_not_break_preview(self):
        root, app = self.changed()
        expected = app.editor.cget('font')
        app.font_size.set('尚未輸入有效字級')
        app.cleanup_button.invoke()
        self.settle(root, app, '900x640')
        self.assertEqual(app.cleanup_preview.diff.cget('font'), expected)
        self.assertTrue(app.inner_host.winfo_ismapped())


if __name__ == '__main__':
    unittest.main()
