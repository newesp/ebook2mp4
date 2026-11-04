"""Public workflow regression for the built-in service capability seam."""
import unittest
from unittest.mock import patch

import test_voice as fixture
from ebook2mp4.tts_services import save_profile
from ebook2mp4.workflow import ProjectWorkflow, ProjectError, digest, encode


class ServiceJourneys(unittest.TestCase):
    setUp = fixture.VoiceJourney.setUp
    refresh_voices = fixture.VoiceJourney.refresh_voices
    audio = fixture.VoiceJourney.audio

    def test_all_cloud_services_refuse_uncached_narration_without_consent(self):
        self.refresh_voices()
        for provider in ('edge-tts', 'gemini-tts', 'fish-audio'):
            with self.subTest(provider=provider):
                value = self.flow.voice_settings(self.batch)
                value.update(provider=provider, voice='zh-TW-TestNeural')
                if provider != 'edge-tts':
                    value.update(profile=save_profile(provider, provider, 'synthetic-key'),
                                 model='gemini-3.8-flash-tts' if provider=='gemini-tts' else 's2.1-pro',
                                 voice='Kore' if provider=='gemini-tts' else 'reference-voice')
                self.flow.save_voice_settings(value['voice'], batch_id=self.batch, settings_override=value)
                self.flow.save_draft(self.batch, '未快取的文字。' + provider)
                self.flow.confirm_reading(self.batch)
                with patch('edge_tts.Communicate') as edge, patch('aiohttp.ClientSession') as http:
                    job = self.flow.start_narration(self.batch, allow_network=False)
                    try:
                        self.assertTrue(job.wait(10), job.state)
                        self.assertEqual(job.state['status'], 'failed')
                        self.assertIn('同意', job.state['error'])
                        edge.assert_not_called()
                        http.assert_not_called()
                    finally:
                        job.cancel()
                        self.assertTrue(job.wait(5))
                        self.flow.discard_narration(job)
                reopened = ProjectWorkflow.open(self.flow.root)
                self.assertEqual(reopened.voice_settings(self.batch), value)
                self.assertEqual(reopened.texts(self.batch)[1], '未快取的文字。' + provider)

    def test_legacy_pcm_cache_and_snapshot_rules_remain_usable_offline(self):
        self.refresh_voices()
        self.flow.save_voice_settings('zh-TW-TestNeural', batch_id=self.batch)
        self.flow.save_draft(self.batch, '第一段。')
        self.flow.confirm_reading(self.batch)
        # Frozen identity from the pre-K02 block format. Populate a complete PCM
        # cache as an older application would, then observe only public behavior.
        import subprocess
        import shutil
        cache = self.flow.root/'batches'/self.batch/'voice-blocks'
        cache.mkdir(parents=True,exist_ok=True)
        key = '46545532b103c3a4885e16c143cb6e5b87e61ca3eaa24a01ed883a60f80f2002'
        pcm = cache/(key+'.wav')
        subprocess.run([shutil.which('ffmpeg'), '-v','error','-f','lavfi','-i',
                        'sine=frequency=440:duration=0.2','-ac','1','-ar','24000',
                        '-c:a','pcm_s16le','-y',str(pcm)], check=True)
        (cache/(key+'.json')).write_bytes(encode(dict(sha256=digest(pcm.read_bytes()))))
        reopened = ProjectWorkflow.open(self.flow.root)
        inspected = reopened.inspect_narration(self.batch)
        self.assertEqual(inspected['reusable'],1)
        self.assertEqual(inspected['snapshot']['rules_sha256'],
                         'cf79d3f4f61dd4fa9bd18e78d4437c590c565bebdbd38538e4dbb6419c4546af')
        with patch('edge_tts.Communicate') as transport:
            job = reopened.start_narration(self.batch,allow_network=False)
            published = False
            try:
                self.assertTrue(job.wait(15),job.state)
                product = reopened.finish_narration(job)
                published = True
            finally:
                if not published:
                    job.cancel()
                    self.assertTrue(job.wait(5))
                    reopened.discard_narration(job)
            transport.assert_not_called()
        self.assertTrue(product['chunks'][0]['reused'])
        self.assertEqual(product['text'],'第一段。')
        self.assertTrue(reopened.narration_path(self.batch).is_file())
        self.assertIn('第一段。',reopened.narration_path(self.batch,'srt').read_text(encoding='utf-8-sig'))

    def test_uninstalled_local_service_is_not_advertised_as_usable(self):
        before = self.flow.voice_settings(self.batch)
        value = dict(before,provider='kokoro',voice='zf_001')
        with self.assertRaises(ProjectError):
            self.flow.save_voice_settings('zf_001',batch_id=self.batch,settings_override=value)
        self.assertEqual(ProjectWorkflow.open(self.flow.root).voice_settings(self.batch),before)


if __name__ == '__main__':
    unittest.main()
