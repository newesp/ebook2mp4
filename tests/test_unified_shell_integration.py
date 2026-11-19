"""Real route transitions, command ownership and bounded scrolling."""
import time
import gc
import unittest
from unittest.mock import AsyncMock, patch

import test_unified_manuscript as fixture
from test_voice import VOICES
from ebook2mp4.workflow import ProjectWorkflow


class UnifiedShellIntegration(unittest.TestCase):
    def setUp(self):
        fixture.ManuscriptTests.setUp(self)
        self.addCleanup(gc.collect)

    def app(self):
        from ebook2mp4.desktop import make_app
        root,app=make_app()
        app.flow,app.batch_id=self.flow,self.batch
        app.refresh();root.update()
        app.report=lambda error:app.status.configure(text=str(error))
        def shutdown():
            with patch('tkinter.messagebox.askyesnocancel',return_value=False):
                app.close()
                end=time.monotonic()+8
                while time.monotonic()<end:
                    try:
                        if not root.winfo_exists():return
                        root.update();time.sleep(.01)
                    except Exception:return
                self.fail('Owned test window did not close normally')
        self.addCleanup(shutdown)
        return root,app

    def settle(self, root, app, size=None):
        if size:
            root.state('normal');root.geometry(size)
        end=time.monotonic()+.15
        while time.monotonic()<end:
            root.update();time.sleep(.008)
        app.layout_workspace();root.update()

    def ready(self):
        self.flow.save_reading_manuscript(self.batch,self.flow.texts(self.batch)[1])
        mock=patch('edge_tts.list_voices',new=AsyncMock(return_value=VOICES))
        mock.start();self.addCleanup(mock.stop)
        return self.app()

    def test_real_routes_keep_fixed_parents_and_exclusive_action_port(self):
        root,app=self.ready();shell=app.shell
        common=(shell.navigation,shell.documents,shell.workspace,shell.footer,app.editor)
        parents=tuple(w.master for w in common)
        routes=(app.show_versions,app.gemini_settings,app.compare_pdf_pages,
                app.voice_settings,app.narration,app.total_audio,
                app.batch_video,app.total_video,lambda:app.production.show('merge'),
                app.production.show_versions)
        for route in routes:
            route();self.settle(root,app,'1280x720')
            current=shell.current
            self.assertIsNotNone(current)
            self.assertTrue(current.page_id)
            self.assertEqual(tuple(w.master for w in common),parents)
            self.assertEqual(sum(bool(w.winfo_ismapped()) for w in shell._roots),1)
            if current.production:
                self.assertFalse(app.next_button.winfo_ismapped())
                self.assertTrue(current.footer.winfo_ismapped())
                self.assertIs(current.footer.master,shell.footer)
                self.assertEqual([p for p in shell.footer.ports if p.winfo_ismapped()],[current.footer])
        app.show_step(1)
        if app.tools_open:app.close_tools()
        self.settle(root,app)
        self.assertTrue(app.next_button.winfo_ismapped())
        self.assertFalse(any(p.winfo_ismapped() for p in shell.footer.ports))

    def test_hidden_actions_dynamic_commands_and_old_project_are_guarded(self):
        root,app=self.ready();app.voice_settings();self.settle(root,app)
        voice=app.voice_dialog;button=voice.save_button;calls=[]
        dispatcher=button.cget('command')
        button.configure(command=lambda:calls.append('current'))
        button.invoke();self.assertEqual(calls,['current'])
        self.assertEqual(str(button.cget('command')),str(dispatcher))
        app.narration();self.settle(root,app)
        button.invoke();self.assertEqual(calls,['current'])
        owner=app.shell.current.owner;generation=app.shell.generation
        from types import SimpleNamespace
        voice.reflow(SimpleNamespace(widget=voice.settings_panel,width=500))
        app.production.sync_chrome();self.settle(root,app)
        self.assertIs(app.shell.current.owner,owner)
        self.assertEqual(app.shell.generation,generation)
        app.voice_settings();self.settle(root,app)
        app.flow=ProjectWorkflow.create(self.folder/'other','另一專案')
        button.invoke();self.assertEqual(calls,['current'])
        app.flow=voice.flow

    def test_generic_pages_use_shell_actions_without_losing_preview_draft(self):
        root,app=self.ready();app.voice_settings();self.settle(root,app)
        voice=app.voice_dialog
        voice.outgoing.delete('1.0','end');voice.outgoing.insert('1.0','保留試聽文字與游標。')
        voice.rate.set('-10%');voice.consent.set(False)
        for command in (voice.manage_services,voice.manage_local_packages):
            command();self.settle(root,app,'900x640')
            page=app.production.current
            self.assertIs(page.shell_footer.master,app.shell.footer)
            self.assertFalse(app.next_button.winfo_ismapped())
            self.assertTrue(page.back_button.winfo_ismapped())
            page.back_button.invoke();self.settle(root,app)
            self.assertIs(app.production.current,voice)
            self.assertEqual(voice.outgoing.get('1.0','end-1c'),'保留試聽文字與游標。')
            self.assertEqual(voice.rate.get(),'-10%')
            self.assertFalse(voice.consent.get())

    def test_scroll_page_removes_fit_track_and_resets_after_long_content(self):
        import tkinter as tk
        from tkinter import ttk
        from ebook2mp4.production_desktop import ScrollPage
        root=tk.Tk();self.addCleanup(root.destroy)
        root.geometry('500x300')
        page=ScrollPage(root);page.pack(fill='both',expand=True)
        labels=[ttk.Label(page.content,text=f'第 {i} 行') for i in range(80)]
        for label in labels:label.pack()
        root.update()
        self.assertTrue(page.scrollbar.winfo_ismapped())
        page.canvas.yview_moveto(1);root.update()
        self.assertAlmostEqual(page.canvas.yview()[1],1,places=3)
        for label in labels[1:]:label.destroy()
        end=time.monotonic()+.2
        while time.monotonic()<end:root.update();time.sleep(.01)
        self.assertFalse(page.scrollbar.winfo_ismapped())
        self.assertEqual(page.canvas.yview(),(0.,1.))

    def test_video_header_track_is_released_before_returning_to_other_pages(self):
        root,app=self.ready()
        for size in ('1360x820','900x640'):
            app.total_video();self.settle(root,app,size)
            self.assertGreater(app.production.grid_rowconfigure(1)['minsize'],0)
            app.voice_settings();self.settle(root,app)
            self.assertEqual(app.production.grid_rowconfigure(1)['minsize'],0)
            self.assertLessEqual(abs(app.voice_dialog.sources_panel.winfo_rooty()-app.list_header.winfo_rooty()),2)
            app.voice_dialog.manage_services();self.settle(root,app)
            self.assertLessEqual(abs(app.production.service_page.title.winfo_rooty()-app.list_header.winfo_rooty()),2)

    def test_voice_settings_overflow_has_its_own_reachable_viewport(self):
        root,app=self.ready();app.voice_settings();voice=app.voice_dialog
        original=voice.rate_info.cget('text')
        voice.rate_info.configure(text='\n'.join(f'第 {i} 項語速說明。' for i in range(20)))
        app.focus_mode=False;self.settle(root,app,'900x640')
        scroll=voice.settings_scroll
        self.assertTrue(scroll.scrollbar.winfo_ismapped())
        scroll.canvas.yview_moveto(1);self.settle(root,app)
        bottom=voice.refresh_button.winfo_rooty()+voice.refresh_button.winfo_height()
        self.assertLessEqual(bottom,scroll.canvas.winfo_rooty()+scroll.canvas.winfo_height()+2)
        self.assertTrue(voice.produce_button.winfo_ismapped())
        self.assertTrue(voice.outgoing.winfo_ismapped())
        for control in (voice.filter,voice.refresh_button):
            self.assertGreaterEqual(control.winfo_width(),control.winfo_reqwidth()-2)
        self.assertLessEqual(voice.sentence_label.winfo_width(),voice.sentence_control.winfo_width()+2)
        self.assertLessEqual(voice.paragraph_label.winfo_width(),voice.paragraph_control.winfo_width()+2)
        voice.rate_info.configure(text=original)
        self.settle(root,app,'1360x820')
        self.assertFalse(scroll.scrollbar.winfo_ismapped())
        self.assertEqual(scroll.canvas.yview(),(0.,1.))


if __name__=='__main__':unittest.main()
