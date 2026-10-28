"""Formal narration journeys at the agreed ProjectWorkflow boundary."""
import asyncio
from pathlib import Path
import subprocess
import threading
import unittest
from unittest.mock import patch

import test_voice as fixture
from ebook2mp4.workflow import ProjectWorkflow, ProjectError


class NarrationJourney(unittest.TestCase):
    setUp = fixture.VoiceJourney.setUp
    refresh_voices = fixture.VoiceJourney.refresh_voices
    audio = fixture.VoiceJourney.audio
    def test_confirmed_snapshot_outputs_measured_cues_and_reopens(self):
        self.refresh_voices()
        self.flow.save_voice_settings('zh-TW-TestNeural', batch_id=self.batch)
        with self.assertRaisesRegex(ProjectError, '確認'):
            self.flow.start_narration(self.batch)
        text = 'Hello 3.14, Dr. Chen.\n\n「第二段……」 https://example.com。'
        self.flow.save_draft(self.batch, text)
        self.flow.confirm_reading(self.batch)
        audio, requests = self.audio(), []
        started, proceed = threading.Event(), threading.Event()
        class Service:
            def __init__(self, text, voice, **options):
                requests.append((text, voice, options['rate']))
            async def stream(self):
                started.set()
                while not proceed.is_set():
                    await asyncio.sleep(.01)
                yield dict(type='audio', data=audio)
        with patch('edge_tts.Communicate', Service):
            job = self.flow.start_narration(self.batch)
            self.assertTrue(started.wait(5))
            other = ProjectWorkflow.open(self.flow.root)
            with self.assertRaisesRegex(ProjectError, '任務'):
                other.start_narration(self.batch)
            self.flow.save_draft(self.batch, '工作中改稿。')
            self.flow.save_voice_settings('en-US-TestNeural', '+20%', batch_id=self.batch)
            proceed.set()
            self.assertTrue(job.wait(15), job.state)
            product = self.flow.finish_narration(job)
        self.assertEqual(requests, [('Hello 3.14, Dr. Chen.', 'zh-TW-TestNeural', '+0%'),
                                    ('「第二段……」 https://example.com。', 'zh-TW-TestNeural', '+0%')])
        reopened = ProjectWorkflow.open(self.flow.root)
        self.assertEqual(reopened.narration(self.batch), product)
        mp3 = reopened.narration_path(self.batch, 'mp3')
        srt = reopened.narration_path(self.batch, 'srt').read_text(encoding='utf-8')
        self.assertEqual(srt, '1\n00:00:00,000 --> 00:00:00,200\nHello 3.14, Dr. Chen.\n\n'
                             '2\n00:00:00,700 --> 00:00:00,900\n「第二段……」 https://example.com。\n\n')
        pcm = subprocess.check_output([__import__('os').environ['EBOOK2MP4_FFMPEG'], '-v', 'error',
            '-i', str(mp3), '-f', 's16le', '-ac', '1', '-ar', '24000', '-'])
        self.assertAlmostEqual(len(pcm)/48000, .9, delta=.025)
        self.assertEqual(product['text'], text)
        self.assertEqual([c['duration_ms'] for c in product['chunks']], [200, 200])
        destination = self.path / '另存'
        reopened.export_narration(self.batch, destination)
        self.assertEqual((destination / 'narration.mp3').read_bytes(), mp3.read_bytes())
        self.assertEqual((destination / 'narration.srt').read_text(encoding='utf-8'), srt)
        with self.assertRaises(ProjectError):
            reopened.export_narration(self.batch, destination)


    def prepare(self, text='第一段。\n\n第二段。'):
        self.refresh_voices()
        self.flow.save_voice_settings('zh-TW-TestNeural', batch_id=self.batch)
        self.flow.save_draft(self.batch, text)
        self.flow.confirm_reading(self.batch)

    def test_failed_retries_cancel_and_conflict_keep_previous_product(self):
        self.prepare()
        audio = self.audio()
        class Service:
            def __init__(self, *args, **options): pass
            async def stream(self):
                yield dict(type='audio', data=audio)
        with patch('edge_tts.Communicate', Service):
            job = self.flow.start_narration(self.batch)
            self.assertTrue(job.wait(15))
            previous = self.flow.finish_narration(job)
        self.flow.save_voice_settings('zh-TW-TestNeural', '+10%', batch_id=self.batch)
        calls = []
        class Failure(Service):
            def __init__(self, text, *args, **options):
                calls.append(text)
            async def stream(self):
                raise OSError('private text')
                yield
        with patch('edge_tts.Communicate', Failure):
            job = self.flow.start_narration(self.batch)
            self.assertTrue(job.wait(15))
            self.assertEqual(job.state['status'], 'failed')
            self.assertEqual(calls, ['第一段。'] * 3)
            self.assertNotIn('private text', job.state['error'])
            self.flow.discard_narration(job)
        run = self.flow.narration_runs(self.batch)[-1]
        self.assertEqual(run['progress']['failed'], 1)
        self.assertEqual(run['progress']['chunks'][0]['attempts'], 3)
        started, released = threading.Event(), threading.Event()
        class Waiting(Service):
            async def stream(self):
                started.set()
                try:
                    await asyncio.sleep(60)
                    yield
                finally:
                    await asyncio.sleep(.1)
                    released.set()
        with patch('edge_tts.Communicate', Waiting):
            job = self.flow.start_narration(self.batch)
            self.assertTrue(started.wait(5))
            job.cancel()
            job.cancel()
            self.assertTrue(job.wait(5))
            self.assertTrue(released.is_set())
            self.flow.discard_narration(job)
        self.assertEqual(self.flow.narration_runs(self.batch)[-1]['progress']['status'], 'cancelled')
        self.assertEqual(self.flow.narration(self.batch)['id'], previous['id'])
        with patch('edge_tts.Communicate', Service):
            job = self.flow.start_narration(self.batch)
            self.assertTrue(job.wait(15))
            other = ProjectWorkflow.open(self.flow.root)
            other.rename_batch(self.batch, '他窗')
            with self.assertRaisesRegex(ProjectError, '另一個視窗'):
                self.flow.finish_narration(job)
            self.flow.discard_narration(job)
        self.assertEqual(ProjectWorkflow.open(self.flow.root).narration(self.batch)['id'], previous['id'])
        self.assertFalse((self.flow.root / '.production.lock').exists())
        self.assertEqual(list(self.flow.root.rglob('*.mp3')), [self.flow.narration_path(self.batch)])

    def test_long_paragraph_preserves_protected_spans_and_exact_content(self):
        sentence = 'Dr. Chen reads 3.14 at https://example.com/a?q=1.2, then says 「引文……（保持完整）」；結束。 '
        text = (sentence * 35) + '\n\nSecond paragraph.\n\n'
        self.prepare(text)
        audio, requests = self.audio(), []
        class Service:
            def __init__(self, text, *args, **options): requests.append(text)
            async def stream(self): yield dict(type='audio', data=audio)
        with patch('edge_tts.Communicate', Service):
            job = self.flow.start_narration(self.batch)
            self.assertTrue(job.wait(30), job.state)
            result = self.flow.finish_narration(job)
        self.assertGreater(len(requests), 2)
        self.assertEqual(''.join(c['text'] + c['separator_after'] for c in result['chunks']), text)
        self.assertEqual(''.join(requests).count('Dr. Chen'), 35)
        self.assertEqual(''.join(requests).count('https://example.com/a?q=1.2,'), 35)
        for sent in requests[:-1]:
            self.assertEqual(sent.count('「'), sent.count('」'))
            self.assertFalse(sent.rstrip().endswith('Dr.'))
            self.assertTrue(sent.rstrip().endswith('結束。'))
            self.assertLessEqual(len(__import__('html').escape(sent, quote=False).encode('utf-8')), 3000)
        self.assertEqual(sum(c['pause_after_ms'] for c in result['chunks']), 500)

    def test_indivisible_long_quotation_is_rejected_before_any_online_request(self):
        self.prepare('「' + '完整文字' * 1000 + '」')
        with self.assertRaisesRegex(ProjectError, '安全切分'):
            self.flow.start_narration(self.batch)
        self.assertEqual(self.flow.narration_runs(self.batch), [])
        self.assertFalse((self.flow.root / '.production.lock').exists())

    def test_long_english_prefers_complete_sentences_over_word_boundaries(self):
        text = 'Dr. Chen reads the value 3.14 and a complete sentence. ' * 100
        self.prepare(text)
        audio, requests = self.audio(), []
        class Service:
            def __init__(self, text, *args, **options): requests.append(text)
            async def stream(self): yield dict(type='audio', data=audio)
        with patch('edge_tts.Communicate', Service):
            job = self.flow.start_narration(self.batch)
            self.assertTrue(job.wait(30))
            self.flow.finish_narration(job)
        self.assertGreater(len(requests), 1)
        self.assertEqual(''.join(requests), text)
        self.assertTrue(all(sent.rstrip().endswith('sentence.') for sent in requests), requests)

    def test_lock_cleanup_failure_cannot_discard_a_published_product(self):
        self.prepare('已發布成品必須保留。')
        audio = self.audio()
        class Service:
            def __init__(self, *args, **options): pass
            async def stream(self): yield dict(type='audio', data=audio)
        with patch('edge_tts.Communicate', Service):
            job = self.flow.start_narration(self.batch)
            self.assertTrue(job.wait(15))
        original_unlink = Path.unlink
        def cannot_release(path, *args, **kwargs):
            if path.name == '.production.lock':
                raise PermissionError('lock cleanup injection')
            return original_unlink(path, *args, **kwargs)
        with patch.object(Path, 'unlink', cannot_release):
            with self.assertRaises(ProjectError):
                self.flow.finish_narration(job)
        self.assertIsNotNone(self.flow.narration(self.batch))
        self.flow.discard_narration(job)
        reopened = ProjectWorkflow.open(self.flow.root)
        self.assertTrue(reopened.narration_path(self.batch).is_file())
        self.assertTrue(reopened.narration_path(self.batch, 'srt').is_file())
        self.assertFalse((self.flow.root / '.production.lock').exists())

    def test_surrounding_quotes_and_brackets_do_not_block_long_url_prose(self):
        text = ('Read this link (https://example.com). This is a complete sentence. '
                'Read "https://example.com" and \'https://example.com\'. Another sentence. ') * 60
        self.prepare(text)
        audio, requests = self.audio(), []
        class Service:
            def __init__(self, text, *args, **options): requests.append(text)
            async def stream(self): yield dict(type='audio', data=audio)
        with patch('edge_tts.Communicate', Service):
            job = self.flow.start_narration(self.batch)
            self.assertTrue(job.wait(30))
            self.flow.finish_narration(job)
        self.assertGreater(len(requests), 1)
        self.assertEqual(''.join(requests), text)
        for sent in requests:
            self.assertEqual(sent.count('('), sent.count(')'))
            self.assertEqual(sent.count('"') % 2, 0)
            self.assertEqual(sent.count("'") % 2, 0)
