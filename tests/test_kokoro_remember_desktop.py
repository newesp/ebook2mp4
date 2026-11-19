"""Remember only successfully imported archives across package-page visits."""
from pathlib import Path
import unittest
from unittest.mock import patch

import test_voice_desktop as fixture
from ebook2mp4.kokoro_packages import remembered_archive


class RememberArchive(unittest.TestCase):
    setUp=fixture.VoiceDesktop.setUp

    def test_success_reopens_path_failure_preserves_it_and_missing_file_clears_it(self):
        with patch.dict('os.environ',EBOOK2MP4_KOKORO_HOME=str(self.path/'local-packages')):
            d=self.dialog
            d.service.set(d.service_labels['kokoro']);d.change_service();d.update_service_menu()
            d.service_menu.invoke(1);self.root.update()
            page=self.app.production.package_page
            original=self.path/'voice.zip';original.write_bytes(b'test fixture')
            class Finished:
                def __init__(self,status):self.state=dict(status=status,error='匯入失敗')
                def wait(self,timeout):return True
            page.path.set(str(original));page.job=Finished('completed');page.poll()
            self.assertEqual(remembered_archive(),str(original.resolve()))
            other=self.path/'other.zip';other.write_bytes(b'invalid fixture')
            page.path.set(str(other));page.job=Finished('failed');page.poll()
            self.assertEqual(remembered_archive(),str(original.resolve()))
            page.destroy();self.app.production.package_page=None
            d.service_menu.invoke(1);self.root.update()
            page=self.app.production.package_page
            self.assertEqual(page.path.get(),str(original.resolve()))
            original.unlink();page.refresh()
            self.assertEqual(page.path.get(),'')
            self.assertEqual(remembered_archive(),'')
            page.destroy();self.app.production.package_page=None
            d.service_menu.invoke(1);self.root.update()
            self.assertEqual(self.app.production.package_page.path.get(),'')


if __name__=='__main__':unittest.main()
