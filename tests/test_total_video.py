"""Total-video journeys through the public project workflow and real media."""
from pathlib import Path
import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from PIL import Image

import test_total_audio as fixture
from ebook2mp4.workflow import ProjectError, ProjectWorkflow


class TotalVideoJourney(unittest.TestCase):
    setUp = fixture.TotalAudioJourney.setUp
    prepare = fixture.TotalAudioJourney.prepare
    refresh_voices = fixture.TotalAudioJourney.refresh_voices
    audio = fixture.TotalAudioJourney.audio
    merge = fixture.TotalAudioJourney.merge

    def picture(self, name='封面.png'):
        path = self.path/name
        Image.new('RGBA', (80, 120), (255, 0, 0, 128)).save(path)
        return path

    def test_picture_is_copied_and_resolution_survives_reopen(self):
        self.assertEqual(self.flow.total_video_settings()['resolution'], '1080p')
        source = self.picture()
        image = self.flow.inspect_total_video_image(source)
        self.flow.save_total_video_settings(image=image, resolution='720p')
        source.unlink()
        reopened = ProjectWorkflow.open(self.flow.root)
        settings = reopened.total_video_settings()
        self.assertEqual(settings['resolution'], '720p')
        self.assertEqual((settings['image']['width'], settings['image']['height']), (80, 120))
        self.assertTrue((reopened.root/settings['image']['path']).is_file())
        self.assertIsNone(reopened.total_audio())
        with self.assertRaises(ProjectError):
            reopened.save_total_video_settings(resolution='480p')
        self.assertEqual(reopened.total_video_settings(), settings)

    def test_reopen_then_encode_without_batch_video_or_new_tts(self):
        ids = self.prepare(2)
        self.flow.save_assembly_settings(ids)
        audio = self.merge()
        original = self.flow.total_audio_path().read_bytes()
        captions = self.flow.total_audio_path('srt').read_bytes()
        self.flow.save_total_video_settings(image=self.flow.inspect_total_video_image(self.picture()), resolution='720p')
        flow = ProjectWorkflow.open(self.flow.root)
        with patch('edge_tts.Communicate', side_effect=AssertionError('video must not send text')):
            job = flow.start_total_video()
            self.assertTrue(job.wait(30), job.state)
            self.assertEqual(job.state['status'], 'completed', job.state)
            product = flow.finish_total_video(job)
        self.assertFalse(product['stale'])
        self.assertEqual(product['audio']['id'], audio['id'])
        self.assertEqual(flow.total_video_path('srt').read_bytes(), captions)
        self.assertEqual(flow.total_audio_path().read_bytes(), original)
        metadata = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format',
                            '-of', 'json', str(flow.total_video_path())]))
        video = next(s for s in metadata['streams'] if s['codec_type'] == 'video')
        sound = next(s for s in metadata['streams'] if s['codec_type'] == 'audio')
        self.assertEqual((video['codec_name'], video['pix_fmt'], video['width'], video['height'], video['r_frame_rate']),
                         ('h264', 'yuv420p', 1280, 720, '30/1'))
        self.assertEqual((sound['codec_name'], sound['profile'], sound['sample_rate'], sound['channels']),
                         ('aac', 'LC', '48000', 2))
        self.assertLessEqual(abs(float(metadata['format']['duration'])*1000-900), 200)
        self.assertLessEqual(abs(product['duration_ms']-900), 200)
        raw = flow.total_video_path().read_bytes()
        self.assertLess(raw.index(b'moov'), raw.index(b'mdat'))
        reopened = ProjectWorkflow.open(flow.root)
        self.assertFalse(reopened.total_video()['stale'])
        reopened.save_total_video_settings(resolution='1080p')
        self.assertTrue(reopened.total_video()['stale'])
        self.assertFalse(reopened.total_audio()['stale'])

    def ready_video(self):
        self.flow.save_assembly_settings(self.prepare(1))
        self.merge()
        self.flow.save_total_video_settings(image=self.flow.inspect_total_video_image(self.picture()), resolution='720p')
        job = self.flow.start_total_video()
        self.assertTrue(job.wait(30), job.state)
        return self.flow.finish_total_video(job)

    def test_cancel_failure_export_and_retry_keep_previous_artifacts(self):
        old = self.ready_video()
        old_bytes = self.flow.total_video_path().read_bytes()
        job = self.flow.start_total_video()
        other = ProjectWorkflow.open(self.flow.root)
        try:
            with self.assertRaisesRegex(ProjectError, '任務'):
                other.start_total_audio()
            with self.assertRaisesRegex(ProjectError, '任務'):
                other.save_total_video_settings(resolution='1080p')
            job.cancel()
            self.assertTrue(job.wait(10))
            self.flow.discard_total_video(job)
        finally:
            if not job.wait(0):
                job.cancel()
                job.wait(10)
                self.flow.discard_total_video(job)
        self.assertEqual(self.flow.total_video_path().read_bytes(), old_bytes)
        with patch.dict(os.environ, EBOOK2MP4_FFMPEG=sys.executable):
            job = self.flow.start_total_video()
            self.assertTrue(job.wait(15))
            self.assertEqual(job.state['status'], 'failed')
            self.flow.discard_total_video(job)
        self.assertEqual(self.flow.total_video()['id'], old['id'])
        self.assertFalse((self.flow.root/'.production.lock').exists())
        export = self.path/'export'
        self.flow.export_total_video(export)
        self.assertEqual((export/'total.mp4').read_bytes(), old_bytes)
        self.assertEqual((export/'total.srt').read_bytes(), self.flow.total_audio_path('srt').read_bytes())
        job = self.flow.start_total_video()
        self.assertTrue(job.wait(30), job.state)
        self.assertNotEqual(self.flow.finish_total_video(job)['id'], old['id'])
        self.assertEqual(self.flow.total_video_runs()[-1]['progress']['status'], 'completed')
        self.assertFalse((self.flow.root/'.production.lock').exists())

    def test_changed_source_blocks_video_and_corrupt_picture_preserves_settings(self):
        self.ready_video()
        settings = self.flow.total_video_settings()
        broken = self.path/'broken.png'
        broken.write_bytes(b'not a picture')
        with self.assertRaises(ProjectError):
            self.flow.inspect_total_video_image(broken)
        self.assertEqual(self.flow.total_video_settings(), settings)
        self.flow.save_draft(self.batch, '已修改。')
        self.assertTrue(self.flow.total_video()['stale'])
        with self.assertRaisesRegex(ProjectError, '總音訊'):
            self.flow.start_total_video()
        self.assertFalse((self.flow.root/'.production.lock').exists())

    def test_corrupted_audio_is_not_current_and_cannot_publish_video(self):
        old = self.ready_video()
        self.flow.total_audio_path().write_bytes(b'corrupt')
        self.assertTrue(self.flow.total_video()['stale'])
        self.assertTrue(self.flow.inspect_total_video()['product']['stale'])
        job = self.flow.start_total_video()
        self.assertTrue(job.wait(15), job.state)
        self.assertEqual(job.state['status'], 'failed')
        self.flow.discard_total_video(job)
        self.assertEqual(self.flow.total_video()['id'], old['id'])

    def test_publication_conflict_and_disk_shortage_keep_old_video(self):
        old = self.ready_video()
        import shutil
        usage = shutil.disk_usage(self.flow.root)
        with patch('shutil.disk_usage', return_value=type(usage)(usage.total, usage.total-1, 1)):
            with self.assertRaisesRegex(ProjectError, '磁碟空間'):
                self.flow.start_total_video()
        self.assertEqual(self.flow.total_video()['id'], old['id'])
        job = self.flow.start_total_video()
        self.assertTrue(job.wait(30), job.state)
        other = ProjectWorkflow.open(self.flow.root)
        other.rename_batch(self.batch, '其他視窗修改')
        with self.assertRaisesRegex(ProjectError, '另一個視窗'):
            self.flow.finish_total_video(job)
        self.flow.discard_total_video(job)
        self.flow = ProjectWorkflow.open(self.flow.root)
        self.assertEqual(self.flow.total_video()['id'], old['id'])
        self.assertFalse((self.flow.root/'.production.lock').exists())


if __name__ == '__main__':
    unittest.main()
