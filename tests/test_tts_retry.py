"""Retry-After recovery through the real provider and narration pipeline."""
import asyncio
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import threading
import unittest
from unittest.mock import patch, AsyncMock

import test_voice as fixture
from ebook2mp4.narration import NarrationJob
from ebook2mp4.tts_services import RetryableServiceError, request_audio, save_profile
from ebook2mp4.workflow import ProjectWorkflow


def transport(respond):
    class Response:
        def __init__(self, status, delay, payload):
            self.status = status
            self.headers = {'Retry-After': delay}
            self.payload = payload
            self.content = self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def iter_chunked(self, size):
            yield self.payload

    class Session:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def post(self, url, **kwargs):
            return Response(*respond(kwargs['json']))

    return Session


class RetryRecovery(unittest.TestCase):
    def setUp(self):
        fixture.VoiceJourney.setUp(self)
        for name, replacement in [('before_request', AsyncMock()), ('record_limit', None)]:
            control = patch('ebook2mp4.tts_control.' + name, new=replacement) if replacement else patch('ebook2mp4.tts_control.' + name)
            control.start()
            self.addCleanup(control.stop)
    audio = fixture.VoiceJourney.audio

    def prepare(self, count=36):
        identity = save_profile('Fish', 'fish-audio', 'synthetic-key')
        value = self.flow.voice_settings(self.batch)
        value.update(provider='fish-audio', profile=identity, model='s2.1-pro', voice='test-voice')
        self.flow.save_voice_settings('test-voice', batch_id=self.batch, settings_override=value)
        # Repeated verified audio makes a 36-block recovery fast and deterministic.
        self.flow.save_draft(self.batch, '\n\n'.join(['已完成。'] * (count - 1) + ['待完成。']))
        self.flow.confirm_reading(self.batch)
        return self.audio()

    def release(self, flow, job):
        job.cancel()
        self.assertTrue(job.wait(5))
        if job.production_lock is not None:
            flow.discard_narration(job)

    def test_resume_block_36_waits_for_long_retry_after_and_reuses_first_35(self):
        audio = self.prepare()
        requests, sleeps = [], []
        real_sleep = asyncio.sleep

        async def virtual_sleep(delay):
            if delay:
                sleeps.append(delay)
            await real_sleep(0)

        def unavailable(body):
            return (429, '120', b'') if body['text'] == '待完成。' else (200, '0', audio)

        with patch('aiohttp.ClientSession', transport(unavailable)), patch('asyncio.sleep', virtual_sleep):
            job = self.flow.start_narration(self.batch)
            self.addCleanup(self.release, self.flow, job)
            self.assertTrue(job.wait(10))
            self.assertEqual(job.state['status'], 'failed')
            self.assertEqual(job.state['chunks'][-1]['attempts'], 3)
            self.assertIn('HTTP 429', job.state['error'])
            self.assertIn('120 秒', job.state['error'])
            self.assertEqual(sleeps, [120, 120])
            self.flow.discard_narration(job)

        reopened = ProjectWorkflow.open(self.flow.root)
        run = reopened.narration_runs(self.batch)[-1]
        self.assertEqual(run['reusable'], 35)
        sleeps.clear()

        def restored(body):
            requests.append(body['text'])
            return (429, '120', b'') if len(requests) == 1 else (200, '0', audio)

        with patch('aiohttp.ClientSession', transport(restored)), patch('asyncio.sleep', virtual_sleep):
            job = reopened.resume_narration(self.batch, run['snapshot']['id'])
            self.addCleanup(self.release, reopened, job)
            self.assertTrue(job.wait(10))
            self.assertTrue(requests, 'Resume must issue a fresh HTTP request')
            self.assertEqual(job.state['status'], 'completed', job.state['error'])
            reopened.finish_narration(job)

        self.assertEqual(sleeps, [120])
        self.assertEqual(requests, ['待完成。', '待完成。'])
        self.assertFalse((reopened.root / '.production.lock').exists())

    def test_cancel_during_long_wait_releases_resources_and_keeps_successful_audio(self):
        audio = self.prepare(2)
        waiting = threading.Event()
        real_save = NarrationJob.save_progress

        def save(job, **changes):
            real_save(job, **changes)
            if changes.get('phase') == '等待 120 秒後重試':
                waiting.set()

        def unavailable(body):
            return (503, '120', b'') if body['text'] == '待完成。' else (200, '0', audio)

        with patch('aiohttp.ClientSession', transport(unavailable)), \
             patch('ebook2mp4.narration.NarrationJob.save_progress', save):
            job = self.flow.start_narration(self.batch)
            self.addCleanup(self.release, self.flow, job)
            self.assertTrue(waiting.wait(10), job.state)
            self.assertFalse(job.wait(0))
            self.assertEqual(job.state['status'], 'running')
            job.cancel()
            self.assertTrue(job.wait(3))
            self.assertEqual(job.state['status'], 'cancelled')
            self.flow.discard_narration(job)

        self.assertFalse((self.flow.root / '.production.lock').exists())
        self.assertFalse((job.folder / 'media').exists())
        self.assertFalse(list(job.folder.parent.glob('voice-blocks/.block-*')))
        run = ProjectWorkflow.open(self.flow.root).narration_runs(self.batch)[-1]
        self.assertEqual(run['reusable'], 1)

    def test_excessive_retry_after_stops_instead_of_waiting_21_hours(self):
        self.prepare(1)
        sleeps = []
        real_sleep = asyncio.sleep

        async def virtual_sleep(delay):
            if delay:
                sleeps.append(delay)
            await real_sleep(0)

        with patch('aiohttp.ClientSession', transport(lambda body: (429, '77813', b''))), \
             patch('asyncio.sleep', virtual_sleep):
            job = self.flow.start_narration(self.batch)
            self.addCleanup(self.release, self.flow, job)
            self.assertTrue(job.wait(5))
            self.assertEqual(job.state['status'], 'failed')
            self.assertEqual(sleeps, [], 'A 21-hour cooldown must not keep production busy')
            self.assertEqual(job.state['chunks'][0]['attempts'], 1)
            self.assertIn('77813', job.state['error'])
            self.assertIn('HTTP 429', job.state['error'])
            self.assertIn('停止自動重試', job.state['error'])
            self.flow.discard_narration(job)
        self.assertFalse((self.flow.root / '.production.lock').exists())

    def test_retry_wait_budget_stops_at_five_minutes_total(self):
        self.prepare(1)
        real_sleep = asyncio.sleep
        for header, expected_sleeps, attempts in [('300', [300], 2), ('301', [], 1), ('200', [200], 2)]:
            with self.subTest(header=header):
                sleeps = []

                async def virtual_sleep(delay):
                    if delay:
                        sleeps.append(delay)
                    await real_sleep(0)

                with patch('aiohttp.ClientSession', transport(lambda body: (503, header, b''))), \
                     patch('asyncio.sleep', virtual_sleep):
                    job = self.flow.start_narration(self.batch)
                    self.addCleanup(self.release, self.flow, job)
                    self.assertTrue(job.wait(5))
                    self.assertEqual(job.state['status'], 'failed')
                    self.assertEqual(sleeps, expected_sleeps)
                    self.assertEqual(job.state['chunks'][0]['attempts'], attempts)
                    self.assertIn('HTTP 503', job.state['error'])
                    self.assertIn('停止自動重試', job.state['error'])
                    self.flow.discard_narration(job)

    def test_resume_after_excessive_cooldown_preserves_successful_block(self):
        audio = self.prepare(2)

        def limited(body):
            return (429, '77813', b'') if body['text'] == '待完成。' else (200, '0', audio)

        with patch('aiohttp.ClientSession', transport(limited)):
            job = self.flow.start_narration(self.batch)
            self.addCleanup(self.release, self.flow, job)
            self.assertTrue(job.wait(5), job.state)
            self.assertEqual(job.state['status'], 'failed')
            self.flow.discard_narration(job)
        reopened = ProjectWorkflow.open(self.flow.root)
        run = reopened.narration_runs(self.batch)[-1]
        self.assertEqual(run['reusable'], 1)
        self.assertEqual(run['progress']['chunks'][1]['status'], 'failed')
        self.assertIn('77813', run['progress']['chunks'][1]['error'])
        requests = []

        def restored(body):
            requests.append(body['text'])
            return 200, '0', audio

        with patch('aiohttp.ClientSession', transport(restored)):
            job = reopened.resume_narration(self.batch, run['snapshot']['id'])
            self.addCleanup(self.release, reopened, job)
            self.assertTrue(job.wait(10), job.state)
            self.assertEqual(job.state['status'], 'completed', job.state)
            reopened.finish_narration(job)
        self.assertEqual(requests, ['待完成。'])
        self.assertFalse((reopened.root / '.production.lock').exists())


