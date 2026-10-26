"""Opt-in synthetic cloud check plus local supplied-book title evidence."""
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ebook2mp4.workflow import ProjectWorkflow

base = Path('.scratch/optimization-temp').resolve()
base.mkdir(parents=True, exist_ok=True)
report = dict(date='2026-10-26', cloud_input='synthetic selected text only', checks=[])
with tempfile.TemporaryDirectory(dir=base) as temp:
    folder = Path(temp)
    for target, prefix, selected, expected in (
        ('traditional', '這份書稿使用繁體中文，讀者應該確認轉錄內容與標點。'*4,
         '这里有头发,请检查(文字). Visit https://example.com/a?q=3.14 and U.S.A.', '頭髮'),
        ('simplified', '这份书稿使用简体中文，请读者检查转录内容和标点。'*4,
         '這裏有頭髮,請檢查(文字). Visit https://example.com/a?q=3.14 and U.S.A.', '头发')):
        source = folder/(target+'.txt')
        original = prefix+'\n\n'+selected+'\n\nOutside unchanged.'
        source.write_bytes(original.encode('utf-8'))
        flow = ProjectWorkflow.create(folder/target, target)
        batch = flow.import_txt(flow.inspect_txt(source))
        start = len(prefix)+2
        started = time.monotonic()
        job = flow.start_gemini_review(batch,start=start,end=start+len(selected))
        if not job.wait(70):
            job.cancel()
            job.wait()
        review_id = flow.finish_gemini_review(job)
        result = dict(check='live-'+target, **job.state, seconds=round(time.monotonic()-started,3))
        if job.state['status'] == 'completed':
            review = flow.gemini_reviews(batch)[0]
            candidate = review['paragraphs'][0]['candidate']
            assert review['normalization']['target'] == target
            assert expected in candidate and '，' in candidate and '（' in candidate
            assert 'https://example.com/a?q=3.14' in candidate and 'U.S.A.' in candidate
            assert flow.texts(batch)[1] == original
            flow.decide_gemini(batch,review_id,None,'accepted')
            assert flow.texts(batch)[1] == original[:start]+candidate+original[start+len(selected):]
            flow.undo_gemini(batch,review_id)
            assert flow.texts(batch)[1] == original
            result.update(policy=review['normalization'], synthetic_candidate=candidate, outside_and_undo=True)
        report['checks'].append(result)
    if os.environ.get('EBOOK2MP4_BOOK_PDF'):
        flow = ProjectWorkflow.create(folder/'ocr', 'Local OCR')
        preview = flow.inspect_pdf(os.environ['EBOOK2MP4_BOOK_PDF'])
        for language,layout in [('繁中＋英文','block'),('自動中英','auto')]:
            job = flow.start_pdf_extraction(preview,1,1,mode='ocr',language=language,layout=layout)
            job.wait()
            page = flow.pdf_extraction_pages(job)[0]
            title = next((line for line in page['text'].splitlines() if re.match(r'^1\s*[.、]',line)), '')
            report['checks'].append(dict(check='local-book-title',language=language,layout=layout,
                                          title=title,status=page['status'],settings=page['settings']))
            flow.discard_pdf_extraction(job)
Path('docs/verification/optimization-real.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
if any(c.get('status') != 'completed' for c in report['checks'] if c['check'].startswith('live-')):
    raise SystemExit(1)
