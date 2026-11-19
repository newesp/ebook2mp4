"""Natural request boundaries survive mismatched manuscript quotation marks."""
import unittest

from ebook2mp4.narration import plan, request_size
from ebook2mp4.voice import DEFAULT_SETTINGS
from ebook2mp4.workflow import ProjectError


class QuoteSplitting(unittest.TestCase):
    def test_dialogue_and_long_quotes_preserve_text_and_request_limit(self):
        for opening, closing in [('“好？"\n', ''), ('“', '”'), ('「', '」'), ('“好。“\n', '')]:
            for pause in (0, 250):
                with self.subTest(opening=opening, pause=pause):
                    text = opening + '這是完整句子。' * 200 + closing
                    result = plan(text, dict(DEFAULT_SETTINGS, sentence_pause_ms=pause), 'r', 'b')
                    chunks = result['chunks']
                    self.assertEqual(''.join(c['text'] + c['separator_after'] for c in chunks), text)
                    self.assertGreater(len(chunks), 1)
                    self.assertTrue(all(request_size(c['text']) <= 3000 for c in chunks))
                    self.assertTrue(all(c['text'].rstrip().rstrip('\"”」').endswith(('。', '？')) for c in chunks[:-1]))

    def test_indivisible_spans_remain_rejected(self):
        for text in ['「' + '字' * 1100 + '」', '“https://example.com/' + 'a' * 3100 + '”',
                     '“（' + '完整句子。' * 300 + '）”']:
            with self.subTest(prefix=text[:20]):
                with self.assertRaisesRegex(ProjectError, '安全切分'):
                    plan(text, DEFAULT_SETTINGS, 'r', 'b')
