import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ebook2mp4 import tts_control as control
from ebook2mp4.tts_services import request_audio
from ebook2mp4.workflow import ProjectError
import test_tts_retry as fixture


class ControlTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / '.scratch/test-runs')
        self.addCleanup(self.temp.cleanup)
        environment = patch.dict('os.environ', EBOOK2MP4_VOICE_HOME=self.temp.name)
        environment.start()
        self.addCleanup(environment.stop)
        self.value = dict(provider='fish-audio', model='s2.1-pro-free', voice='test', rate='+0%')

    async def test_persisted_cooldown_blocks_http_and_other_profile_with_same_key(self):
        requests = []
        def respond(body):
            requests.append(body)
            return 429, '75876', b'{"code":"daily_quota_exceeded","secret":"do-not-display"}'
        with patch('ebook2mp4.tts_services.credential', return_value='synthetic-key'), \
             patch('aiohttp.ClientSession', fixture.transport(respond)):
            with self.assertRaisesRegex(ProjectError, '配額已用盡') as error:
                await request_audio('private manuscript', self.value)
            self.assertNotIn('do-not-display', str(error.exception))
            with self.assertRaisesRegex(ProjectError, '冷卻尚未結束'):
                await request_audio('private manuscript', dict(self.value, profile='another'))
        self.assertEqual(len(requests), 1)
        raw = (Path(self.temp.name) / 'tts-usage.sqlite3').read_bytes()
        for secret in (b'synthetic-key', b'private manuscript', b'do-not-display'):
            self.assertNotIn(secret, raw)

    async def test_expiry_and_account_model_isolation(self):
        with patch.object(control.time, 'time', return_value=1000):
            control.record_limit(self.value, 'key', 100, 'HTTP 429')
            await control.before_request(self.value, 'other-key')
            await control.before_request(dict(self.value, model='other-model'), 'key')
        with patch.object(control.time, 'time', return_value=1101):
            await control.before_request(self.value, 'key')

    async def test_configured_rpm_reserves_spacing_and_wait_is_cancellable(self):
        (Path(self.temp.name) / 'tts-limits.json').write_text(json.dumps({
            'fish-audio:s2.1-pro-free': {'requests_per_minute': 2}}))
        with patch.object(control.time, 'time', return_value=1000):
            await control.before_request(self.value, 'key')
            with patch.object(control.asyncio, 'sleep') as sleep:
                await control.before_request(self.value, 'key')
                sleep.assert_awaited_once_with(30)
            task = asyncio.create_task(control.before_request(self.value, 'key'))
            await asyncio.sleep(0)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task

    async def test_classification_and_malformed_payload(self):
        for payload, label in [(b'{"code":"rate_limit_exceeded"}', '頻率'),
                               (b'{"message":"insufficient balance"}', '帳務'),
                               (b'not json', '無法'), (b'x'*70000, '過大')]:
            class Response:
                content = None
                async def iter_chunked(self, size):
                    yield payload
            response = Response()
            response.content = response
            result = await control.error_reason(response)
            self.assertTrue(label in result or ('未提供' in result and label == '無法'))
