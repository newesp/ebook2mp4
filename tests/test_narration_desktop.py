"""Production journeys through real Tk controls and the public workflow."""
import asyncio
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import AsyncMock, patch

from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow
import test_voice as fixture


class NarrationDesktop(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[1] / '.scratch/test-runs'
        base.mkdir(exist_ok=True, parents=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.env = patch.dict('os.environ', EBOOK2MP4_VOICE_HOME=str(self.path / 'cache'))
        self.env.start()
        self.addCleanup(self.env.stop)
        self.root, self.app = make_app()
        self.addCleanup(self.root.destroy)
        self.errors = []
        self.root.report_callback_exception = lambda *args: self.errors.append(args)
        self.flow = self.app.flow = ProjectWorkflow.create(self.path / 'book', '正式合成測試')
        source = self.path / 'source.txt'
        source.write_text('第一段。\n\nSecond paragraph 3.14.', encoding='utf-8')
        self.batch = self.app.batch_id = self.flow.import_txt(self.flow.inspect_txt(source))
        with patch('edge_tts.list_voices', new=AsyncMock(return_value=fixture.VOICES)):
            job = self.flow.start_voice_refresh()
            self.assertTrue(job.wait(5))
        self.flow.save_voice_settings('zh-TW-TestNeural', batch_id=self.batch)
        self.app.refresh()
        self.app.narration()
        self.dialog = self.app.narration_dialog
        self.root.update()
        deadline=time.monotonic()+5
        while self.dialog.check_job is not None and time.monotonic()<deadline:
            self.root.update()
            time.sleep(.02)
        self.addCleanup(lambda: self.dialog.close() if self.dialog.winfo_exists() else None)

    def poll(self):
        deadline = time.monotonic() + 15
        while (self.dialog.job is not None or self.dialog.check_job is not None) and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.02)
        self.root.update()
        self.assertIsNone(self.dialog.job, self.dialog.status.cget('text'))
        self.assertEqual(self.errors, [])

    def test_confirm_consent_produce_export_play_and_small_window(self):
        self.dialog.consent.set(True)
        self.dialog.start_button.invoke()
        self.assertIn('確認', self.dialog.status.cget('text'))
        self.flow.confirm_reading(self.batch)
        self.dialog.reload_button.invoke()
        self.assertTrue(self.dialog.consent.get())
        self.dialog.consent.set(False)
        self.dialog.start_button.invoke()
        self.assertIn('勾選', self.dialog.status.cget('text'))
        self.dialog.consent.set(True)
        audio = fixture.VoiceJourney.audio(self)
        class Service:
            def __init__(self, *args, **kwargs): pass
            async def stream(self): yield dict(type='audio', data=audio)
        with patch('edge_tts.Communicate', Service):
            self.dialog.start_button.invoke()
            self.poll()
        self.assertIn('完成並保存', self.dialog.status.cget('text'))
        destination = self.path / '另存成品'
        with patch('ebook2mp4.narration_desktop.filedialog.asksaveasfilename', return_value=str(destination)):
            self.dialog.export_button.invoke()
        self.assertTrue((destination / 'narration.srt').is_file())
        with patch('ebook2mp4.voice_media.ctypes.WinDLL') as api:
            api.return_value.mciSendStringW.return_value = 0
            self.dialog.play_button.invoke()
            self.dialog.stop_button.invoke()
        with patch('ebook2mp4.narration_desktop.os.startfile') as open_folder:
            self.dialog.folder_button.invoke()
            self.assertEqual(open_folder.call_args.args[0], self.flow.narration_path(self.batch).parent)
        self.root.state('normal')
        self.root.geometry('1040x640+20+20')
        self.root.update()
        for control in (self.dialog.start_button, self.dialog.cancel_button, self.dialog.play_button,
                        self.dialog.export_button, self.dialog.folder_button, self.dialog.consent_control):
            if not control.winfo_ismapped():
                continue
            self.assertGreaterEqual(control.winfo_rootx(), self.dialog.winfo_rootx())
            self.assertLessEqual(control.winfo_rootx()+control.winfo_width(), self.dialog.winfo_rootx()+self.dialog.winfo_width())
            self.assertLessEqual(control.winfo_rooty()+control.winfo_height(), self.dialog.winfo_rooty()+self.dialog.winfo_height())
        self.flow.save_voice_settings('zh-TW-TestNeural','+10%',batch_id=self.batch)
        self.dialog.load_runs()
        self.poll()
        self.assertFalse(self.dialog.start_button.instate(['disabled']))
        self.assertIn('核對',self.dialog.start_button.cget('text'))
        self.dialog.start_button.invoke()
        self.assertIsNone(self.dialog.job)
        self.assertTrue(self.dialog.consent.get())
        self.dialog.consent.set(True)
        class Offline(Service):
            async def stream(self):
                raise OSError('offline fixture')
                yield
        with patch('edge_tts.Communicate',Offline):
            self.dialog.start_button.invoke()
            self.poll()
        self.dialog.details.selection_set(self.dialog.details.get_children()[0])
        self.root.update()
        self.assertIn('第 1 塊',self.dialog.status.cget('text'))

    def test_compact_page_has_no_outer_scroll_and_footer_stays_visible(self):
        import tkinter as tk
        self.root.state('normal')
        self.root.geometry('1040x640')
        self.root.update()
        def children(widget):
            for child in widget.winfo_children():
                yield child
                yield from children(child)
        self.assertFalse(any(isinstance(w,tk.Canvas) for w in children(self.dialog)))
        self.assertFalse(self.dialog.source_info.winfo_ismapped())
        for widget in (self.dialog.details,self.dialog.start_button,self.dialog.consent_control,self.dialog.folder_button):
            self.assertTrue(widget.winfo_ismapped())
            self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),self.root.winfo_rooty()+self.root.winfo_height())
        self.dialog.info_button.invoke()
        self.root.update()
        self.assertTrue(self.dialog.source_info.winfo_ismapped())
        self.assertFalse(self.dialog.outgoing.winfo_ismapped())
        self.dialog.info_button.invoke()
        self.root.geometry('1360x800')
        self.root.update()
        self.assertGreaterEqual(self.dialog.details.winfo_height(),150)

    def test_close_waits_for_cancel_and_changed_source_requires_new_consent(self):
        self.flow.confirm_reading(self.batch)
        self.dialog.reload_button.invoke()
        self.dialog.consent.set(True)
        self.flow.save_voice_settings('en-US-TestNeural', batch_id=self.batch)
        self.dialog.start_button.invoke()
        self.assertTrue(self.dialog.consent.get())
        self.assertIn('變更', self.dialog.status.cget('text'))
        self.dialog.consent.set(True)
        class Waiting:
            def __init__(self, *args, **kwargs): pass
            async def stream(self):
                await asyncio.sleep(60)
                yield
        with patch('edge_tts.Communicate', Waiting):
            self.dialog.start_button.invoke()
            job = self.dialog.job
            self.dialog.close()
            deadline = time.monotonic() + 5
            while self.app.narration_dialog is not None and time.monotonic() < deadline:
                self.root.update()
                time.sleep(.02)
            self.assertIsNone(self.app.narration_dialog)
            self.assertTrue(job.wait(0))
            self.assertEqual(job.state['status'], 'cancelled')
            self.assertFalse((self.flow.root / '.production.lock').exists())
            self.assertIsNone(self.dialog.timer)
        self.assertEqual(self.errors, [])
