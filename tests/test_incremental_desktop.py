"""T13 extends the existing Tk pages without adding workflow windows."""
import unittest
import time
from unittest.mock import patch

import test_voice_desktop as fixture
from ebook2mp4.workflow import ProjectWorkflow


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

    def test_incremental_plan_and_stale_product_then_offline_reassembly(self):
        self.choose()
        flow, batch = self.app.flow, self.app.batch_id
        flow.save_voice_settings('zh-TW-TestNeural', batch_id=batch)
        flow.confirm_reading(batch)
        audio = fixture.fixture.VoiceJourney.audio(self)
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
        page.consent.set(False)
        with patch('edge_tts.Communicate', side_effect=AssertionError('offline means no TTS')):
            page.start_button.invoke()
            wait()
        self.assertIn('目前成品', page.result_info.cget('text'))
        self.assertEqual(flow.narration(batch)['duration_ms'], 2200)
