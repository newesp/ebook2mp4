"""Version host ownership, applicable actions, scroll transitions, and guards."""
import unittest
from unittest.mock import patch
import test_unified_manuscript as unified
from ebook2mp4.workflow import ProjectError


class VersionTests(unittest.TestCase):
    setUp = unified.ManuscriptTests.setUp
    app = unified.ManuscriptTests.app

    def test_empty_short_long_and_return_to_other_inner_page(self):
        root, app = self.app()
        app.show_versions();root.update()
        self.assertFalse(app.inner_host.context.winfo_ismapped())
        self.assertFalse(app.inner_host.actions.visible_ids)
        self.assertFalse(app.version_page.scroll.winfo_ismapped())
        self.flow.save_reading_manuscript(self.batch,'short')
        app.refresh_versions();app.inner_host.refresh(app.version_page.page_id);root.update()
        app.version_selector.current(0);app.version_page.select();root.update()
        self.assertEqual(app.inner_host.actions.visible_ids, {'versions.delete','versions.restore'})
        self.assertFalse(app.version_page.scroll.winfo_ismapped())
        app.set_editor('\n'.join('很長的人工稿。' for _ in range(500)))
        app.preview_version();root.update()
        self.assertTrue(app.version_page.scroll.winfo_ismapped())
        app.version_diff.yview_moveto(1);root.update()
        self.assertEqual(app.version_diff.yview()[1],1)
        app.set_editor('short');app.preview_version();root.update()
        self.assertFalse(app.version_page.scroll.winfo_ismapped())
        app.close_tools();app.gemini_settings();root.update()
        self.assertTrue(app.inner_host.context.winfo_ismapped())
        self.assertNotIn('versions.restore',app.inner_host.actions.callbacks)

    def test_backup_has_no_delete_and_failed_restore_preserves_editor(self):
        root, app = self.app()
        self.flow.backup_manuscript(self.batch,'historical')
        app.show_versions();root.update()
        self.assertEqual(app.inner_host.actions.visible_ids, {'versions.restore'})
        before=app.current_text
        with patch.object(self.flow,'backup_manuscript',side_effect=ProjectError('controlled backup failure')):
            app.inner_host.actions.buttons['versions.restore'].invoke()
        self.assertEqual(app.current_text,before)

    def test_delete_cancel_and_restore_backup(self):
        self.flow.save_reading_manuscript(self.batch,'historical')
        root, app = self.app();app.show_versions();root.update()
        app.version_selector.current(0);app.version_page.select();root.update()
        with patch('tkinter.messagebox.askyesno',return_value=False) as confirm:
            app.inner_host.actions.buttons['versions.delete'].invoke()
            self.assertEqual(confirm.call_args.kwargs['default'],'no')
        self.assertEqual(len(self.flow._batch(self.batch)['readings']),1)
        before=app.current_text
        app.inner_host.actions.buttons['versions.restore'].invoke()
        self.assertEqual(app.current_text,'historical')
        self.assertTrue(self.flow._batch(self.batch)['draft_copies'])
