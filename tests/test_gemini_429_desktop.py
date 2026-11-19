import time
import unittest
from unittest.mock import patch

import test_tts_retry_desktop as fixture
from ebook2mp4.tts_services import save_profile


class GeminiWait(fixture.RetryDesktop):
    def test_gemini_wait_and_cancel(self):
        self.prepare(1)
        identity = save_profile('Gemini', 'gemini-tts', 'synthetic-key')
        value = self.flow.voice_settings(self.batch)
        value.update(provider='gemini-tts', profile=identity, model='test', voice='Kore')
        self.flow.save_voice_settings('Kore', batch_id=self.batch, settings_override=value)
        self.dialog.reload_button.invoke()
        self.poll()
        self.root.state('normal')
        self.root.geometry('1040x640')
        with patch('aiohttp.ClientSession', fixture.retry_fixture.transport(
                lambda body: (429, '120', b'{"error":{"message":"rate limit"}}'))):
            self.dialog.start_button.invoke()
            deadline = time.monotonic() + 10
            while '等待' not in self.dialog.status.cget('text') and time.monotonic() < deadline:
                self.root.update()
                time.sleep(.02)
            self.assertIn('等待', self.dialog.status.cget('text'))
            self.assertEqual(str(self.dialog.cancel_button.cget('state')), 'normal')
            self.capture('EBOOK2MP4_GEMINI_429_SCREENSHOT')
            self.dialog.cancel_button.invoke()
            self.poll()
        self.assertEqual(self.flow.narration_runs(self.batch)[-1]['progress']['status'], 'cancelled')
        self.assertFalse((self.flow.root / '.production.lock').exists())


if __name__ == '__main__':
    unittest.main()
