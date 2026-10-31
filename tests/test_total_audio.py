"""Total-audio journeys at ProjectWorkflow, with real FFmpeg and synthetic speech."""
import os
import json
import hashlib
from pathlib import Path
import subprocess
import sys
import unittest
import wave
from unittest.mock import patch

import test_voice as fixture
from ebook2mp4.workflow import ProjectError, ProjectWorkflow


class TotalAudioJourney(unittest.TestCase):
    setUp = fixture.VoiceJourney.setUp
    refresh_voices = fixture.VoiceJourney.refresh_voices
    audio = fixture.VoiceJourney.audio

    def prepare(self, count=1, audio=None):
        self.refresh_voices()
        audio = self.audio() if audio is None else audio
        ids = [self.batch]
        for _ in range(count-1):
            ids.append(self.flow.import_txt(self.flow.inspect_txt(self.source)))
        class Service:
            def __init__(self, *args, **kwargs): pass
            async def stream(self): yield dict(type='audio', data=audio)
        with patch('edge_tts.Communicate', Service):
            for index, batch in enumerate(ids):
                self.flow.save_voice_settings('zh-TW-TestNeural', batch_id=batch)
                self.flow.save_draft(batch, f'第 {index+1} 批。')
                self.flow.confirm_reading(batch)
                job = self.flow.start_narration(batch)
                self.assertTrue(job.wait(15), job.state)
                self.flow.finish_narration(job)
        return ids

    def merge(self):
        with patch('edge_tts.Communicate', side_effect=AssertionError('merging must not call TTS')) as tts:
            job = self.flow.start_total_audio()
            self.assertTrue(job.wait(20), job.state)
            self.assertEqual(job.state['status'], 'completed', job.state)
            result = self.flow.finish_total_audio(job)
            tts.assert_not_called()
        return result

    def pcm(self, path):
        return subprocess.check_output([os.environ['EBOOK2MP4_FFMPEG'], '-v', 'error', '-i', str(path),
                                      '-ac', '1', '-ar', '24000', '-f', 's16le', '-'])

    def test_selection_order_and_versions_survive_reopen(self):
        a, b = self.prepare(2)
        self.assertEqual(self.flow.assembly_settings()['sources'], [])
        self.flow.save_assembly_settings([b, a])
        reopened = ProjectWorkflow.open(self.flow.root)
        settings = reopened.assembly_settings()
        self.assertEqual(settings['pause_ms'], 500)
        self.assertEqual([s['batch_id'] for s in settings['sources']], [b, a])
        self.assertEqual(settings['sources'][0]['product_id'], reopened.narration(b)['id'])
        self.assertEqual(settings['sources'][0]['mp3'], reopened.narration(b)['mp3'])
        self.assertEqual(settings['sources'][0]['srt'], reopened.narration(b)['srt'])
        self.assertEqual(reopened.total_audio(), None)

    def test_one_two_three_batches_use_decoded_timeline_and_no_tts(self):
        ids = self.prepare(3)
        for count, milliseconds, last_start in ((1, 200, '00:00:00,000'),
                                                (2, 900, '00:00:00,700'),
                                                (3, 1600, '00:00:01,400')):
            with self.subTest(count=count):
                self.flow.save_assembly_settings(ids[:count])
                result = self.merge()
                pcm = self.pcm(self.flow.total_audio_path())
                self.assertEqual(len(pcm) // 48, milliseconds)
                self.assertEqual(result['duration_ms'], milliseconds)
                text = self.flow.total_audio_path('srt').read_text(encoding='utf-8')
                self.assertIn(f'{last_start} --> ', text)
                self.assertEqual(text.count(' --> '), count)
                self.assertTrue(text.endswith(f'第 {count} 批。\n\n'))
        reopened = ProjectWorkflow.open(self.flow.root)
        self.assertFalse(reopened.total_audio()['stale'])
        destination = self.path / 'total-export'
        reopened.export_total_audio(destination)
        self.assertEqual((destination/'total.mp3').read_bytes(), reopened.total_audio_path().read_bytes())
        self.assertEqual((destination/'total.srt').read_bytes(), reopened.total_audio_path('srt').read_bytes())
        with self.assertRaises(ProjectError):
            reopened.export_total_audio(destination)

    def test_only_selected_sources_and_shared_settings_invalidate_total(self):
        a, b = self.prepare(2)
        self.flow.save_assembly_settings([a])
        previous = self.merge()
        old_audio = self.flow.total_audio_path().read_bytes()
        self.flow.save_draft(b, '未選批次修改。')
        self.assertFalse(self.flow.total_audio()['stale'])
        self.flow.save_assembly_settings([a], pause_ms=800)
        self.assertTrue(self.flow.total_audio()['stale'])
        self.assertEqual(self.flow.total_audio_path().read_bytes(), old_audio)
        self.flow.save_assembly_settings([a], pause_ms=500)
        self.assertFalse(self.flow.total_audio()['stale'])
        self.flow.save_draft(a, '已選批次修改。')
        reopened = ProjectWorkflow.open(self.flow.root)
        self.assertTrue(reopened.total_audio()['stale'])
        self.assertEqual(reopened.total_audio()['id'], previous['id'])
        with self.assertRaises(ProjectError):
            reopened.start_total_audio()
        invalid = next(row for row in reopened.inspect_assembly() if row['batch_id'] == a)
        self.assertFalse(invalid['valid'])

    def test_cancel_conflict_and_disk_shortage_preserve_previous_product(self):
        ids = self.prepare(1)
        self.flow.save_assembly_settings(ids)
        previous = self.merge()
        mp3 = self.flow.total_audio_path().read_bytes()
        job = self.flow.start_total_audio()
        other = ProjectWorkflow.open(self.flow.root)
        try:
            with self.assertRaisesRegex(ProjectError, '任務'):
                other.start_total_audio()
            with self.assertRaisesRegex(ProjectError, '任務'):
                other.start_narration(self.batch)
            with self.assertRaisesRegex(ProjectError, '任務'):
                self.flow.save_assembly_settings(ids)
        finally:
            job.cancel()
            self.assertTrue(job.wait(10), job.state)
            self.flow.discard_total_audio(job)
        self.assertEqual(self.flow.total_audio_runs()[-1]['progress']['status'], 'cancelled')
        from collections import namedtuple
        usage = namedtuple('usage', 'total used free')
        with patch('shutil.disk_usage', return_value=usage(100, 100, 0)):
            with self.assertRaisesRegex(ProjectError, '磁碟空間'):
                self.flow.start_total_audio()
        self.assertEqual(self.flow.total_audio()['id'], previous['id'])
        self.assertEqual(self.flow.total_audio_path().read_bytes(), mp3)
        self.assertFalse((self.flow.root/'.production.lock').exists())

    def test_invalid_selection_and_missing_sources_are_reported(self):
        ids = self.prepare(1)
        for selection, pause in (([], 500), (ids*2, 500), (ids, -1), (ids, True)):
            with self.subTest(selection=selection, pause=pause), self.assertRaises(ProjectError):
                self.flow.save_assembly_settings(selection, pause)
        self.flow.save_assembly_settings(ids)
        self.flow.narration_path(self.batch, 'srt').write_text('broken subtitles', encoding='utf-8')
        self.assertFalse(self.flow.inspect_assembly()[0]['valid'])
        with self.assertRaises(ProjectError):
            self.flow.start_total_audio()
        self.assertEqual(self.flow.total_audio_runs(), [])

    def test_media_failure_has_three_attempts_and_keeps_old_publication(self):
        ids = self.prepare(1)
        self.flow.save_assembly_settings(ids)
        previous = self.merge()
        # Exercise the real subprocess boundary with an executable rejecting FFmpeg arguments.
        with patch.dict(os.environ, EBOOK2MP4_FFMPEG=sys.executable):
            job = self.flow.start_total_audio()
            self.assertTrue(job.wait(15), job.state)
        self.assertEqual(job.state['status'], 'failed')
        self.assertIn('3 次', job.state['error'])
        self.flow.discard_total_audio(job)
        progress = self.flow.total_audio_runs()[-1]['progress']
        self.assertEqual(progress['sources'][0]['attempts'], 3)
        self.assertEqual(progress['sources'][0]['status'], 'failed')
        self.assertEqual(self.flow.total_audio()['id'], previous['id'])
        self.assertFalse((self.flow.root/'.production.lock').exists())

    def test_zero_pause_order_and_publication_conflict_preserve_old_total(self):
        a, b = self.prepare(2)
        self.flow.save_assembly_settings([a])
        old = self.merge()
        self.flow.save_assembly_settings([b, a], pause_ms=0)
        job = self.flow.start_total_audio()
        self.assertTrue(job.wait(15), job.state)
        other = ProjectWorkflow.open(self.flow.root)
        other.rename_batch(a, '另一個視窗修改名稱')
        with self.assertRaisesRegex(ProjectError, '另一個視窗'):
            self.flow.finish_total_audio(job)
        self.flow.discard_total_audio(job)
        self.flow = ProjectWorkflow.open(self.flow.root)
        self.assertEqual(self.flow.total_audio()['id'], old['id'])
        result = self.merge()
        self.assertEqual(result['duration_ms'], 400)
        self.assertEqual(self.flow.total_audio_path('srt').read_text(encoding='utf-8'),
                         '1\n00:00:00,000 --> 00:00:00,200\n第 2 批。\n\n'
                         '2\n00:00:00,200 --> 00:00:00,400\n第 1 批。\n\n')

    def test_new_selected_audio_version_requires_explicit_saved_selection(self):
        ids = self.prepare(1)
        self.flow.save_assembly_settings(ids)
        self.merge()
        job = self.flow.start_narration(self.batch, allow_network=False)
        self.assertTrue(job.wait(10), job.state)
        self.flow.finish_narration(job)
        self.assertTrue(self.flow.total_audio()['stale'])
        with self.assertRaisesRegex(ProjectError, '版本變更'):
            self.flow.start_total_audio()
        self.flow.save_assembly_settings(ids)
        self.merge()
        self.assertFalse(self.flow.total_audio()['stale'])

    def test_invalid_caption_timeline_is_not_published_even_with_matching_checksum(self):
        ids = self.prepare(1)
        self.flow.save_assembly_settings(ids)
        previous = self.merge()
        # Simulate a damaged but checksum-consistent imported project at the filesystem boundary.
        for text in ('1\n00:00:00,000 --> 00:00:02,000\n超出音訊。\n\n',
                     '1\n00:00:00,000 --> 00:00:00,150\n第一句。\n\n'
                     '2\n00:00:00,100 --> 00:00:00,200\n重疊。\n\n',
                     'this is not SRT'):
            with self.subTest(text=text):
                manifest = json.loads((self.flow.root/'project.json').read_bytes())
                ref = manifest['batches'][0]['narration']['srt']
                (self.flow.root/ref['path']).write_bytes(text.encode('utf-8'))
                ref['sha256'] = hashlib.sha256(text.encode('utf-8')).hexdigest()
                (self.flow.root/'project.json').write_text(json.dumps(manifest), encoding='utf-8')
                self.flow = ProjectWorkflow.open(self.flow.root)
                self.flow.save_assembly_settings(ids)
                job = self.flow.start_total_audio()
                self.assertTrue(job.wait(10), job.state)
                self.assertEqual(job.state['status'], 'failed')
                self.assertIn('字幕', job.state['error'])
                self.flow.discard_total_audio(job)
                self.assertEqual(self.flow.total_audio()['id'], previous['id'])

    def test_cleanup_failure_cannot_discard_an_already_published_total(self):
        ids = self.prepare(1)
        self.flow.save_assembly_settings(ids)
        job = self.flow.start_total_audio()
        self.assertTrue(job.wait(10), job.state)
        unlink = Path.unlink
        def locked(path, *args, **kwargs):
            if path.name == '.production.lock':
                raise PermissionError('simulated lock cleanup failure')
            return unlink(path, *args, **kwargs)
        with patch.object(Path, 'unlink', locked):
            with self.assertRaises(ProjectError):
                self.flow.finish_total_audio(job)
        self.flow.discard_total_audio(job)
        reopened = ProjectWorkflow.open(self.flow.root)
        self.assertFalse(reopened.total_audio()['stale'])
        self.assertTrue(reopened.total_audio_path().is_file())
        self.assertFalse((self.flow.root/'.production.lock').exists())

    def test_fractional_millisecond_sources_do_not_overlap_at_zero_pause(self):
        wav = self.path/'fractional.wav'
        with wave.open(str(wav), 'wb') as output:
            output.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
            output.writeframes(b'\x40\x00'*4814)
        mp3 = self.path/'fractional.mp3'
        subprocess.run([os.environ['EBOOK2MP4_FFMPEG'], '-v', 'error', '-i', str(wav),
                        '-c:a', 'libmp3lame', '-b:a', '96k', str(mp3)], check=True)
        ids = self.prepare(3, mp3.read_bytes())
        self.flow.save_assembly_settings(ids, pause_ms=0)
        result = self.merge()
        self.assertEqual(result['planned_frames'], 14442)
        self.assertEqual(result['frames'], len(self.pcm(self.flow.total_audio_path()))//2)
        self.assertLessEqual(abs(result['frames']-14442), 24)
        self.assertEqual(result['duration_ms'], 602)
        text = self.flow.total_audio_path('srt').read_text(encoding='utf-8')
        self.assertIn('00:00:00,201 --> 00:00:00,401', text)
        self.assertIn('00:00:00,401 --> 00:00:00,602', text)


if __name__ == '__main__':
    unittest.main()
