"""Native save/load/navigation acceptance for the single save control."""
import unittest
from pathlib import Path
import test_voice_desktop as fixture


class SavedSettingsUI(unittest.TestCase):
    setUp = fixture.VoiceDesktop.setUp
    poll = fixture.VoiceDesktop.poll
    choose = fixture.VoiceDesktop.choose

    def test_production_restore_preserves_selected_task(self):
        import time
        from ebook2mp4.narration import plan
        from ebook2mp4.workflow import encode, digest
        self.choose()
        d = self.dialog
        self.assertTrue(d.save())
        flow, batch = self.app.flow, self.app.batch_id
        flow.confirm_reading(batch)
        snapshot = plan(flow.reading_text(batch), flow.voice_settings(batch), flow._batch(batch)['current_reading'], batch)
        data = encode(snapshot)
        path, progress = f'batches/{batch}/recovery/plan.json', f'batches/{batch}/recovery/progress.json'
        state = flow.state
        state['batches'][0]['narration_runs'] = [dict(id=snapshot['id'], path=path, sha256=digest(data), progress_path=progress)]
        flow._commit(state, [(path, data), (progress, encode(dict(status='cancelled', chunks=[])))])
        flow.save_voice_settings('en-US-TestNeural', '+20%', batch_id=batch)
        d.load_settings()
        self.app.narration()
        page = self.app.narration_dialog
        def settle():
            deadline = time.monotonic()+10
            while page.check_job is not None and time.monotonic() < deadline:
                self.root.update()
                time.sleep(.02)
            self.root.update()
            self.assertIsNone(page.check_job)
        settle()
        page.consent.set(False)
        self.assertTrue(page.run['settings_changed'])
        page.restore_button.invoke()
        settle()
        self.assertEqual(page.run['snapshot']['id'], snapshot['id'])
        self.assertFalse(page.run['stale'])
        self.assertFalse(page.consent.get())
        self.assertEqual(d.current_settings(), snapshot['settings'])
        self.assertEqual(flow.voice_settings(batch), snapshot['settings'])

    def test_one_save_loads_complete_settings_and_blocks_unsaved_navigation(self):
        self.choose()
        d = self.dialog
        d.rate.set('+20%')
        d.sentence_pause.set('200')
        d.paragraph_pause.set('800')
        self.root.update()
        self.assertEqual(str(d.produce_button.cget('state')), 'disabled')
        self.assertTrue(d.save())
        self.assertEqual(d.save_button.cget('text'), '儲存設定')
        self.assertEqual(d.produce_button.cget('text'), '前往音訊製做 →')
        self.assertEqual(str(d.produce_button.cget('state')), 'normal')
        self.assertRegex(d.setting_sources[0]['name'], r'\d{4}/\d{2}/\d{2} \d{2}:\d{2} \(zh-TW-TestNeural\)')
        d.rate.set('-20%')
        self.assertTrue(d.save())
        d.source_control.current(0)
        d.load_selected_settings()
        self.root.update()
        self.assertEqual(d.current_settings()['rate'], '+20%')
        self.assertEqual(d.current_settings()['sentence_pause_ms'], 200)
        self.assertEqual(str(d.produce_button.cget('state')), 'disabled')
        self.assertTrue(d.save())
        d.consent.set(False)
        self.app.narration()
        self.app.voice_settings()
        self.root.update()
        self.assertFalse(d.consent.get())
        self.root.state('normal')
        self.root.geometry('1040x740+0+0')
        self.root.update()
        for control in (d.source_button, d.save_button, d.produce_button):
            self.assertLessEqual(control.winfo_rootx()+control.winfo_width(), self.app.winfo_rootx()+self.app.winfo_width())
            self.assertLessEqual(control.winfo_rooty()+control.winfo_height(), self.app.winfo_rooty()+self.app.winfo_height())
        from PIL import ImageGrab
        ImageGrab.grab(window=self.root.winfo_id()).save(
            Path(__file__).resolve().parents[1] / 'docs/verification/voice-settings-native.png')
