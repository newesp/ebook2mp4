"""The WM close command must finish after cached production pages are visited."""
import time
import asyncio
import threading
import tkinter as tk
import unittest
from unittest.mock import patch, AsyncMock
import test_ui_layout as fixture
import test_voice as voice_fixture


class CloseLifecycle(unittest.TestCase):
    setUp=fixture.WorkbenchLayout.setUp

    def close_window(self):
        errors=[]
        self.root.report_callback_exception=lambda *args: errors.append(args)
        command=self.root.protocol('WM_DELETE_WINDOW')
        self.root.tk.call(command)
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            try:
                if not self.root.winfo_exists(): break
                self.root.update()
            except tk.TclError:
                break
            time.sleep(.01)
        try:
            alive=bool(self.root.winfo_exists())
        except tk.TclError:
            alive=False
        self.assertFalse(alive,repr(errors))
        self.assertFalse(errors,repr(errors))

    def test_close_from_audio(self):
        self.app.narration()
        self.root.update()
        self.close_window()

    def test_close_after_returning_from_audio(self):
        self.app.narration()
        self.root.update()
        self.app.voice_settings()
        self.root.update()
        self.close_window()

    def test_close_after_video_page(self):
        self.app.step=4
        self.app.production.show('batch_video')
        self.root.update()
        self.close_window()

    def test_close_with_service_page(self):
        self.app.voice_settings()
        self.app.production.manage_services(self.app.voice_dialog)
        self.root.update()
        self.close_window()

    def test_close_cancels_running_narration_and_releases_lock(self):
        environment=patch.dict('os.environ',EBOOK2MP4_VOICE_HOME=str(self.folder/'voice-cache'))
        environment.start()
        self.addCleanup(environment.stop)
        flow,batch=self.app.flow,self.app.batch_id
        with patch('edge_tts.list_voices',new=AsyncMock(return_value=voice_fixture.VOICES)):
            refresh=flow.start_voice_refresh()
            self.assertTrue(refresh.wait(5))
        flow.save_voice_settings('zh-TW-TestNeural',batch_id=batch)
        flow.confirm_reading(batch)
        self.app.narration()
        page=self.app.narration_dialog
        deadline=time.monotonic()+5
        while page.check_job is not None and time.monotonic()<deadline:
            self.root.update();time.sleep(.01)
        waiting=threading.Event()
        class Service:
            def __init__(self,*args,**kwargs): pass
            async def stream(self):
                waiting.set()
                await asyncio.sleep(3600)
                yield {}
        with patch('edge_tts.Communicate',Service):
            page.start_button.invoke()
            job=page.job
            self.assertIsNotNone(job)
            self.assertTrue(waiting.wait(5))
            self.close_window()
            self.assertTrue(job.wait(1))
            self.assertEqual(job.state['status'],'cancelled')
        self.assertFalse((flow.root/'.production.lock').exists())


if __name__=='__main__':
    unittest.main()
