import asyncio
import json
import tempfile
import unittest
import wave
import base64
import types
import subprocess
import sys
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

from ebook2mp4.tts_services import RetryableServiceError
from ebook2mp4.voice_media import speech_block
from ebook2mp4.workflow import ProjectError
import test_tts_retry as fixture


class FullRecovery(unittest.TestCase):
    setUp = fixture.RetryRecovery.setUp
    audio = fixture.RetryRecovery.audio
    release = fixture.RetryRecovery.release

    def test_two_processes_share_request_spacing(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'tts-limits.json').write_text(json.dumps({
                'gemini-tts:test': {'requests_per_minute': 120}}))
            environment = dict(os.environ, EBOOK2MP4_VOICE_HOME=directory)
            script = ('import asyncio,time; from ebook2mp4.tts_control import before_request; '
                      'asyncio.run(before_request(dict(provider="gemini-tts",model="test"),"synthetic-key")); '
                      'print(time.time())')
            workers = [subprocess.Popen([sys.executable, '-B', '-c', script], env=environment,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
            try:
                outputs = [worker.communicate(timeout=10) for worker in workers]
                self.assertEqual([worker.returncode for worker in workers], [0, 0], outputs)
                self.assertGreaterEqual(abs(float(outputs[0][0]) - float(outputs[1][0])), .45)
            finally:
                for worker in workers:
                    if worker.poll() is None:
                        worker.kill()
                    worker.wait()

    def test_real_limiter_narration_recovers_block_36(self):
        from ebook2mp4.tts_services import save_profile
        from ebook2mp4 import tts_control
        # Use the real limiter, unlike the older provider retry fixture.
        for cleanup in self._cleanups[-2:]:
            cleanup[0]()
        identity = save_profile('Gemini', 'gemini-tts', 'synthetic-key')
        value = self.flow.voice_settings(self.batch)
        value.update(provider='gemini-tts', profile=identity, model='test', voice='Kore')
        self.flow.save_voice_settings('Kore', batch_id=self.batch, settings_override=value)
        texts = [f'第{i}段測試。' for i in range(36)]
        self.flow.save_draft(self.batch, '\n\n'.join(texts))
        self.flow.confirm_reading(self.batch)
        audio = json.dumps({'steps': [{'type': 'model_output', 'content': [
            {'type': 'audio', 'data': base64.b64encode(self.audio()).decode()}]}]}).encode()
        requests = []
        now = [10000.0]
        real_sleep = asyncio.sleep

        async def sleep(delay):
            now[0] += delay
            await real_sleep(0)

        def respond(body):
            text = body['input'][0]['content'][0]['text']
            requests.append(text)
            if text == texts[-1] and requests.count(text) <= 4:
                return 429, '120', b'{"error":{"message":"rate limit"}}'
            return 200, '0', audio

        clock = types.SimpleNamespace(time=lambda: now[0], monotonic=lambda: now[0])
        with patch('aiohttp.ClientSession', fixture.transport(respond)), \
             patch.object(tts_control, 'time', clock), \
             patch('ebook2mp4.voice_media.time', clock), \
             patch('asyncio.sleep', sleep), \
             patch('ebook2mp4.tts_control.stamp_after', return_value='test time'):
            job = self.flow.start_narration(self.batch)
            self.addCleanup(self.release, self.flow, job)
            self.assertTrue(job.wait(60), job.state)
            self.assertEqual(job.state['status'], 'completed', job.state)
            self.flow.finish_narration(job)
        self.assertEqual(len(requests), 40)
        self.assertEqual(requests.count(texts[-1]), 5)
        self.assertFalse((self.flow.root / '.production.lock').exists())


class GeminiRecovery(unittest.IsolatedAsyncioTestCase):
    async def test_persistent_limits_and_long_delay_stop_without_network_loop(self):
        settings = dict(provider='gemini-tts', model='test', voice='Kore', rate='+0%', processing={})
        for seconds, expected in [(0, 30), (77813, 1)]:
            calls = []

            async def write(*args):
                calls.append(1)
                raise RetryableServiceError('HTTP 429', seconds, status=429)

            with tempfile.TemporaryDirectory() as directory, patch('ebook2mp4.voice.require_voice'), \
                 patch('ebook2mp4.tts_backend.write_speech', write), \
                 patch('ebook2mp4.voice_media.asyncio.sleep', new=AsyncMock()):
                with self.assertRaisesRegex(ProjectError, '停止自動重試'):
                    await speech_block('測試', settings, 'ffmpeg', Path(directory))
                self.assertFalse(list(Path(directory).glob('.block-*')))
            self.assertEqual(len(calls), expected)

    async def test_shared_cooldown_extends_and_cancel_leaves_database_available(self):
        from ebook2mp4 import tts_control as control
        import os
        settings = dict(provider='gemini-tts', model='test')
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, EBOOK2MP4_VOICE_HOME=directory):
            control.record_limit(settings, 'test-key', 120, 'HTTP 429', category='temporary')
            task = asyncio.create_task(control.before_request(settings, 'test-key'))
            await asyncio.sleep(.02)
            self.assertFalse(task.done())
            control.record_limit(settings, 'test-key', 150, 'HTTP 429', category='temporary')
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await asyncio.wait_for(task, 3)
            with control.database() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM usage').fetchone()[0], 1)

    async def test_classifies_quota_and_retry_info_without_exposing_payload(self):
        from ebook2mp4.tts_control import gemini_error

        class Response:
            content = None

            def __init__(self, payload):
                self.content = self
                self.payload = json.dumps(payload).encode()

            async def iter_chunked(self, size):
                yield self.payload

        retry = {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '150s'}
        quota = {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [
            {'quotaId': 'GenerateRequestsPerDayPerProject'}]}
        self.assertEqual(await gemini_error(Response({'error': {'message': 'quota_exceeded'}})), ('unknown', 0))
        self.assertEqual(await gemini_error(Response({'error': {'details': [retry, quota]}})), ('daily', 150))

    async def test_four_rate_limits_then_success(self):
        attempts = []

        async def write(text, settings, target):
            attempts.append(1)
            if len(attempts) <= 4:
                error = RetryableServiceError('HTTP 429', 0)
                error.status = 429
                raise error
            target.write_bytes(b'audio')

        async def decode(tool, args, **kwargs):
            with wave.open(args[-1], 'wb') as result:
                result.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
                result.writeframes(b'\0\0' * 24)

        settings = dict(provider='gemini-tts', model='test', voice='Kore', rate='+0%', processing={})
        with tempfile.TemporaryDirectory() as directory, \
             patch('ebook2mp4.voice.require_voice'), \
             patch('ebook2mp4.tts_backend.write_speech', write), \
             patch('ebook2mp4.voice_media.media_command', decode), \
             patch('ebook2mp4.voice_media.asyncio.sleep', new=AsyncMock()):
            result, reused = await speech_block('測試', settings, 'ffmpeg', Path(directory))
            self.assertTrue(result.exists())
            self.assertFalse(reused)
        self.assertEqual(len(attempts), 5)


if __name__ == '__main__':
    unittest.main()
