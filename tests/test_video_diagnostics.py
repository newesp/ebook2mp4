"""FFmpeg progress and actionable failure diagnostics."""
import asyncio
import unittest
from unittest.mock import patch
from ebook2mp4.total_video import TotalVideoJob

class VideoDiagnostics(unittest.IsolatedAsyncioTestCase):
    async def test_unknown_progress_timestamp_does_not_fail_successful_encoding(self):
        stream=asyncio.StreamReader()
        stream.feed_data(b'frame=1\nout_time_us=N/A\nprogress=continue\nframe=30\nout_time_us=1000000\nprogress=end\n')
        stream.feed_eof()
        class Process:
            stdout=stream
            returncode=0
            async def wait(self):return 0
        async def launch(*args,**kwargs):return Process()
        job=object.__new__(TotalVideoJob)
        job.tool='ffmpeg'
        job.progress=lambda **changes:None
        with patch('asyncio.create_subprocess_exec',launch):
            result=await job.command([],phase='製作影片',duration_ms=1000)
        self.assertEqual(result['frame'],'30')

    async def test_failed_ffmpeg_preserves_reason_and_specific_recovery(self):
        from ebook2mp4.workflow import ProjectError
        stream=asyncio.StreamReader();stream.feed_eof()
        class Process:
            stdout=stream
            returncode=1
            async def wait(self):return 1
        async def launch(*args,**kwargs):
            kwargs['stderr'].write(b'Error opening output: No space left on device')
            return Process()
        job=object.__new__(TotalVideoJob);job.tool='ffmpeg';job.report={}
        job.progress=lambda **changes:job.report.update(changes)
        with patch('asyncio.create_subprocess_exec',launch):
            with self.assertRaisesRegex(ProjectError,'空間不足'):
                await job.command([],phase='製作影片',duration_ms=1000)
        self.assertEqual(job.report['diagnostic']['category'],'space')
        self.assertIn('No space left',job.report['diagnostic']['detail'])

    async def test_unknown_python_error_is_not_reported_as_network_failure(self):
        from ebook2mp4.workflow import ProjectError
        job=object.__new__(TotalVideoJob);job.report={}
        job.progress=lambda **changes:job.report.update(changes)
        async def operation():raise ValueError('unexpected timestamp')
        job.produce=operation
        with self.assertRaisesRegex(ProjectError,'非預期錯誤'):
            await job.diagnosed_produce()
        self.assertIn('ValueError',job.report['diagnostic']['detail'])

    def test_categories_have_actionable_guidance_and_bounded_evidence(self):
        from ebook2mp4.video_diagnostics import diagnose
        for message,category in [('Permission denied','permission'),('Cannot allocate memory','memory'),('Unknown encoder libx264','tool'),('Invalid data found','media')]:
            result=diagnose(message)
            self.assertEqual(result['category'],category)
            self.assertIn('→',result['message'])
        self.assertLessEqual(len(diagnose('x'*20000)['detail']),16384)
