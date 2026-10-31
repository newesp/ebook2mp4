"""Approved join controls through the native main-window surface."""
import unittest
import time
from unittest.mock import patch
import threading
from pathlib import Path

from ebook2mp4.workflow import ProjectWorkflow
import test_total_audio_desktop as fixture
import test_assembly_joins as joins_fixture


class AssemblyJoinsDesktop(unittest.TestCase):
    setUp = fixture.TotalAudioDesktop.setUp
    prepare = fixture.TotalAudioDesktop.prepare
    refresh_voices = fixture.TotalAudioDesktop.refresh_voices
    audio = fixture.TotalAudioDesktop.audio
    shutdown = fixture.TotalAudioDesktop.shutdown
    wait_page = fixture.TotalAudioDesktop.wait_page
    pdf_batches = joins_fixture.AssemblyJoinJourney.pdf_batches
    narrate = joins_fixture.AssemblyJoinJourney.narrate

    def wait_join(self, join):
        deadline = time.monotonic()+20
        while join.info_job is not None and time.monotonic()<deadline:
            self.root.update()
            time.sleep(.02)
        self.assertIsNone(join.info_job)
        self.root.update()

    def test_join_page_save_preview_edit_return_and_sizes(self):
        self.app.total_audio()
        page = self.app.production.current
        self.wait_page(page)
        page.select_button.invoke()
        page.join_button.invoke()
        join = page.join_page
        self.wait_join(join)
        self.assertIs(join.winfo_toplevel(), self.root)
        self.root.state('normal')
        for size in ('1040x640', '1360x800'):
            self.root.geometry(size)
            self.root.update()
            for widget in (join.play_button, join.back_button, join.save_button, join.left_edit,
                           join.right_edit, join.pause_control, join.pair_control):
                self.assertTrue(widget.winfo_viewable())
                self.assertGreaterEqual(widget.winfo_rootx(), self.root.winfo_rootx())
                self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(), self.root.winfo_rootx()+self.root.winfo_width())
                self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(), self.root.winfo_rooty()+self.root.winfo_height())
        page.pause.set('5')
        join.save_button.invoke()
        self.wait_page(page)
        self.assertEqual(ProjectWorkflow.open(self.flow.root).assembly_settings()['pause_ms'], 5000)
        page.join_button.invoke()
        self.wait_join(join)
        with patch('ebook2mp4.voice_media.PreviewPlayer._send', return_value='playing'):
            join.play_button.invoke()
            deadline = time.monotonic()+20
            while join.job is not None and not join.playing and time.monotonic()<deadline:
                self.root.update()
                time.sleep(.02)
            self.assertTrue(join.playing, join.status.cget('text'))
            self.assertIn('第 1 批', join.left_text.get('1.0', 'end'))
            join.right_edit.invoke()
            self.root.update()
            self.assertEqual(self.app.step, 2)
            self.assertEqual(self.app.batch_id, self.ids[1])
            self.assertIsNone(join.player.alias)
        self.app.total_audio()
        self.wait_page(page)
        self.wait_join(join)
        self.assertTrue(join.winfo_viewable())
        self.assertEqual(page.selected, self.ids)
        self.assertEqual(page.pause.get(), '5')

    def test_each_pdf_warning_requires_explicit_confirmation(self):
        ids = self.pdf_batches()
        self.narrate(ids)
        self.app.total_audio()
        page = self.app.production.current
        self.wait_page(page)
        for identity in ids:
            page.table.selection_set(identity)
            page.toggle_selected()
        self.assertTrue(page.start_button.instate(['disabled']))
        page.join_button.invoke()
        join = page.join_page
        self.wait_join(join)
        self.assertIn('第 8 頁', join.warning_title.cget('text'))
        join.ack_control.invoke()
        self.assertTrue(page.start_button.instate(['disabled']))
        join.next.invoke()
        self.assertIn('第 16～17 頁', join.warning_title.cget('text'))
        join.ack_control.invoke()
        join.save_button.invoke()
        self.wait_page(page)
        self.assertFalse(page.start_button.instate(['disabled']))
        reopened = ProjectWorkflow.open(self.flow.root)
        self.assertTrue(all(j['accepted'] for j in reopened.inspect_assembly_joins()))

    def test_leave_during_preparation_never_starts_hidden_audio(self):
        self.app.total_audio()
        page = self.app.production.current
        self.wait_page(page)
        page.select_button.invoke()
        page.join_button.invoke()
        join = page.join_page
        self.wait_join(join)
        source = self.flow.narration_path(self.ids[0])
        opened, proceed = threading.Event(), threading.Event()
        original = Path.open
        class SlowFile:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self
            def __exit__(self, *args): self.stream.close()
            def read(self, *args):
                opened.set()
                proceed.wait(5)
                return self.stream.read(*args)
        def slow_open(path, *args, **kwargs):
            stream = original(path, *args, **kwargs)
            return SlowFile(stream) if path == source else stream
        with patch.object(Path, 'open', slow_open), patch('ebook2mp4.voice_media.PreviewPlayer.play') as play:
            try:
                join.play_button.invoke()
                self.assertTrue(opened.wait(5))
                self.app.voice_settings()
                proceed.set()
                deadline = time.monotonic()+15
                while join.has_work() and time.monotonic()<deadline:
                    self.root.update()
                    time.sleep(.02)
                self.assertFalse(join.has_work())
                play.assert_not_called()
            finally:
                proceed.set()
        self.assertEqual(list(self.flow.root.glob('.join-preview-*')), [])
