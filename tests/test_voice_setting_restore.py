"""Saved settings survive reopen; task recovery preserves immutable plans."""
import unittest
from unittest.mock import patch
import test_voice as fixture
from ebook2mp4.workflow import ProjectWorkflow, encode, digest, ProjectError
from ebook2mp4.narration import plan


class SettingsRecovery(unittest.TestCase):
    setUp = fixture.VoiceJourney.setUp
    refresh_voices = fixture.VoiceJourney.refresh_voices

    def make_run(self):
        self.refresh_voices()
        self.flow.save_voice_settings('zh-TW-TestNeural', batch_id=self.batch)
        self.flow.confirm_reading(self.batch)
        snapshot = plan(self.flow.reading_text(self.batch), self.flow.voice_settings(self.batch),
                        self.flow._batch(self.batch)['current_reading'], self.batch)
        path = f'batches/{self.batch}/recovery/plan.json'
        progress = f'batches/{self.batch}/recovery/progress.json'
        data = encode(snapshot)
        state = self.flow.state
        state['batches'][0]['narration_runs'] = [dict(id=snapshot['id'], path=path,
            sha256=digest(data), progress_path=progress)]
        self.flow._commit(state, [(path, data), (progress, encode(dict(status='cancelled', chunks=[])))])
        return snapshot, data

    def test_timestamp_voice_names_and_independent_records_survive_reopen(self):
        self.refresh_voices()
        self.flow.save_voice_settings('zh-TW-TestNeural', batch_id=self.batch)
        self.flow.save_voice_settings('en-US-TestNeural', '+20%', batch_id=self.batch)
        reopened = ProjectWorkflow.open(self.flow.root)
        sources = reopened.voice_setting_sources(self.batch)
        self.assertEqual(len(sources), 2)
        self.assertRegex(sources[0]['name'], r'^\d{4}/\d{2}/\d{2} \d{2}:\d{2} \(zh-TW-TestNeural\)$')
        self.assertNotEqual(sources[0]['id'], sources[1]['id'])
        self.assertEqual(sources[0]['settings']['rate'], '+0%')

    def test_restore_uses_task_snapshot_and_does_not_restore_changed_manuscript(self):
        snapshot, original = self.make_run()
        self.flow.save_voice_settings('en-US-TestNeural', '+20%', batch_id=self.batch)
        self.assertTrue(self.flow.narration_runs(self.batch)[0]['settings_changed'])
        self.flow.restore_narration_settings(self.batch, snapshot['id'])
        self.assertEqual(self.flow.voice_settings(self.batch), snapshot['settings'])
        self.assertFalse(self.flow.narration_runs(self.batch)[0]['stale'])
        self.flow.save_draft(self.batch, '已修改稿件。')
        self.flow.restore_narration_settings(self.batch, snapshot['id'])
        self.assertTrue(self.flow.narration_runs(self.batch)[0]['reading_changed'])
        self.assertEqual((self.flow.root / f'batches/{self.batch}/recovery/plan.json').read_bytes(), original)
        self.assertFalse((self.flow.root / '.production.lock').exists())

    def test_failed_restore_keeps_previous_settings_and_releases_lock(self):
        snapshot, _ = self.make_run()
        self.flow.save_voice_settings('en-US-TestNeural', batch_id=self.batch)
        previous = self.flow.voice_settings(self.batch)
        with patch.object(self.flow, '_commit', side_effect=ProjectError('儲存失敗')):
            with self.assertRaises(ProjectError):
                self.flow.restore_narration_settings(self.batch, snapshot['id'])
        self.assertEqual(self.flow.voice_settings(self.batch), previous)
        self.assertFalse((self.flow.root / '.production.lock').exists())
