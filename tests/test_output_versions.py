"""T20 route matrix through public workflows; real FFmpeg, synthetic TTS only."""
import unittest
from unittest.mock import patch
from PIL import Image
from ebook2mp4.workflow import ProjectWorkflow, ProjectError
import test_video_merge as fixture


class OutputVersionsJourney(unittest.TestCase):
    setUp = fixture.MergeVideoJourney.setUp
    prepare = fixture.MergeVideoJourney.prepare
    refresh_voices = fixture.MergeVideoJourney.refresh_voices
    audio = fixture.MergeVideoJourney.audio
    picture = fixture.MergeVideoJourney.picture
    movies = fixture.MergeVideoJourney.movies

    def finish_audio(self):
        job = self.flow.start_total_audio()
        self.assertTrue(job.wait(30), job.state)
        return self.flow.finish_total_audio(job)

    def finish_video(self, merge=False):
        job = self.flow.start_video_merge() if merge else self.flow.start_total_video()
        self.assertTrue(job.wait(60), job.state)
        self.assertEqual(job.state['status'], 'completed', job.state)
        return self.flow.finish_total_video(job)

    def ready(self):
        ids = self.movies(3)
        self.flow.save_assembly_settings(ids[:2])
        self.finish_audio()
        image = self.flow.inspect_total_video_image(self.picture('全片.png'))
        self.flow.save_total_video_settings(image=image, resolution='720p')
        self.finish_video()
        self.flow.save_video_merge_settings(ids[:2], resolution='720p')
        self.finish_video(True)
        return ids

    def states(self):
        rows = self.flow.output_versions()
        self.assertTrue(all(not r['error'] for r in rows), rows)
        return [bool(r['reasons']) for r in rows]

    def test_route_matrix_retains_both_movies_exports_and_reopens(self):
        a, b, c = self.ready()
        products = [r['product']['id'] for r in self.flow.output_versions()]
        with patch('edge_tts.Communicate', side_effect=AssertionError('No TTS')):
            self.assertEqual(self.states(), [False, False, False])
            for route in ('total-audio', 'batch-videos'):
                folder = self.path/route
                self.flow.export_total_video(folder, method=route)
                self.assertEqual((folder/'total.mp4').read_bytes(), self.flow.total_video_path(method=route).read_bytes())
                self.assertEqual((folder/'total.srt').read_bytes(), self.flow.total_video_path('srt', method=route).read_bytes())
            self.flow.save_draft(c, 'C 未選入。')
            self.flow.save_voice_settings('en-US-TestNeural', '+20%', batch_id=c)
            self.assertEqual(self.states(), [False, False, False])
            image = self.picture('全片新背景.png')
            Image.new('RGB', (100, 80), 'green').save(image)
            self.flow.save_total_video_settings(image=self.flow.inspect_total_video_image(image), resolution='720p')
            self.assertEqual(self.states(), [False, True, False])
            self.finish_video()
            self.assertEqual(self.states(), [False, False, False])
            target = self.flow.batch_video_target(a)
            target.save_total_video_settings(image=self.flow.inspect_total_video_image(image), resolution='720p')
            self.assertEqual(self.states(), [False, False, True])
            with self.assertRaises(ProjectError): self.flow.start_video_merge()
            job = target.start_total_video()
            self.assertTrue(job.wait(40), job.state)
            target.finish_total_video(job)
            self.assertEqual(self.states(), [False, False, True])
            self.flow.save_video_merge_settings([a,b], resolution='720p')
            self.finish_video(True)
            self.assertEqual(self.states(), [False, False, False])
            self.flow.save_video_merge_settings([a,b], resolution='1080p')
            self.assertEqual(self.states(), [False, False, True])
            self.flow.save_video_merge_settings([a,b], resolution='720p')
            self.flow.save_total_video_settings(resolution='1080p')
            self.assertEqual(self.states(), [False, True, False])
            self.flow.save_total_video_settings(resolution='720p')
            self.flow.save_assembly_settings([b,a], 1000)
            self.assertEqual(self.states(), [True, True, True])
            rows = self.flow.output_versions()
            self.assertEqual([s['batch_id'] for s in rows[0]['current_sources']], [b,a])
            self.assertEqual([s['batch_id'] for s in rows[0]['sources']], [a,b])
            self.flow = ProjectWorkflow.open(self.flow.root)
            self.assertEqual(self.states(), [True, True, True])
            self.assertEqual(self.flow.total_audio()['id'], products[0])
            for route in ('total-audio', 'batch-videos'):
                self.assertTrue(self.flow.total_video_path(method=route).is_file())

    def test_source_text_voice_new_audio_and_launch_snapshot(self):
        a,b,c = self.ready()
        old_audio = self.flow.total_audio()['id']
        self.finish_audio()
        self.assertNotEqual(old_audio, self.flow.total_audio()['id'])
        self.assertEqual(self.states(), [False, True, False])
        self.finish_video()
        # Metadata edits during a job do not get mixed into its delivered snapshot.
        job = self.flow.start_video_merge()
        self.flow.save_draft(a, '任務啟動後修改 A。')
        self.assertTrue(job.wait(60), job.state)
        result = self.flow.finish_total_video(job)
        self.assertTrue(result['stale'])
        self.assertEqual(result['sources'], job.snapshot['sources'])
        self.assertEqual(self.states(), [True, True, True])
        with self.assertRaises(ProjectError): self.flow.start_total_audio()
        with self.assertRaises(ProjectError): self.flow.start_total_video()
        with self.assertRaises(ProjectError): self.flow.start_video_merge()
        self.flow.confirm_reading(a)
        with patch('edge_tts.Communicate') as tts:
            audio = self.audio()
            tts.return_value.stream = lambda: self.stream(audio)
            narration = self.flow.start_narration(a)
            self.assertTrue(narration.wait(20), narration.state)
            self.flow.finish_narration(narration)
        self.flow.save_assembly_settings([a,b])
        self.finish_audio()
        self.assertEqual(self.states(), [False, True, True])
        self.finish_video()
        self.assertEqual(self.states(), [False, False, True])
        self.flow.save_voice_settings('en-US-TestNeural', '+20%', batch_id=a)
        self.assertEqual(self.states(), [True, True, True])
        self.flow = ProjectWorkflow.open(self.flow.root)
        self.assertEqual(self.states(), [True, True, True])

    async def stream(self, audio):
        yield dict(type='audio', data=audio)

    def test_video_launch_snapshot_cancel_and_corrupt_output_are_route_local(self):
        a,b,c = self.ready()
        old = self.flow.total_video(method='total-audio')
        job = self.flow.start_total_video()
        job.cancel()
        self.assertTrue(job.wait(30))
        self.flow.discard_total_video(job)
        rows = self.flow.output_versions()
        self.assertEqual(rows[1]['task']['progress']['status'], 'cancelled')
        self.assertEqual(rows[1]['product']['id'], old['id'])
        job = self.flow.start_total_video()
        self.flow.save_voice_settings('zh-TW-TestNeural', '+20%', batch_id=b)
        self.assertTrue(job.wait(40), job.state)
        product = self.flow.finish_total_video(job)
        self.assertTrue(product['stale'])
        self.assertEqual(product['audio'], job.snapshot['audio'])
        self.assertEqual(product['visual'], job.snapshot['visual'])
        self.assertFalse((self.flow.root/'.production.lock').exists())
        self.flow.total_video_path(method='total-audio').write_bytes(b'broken')
        rows = self.flow.output_versions()
        self.assertTrue(rows[1]['error'])
        self.assertFalse(rows[0]['error'])
        self.assertFalse(rows[2]['error'])
        from ebook2mp4.output_versions import describe
        self.assertIn('請檢查檔案', describe(self.flow, rows[1]))

    def test_empty_and_legacy_project_migration(self):
        self.assertEqual([r['status'] for r in self.flow.output_versions()], ['尚未製作']*3)
        ids = self.movies(1)
        self.flow.save_video_merge_settings(ids, resolution='720p')
        old = self.finish_video(True)
        # Simulate the format written before T20, keeping the original successful movie.
        import json
        manifest = self.flow.state
        manifest.pop('total_video_products')
        path = self.flow.root/'project.json'
        path.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
        self.flow = ProjectWorkflow.open(self.flow.root)
        self.assertEqual(self.flow.total_video(method='batch-videos')['id'], old['id'])
        self.assertIsNone(self.flow.total_video(method='total-audio'))
        self.flow.save_assembly_settings(ids)
        self.finish_audio()
        self.flow.save_total_video_settings(image=self.flow.inspect_total_video_image(self.picture()), resolution='720p')
        self.finish_video()
        self.flow = ProjectWorkflow.open(self.flow.root)
        self.assertEqual(self.flow.total_video(method='batch-videos')['id'], old['id'])
        self.assertEqual(self.states(), [False, False, False])
