"""T21 public journeys: actual local media, synthetic TTS, format-local retry."""
import unittest
from unittest.mock import patch

from ebook2mp4.workflow import ProjectWorkflow, ProjectError
import test_video_merge as fixture


class OutputsJourney(unittest.TestCase):
    setUp = fixture.MergeVideoJourney.setUp
    prepare = fixture.MergeVideoJourney.prepare
    refresh_voices = fixture.MergeVideoJourney.refresh_voices
    audio = fixture.MergeVideoJourney.audio
    picture = fixture.MergeVideoJourney.picture
    movies = fixture.MergeVideoJourney.movies

    def test_moved_partial_project_finishes_video_without_new_speech(self):
        self.plan(self.prepare(2))
        self.assertEqual(self.run_outputs()['status'], 'partial')
        original_audio = self.flow.total_audio_path().read_bytes()
        original_srt = self.flow.total_audio_path('srt').read_bytes()
        original_id = self.flow.total_audio()['id']
        previous_root = self.flow.root.resolve()
        destination = previous_root.with_name('搬移 書籍（T22）')
        self.assertTrue(previous_root.is_relative_to(self.path.resolve()))
        self.assertTrue(destination.is_relative_to(self.path.resolve()))
        self.assertFalse(destination.exists())
        previous_root.rename(destination)
        self.flow = ProjectWorkflow.open(destination)
        self.assertEqual(self.flow.inspect_outputs()['status'], 'partial')
        self.assertEqual(self.flow.output_formats(), ['mp3', 'mp4'])
        self.visual()
        with patch('ebook2mp4.assembly.start', side_effect=AssertionError('moved valid audio must be reused')):
            self.assertEqual(self.run_outputs()['status'], 'completed')
        self.assertEqual(self.flow.total_audio()['id'], original_id)
        self.assertEqual(self.flow.total_audio_path().read_bytes(), original_audio)
        self.assertEqual(self.flow.total_video_path('srt').read_bytes(), original_srt)
        self.assertTrue(self.flow.total_video_path().is_file())
        self.assertFalse(previous_root.exists())

    def plan(self, ids, formats=('mp3', 'mp4'), method='total-audio'):
        self.flow.save_total_video_method(method)
        self.flow.save_output_plan(ids, resolution='720p')
        self.flow.save_output_formats(list(formats))

    def visual(self):
        self.flow.save_total_video_settings(image=self.flow.inspect_total_video_image(self.picture()), resolution='720p')

    def run_outputs(self):
        with patch('edge_tts.Communicate', side_effect=AssertionError('output must never call TTS')) as tts:
            job = self.flow.start_outputs()
            self.assertTrue(job.wait(60), job.state)
            result = self.flow.finish_outputs(job)
            tts.assert_not_called()
        self.assertFalse((self.flow.root/'.production.lock').exists())
        return result

    def test_missing_visual_publishes_audio_reopen_only_encodes_video(self):
        self.plan(self.prepare(2))
        self.assertEqual(self.flow.inspect_outputs()['rows']['mp4']['status'], 'missing')
        result = self.run_outputs()
        self.assertEqual(result['status'], 'partial')
        audio = self.flow.total_audio()
        original = self.flow.total_audio_path().read_bytes()
        captions = self.flow.total_audio_path('srt').read_bytes()
        self.assertEqual(audio['duration_ms'], 900)
        self.flow = ProjectWorkflow.open(self.flow.root)
        self.assertEqual(self.flow.output_formats(), ['mp3', 'mp4'])
        self.assertEqual(self.flow.inspect_outputs()['status'], 'partial')
        self.visual()
        with patch('ebook2mp4.assembly.start', side_effect=AssertionError('valid MP3 must be reused')):
            self.assertEqual(self.run_outputs()['status'], 'completed')
            self.assertEqual(self.run_outputs()['status'], 'completed')
        self.assertEqual(self.flow.total_audio()['id'], audio['id'])
        self.assertEqual(self.flow.total_audio_path().read_bytes(), original)
        self.assertEqual(self.flow.total_video_path('srt').read_bytes(), captions)
        self.assertLessEqual(abs(self.flow.total_video()['duration_ms']-900), 200)
        self.assertEqual(len(self.flow.total_audio_runs()), 1)
        self.assertEqual(len(self.flow.total_video_runs()), 1)

    def test_mp4_only_prepares_audio_and_mp3_only_needs_no_visual(self):
        ids = self.prepare(1)
        self.plan(ids, ('mp3',))
        self.assertEqual(self.run_outputs()['status'], 'completed')
        self.assertIsNone(self.flow.total_video())
        self.visual()
        self.flow.save_output_formats(['mp4'])
        old = self.flow.total_audio()['id']
        self.assertEqual(self.run_outputs()['status'], 'completed')
        self.assertEqual(self.flow.total_audio()['id'], old)
        self.flow.save_output_plan(ids, 1000)
        self.assertEqual(self.flow.inspect_outputs()['rows']['mp4']['status'], 'stale')
        self.assertEqual(self.run_outputs()['status'], 'completed')
        self.assertNotEqual(self.flow.total_audio()['id'], old)
        self.assertEqual(self.flow.inspect_outputs()['formats'], ['mp4'])

    def test_audio_failure_does_not_block_batch_movies_and_retry_preserves_video(self):
        ids = self.movies(2)
        self.plan(ids, method='batch-videos')
        with patch('ebook2mp4.assembly.start', side_effect=ProjectError('模擬 MP3 磁碟空間不足')):
            result = self.run_outputs()
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['formats']['mp3']['status'], 'failed')
        movie = self.flow.total_video(method='batch-videos')
        self.assertIsNone(self.flow.total_audio())
        self.flow = ProjectWorkflow.open(self.flow.root)
        self.assertEqual(self.flow.inspect_outputs()['rows']['mp3']['status'], 'failed')
        with patch('ebook2mp4.video_merge.start', side_effect=AssertionError('valid movie must be reused')):
            self.assertEqual(self.run_outputs()['status'], 'completed')
        self.assertEqual(self.flow.total_video(method='batch-videos')['id'], movie['id'])

    def test_missing_batch_movie_does_not_block_audio_and_default_route_ignores_movies(self):
        ids = self.prepare(2)
        self.plan(ids, method='batch-videos')
        self.assertEqual(self.run_outputs()['status'], 'partial')
        old = self.flow.total_audio()['id']
        self.flow.save_total_video_method('total-audio')
        self.visual()
        self.assertEqual(self.run_outputs()['status'], 'completed')
        self.assertEqual(self.flow.total_audio()['id'], old)

    def test_batch_mp4_only_uses_movies_without_original_mp3_or_total_audio(self):
        ids = self.movies(2)
        self.plan(ids, ('mp4',), method='batch-videos')
        for identity in ids:
            self.flow.narration_path(identity).unlink()
        self.flow = ProjectWorkflow.open(self.flow.root)
        self.assertEqual(self.flow.inspect_outputs()['rows']['mp3']['status'], 'missing')
        self.assertEqual(self.run_outputs()['status'], 'completed')
        self.assertIsNone(self.flow.total_audio())
        self.assertLessEqual(abs(self.flow.total_video(method='batch-videos')['duration_ms']-900), 200)

    def test_video_failure_reopens_as_partial_and_cancel_releases_lease(self):
        self.plan(self.prepare(2))
        self.visual()
        with patch('ebook2mp4.total_video.start', side_effect=ProjectError('模擬影片編碼失敗')):
            result = self.run_outputs()
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['formats']['mp4']['status'], 'failed')
        old = self.flow.total_audio()['id']
        self.flow = ProjectWorkflow.open(self.flow.root)
        self.assertEqual(self.flow.inspect_outputs()['rows']['mp4']['status'], 'failed')
        job = self.flow.start_outputs()
        with self.assertRaises(ProjectError): self.flow.start_total_audio()
        with self.assertRaises(ProjectError): ProjectWorkflow.open(self.flow.root).start_outputs()
        job.cancel()
        self.assertTrue(job.wait(20), job.state)
        self.flow.finish_outputs(job)
        self.assertFalse((self.flow.root/'.production.lock').exists())
        self.assertEqual(self.flow.total_audio()['id'], old)
        self.assertEqual(self.run_outputs()['status'], 'completed')

    def test_source_change_during_audio_stops_next_stage_without_mixing_sources(self):
        ids = self.prepare(2)
        self.plan(ids)
        self.visual()
        job = self.flow.start_outputs()
        import time
        end = time.monotonic()+15
        while job.current != 'mp3' and not job.closed and time.monotonic()<end:
            job.wait(.02)
        self.assertEqual(job.current, 'mp3')
        self.flow.save_draft(ids[0], '任務啟動後變更。')
        self.assertTrue(job.wait(30), job.state)
        result = self.flow.finish_outputs(job)
        self.assertNotEqual(result['status'], 'completed')
        self.assertTrue(self.flow.total_audio()['stale'])
        self.assertIsNone(self.flow.total_video())

    def test_validation_and_missing_sources_are_observable(self):
        for invalid in ([], ['mp3', 'mp3'], ['wav']):
            with self.assertRaises(ProjectError): self.flow.save_output_formats(invalid)
        self.plan([self.batch])
        state = self.flow.inspect_outputs()
        self.assertEqual(state['rows']['mp3']['status'], 'missing')
        self.assertTrue(state['rows']['mp3']['missing'])
        self.assertEqual(self.run_outputs()['status'], 'incomplete')

    def test_failed_publication_waits_for_explicit_retry_and_preserves_other_format(self):
        self.plan(self.prepare(1))
        self.visual()
        job = self.flow.start_outputs()
        import time
        end = time.monotonic()+20
        while job.current != 'mp3' and not job.closed and time.monotonic()<end:
            job.wait(.02)
        self.assertEqual(job.current, 'mp3')
        self.assertTrue(job.child.wait(20))
        original = self.flow.finish_total_audio
        with patch.object(self.flow, 'finish_total_audio', side_effect=ProjectError('模擬儲存空間不足')) as publish:
            job.wait(0)
            self.assertTrue(job.publish_pending)
            job.wait(0)
            self.assertEqual(publish.call_count, 1)
            self.assertIsNone(self.flow.total_audio())
        job.retry_save()
        self.assertTrue(job.wait(40), job.state)
        result = self.flow.finish_outputs(job)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(len(self.flow.total_audio_runs()), 1)
        self.assertFalse((self.flow.root/'.production.lock').exists())

    def test_video_worker_failure_and_cancellation_preserve_successful_audio(self):
        self.plan(self.prepare(2))
        self.visual()
        from ebook2mp4.total_video import TotalVideoJob
        async def fail(*args, **kwargs):
            raise ProjectError('模擬 FFmpeg 輸出空間不足')
        with patch.object(TotalVideoJob, 'produce', fail):
            result = self.run_outputs()
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['formats']['mp4']['status'], 'failed')
        audio = self.flow.total_audio()['id']
        job = self.flow.start_outputs()
        import time
        end = time.monotonic()+20
        while job.current != 'mp4' and not job.closed and time.monotonic()<end:
            job.wait(.02)
        self.assertEqual(job.current, 'mp4')
        job.cancel()
        self.assertTrue(job.wait(30))
        result = self.flow.finish_outputs(job)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['formats']['mp4']['status'], 'cancelled')
        self.assertEqual(self.flow.total_audio()['id'], audio)
        self.assertEqual(self.flow.inspect_outputs()['rows']['mp4']['status'], 'cancelled')
        self.assertFalse((self.flow.root/'.production.lock').exists())
