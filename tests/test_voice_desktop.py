"""Native Tk voice journeys; external Edge service and audio device controlled."""
from pathlib import Path
import asyncio
import tempfile
import time
import unittest
import tkinter as tk
from unittest.mock import AsyncMock, patch

from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow
import test_voice as fixture


class VoiceDesktop(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[1] / '.scratch/test-runs'
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        env = patch.dict('os.environ', EBOOK2MP4_VOICE_HOME=str(self.path / 'cache'))
        env.start()
        self.addCleanup(env.stop)
        self.root, self.app = make_app()
        self.addCleanup(self.root.destroy)
        self.app.flow = ProjectWorkflow.create(self.path / 'book', '試聽連接')
        source = self.path / 'source.txt'
        source.write_bytes('前文。\n\n選取 Hello。\n\n後文。'.encode('utf-8'))
        self.app.batch_id = self.app.flow.import_txt(self.app.flow.inspect_txt(source))
        self.app.refresh()
        self.root.update()
        self.app.steps[3].invoke()
        self.dialog = self.app.voice_dialog
        self.addCleanup(lambda: self.dialog.close() if self.dialog.winfo_exists() else None)
        self.root.update()

    def poll(self):
        deadline = time.monotonic() + 10
        while self.dialog.job is not None and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.02)
        self.root.update()
        self.assertIsNone(self.dialog.job, self.dialog.status.cget('text'))

    def choose(self):
        with patch('edge_tts.list_voices', new=AsyncMock(return_value=fixture.VOICES)):
            self.dialog.refresh_button.invoke()
            self.poll()
        self.dialog.voice_control.set('zh-TW-TestNeural')
        self.dialog.voice_control.event_generate('<<ComboboxSelected>>')
        self.root.update()

    def test_service_controls_and_editable_models_follow_selected_provider(self):
        from ebook2mp4.tts_services import save_profile
        gemini = save_profile('Google Gemini TTS', 'gemini-tts', 'synthetic-key')
        fish = save_profile('Fish Audio', 'fish-audio', 'synthetic-key')
        d = self.dialog
        d.reload_services()
        for identity, voice, model in ((gemini, 'Kore', 'future-gemini-tts'),
                                       (fish, 'reference-test', 's2.1-pro-free')):
            d.service_control.set(d.service_labels[identity])
            d.service_control.event_generate('<<ComboboxSelected>>')
            self.root.update()
            self.assertFalse(d.refresh_button.winfo_ismapped())
            self.assertFalse(d.filter.winfo_ismapped())
            self.assertEqual(bool(d.voice_entry.winfo_ismapped()), identity == fish)
            self.assertEqual(bool(d.voice_control.winfo_ismapped()), identity == gemini)
            if identity == gemini:
                self.assertIn('Kore', d.voice_control.cget('values'))
            with patch.object(self.app.flow, 'start_voice_refresh') as refresh:
                d.refresh_voices()
                refresh.assert_not_called()
            self.assertEqual(str(d.model_control.cget('state')), 'normal')
            self.assertGreater(len(d.model_control.cget('values')), 0)
            d.model_control.delete(0, 'end')
            d.model_control.insert(0, model)
            d.voice.set(voice)
            d.save_button.invoke()
            value = ProjectWorkflow.open(self.app.flow.root).voice_settings(self.app.batch_id)
            self.assertEqual(value['model'], model)
            self.assertEqual(value['voice'], voice)
            d.load_settings()
            self.assertEqual(d.model.get(), model)
        d.service_control.set('Edge-TTS')
        d.service_control.event_generate('<<ComboboxSelected>>')
        self.root.update()
        self.assertTrue(d.refresh_button.winfo_ismapped())
        self.assertTrue(d.filter.winfo_ismapped())

    def test_editable_text_uses_current_settings_and_automatically_plays(self):
        self.assertTrue(self.dialog.consent.get())
        self.assertIs(self.dialog.winfo_toplevel(), self.root)
        self.assertEqual(str(self.dialog.outgoing.cget('state')), 'normal')
        self.choose()
        original = self.app.flow.voice_settings(self.app.batch_id)
        draft = self.app.current_text
        self.dialog.outgoing.delete('1.0', 'end')
        self.dialog.outgoing.insert('1.0', '自訂 Hello。')
        self.dialog.rate.set('-10%')
        audio = fixture.VoiceJourney.audio(self)
        requests = []
        class Service:
            def __init__(self, text, voice, **options):
                requests.append((text, voice, options['rate']))
            async def stream(self): yield dict(type='audio', data=audio)
        with patch('edge_tts.Communicate', Service), patch.object(self.dialog.player, 'play') as play, \
                patch.object(self.dialog.player, 'playing', return_value=False):
            self.dialog.preview_button.invoke()
            self.poll()
            play.assert_called_once()
        self.assertEqual(requests, [('自訂 Hello。', 'zh-TW-TestNeural', '-10%')])
        self.assertEqual(self.app.flow.voice_settings(self.app.batch_id), original)
        self.assertEqual(self.app.current_text, draft)
        self.assertEqual(self.app.flow.voice_preview(self.app.batch_id)['text'], '自訂 Hello。')
        self.dialog.save_button.invoke()
        self.assertEqual(ProjectWorkflow.open(self.app.flow.root).voice_settings(self.app.batch_id)['rate'], '-10%')

    def test_compact_page_keeps_controls_visible_and_only_text_scrolls(self):
        from test_ui_layout import descendants
        d = self.dialog
        self.root.state('normal')
        for size in ('1040x640', '1360x800'):
            self.root.geometry(size)
            self.root.update()
            self.assertFalse(any(isinstance(w, tk.Canvas) for w in descendants(d)))
            self.assertLessEqual(d.winfo_rootx()+d.winfo_width(), self.root.winfo_rootx()+self.root.winfo_width())
            self.assertLessEqual(d.winfo_rooty()+d.winfo_height(), self.root.winfo_rooty()+self.root.winfo_height())
            controls = (d.service_control, d.model_control, d.voice_control, d.filter, d.refresh_button,
                        d.rhythm_control, d.sentence_control, d.paragraph_control,
                        d.save_button, d.preview_button, d.play_button,
                        d.produce_button, d.scope_control, d.consent_control)
            for control in controls:
                self.assertTrue(control.winfo_ismapped(), str(control))
                x, y = control.winfo_rootx()-d.winfo_rootx(), control.winfo_rooty()-d.winfo_rooty()
                self.assertGreaterEqual(x, 0)
                self.assertGreaterEqual(y, 0)
                self.assertLessEqual(x+control.winfo_width(), d.winfo_width())
                self.assertLessEqual(y+control.winfo_height(), d.winfo_height())
            self.assertEqual(d.save_button.winfo_rooty(), d.produce_button.winfo_rooty())
            self.assertEqual(d.scope_control.winfo_rooty()+d.scope_control.winfo_height()//2,
                             d.produce_button.winfo_rooty()+d.produce_button.winfo_height()//2)
            fixed_y = d.produce_button.winfo_rooty()
            d.outgoing.delete('1.0', 'end')
            d.outgoing.insert('1.0', '測試長文。\n'*200)
            d.outgoing.yview_moveto(1)
            self.root.update()
            self.assertGreater(d.outgoing.yview()[0], 0)
            self.assertEqual(d.produce_button.winfo_rooty(), fixed_y)

    def test_close_cancels_background_request_and_releases_timer(self):
        self.choose()
        self.dialog.consent.set(True)
        class Service:
            def __init__(self, *args, **kwargs): pass
            async def stream(self):
                await asyncio.sleep(60)
                yield dict(type='audio', data=b'late')
        with patch('edge_tts.Communicate', Service):
            self.dialog.preview_button.invoke()
            self.root.state('normal')
            self.root.geometry('1040x640')
            self.root.update()
            self.assertTrue(self.dialog.cancel_button.winfo_ismapped())
            self.assertTrue(self.dialog.progress.winfo_ismapped())
            for control in (self.dialog.preview_button, self.dialog.cancel_button, self.dialog.stop_button):
                self.assertLessEqual(control.winfo_rootx()+control.winfo_width(),
                                     self.dialog.winfo_rootx()+self.dialog.winfo_width())
            job = self.dialog.job
            self.dialog.close()
            deadline = time.monotonic() + 5
            while self.app.voice_dialog is not None and time.monotonic() < deadline:
                self.root.update()
                time.sleep(.02)
            self.assertIsNone(self.app.voice_dialog)
            self.assertTrue(job.wait(0))
            self.assertEqual(job.state['status'], 'cancelled')

    def test_normal_dialog_is_centered_and_popover_keeps_anchor(self):
        dialog = tk.Toplevel(self.root)
        dialog.geometry('400x200+1+1')
        self.addCleanup(dialog.destroy)
        self.root.update()
        x, y = map(int, dialog.geometry().split('+')[1:])
        self.assertAlmostEqual(x, (dialog.winfo_screenwidth()-400)//2, delta=2)
        self.assertAlmostEqual(y, (dialog.winfo_screenheight()-200)//2, delta=2)
        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.geometry('100x60+30+40')
        self.addCleanup(popup.destroy)
        self.root.update()
        self.assertEqual(popup.geometry(), '100x60+30+40')

    def test_switching_batch_does_not_write_settings_through_old_dialog(self):
        self.choose()
        previous = self.app.batch_id
        second = self.path / 'second.txt'
        second.write_bytes(b'Second batch.')
        self.app.batch_id = self.app.flow.import_txt(self.app.flow.inspect_txt(second))
        self.app.refresh()
        self.root.update()
        self.dialog.rate.set('+20%')
        self.dialog.save_button.invoke()
        self.assertIn('已切換', self.dialog.status.cget('text'))
        self.assertEqual(self.app.flow.voice_settings(previous)['voice'], '')
        self.assertEqual(self.app.flow.voice_settings(self.app.batch_id)['voice'], '')
        self.dialog.consent.set(True)
        self.dialog.preview_button.invoke()
        self.assertIsNone(self.dialog.job)


if __name__ == '__main__':
    unittest.main()
