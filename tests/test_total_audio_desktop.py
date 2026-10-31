"""Native journeys for shared book selection, saved order and local production."""
import time
import asyncio
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


if __name__ == '__main__':
    unittest.main()
