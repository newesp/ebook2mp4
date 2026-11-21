"""Windows worker lifecycle through public preview operations with a protocol fixture."""
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch
import zipfile

import test_kokoro
from ebook2mp4.kokoro_runtime import engine
from ebook2mp4.workflow import ProjectError


WORKER = r'''
import json, os, subprocess, sys, time, wave
from pathlib import Path
base = Path(__file__).parent
child = None
def send(event, **data):
    print(json.dumps(dict(event=event, **data)), flush=True)
for line in sys.stdin:
    value = json.loads(line)
    if value['action'] == 'load':
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(600)'])
        (base/'descendant.txt').write_text(str(child.pid))
        send('ready', device='cpu', cuda=None)
    elif value['action'] == 'synthesize':
        if 'crash' in value['text']:
            os._exit(23)
        if 'slow' in value['text']:
            send('phase', phase='fixture-slow')
            time.sleep(2)
        with wave.open(value['output'], 'wb') as audio:
            audio.setparams((1, 2, 24000, 0, 'NONE', ''))
            audio.writeframes(b'\0\0' * 4800)
        send('completed')
'''


class WorkerLifecycle(test_kokoro.LocalPackageJourney):
    # Keep the fixture setup without inheriting the unrelated package tests.
    test_invalid_package_does_not_activate_or_leave_installation = None
    test_reimport_repairs_missing_receipt_and_rejects_corrupt_input = None
    test_missing_package_explains_recovery_and_preserves_settings = None
    test_real_package_preview_reopen_and_offline_formal_reuse = None

    def setUp(self):
        super().setUp()
        payload = WORKER.encode()
        self.metadata = dict(id='kokoro-zh-cpu-0000000000000002', model='0'*40,
            processing='kokoro-t2s-v1', python=sys.executable,
            voices=[dict(id='zf_001', verified=False)],
            files=[dict(path='worker.py', bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())])
        trusted = patch('ebook2mp4.kokoro_packages.release', return_value=self.metadata)
        trusted.start()
        self.addCleanup(trusted.stop)
        idle = patch('ebook2mp4.kokoro_runtime.IDLE_SECONDS', 60)
        idle.start()
        self.addCleanup(idle.stop)
        self.addCleanup(self.flow.unload_local_voice)
        archive = self.path/'fixture.zip'
        with zipfile.ZipFile(archive, 'w') as output:
            output.writestr('package.json', json.dumps(self.metadata))
            output.writestr('worker.py', payload)
        job = self.flow.start_voice_package_import(archive)
        self.wait_for(job, 10)
        self.assertEqual(job.state['status'], 'completed', job.state)
        self.folder = Path(self.flow.local_voice_packages()[0]['path'])
        source = self.path/'text.txt'
        source.write_text('測試。', encoding='utf-8')
        self.batch = self.flow.import_txt(self.flow.inspect_txt(source))
        settings = dict(self.flow.voice_settings(self.batch), provider='kokoro', voice='zf_001',
                        package=self.metadata['id'], model=self.metadata['model'], processing='kokoro-t2s-v1')
        self.flow.save_voice_settings('zf_001', batch_id=self.batch, settings_override=settings)

    def preview(self, text):
        return self.flow.start_voice_preview(self.batch, text=text, start=0, end=len(text))

    def finish(self, job):
        self.wait_for(job, 15)
        self.assertEqual(job.state['status'], 'completed', job.state)
        return self.flow.finish_voice_preview(job)

    def handles(self):
        api = ctypes.WinDLL('kernel32', use_last_error=True)
        api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        api.OpenProcess.restype = wintypes.HANDLE
        api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        api.CloseHandle.argtypes = [wintypes.HANDLE]
        pids = [self.flow.local_voice_status()['pid'], int((self.folder/'descendant.txt').read_text())]
        handles = [api.OpenProcess(0x100000, False, pid) for pid in pids]
        self.assertTrue(all(handles))
        for handle in handles:
            self.addCleanup(api.CloseHandle, handle)
        return api, handles

    def test_expired_timer_cannot_unload_a_newer_preview(self):
        self.finish(self.preview('first'))
        old_timer = engine().timer
        self.finish(self.preview('second'))
        before = self.flow.local_voice_status()
        # A cancelled timer callback can already be queued behind the engine lock.
        old_timer.function(*old_timer.args, **old_timer.kwargs)
        self.assertEqual(self.flow.local_voice_status()['pid'], before['pid'])
        self.assertEqual(self.flow.local_voice_status()['loads'], 1)

    def test_busy_idle_cancel_failure_and_retry_release_process_tree(self):
        self.finish(self.preview('initial'))
        api, handles = self.handles()
        previous = self.flow.voice_preview(self.batch)
        with patch('ebook2mp4.kokoro_runtime.IDLE_SECONDS', .3):
            job = self.preview('slow cancel')
            deadline = time.monotonic()+5
            while self.flow.local_voice_status()['phase'] != 'fixture-slow':
                self.assertFalse(job.wait(.02), job.state)
                self.assertLess(time.monotonic(), deadline)
            time.sleep(.5)
            self.assertIsNotNone(self.flow.local_voice_status()['pid'])
            with self.assertRaises(ProjectError):
                self.flow.remove_voice_package(self.metadata['id'])
            job.cancel()
            self.assertTrue(job.wait(10))
            self.flow.discard_voice_preview(job)
            self.assertEqual(self.flow.voice_preview(self.batch)['id'], previous['id'])
            for handle in handles:
                self.assertEqual(api.WaitForSingleObject(handle, 5000), 0)
            failed = self.preview('crash')
            self.wait_for(failed, 10)
            self.assertEqual(failed.state['status'], 'failed')
            self.flow.discard_voice_preview(failed)
            self.assertIsNone(self.flow.local_voice_status()['pid'])
            retry = self.preview('slow retry')
            deadline = time.monotonic()+5
            while self.flow.local_voice_status()['phase'] != 'fixture-slow':
                self.assertFalse(retry.wait(.02), retry.state)
                self.assertLess(time.monotonic(), deadline)
            api, handles = self.handles()
            self.finish(retry)
            for handle in handles:
                self.assertEqual(api.WaitForSingleObject(handle, 5000), 0)
            self.assertIsNone(self.flow.local_voice_status()['pid'])
            self.assertFalse(list(self.folder.parent.glob('.worker-*')))
        self.finish(self.preview('after idle'))
        self.assertGreaterEqual(self.flow.local_voice_status()['loads'], 3)
        api, handles = self.handles()
        self.flow.unload_local_voice()
        for handle in handles:
            self.assertEqual(api.WaitForSingleObject(handle, 5000), 0)
        self.assertFalse(list(self.folder.parent.glob('.worker-*')))
