"""Waiting and cancellation through the native production controls."""
import time
import unittest
from unittest.mock import patch

import test_narration_desktop as fixture
import test_tts_retry as retry_fixture


class RetryDesktop(unittest.TestCase):
    poll = fixture.NarrationDesktop.poll
    prepare = retry_fixture.RetryRecovery.prepare
    audio = retry_fixture.RetryRecovery.audio

    def setUp(self):
        fixture.NarrationDesktop.setUp(self)
        self.addCleanup(self.stop_jobs)

    def stop_jobs(self):
        deadline = time.monotonic() + 10
        while self.app.production.shutdown() != 'complete' and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.02)

    def capture(self, variable):
        import os
        if os.environ.get(variable):
            import ctypes
            from PIL import ImageGrab
            parent = ctypes.windll.user32.GetParent
            parent.argtypes, parent.restype = [ctypes.c_void_p], ctypes.c_void_p
            ImageGrab.grab(window=parent(self.root.winfo_id())).save(os.environ[variable])

    def test_wait_status_and_cancel_at_minimum_window(self):
        audio = self.prepare(2)
        self.dialog.reload_button.invoke()
        self.poll()
        self.root.state('normal')
        self.root.geometry('1040x640')
        self.root.update()

        def unavailable(body):
            return (429, '120', b'') if body['text'] == '待完成。' else (200, '0', audio)

        with patch('aiohttp.ClientSession', retry_fixture.transport(unavailable)):
            self.dialog.start_button.invoke()
            deadline = time.monotonic() + 10
            while '等待 120 秒後重試' not in self.dialog.status.cget('text') and time.monotonic() < deadline:
                self.root.update()
                time.sleep(.02)
            self.assertIn('等待 120 秒後重試', self.dialog.status.cget('text'))
            self.assertIn('區塊 2/2', self.dialog.status.cget('text'))
            self.assertEqual(str(self.dialog.start_button.cget('state')), 'disabled')
            self.assertEqual(str(self.dialog.cancel_button.cget('state')), 'normal')
            self.assertTrue(self.dialog.cancel_button.winfo_ismapped())
            for control in (self.dialog.status, self.dialog.start_button, self.dialog.cancel_button):
                self.assertGreaterEqual(control.winfo_rootx(), self.root.winfo_rootx())
                self.assertLessEqual(control.winfo_rootx() + control.winfo_width(),
                                     self.root.winfo_rootx() + self.root.winfo_width())
            # Optional evidence capture; ordinary test runs leave no images.
            self.capture('EBOOK2MP4_RETRY_SCREENSHOT')
            self.dialog.cancel_button.invoke()
            self.poll()
        self.assertFalse((self.flow.root / '.production.lock').exists())
        self.assertEqual(self.flow.narration_runs(self.batch)[-1]['progress']['status'], 'cancelled')

    def test_resume_refreshes_old_failed_row_while_next_block_waits(self):
        audio = self.prepare(2)
        self.dialog.reload_button.invoke()
        self.poll()
        with patch('aiohttp.ClientSession', retry_fixture.transport(lambda body: (401, '0', b''))):
            self.dialog.start_button.invoke()
            self.poll()
        rows = self.dialog.details.get_children()
        self.assertEqual(self.dialog.details.set(rows[0], 'status'), '失敗')

        def restored(body):
            return (429, '120', b'') if body['text'] == '待完成。' else (200, '0', audio)

        with patch('aiohttp.ClientSession', retry_fixture.transport(restored)):
            self.dialog.start_button.invoke()
            deadline = time.monotonic() + 10
            while '等待 120 秒後重試' not in self.dialog.status.cget('text') and time.monotonic() < deadline:
                self.root.update()
                time.sleep(.02)
            self.assertIn('區塊 2/2', self.dialog.status.cget('text'))
            rows = self.dialog.details.get_children()
            self.assertEqual(self.dialog.details.set(rows[0], 'status'), '已完成')
            self.assertEqual(self.dialog.details.set(rows[1], 'status'), '執行中')
            self.dialog.details.selection_set(rows[0])
            self.root.update()
            self.assertNotIn('HTTP 401', self.dialog.status.cget('text'))
            self.dialog.cancel_button.invoke()
            self.poll()

    def test_173_rows_and_countdown_follow_current_progress_without_losing_selection(self):
        chunks = [dict(order=i, status='completed' if i < 42 else 'running' if i == 42 else 'pending',
                       attempts=1) for i in range(173)]
        state = dict(phase='等待 120 秒後重試', retry_deadline=1120,
                     current=43, total=173, completed=42, failed=0, chunks=chunks)
        with patch('ebook2mp4.narration_desktop.time') as clock:
            clock.monotonic.return_value = 1000
            self.dialog.display_progress(state)
            rows = self.dialog.details.get_children()
            self.dialog.details.selection_set(rows[38])
            self.dialog.details.see(rows[38])
            self.root.update()
            clock.monotonic.return_value = 1010
            self.dialog.display_progress(state)
        self.assertEqual(len(rows), 173)
        self.assertIn('等待 110 秒後重試', self.dialog.status.cget('text'))
        self.assertIn('區塊 43/173', self.dialog.status.cget('text'))
        self.assertEqual(self.dialog.details.set(rows[38], 'status'), '已完成')
        self.assertEqual(self.dialog.details.set(rows[42], 'status'), '執行中')
        self.assertEqual(self.dialog.details.selection(), (rows[38],))

    def test_excessive_wait_stops_and_enables_resume_at_minimum_window(self):
        audio = self.prepare(2)
        self.dialog.reload_button.invoke()
        self.poll()
        self.root.state('normal')
        self.root.geometry('1040x640')
        self.root.update()

        def limited(body):
            return (429, '77813', b'') if body['text'] == '待完成。' else (200, '0', audio)

        with patch('aiohttp.ClientSession', retry_fixture.transport(limited)):
            self.dialog.start_button.invoke()
            self.poll()
        message = self.dialog.status.cget('text')
        self.assertIn('77813', message)
        self.assertIn('HTTP 429', message)
        self.assertIn('停止自動重試', message)
        self.assertEqual(str(self.dialog.start_button.cget('state')), 'normal')
        self.assertFalse(self.dialog.cancel_button.winfo_ismapped())
        self.assertFalse((self.flow.root / '.production.lock').exists())
        rows = self.dialog.details.get_children()
        self.assertEqual(self.dialog.details.set(rows[0], 'status'), '已完成')
        self.assertEqual(self.dialog.details.set(rows[1], 'status'), '失敗')
        self.dialog.details.selection_set(rows[1])
        self.root.update()
        self.assertIn('第 2 塊', self.dialog.status.cget('text'))
        for control in (self.dialog.status, self.dialog.start_button, self.dialog.details):
            self.assertGreaterEqual(control.winfo_rootx(), self.root.winfo_rootx())
            self.assertLessEqual(control.winfo_rootx() + control.winfo_width(),
                                 self.root.winfo_rootx() + self.root.winfo_width())
            self.assertLessEqual(control.winfo_rooty() + control.winfo_height(),
                                 self.root.winfo_rooty() + self.root.winfo_height())
        self.capture('EBOOK2MP4_COOLDOWN_SCREENSHOT')
