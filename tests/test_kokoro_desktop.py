"""Native UI additions preserve the incumbent voice page structure."""
import unittest
from unittest.mock import patch
import test_voice_desktop as fixture


class LocalDesktop(unittest.TestCase):
    setUp=fixture.VoiceDesktop.setUp

    def test_local_service_reuses_controls_and_package_page_preserves_text(self):
        d=self.dialog
        self.assertIn('kokoro',d.service_labels)
        d.service.set(d.service_labels['kokoro']);d.change_service();self.root.update()
        self.assertFalse(d.consent_control.winfo_ismapped())
        self.assertFalse(d.refresh_button.winfo_ismapped())
        self.assertEqual(str(d.preview_button.cget('state')),'disabled')
        d.outgoing.delete('1.0','end');d.outgoing.insert('1.0','保留試聽編輯。')
        d.manage_button.invoke();self.root.update()
        page=self.app.production.package_page
        self.assertTrue(page.winfo_ismapped())
        page.back_button.invoke();self.root.update()
        self.assertEqual(d.outgoing.get('1.0','end-1c'),'保留試聽編輯。')
        self.assertTrue(d.winfo_ismapped())
        self.assertEqual(str(d.settings_panel.grid_info()['column']),'0')
        self.assertEqual(str(d.preview_panel.grid_info()['column']),'1')


if __name__=='__main__':unittest.main()
