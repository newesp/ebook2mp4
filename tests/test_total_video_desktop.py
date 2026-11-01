"""Approved two-step journey in the native main window."""
import time
import tkinter as tk
import unittest
from unittest.mock import patch
from PIL import Image
import test_total_audio_desktop as fixture


class TotalVideoDesktop(unittest.TestCase):
    setUp = fixture.TotalAudioDesktop.setUp
    prepare = fixture.TotalAudioDesktop.prepare
    refresh_voices = fixture.TotalAudioDesktop.refresh_voices
    audio = fixture.TotalAudioDesktop.audio
    shutdown = fixture.TotalAudioDesktop.shutdown
    wait_page = fixture.TotalAudioDesktop.wait_page

    def test_two_steps_encode_and_return_keep_picture_and_resolution(self):
        self.app.total_audio()
        assembly = self.app.production.current
        self.wait_page(assembly)
        assembly.select_button.invoke()
        assembly.start_button.invoke()
        self.wait_page(assembly)
        self.assertTrue(assembly.video_button.winfo_viewable())
        self.assertFalse(assembly.start_button.winfo_viewable())
        assembly.video_button.invoke()
        page = self.app.production.current
        self.wait_page(page)
        self.assertIs(page.winfo_toplevel(), self.root)
        image = self.path/'封面.png'
        Image.new('RGBA', (80, 120), (255, 0, 0, 128)).save(image)
        with patch('tkinter.filedialog.askopenfilename', return_value=str(image)):
            page.choose_button.invoke()
            self.wait_page(page)
        page.resolution.set('720p')
        page.back_button.invoke()
        self.wait_page(assembly)
        assembly.video_button.invoke()
        self.wait_page(page)
        self.assertEqual(page.resolution.get(), '720p')
        self.assertIn('封面.png', page.image_info.cget('text'))
        self.root.state('normal')
        for size in ('1040x640', '1360x800'):
            self.root.geometry(size)
            self.root.update()
            for widget in (page.choose_button, page.start_button, page.back_button, page.outputs_button, page.resolution_control):
                self.assertTrue(widget.winfo_viewable())
                self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(), self.root.winfo_rootx()+self.root.winfo_width())
                self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(), self.root.winfo_rooty()+self.root.winfo_height())
        with patch('edge_tts.Communicate', side_effect=AssertionError('no TTS')):
            page.start_button.invoke()
            self.wait_page(page)
        self.assertIsNotNone(self.flow.total_video())
        self.assertIn('目前總影片', page.result_info.cget('text'))
        page.resolution.set('1080p')
        page.output_menu()
        page.menu.invoke('儲存視覺設定')
        self.assertTrue(self.flow.total_video()['stale'])
        self.assertIn('待更新', page.result_info.cget('text'))
        old_id = self.flow.total_video()['id']
        page.start_button.invoke()
        self.root.update()
        self.assertTrue(page.choose_button.instate(['disabled']))
        page.cancel_button.invoke()
        self.wait_page(page)
        self.assertEqual(self.flow.total_video()['id'], old_id)
        with patch('ebook2mp4.voice_media.PreviewPlayer._send', return_value='playing'):
            page.output_menu()
            page.menu.invoke('播放上一版影片')
            self.wait_page(page)
            self.assertIsNotNone(page.player.alias)
            self.assertTrue(list(self.flow.root.glob('.video-preview-*')))
            with patch('shutil.rmtree', side_effect=PermissionError('locked playback files')):
                page.stop()
                page.output_menu()
                page.menu.invoke('播放上一版影片')
                self.assertEqual(len(list(self.flow.root.glob('.video-preview-*'))), 1)
            page.stop()
            page.back_button.invoke()
            self.assertIsNone(page.player.alias)
            self.assertEqual(list(self.flow.root.glob('.video-preview-*')), [])


if __name__ == '__main__':
    unittest.main()
