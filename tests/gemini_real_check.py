"""Opt-in live Gemini check using synthetic text, never user book content."""
from pathlib import Path
import json
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ebook2mp4.workflow import ProjectWorkflow, ProjectError

base = Path('.scratch/t07-temp').resolve()
base.mkdir(parents=True, exist_ok=True)
report = dict(service='Gemini', synthetic_only=True, checks=[])
with tempfile.TemporaryDirectory(dir=base) as temp:
    folder = Path(temp)
    source = folder / 'synthetic.txt'
    source.write_bytes('Outside unchanged.\n\n今天天氣很好。我們去公圜散步。\n\nKeep this tail.'.encode('utf-8'))
    flow = ProjectWorkflow.create(folder / 'book', 'Live synthetic check')
    batch = flow.import_txt(flow.inspect_txt(source))
    report['model'] = flow.gemini_settings()['model']
    for name in ('connection', 'selected-proofreading'):
        started = time.monotonic()
        try:
            original = flow.texts(batch)[1]
            start = original.index('今天')
            end = original.index('\n\nKeep')
            job = flow.test_gemini_connection() if name == 'connection' else flow.start_gemini_review(batch, start=start, end=end)
            if not job.wait(65):
                job.cancel()
                job.wait()
                raise ProjectError('連線逾時')
            result = dict(check=name, **job.state)
            if name == 'selected-proofreading':
                review_id = flow.finish_gemini_review(job)
                review = flow.gemini_reviews(batch)[0]
                if job.state['status'] == 'completed':
                    result['synthetic_original'] = review['paragraphs'][0]['original']
                    result['synthetic_candidate'] = review['paragraphs'][0]['candidate']
                    result['notes'] = review['notes']
                    flow.decide_gemini(batch, review_id, None, 'accepted')
                    updated = ProjectWorkflow.open(flow.root).texts(batch)[1]
                    assert updated.startswith(original[:start]) and updated.endswith(original[end:])
                    flow.undo_gemini(batch, review_id)
                    assert flow.texts(batch)[1] == original
                    result['outside_preserved_and_undo'] = True
        except ProjectError as e:
            result = dict(check=name, status='failed', error=str(e))
        result['seconds'] = round(time.monotonic()-started, 3)
        report['checks'].append(result)
Path('docs/verification/T07-real-gemini.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=True))
