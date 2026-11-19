"""Shared host, settings retention, connection scope, and usable form geometry."""
import unittest
from unittest.mock import patch
import test_unified_manuscript as unified
from ebook2mp4.workflow import ProjectError


class AiSettingsTests(unittest.TestCase):
    setUp = unified.ManuscriptTests.setUp
    app = unified.ManuscriptTests.app

    def test_save_settings_includes_local_connection_and_project_preferences(self):
        root, app = self.app()
        app.gemini_settings()
        app.model.set('gemini-controlled-custom');app.api_key.set('synthetic-key');app.font_size.set('18')
        with patch('ebook2mp4.workflow.ProjectWorkflow.save_gemini_settings') as save:
            app.inner_host.actions.buttons['ai.save-settings'].invoke()
            save.assert_called_once_with('synthetic-key','gemini-controlled-custom')
        self.assertEqual(app.flow.state['manuscript_settings']['font_size'],18)
        self.assertIn('含本機連線',app.inner_host.presentation.summary)
        app.font_size.set('invalid')
        with patch('ebook2mp4.workflow.ProjectWorkflow.save_gemini_settings') as save:
            self.assertFalse(app.save_connection())
            save.assert_not_called()

    def test_shared_host_and_connection_commands_in_both_states(self):
        root, app = self.app()
        app.gemini_settings()
        root.update()
        page = app.ai_settings_page
        self.assertIs(page.master, app.inner_host.content)
        self.assertFalse(app.tool_panel.winfo_ismapped())
        for _ in range(3):
            self.assertEqual(app.inner_host.actions.visible_ids, {'ai.save-settings','ai.test-connection'})
            with patch.object(app, 'test_connection') as callback:
                app.inner_host.actions.buttons['ai.test-connection'].invoke()
                callback.assert_called_once()
            page.toggle_connection()
            root.update()
        app.close_tools()
        self.assertFalse(app.inner_host.actions.callbacks)

    def test_form_fits_and_preserves_inputs_after_failure_and_return(self):
        root, app = self.app()
        app.gemini_settings()
        page = app.ai_settings_page
        app.model.set('gemini-controlled-custom')
        app.api_key.set('synthetic-key')
        for size in ('1360x820','1280x720','900x640'):
            root.state('normal');root.geometry(size)
            for expanded in (False,True):
                if page.expanded != expanded:page.toggle_connection()
                for _ in range(3):root.update();app.layout_workspace()
                self.assertEqual(page.scroll.canvas.yview(), (0,1))
                controls = page.controls
                self.assertEqual(len({w.winfo_height() for w in controls}),1)
                self.assertLessEqual(abs(controls[0].winfo_rooty()-controls[1].winfo_rooty()),2)
        with patch.object(app.flow, '_commit', side_effect=ProjectError('controlled failure')):
            page.save_preferences()
        self.assertEqual(app.model.get(),'gemini-controlled-custom')
        self.assertIn('controlled failure',app.inner_host.presentation.summary)
        app.close_tools();app.gemini_settings();root.update()
        self.assertEqual(app.api_key.get(),'synthetic-key')
        self.assertEqual(app.model.get(),'gemini-controlled-custom')
