"""Local formal production with a real Windows protocol worker and real media tools."""
import os
import subprocess
import time

import test_kokoro_lifecycle
from ebook2mp4.workflow import ProjectError, ProjectWorkflow


class LocalNarration(test_kokoro_lifecycle.WorkerLifecycle):
    test_expired_timer_cannot_unload_a_newer_preview = None
    test_busy_idle_cancel_failure_and_retry_release_process_tree = None

    def test_local_cancel_corrupt_cache_resume_and_pause_reuse(self):
        text = '第一段。\n\nslow。\n\n最後一段。'
        self.flow.save_draft(self.batch, text)
        self.flow.confirm_reading(self.batch)
        job = self.flow.start_narration(self.batch, allow_network=False)
        try:
            deadline = time.monotonic()+10
            while self.flow.local_voice_status()['phase'] != 'fixture-slow':
                self.assertFalse(job.wait(.02), job.state)
                self.assertLess(time.monotonic(), deadline)
            self.assertEqual(job.state['completed'], 1)
            job.cancel()
            self.assertTrue(job.wait(10))
        finally:
            self.flow.discard_narration(job)
        reopened = ProjectWorkflow.open(self.flow.root)
        run, = reopened.narration_runs(self.batch)
        self.assertEqual(run['reusable'], 1)
        cache = reopened.root/'batches'/self.batch/'voice-blocks'
        target, = cache.glob('*.wav')
        target.write_bytes(target.read_bytes()[:45])
        self.assertEqual(reopened.narration_runs(self.batch)[0]['reusable'], 0)
        job = reopened.resume_narration(self.batch, run['snapshot']['id'], allow_network=False)
        try:
            self.wait_for(job, 20)
            self.assertEqual(job.state['status'], 'completed', job.state)
            product = reopened.finish_narration(job)
            self.assertFalse(any(chunk['reused'] for chunk in product['chunks']))
            self.assertEqual(product['text'], text)
        finally:
            if reopened._narration_job is job:
                reopened.discard_narration(job)
        settings = reopened.voice_settings(self.batch)
        reopened.save_voice_settings('zf_001', batch_id=self.batch, settings_override=settings,
                                     paragraph_pause_ms=800)
        job = reopened.start_narration(self.batch, allow_network=False)
        try:
            self.wait_for(job, 15)
            changed = reopened.finish_narration(job)
            self.assertTrue(all(chunk['reused'] for chunk in changed['chunks']))
            self.assertEqual(changed['duration_ms']-product['duration_ms'], 600)
            self.assertIn('00:00:01,000 --> 00:00:01,200',
                          reopened.narration_path(self.batch, 'srt').read_text(encoding='utf-8'))
        finally:
            if reopened._narration_job is job:
                reopened.discard_narration(job)
        from ebook2mp4.voice_media import cached_block
        self.assertIsNotNone(cached_block('第一段。', settings, cache))
        for field, value in (('model', 'another-model-revision'),
                             ('package', 'another-package-content'),
                             ('processing', 'another-preprocessing-version'),
                             ('voice', 'another-voice'), ('rate', '+10%'),
                             ('provider', 'edge-tts')):
            with self.subTest(changed=field):
                self.assertIsNone(cached_block('第一段。', dict(settings, **{field: value}), cache))
        for rate in ('-10%', '+10%'):
            reopened.save_voice_settings('zf_001', rate, batch_id=self.batch, settings_override=settings)
            self.assertEqual(reopened.inspect_narration(self.batch)['reusable'], 0)
        reopened.unload_local_voice()

    def test_confirmed_snapshot_local_chunks_cues_and_conflicts(self):
        with self.assertRaisesRegex(ProjectError, '確認'):
            self.flow.start_narration(self.batch, allow_network=False)
        text = 'slow。\n\n' + '臺灣繁體與 English 混讀測試。'*12 + '\n\n最後一段。'
        self.flow.save_draft(self.batch, text)
        self.flow.confirm_reading(self.batch)
        settings = self.flow.voice_settings(self.batch)
        job = self.flow.start_narration(self.batch, allow_network=False)
        try:
            deadline = time.monotonic()+10
            while self.flow.local_voice_status()['phase'] != 'fixture-slow':
                self.assertFalse(job.wait(.02), job.state)
                self.assertLess(time.monotonic(), deadline)
            with self.assertRaises(ProjectError):
                self.flow.remove_voice_package(settings['package'])
            preview = self.preview('concurrent')
            self.wait_for(preview, 5)
            self.assertEqual(preview.state['status'], 'failed')
            self.flow.discard_voice_preview(preview)
            self.flow.save_draft(self.batch, '製作時修改的新版。')
            self.flow.save_voice_settings('zf_001', '+20%', batch_id=self.batch, settings_override=settings)
            self.wait_for(job, 20)
            self.assertEqual(job.state['status'], 'completed', job.state)
            product = self.flow.finish_narration(job)
            self.assertEqual(product['text'], text)
            self.assertEqual(product['settings'], settings)
            self.assertGreater(len(product['chunks']), 3)
            self.assertEqual(''.join(c['text']+c['separator_after'] for c in product['chunks']), text)
            self.assertTrue(all(len(__import__('html').escape(c['text'], quote=False).encode()) <= 240
                                for c in product['chunks']))
            srt = self.flow.narration_path(self.batch, 'srt').read_text(encoding='utf-8')
            self.assertIn('00:00:00,000 --> 00:00:00,200\nslow。', srt)
            self.assertIn('00:00:00,700 --> 00:00:00,900', srt)
            self.assertEqual(srt.count('臺灣繁體'), 12)
            frames = subprocess.check_output([os.environ['EBOOK2MP4_FFMPEG'], '-v', 'error', '-i',
                str(self.flow.narration_path(self.batch)), '-f', 's16le', '-ar', '24000', '-ac', '1', '-'])
            self.assertAlmostEqual(len(frames)/48, product['duration_ms'], delta=25)
            self.assertEqual(self.flow.local_voice_status()['loads'], 1)
            reopened = ProjectWorkflow.open(self.flow.root)
            self.assertEqual(reopened.narration(self.batch)['id'], product['id'])
            self.assertEqual(reopened.texts(self.batch)[1], '製作時修改的新版。')
        finally:
            if self.flow._narration_job is job:
                self.flow.discard_narration(job)
