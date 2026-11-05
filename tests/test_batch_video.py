"""Batch video uses the shared workflow without total products or TTS."""
from unittest.mock import patch
from ebook2mp4.workflow import ProjectWorkflow, ProjectError
import test_total_video as fixture


class BatchVideoJourney(fixture.TotalVideoJourney):
    # Reuse media fixtures; inherited book journeys guard compatibility.
    def test_batch_image_offline_isolation_and_stale_source(self):
        a, b = self.prepare(2)
        target = self.flow.batch_video_target(a)
        image = self.flow.inspect_total_video_image(self.picture())
        target.save_total_video_settings(image=image, resolution='720p')
        self.flow.save_total_video_settings(image=image, resolution='1080p')
        with patch('edge_tts.Communicate', side_effect=AssertionError('no TTS')):
            job = target.start_total_video()
            self.assertTrue(job.wait(30), job.state)
            self.assertEqual(job.state['status'], 'completed', job.state)
            product = target.finish_total_video(job)
        self.assertFalse(product['stale'])
        self.assertLessEqual(abs(product['duration_ms']-self.flow.narration(a)['duration_ms']),200)
        self.assertEqual(target.total_video_path('srt').read_bytes(),self.flow.narration_path(a,'srt').read_bytes())
        self.assertIsNone(self.flow.total_audio())
        self.assertIsNone(self.flow.total_video())
        self.assertIsNone(self.flow.batch_video_target(b).total_video())
        self.assertIsNone(self.flow.batch_video_target(b).total_video_settings()['image'])
        reopened = ProjectWorkflow.open(self.flow.root)
        saved = reopened.batch_video_target(a)
        self.assertEqual(saved.total_video()['id'],product['id'])
        saved.save_total_video_settings(resolution='1080p')
        self.assertTrue(saved.total_video()['stale'])
        self.assertEqual(reopened.total_video_settings()['resolution'],'1080p')
        reopened.save_draft(a,'已修改。')
        with self.assertRaises(ProjectError): saved.start_total_video()
        self.assertTrue(saved.total_video_path().is_file())

    def test_background_modes_cancel_and_wrong_target_publication(self):
        import asyncio
        from test_total_video_background import background
        from ebook2mp4.total_video import inspect_background
        a,b = self.prepare(2)
        target = self.flow.batch_video_target(a)
        source = background(self.path/'背景.mp4', .1, portrait=True)
        media = asyncio.run(inspect_background(source))
        for mode in ('loop','hold'):
            target.save_total_video_settings(background=media,source_type='video',background_mode=mode,resolution='720p')
            job=target.start_total_video()
            self.assertTrue(job.wait(30),job.state)
            self.assertEqual(job.state['status'],'completed',job.state)
            with self.assertRaises(ProjectError): self.flow.batch_video_target(b).finish_total_video(job)
            with self.assertRaises(ProjectError): self.flow.finish_total_video(job)
            product=target.finish_total_video(job)
            self.assertFalse(product['stale'])
        old=product['id']
        job=target.start_total_video();job.cancel()
        self.assertTrue(job.wait(30),job.state)
        target.discard_total_video(job)
        self.assertEqual(target.total_video()['id'],old)
        from ebook2mp4.production_lock import production_active
        self.assertFalse(production_active(self.flow.root/'.production.lock'))
