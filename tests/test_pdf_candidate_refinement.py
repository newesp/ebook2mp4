"""Consecutive candidate corrections through ProjectWorkflow and real PDFium pages."""
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from ebook2mp4.workflow import ProjectError, ProjectWorkflow
from test_pdf import pdf_bytes


class PdfCandidateRefinement(unittest.TestCase):
    def setUp(self):
        base = Path('.scratch/test-runs')
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='candidate-refinement-', dir=base)
        self.addCleanup(self.temp.cleanup)
        folder = Path(self.temp.name)
        source = folder / 'book.pdf'
        source.write_bytes(pdf_bytes(2))
        self.flow = ProjectWorkflow.create(folder / 'project', 'Refinement')
        self.preview = self.flow.inspect_pdf(source)
        job = self.wait(self.flow.start_pdf_extraction(self.preview, 1, 2))
        self.batch = self.flow.finish_pdf_extraction(job)
        self.original = self.flow.pdf_pages(self.batch)
        available = patch('ebook2mp4.ocr.model_info', return_value=dict(ready=True, codes='eng', engine_error=''))
        available.start()
        self.addCleanup(available.stop)

    def wait(self, job):
        self.addCleanup(lambda: (job.cancel(), job.wait()))
        self.assertTrue(job.wait(10))
        return job

    def recognize(self, text):
        return patch('ebook2mp4.ocr.recognize_page', return_value=dict(text=text, confidence=95))

    def first_correction(self):
        with self.recognize('First corrected title'):
            return self.wait(self.flow.start_pdf_retry(self.batch, pages=[1], language='英文',
                             region=(0., 0., .5, .5), text_range=(0, 7)))

    def test_two_regions_accumulate_with_shifted_offsets_and_publish_once(self):
        self.flow.save_draft(self.batch, 'Existing manually corrected manuscript.')
        snapshot = self.flow.confirm_reading(self.batch)
        before = self.flow.state
        first = self.first_correction()
        text = self.flow.pdf_extraction_pages(first)[0]['text']
        begin = text.index('Hello')
        with self.recognize('Second body correction'):
            second = self.wait(self.flow.start_pdf_candidate_retry(first, pages=[1], accepted_pages=[1],
                               language='英文', region=(.5, .5, 1., 1.), text_range=(begin, begin + 5)))
        pages = self.flow.pdf_extraction_pages(second)
        self.assertIn('First corrected title', pages[0]['text'])
        self.assertIn('Second body correction', pages[0]['text'])
        self.assertEqual(pages[1], self.original[1])
        self.assertEqual(self.flow.state, before, 'Refining must not publish intermediate batches')
        new = self.flow.finish_pdf_extraction(second)
        reopened = ProjectWorkflow.open(self.flow.root)
        self.assertEqual(len(reopened.state['batches']), 2)
        self.assertEqual(reopened.pdf_pages(new), pages)
        self.assertEqual(reopened.pdf_pages(self.batch), self.original)
        self.assertEqual(reopened.reading_text(self.batch, snapshot['id']), 'Existing manually corrected manuscript.')
        self.assertEqual(reopened.reading_text(self.batch), 'Existing manually corrected manuscript.')

    def test_accumulated_page_selection_uses_original_publication_baseline(self):
        first = self.first_correction()
        with self.recognize('Replacement text for a different page.'):
            second = self.wait(self.flow.start_pdf_candidate_retry(first, pages=[2], accepted_pages=[1], language='英文'))
        self.assertEqual(second.numbers, (2,))
        self.assertEqual(second.candidate_numbers, (1, 2))
        new = self.flow.finish_pdf_extraction(second, accepted_pages=[1])
        result = self.flow.pdf_pages(new)
        self.assertIn('First corrected title', result[0]['text'])
        self.assertEqual(result[1], self.original[1])

    def test_unchecked_previous_page_is_frozen_back_to_original_before_next_region(self):
        first = self.first_correction()
        with self.recognize('Restarted'):
            second = self.wait(self.flow.start_pdf_candidate_retry(first, pages=[1], accepted_pages=[],
                               language='英文', region=(0., 0., .5, .5), text_range=(0, 7)))
        candidate = self.flow.pdf_extraction_pages(second)[0]['text']
        self.assertEqual(candidate, 'Restarted' + self.original[0]['text'][7:])
        new = self.flow.finish_pdf_extraction(second, accepted_pages=[])
        self.assertEqual(self.flow.pdf_pages(new), self.original)

    def test_cancelled_and_failed_refinements_keep_already_corrected_text(self):
        first = self.first_correction()
        corrected = self.flow.pdf_extraction_pages(first)[0]['text']
        with patch('ebook2mp4.ocr.recognize_page', side_effect=ProjectError('Controlled recognition failure')):
            failed = self.wait(self.flow.start_pdf_candidate_retry(first, pages=[1], language='英文'))
        self.assertEqual(self.flow.pdf_extraction_pages(failed)[0]['text'], corrected)
        self.assertEqual(self.flow.pdf_extraction_pages(failed)[0]['status'], 'failed')
        from ebook2mp4.ocr import OcrCancelled
        entered, release = threading.Event(), threading.Event()
        def cancelled(*args, **kwargs):
            entered.set()
            release.wait(10)
            raise OcrCancelled()
        with patch('ebook2mp4.ocr.recognize_page', side_effect=cancelled):
            job = self.flow.start_pdf_candidate_retry(failed, pages=[1], language='英文')
            self.addCleanup(lambda: (job.cancel(), release.set(), job.wait()))
            self.assertTrue(entered.wait(10))
            with self.assertRaises(ProjectError):
                self.flow.start_pdf_candidate_retry(job, pages=[1], language='英文')
            job.cancel()
            release.set()
            self.assertTrue(job.wait(10))
        self.assertEqual(self.flow.pdf_extraction_pages(job)[0]['text'], corrected)
        self.assertEqual(self.flow.pdf_extraction_pages(job)[0]['status'], 'cancelled')
        new = self.flow.finish_pdf_extraction(job)
        self.assertEqual(self.flow.pdf_pages(new)[0]['text'], corrected)
        self.assertTrue(self.flow.confirmation_blockers(new))

    def test_reject_latest_region_then_publish_preserves_earlier_regions(self):
        first = self.first_correction()
        text = self.flow.pdf_extraction_pages(first)[0]['text']
        begin = text.index('Hello')
        with self.recognize('Second accepted body'):
            second = self.wait(self.flow.start_pdf_candidate_retry(first, pages=[1], language='英文',
                               region=(0., 0., .5, .5), text_range=(begin, begin+5)))
        before_bad = self.flow.pdf_extraction_pages(second)
        begin = before_bad[0]['text'].index('3.14')
        with self.recognize('INCORRECT THIRD'):
            third = self.wait(self.flow.start_pdf_candidate_retry(second, pages=[1], language='英文',
                              region=(0., 0., .5, .5), text_range=(begin, begin+4)))
        new = self.flow.finish_pdf_extraction(third, accepted_pages=[])
        reopened = ProjectWorkflow.open(self.flow.root)
        self.assertEqual(reopened.pdf_pages(new), before_bad)
        self.assertEqual(reopened.pdf_pages(self.batch), self.original)
        self.assertEqual(len(reopened.state['batches']), 2)

    def test_reject_overlapping_retry_restores_previous_accepted_correction(self):
        first = self.first_correction()
        accepted = self.flow.pdf_extraction_pages(first)
        with self.recognize('BAD OVERLAPPING RETRY'):
            second = self.wait(self.flow.start_pdf_candidate_retry(first, pages=[1], language='英文',
                               region=(0., 0., .5, .5), text_range=(0, len('First corrected title'))))
        new = self.flow.finish_pdf_extraction(second, accepted_pages=[])
        self.assertEqual(self.flow.pdf_pages(new), accepted)

    def test_reject_region_on_another_page_keeps_previously_accepted_page(self):
        first = self.first_correction()
        accepted = self.flow.pdf_extraction_pages(first)
        with self.recognize('BAD SECOND PAGE'):
            second = self.wait(self.flow.start_pdf_candidate_retry(first, pages=[2], language='英文',
                               region=(0., 0., .5, .5), text_range=(0, 7)))
        new = self.flow.finish_pdf_extraction(second, accepted_pages=[1])
        self.assertEqual(self.flow.pdf_pages(new), accepted)

    def test_reject_region_then_retry_another_whole_page_keeps_prior_region(self):
        with self.recognize('Accepted page two correction'):
            first = self.wait(self.flow.start_pdf_retry(self.batch, pages=[2], language='英文',
                             region=(0., 0., .5, .5), text_range=(0, 7)))
        accepted_page = self.flow.pdf_extraction_pages(first)[1]
        with self.recognize('WRONG RETRY'):
            second = self.wait(self.flow.start_pdf_candidate_retry(first, pages=[2], language='英文',
                               region=(0., 0., .5, .5), text_range=(0, 5)))
        with self.recognize('Whole page one correction'):
            third = self.wait(self.flow.start_pdf_candidate_retry(second, pages=[1], accepted_pages=[], language='英文'))
        new = self.flow.finish_pdf_extraction(third)
        self.assertEqual(self.flow.pdf_pages(new)[1], accepted_page)

    def test_reject_latest_region_keeps_prior_correction_pending_for_page_review(self):
        with self.recognize('Short'):
            sparse = self.wait(self.flow.start_pdf_retry(self.batch, pages=[1], language='英文'))
        source = self.flow.finish_pdf_extraction(sparse)
        issue = next(i for i, item in enumerate(self.flow.state['batches'][-1]['source_issues']) if item.get('page') == 1)
        self.flow.resolve_source_issue(source, issue, 'resolved')
        with self.recognize('Previously accepted local correction'):
            first = self.wait(self.flow.start_pdf_retry(source, pages=[1], language='英文',
                             region=(0., 0., .5, .5), text_range=(0, 5)))
        with self.recognize('Wrong retry'):
            second = self.wait(self.flow.start_pdf_candidate_retry(first, pages=[1], language='英文',
                               region=(0., 0., .5, .5), text_range=(0, 5)))
        new = self.flow.finish_pdf_extraction(second, accepted_pages=[])
        self.assertEqual(self.flow.pdf_pages(new)[0]['text'], 'Previously accepted local correction')
        self.assertTrue(self.flow.confirmation_blockers(new))

    def test_construction_and_publication_failure_keep_current_owner_and_work(self):
        first = self.first_correction()
        previous = self.flow.pdf_extraction_pages(first)
        exposed = self.flow.pdf_extraction_pages(first)
        exposed[1]['text'] = 'A view must not mutate the working baseline.'
        self.assertEqual(self.flow.pdf_extraction_pages(first), previous)
        for pages, accepted in (([], [1]), ([True], [1]), ([2, 1], [1]), ([3], [1]),
                                ([1], [True]), ([1], [2])):
            with self.assertRaises(ProjectError):
                self.flow.start_pdf_candidate_retry(first, pages=pages, accepted_pages=accepted, language='英文')
            self.assertEqual(self.flow.pdf_extraction_pages(first), previous)
        with patch('ebook2mp4.ocr.model_info', return_value=dict(ready=False, engine_error='Missing model')):
            with self.assertRaisesRegex(ProjectError, 'Missing model'):
                self.flow.start_pdf_candidate_retry(first, pages=[1], language='英文')
        self.assertEqual(self.flow.pdf_extraction_pages(first), previous)
        with self.recognize('Next'):
            second = self.wait(self.flow.start_pdf_candidate_retry(first, pages=[1], language='英文',
                               region=(0., 0., .5, .5), text_range=(0, 5)))
        current = self.flow.pdf_extraction_pages(second)
        with patch('ebook2mp4.workflow.os.replace', side_effect=OSError('disk full')):
            with self.assertRaises(ProjectError):
                self.flow.finish_pdf_extraction(second)
        self.assertEqual(self.flow.pdf_extraction_pages(second), current)
        self.assertEqual(len(ProjectWorkflow.open(self.flow.root).state['batches']), 1)
        self.flow.finish_pdf_extraction(second)

    def test_foreign_retired_and_removed_source_jobs_are_rejected(self):
        first = self.first_correction()
        foreign = ProjectWorkflow.open(self.flow.root)
        with self.assertRaises(ProjectError):
            foreign.start_pdf_candidate_retry(first, pages=[1], language='英文')
        with self.recognize('Next'):
            second = self.wait(self.flow.start_pdf_candidate_retry(first, pages=[1], language='英文'))
        for operation in (self.flow.finish_pdf_extraction, self.flow.discard_pdf_extraction):
            with self.assertRaises(ProjectError):
                operation(first)
        self.flow.remove_pdf_batch(self.batch)
        for operation in (lambda: self.flow.start_pdf_candidate_retry(second, pages=[1], language='英文'),
                          lambda: self.flow.finish_pdf_extraction(second)):
            with self.assertRaises(ProjectError):
                operation()
        self.assertTrue(self.flow.pdf_extraction_pages(second))
        self.flow.discard_pdf_extraction(second)

    def test_manual_draft_saved_during_refinement_is_preserved_without_invalidating_candidate(self):
        snapshot = self.flow.confirm_reading(self.batch)
        snapshot_text = self.flow.reading_text(self.batch, snapshot['id'])
        first = self.first_correction()
        self.flow.save_draft(self.batch, 'Manual work saved after candidate creation.')
        with self.recognize('Another correction'):
            second = self.wait(self.flow.start_pdf_candidate_retry(first, pages=[1], language='英文',
                               region=(0., 0., .5, .5), text_range=(0, 5)))
        self.flow.save_draft(self.batch, 'Manual work saved before final publication.')
        new = self.flow.finish_pdf_extraction(second)
        self.assertIn('Another correction', self.flow.texts(new)[1])
        self.assertEqual(self.flow.texts(self.batch)[1], 'Manual work saved before final publication.')
        self.assertEqual(self.flow.reading_text(self.batch, snapshot['id']), snapshot_text)

    def test_changed_source_or_extracted_content_is_rejected_without_losing_candidate(self):
        first = self.first_correction()
        current = self.flow.pdf_extraction_pages(first)
        batch = self.flow.state['batches'][0]
        for reference in (batch['source'], batch['pdf']['extracted']):
            path = self.flow.root / reference['path']
            data = path.read_bytes()
            try:
                path.write_bytes(data + b'changed baseline')
                with self.assertRaises(ProjectError):
                    self.flow.start_pdf_candidate_retry(first, pages=[1], language='英文')
                with self.assertRaises(ProjectError):
                    self.flow.finish_pdf_extraction(first)
                self.assertEqual(self.flow.pdf_extraction_pages(first), current)
            finally:
                path.write_bytes(data)
        self.flow.discard_pdf_extraction(first)

    def test_rename_reorder_and_reading_snapshot_do_not_invalidate_source(self):
        first = self.first_correction()
        self.flow.rename_batch(self.batch, 'Renamed source')
        self.flow.reorder_batches([self.batch])
        snapshot = self.flow.confirm_reading(self.batch)
        with self.recognize('Next correction'):
            second = self.wait(self.flow.start_pdf_candidate_retry(first, pages=[1], language='英文',
                               region=(0., 0., .5, .5), text_range=(0, 5)))
        self.assertIn('Next correction', self.flow.pdf_extraction_pages(second)[0]['text'])
        self.flow.finish_pdf_extraction(second)
        self.assertEqual(self.flow.reading_text(self.batch, snapshot['id']), self.flow.texts(self.batch)[1])

    def test_initial_import_candidate_can_refine_before_any_batch_exists(self):
        flow = ProjectWorkflow.create(Path(self.temp.name) / 'initial', 'Initial import')
        first = self.wait(flow.start_pdf_extraction(self.preview, 1, 2))
        original = flow.pdf_extraction_pages(first)
        with self.recognize('Corrected'):
            second = self.wait(flow.start_pdf_candidate_retry(first, pages=[1], language='英文',
                               region=(0., 0., .5, .5), text_range=(0, 7)))
        self.assertEqual(flow.state['batches'], [])
        new = flow.finish_pdf_extraction(second)
        self.assertEqual(len(flow.state['batches']), 1)
        self.assertIsNone(flow.state['batches'][0]['pdf']['source_batch'])
        self.assertEqual(flow.pdf_pages(new)[0]['text'], 'Corrected' + original[0]['text'][7:])
        self.assertEqual(flow.pdf_pages(new)[1], original[1])


if __name__ == '__main__':
    unittest.main()
