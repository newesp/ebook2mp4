"""Service menu and editor journeys with isolated local credentials."""
import asyncio
import gc
import time
import unittest
from unittest.mock import patch
import test_voice_desktop as fixture
from ebook2mp4.tts_services import save_profile, profiles, delete_profile, credential
from ebook2mp4.workflow import ProjectError


class ServiceManagement(unittest.TestCase):
    def setUp(self):
        self.addCleanup(self.collect_ui)
        fixture.VoiceDesktop.setUp(self)

    def collect_ui(self):
        self.dialog=None;self.app=None;self.root=None
        gc.collect()

    def editor(self):
        identity=save_profile('Google','gemini-tts','test-secret')
        d=self.dialog
        d.reload_services();d.service.set(d.service_labels[identity]);d.change_service()
        d.model.set('future-tts-model');d.voice.set('Kore');d.rate.set('-10%')
        d.outgoing.delete('1.0','end');d.outgoing.insert('1.0','保留這段試聽文字。')
        d.update_service_menu();d.service_menu.invoke(1);self.root.update()
        editor=self.app.production.service_page
        self.addCleanup(lambda:editor.close() if editor.winfo_exists() else None)
        return identity,editor

    def test_one_menu_opens_selected_profile_and_preserves_settings_on_save(self):
        identity,e=self.editor()
        self.assertEqual(self.dialog.manage_button.winfo_class(),'TMenubutton')
        self.assertEqual(e.identity,identity)
        self.assertEqual(str(e.provider_control.cget('state')),'disabled')
        self.assertEqual(e.key.get(),'')
        e.name.set('有聲書 Gemini');e.save_button.invoke();self.root.update()
        self.assertEqual(profiles()[identity]['name'],'有聲書 Gemini')
        self.assertEqual(credential(dict(provider='gemini-tts',profile=identity)),'test-secret')
        self.assertEqual(self.dialog.service_ids[self.dialog.service.get()],identity)
        self.assertEqual(self.dialog.model.get(),'future-tts-model')
        self.assertEqual(self.dialog.voice.get(),'Kore')
        self.assertEqual(self.dialog.rate.get(),'-10%')
        self.assertEqual(self.dialog.outgoing.get('1.0','end-1c'),'保留這段試聽文字。')

    def test_cancel_then_confirm_delete_preserves_projects_and_shared_credentials(self):
        identity,e=self.editor()
        other=save_profile('Fish','fish-audio','other-secret')
        before=self.app.flow.state.copy()
        e.delete_button.invoke();self.root.update()
        self.assertTrue(e.delete_frame.winfo_ismapped())
        e.cancel_delete_button.invoke();self.assertIn(identity,profiles())
        e.delete_button.invoke();e.confirm_delete_button.invoke();self.root.update()
        self.assertNotIn(identity,profiles())
        self.assertIn(other,profiles())
        self.assertEqual(self.app.flow.state,before)
        self.assertEqual(self.dialog.service.get(),'Edge-TTS')
        self.assertEqual(self.dialog.voice.get(),'')
        self.assertEqual(self.dialog.outgoing.get('1.0','end-1c'),'保留這段試聽文字。')
        with self.assertRaises(ProjectError): delete_profile('edge-tts')

    def test_unsaved_edits_cancel_and_write_failures_keep_editor_open(self):
        identity,e=self.editor()
        e.name.set('尚未儲存')
        e.back_button.invoke();self.root.update()
        self.assertTrue(e.discard_frame.winfo_ismapped())
        e.keep_button.invoke();self.assertEqual(e.name.get(),'尚未儲存')
        with patch('ebook2mp4.workflow.ProjectWorkflow._atomic',side_effect=OSError('test')):
            e.save_button.invoke()
            self.assertTrue(e.winfo_exists())
            self.assertEqual(profiles()[identity]['name'],'Google')
            e.delete_button.invoke();e.confirm_delete_button.invoke()
            self.assertIn(identity,profiles())
        e.back_button.invoke();e.discard_button.invoke();self.root.update()
        self.assertEqual(profiles()[identity]['name'],'Google')

    def test_check_uses_draft_without_persisting_and_cancel_releases_job(self):
        identity,e=self.editor()
        e.name.set('不應儲存');e.key.set('replacement-key')
        requests=[]
        async def check(provider,key):
            requests.append((provider,key))
            await asyncio.sleep(60)
        with patch('ebook2mp4.service_desktop.check_service',check):
            e.check_button.invoke()
            self.assertEqual(str(e.save_button.cget('state')),'disabled')
            deadline=time.monotonic()+5
            while not requests and time.monotonic()<deadline:
                self.root.update();time.sleep(.01)
            e.check_button.invoke()
            while e.job is not None and time.monotonic()<deadline:
                self.root.update();time.sleep(.01)
        self.assertIsNone(e.job)
        self.assertIsNone(e.timer)
        self.assertEqual(requests,[('gemini-tts','replacement-key')])
        self.assertEqual(profiles()[identity]['name'],'Google')
        self.assertEqual(credential(dict(profile=identity,provider='gemini-tts')),'test-secret')

    def test_menu_builtin_states_and_busy_guard(self):
        d=self.dialog
        d.update_service_menu()
        self.assertEqual(str(d.service_menu.entrycget(1,'state')),'disabled')
        d.service.set('Kokoro · 本機 CPU');d.change_service();d.update_service_menu()
        self.assertEqual(d.manage_button.cget('text'),'新增／管理服務…')
        self.assertEqual(d.service_menu.entrycget(1,'label'),'管理本機語音包…')
        identity,e=self.editor()
        with patch.object(self.app.production,'service_changes_busy',return_value=True):
            e.update_controls()
            self.assertEqual(str(e.delete_button.cget('state')),'disabled')
            e.save();e.delete()
            self.assertIn(identity,profiles())

    def test_deleted_profile_cannot_be_recreated_by_stale_editor(self):
        identity,e=self.editor()
        delete_profile(identity)
        e.name.set('不能復活');e.key.set('replacement')
        e.save_button.invoke()
        self.assertNotIn(identity,profiles())
        self.assertTrue(e.winfo_exists())
        self.assertIn('已被移除',e.status.cget('text'))

    def test_replacing_key_and_reloading_preserves_profile_and_reuse_reference(self):
        identity,e=self.editor()
        e.key.set('replacement');e.save_button.invoke();self.root.update()
        self.assertEqual(credential(dict(provider='gemini-tts',profile=identity)),'replacement')
        self.dialog.update_service_menu();self.dialog.service_menu.invoke(1);self.root.update()
        e=self.app.production.service_page
        with patch('ebook2mp4.gemini.load_settings',return_value={'key':'shared-key'}):
            e.reuse_check.invoke();e.save_button.invoke();self.root.update()
        self.assertTrue(profiles()[identity]['reuse'])
        self.dialog.update_service_menu();self.dialog.service_menu.invoke(1);self.root.update()
        e=self.app.production.service_page
        self.assertTrue(e.reuse.get())
        with patch('ebook2mp4.gemini.load_settings',return_value={'key':'shared-key'}):
            e.delete_button.invoke();e.confirm_delete_button.invoke();self.root.update()
            from ebook2mp4.gemini import load_settings
            self.assertEqual(load_settings()['key'],'shared-key')

    def test_restored_window_keeps_footer_and_confirmation_inside_page(self):
        _,e=self.editor()
        self.root.state('normal')
        for size in ('1040x640','1360x820'):
            self.root.geometry(size);self.root.update()
            self.assertGreater(e.scroll.winfo_width(),e.help.master.winfo_width()*2)
            e.delete_button.invoke();self.root.update()
            for control in (e.back_button,e.save_button,e.delete_button,e.confirm_delete_button,e.cancel_delete_button):
                self.assertTrue(control.winfo_ismapped())
                # Fixed actions now live in the one shell footer. Confirmation
                # remains in the bounded service form, with its own scroll.
                bounds=e.shell_footer if control in (e.back_button,e.save_button,e.delete_button) else e
                self.assertGreaterEqual(control.winfo_rootx(),bounds.winfo_rootx())
                self.assertLessEqual(control.winfo_rootx()+control.winfo_width(),bounds.winfo_rootx()+bounds.winfo_width())
                self.assertGreaterEqual(control.winfo_rooty(),bounds.winfo_rooty())
                self.assertLessEqual(control.winfo_rooty()+control.winfo_height(),bounds.winfo_rooty()+bounds.winfo_height())
            self.assertIs(e.shell_footer.master,self.app.shell.footer)
            self.assertLessEqual(abs(e.shell_footer.winfo_rootx()-self.app.shell.workspace.winfo_rootx()),2)
            e.cancel_delete_button.invoke()


if __name__=='__main__': unittest.main()
