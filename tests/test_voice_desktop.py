"""Native Tk voice journeys; external Edge service and audio device controlled."""
from pathlib import Path
import asyncio
import tempfile
import time
import unittest
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
        self.app.steps[2].invoke()
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
        self.dialog.voices.selection_set('zh-TW-TestNeural')
        self.root.update()

    def test_selected_unsaved_text_consent_save_preview_and_play(self):
        self.choose()
        self.app.editor.insert('end', '未存文字。')
        self.app.editor.tag_add('sel', '3.0', '3.end')
        self.root.update()
        self.dialog.source.set('校對稿選取文字')
        self.dialog.prepare_text()
        self.dialog.preview_button.invoke()
        self.assertIn('同意', self.dialog.status.cget('text'))
        self.assertIsNone(self.dialog.job)
        self.dialog.consent.set(True)
        self.dialog.rate.set('-10%')
        audio = fixture.VoiceJourney.audio(self)
        requests = []
        class Service:
            def __init__(self, text, voice, **options):
                requests.append((text, voice, options['rate']))
            async def stream(self):
                yield dict(type='audio', data=audio)
        with patch('edge_tts.Communicate', Service):
            self.dialog.preview_button.invoke()
            self.poll()
        self.assertEqual(requests, [('選取 Hello。', 'zh-TW-TestNeural', '-10%')])
        self.assertTrue(self.app.dirty)
        with patch('ebook2mp4.voice_media.ctypes.WinDLL') as device:
            device.return_value.mciSendStringW.return_value = 0
            self.dialog.play_button.invoke()
            commands = [call.args[0] for call in device.return_value.mciSendStringW.call_args_list]
            self.assertTrue(any(command.startswith('play ') for command in commands))
            self.dialog.stop_button.invoke()
            self.assertTrue(device.return_value.mciSendStringW.call_args.args[0].startswith('close '))
        self.dialog.close()
        self.assertIsNone(self.app.voice_dialog)
        reopened = ProjectWorkflow.open(self.app.flow.root)
        self.assertEqual(reopened.voice_settings(self.app.batch_id)['rate'], '-10%')
        self.assertEqual(reopened.voice_preview(self.app.batch_id)['text'], '選取 Hello。')

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
            job = self.dialog.job
            self.dialog.close()
            deadline = time.monotonic() + 5
            while self.app.voice_dialog is not None and time.monotonic() < deadline:
                self.root.update()
                time.sleep(.02)
            self.assertIsNone(self.app.voice_dialog)
            self.assertTrue(job.wait(0))
            self.assertEqual(job.state['status'], 'cancelled')

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
