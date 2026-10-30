"""T13 extends the existing Tk pages without adding workflow windows."""
import unittest
import time
import asyncio
from unittest.mock import patch

import test_voice_desktop as fixture
from ebook2mp4.workflow import ProjectWorkflow
import test_voice as voice_fixture


class IncrementalDesktop(unittest.TestCase):
    setUp = fixture.VoiceDesktop.setUp
    poll = fixture.VoiceDesktop.poll
    choose = fixture.VoiceDesktop.choose

    def test_saved_defaults_apply_to_selected_batch_in_same_window(self):
        self.choose()
        d = self.dialog
        d.scope.set('全書預設')
        d.scope_control.event_generate('<<ComboboxSelected>>')
        d.voice.set('en-US-TestNeural')
        d.save_button.invoke()
        d.apply_defaults_button.invoke()
        self.root.update()
        page = self.app.production.current
        self.assertIs(page.winfo_toplevel(), self.root)
        self.assertFalse(page.selected)
        page.table.selection_set(self.app.batch_id)
        page.toggle_selected()
        page.apply_button.invoke()
        reopened = ProjectWorkflow.open(self.app.flow.root)
        self.assertEqual(reopened.voice_settings(self.app.batch_id)['voice'], 'en-US-TestNeural')
        page.back_button.invoke()
        self.assertIs(self.app.production.current, d)
        self.assertEqual(d.scope.get(), '全書預設')
        d.apply_defaults_button.invoke()
        self.assertEqual(self.app.production.current.selected, {self.app.batch_id})
        page = self.app.production.current
        page.table.selection_set(self.app.batch_id)
        page.table.event_generate('<ButtonRelease-1>', x=10, y=5)
        self.root.update()
        self.assertEqual(page.selected, {self.app.batch_id})
        page.back_button.invoke()
        d.rate.set('+10%')
        d.save_button.invoke()
        d.apply_defaults_button.invoke()
        page = self.app.production.current
        self.assertIn('+10%', page.summary.cget('text'))
        self.assertEqual(page.selected, {self.app.batch_id})
        page.back_button.invoke()
        self.app.flow.save_voice_settings('zh-TW-TestNeural', batch_id=self.app.batch_id)
        d.apply_defaults_button.invoke()
        self.assertIn('zh-TW-TestNeural', page.table.set(self.app.batch_id, 'settings'))

    def test_incremental_plan_and_stale_product_then_offline_reassembly(self):
        self.choose()
        flow, batch = self.app.flow, self.app.batch_id
        flow.save_voice_settings('zh-TW-TestNeural', batch_id=batch)
        flow.confirm_reading(batch)
        audio = voice_fixture.VoiceJourney.audio(self)
        class Service:
            def __init__(self, *args, **kwargs): pass
            async def stream(self): yield dict(type='audio', data=audio)
        with patch('edge_tts.Communicate', Service):
            job = flow.start_narration(batch)
            self.assertTrue(job.wait(20))
            flow.finish_narration(job)
        flow.save_voice_settings('zh-TW-TestNeural', batch_id=batch, paragraph_pause_ms=800)
        self.app.narration()
        page = self.app.narration_dialog
        self.addCleanup(lambda: page.close() if page.winfo_exists() else None)
        def wait():
            deadline = time.monotonic()+15
            while (page.job is not None or page.check_job is not None) and time.monotonic()<deadline:
                self.root.update()
                time.sleep(.02)
            self.assertIsNone(page.job)
            self.assertIsNone(page.check_job)
        wait()
        self.assertIn('待更新', page.result_info.cget('text'))
        self.assertIn('可重用 3', page.run_summary.cget('text'))
        self.assertIn('重新組裝', page.start_button.cget('text'))
        self.assertTrue(page.consent.get())
        from ebook2mp4.voice import cache_path
        cache_path().unlink()
        with patch('edge_tts.Communicate', side_effect=AssertionError('offline means no TTS')):
            page.start_button.invoke()
            wait()
        self.assertIn('目前成品', page.result_info.cget('text'))
        self.assertEqual(flow.narration(batch)['duration_ms'], 2200)
        previous = flow.narration(batch)['id']
        page.recheck()
        wait()
        next((flow.root/'batches'/batch/'voice-blocks').glob('*.wav')).unlink()
        with patch('edge_tts.Communicate', side_effect=AssertionError('no silent network fallback')):
            page.start_button.invoke()
            wait()
        self.assertEqual(flow.narration(batch)['id'], previous)
        self.assertEqual(flow.narration_runs(batch)[-1]['progress']['status'], 'failed')

    def test_background_production_disables_defaults_and_cancel_releases_controls(self):
        self.choose()
        d, flow, batch = self.dialog, self.app.flow, self.app.batch_id
        flow.save_voice_settings('zh-TW-TestNeural', batch_id=batch)
        flow.save_voice_settings('zh-TW-TestNeural')
        flow.confirm_reading(batch)
        d.scope.set('全書預設')
        d.load_settings()
        d.apply_defaults_button.invoke()
        page = self.app.production.current
        page.table.selection_set(batch)
        page.toggle_selected()
        class Waiting:
            def __init__(self, *args, **kwargs): pass
            async def stream(self):
                await asyncio.sleep(60)
                yield
        with patch('edge_tts.Communicate', Waiting):
            job = flow.start_narration(batch)
            try:
                deadline = time.monotonic()+1
                while time.monotonic()<deadline:
                    self.root.update()
                    time.sleep(.02)
                self.assertTrue(page.apply_button.instate(['disabled']))
                page.back_button.invoke()
                self.assertTrue(d.apply_defaults_button.instate(['disabled']))
            finally:
                job.cancel()
                self.assertTrue(job.wait(5))
                flow.discard_narration(job)
        deadline = time.monotonic()+1
        while time.monotonic()<deadline:
            self.root.update()
            time.sleep(.02)
        self.assertFalse(d.apply_defaults_button.instate(['disabled']))
