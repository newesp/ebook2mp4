"""Existing batch movies merge through the public workflow using real local tools."""
import os
import subprocess
from unittest.mock import patch
from pathlib import Path
import unittest
import json
import hashlib
from ebook2mp4.workflow import ProjectError
import test_total_video as fixture
from ebook2mp4.workflow import ProjectWorkflow

class MergeVideoJourney(unittest.TestCase):
    setUp = fixture.TotalVideoJourney.setUp
    prepare = fixture.TotalVideoJourney.prepare
    refresh_voices = fixture.TotalVideoJourney.refresh_voices
    audio = fixture.TotalVideoJourney.audio
    picture = fixture.TotalVideoJourney.picture

    def movies(self, count=2):
        ids = self.prepare(count)
        for i, identity in enumerate(ids):
            target = self.flow.batch_video_target(identity)
            from PIL import Image
            image=self.picture()
            Image.new('RGB',(80,120),'red' if i%2==0 else 'blue').save(image)
            target.save_total_video_settings(image=self.flow.inspect_total_video_image(image),
                resolution='720p' if i % 2 == 0 else '1080p')
            job = target.start_total_video()
            self.assertTrue(job.wait(40), job.state)
            target.finish_total_video(job)
        return ids

    def merge_video(self):
        with patch('edge_tts.Communicate', side_effect=AssertionError('No TTS')):
            job = self.flow.start_video_merge()
            self.assertTrue(job.wait(60), job.state)
            self.assertEqual(job.state['status'], 'completed', job.state)
            result=self.flow.finish_total_video(job)
            print(json.dumps(dict(kind='merged-video',batches=len(result['sources']),pause_ms=result['pause_ms'],
                video_ms=result['duration_ms'],audio_ms=job.result['audio_duration_ms']),ensure_ascii=False),flush=True)
            return result

    def test_merge_uses_only_movies_and_shared_order_without_total_audio(self):
        a,b = self.movies()
        before = [self.flow.batch_video_target(i).total_video_path().read_bytes() for i in (a,b)]
        self.flow.save_video_merge_settings([b,a], resolution='720p')
        # Completed MP4 and its SRT suffice even if the original MP3 is no longer available.
        for i in (a,b): self.flow.narration_path(i).unlink()
        self.flow = ProjectWorkflow.open(self.flow.root)
        result = self.merge_video()
        self.assertIsNone(self.flow.total_audio())
        self.assertFalse(result['stale'])
        self.assertLessEqual(abs(result['duration_ms']-900),200)
        self.assertEqual([s['batch_id'] for s in result['sources']],[b,a])
        srt=self.flow.total_video_path('srt').read_text(encoding='utf-8')
        self.assertLess(srt.index('第 2 批。'),srt.index('第 1 批。'))
        self.assertIn('00:00:00,700 --> ',srt)
        self.assertEqual([self.flow.batch_video_target(i).total_video_path().read_bytes() for i in (a,b)],before)
        reopened=ProjectWorkflow.open(self.flow.root)
        self.assertFalse(reopened.total_video()['stale'])
        self.assertEqual([s['batch_id'] for s in reopened.assembly_settings()['sources']],[b,a])


    def test_default_counts_extreme_pauses_actual_frames_silence_and_encoding(self):
        ids=self.movies(3)
        for count,pause,expected in ((1,500,200),(2,500,900),(3,500,1600),(2,0,400),(2,5000,5400),(3,17,634)):
            with self.subTest(count=count,pause=pause):
                self.flow.save_video_merge_settings(ids[:count],pause,resolution='720p')
                result=self.merge_video()
                self.assertLessEqual(abs(result['duration_ms']-expected),200)
                self.assertEqual(self.flow.total_video_path('srt').read_text(encoding='utf-8').count(' --> '),count)
        self.flow.save_video_merge_settings(ids[:2],500,resolution='720p');self.merge_video()
        path=self.flow.total_video_path()
        metadata=json.loads(subprocess.check_output([os.environ['EBOOK2MP4_FFPROBE'],'-v','error','-show_streams','-of','json',str(path)]))
        v,a=metadata['streams']
        self.assertEqual((v['codec_name'],v['width'],v['height'],v['pix_fmt'],v['r_frame_rate']),('h264',1280,720,'yuv420p','30/1'))
        self.assertEqual((a['codec_name'],a['profile'],a['sample_rate'],a['channels']),('aac','LC','48000',2))
        def pixel(second):
            return subprocess.check_output([os.environ['EBOOK2MP4_FFMPEG'],'-v','error','-ss',str(second),'-i',str(path),
                '-frames:v','1','-vf','crop=2:2:640:360','-pix_fmt','rgb24','-f','rawvideo','-'])[:3]
        self.assertGreater(pixel(.1)[0],200)
        self.assertGreater(pixel(.45)[0],200)
        self.assertGreater(pixel(.75)[2],200)
        pcm=subprocess.check_output([os.environ['EBOOK2MP4_FFMPEG'],'-v','error','-ss','0.35','-i',str(path),'-t','0.15',
            '-vn','-ac','1','-ar','24000','-f','s16le','-'])
        import array
        values=array.array('h',pcm)
        self.assertLessEqual(max(abs(x) for x in values),2)
        raw=path.read_bytes();self.assertLess(raw.index(b'moov'),raw.index(b'mdat'))

    def test_preview_matches_join_and_cleans_on_cancel(self):
        a,b=self.movies()
        self.flow.save_video_merge_settings([a,b],500,resolution='720p')
        preview=self.flow.start_video_join_preview([a,b],0,pause_ms=500,clip_ms=3000)
        self.assertTrue(preview.wait(60),preview.state)
        result=self.flow.finish_video_join_preview(preview)
        self.assertLessEqual(abs(result['duration_ms']-900),200)
        self.assertIn('第 1 批。',result['left_text']);self.assertIn('第 2 批。',result['right_text'])
        from ebook2mp4.workflow import digest
        self.assertEqual(digest((self.flow.root/result['mp4']['path']).read_bytes()),result['mp4']['sha256'])
        self.flow.discard_assembly_join_preview(preview)
        self.assertFalse(list(self.flow.root.glob('.video-join-*')))
        job=self.flow.start_video_join_preview([a,b],0,pause_ms=5000);job.cancel()
        self.assertTrue(job.wait(30));self.flow.discard_assembly_join_preview(job)
        self.assertFalse(list(self.flow.root.glob('.video-join-*')))

    def test_failure_cancel_stale_and_changed_publication_preserve_previous_outputs(self):
        a,b=self.movies()
        self.flow.save_assembly_settings([a,b]);audiojob=self.flow.start_total_audio()
        self.assertTrue(audiojob.wait(30));audio=self.flow.finish_total_audio(audiojob)
        self.flow.save_video_merge_settings([a,b],resolution='720p');old=self.merge_video()
        before=self.flow.total_video_path().read_bytes()
        job=self.flow.start_video_merge();job.cancel();self.assertTrue(job.wait(30));self.flow.discard_total_video(job)
        self.assertEqual(self.flow.total_video()['id'],old['id'])
        job=self.flow.start_video_merge();self.assertTrue(job.wait(60),job.state)
        self.flow.batch_video_target(a).total_video_path().write_bytes(b'broken')
        with self.assertRaises(ProjectError):self.flow.finish_total_video(job)
        self.flow.discard_total_video(job)
        self.assertEqual(self.flow.total_video_path().read_bytes(),before)
        self.assertEqual(self.flow.total_audio()['id'],audio['id'])
        invalid=next(r for r in self.flow.inspect_video_merge() if r['batch_id']==a)
        self.assertFalse(invalid['valid'])
        job=self.flow.start_video_merge();self.assertTrue(job.wait(30),job.state)
        self.assertEqual(job.state['status'],'failed');self.flow.discard_total_video(job)
        self.assertEqual(self.flow.total_video()['id'],old['id'])
        self.assertFalse((self.flow.root/'.production.lock').exists())
        target=self.path/'export-video';self.flow.export_total_video(target)
        self.assertEqual((target/'total.mp4').read_bytes(),before)
        self.flow.save_draft(b,'已修改。')
        self.assertTrue(self.flow.total_video()['stale'])
        with self.assertRaises(ProjectError):self.flow.save_video_merge_settings([b])


    def test_pdf_warnings_require_confirmation_and_survive_reopen(self):
        from test_assembly_joins import AssemblyJoinJourney
        ids=AssemblyJoinJourney.pdf_batches(self)
        AssemblyJoinJourney.narrate(self,ids)
        for identity in ids:
            target=self.flow.batch_video_target(identity)
            target.save_total_video_settings(image=self.flow.inspect_total_video_image(self.picture()),resolution='720p')
            job=target.start_total_video();self.assertTrue(job.wait(40),job.state);target.finish_total_video(job)
        joins=self.flow.inspect_video_merge_joins(ids)
        self.assertEqual([j['warning']['kind'] for j in joins],['overlap','gap'])
        self.flow.save_video_merge_settings(ids,resolution='720p')
        with self.assertRaisesRegex(ProjectError,'頁碼'):self.flow.start_video_merge()
        self.flow.save_video_merge_settings(ids,resolution='720p',accepted_joins=[j['key'] for j in joins])
        self.flow=ProjectWorkflow.open(self.flow.root)
        self.assertTrue(all(j['accepted'] for j in self.flow.inspect_video_merge_joins(ids)))
        self.merge_video()
        self.flow.save_video_merge_settings(ids[::-1],resolution='720p')
        with self.assertRaisesRegex(ProjectError,'頁碼'):self.flow.start_video_merge()

    def test_failed_publication_can_retry_without_reencoding_and_unselected_changes_are_ignored(self):
        a,b=self.movies()
        self.flow.save_video_merge_settings([a],resolution='720p');old=self.merge_video()
        self.flow.save_draft(b,'未選批次變更。')
        self.assertFalse(self.flow.total_video()['stale'])
        self.flow.save_video_merge_settings([a],1000,resolution='720p')
        job=self.flow.start_video_merge();self.assertTrue(job.wait(40),job.state)
        artifact=(self.flow.root/job.result['artifacts']['mp4']['path']).read_bytes()
        original=os.replace
        def denied(source,target):
            if Path(target)==self.flow.root/'project.json':raise PermissionError('test publication failure')
            return original(source,target)
        with patch('os.replace',side_effect=denied):
            with self.assertRaises(ProjectError):self.flow.finish_total_video(job)
        self.assertEqual(self.flow.total_video()['id'],old['id'])
        result=self.flow.finish_total_video(job)
        self.assertNotEqual(result['id'],old['id'])
        self.assertEqual(self.flow.total_video_path().read_bytes(),artifact)
        self.assertFalse((self.flow.root/'.production.lock').exists())


    def test_moving_batch_holds_actual_final_frame_in_preview_and_total(self):
        from test_total_video_background import background,pixel
        a,b=self.movies()
        source=background(self.path/'moving.mp4',.2)
        target=self.flow.batch_video_target(a)
        target.save_total_video_settings(background=self.flow.inspect_total_video_background(source),source_type='video',resolution='720p')
        job=target.start_total_video();self.assertTrue(job.wait(40),job.state);target.finish_total_video(job)
        self.flow.save_video_merge_settings([a,b],500,resolution='720p');self.merge_video()
        path=self.flow.total_video_path()
        self.assertGreater(pixel(path,.01)[0],200)
        self.assertGreater(pixel(path,.09)[1],200)
        self.assertGreater(pixel(path,.45)[2],200)
        preview=self.flow.start_video_join_preview([a,b],0,pause_ms=500,clip_ms=3000)
        self.assertTrue(preview.wait(40),preview.state)
        result=self.flow.finish_video_join_preview(preview)
        self.assertGreater(pixel(self.flow.root/result['mp4']['path'],.45)[2],200)
        self.flow.discard_assembly_join_preview(preview)


    def test_media_failure_stops_after_three_attempts_and_preserves_output(self):
        import sys
        ids=self.movies(1)
        self.flow.save_video_merge_settings(ids,resolution='720p');old=self.merge_video()
        with patch.dict(os.environ,EBOOK2MP4_FFMPEG=sys.executable):
            job=self.flow.start_video_merge();self.assertTrue(job.wait(20),job.state)
            self.assertEqual(job.state['status'],'failed')
            self.assertEqual(job.state['attempt'],3)
            self.flow.discard_total_video(job)
        self.assertEqual(self.flow.total_video()['id'],old['id'])
        self.assertFalse((self.flow.root/'.production.lock').exists())
