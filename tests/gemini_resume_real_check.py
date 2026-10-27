"""Opt-in T08 live synthetic requests with one explicitly injected network failure."""
from pathlib import Path
import json
import sys
import tempfile
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ebook2mp4.workflow import ProjectWorkflow, ProjectError
from ebook2mp4.gemini import generate

base = Path('.scratch/t08/live').resolve()
base.mkdir(parents=True, exist_ok=True)
report = dict(synthetic_only=True, real_requests=0, injected_failures=0)
started = time.monotonic()
with tempfile.TemporaryDirectory(dir=base) as temp:
    folder = Path(temp)
    source = folder / 'synthetic.txt'
    text = '\n\n'.join((sentence + ' ') * 65 for sentence in (
        'The garden was quiet. We walked slowly beside the trees.',
        'The library was open. We read a story beside the window.',
        'The evening was calm. We watched the clouds above the river.'))
    source.write_bytes(text.encode('utf-8'))
    flow = ProjectWorkflow.create(folder / 'book', 'T08 live synthetic check')
    batch = flow.import_txt(flow.inspect_txt(source))
    report['model'] = flow.gemini_settings()['model']
    def service(key, model, paragraphs):
        if paragraphs[0].startswith('The library'):
            report['injected_failures'] += 1
            raise ProjectError('合成中段網路錯誤（驗證注入）')
        report['real_requests'] += 1
        return generate(key, model, paragraphs)
    with patch('ebook2mp4.gemini.generate', side_effect=service):
        job = flow.start_gemini_review(batch, script='preserve', punctuation=False)
        try:
            if not job.wait(120):
                raise ProjectError('驗證逾時')
            review_id = flow.finish_gemini_review(job)
        finally:
            job.cancel()
            job.wait()
    report['first_status'] = job.state['status']
    report['first_ranges'] = job.state['requests']
    reopened = ProjectWorkflow.open(flow.root)
    report['draft_unchanged'] = reopened.texts(batch)[1] == text
    if job.state['status'] == 'partial':
        retry = reopened.start_gemini_retry(batch, review_id, failed_only=True)
        try:
            if not retry.wait(120):
                raise ProjectError('重試驗證逾時')
            reopened.finish_gemini_review(retry)
        finally:
            retry.cancel()
            retry.wait()
        report['real_requests'] += sum(r['attempts'] == 2 for r in retry.state['requests'])
        report['retry_status'] = retry.state['status']
        report['final_attempts'] = [r['attempts'] for r in retry.state['requests']]
        if retry.state['status'] == 'completed':
            reopened.decide_gemini(batch, review_id, 1, 'accepted')
            report['adoption_reopened'] = ProjectWorkflow.open(reopened.root).gemini_reviews(batch)[0]['paragraphs'][1]['decision'] == 'accepted'
            reopened.undo_gemini(batch, review_id)
            report['undo_preserved_source'] = reopened.texts(batch)[1] == text
report['seconds'] = round(time.monotonic()-started, 3)
Path('docs/verification/T08-real-gemini.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=True))
