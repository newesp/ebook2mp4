"""Join journeys through ProjectWorkflow, using real media and synthetic speech."""
import unittest
from pathlib import Path
import threading
import wave
import subprocess
import os
import json
import hashlib
from unittest.mock import patch

from test_pdf import pdf_bytes

from ebook2mp4.workflow import ProjectError, ProjectWorkflow
import test_total_audio as fixture


class AssemblyJoinJourney(unittest.TestCase):
    setUp = fixture.TotalAudioJourney.setUp
    prepare = fixture.TotalAudioJourney.prepare
    refresh_voices = fixture.TotalAudioJourney.refresh_voices
    audio = fixture.TotalAudioJourney.audio
    pcm = fixture.TotalAudioJourney.pcm
    merge = fixture.TotalAudioJourney.merge

    def test_pause_bounds_and_reopen(self):
        ids = self.prepare()
        for pause in (0, 500, 5000):
            self.flow.save_assembly_settings(ids, pause)
            self.assertEqual(ProjectWorkflow.open(self.flow.root).assembly_settings()['pause_ms'], pause)
        for pause in (-1, 5001, True, 0.5):
            with self.subTest(pause=pause), self.assertRaises(ProjectError):
                self.flow.save_assembly_settings(ids, pause)
        self.assertEqual(self.flow.assembly_settings()['pause_ms'], 5000)

    def pdf_batches(self):
        pdf = self.path/'shared.pdf'
        pdf.write_bytes(pdf_bytes())
        preview = self.flow.inspect_pdf(pdf)
        ids = []
        for start, end in ((18, 20), (8, 15), (1, 8)):
            job = self.flow.start_pdf_extraction(preview, start, end)
            self.assertTrue(job.wait(15))
            ids.append(self.flow.finish_pdf_extraction(job))
        return ids[::-1]

    def narrate(self, ids):
        self.refresh_voices()
        audio = self.audio()
        class Service:
            def __init__(self, *args, **kwargs): pass
            async def stream(self): yield dict(type='audio', data=audio)
        with patch('edge_tts.Communicate', Service):
            for batch in ids:
                self.flow.save_voice_settings('zh-TW-TestNeural', batch_id=batch)
                self.flow.confirm_reading(batch)
                job = self.flow.start_narration(batch)
                self.assertTrue(job.wait(15), job.state)
                self.flow.finish_narration(job)

    def test_pdf_warning_confirmation_is_bound_to_order_and_audio_versions(self):
        a, b, c = self.pdf_batches()
        self.narrate([a, b, c])
        joins = self.flow.inspect_assembly_joins([a, b, c])
        self.assertEqual([(j['warning']['kind'], j['warning']['start'], j['warning']['end'])
                          for j in joins], [('overlap', 8, 8), ('gap', 16, 17)])
        self.assertIn('Chapter 8', joins[0]['left']['text'])
        self.flow.save_assembly_settings([a, b, c])
        with self.assertRaisesRegex(ProjectError, '接點'):
            self.flow.start_total_audio()
        accepted = [j['key'] for j in joins]
        self.flow.save_assembly_settings([a, b, c], accepted_joins=accepted)
        reopened = ProjectWorkflow.open(self.flow.root)
        self.assertTrue(all(j['accepted'] for j in reopened.inspect_assembly_joins()))
        self.merge()
        self.flow.save_assembly_settings([c, a, b], accepted_joins=accepted)
        self.assertFalse(self.flow.inspect_assembly_joins()[0]['accepted'])
        with self.assertRaisesRegex(ProjectError, '接點'):
            self.flow.start_total_audio()
        self.flow.save_draft(a, 'New confirmed manuscript.')
        self.narrate([a])
        self.flow.save_assembly_settings([a, b], accepted_joins=accepted)
        self.assertFalse(self.flow.inspect_assembly_joins()[0]['accepted'])

    def test_preview_reuses_audio_matches_total_timeline_and_releases_files(self):
        ids = self.prepare(3)
        original = [self.flow.narration_path(i).read_bytes() for i in ids]
        for pause, expected in ((0, 400), (500, 900), (5000, 5400)):
            with self.subTest(pause=pause), patch('edge_tts.Communicate', side_effect=AssertionError('no TTS')):
                job = self.flow.start_assembly_join_preview(ids, 0, pause_ms=pause)
                self.assertTrue(job.wait(15), job.state)
                try:
                    preview = self.flow.finish_assembly_join_preview(job)
                    path = Path(preview['path'])
                    pcm = self.pcm(path)
                    self.assertEqual(len(pcm)//48, expected)
                    self.assertEqual(preview['left_text'], '第 1 批。')
                    self.assertEqual(preview['right_text'], '第 2 批。')
                    if pause:
                        middle = 200+pause//2
                        self.assertEqual(set(pcm[(middle-5)*48:(middle+5)*48]), {0})
                    self.flow.save_assembly_settings(ids[:2], pause)
                    total = self.merge()
                    self.assertEqual(total['duration_ms'], expected)
                    srt = self.flow.total_audio_path('srt').read_text(encoding='utf-8')
                    self.assertIn({0:'00:00:00,200',500:'00:00:00,700',5000:'00:00:05,200'}[pause], srt)
                finally:
                    self.flow.discard_assembly_join_preview(job)
                self.assertFalse(path.exists())
        self.assertEqual([self.flow.narration_path(i).read_bytes() for i in ids], original)
        self.assertEqual(list(self.flow.root.glob('.join-preview-*')), [])

    def test_one_two_three_batches_at_all_pause_limits(self):
        ids = self.prepare(3)
        for pause, lengths in ((0, (200, 400, 600)), (500, (200, 900, 1600)),
                               (5000, (200, 5400, 10600))):
            for count, expected in enumerate(lengths, 1):
                with self.subTest(pause=pause, count=count):
                    self.flow.save_assembly_settings(ids[:count], pause)
                    self.assertEqual(self.merge()['duration_ms'], expected)
                    self.assertEqual(len(self.pcm(self.flow.total_audio_path()))//48, expected)

    def test_cancel_and_changed_manuscript_do_not_leave_preview_resources(self):
        ids = self.prepare(2)
        source = self.flow.narration_path(ids[0])
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
        with patch.object(Path, 'open', slow_open):
            job = self.flow.start_assembly_join_preview(ids, 0)
            try:
                self.assertTrue(opened.wait(5))
                job.cancel()
            finally:
                proceed.set()
                self.assertTrue(job.wait(10))
                self.flow.discard_assembly_join_preview(job)
        self.assertEqual(job.state['status'], 'cancelled')
        self.assertFalse(job.folder.exists())
        job = self.flow.start_assembly_join_preview(ids, 0)
        self.assertTrue(job.wait(15))
        try:
            self.flow.save_draft(ids[0], 'Changed manuscript.')
            with self.assertRaises(ProjectError):
                self.flow.finish_assembly_join_preview(job)
        finally:
            self.flow.discard_assembly_join_preview(job)
        self.flow.save_draft(ids[0], '第 1 批。')
        self.flow.confirm_reading(ids[0])
        # A different reading id requires regeneration even if text was restored.
        with self.assertRaises(ProjectError):
            self.flow.start_assembly_join_preview(ids, 0)
        self.assertEqual(list(self.flow.root.glob('.join-preview-*')), [])

    def test_txt_and_single_batch_have_no_page_warnings(self):
        ids = self.prepare(2)
        self.assertEqual(self.flow.inspect_assembly_joins(ids[:1]), [])
        self.assertIsNone(self.flow.inspect_assembly_joins(ids)[0]['warning'])
        with self.assertRaises(ProjectError):
            self.flow.start_assembly_join_preview(ids[:1], 0)

    def test_source_changed_after_preview_preparation_is_not_played(self):
        ids = self.prepare(2)
        job = self.flow.start_assembly_join_preview(ids, 0)
        self.assertTrue(job.wait(15))
        try:
            with self.flow.narration_path(ids[0]).open('ab') as stream:
                stream.write(b'corrupted after preparation')
            with self.assertRaises(ProjectError):
                self.flow.finish_assembly_join_preview(job)
        finally:
            self.flow.discard_assembly_join_preview(job)
        self.assertFalse(job.folder.exists())

    def test_fractional_clip_boundary_does_not_create_empty_caption(self):
        wav = self.path/'fractional.wav'
        with wave.open(str(wav), 'wb') as output:
            output.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
            output.writeframes(b'\x40\x00'*95990)
        mp3 = self.path/'fractional.mp3'
        subprocess.run([os.environ['EBOOK2MP4_FFMPEG'], '-v', 'error', '-i', str(wav),
                        '-c:a', 'libmp3lame', '-b:a', '96k', str(mp3)], check=True)
        ids = self.prepare(2, mp3.read_bytes())
        # Import a checksum-consistent, valid SRT through the project-file boundary.
        manifest = json.loads((self.flow.root/'project.json').read_bytes())
        ref = next(b for b in manifest['batches'] if b['id'] == ids[0])['narration']['srt']
        data = ('1\n00:00:00,000 --> 00:00:01,000\nFirst sentence.\n\n'
                '2\n00:00:01,000 --> 00:00:04,000\nLast sentence.\n\n').encode('utf-8')
        (self.flow.root/ref['path']).write_bytes(data)
        ref['sha256'] = hashlib.sha256(data).hexdigest()
        (self.flow.root/'project.json').write_text(json.dumps(manifest), encoding='utf-8')
        self.flow = ProjectWorkflow.open(self.flow.root)
        job = self.flow.start_assembly_join_preview(ids, 0, clip_ms=3000)
        try:
            self.assertTrue(job.wait(15))
            self.assertEqual(job.state['status'], 'completed', job.state)
            preview = self.flow.finish_assembly_join_preview(job)
            srt = Path(preview['srt_path']).read_text(encoding='utf-8')
            self.assertNotIn('00:00:00,000 --> 00:00:00,000', srt)
            self.assertIn('Last sentence.', preview['left_text'])
        finally:
            self.flow.discard_assembly_join_preview(job)


if __name__ == '__main__':
    unittest.main()
