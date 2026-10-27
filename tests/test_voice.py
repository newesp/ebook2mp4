"""Voice journeys through the agreed ProjectWorkflow boundary."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, AsyncMock
import asyncio
import subprocess
import shutil

from ebook2mp4.workflow import ProjectWorkflow, ProjectError


VOICES = [dict(ShortName='zh-TW-TestNeural', FriendlyName='測試台灣人聲', Locale='zh-TW', Gender='Female'),
          dict(ShortName='en-US-TestNeural', FriendlyName='English test', Locale='en-US', Gender='Male')]


class VoiceJourney(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[1] / '.scratch/test-runs'
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.env = patch.dict('os.environ', EBOOK2MP4_VOICE_HOME=str(self.path / 'voice-cache'))
        self.env.start()
        self.addCleanup(self.env.stop)
        self.flow = ProjectWorkflow.create(self.path / '書籍', '語音測試')
        self.source = self.path / '原稿.txt'
        self.source.write_bytes('前文保留。\n\n選取 Hello 3.14。\n\n後文保留。'.encode('utf-8'))
        self.batch = self.flow.import_txt(self.flow.inspect_txt(self.source))

    def refresh_voices(self):
        with patch('edge_tts.list_voices', new=AsyncMock(return_value=VOICES)):
            job = self.flow.start_voice_refresh()
            self.assertTrue(job.wait(5))
            self.assertEqual(job.state['status'], 'completed', job.state)
        return self.flow.voice_catalog()

    def test_live_catalog_cache_and_independent_batch_defaults_survive_reopen(self):
        catalog = self.refresh_voices()
        self.assertEqual(catalog['voices'], [dict(id='zh-TW-TestNeural', name='測試台灣人聲', locale='zh-TW', gender='Female'),
                                            dict(id='en-US-TestNeural', name='English test', locale='en-US', gender='Male')])
        self.assertTrue(catalog['updated_at'])
        self.assertEqual(self.flow.voice_settings(self.batch)['rate'], '+0%')
        self.assertEqual(self.flow.voice_settings(self.batch)['voice'], '')
        self.flow.save_voice_settings('zh-TW-TestNeural', '-10%')
        self.assertEqual(self.flow.voice_settings(self.batch)['voice'], '')
        second = self.flow.import_txt(self.flow.inspect_txt(self.source))
        self.assertEqual(self.flow.voice_settings(second)['voice'], 'zh-TW-TestNeural')
        self.flow.save_voice_settings('en-US-TestNeural', '+20%', batch_id=self.batch)
        reopened = ProjectWorkflow.open(self.flow.root)
        self.assertEqual(reopened.voice_settings(self.batch)['voice'], 'en-US-TestNeural')
        self.assertEqual(reopened.voice_settings(second)['rate'], '-10%')
        with patch('edge_tts.list_voices', new=AsyncMock(side_effect=OSError('offline'))):
            job = reopened.start_voice_refresh()
            self.assertTrue(job.wait(5))
            self.assertEqual(job.state['status'], 'failed')
        self.assertEqual(reopened.voice_catalog(), catalog)
        reopened.save_draft(self.batch, '離線仍可校對。')

    def audio(self):
        target = self.path / '服務音訊.mp3'
        subprocess.run([shutil.which('ffmpeg'), '-v', 'error', '-f', 'lavfi', '-i',
                        'sine=frequency=440:duration=0.2', '-y', str(target)], check=True)
        return target.read_bytes()

    def test_selected_preview_snapshots_requests_and_reopens_playable_result(self):
        self.refresh_voices()
        self.flow.save_voice_settings('zh-TW-TestNeural', '+10%', batch_id=self.batch)
        audio = self.audio()
        requests = []
        class Service:
            def __init__(self, text, voice, **options):
                requests.append((text, voice, options['rate']))
            async def stream(self):
                yield dict(type='audio', data=audio)
        text = self.flow.texts(self.batch)[1]
        start = text.index('選取')
        with patch('edge_tts.Communicate', Service):
            job = self.flow.start_voice_preview(self.batch, start=start, end=start+len('選取 Hello 3.14。'))
            self.flow.save_voice_settings('en-US-TestNeural', '-20%', batch_id=self.batch)
            self.flow.save_draft(self.batch, '請求中已改稿。')
            self.assertTrue(job.wait(10))
            preview = self.flow.finish_voice_preview(job)
        self.assertEqual(requests, [('選取 Hello 3.14。', 'zh-TW-TestNeural', '+10%')])
        self.assertEqual(preview['settings']['voice'], 'zh-TW-TestNeural')
        self.assertEqual(preview['text'], '選取 Hello 3.14。')
        reopened = ProjectWorkflow.open(self.flow.root)
        saved = reopened.voice_preview(self.batch)
        self.assertEqual(saved['id'], preview['id'])
        self.assertGreater(reopened.voice_preview_path(self.batch).stat().st_size, 100)
        self.assertEqual(reopened.texts(self.batch)[1], '請求中已改稿。')

    def test_cancel_failure_and_unavailable_voice_keep_last_success(self):
        self.refresh_voices()
        self.flow.save_voice_settings('zh-TW-TestNeural', batch_id=self.batch)
        audio = self.audio()
        class Service:
            def __init__(self, *args, **kwargs): pass
            async def stream(self):
                yield dict(type='audio', data=audio)
        with patch('edge_tts.Communicate', Service):
            job = self.flow.start_voice_preview(self.batch)
            self.assertTrue(job.wait(10))
            previous = self.flow.finish_voice_preview(job)
        class Waiting(Service):
            async def stream(self):
                await asyncio.sleep(60)
                yield dict(type='audio', data=audio)
        with patch('edge_tts.Communicate', Waiting):
            job = self.flow.start_voice_preview(self.batch)
            job.cancel()
            self.assertTrue(job.wait(5))
            self.assertEqual(job.state['status'], 'cancelled')
            self.flow.discard_voice_preview(job)
        class Failure(Service):
            async def stream(self):
                raise OSError('private manuscript should not appear')
                yield
        with patch('edge_tts.Communicate', Failure):
            job = self.flow.start_voice_preview(self.batch)
            self.assertTrue(job.wait(5))
            self.assertEqual(job.state['status'], 'failed')
            self.assertNotIn('private manuscript', job.state['error'])
            self.flow.discard_voice_preview(job)
        with patch('edge_tts.list_voices', new=AsyncMock(return_value=[VOICES[1]])):
            job = self.flow.start_voice_refresh()
            self.assertTrue(job.wait(5))
        with self.assertRaisesRegex(ProjectError, '不可用'):
            self.flow.start_voice_preview(self.batch)
        self.assertEqual(self.flow.voice_preview(self.batch)['id'], previous['id'])

    def test_paragraph_processing_keeps_words_and_adds_only_one_interior_pause(self):
        self.refresh_voices()
        self.flow.save_voice_settings('zh-TW-TestNeural', batch_id=self.batch)
        audio = self.audio()
        requests = []
        class Service:
            def __init__(self, text, voice, **kwargs):
                requests.append(text)
            async def stream(self):
                yield dict(type='audio', data=audio)
        source = 'Hello 3.14, Dr. Chen.\n\n「第二段……」 https://example.com。'
        with patch('edge_tts.Communicate', Service):
            job = self.flow.start_voice_preview(self.batch, text=source, start=0, end=len(source))
            self.assertTrue(job.wait(10))
            self.flow.finish_voice_preview(job)
        self.assertEqual(requests, ['Hello 3.14, Dr. Chen.', '「第二段……」 https://example.com。'])
        result = subprocess.check_output([shutil.which('ffmpeg'), '-v', 'error', '-i',
            str(self.flow.voice_preview_path(self.batch)), '-f', 's16le', '-ac', '1', '-ar', '24000', '-'])
        # 0.2 + 0.5 + 0.2; no extra 0.5 seconds after the last paragraph.
        self.assertAlmostEqual(len(result) / 48000, .9, delta=.025)

    def test_invalid_ranges_missing_tools_and_dependencies_do_not_block_editing(self):
        self.refresh_voices()
        self.flow.save_voice_settings('zh-TW-TestNeural', batch_id=self.batch)
        for rate in ('+30%', 'normal', '', None):
            with self.assertRaises(ProjectError):
                self.flow.save_voice_settings('zh-TW-TestNeural', rate, batch_id=self.batch)
        for start, end, text in ((-1, 2, 'abc'), (0, 4, 'abc'), (0, 3001, 'x'*3001), (0, 2, '  ')):
            with self.assertRaises(ProjectError):
                self.flow.start_voice_preview(self.batch, start=start, end=end, text=text)
        with patch.dict('os.environ', EBOOK2MP4_FFMPEG=str(self.path / 'missing.exe')):
            with self.assertRaisesRegex(ProjectError, 'FFmpeg'):
                self.flow.start_voice_preview(self.batch)
        with patch.dict('sys.modules', edge_tts=None):
            job = self.flow.start_voice_preview(self.batch)
            self.assertTrue(job.wait(5))
            self.assertIn('缺少 Edge-TTS', job.state['error'])
            self.flow.discard_voice_preview(job)
        self.flow.save_draft(self.batch, '仍可保存。')
        self.assertEqual(ProjectWorkflow.open(self.flow.root).texts(self.batch)[1], '仍可保存。')

    def test_corrupt_audio_and_conflicting_save_keep_previous_success(self):
        self.refresh_voices()
        self.flow.save_voice_settings('zh-TW-TestNeural', batch_id=self.batch)
        good_audio = self.audio()
        data = good_audio
        class Service:
            def __init__(self, *args, **kwargs): pass
            async def stream(self):
                yield dict(type='audio', data=data)
        with patch('edge_tts.Communicate', Service):
            job = self.flow.start_voice_preview(self.batch)
            self.assertTrue(job.wait(10))
            original = self.flow.finish_voice_preview(job)
            data = b'not an MP3'
            job = self.flow.start_voice_preview(self.batch)
            self.assertTrue(job.wait(10))
            self.assertEqual(job.state['status'], 'failed')
            self.flow.discard_voice_preview(job)
            data = good_audio
            job = self.flow.start_voice_preview(self.batch)
            self.assertTrue(job.wait(10))
            other = ProjectWorkflow.open(self.flow.root)
            other.rename_batch(self.batch, '其他視窗')
            with self.assertRaisesRegex(ProjectError, '另一個視窗'):
                self.flow.finish_voice_preview(job)
            self.flow.discard_voice_preview(job)
        self.assertEqual(ProjectWorkflow.open(self.flow.root).voice_preview(self.batch)['id'], original['id'])


if __name__ == '__main__':
    unittest.main()
