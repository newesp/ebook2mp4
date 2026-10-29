"""Native notification lifecycle, placement and manuscript-focus contracts."""
import time
import tkinter as tk
import unittest
from unittest.mock import patch

from ebook2mp4.desktop import make_app
from ebook2mp4.ui_controls import notify


class Notifications(unittest.TestCase):
    def setUp(self):
        self.root, self.app = make_app()
        self.errors = []
        self.root.report_callback_exception = lambda *error: self.errors.append(error)
        self.root.geometry('1040x640+20+20')
        # Manuscript focus contracts apply to the proofreading surface.
        self.app.show_step(2)
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.assertEqual(self.errors, [])

    def pump(self, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.root.update()
            time.sleep(.01)

    def test_top_center_tracks_owner_without_stealing_editor_focus(self):
        self.app.editor.focus_force()
        self.root.update()
        layer = self.app.notify('校對稿已儲存。')
        self.root.update()
        self.assertIs(self.root.focus_displayof(), self.app.editor)
        for geometry in ('1040x640+60+60', '1200x700+100+90'):
            self.root.geometry(geometry)
            self.root.update()
            window = layer.window
            self.assertIsNotNone(window)
            self.assertLessEqual(abs(window.winfo_rootx() + window.winfo_width()/2 -
                                     self.root.winfo_rootx() - self.root.winfo_width()/2), 1)
            self.assertEqual(window.winfo_rooty() - self.root.winfo_rooty(), 16)
        layer.close_button.invoke()
        self.assertIsNone(layer.window)
        self.assertIsNone(layer.timer)
        self.assertIsNone(layer.position_timer)

    def test_new_message_replaces_old_timer_and_history_keeps_both(self):
        first = self.app.notify('第一段已採用。')
        old_window, old_timer = first.window, first.timer
        second = self.app.notify('第二段已採用。')
        self.assertIs(first, second)
        self.assertFalse(old_window.winfo_exists())
        self.assertNotIn(old_timer, self.root.tk.call('after', 'info'))
        self.assertIn('第二段', second.message.cget('text'))
        self.assertEqual(self.app.status.history[-2:], ['第一段已採用。', '第二段已採用。'])

    def test_auto_dismiss_eases_out(self):
        layer = notify(self.root, '自動關閉', duration=20)
        self.pump(.4)
        self.assertIsNone(layer.window)
        self.assertIsNone(layer.timer)
        layer.show('淡出驗證', duration=3000)
        layer.cancel_timer()
        layer.fade_started = time.monotonic() - .125
        layer.fade()
        self.assertLess(float(layer.window.attributes('-alpha')), .5)
        layer.dismiss()

    def test_hover_and_focus_pause_then_resume_countdown(self):
        layer = notify(self.root, '可停留閱讀', duration=20)
        layer.pause()
        self.pump(.1)
        self.assertIsNotNone(layer.window)
        self.assertIsNone(layer.timer)
        with patch.object(layer.window, 'winfo_containing', return_value=None), patch.object(
                layer.window, 'focus_displayof', return_value=None):
            layer.resume()
        self.pump(.4)
        self.assertIsNone(layer.window)

    def test_sticky_error_close_does_not_clear_existing_blocker(self):
        self.app.status.configure(text='來源仍有異常。')
        layer = self.app.notify('儲存失敗，請重試。', kind='error')
        self.assertIsNone(layer.timer)
        layer.close_button.invoke()
        self.assertEqual(self.app.status.full_text, '來源仍有異常。')
        self.assertIn('儲存失敗', self.app.status.history[-1])

    def test_small_child_owner_long_message_and_destruction_release_timers(self):
        child = tk.Toplevel(self.root)
        child.title('設定驗證')
        child.geometry('320x240+100+100')
        self.root.update()
        text = '長訊息測試。' * 100
        layer = self.app.notify(text, owner=child)
        self.root.update()
        self.assertLessEqual(layer.window.winfo_width(), child.winfo_width()-32)
        self.assertLess(layer.window.winfo_height(), child.winfo_height())
        self.assertIn(text, self.app.status.history[-1])
        token = layer.timer
        child.destroy()
        self.root.update()
        self.assertIsNone(layer.window)
        self.assertIsNone(layer.timer)
        self.assertNotIn(token, self.root.tk.call('after', 'info'))

    def test_unmapped_owner_dismisses_and_hidden_owner_only_records_history(self):
        layer = self.app.notify('完成。')
        self.root.withdraw()
        self.root.update()
        self.assertIsNone(layer.window)
        self.app.notify('背景結果。')
        self.assertIsNone(layer.window)
        self.assertIn('背景結果。', self.app.status.history)
        self.root.deiconify()

    def test_switching_owner_dismisses_toast_and_never_uses_global_topmost(self):
        self.app.editor.focus_force()
        self.root.update()
        layer = self.app.notify('已儲存。')
        self.root.update()
        self.assertFalse(layer.window.attributes('-topmost'))
        other = tk.Toplevel(self.root)
        other.focus_force()
        self.root.update()
        self.assertIsNone(layer.window)
        self.assertIsNone(layer.focus_timer)
        self.assertIsNone(layer.timer)
        other.destroy()

