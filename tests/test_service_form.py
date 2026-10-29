import tkinter as tk
import unittest
from unittest.mock import patch, Mock
from ebook2mp4.service_desktop import ServiceDialog

class ServiceForm(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk(); self.addCleanup(self.root.destroy)
        with patch('ebook2mp4.service_desktop.profiles',return_value={}):
            self.dialog=ServiceDialog(self.root)
        self.root.update()
    def test_switch_and_mask_reused_key(self):
        d=self.dialog
        d.provider_control.set('Fish Audio');d.provider_control.event_generate('<<ComboboxSelected>>');self.root.update()
        self.assertEqual(d.name.get(),'Fish Audio')
        self.assertFalse(d.reuse_check.winfo_ismapped())
        d.provider_control.set('Google Gemini TTS');d.provider_control.event_generate('<<ComboboxSelected>>');self.root.update()
        self.assertTrue(d.reuse_check.winfo_ismapped())
        d.key.set('manual-key')
        with patch('ebook2mp4.gemini.load_settings',return_value={'key':'synthetic-secret'}):
            d.reuse_check.invoke()
        self.assertEqual(d.key.get(),'synthetic-secret')
        self.assertEqual(str(d.key_entry.cget('show')),'•')
        self.assertEqual(str(d.key_entry.cget('state')),'readonly')
        d.reuse_check.invoke()
        self.assertEqual(d.key.get(),'manual-key')
        self.assertEqual(str(d.key_entry.cget('state')),'normal')
    def test_reuse_saves_reference_without_copying_secret(self):
        d=self.dialog
        with patch('ebook2mp4.gemini.load_settings',return_value={'key':'synthetic-secret'}):
            d.reuse_check.invoke()
        d.owner=Mock()
        d.owner.service_labels={'profile':'Google'}
        with patch('ebook2mp4.service_desktop.save_profile',return_value='profile') as save:
            d.save()
        self.assertEqual(save.call_args.args[2:4],('', True))

    def test_missing_reuse_key_is_explained(self):
        with patch('ebook2mp4.gemini.load_settings',return_value={'key':''}):
            self.dialog.reuse_check.invoke()
        self.assertFalse(self.dialog.reuse.get())
        self.assertIn('尚未設定',self.dialog.status.cget('text'))

if __name__=='__main__': unittest.main()
