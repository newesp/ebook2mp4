"""Kokoro journeys through the agreed ProjectWorkflow seam."""
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from ebook2mp4.workflow import ProjectWorkflow, ProjectError


class LocalPackageJourney(unittest.TestCase):
    def wait_for(self,job,seconds):
        def stop():
            job.cancel()
            self.assertTrue(job.wait(30),'Test job did not release resources')
        self.addCleanup(stop)
        started=time.monotonic()
        self.assertTrue(job.wait(seconds),job.state)
        print(f'Public workflow wait: {time.monotonic()-started:.2f}s; {job.state["status"]}',flush=True)

    def setUp(self):
        base = Path(__file__).resolve().parents[1]/'.scratch/test-runs'
        base.mkdir(parents=True,exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)
        env=patch.dict(os.environ,EBOOK2MP4_KOKORO_HOME=str(self.path/'packages'))
        env.start();self.addCleanup(env.stop)
        self.flow=ProjectWorkflow.create(self.path/'book','本機語音')

    def test_invalid_package_does_not_activate_or_leave_installation(self):
        import zipfile
        archive=self.path/'bad.zip'
        with zipfile.ZipFile(archive,'w') as target:
            target.writestr('../escaped.txt',b'not a package')
        job=self.flow.start_voice_package_import(archive)
        self.wait_for(job,10)
        self.assertEqual(job.state['status'],'failed')
        self.assertEqual(self.flow.local_voice_packages(),[])
        self.assertFalse((self.path/'escaped.txt').exists())
        self.assertFalse(list((self.path/'packages').glob('.install-*')))

    def test_missing_package_explains_recovery_and_preserves_settings(self):
        original=self.flow.voice_settings()
        value=dict(original,provider='kokoro',voice='zf_001',package='kokoro-zh-cpu-0000000000000000',
                   model='01e7505bd6a7a2ac4975463114c3a7650a9f7218',processing='kokoro-t2s-v1')
        with self.assertRaisesRegex(ProjectError,'語音包'):
            self.flow.save_voice_settings('zf_001',settings_override=value)
        self.assertEqual(ProjectWorkflow.open(self.flow.root).voice_settings(),original)

    @unittest.skipUnless(os.environ.get('EBOOK2MP4_TEST_KOKORO_PACKAGE'),'real offline package required')
    def test_real_package_preview_reopen_and_offline_formal_reuse(self):
        archive=Path(os.environ['EBOOK2MP4_TEST_KOKORO_PACKAGE'])
        job=self.flow.start_voice_package_import(archive)
        self.wait_for(job,600)
        self.assertEqual(job.state['status'],'completed',job.state)
        installed=self.flow.local_voice_packages()
        self.assertEqual(len(installed),1)
        self.assertEqual(len(installed[0]['voices']),100)
        self.assertFalse(any(v['verified'] for v in installed[0]['voices']))
        # A damaged installed resource must be recoverable through re-import.
        worker=Path(installed[0]['path'])/'worker.py'
        worker.write_text('damaged',encoding='utf-8')
        repaired=self.flow.start_voice_package_import(archive)
        self.wait_for(repaired,600)
        self.assertEqual(repaired.state['status'],'completed',repaired.state)
        source=self.path/'source.txt';source.write_text('今天，歡迎閱讀。Hello world。',encoding='utf-8')
        batch=self.flow.import_txt(self.flow.inspect_txt(source))
        value=dict(self.flow.voice_settings(batch),provider='kokoro',voice='zf_001',
                   package=installed[0]['id'],model=installed[0]['model'],processing='kokoro-t2s-v1')
        self.flow.save_voice_settings('zf_001',batch_id=batch,settings_override=value)
        self.assertEqual(ProjectWorkflow.open(self.flow.root).voice_settings(batch),value)
        self.addCleanup(self.flow.unload_local_voice)
        preview=self.flow.start_voice_preview(batch,text=source.read_text(encoding='utf-8'),start=0,end=len(source.read_text(encoding='utf-8')))
        self.wait_for(preview,900)
        self.assertEqual(preview.state['status'],'completed',preview.state)
        result=self.flow.finish_voice_preview(preview)
        self.assertEqual(result['text'],source.read_text(encoding='utf-8'))
        loads=self.flow.local_voice_status()['loads']
        self.flow.confirm_reading(batch)
        narration=self.flow.start_narration(batch,allow_network=False)
        self.wait_for(narration,60)
        self.assertEqual(narration.state['status'],'completed',narration.state)
        product=self.flow.finish_narration(narration)
        self.assertTrue(all(c['reused'] for c in product['chunks']))
        self.assertEqual(self.flow.local_voice_status()['loads'],loads)
        self.flow.unload_local_voice()
        self.assertIsNone(self.flow.local_voice_status()['pid'])
        self.flow.remove_voice_package(installed[0]['id'])
        self.assertEqual(self.flow.local_voice_packages(),[])
        self.assertTrue(self.flow.narration_path(batch).exists())


if __name__=='__main__':unittest.main()
