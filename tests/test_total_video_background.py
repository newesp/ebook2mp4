"""T17 public workflow journeys with real, audible MP4 backgrounds and synthetic narration."""
import asyncio
from array import array
import json
import math
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import test_total_video as fixture
from ebook2mp4.workflow import ProjectWorkflow, ProjectError


def background(path: Path, seconds=.3, portrait=False, audio_seconds=None):
    size = '80x120' if portrait else '160x90'
    tool = os.environ['EBOOK2MP4_FFMPEG']
    args = [tool, '-v', 'error', '-y']
    for color in ('red', 'lime', 'blue'):
        args += ['-f', 'lavfi', '-i', f'color={color}:s={size}:r=30:d={seconds/3:.6f}']
    args += ['-f', 'lavfi', '-i', f'sine=frequency=1600:duration={seconds if audio_seconds is None else audio_seconds}', '-filter_complex',
             '[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]', '-map', '[v]', '-map', '3:a:0',
             '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(path)]
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return path


def pixel(path, seconds):
    return tuple(subprocess.check_output([os.environ['EBOOK2MP4_FFMPEG'], '-v', 'error', '-ss', str(seconds),
        '-i', str(path), '-vf', 'crop=2:2:iw/2:ih/2,scale=1:1', '-frames:v', '1', '-pix_fmt', 'rgb24',
        '-f', 'rawvideo', '-']))


class BackgroundJourney(unittest.TestCase):
    setUp = fixture.TotalVideoJourney.setUp
    prepare = fixture.TotalVideoJourney.prepare
    refresh_voices = fixture.TotalVideoJourney.refresh_voices
    audio = fixture.TotalVideoJourney.audio
    merge = fixture.TotalVideoJourney.merge
    picture = fixture.TotalVideoJourney.picture
    ready_video = fixture.TotalVideoJourney.ready_video

    def ready_audio(self):
        self.flow.save_assembly_settings(self.prepare(2))
        self.merge()

    def render(self):
        with patch('edge_tts.Communicate', side_effect=AssertionError('T17 must never request TTS')):
            job = self.flow.start_total_video()
            self.assertTrue(job.wait(35), job.state)
            self.assertEqual(job.state['status'], 'completed', job.state)
            return self.flow.finish_total_video(job)

    def test_loop_hold_trim_sound_and_subtitles_use_the_same_narration(self):
        self.ready_audio()
        audio = self.flow.total_audio_path().read_bytes()
        captions = self.flow.total_audio_path('srt').read_bytes()
        sound = self.path/'短片 有原聲.mp4'
        background(sound)
        video = self.flow.inspect_total_video_background(sound)
        self.flow.save_total_video_settings(background=video, source_type='video', resolution='720p')
        sound.unlink()
        self.flow = ProjectWorkflow.open(self.flow.root)
        self.assertEqual(self.flow.total_video_settings()['background_mode'], 'loop')
        original_id = self.flow.total_audio()['id']
        for mode, samples in [('loop', [(.05, 0), (.15, 1), (.25, 2), (.35, 0), (.75, 1)]),
                              ('hold', [(.05, 0), (.15, 1), (.25, 2), (.65, 2), (.85, 2)])]:
            with self.subTest(mode=mode):
                self.flow.save_total_video_settings(source_type='video', background_mode=mode, resolution='720p')
                self.render()
                target = self.flow.total_video_path()
                for second, channel in samples:
                    rgb = pixel(target, second)
                    self.assertEqual(rgb.index(max(rgb)), channel, (second, rgb))
                self.assertEqual(self.flow.total_video_path('srt').read_bytes(), captions)
                pcm = array('h', subprocess.check_output([os.environ['EBOOK2MP4_FFMPEG'], '-v', 'error',
                    '-i', str(target), '-vn', '-ac', '1', '-ar', '24000', '-f', 's16le', '-']))
                self.assertLessEqual(abs(len(pcm)/24-900), 200)
                # The middle is the single existing 500 ms join, not another pass through the narration.
                silence = pcm[round(.35*24000):round(.55*24000)]
                self.assertLess(max(abs(x) for x in silence), 40)
                segment = pcm[1200:3600]
                def amplitude(hz):
                    return abs(sum(x*complex(math.cos(2*math.pi*hz*i/24000), math.sin(2*math.pi*hz*i/24000))
                                   for i, x in enumerate(segment)))
                self.assertGreater(amplitude(440), amplitude(1600)*30)
                metadata = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
                    '-show_format', '-of', 'json', str(target)]))
                streams = metadata['streams']
                v, a = [s for s in streams if s['codec_type']=='video'][0], [s for s in streams if s['codec_type']=='audio'][0]
                self.assertEqual((v['codec_name'], v['pix_fmt'], v['width'], v['height'], v['r_frame_rate']),
                                 ('h264', 'yuv420p', 1280, 720, '30/1'))
                self.assertEqual((a['codec_name'], a['sample_rate'], a['channels']), ('aac', '48000', 2))
                data = target.read_bytes()
                self.assertLess(data.index(b'moov'), data.index(b'mdat'))
        long = background(self.path/'長背景.mp4', 1.8)
        self.flow.save_total_video_settings(background=self.flow.inspect_total_video_background(long),
            source_type='video', background_mode='hold', resolution='720p')
        self.render()
        rgb = pixel(self.flow.total_video_path(), .85)
        self.assertEqual(rgb.index(max(rgb)), 1)
        self.assertLessEqual(abs(self.flow.total_video()['duration_ms']-900), 200)
        self.assertEqual(self.flow.total_audio()['id'], original_id)
        self.assertEqual(self.flow.total_audio_path().read_bytes(), audio)
        self.assertEqual(self.flow.total_video_path('srt').read_bytes(), captions)

    def test_validation_failures_cancellation_and_video_only_retry_protect_old_products(self):
        old = self.ready_video()
        old_bytes = self.flow.total_video_path().read_bytes()
        original_audio = self.flow.total_audio_path().read_bytes()
        invalid = self.path/'假影片.mp4'
        invalid.write_bytes(b'not an MP4')
        before = self.flow.total_video_settings()
        with self.assertRaises(ProjectError):
            self.flow.inspect_total_video_background(invalid)
        self.assertEqual(self.flow.total_video_settings(), before)
        path = background(self.path/'背景.mp4')
        inspected = self.flow.inspect_total_video_background(path)
        path.write_bytes(b'changed')
        with self.assertRaises(ProjectError):
            self.flow.save_total_video_settings(background=inspected, source_type='video')
        background(path)
        self.flow.save_total_video_settings(background=self.flow.inspect_total_video_background(path),
            source_type='video', resolution='720p')
        self.assertTrue(self.flow.total_video()['stale'])
        self.assertFalse(self.flow.total_audio()['stale'])
        job = self.flow.start_total_video()
        job.cancel()
        self.assertTrue(job.wait(15))
        self.flow.discard_total_video(job)
        self.assertEqual(self.flow.total_video()['id'], old['id'])
        self.assertEqual(self.flow.total_video_path().read_bytes(), old_bytes)
        asset = self.flow._path(self.flow.total_video_settings()['background']['path'])
        good_bytes = asset.read_bytes()
        asset.write_bytes(b'corrupt')
        job = self.flow.start_total_video()
        self.assertTrue(job.wait(15))
        self.assertEqual(job.state['status'], 'failed')
        self.flow.discard_total_video(job)
        self.assertEqual(self.flow.total_video_path().read_bytes(), old_bytes)
        asset.write_bytes(good_bytes)
        self.render()
        self.assertNotEqual(self.flow.total_video()['id'], old['id'])
        self.assertEqual(self.flow.total_audio_path().read_bytes(), original_audio)
        self.assertFalse((self.flow.root/'.production.lock').exists())
        self.assertFalse(list(self.flow.root.glob('video/*/media/background.mp4')))

    def test_portrait_preview_black_padding_and_modes_survive_reopen(self):
        self.ready_audio()
        video = self.flow.inspect_total_video_background(background(self.path/'直式.mp4', portrait=True))
        self.flow.save_total_video_settings(background=video, source_type='video', background_mode='hold', resolution='720p')
        self.flow = ProjectWorkflow.open(self.flow.root)
        self.assertEqual(self.flow.total_video_settings()['background_mode'], 'hold')
        self.render()
        raw = subprocess.check_output([os.environ['EBOOK2MP4_FFMPEG'], '-v', 'error', '-i',
            str(self.flow.total_video_path()), '-frames:v', '1', '-vf', 'crop=2:2:0:0,scale=1:1',
            '-pix_fmt', 'rgb24', '-f', 'rawvideo', '-'])
        self.assertLessEqual(max(raw), 3)
        view = self.flow.inspect_total_video()
        self.assertIsNotNone(view['preview'])
        self.assertEqual(view['warning'], '')
        self.flow.save_total_video_settings(source_type='image', image=self.flow.inspect_total_video_image(self.picture()), resolution='720p')
        self.assertTrue(self.flow.total_video()['stale'])
        self.assertFalse(self.flow.total_audio()['stale'])

    def test_long_excluded_sound_does_not_delay_visual_loops(self):
        self.ready_audio()
        source = background(self.path/'短畫面長原聲.mp4', .3, audio_seconds=1.2)
        self.flow.save_total_video_settings(background=self.flow.inspect_total_video_background(source),
            source_type='video', resolution='720p')
        self.render()
        for second, channel in [(.35, 0), (.45, 1), (.65, 0), (.85, 2)]:
            rgb = pixel(self.flow.total_video_path(), second)
            self.assertEqual(rgb.index(max(rgb)), channel, (second, rgb))
        from ebook2mp4.total_video import stream_frames
        frames = []
        def emit(data, ms):
            if ms == 400:
                offset = (270*960+480)*3
                rgb = data[offset:offset+3]
                self.assertEqual(rgb.index(max(rgb)), 1, (ms, rgb))
            frames.append(ms)
        asyncio.run(stream_frames(source, 900, 'loop', emit))
        self.assertIn(400, frames)
        self.assertEqual(list(source.parent.glob('.background-stream-*')), [])


if __name__ == '__main__':
    unittest.main()
