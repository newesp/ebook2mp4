"""Normalization through the agreed workflow; only Gemini responses are controlled."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ebook2mp4.workflow import ProjectWorkflow


class ProofreadingOptimization(unittest.TestCase):
    def setUp(self):
        base = Path('.scratch/test-runs')
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.flow = ProjectWorkflow.create(self.root / 'book', '中文校對')

    def imported(self, text):
        source = self.root / 'source.txt'
        source.write_bytes(text.encode('utf-8'))
        return self.flow.import_txt(self.flow.inspect_txt(source))

    def review(self, batch, start=0, end=None, **options):
        text = self.flow.texts(batch)[1]
        end = len(text) if end is None else end
        with patch('ebook2mp4.gemini.generate', return_value=dict(paragraphs=[text[start:end]], notes=[])), patch.dict('os.environ', GEMINI_API_KEY='fake'):
            job = self.flow.start_gemini_review(batch, start=start, end=end, **options)
            self.assertTrue(job.wait(5))
            review_id = self.flow.finish_gemini_review(job)
        return review_id

    def test_full_batch_script_guides_selected_candidate_without_changing_outside(self):
        prefix = '這份書稿使用繁體中文，讀者應該確認轉錄內容與標點。' * 4 + '\n\n'
        selected = '这里有头发,请检查(文字). Visit https://example.com/a?q=3.14 and U.S.A.'
        original = prefix + selected + '\n\n結尾保留。'
        batch = self.imported(original)
        scope = self.flow.gemini_scope(batch, start=len(prefix), end=len(prefix)+len(selected))
        self.assertEqual(scope['normalization']['target'], 'traditional')
        review_id = self.review(batch, len(prefix), len(prefix)+len(selected))
        candidate = self.flow.gemini_reviews(batch)[0]['paragraphs'][0]['candidate']
        self.assertEqual(candidate, '這裏有頭髮，請檢查（文字）。 Visit https://example.com/a?q=3.14 and U.S.A.')
        self.assertEqual(self.flow.texts(batch)[1], original)
        self.flow.decide_gemini(batch, review_id, None, 'accepted')
        self.assertEqual(self.flow.texts(batch)[1], prefix+candidate+'\n\n結尾保留。')
        reopened = ProjectWorkflow.open(self.flow.root)
        reopened.undo_gemini(batch, review_id)
        self.assertEqual(reopened.texts(batch)[1], original)

    def test_simplified_and_ambiguous_detection_and_explicit_preserve(self):
        text = '这份书稿使用简体中文，请读者检查转录内容和标点。' * 4 + '\n\n這裏有頭髮,請檢查.'
        batch = self.imported(text)
        start = text.index('這裏')
        self.assertEqual(self.flow.gemini_scope(batch)['normalization']['target'], 'simplified')
        review_id = self.review(batch, start)
        self.flow.decide_gemini(batch, review_id, None, 'accepted')
        self.assertTrue(self.flow.texts(batch)[1].endswith('这里有头发，请检查。'))
        short = self.imported('中文文字,不能猜测.')
        self.assertEqual(self.flow.gemini_scope(short)['normalization']['target'], 'preserve')
        self.review(short, script='preserve', punctuation=False)
        self.assertEqual(self.flow.gemini_reviews(short)[0]['paragraphs'][0]['candidate'], '中文文字,不能猜测.')

    def test_english_numbers_code_and_identifiers_are_preserved(self):
        text = '中文说:"你好,世界!" (English, text!)\nEnglish, text!\n小数3.14,版本v1.2,邮箱a.b@example.com。`简体,代码()`'
        batch = self.imported(text)
        self.review(batch, script='traditional')
        candidate = self.flow.gemini_reviews(batch)[0]['paragraphs'][0]['candidate']
        self.assertEqual(candidate, '中文說：「你好，世界！」 (English, text!)\nEnglish, text!\n小數3.14，版本v1.2，郵箱a.b@example.com。`简体,代码()`')

    def test_quotes_with_url_and_code_keep_protected_content_unchanged(self):
        text = '他说:"请访问 https://example.com/a?q=1.2,foo, 或输入 `简体,代码()`!"'
        batch = self.imported(text)
        self.review(batch, script='traditional')
        self.assertEqual(self.flow.gemini_reviews(batch)[0]['paragraphs'][0]['candidate'],
                         '他說：「請訪問 https://example.com/a?q=1.2,foo, 或輸入 `简体,代码()`！」')
