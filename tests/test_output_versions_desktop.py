"""T20 native single-window navigation, saved drafts, route actions and sizing."""
import time
import tkinter.ttk as ttk
import unittest
from unittest.mock import patch
from pathlib import Path
from ebook2mp4.desktop import make_app
from ebook2mp4.workspace_layout import TOOLBAR_GAP
import test_output_versions as core
import test_total_audio_desktop as gui


class OutputVersionsDesktop(core.OutputVersionsJourney):
    # Only the native journey belongs in this class; core cases are run separately.
    test_route_matrix_retains_both_movies_exports_and_reopens = None
    test_source_text_voice_new_audio_and_launch_snapshot = None
    test_empty_and_legacy_project_migration = None
    test_video_launch_snapshot_cancel_and_corrupt_output_are_route_local = None
    shutdown = gui.TotalAudioDesktop.shutdown
    wait_page = gui.TotalAudioDesktop.wait_page

    def test_versions_details_return_exports_playback_and_layout(self):
        ids = self.ready()
        self.root, self.app = make_app()
        self.addCleanup(self.shutdown)
        errors = []
        self.root.report_callback_exception = lambda *args: errors.append(str(args))
        self.app.flow, self.app.batch_id = self.flow, self.batch
        self.app.refresh()
        self.app.total_audio()
        origin = self.app.production.current
        self.wait_page(origin)
        origin.selected = ids[:2][::-1]
        origin.pause.set('1.25')
        origin.versions_button.invoke()
        page = self.app.production.current
        self.wait_page(page)
        self.assertIs(page.winfo_toplevel(), self.root)
        self.assertEqual(len(page.table.get_children()), 3)
        self.assertTrue(page.stop_button.instate(['disabled']))
        style = ttk.Style(self.root)
        style.configure('.', font=('Microsoft JhengHei', 13))
        for route in ('audio', 'total-audio', 'batch-videos'):
            page.table.selection_set(route)
            self.root.update()
            page.detail_button.invoke()
            self.assertIn('這份成品使用的來源', page.text.get('1.0', 'end'))
            self.assertIn('目前設定', page.text.get('1.0', 'end'))
            self.assertIn('最近任務：已完成 · 已保存成品', page.text.get('1.0', 'end'))
            page.technical.set(False)
            page.technical_button.invoke()
            self.assertIn('sha256', page.text.get('1.0', 'end'))
            self.root.state('normal')
            for size in ('900x640', '1280x720', '1360x820'):
                self.root.geometry(size)
                self.root.update()
                for widget in (page.text, page.back_button, page.play_button, page.export_button, page.goto_button):
                    self.assertTrue(widget.winfo_viewable())
                    self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(), self.root.winfo_rootx()+self.root.winfo_width())
                    self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(), self.root.winfo_rooty()+self.root.winfo_height())
                actions = (page.play_button, page.stop_button, page.export_button, page.goto_button)
                self.assertEqual(len({(w.winfo_width(), w.winfo_height()) for w in actions[:3]}), 1)
                for left, right in zip(actions, actions[1:]):
                    self.assertEqual(right.winfo_rootx()-left.winfo_rootx()-left.winfo_width(), TOOLBAR_GAP)
            page.back_button.invoke()
            destination = self.path/('native-'+route)
            with patch('ebook2mp4.output_versions_desktop.filedialog.asksaveasfilename', return_value=str(destination)):
                page.export_button.invoke()
                self.wait_page(page)
            self.assertTrue((destination/'total.srt').is_file())
        page.table.selection_set('batch-videos')
        self.root.update()
        page.play_button.invoke()
        self.assertTrue(page.stop_button.instate(['!disabled']))
        deadline = time.monotonic()+30
        while page.movie_player.has_work() and time.monotonic()<deadline:
            self.root.update()
            time.sleep(.02)
        self.assertIsNone(page.movie_player.folder)
        page.movie_player.leave()
        self.assertTrue(page.stop_button.instate(['disabled']))
        page.back_button.invoke()
        self.assertIs(self.app.production.current, origin)
        self.assertEqual(origin.selected, ids[:2][::-1])
        self.assertEqual(origin.pause.get(), '1.25')
        origin.versions_button.invoke()
        self.wait_page(page)
        page.table.selection_set('total-audio')
        self.root.update()
        page.goto_button.invoke()
        video = self.app.production.current
        self.wait_page(video)
        self.assertEqual(video.product['id'], self.flow.total_video(method='total-audio')['id'])
        self.assertNotEqual(video.product['id'], self.flow.total_video(method='batch-videos')['id'])
        video.versions_button.invoke()
        self.wait_page(page)
        self.flow.save_draft(ids[0], 'A 已修改。')
        page.recheck()
        self.wait_page(page)
        self.assertTrue(all('待更新' in page.table.item(route, 'values')[1] for route in page.table.get_children()))
        page.table.selection_set('batch-videos')
        self.root.update()
        page.goto_button.invoke()
        self.assertEqual(self.app.batch_id, ids[0])
        self.assertIs(self.app.production.current, self.app.narration_dialog)
        self.assertEqual(errors, [])
