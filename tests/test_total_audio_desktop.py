"""Native journeys for shared book selection, saved order and local production."""
import time
import asyncio
import threading
from pathlib import Path
import tkinter as tk
import unittest
from unittest.mock import patch

from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow
import test_total_audio as fixture


class TotalAudioDesktop(unittest.TestCase):
    prepare = fixture.TotalAudioJourney.prepare
    refresh_voices = fixture.TotalAudioJourney.refresh_voices
    audio = fixture.TotalAudioJourney.audio
    merge = fixture.TotalAudioJourney.merge

    def setUp(self):
        fixture.TotalAudioJourney.setUp(self)
        self.ids = self.prepare(2)
        self.root, self.app = make_app()
        self.app.flow, self.app.batch_id = self.flow, self.batch
        self.app.refresh()
        self.root.update()
        self.addCleanup(self.shutdown)

    def shutdown(self):
        try:
            self.app.close()
            deadline = time.monotonic()+10
            while self.root.winfo_exists() and time.monotonic()<deadline:
                self.root.update()
                time.sleep(.02)
        except tk.TclError:
            pass

    def wait_page(self, page):
        deadline = time.monotonic()+20
        while (page.check_job is not None or page.job is not None) and time.monotonic()<deadline:
            self.root.update()
            time.sleep(.02)
        self.root.update()
        self.assertIsNone(page.check_job)
        self.assertIsNone(page.job, page.status.cget('text'))

    def test_gui_selection_save_reorder_and_production_stay_in_main_window(self):
        self.app.total_audio()
        page = self.app.production.current
        self.wait_page(page)
        self.assertIs(page.winfo_toplevel(), self.root)
        self.assertEqual(page.selected, [])
        page.table.selection_set(self.ids[0])
        page.toggle_selected()
        page.table.selection_set(self.ids[1])
        page.toggle_selected()
        page.up_button.invoke()
        page.save_button.invoke()
        reopened = ProjectWorkflow.open(self.flow.root)
        self.assertEqual([s['batch_id'] for s in reopened.assembly_settings()['sources']], self.ids[::-1])
        page.back_button.invoke()
        self.app.production.assembly_tab.invoke()
        self.assertIs(self.app.production.current, page)
        self.wait_page(page)
        with patch('edge_tts.Communicate', side_effect=AssertionError('no TTS')):
            page.start_button.invoke()
            self.wait_page(page)
        self.assertEqual(self.flow.total_audio()['duration_ms'], 900)
        self.assertIn('目前總成品', page.result_info.cget('text'))
        self.assertFalse(page.play_button.instate(['disabled']))
        with patch('ebook2mp4.voice_media.PreviewPlayer._send', return_value='playing'):
            page.play_button.invoke()
            self.wait_page(page)
            self.assertIn('正在播放', page.status.cget('text'))
            page.stop_button.invoke()
            self.assertIn('已停止', page.status.cget('text'))
            self.assertIsNone(page.player.alias)

    def test_main_window_busy_guard_invalid_source_and_minimum_size(self):
        self.app.total_audio()
        page = self.app.production.current
        self.wait_page(page)
        self.root.state('normal')
        self.root.geometry('1040x640')
        self.root.update()
        for widget in (page.start_button, page.save_button, page.back_button, page.play_button,
                       page.export_button, page.folder_button, page.pause_control, page.info_button):
            self.assertGreaterEqual(widget.winfo_rootx(), self.root.winfo_rootx())
            self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(), self.root.winfo_rootx()+self.root.winfo_width())
            self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(), self.root.winfo_rooty()+self.root.winfo_height())
        self.assertGreater(page.table.winfo_height(), 60)
        page.table.selection_set(self.ids[0])
        page.toggle_selected()
        page.save_button.invoke()
        self.wait_page(page)
        self.flow.save_draft(self.batch, '新的等待中合成範例。')
        self.flow.confirm_reading(self.batch)
        class Waiting:
            def __init__(self, *args, **kwargs): pass
            async def stream(self):
                await asyncio.sleep(60)
                yield
        with patch('edge_tts.Communicate', Waiting):
            job = self.flow.start_narration(self.batch)
            try:
                deadline = time.monotonic()+2
                while not page.save_button.instate(['disabled']) and time.monotonic()<deadline:
                    self.root.update()
                    time.sleep(.02)
                self.assertTrue(page.save_button.instate(['disabled']))
                self.assertTrue(page.start_button.instate(['disabled']))
                self.assertIn('另有製作任務', page.status.cget('text'))
            finally:
                job.cancel()
                self.assertTrue(job.wait(10))
                self.flow.discard_narration(job)
        deadline = time.monotonic()+2
        while page.production_busy and time.monotonic()<deadline:
            self.root.update()
            time.sleep(.02)
        self.wait_page(page)
        self.assertIn('待更新', page.table.set(self.batch, 'status'))
        self.assertTrue(page.start_button.instate(['disabled']))
        page.table.selection_set(self.batch)
        page.toggle_selected()
        page.table.selection_set(self.ids[1])
        page.toggle_selected()
        self.assertFalse(page.start_button.instate(['disabled']))
        page.info_button.invoke()
        self.assertTrue(page.info_open)
        page.info_button.invoke()
        self.assertEqual(page.selected, [self.ids[1]])

    def test_source_reading_does_not_block_main_window_cancellation(self):
        self.app.total_audio()
        page = self.app.production.current
        self.wait_page(page)
        page.table.selection_set(self.batch)
        page.toggle_selected()
        source = self.flow.narration_path(self.batch)
        opened, proceed, ui_event = threading.Event(), threading.Event(), threading.Event()
        original = Path.open
        main_thread = threading.get_ident()
        readers = []
        class SlowFile:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self
            def __exit__(self, *args): self.stream.close()
            def read(self, *args):
                readers.append(threading.get_ident())
                opened.set()
                proceed.wait(5)
                return self.stream.read(*args)
        def slow_open(path, *args, **kwargs):
            stream = original(path, *args, **kwargs)
            return SlowFile(stream) if path == source else stream
        with patch.object(Path, 'open', slow_open):
            try:
                page.start_button.invoke()
                self.assertTrue(opened.wait(5))
                self.root.after(0, ui_event.set)
                self.root.update()
                self.assertTrue(ui_event.is_set())
                self.assertNotIn(main_thread, readers)
                page.cancel_button.invoke()
                proceed.set()
                self.wait_page(page)
            finally:
                proceed.set()
        self.assertEqual(self.flow.total_audio_runs()[-1]['progress']['status'], 'cancelled')
        self.assertFalse((self.flow.root/'.production.lock').exists())

    def test_leaving_page_cancels_pending_playback_verification(self):
        self.flow.save_assembly_settings(self.ids)
        self.merge()
        self.app.total_audio()
        page = self.app.production.current
        self.wait_page(page)
        source = self.flow.total_audio_path()
        original = Path.open
        opened, proceed = threading.Event(), threading.Event()
        class SlowFile:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self
            def __exit__(self, *args): self.stream.close()
            def read(self, *args):
                opened.set()
                proceed.wait(5)
                return self.stream.read(*args)
        def slow_open(path, *args, **kwargs):
            stream = original(path, *args, **kwargs)
            return SlowFile(stream) if path == source else stream
        with patch.object(Path, 'open', slow_open), patch('ebook2mp4.voice_media.PreviewPlayer.play') as play:
            try:
                page.play_button.invoke()
                self.assertTrue(opened.wait(5))
                self.app.voice_settings()
                proceed.set()
                self.wait_page(page)
                play.assert_not_called()
                self.assertIsNone(page.player.alias)
            finally:
                proceed.set()

    def test_damaged_old_total_does_not_block_rebuilding_from_valid_batches(self):
        self.flow.save_assembly_settings(self.ids)
        self.merge()
        old = self.flow.total_audio_path()
        old.unlink()
        self.app.total_audio()
        page = self.app.production.current
        self.wait_page(page)
        self.assertIn('舊總成品', page.status.cget('text'))
        self.assertFalse(page.start_button.instate(['disabled']))
        self.assertTrue(page.play_button.instate(['disabled']))
        page.start_button.invoke()
        self.wait_page(page)
        self.assertTrue(self.flow.total_audio_path().is_file())
        self.assertIn('目前總成品', page.result_info.cget('text'))


if __name__ == '__main__':
    unittest.main()
