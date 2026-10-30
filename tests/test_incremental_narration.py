"""T13 journeys through the public project workflow and external TTS boundary."""
import unittest
import asyncio
import threading
from unittest.mock import patch

import test_voice as fixture
from ebook2mp4.workflow import ProjectWorkflow, ProjectError


class IncrementalNarration(unittest.TestCase):
    setUp = fixture.VoiceJourney.setUp
    refresh_voices = fixture.VoiceJourney.refresh_voices
    audio = fixture.VoiceJourney.audio

    def test_defaults_apply_only_to_explicit_batches_and_survive_reopen(self):
        self.refresh_voices()
        self.flow.save_voice_settings('zh-TW-TestNeural', batch_id=self.batch)
        self.flow.confirm_reading(self.batch)
        second = self.flow.import_txt(self.flow.inspect_txt(self.source))
        self.flow.save_voice_settings('en-US-TestNeural', '+10%',
                                      sentence_pause_ms=200, paragraph_pause_ms=800)
        third = self.flow.import_txt(self.flow.inspect_txt(self.source))
        self.assertEqual(self.flow.voice_settings(third)['voice'], 'en-US-TestNeural')
        self.assertEqual(self.flow.voice_settings(self.batch)['voice'], 'zh-TW-TestNeural')
        with self.assertRaises(ProjectError):
            self.flow.apply_voice_defaults([self.batch, 'missing'])
        self.assertEqual(self.flow.voice_settings(self.batch)['voice'], 'zh-TW-TestNeural')
        self.flow.apply_voice_defaults([self.batch])
        reopened = ProjectWorkflow.open(self.flow.root)
        self.assertEqual(reopened.voice_settings(self.batch), reopened.voice_settings())
        self.assertEqual(reopened.voice_settings(second)['voice'], '')
        self.assertEqual(reopened.reading_text(self.batch), self.source.read_text(encoding='utf-8'))
        self.assertEqual(reopened.voice_settings(third)['paragraph_pause_ms'], 800)

    def test_edit_insert_and_pause_changes_reuse_actual_requests(self):
        self.refresh_voices()
        self.flow.save_voice_settings('zh-TW-TestNeural', batch_id=self.batch)
        other = self.flow.import_txt(self.flow.inspect_txt(self.source))
        self.flow.confirm_reading(other)
        text = '第一段。\n\n第二段。\n\n第三段。'
        self.flow.save_draft(self.batch, text)
        self.flow.confirm_reading(self.batch)
        audio, requests = self.audio(), []
        class Service:
            def __init__(self, text, voice, **options):
                requests.append((text, voice, options['rate']))
            async def stream(self):
                yield dict(type='audio', data=audio)
        def produce(flow, **options):
            job = flow.start_narration(self.batch, **options)
            self.assertTrue(job.wait(20), job.state)
            return flow.finish_narration(job)
        with patch('edge_tts.Communicate', Service):
            original = produce(self.flow)
            old_mp3 = self.flow.narration_path(self.batch).read_bytes()
            new_text = '第一段。\n\n插入段落。\n\n修改第二段。\n\n第三段。'
            self.flow.save_draft(self.batch, new_text)
            with self.assertRaises(ProjectError):
                self.flow.inspect_narration(self.batch)
            self.assertEqual(self.flow.narration(self.batch)['id'], original['id'])
            self.assertEqual(self.flow.reading_text(other), self.source.read_text(encoding='utf-8'))
            self.flow.confirm_reading(self.batch)
            reopened = ProjectWorkflow.open(self.flow.root)
            inspection = reopened.inspect_narration(self.batch)
            self.assertEqual((inspection['reusable'], inspection['remaining']), (2, 2))
            requests.clear()
            result = produce(reopened)
            self.assertEqual(requests, [('插入段落。', 'zh-TW-TestNeural', '+0%'),
                                        ('修改第二段。', 'zh-TW-TestNeural', '+0%')])
            self.assertEqual(result['text'], new_text)
            srt = reopened.narration_path(self.batch, 'srt').read_text(encoding='utf-8')
            for sentence in ('第一段。', '插入段落。', '修改第二段。', '第三段。'):
                self.assertEqual(srt.count(sentence), 1)
            self.assertEqual(result['duration_ms'], 2300)
            reopened.save_voice_settings('zh-TW-TestNeural', batch_id=self.batch, paragraph_pause_ms=800)
            requests.clear()
            self.assertEqual(reopened.inspect_narration(self.batch)['remaining'], 0)
            result = produce(reopened, allow_network=False)
            self.assertEqual(requests, [])
            self.assertEqual(result['duration_ms'], 3200)
            self.assertEqual((self.flow.root / original['mp3']['path']).read_bytes(), old_mp3)
            reopened.save_voice_settings('en-US-TestNeural', '+10%', batch_id=self.batch)
            self.assertEqual(reopened.inspect_narration(self.batch)['remaining'], 4)
            result = produce(reopened)
            self.assertTrue(all(voice == 'en-US-TestNeural' and rate == '+10%' for _, voice, rate in requests))
            self.assertEqual(len(requests), 4)

    def test_new_revision_cancel_and_cache_loss_preserve_old_product(self):
        self.refresh_voices()
        self.flow.save_voice_settings('zh-TW-TestNeural', batch_id=self.batch)
        self.flow.save_draft(self.batch, '第一段。\n\n第二段。')
        self.flow.confirm_reading(self.batch)
        audio = self.audio()
        class Service:
            def __init__(self, text, *args, **kwargs): self.text = text
            async def stream(self): yield dict(type='audio', data=audio)
        with patch('edge_tts.Communicate', Service):
            job = self.flow.start_narration(self.batch)
            self.assertTrue(job.wait(15))
            old = self.flow.finish_narration(job)
        old_bytes = {kind: self.flow.narration_path(self.batch, kind).read_bytes() for kind in ('mp3', 'srt')}
        self.flow.save_draft(self.batch, '第一段。\n\n修改第二段。')
        self.flow.confirm_reading(self.batch)
        waiting = threading.Event()
        class Waiting(Service):
            async def stream(self):
                waiting.set()
                await asyncio.sleep(60)
                yield dict(type='audio', data=audio)
        with patch('edge_tts.Communicate', Waiting):
            job = self.flow.start_narration(self.batch)
            self.assertTrue(waiting.wait(10))
            self.flow.save_voice_settings('en-US-TestNeural')
            with self.assertRaisesRegex(ProjectError, '任務'):
                self.flow.apply_voice_defaults([self.batch])
            job.cancel()
            self.assertTrue(job.wait(5))
            self.flow.discard_narration(job)
        self.assertEqual(self.flow.narration(self.batch)['id'], old['id'])
        for kind in ('mp3', 'srt'):
            self.assertEqual(self.flow.narration_path(self.batch, kind).read_bytes(), old_bytes[kind])
        cache = self.flow.root / 'batches' / self.batch / 'voice-blocks'
        next(cache.glob('*.wav')).write_bytes(b'corrupt')
        with patch('edge_tts.Communicate', side_effect=AssertionError('must not transmit')):
            job = self.flow.start_narration(self.batch, allow_network=False)
            self.assertTrue(job.wait(15))
            self.assertEqual(job.state['status'], 'failed')
            self.flow.discard_narration(job)
        self.assertFalse((self.flow.root / '.production.lock').exists())
        self.assertEqual(self.flow.narration_path(self.batch).read_bytes(), old_bytes['mp3'])
