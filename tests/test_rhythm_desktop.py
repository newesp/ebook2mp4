"""Rhythm settings through native Tk controls and project reopen."""
import unittest
import test_voice_desktop as fixture
from ebook2mp4.workflow import ProjectWorkflow


class RhythmDesktop(unittest.TestCase):
    setUp = fixture.VoiceDesktop.setUp
    poll = fixture.VoiceDesktop.poll
    choose = fixture.VoiceDesktop.choose

    def test_presets_custom_validation_and_minimum_window(self):
        self.choose()
        dialog = self.dialog
        dialog.geometry('740x650')
        dialog.rhythm.set('舒緩')
        dialog.rhythm_control.event_generate('<<ComboboxSelected>>')
        self.root.update()
        self.assertEqual((dialog.sentence_pause.get(), dialog.paragraph_pause.get()), ('200', '800'))
        dialog.save_button.invoke()
        flow = ProjectWorkflow.open(self.app.flow.root)
        self.assertEqual(flow.voice_settings(self.app.batch_id)['sentence_pause_ms'], 200)
        dialog.sentence_pause.set('1501')
        dialog.save_button.invoke()
        self.assertIn('1,500', dialog.status.cget('text'))
        self.assertEqual(self.app.flow.voice_settings(self.app.batch_id)['sentence_pause_ms'], 200)
        dialog.sentence_pause.set('1000')
        dialog.paragraph_pause.set('300')
        self.assertEqual(dialog.rhythm.get(), '自訂')
        dialog.save_button.invoke()
        self.app.flow.confirm_reading(self.app.batch_id)
        self.app.narration()
        narration = self.app.narration_dialog
        self.addCleanup(lambda: narration.close() if narration.winfo_exists() else None)
        self.root.update()
        self.assertIn('1000 ms', narration.source_info.cget('text'))
        self.assertIn('300 ms', narration.source_info.cget('text'))
        for control in (dialog.rhythm_control, dialog.sentence_control, dialog.paragraph_control,
                        dialog.save_button, dialog.preview_button, dialog.cancel_button,
                        dialog.play_button, dialog.status, dialog.rules_info):
            self.assertTrue(control.winfo_ismapped())
            x = control.winfo_rootx() - dialog.winfo_rootx()
            y = control.winfo_rooty() - dialog.winfo_rooty()
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertLessEqual(x + control.winfo_width(), dialog.winfo_width())
            self.assertLessEqual(y + control.winfo_height(), dialog.winfo_height())
        narration.close()
        other = ProjectWorkflow.open(self.app.flow.root)
        other.rename_batch(self.app.batch_id, '其他視窗已更新')
        dialog.save_button.invoke()
        self.assertIn('另一個視窗', dialog.status.cget('text'))
        sentence, paragraph = dialog.sentence_pause, dialog.paragraph_pause
        dialog.close()
        self.assertEqual(sentence.trace_info(), [])
        self.assertEqual(paragraph.trace_info(), [])
