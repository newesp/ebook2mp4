"""Long-draft journeys at ProjectWorkflow; only the external service is replaced."""
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from ebook2mp4.workflow import ProjectWorkflow, ProjectError


class LongDraft(unittest.TestCase):
    def setUp(self):
        base = Path('.scratch/test-runs')
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.original = '\n\n'.join(letter * 3500 + '。' for letter in ('甲', '乙', '丙'))
        source = self.folder / 'source.txt'
        source.write_bytes(self.original.encode('utf-8'))
        self.flow = ProjectWorkflow.create(self.folder / 'book', '長稿')
        self.batch = self.flow.import_txt(self.flow.inspect_txt(source))
        env = patch.dict('os.environ', GEMINI_API_KEY='synthetic-key')
        env.start()
        self.addCleanup(env.stop)

    def stop(self, job):
        job.cancel()
        self.assertTrue(job.wait(5))

    def test_middle_failure_is_retained_after_reopen_and_only_failed_range_retries(self):
        outgoing = []
        def service(key, model, paragraphs):
            outgoing.extend(paragraphs)
            if paragraphs[0].startswith('乙'):
                raise ProjectError('合成網路失敗')
            return dict(paragraphs=[p + '改' for p in paragraphs], notes=[])
        with patch('ebook2mp4.gemini.generate', side_effect=service):
            job = self.flow.start_gemini_review(self.batch, script='preserve', punctuation=False)
            self.addCleanup(self.stop, job)
            self.assertTrue(job.wait(5))
            review_id = self.flow.finish_gemini_review(job)
        self.assertEqual(job.state['status'], 'partial')
        reopened = ProjectWorkflow.open(self.flow.root)
        review = reopened.gemini_reviews(self.batch)[0]
        self.assertEqual([r['status'] for r in review['requests']], ['completed', 'failed', 'completed'])
        self.assertEqual(outgoing, [p + '。' for p in ('甲' * 3500, '乙' * 3500, '丙' * 3500)])
        self.assertEqual(reopened.texts(self.batch)[1], self.original)
        reopened.decide_gemini(self.batch, review_id, 0, 'accepted')
        with self.assertRaises(ProjectError):
            reopened.decide_gemini(self.batch, review_id, 1, 'accepted')
        with patch('ebook2mp4.gemini.generate', return_value=dict(paragraphs=['乙' * 3500 + '。改'], notes=[])) as service:
            retry = reopened.start_gemini_retry(self.batch, review_id, failed_only=True)
            self.addCleanup(self.stop, retry)
            self.assertTrue(retry.wait(5))
            reopened.finish_gemini_review(retry)
            self.assertEqual(service.call_args.args[2], ['乙' * 3500 + '。'])
            self.assertEqual(service.call_count, 1)
        final = ProjectWorkflow.open(reopened.root).gemini_reviews(self.batch)[0]
        self.assertEqual(final['status'], 'completed')
        self.assertEqual(final['paragraphs'][0]['decision'], 'accepted')
        reopened.decide_gemini(self.batch, review_id, None, 'accepted')
        self.assertEqual(reopened.texts(self.batch)[1], self.original.replace('。', '。改'))
        reopened.undo_gemini(self.batch, review_id)
        self.assertEqual(reopened.texts(self.batch)[1], self.original)

    def test_cancel_keeps_checkpoint_and_late_output_is_not_reused(self):
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        def service(key, model, paragraphs):
            if paragraphs[0].startswith('乙'):
                entered.set()
                release.wait(4)
            return dict(paragraphs=[p + '改' for p in paragraphs], notes=['合成疑點'])
        with patch('ebook2mp4.gemini.generate', side_effect=service):
            job = self.flow.start_gemini_review(self.batch, script='preserve', punctuation=False)
            self.addCleanup(self.stop, job)
            self.assertTrue(entered.wait(4))
            # No finish or UI polling: the prior successful request is already durable.
            saved = ProjectWorkflow.open(self.flow.root).gemini_reviews(self.batch)[0]
            self.assertEqual(saved['status'], 'interrupted')
            self.assertEqual(saved['paragraphs'][0]['candidate'], '甲' * 3500 + '。改')
            self.assertIsNone(saved['paragraphs'][1]['candidate'])
            job.cancel()
            release.set()
            self.assertTrue(job.wait(4))
            review_id = self.flow.finish_gemini_review(job)
        reopened = ProjectWorkflow.open(self.flow.root)
        saved = reopened.gemini_reviews(self.batch)[0]
        self.assertEqual([r['status'] for r in saved['requests']], ['completed', 'cancelled', 'pending'])
        self.assertEqual(saved['status'], 'cancelled')
        with self.assertRaisesRegex(ProjectError, '沒有需要'):
            reopened.start_gemini_retry(self.batch, review_id, failed_only=True)
        outgoing = []
        def retry_service(key, model, paragraphs):
            outgoing.extend(paragraphs)
            return dict(paragraphs=paragraphs, notes=[])
        with patch('ebook2mp4.gemini.generate', side_effect=retry_service):
            retry = reopened.start_gemini_retry(self.batch, review_id)
            self.addCleanup(self.stop, retry)
            self.assertTrue(retry.wait(4))
            reopened.finish_gemini_review(retry)
        self.assertEqual(outgoing, ['乙' * 3500 + '。', '丙' * 3500 + '。'])
        self.assertEqual(reopened.gemini_reviews(self.batch)[0]['paragraphs'][0]['candidate'], '甲' * 3500 + '。改')

    def test_changed_source_blocks_resume_and_apply_without_losing_candidates(self):
        with patch('ebook2mp4.gemini.generate', side_effect=[
                dict(paragraphs=['甲' * 3500 + '。改'], notes=[]), ProjectError('中段失敗'),
                dict(paragraphs=['丙' * 3500 + '。改'], notes=[])]):
            job = self.flow.start_gemini_review(self.batch, script='preserve', punctuation=False)
            self.addCleanup(self.stop, job)
            self.assertTrue(job.wait(4))
            review_id = self.flow.finish_gemini_review(job)
        self.flow.save_draft(self.batch, '人工新稿')
        reopened = ProjectWorkflow.open(self.flow.root)
        with self.assertRaisesRegex(ProjectError, '版本已變更'):
            reopened.start_gemini_retry(self.batch, review_id)
        with self.assertRaisesRegex(ProjectError, '版本已變更'):
            reopened.decide_gemini(self.batch, review_id, 0, 'accepted')
        self.assertEqual(reopened.texts(self.batch)[1], '人工新稿')
        self.assertEqual(reopened.gemini_reviews(self.batch)[0]['paragraphs'][0]['candidate'], '甲' * 3500 + '。改')

    def test_selected_oversized_paragraph_covers_source_once_and_keeps_separators(self):
        text = '外面\r\n\r\n' + '一個句子。' * 2500 + '    \r\n\r\n結尾'
        self.flow.save_draft(self.batch, text)
        start, end = 6, len(text)-6
        outgoing = []
        def service(key, model, paragraphs):
            outgoing.extend(paragraphs)
            self.assertLessEqual(sum(map(len, paragraphs)), 6000)
            return dict(paragraphs=paragraphs, notes=[])
        with patch('ebook2mp4.gemini.generate', side_effect=service):
            job = self.flow.start_gemini_review(self.batch, start=start, end=end, script='preserve', punctuation=False)
            self.addCleanup(self.stop, job)
            self.assertTrue(job.wait(5))
            review_id = self.flow.finish_gemini_review(job)
        review = ProjectWorkflow.open(self.flow.root).gemini_reviews(self.batch)[0]
        self.assertEqual(review['requests'][0]['start'], start)
        self.assertEqual(review['requests'][-1]['end'], end)
        self.assertEqual(''.join(outgoing), text[start:end])
        self.flow.decide_gemini(self.batch, review_id, None, 'accepted')
        self.assertEqual(self.flow.texts(self.batch)[1], text)

    def test_invalid_response_cannot_leave_half_of_request_as_success(self):
        self.flow.save_draft(self.batch, '甲。\n\n乙。')
        with patch('ebook2mp4.gemini.generate', return_value=dict(paragraphs=['修改甲。', ''], notes=[])):
            job = self.flow.start_gemini_review(self.batch)
            self.addCleanup(self.stop, job)
            self.assertTrue(job.wait(5))
            self.flow.finish_gemini_review(job)
        review = ProjectWorkflow.open(self.flow.root).gemini_reviews(self.batch)[0]
        self.assertEqual(review['requests'][0]['status'], 'failed')
        self.assertEqual([p['candidate'] for p in review['paragraphs']], [None, None])

    def test_oversized_paragraph_leading_space_is_never_sent_alone(self):
        text = ' ' + '甲' * 6500
        self.flow.save_draft(self.batch, text)
        def service(key, model, paragraphs):
            self.assertTrue(all(p.strip() for p in paragraphs))
            return dict(paragraphs=paragraphs, notes=[])
        with patch('ebook2mp4.gemini.generate', side_effect=service):
            job = self.flow.start_gemini_review(self.batch)
            self.addCleanup(self.stop, job)
            self.assertTrue(job.wait(5))
            review_id = self.flow.finish_gemini_review(job)
        self.assertEqual(job.state['status'], 'completed')
        self.flow.decide_gemini(self.batch, review_id, None, 'accepted')
        self.assertEqual(ProjectWorkflow.open(self.flow.root).texts(self.batch)[1], text)

    def test_final_save_recovers_accurate_status_after_checkpoint_write_failure(self):
        import os
        self.flow.save_draft(self.batch, '甲。')
        replace = os.replace
        def disk_failure(source, destination):
            if Path(destination).name.startswith('gemini-progress-'):
                raise OSError('controlled journal disk failure')
            return replace(source, destination)
        with patch('ebook2mp4.gemini.generate', return_value=dict(paragraphs=['甲改。'], notes=[])), patch(
                'os.replace', side_effect=disk_failure):
            job = self.flow.start_gemini_review(self.batch)
            self.addCleanup(self.stop, job)
            self.assertTrue(job.wait(5))
        review_id = self.flow.finish_gemini_review(job)
        saved = ProjectWorkflow.open(self.flow.root).gemini_reviews(self.batch)[0]
        self.assertEqual(saved['status'], 'completed')
        self.assertEqual(saved['error'], '')
        self.flow.decide_gemini(self.batch, review_id, 0, 'accepted')
        self.assertEqual(self.flow.texts(self.batch)[1], '甲改。')

    def test_long_unbroken_text_scope_returns_without_freezing_the_caller(self):
        import subprocess
        import sys
        for text in ('漢字內容' * 25000, 'A' * 100000, '9' * 100000):
            with self.subTest(script=text[0]):
                self.flow.save_draft(self.batch, text)
                result = subprocess.run([sys.executable, '-c',
                    'import sys; from ebook2mp4.workflow import ProjectWorkflow; '
                    'f=ProjectWorkflow.open(sys.argv[1]); '
                    'assert f.gemini_scope(sys.argv[2])["characters"] == 100000',
                    str(self.flow.root), self.batch], timeout=10, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))

    def test_process_interruption_reopens_checkpoint_and_resumes_remaining_ranges(self):
        import subprocess
        import sys
        code = '''import os, sys
from unittest.mock import patch
from ebook2mp4.workflow import ProjectWorkflow
flow = ProjectWorkflow.open(sys.argv[1])
def service(key, model, paragraphs):
    if paragraphs[0].startswith('乙'):
        os._exit(0)
    return dict(paragraphs=paragraphs, notes=[])
with patch('ebook2mp4.gemini.generate', side_effect=service):
    flow.start_gemini_review(sys.argv[2], script='preserve', punctuation=False).wait()
'''
        result = subprocess.run([sys.executable, '-c', code, str(self.flow.root), self.batch],
                                timeout=10, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        reopened = ProjectWorkflow.open(self.flow.root)
        review = reopened.gemini_reviews(self.batch)[0]
        self.assertEqual(review['status'], 'interrupted')
        self.assertEqual([r['status'] for r in review['requests']], ['completed', 'pending', 'pending'])
        outgoing = []
        def service(key, model, paragraphs):
            outgoing.extend(paragraphs)
            return dict(paragraphs=paragraphs, notes=[])
        with patch('ebook2mp4.gemini.generate', side_effect=service):
            retry = reopened.start_gemini_retry(self.batch, review['id'])
            self.addCleanup(self.stop, retry)
            self.assertTrue(retry.wait(5))
            reopened.finish_gemini_review(retry)
        self.assertEqual(outgoing, ['乙' * 3500 + '。', '丙' * 3500 + '。'])
        self.assertEqual(reopened.gemini_reviews(self.batch)[0]['status'], 'completed')
