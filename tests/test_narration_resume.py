"""Recovery journeys at the agreed ProjectWorkflow seam."""
import asyncio
import threading
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_narration as fixture
from ebook2mp4.workflow import ProjectError, ProjectWorkflow


class NarrationRecovery(unittest.TestCase):
    setUp = fixture.NarrationJourney.setUp
    refresh_voices = fixture.NarrationJourney.refresh_voices
    audio = fixture.NarrationJourney.audio
    prepare = fixture.NarrationJourney.prepare

    def test_cancel_reopen_resume_reuses_successful_blocks(self):
        self.prepare('第一段。\n\n第二段。\n\n第三段。')
        audio, requests = self.audio(), []
        waiting = threading.Event()
        class Interrupted:
            def __init__(self, text, *args, **kwargs):
                self.text = text
                requests.append(text)
            async def stream(self):
                if self.text == '第二段。':
                    waiting.set()
                    await asyncio.sleep(60)
                yield dict(type='audio', data=audio)
        with patch('edge_tts.Communicate', Interrupted):
            job = self.flow.start_narration(self.batch)
            self.assertTrue(waiting.wait(10))
            job.cancel()
            self.assertTrue(job.wait(5))
            self.flow.discard_narration(job)
        reopened = ProjectWorkflow.open(self.flow.root)
        run = reopened.narration_runs(self.batch)[-1]
        self.assertEqual(run['progress']['status'], 'cancelled')
        self.assertEqual(run['reusable'], 1)
        class Restored(Interrupted):
            async def stream(self):
                yield dict(type='audio', data=audio)
        requests.clear()
        with patch('edge_tts.Communicate', Restored):
            job = reopened.resume_narration(self.batch, run['snapshot']['id'])
            self.assertTrue(job.wait(20), job.state)
            result = reopened.finish_narration(job)
        self.assertEqual(requests, ['第二段。', '第三段。'])
        self.assertEqual(result['id'], run['snapshot']['id'])
        self.assertEqual(result['text'], '第一段。\n\n第二段。\n\n第三段。')
        self.assertTrue(reopened.narration_path(self.batch).is_file())

    def test_hard_exit_recovers_lease_and_rejects_changed_settings(self):
        self.prepare('第一段。\n\n第二段。')
        self.audio()
        script = '''
import asyncio, os, sys
from unittest.mock import patch
from pathlib import Path
from ebook2mp4.workflow import ProjectWorkflow
flow = ProjectWorkflow.open(sys.argv[1])
audio = Path(sys.argv[2]).read_bytes()
class Service:
    def __init__(self, text, *a, **k): self.text = text
    async def stream(self):
        if self.text == '第二段。': os._exit(0)
        yield dict(type='audio', data=audio)
with patch('edge_tts.Communicate', Service):
    job = flow.start_narration(sys.argv[3])
    job.wait(20)
os._exit(2)
'''
        subprocess.run([sys.executable, '-c', script, str(self.flow.root),
                        str(self.path / '服務音訊.mp3'), self.batch], check=True, timeout=30)
        reopened = ProjectWorkflow.open(self.flow.root)
        run = reopened.narration_runs(self.batch)[-1]
        self.assertEqual(run['progress']['status'], 'interrupted')
        self.assertEqual(run['reusable'], 1)
        reopened.save_voice_settings('en-US-TestNeural', batch_id=self.batch)
        with self.assertRaisesRegex(ProjectError, '變更'):
            reopened.resume_narration(self.batch, run['snapshot']['id'])
        reopened.save_voice_settings('zh-TW-TestNeural', batch_id=self.batch)
        audio, requests = self.audio(), []
        class Service:
            def __init__(self, text, *a, **k): requests.append(text)
            async def stream(self): yield dict(type='audio', data=audio)
        with patch('edge_tts.Communicate', Service):
            job = reopened.resume_narration(self.batch, run['snapshot']['id'])
            self.assertTrue(job.wait(15))
            reopened.finish_narration(job)
        self.assertEqual(requests, ['第二段。'])
        self.assertFalse((reopened.root / '.production.lock').exists())

    def test_failed_assembly_resumes_offline_and_preserves_previous_product(self):
        self.prepare('第一段。\n\n第二段。')
        audio, requests = self.audio(), []
        class Service:
            def __init__(self, text, *a, **k): requests.append(text)
            async def stream(self): yield dict(type='audio', data=audio)
        with patch('edge_tts.Communicate', Service):
            job=self.flow.start_narration(self.batch)
            self.assertTrue(job.wait(15))
            previous=self.flow.finish_narration(job)
            old_audio=self.flow.narration_path(self.batch).read_bytes()
            old_srt=self.flow.narration_path(self.batch,'srt').read_bytes()
            self.flow.save_voice_settings('zh-TW-TestNeural','+10%',batch_id=self.batch)
            original_replace=os.replace
            def no_space(source,target):
                if str(target).endswith('narration.srt'):
                    raise OSError('disk full')
                return original_replace(source,target)
            with patch('os.replace',side_effect=no_space):
                job=self.flow.start_narration(self.batch)
                self.assertTrue(job.wait(15))
                self.assertEqual(job.state['status'],'failed')
                self.flow.discard_narration(job)
        self.assertEqual(self.flow.narration(self.batch)['id'],previous['id'])
        self.assertEqual(self.flow.narration_path(self.batch).read_bytes(),old_audio)
        self.assertEqual(self.flow.narration_path(self.batch,'srt').read_bytes(),old_srt)
        reopened=ProjectWorkflow.open(self.flow.root)
        run=reopened.narration_runs(self.batch)[-1]
        self.assertEqual(run['remaining'],0)
        # No catalog or online credentials are needed for local-only assembly.
        (self.path/'voice-cache'/'voices.json').unlink()
        requests.clear()
        with patch('edge_tts.Communicate',side_effect=AssertionError('unexpected TTS')):
            job=reopened.resume_narration(self.batch,run['snapshot']['id'])
            self.assertTrue(job.wait(15),job.state)
            reopened.finish_narration(job)
        self.assertEqual(requests,[])
        self.assertEqual(reopened.narration_runs(self.batch)[-1]['progress']['resume_history'][-1]['status'],'failed')

    def test_corrupt_cache_is_not_reused(self):
        self.prepare('第一段。\n\n第二段。')
        audio, requests=self.audio(),[]
        class Service:
            def __init__(self,text,*a,**k): requests.append(text)
            async def stream(self): yield dict(type='audio',data=audio)
        with patch('edge_tts.Communicate',Service):
            job=self.flow.start_narration(self.batch)
            self.assertTrue(job.wait(15))
            # Discard unpublished assembly, keeping its verified speech blocks.
            self.flow.discard_narration(job)
        run=self.flow.narration_runs(self.batch)[-1]
        cache=self.flow.root/'batches'/self.batch/'voice-blocks'
        target=next(cache.glob('*.wav'))
        target.write_bytes(target.read_bytes()[:45])
        reopened=ProjectWorkflow.open(self.flow.root)
        self.assertEqual(reopened.narration_runs(self.batch)[-1]['reusable'],1)
        requests.clear()
        with patch('edge_tts.Communicate',Service):
            job=reopened.resume_narration(self.batch,run['snapshot']['id'])
            self.assertTrue(job.wait(15))
            reopened.finish_narration(job)
        self.assertEqual(len(requests),1)

    def test_offline_permission_is_enforced_after_cache_changes(self):
        self.prepare('第一段。')
        audio=self.audio()
        class Service:
            def __init__(self,*a,**k): pass
            async def stream(self): yield dict(type='audio',data=audio)
        with patch('edge_tts.Communicate',Service):
            job=self.flow.start_narration(self.batch)
            self.assertTrue(job.wait(15))
            self.flow.discard_narration(job)

    def test_assembly_cancel_joins_media_process_and_resumes_without_tts(self):
        self.prepare('第一段。\n\n第二段。')
        audio=self.audio()
        class Service:
            def __init__(self,*a,**k): pass
            async def stream(self): yield dict(type='audio',data=audio)
        with patch('edge_tts.Communicate',Service):
            job=self.flow.start_narration(self.batch)
            self.assertTrue(job.wait(15))
            previous=self.flow.finish_narration(job)
        old_audio=self.flow.narration_path(self.batch).read_bytes()
        old_srt=self.flow.narration_path(self.batch,'srt').read_bytes()
        started=threading.Event()
        processes=[]
        original_exec=asyncio.create_subprocess_exec
        async def block_encoder(tool,*arguments,**options):
            if 'libmp3lame' in arguments:
                process=await original_exec(sys.executable,'-c','import time; time.sleep(60)',**options)
                processes.append(process)
                started.set()
                return process
            return await original_exec(tool,*arguments,**options)
        with patch('asyncio.create_subprocess_exec',side_effect=block_encoder), \
                patch('edge_tts.Communicate',side_effect=AssertionError('cached speech must not transmit')):
            job=self.flow.start_narration(self.batch)
            self.assertTrue(started.wait(10))
            job.cancel()
            self.assertTrue(job.wait(10))
            self.assertEqual(job.state['status'],'cancelled')
            self.assertIsNotNone(processes[0].returncode)
            self.flow.discard_narration(job)
        self.assertEqual(self.flow.narration(self.batch)['id'],previous['id'])
        self.assertEqual(self.flow.narration_path(self.batch).read_bytes(),old_audio)
        self.assertEqual(self.flow.narration_path(self.batch,'srt').read_bytes(),old_srt)
        reopened=ProjectWorkflow.open(self.flow.root)
        run=reopened.narration_runs(self.batch)[-1]
        with patch('edge_tts.Communicate',side_effect=AssertionError('offline assembly must not transmit')):
            job=reopened.resume_narration(self.batch,run['snapshot']['id'],allow_network=False)
            self.assertTrue(job.wait(15))
            reopened.finish_narration(job)
        run=self.flow.narration_runs(self.batch)[-1]
        self.assertEqual(run['remaining'],0)
        next((self.flow.root/'batches'/self.batch/'voice-blocks').glob('*.wav')).unlink()
        with patch('edge_tts.Communicate',side_effect=AssertionError('must not transmit')):
            job=self.flow.resume_narration(self.batch,run['snapshot']['id'],allow_network=False)
            self.assertTrue(job.wait(15))
            self.assertEqual(job.state['status'],'failed')
            self.assertIn('同意',job.state['error'])
            self.flow.discard_narration(job)


if __name__ == '__main__':
    unittest.main()