class RetryHeaders(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        for name in ('before_request', 'record_limit'):
            control = patch('ebook2mp4.tts_control.' + name)
            control.start()
            self.addCleanup(control.stop)
    async def test_long_delay_is_retryable_for_both_providers(self):
        for provider in ('fish-audio', 'gemini-tts'):
            for status in (429, 503):
                with self.subTest(provider=provider, status=status):
                    with patch('ebook2mp4.tts_services.credential', return_value='synthetic-key'), \
                         patch('aiohttp.ClientSession', transport(lambda body: (status, '120', b''))):
                        with self.assertRaises(RetryableServiceError) as error:
                            await request_audio('text', dict(provider=provider, model='test', voice='test', rate='+0%'))
                    self.assertEqual(error.exception.retry_after, 120)

    async def test_http_date_and_invalid_delays(self):
        fixed = datetime(2026, 10, 31, tzinfo=timezone.utc)
        headers = [(format_datetime(fixed + timedelta(seconds=120), usegmt=True), 120),
                   ('60', 60), ('61', 61), ('-1', 0), ('invalid', 0), ('inf', 0), ('nan', 0)]
        for header, expected in headers:
            with self.subTest(header=header):
                with patch('ebook2mp4.tts_services.credential', return_value='synthetic-key'), \
                     patch('aiohttp.ClientSession', transport(lambda body: (429, header, b''))), \
                     patch('ebook2mp4.tts_services.datetime') as clock:
                    clock.now.return_value = fixed
                    with self.assertRaises(RetryableServiceError) as error:
                        await request_audio('text', dict(provider='fish-audio', model='test', voice='test', rate='+0%'))
                self.assertEqual(error.exception.retry_after, expected or 60)


if __name__ == '__main__':
    unittest.main()
