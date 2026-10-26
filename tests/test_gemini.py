"""Gemini behavior at the shared project workflow seam; transport is external."""
from pathlib import Path
import tempfile
import unittest
import threading
import json
from unittest.mock import patch

from ebook2mp4.workflow import ProjectWorkflow, ProjectError


class GeminiJourney(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[1] / '.scratch' / 'test-runs'
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        source = self.folder / '原稿.txt'
        source.write_bytes('外面保留。\n\n這是錯宇。\n\n第二叚。\n\n結尾保留。'.encode('utf-8'))
        self.flow = ProjectWorkflow.create(self.folder / 'book', '測試書')
        self.batch = self.flow.import_txt(self.flow.inspect_txt(source))

    def test_selected_paragraph_decisions_undo_and_reopen(self):
        original = self.flow.texts(self.batch)[1]
        reading = self.flow.confirm_reading(self.batch)
        start = original.index('這')
        end = original.index('\n\n結尾')
        with patch('ebook2mp4.gemini.generate', return_value={
                'paragraphs': ['這是錯字。', '第二段。'], 'notes': ['']}), patch.dict(
                    'os.environ', GEMINI_API_KEY='test-secret'):
            job = self.flow.start_gemini_review(self.batch, start=start, end=end)
            self.assertTrue(job.wait(3))
            review_id = self.flow.finish_gemini_review(job)
        self.assertEqual(self.flow.texts(self.batch)[1], original)
        self.flow.decide_gemini(self.batch, review_id, 0, 'accepted')
        self.flow.decide_gemini(self.batch, review_id, 1, 'rejected')
        self.assertEqual(self.flow.texts(self.batch)[1], '外面保留。\n\n這是錯字。\n\n第二叚。\n\n結尾保留。')
        self.assertIsNone(self.flow.state['batches'][0]['current_reading'])
        self.assertEqual(self.flow.reading_text(self.batch, reading['id']), original)
        reopened = ProjectWorkflow.open(self.flow.root)
        self.assertEqual(reopened.gemini_reviews(self.batch)[0]['paragraphs'][1]['decision'], 'rejected')
        reopened.undo_gemini(self.batch, review_id)
        self.assertEqual(reopened.texts(self.batch), (original, original))
        self.assertNotIn('test-secret', ''.join(p.read_text(encoding='utf-8') for p in reopened.root.rglob('*') if p.is_file()))

    def test_edit_during_request_preserves_stale_candidate_without_overwrite(self):
        gate = threading.Event()
        self.addCleanup(gate.set)
        def response(*args):
            gate.wait(3)
            return dict(paragraphs=['外面保留。', '這是錯字。', '第二段。', '結尾保留。'], notes=['疑點保留'])
        with patch('ebook2mp4.gemini.generate', side_effect=response), patch.dict('os.environ', GEMINI_API_KEY='secret'):
            job = self.flow.start_gemini_review(self.batch)
            self.flow.save_draft(self.batch, '人工新稿。')
            gate.set()
            self.assertTrue(job.wait(3))
            review_id = self.flow.finish_gemini_review(job)
        with self.assertRaisesRegex(ProjectError, '版本已變更'):
            self.flow.decide_gemini(self.batch, review_id, None, 'accepted')
        self.assertEqual(self.flow.texts(self.batch)[1], '人工新稿。')
        self.assertTrue(ProjectWorkflow.open(self.flow.root).gemini_reviews(self.batch)[0]['stale'])

    def test_cancel_and_failure_preserve_manual_work(self):
        original = self.flow.texts(self.batch)[1]
        for cancel in (False, True):
            gate = threading.Event()
            def fail(*args):
                gate.wait(3)
                raise ProjectError('網路不可用')
            with patch('ebook2mp4.gemini.generate', side_effect=fail), patch.dict('os.environ', GEMINI_API_KEY='secret'):
                job = self.flow.start_gemini_review(self.batch)
                if cancel:
                    job.cancel()
                gate.set()
                self.assertTrue(job.wait(3))
                review_id = self.flow.finish_gemini_review(job)
            self.assertEqual(job.state['status'], 'cancelled' if cancel else 'failed')
            with self.assertRaises(ProjectError):
                self.flow.decide_gemini(self.batch, review_id, None, 'accepted')
        self.assertEqual(self.flow.texts(self.batch)[1], original)
        self.flow.save_draft(self.batch, '仍可人工校對。')
        self.assertEqual(ProjectWorkflow.open(self.flow.root).texts(self.batch)[1], '仍可人工校對。')

    def test_local_encrypted_settings_connection_and_outgoing_selection(self):
        from unittest.mock import MagicMock
        connection = MagicMock()
        response = connection.getresponse.return_value
        response.status = 200
        response.read.return_value = json.dumps(dict(candidates=[dict(finishReason='STOP',
            content=dict(parts=[dict(text=json.dumps(dict(paragraphs=['這是錯字。'], notes=[])))]))])).encode()
        with patch.dict('os.environ', LOCALAPPDATA=str(self.folder), GEMINI_API_KEY=''):
            self.flow.save_gemini_settings('local-secret-key', 'gemini-2.5-flash')
            self.assertEqual(self.flow.gemini_settings(), dict(key='local-secret-key', model='gemini-2.5-flash'))
            self.assertNotIn(b'local-secret-key', (self.folder / 'ebook2mp4/gemini.json').read_bytes())
            with patch('http.client.HTTPSConnection', return_value=connection):
                text = self.flow.texts(self.batch)[1]
                start = text.index('這')
                job = self.flow.start_gemini_review(self.batch, start=start, end=start+6)
                self.assertTrue(job.wait(3))
                self.flow.finish_gemini_review(job)
                body = json.loads(connection.request.call_args.kwargs['body'])
                outgoing = json.loads(body['contents'][0]['parts'][0]['text'])
                self.assertEqual(outgoing, dict(paragraphs=['這是錯宇。\n']))
                self.assertNotIn('外面保留', json.dumps(body, ensure_ascii=False))
                test = self.flow.test_gemini_connection()
                self.assertTrue(test.wait(3))
                self.assertEqual(test.state['status'], 'completed')
            self.flow.save_gemini_settings('', 'gemini-2.5-flash')
            with self.assertRaisesRegex(ProjectError, 'API Key'):
                self.flow.start_gemini_review(self.batch)
            self.flow.save_draft(self.batch, '離線人工校對')
