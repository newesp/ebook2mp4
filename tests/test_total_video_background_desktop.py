"""T17 approved native page: real media, saved modes, cancellation and live frames."""
import time
import unittest
from unittest.mock import patch

import test_total_video_desktop as fixture
import test_total_audio_desktop as audio_fixture
from test_total_video_background import background
from ebook2mp4.workflow import ProjectWorkflow


class BackgroundDesktop(unittest.TestCase):
    setUp = fixture.TotalVideoDesktop.setUp
    prepare = fixture.TotalVideoDesktop.prepare
    refresh_voices = fixture.TotalVideoDesktop.refresh_voices
    audio = fixture.TotalVideoDesktop.audio
    shutdown = fixture.TotalVideoDesktop.shutdown
    wait_page = fixture.TotalVideoDesktop.wait_page

    def open_page(self):
        self.errors = []
        self.root.report_callback_exception = lambda *error: self.errors.append(error)
        self.flow.save_assembly_settings(self.ids)
        audio_fixture.TotalAudioDesktop.merge(self)
        self.app.total_video()
        page = self.app.production.current
        self.wait_page(page)
        page.source_kind.set('背景影片（MP4）')
        page.kind_changed()
        self.wait_page(page)
        source = background(self.path/'短背景.mp4', portrait=True)
        with patch('tkinter.filedialog.askopenfilename', return_value=str(source)):
            page.choose_button.invoke()
            self.wait_page(page)
        return page

    def pump(self, seconds):
        deadline = time.monotonic()+seconds
        while time.monotonic()<deadline:
            self.root.update()
            time.sleep(.01)

    def test_background_mode_preview_save_return_and_render_are_connected(self):
        page = self.open_page()
        self.assertEqual(page.kind, 'video')
        self.assertTrue(page.mode_control.winfo_viewable())
        page.mode.set('最後一格定格')
        page.resolution.set('720p')
        page.seek.set(.7)
        page.scrub()
        self.wait_page(page)
        self.assertIn('0.3 秒', page.seek_info.cget('text'))
        page.preview_button.invoke()
        self.pump(.5)
        self.assertIsNotNone(page.playback_image)
        page.preview_button.invoke()
        self.assertIsNone(page.frame_job)
        self.assertIsNone(page.player.alias)
        page.back_button.invoke()
        self.app.total_video()
        self.wait_page(page)
        self.assertEqual(page.mode.get(), '最後一格定格')
        self.assertEqual(page.resolution.get(), '720p')
        with patch('edge_tts.Communicate', side_effect=AssertionError('no TTS')):
            page.start_button.invoke()
            self.wait_page(page)
        self.assertIsNotNone(self.flow.total_video())
        self.assertEqual(ProjectWorkflow.open(self.flow.root).total_video_settings()['background_mode'], 'hold')
        self.assertFalse(self.flow.total_audio()['stale'])
        page.file_action('play')
        self.wait_page(page)
        self.pump(.3)
        self.assertIsNotNone(page.player.alias)
        self.assertIsNotNone(page.playback_image)
        page.back_button.invoke()
        self.pump(.2)
        self.assertIsNone(page.frame_job)
        self.assertIsNone(page.player.alias)
        self.assertEqual(list(self.flow.root.glob('.video-preview-*')), [])
        self.assertEqual(self.errors, [])

    def test_required_controls_fit_sizes_and_long_background_hides_short_mode(self):
        page = self.open_page()
        self.root.state('normal')
        for size in ('1040x640', '1360x800'):
            self.root.geometry(size)
            self.root.update()
            for widget in (page.kind_control, page.mode_control, page.choose_button, page.start_button,
                           page.back_button, page.outputs_button, page.resolution_control, page.seek_control):
                self.assertTrue(widget.winfo_viewable(), (size, widget))
                self.assertGreaterEqual(widget.winfo_rootx(), self.root.winfo_rootx())
                self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(), self.root.winfo_rootx()+self.root.winfo_width())
                self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(), self.root.winfo_rooty()+self.root.winfo_height())
            self.assertGreater(page.canvas.winfo_height(), 60)
        source = background(self.path/'長背景.mp4', 1.8)
        with patch('tkinter.filedialog.askopenfilename', return_value=str(source)):
            page.choose_button.invoke()
            self.wait_page(page)
        self.assertFalse(page.mode_control.winfo_viewable())
        self.assertIn('裁切', page.material_rule.cget('text'))
        page.source_kind.set('圖片（JPEG／PNG）')
        page.kind_changed()
        self.wait_page(page)
        self.assertFalse(page.preview_controls.winfo_viewable())
        self.assertFalse(page.mode_control.winfo_viewable())
        self.assertEqual(self.errors, [])


if __name__ == '__main__':
    unittest.main()
