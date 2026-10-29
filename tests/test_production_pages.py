"""Single-window journeys through real Tk actions."""
import tkinter as tk
import unittest
import asyncio
import threading
import time
from unittest.mock import patch, AsyncMock

import test_ui_layout as fixture
import test_voice as voice_fixture


class ProductionPages(unittest.TestCase):
    def setUp(self):
        fixture.WorkbenchLayout.setUp(self)
        environment=patch.dict('os.environ',EBOOK2MP4_VOICE_HOME=str(self.folder/'voice-cache'))
        environment.start()
        self.addCleanup(environment.stop)

    def test_voice_production_and_service_management_share_main_window(self):
        self.app.steps[3].invoke()
        self.root.update()
        voice = self.app.voice_dialog
        self.assertIs(voice.winfo_toplevel(), self.root)
        voice.outgoing.delete('1.0', 'end')
        voice.outgoing.insert('1.0', '往返後仍保留的試聽文字。')
        self.app.narration()
        self.root.update()
        production = self.app.narration_dialog
        self.assertIs(production.winfo_toplevel(), self.root)
        self.app.voice_settings()
        self.root.update()
        self.assertEqual(voice.outgoing.get('1.0', 'end-1c'), '往返後仍保留的試聽文字。')
        voice.manage_button.invoke()
        self.root.update()
        service = self.app.production.service_page
        self.assertIs(service.winfo_toplevel(), self.root)
        self.assertEqual(self.app.production.voice_tab.cget('style'),'CompactActive.TButton')
        first=self.app.batch_id
        source=self.folder/'另一批次.txt'
        source.write_text('另一批次。',encoding='utf-8')
        self.app.batch_id=self.app.flow.import_txt(self.app.flow.inspect_txt(source))
        self.app.refresh()
        self.app.voice_settings()
        other_voice=self.app.voice_dialog
        other_voice.manage_button.invoke()
        self.root.update()
        self.assertIs(service.owner,other_voice)
        service.close()
        self.root.update()
        self.assertIs(self.app.production.current,other_voice)
        self.app.batch_id=first
        self.app.refresh()
        self.app.voice_settings()
        self.root.update()
        self.assertTrue(voice.winfo_ismapped())
        self.assertFalse(any(isinstance(w, tk.Toplevel) for w in self.root.winfo_children()))

    def test_background_narration_keeps_owner_and_survives_navigation(self):
        flow=self.app.flow
        batch=self.app.batch_id
        with patch('edge_tts.list_voices',new=AsyncMock(return_value=voice_fixture.VOICES)):
            job=flow.start_voice_refresh()
            self.assertTrue(job.wait(5))
        flow.save_voice_settings('zh-TW-TestNeural',batch_id=batch)
        flow.confirm_reading(batch)
        self.path=self.folder
        audio=voice_fixture.VoiceJourney.audio(self)
        waiting=threading.Event()
        proceed=threading.Event()
        class Service:
            def __init__(self,*a,**k): pass
            async def stream(self):
                waiting.set()
                while not proceed.is_set(): await asyncio.sleep(.01)
                yield dict(type='audio',data=audio)
        self.app.narration()
        page=self.app.narration_dialog
        deadline=time.monotonic()+5
        while page.check_job is not None and time.monotonic()<deadline:
            self.root.update();time.sleep(.02)
        with patch('edge_tts.Communicate',Service):
            page.consent.set(True)
            page.start_button.invoke()
            job=page.job
            self.addCleanup(lambda: job.cancel() if not job.wait(0) else None)
            self.assertTrue(waiting.wait(5))
            self.app.show_step(2)
            self.root.update()
            self.assertFalse(job.wait(0))
            second=self.folder/'second.txt'
            second.write_text('另一批次。',encoding='utf-8')
            second_id=flow.import_txt(flow.inspect_txt(second))
            self.app.batch_id=second_id
            self.app.refresh()
            self.app.voice_settings()
            self.root.update()
            self.assertEqual(self.app.voice_dialog.batch_id,second_id)
            self.assertEqual(page.job.snapshot['batch_id'],batch)
            self.app.production.task_button.invoke()
            self.root.update()
            self.assertEqual(self.app.batch_id,batch)
            self.assertIs(self.app.narration_dialog,page)
            proceed.set()
            deadline=time.monotonic()+15
            while (page.job is not None or page.check_job is not None) and time.monotonic()<deadline:
                self.root.update();time.sleep(.02)
            self.assertIsNone(page.job)
        self.assertIsNotNone(flow.narration(batch))

    def test_secondary_dialog_close_does_not_bypass_later_unsaved_text_check(self):
        dialog=tk.Toplevel(self.root)
        dialog.close=dialog.destroy
        self.app.gemini_settings_dialog=dialog
        self.app.close()
        self.assertFalse(self.app._closing)
        self.assertIsNotNone(self.app.production.timer)
        self.app.editor.insert('end','未存稿必須保留。')
        self.root.update()
        with patch('ebook2mp4.desktop.messagebox.askyesnocancel',return_value=None) as prompt:
            self.app.close()
        prompt.assert_called_once()
        self.assertTrue(self.root.winfo_exists())
        self.assertTrue(self.app.dirty)


if __name__ == '__main__':
    unittest.main()
