"""User-entry contracts for the cleanup page and fixed footer, including no-ops."""
from pathlib import Path
import unittest
from unittest.mock import patch

import test_unified_manuscript as unified
from ebook2mp4.workflow import ProjectError, ProjectWorkflow


class CleanupWorkspace(unittest.TestCase):
    setUp = unified.ManuscriptTests.setUp
    app = unified.ManuscriptTests.app
    spin = unified.ManuscriptTests.spin

    def changed(self):
        self.flow.save_draft(self.batch, '第一行。\n第二行。\n\n第三段。')
        return self.app()

    def test_entry_is_cleanup_not_source_and_exit_retains_context(self):
        root, app = self.changed()
        app.editor.tag_add('sel', '1.0', '1.3')
        app.editor.mark_set('insert', '1.2')
        before = app.current_text
        app.cleanup_button.invoke()
        root.update()
        self.assertEqual(app.inner_host.title.cget('text'), '整理換行預覽')
        self.assertTrue(app.cleanup_preview.diff.winfo_ismapped())
        self.assertFalse(app.tool_pages[2].winfo_ismapped())
        for control in (app.source_tools.form_button, app.source_tools.run_button, app.source_tools.apply_button, app.next_button):
            self.assertFalse(control.winfo_ismapped())
        self.assertTrue(app.message_button.winfo_ismapped())
        self.assertEqual(app.inner_host.actions.buttons['manuscript.cleanup.apply'].cget('text'), '套用換行整理')
        app.inner_host.back.invoke()
        root.update()
        self.assertEqual(app.current_text, before)
        self.assertEqual(app.editor.index('insert'), '1.2')
        self.assertEqual(app.editor.get('sel.first', 'sel.last'), '第一行')
        self.assertTrue(app.next_button.winfo_ismapped())

    def test_unchanged_preview_never_backs_up_or_invalidates_reading(self):
        root, app = self.app()
        self.assertTrue(app.confirm_reading())
        state = app.flow.state
        app.cleanup_button.invoke()
        root.update()
        preview = app.cleanup_preview
        self.assertTrue(preview.empty.winfo_ismapped())
        self.assertFalse(preview.diff.winfo_ismapped())
        self.assertFalse(preview.scroll.winfo_ismapped())
        self.assertNotIn('manuscript.cleanup.apply', app.inner_host.actions.visible_ids)
        self.assertEqual(app.inner_host.back.cget('text'), '← 返回文稿')
        self.assertFalse(preview.apply())
        self.assertEqual(app.flow.state, state)
        self.assertTrue(app.reading_ready())
        app.inner_host.back.invoke()
        self.assertEqual(app.flow.state, state)

    def test_apply_persists_backup_and_is_one_undo_unit(self):
        root, app = self.changed()
        before = app.current_text
        app.cleanup_button.invoke()
        candidate = app.cleanup_preview.candidate
        self.assertTrue(app.cleanup_preview.apply())
        root.update()
        self.assertFalse(app.tools_open)
        self.assertEqual(app.current_text, candidate)
        opened = ProjectWorkflow.open(app.flow.root)
        self.assertEqual(opened.workspace_state(self.batch)['text'], candidate)
        copy = opened._batch(self.batch)['draft_copies'][-1]
        self.assertEqual(opened.draft_copy_text(self.batch, copy['id']), before)
        self.assertFalse(app.reading_ready())
        app.undo()
        root.update()
        self.assertEqual(app.current_text, before)

    def test_failed_apply_keeps_text_and_reading_confirmation(self):
        root, app = self.changed()
        app.confirm_reading()
        before = app.current_text
        app.cleanup_button.invoke()
        with patch.object(app.flow, 'save_workspace', side_effect=ProjectError('受控儲存失敗')):
            self.assertFalse(app.cleanup_preview.apply())
        self.assertTrue(app.tools_open)
        self.assertEqual(app.current_text, before)
        self.assertTrue(app.reading_ready())
        self.assertIn('受控儲存失敗', app.inner_host.actions.stats.cget('text'))

    def test_stale_preview_rejects_newer_editor_text(self):
        root, app = self.changed()
        app.cleanup_button.invoke()
        app.set_editor('後來的人工稿。')
        self.assertFalse(app.cleanup_preview.apply())
        self.assertEqual(app.current_text, '後來的人工稿。')
        self.assertIn('重新預覽', app.inner_host.actions.stats.cget('text'))

    def test_long_diff_scrolls_alone_with_fixed_actions(self):
        self.flow.save_draft(self.batch, '\n\n'.join(f'第 {i} 段\n第二行' for i in range(500)))
        root, app = self.app()
        app.cleanup_button.invoke()
        root.update()
        preview = app.cleanup_preview
        self.assertEqual(preview.change_count, 500)
        controls = (app.inner_host.back, app.inner_host.actions.stats,
                    app.inner_host.actions.buttons['manuscript.cleanup.apply'], app.message_button)
        bounds = [(w.winfo_rooty(), w.winfo_height()) for w in controls]
        preview.diff.yview_moveto(1)
        root.update()
        self.assertEqual(preview.diff.yview()[1], 1)
        self.assertEqual(bounds, [(w.winfo_rooty(), w.winfo_height()) for w in controls])
        preview.diff.yview_moveto(0)
        self.assertEqual(preview.diff.yview()[0], 0)

    def test_global_messages_align_with_project_in_normal_and_reduced_windows(self):
        root, app = self.app()
        root.state('normal')
        for geometry in ('1400x820', '900x640'):
            root.geometry(geometry)
            root.update()
            top = app.book.master
            project = app.project_menu.master
            buttons = (project, app.message_button)
            self.assertEqual(app.message_button.master, top)
            self.assertLessEqual(abs(buttons[0].winfo_rooty()-buttons[1].winfo_rooty()), 2)
            self.assertLessEqual(abs(buttons[0].winfo_height()-buttons[1].winfo_height()), 2)
            self.assertLessEqual(project.winfo_rootx()+project.winfo_width(), app.message_button.winfo_rootx())
            self.assertNotIn(app.message_button, app.footer_actions.winfo_children())
            for button in buttons:
                self.assertLessEqual(button.winfo_rootx()+button.winfo_width(), root.winfo_rootx()+root.winfo_width())
            self.assertFalse(app.job_bar.winfo_ismapped())

    def test_partial_controls_are_adjacent_and_cleanup_keeps_partial_contract(self):
        root, app = self.changed()
        with patch('ebook2mp4.gemini.load_settings', return_value=dict(key='controlled', model='gemini-test')), patch('ebook2mp4.gemini.generate', side_effect=ProjectError('受控服務失敗')):
            app.gemini_review()
            self.spin(root, lambda: app.workspace_job is None)
        root.state('normal')
        root.geometry('900x640')
        root.update()
        self.assertTrue(app.job_bar.winfo_ismapped())
        self.assertIn('尚有未校對', app.job_status.cget('text'))
        self.assertTrue(app.next_button.instate(['disabled']))
        self.assertEqual(app.retry_button.winfo_rooty(), app.keep_partial_button.winfo_rooty())
        self.assertLessEqual(app.retry_button.winfo_rootx()+app.retry_button.winfo_width(), app.keep_partial_button.winfo_rootx())
        review = app.workspace_review
        app.cleanup_button.invoke()
        root.update()
        self.assertFalse(app.job_bar.winfo_ismapped())
        self.assertTrue(app.cleanup_preview.apply())
        self.assertEqual(app.workspace_review, review)
        self.assertFalse(app.allow_partial)
        self.assertTrue(app.next_button.instate(['disabled']))
        app.keep_partial_button.invoke()
        self.assertTrue(app.allow_partial)
        self.assertFalse(app.next_button.instate(['disabled']))

    def test_global_messages_stay_available_across_pages_and_without_project(self):
        import tkinter as tk
        root, app = self.app()
        button = app.message_button
        app.status.remember('全域訊息驗收')
        for step in (4, 1):
            app.show_step(step)
            root.update()
            self.assertIs(app.message_button, button)
            self.assertTrue(button.winfo_ismapped())
            self.assertFalse(button.instate(['disabled']))
        app.flow, app.batch_id = None, None
        app.refresh()
        root.update()
        self.assertTrue(button.winfo_ismapped())
        button.invoke()
        root.update()
        dialog = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel)
                      and w.title() == '操作訊息記錄')
        def texts(widget):
            return ([widget.get('1.0', 'end')] if isinstance(widget, tk.Text) else
                    [text for child in widget.winfo_children() for text in texts(child)])
        self.assertTrue(any('全域訊息驗收' in text for text in texts(dialog)))
        dialog.destroy()
