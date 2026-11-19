"""Native T21 format controls, material return, result actions and small window."""
import unittest
from unittest.mock import patch
import tkinter.font as tkfont

from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow
import test_outputs as core
import test_total_audio_desktop as gui


class OutputsDesktop(unittest.TestCase):
    setUp = core.OutputsJourney.setUp
    prepare = core.OutputsJourney.prepare
    refresh_voices = core.OutputsJourney.refresh_voices
    audio = core.OutputsJourney.audio
    picture = core.OutputsJourney.picture
    plan = core.OutputsJourney.plan
    visual = core.OutputsJourney.visual
    shutdown = gui.TotalAudioDesktop.shutdown
    wait_page = gui.TotalAudioDesktop.wait_page

    def test_partial_retry_material_return_and_window_sizes(self):
        ids = self.prepare(2)
        self.plan(ids)
        self.root, self.app = make_app()
        self.addCleanup(self.shutdown)
        errors = []
        self.root.report_callback_exception = lambda *args: errors.append(str(args))
        self.app.flow, self.app.batch_id = self.flow, self.batch
        self.app.refresh()
        self.app.total_audio()
        page = self.app.production.current
        self.wait_page(page)
        controls = page.output_controls
        self.assertEqual(controls.plan['rows']['mp4']['status'], 'missing')
        with patch('edge_tts.Communicate', side_effect=AssertionError('No TTS')):
            page.start_button.invoke()
            self.wait_page(page)
        self.assertIn('部分完成', controls.summary.cget('text'))
        old = self.flow.total_audio()['id']
        self.root.state('normal')
        for size in ('1040x640', '1360x800'):
            self.root.geometry(size)
            self.root.update()
            for widget in (page.table, page.start_button, page.back_button, controls.summary,
                           *controls.checks, controls.labels['mp4'][3]):
                self.assertTrue(widget.winfo_viewable(), str(widget))
                self.assertGreaterEqual(widget.winfo_rootx(), self.root.winfo_rootx())
                self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(), self.root.winfo_rootx()+self.root.winfo_width())
                self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(), self.root.winfo_rooty()+self.root.winfo_height())
            self.assertGreaterEqual(page.table.winfo_height(), 60)
            self.assertLess(tkfont.Font(font='TkDefaultFont').measure(page.start_button.cget('text')), page.start_button.winfo_width())
        controls.labels['mp4'][3].invoke()
        video = self.app.production.current
        self.wait_page(video)
        self.assertIsNot(video, page)
        with patch('ebook2mp4.total_video_desktop.filedialog.askopenfilename', return_value=str(self.picture())):
            video.choose_button.invoke()
            self.wait_page(video)
        video.save_return_button.invoke()
        video.back_button.invoke()
        self.wait_page(page)
        self.assertEqual(page.selected, ids)
        page.start_button.invoke()
        self.wait_page(page)
        self.assertEqual(self.flow.total_audio()['id'], old)
        self.assertIn('全部要求已完成', controls.summary.cget('text'))
        self.assertIn('各要求格式與同版 SRT 均已保存', page.status.cget('text'))
        self.assertEqual(page.start_button.cget('text'), '輸出均已完成')
        controls.labels['mp4'][3].invoke()
        versions = self.app.production.current
        self.wait_page(versions)
        self.assertEqual(versions.table.selection(), ('total-audio',))
        versions.back_button.invoke()
        self.wait_page(page)
        controls.values['mp4'].set(False)
        controls.changed()
        self.wait_page(page)
        self.assertEqual(ProjectWorkflow.open(self.flow.root).output_formats(), ['mp3'])
        self.assertFalse(controls.labels['mp4'][0].winfo_viewable())
        self.assertEqual(errors, [])
