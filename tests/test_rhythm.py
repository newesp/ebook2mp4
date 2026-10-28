"""Rhythm journeys through the agreed public workflow, with real media tools."""
import subprocess
import shutil
import unittest
from unittest.mock import patch

import test_voice as fixture
from ebook2mp4.workflow import ProjectWorkflow, ProjectError


class RhythmJourney(unittest.TestCase):
    setUp = fixture.VoiceJourney.setUp
    refresh_voices = fixture.VoiceJourney.refresh_voices
    audio = fixture.VoiceJourney.audio
    # Reuse setup/helpers without inheriting the voice suite a second time.
    def test_pause_settings_persist_and_reject_out_of_range(self):
        self.refresh_voices()
        self.flow.save_voice_settings('zh-TW-TestNeural', batch_id=self.batch,
                                      sentence_pause_ms=200, paragraph_pause_ms=800)
        reopened = ProjectWorkflow.open(self.flow.root)
        value = reopened.voice_settings(self.batch)
        self.assertEqual((value['sentence_pause_ms'], value['paragraph_pause_ms']), (200, 800))
        for sentence, paragraph in ((-1, 800), (1501, 800), (200, 3001), (True, 800), (0, -1)):
            with self.assertRaises(ProjectError):
                reopened.save_voice_settings('zh-TW-TestNeural', batch_id=self.batch,
                                             sentence_pause_ms=sentence, paragraph_pause_ms=paragraph)
        self.assertEqual(reopened.voice_settings(self.batch), value)

    def test_shared_sentence_audio_reused_and_silence_has_no_caption(self):
        self.refresh_voices()
        text = '第一句。Hello Dr. Chen, 3.14 is fine!\n\n最後一段。'
        self.flow.save_draft(self.batch, text)
        self.flow.confirm_reading(self.batch)
        self.flow.save_voice_settings('zh-TW-TestNeural', batch_id=self.batch,
                                      sentence_pause_ms=200, paragraph_pause_ms=800)
        audio, requests = self.audio(), []
        class Service:
            def __init__(self, text, voice, **kwargs): requests.append(text)
            async def stream(self): yield dict(type='audio', data=audio)
        with patch('edge_tts.Communicate', Service):
            job = self.flow.start_voice_preview(self.batch, text=text, start=0, end=len(text))
            self.assertTrue(job.wait(15))
            self.flow.finish_voice_preview(job)
            self.assertEqual(requests, ['第一句。', 'Hello Dr. Chen, 3.14 is fine!', '最後一段。'])
            requests.clear()
            job = self.flow.start_narration(self.batch)
            self.assertTrue(job.wait(15))
            product = self.flow.finish_narration(job)
            self.assertEqual(requests, [])
            self.assertEqual(product['duration_ms'], 1600)
            srt = self.flow.narration_path(self.batch, 'srt').read_text(encoding='utf-8')
            self.assertIn('00:00:00,400 --> 00:00:00,600', srt)
            self.assertIn('00:00:01,400 --> 00:00:01,600', srt)
            self.flow.save_voice_settings('zh-TW-TestNeural', batch_id=self.batch,
                                          sentence_pause_ms=1000, paragraph_pause_ms=300)
            job = self.flow.start_narration(self.batch)
            self.assertTrue(job.wait(15))
            product = self.flow.finish_narration(job)
            self.assertEqual(requests, [])
            self.assertEqual(product['duration_ms'], 2600)  # max(1000, 300), no trailing pause.
        pcm = subprocess.check_output([shutil.which('ffmpeg'), '-v', 'error', '-i',
            str(self.flow.narration_path(self.batch)), '-f', 's16le', '-ac', '1', '-ar', '24000', '-'])
        self.assertAlmostEqual(len(pcm) / 48000, 2.6, delta=.025)
        self.assertEqual(self.flow.texts(self.batch)[1], text)

    def test_quotes_and_punctuation_run_are_one_sentence_boundary(self):
        self.refresh_voices()
        text = '「第一句。」 下一句！？ 最後一句。'
        self.flow.save_draft(self.batch, text)
        self.flow.confirm_reading(self.batch)
        self.flow.save_voice_settings('zh-TW-TestNeural', batch_id=self.batch,
                                      sentence_pause_ms=200, paragraph_pause_ms=800)
        audio, requests = self.audio(), []
        class Service:
            def __init__(self, text, *args, **kwargs): requests.append(text)
            async def stream(self): yield dict(type='audio', data=audio)
        with patch('edge_tts.Communicate', Service):
            job = self.flow.start_narration(self.batch)
            self.assertTrue(job.wait(15))
            product = self.flow.finish_narration(job)
        self.assertEqual(requests, ['「第一句。」 ', '下一句！？ ', '最後一句。'])
        self.assertEqual([c['pause_after_ms'] for c in product['chunks']], [200, 200, 0])
        self.assertEqual(product['duration_ms'], 1000)

    def test_ascii_opening_quote_stays_with_its_sentence(self):
        self.refresh_voices()
        text = 'Hello. "Next sentence." Last.'
        self.flow.save_voice_settings('zh-TW-TestNeural', batch_id=self.batch, sentence_pause_ms=200)
        audio, requests = self.audio(), []
        class Service:
            def __init__(self, text, *args, **kwargs): requests.append(text)
            async def stream(self): yield dict(type='audio', data=audio)
        with patch('edge_tts.Communicate', Service):
            job = self.flow.start_voice_preview(self.batch, text=text, start=0, end=len(text))
            self.assertTrue(job.wait(15))
            self.flow.finish_voice_preview(job)
        self.assertEqual(requests, ['Hello. ', '"Next sentence." ', 'Last.'])
