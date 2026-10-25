"""PDF behavior at the agreed ProjectWorkflow boundary, using real PDFium."""
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
import time
from unittest.mock import patch

from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from ebook2mp4.workflow import ProjectWorkflow, ProjectError


def pdf_bytes(pages=20):
    output = BytesIO()
    doc = canvas.Canvas(output)
    for page in range(1, pages + 1):
        doc.drawString(40, 780, f'Chapter {page}: Hello 3.14 U.S.A. - original text.')
        doc.showPage()
    doc.save()
    return output.getvalue()


class PdfJourney(unittest.TestCase):
    def setUp(self):
        base = Path('.scratch/test-runs')
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pdf = self.root / 'book.pdf'
        self.pdf.write_bytes(pdf_bytes())
        self.flow = ProjectWorkflow.create(self.root / 'project', 'Book')

    def test_remove_selected_pdf_preserves_other_batches_and_source(self):
        original = self.pdf.read_bytes()
        preview = self.flow.inspect_pdf(self.pdf)
        ids = []
        for _ in range(2):
            job = self.flow.start_pdf_extraction(preview, 1, 1)
            job.wait()
            ids.append(self.flow.finish_pdf_extraction(job))
        self.flow.save_draft(ids[1], 'Other corrected batch')
        self.flow.confirm_reading(ids[1])
        txt = self.root / 'chapter.txt'
        txt.write_text('TXT retained', encoding='utf-8')
        txt_id = self.flow.import_txt(self.flow.inspect_txt(txt))
        with self.assertRaises(ProjectError):
            self.flow.remove_pdf_batch(txt_id)
        stale = ProjectWorkflow.open(self.flow.root)
        self.flow.remove_pdf_batch(ids[0])
        reopened = ProjectWorkflow.open(self.flow.root)
        self.assertEqual([b['id'] for b in reopened.state['batches']], [ids[1], txt_id])
        self.assertEqual(reopened.reading_text(ids[1]), 'Other corrected batch')
        self.assertEqual(reopened.texts(txt_id)[1], 'TXT retained')
        self.assertEqual(self.pdf.read_bytes(), original)
        with self.assertRaises(ProjectError):
            reopened.texts(ids[0])
        with self.assertRaisesRegex(ProjectError, '另一個視窗'):
            stale.remove_pdf_batch(ids[1])
        reopened.remove_pdf_batch(ids[1])
        self.assertEqual([b['id'] for b in ProjectWorkflow.open(self.flow.root).state['batches']], [txt_id])

    def test_failed_pdf_removal_retains_previous_project(self):
        job = self.flow.start_pdf_extraction(self.flow.inspect_pdf(self.pdf), 1, 1)
        job.wait()
        batch = self.flow.finish_pdf_extraction(job)
        before = self.flow.state
        with patch('ebook2mp4.workflow.os.replace', side_effect=OSError('disk full')):
            with self.assertRaises(ProjectError):
                self.flow.remove_pdf_batch(batch)
        self.assertEqual(self.flow.state, before)
        self.assertEqual(ProjectWorkflow.open(self.flow.root).state, before)
        self.flow.remove_pdf_batch(batch)
        self.assertEqual(ProjectWorkflow.open(self.flow.root).state['batches'], [])

    def test_selected_pages_are_independent_persistent_batches_with_txt(self):
        preview = self.flow.inspect_pdf(self.pdf)
        self.assertEqual(preview.page_count, 20)
        image = self.flow.preview_pdf_page(preview, 3)
        self.assertTrue(image.startswith(b'\x89PNG'))
        job = self.flow.start_pdf_extraction(preview, 3, 5)
        job.wait()
        batch = self.flow.finish_pdf_extraction(job)
        pages = self.flow.pdf_pages(batch)
        self.assertEqual([p['number'] for p in pages], [3, 4, 5])
        self.assertTrue(all(p['method'] == 'text-layer' and p['status'] == 'success' for p in pages))
        original, draft = self.flow.texts(batch)
        self.assertIn('Chapter 3:', original)
        self.assertNotIn('Chapter 2:', original)
        self.assertNotIn('Chapter 6:', original)
        self.assertEqual(original, draft)
        self.flow.save_draft(batch, 'Corrected manuscript')
        second_job = self.flow.start_pdf_extraction(preview, 6, 7)
        second_job.wait()
        second = self.flow.finish_pdf_extraction(second_job)
        txt = self.root / 'part.txt'
        txt.write_text('TXT content', encoding='utf-8')
        third = self.flow.import_txt(self.flow.inspect_txt(txt))
        reopened = ProjectWorkflow.open(self.flow.root)
        self.assertEqual(reopened.texts(batch)[1], 'Corrected manuscript')
        self.assertIn('Chapter 6:', reopened.texts(second)[1])
        self.assertEqual(reopened.texts(third)[1], 'TXT content')
        self.assertEqual(len({b['draft']['path'] for b in reopened.state['batches']}), 3)
        self.assertEqual(reopened.pdf_pages(batch), pages)

    def test_line_break_cleanup_preview_never_rewrites_original_and_can_be_undone(self):
        original = 'Header\nHello  world 3.14 U.S.A.\nnext-line-\nword.\n\n新段落。\n頁尾 12'
        candidate = self.flow.preview_line_breaks(original)
        self.assertEqual(candidate, 'Header Hello  world 3.14 U.S.A. next-line- word.\n\n新段落。 頁尾 12')
        self.assertEqual(self.flow.preview_line_breaks(original, mode='original'), original)
        self.assertEqual(self.flow.preview_line_breaks('one\n \nnext\nline\n\n\nlast'), 'one\n \nnext line\n\n\nlast')

    def test_invalid_ranges_and_unreadable_corrupt_password_sources_do_not_start(self):
        preview = self.flow.inspect_pdf(self.pdf)
        for start, end in [(0, 5), (3, 21), (5, 3), (1.5, 3), ('3', 5), (True, 5)]:
            with self.subTest(start=start, end=end), self.assertRaises(ProjectError):
                self.flow.start_pdf_extraction(preview, start, end)
        self.assertEqual(self.flow.state['batches'], [])
        self.pdf.write_bytes(b'%PDF-1.7\nbroken')
        with self.assertRaisesRegex(ProjectError, '損毀|格式'):
            self.flow.inspect_pdf(self.pdf)
        with self.assertRaisesRegex(ProjectError, '不可讀'):
            self.flow.inspect_pdf(self.root / 'missing.pdf')
        protected = BytesIO()
        doc = canvas.Canvas(protected, encrypt='secret')
        doc.drawString(40, 780, 'Private')
        doc.save()
        self.pdf.write_bytes(protected.getvalue())
        with self.assertRaisesRegex(ProjectError, '密碼'):
            self.flow.inspect_pdf(self.pdf)

    def test_blank_and_failed_pages_block_confirmation_until_explicit_resolution(self):
        import pypdfium2
        output = BytesIO()
        doc = canvas.Canvas(output)
        doc.drawString(40, 780, 'This is a complete paragraph with enough original content.')
        doc.showPage()
        doc.showPage()
        doc.drawString(40, 780, '3')
        doc.showPage()
        doc.save()
        self.pdf.write_bytes(output.getvalue())
        preview = self.flow.inspect_pdf(self.pdf)
        job = self.flow.start_pdf_extraction(preview, 1, 3)
        job.wait()
        batch = self.flow.finish_pdf_extraction(job)
        self.assertEqual([p['status'] for p in self.flow.pdf_pages(batch)], ['success', 'pending', 'pending'])
        self.assertEqual(len(self.flow.confirmation_blockers(batch)), 2)
        with self.assertRaises(ProjectError):
            self.flow.confirm_reading(batch)
        self.flow.resolve_source_issue(batch, 0, 'skipped')
        self.flow.resolve_source_issue(batch, 1, 'resolved')
        self.flow.confirm_reading(batch)
        self.assertEqual(ProjectWorkflow.open(self.flow.root).reading_text(batch), self.flow.texts(batch)[1])
        with patch.object(pypdfium2.PdfPage, 'get_textpage', side_effect=RuntimeError('native failure')):
            failed = self.flow.start_pdf_extraction(preview, 1, 1)
            failed.wait()
        failed_batch = self.flow.finish_pdf_extraction(failed)
        self.assertEqual(self.flow.pdf_pages(failed_batch)[0]['status'], 'failed')
        self.assertTrue(self.flow.confirmation_blockers(failed_batch))

    def test_cancellation_keeps_complete_pages_and_leaves_corrected_batch_intact(self):
        self.pdf.write_bytes(pdf_bytes(250))
        preview = self.flow.inspect_pdf(self.pdf)
        job = self.flow.start_pdf_extraction(preview, 1, 1)
        job.wait()
        first = self.flow.finish_pdf_extraction(job)
        self.flow.save_draft(first, 'Already corrected')
        confirmation = self.flow.confirm_reading(first)
        job = self.flow.start_pdf_extraction(preview, 1, 250)
        deadline = time.monotonic() + 5
        while not job.pages and time.monotonic() < deadline:
            time.sleep(.002)
        job.cancel()
        self.assertTrue(job.wait(10))
        batch = self.flow.finish_pdf_extraction(job)
        reopened = ProjectWorkflow.open(self.flow.root)
        pages = reopened.pdf_pages(batch)
        self.assertEqual(len(pages), 250)
        self.assertEqual(pages[0]['status'], 'success')
        self.assertEqual(pages[-1]['status'], 'cancelled')
        self.assertEqual(reopened.reading_text(first, confirmation['id']), 'Already corrected')
        self.assertEqual(reopened.reading_text(first), 'Already corrected')
        self.assertTrue(reopened.confirmation_blockers(batch))

    def test_mapping_invalidates_on_edit_reload_and_original_export_has_no_labels(self):
        preview = self.flow.inspect_pdf(self.pdf)
        job = self.flow.start_pdf_extraction(preview, 3, 5)
        job.wait()
        batch = self.flow.finish_pdf_extraction(job)
        self.assertTrue(self.flow.state['batches'][0]['pdf']['mapping_valid'])
        original, _ = self.flow.texts(batch)
        self.flow.invalidate_reading(batch)
        self.assertFalse(ProjectWorkflow.open(self.flow.root).state['batches'][0]['pdf']['mapping_valid'])
        self.flow.save_draft(batch, 'New text')
        self.assertEqual(self.flow.texts(batch)[0], original)
        external = self.root / 'external.txt'
        external.write_text('External manuscript', encoding='utf-8')
        self.flow.reload_draft(batch, self.flow.inspect_txt(external))
        export = self.root / 'reading.txt'
        self.flow.export_txt(batch, export)
        self.assertEqual(export.read_text(encoding='utf-8'), 'External manuscript')
        self.assertFalse(self.flow.state['batches'][0]['pdf']['mapping_valid'])

    def test_real_multilingual_text_layer_preserves_script_numbers_and_punctuation(self):
        output = BytesIO()
        doc = canvas.Canvas(output)
        pdfmetrics.registerFont(UnicodeCIDFont('MSung-Light'))
        doc.setFont('MSung-Light', 12)
        expected = '繁體中文與简体中文保留原文，English 3.14 U.S.A. punctuation!'
        doc.drawString(40, 780, expected)
        doc.showPage()
        doc.save()
        self.pdf.write_bytes(output.getvalue())
        preview = self.flow.inspect_pdf(self.pdf)
        job = self.flow.start_pdf_extraction(preview, 1, 1)
        job.wait()
        batch = self.flow.finish_pdf_extraction(job)
        self.assertEqual(self.flow.texts(batch), (expected, expected))

    def test_commit_failure_retains_candidate_and_previous_confirmed_content(self):
        preview = self.flow.inspect_pdf(self.pdf)
        job = self.flow.start_pdf_extraction(preview, 3, 5)
        job.wait()
        with patch('ebook2mp4.workflow.os.replace', side_effect=OSError('disk full')):
            with self.assertRaises(ProjectError):
                self.flow.finish_pdf_extraction(job)
        self.assertEqual(ProjectWorkflow.open(self.flow.root).state['batches'], [])
        batch = self.flow.finish_pdf_extraction(job)
        self.assertEqual([p['number'] for p in self.flow.pdf_pages(batch)], [3, 4, 5])
        with self.assertRaises(ProjectError):
            self.flow.finish_pdf_extraction(job)


if __name__ == '__main__':
    unittest.main()
