"""Real native PDF refinement workflow; only OCR/model boundaries are controlled."""
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow
from test_pdf import pdf_bytes


READY = dict(language='自動中英', codes='chi_sim+chi_tra+eng', missing=[],
             download_bytes=0, engine_error='', ready=True)


class PdfRefinementDesktop(unittest.TestCase):
    def setUp(self):
        base = Path('.scratch/test-runs')
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        folder = Path(self.temp.name)
        source = folder / 'book.pdf'
        source.write_bytes(pdf_bytes(1))
        self.root, self.app = make_app()
        self.addCleanup(self.root.destroy)
        self.flow = ProjectWorkflow.create(folder / 'book', 'Refinement')
        job = self.flow.start_pdf_extraction(self.flow.inspect_pdf(source), 1, 1)
        self.assertTrue(job.wait(5))
        self.batch = self.flow.finish_pdf_extraction(job)
        self.original = self.flow.pdf_pages(self.batch)[0]['text']
        self.app.flow, self.app.batch_id = self.flow, self.batch
        self.app.refresh()
        self.models = patch.object(self.flow, 'ocr_models', return_value=READY.copy())
        self.models.start()
        self.addCleanup(self.models.stop)
        self.app.compare_pdf_pages()
        self.dialog = self.app.pdf_dialog
        self.until(lambda: self.dialog.ready and self.dialog.image is not None and not self.dialog.ocr_info_pending)

    def until(self, predicate):
        deadline = time.monotonic() + 10
        while not predicate() and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.01)
        self.assertTrue(predicate())

    def select_text(self, text):
        widget = self.dialog.text
        start = widget.search(text, '1.0', stopindex='end', exact=True)
        self.assertTrue(start)
        widget.tag_remove('sel', '1.0', 'end')
        widget.tag_add('sel', start, f'{start}+{len(text)}c')
        self.dialog.region = (.1, .1, .5, .4)

    def test_ready_model_does_not_offer_or_start_zero_byte_download(self):
        self.assertIn('模型已就緒', self.dialog.install_button.cget('text'))
        self.assertTrue(self.dialog.install_button.instate(['disabled']))
        with patch.object(self.flow, 'start_ocr_model_install') as install:
            self.dialog.install_models()
        install.assert_not_called()
        self.assertIn('不需下載', self.dialog.model_info.cget('text'))

    def test_settings_unlock_and_next_region_uses_new_language_and_layout(self):
        from ebook2mp4.ocr import LANGUAGES
        release, entered = threading.Event(), threading.Event()
        def info(language):
            return dict(READY, language=language, codes=LANGUAGES[language])
        calls = []
        def recognize(*args, **kwargs):
            calls.append((args, kwargs))
            if len(calls) == 2:
                entered.set()
                release.wait(10)
            return dict(text='First accepted' if len(calls) == 1 else '3.14159', confidence=95)
        self.flow.ocr_models.side_effect = info
        with patch('ebook2mp4.ocr.model_info', side_effect=info), \
                patch('ebook2mp4.ocr.recognize_page', side_effect=recognize):
            self.dialog.language.set('繁中＋英文')
            self.dialog.layout.set('單一區塊')
            self.select_text('Hello')
            self.dialog.retry_region()
            self.until(lambda: self.dialog.pending_job is not None and self.dialog.ready)
            first = self.dialog.pending_job
            for control in (self.dialog.mode_select, self.dialog.language_select, self.dialog.layout_select):
                self.assertTrue(control.instate(['readonly']), str(control))
                self.assertFalse(control.instate(['disabled']), str(control))
            self.dialog.language_select.set('簡中＋英文')
            self.dialog.language_select.event_generate('<<ComboboxSelected>>')
            self.until(lambda: self.dialog.ready and not self.dialog.ocr_info_pending)
            self.assertEqual(self.dialog.model_state['codes'], 'chi_sim+eng')
            self.dialog.layout_select.set('單行標題')
            self.assertEqual(first.settings['language'], 'chi_tra+eng')
            self.assertEqual(first.settings['psm'], 6)
            self.dialog.continue_button.invoke()
            self.until(lambda: self.dialog.ready)
            self.select_text('3.14')
            self.dialog.retry_region()
            try:
                self.assertTrue(entered.wait(5))
                self.root.update()
                for control in (self.dialog.mode_select, self.dialog.language_select, self.dialog.layout_select):
                    self.assertTrue(control.instate(['disabled']))
                self.assertEqual(self.dialog.job.settings['language'], 'chi_sim+eng')
                self.assertEqual(self.dialog.job.settings['psm'], 7)
            finally:
                release.set()
                self.until(lambda: self.dialog.pending_job is not None and self.dialog.ready)
            for control in (self.dialog.mode_select, self.dialog.language_select, self.dialog.layout_select):
                self.assertTrue(control.instate(['readonly']))
            self.assertIn('First accepted', self.dialog.text.get('1.0', 'end-1c'))
            self.dialog.accept_button.invoke()
            self.until(lambda: self.app.pdf_dialog is None)
        self.assertIn('First accepted', self.app.current_text)
        self.assertIn('3.14159', self.app.current_text)
        self.assertEqual(self.flow.pdf_pages(self.batch)[0]['text'], self.original)

    def test_failed_region_unlocks_settings_and_missing_model_can_be_installed(self):
        from ebook2mp4.workflow import ProjectError
        with patch('ebook2mp4.pdf.PdfExtraction.ocr_settings', return_value={'language': 'eng'}), \
                patch('ebook2mp4.ocr.recognize_page', side_effect=ProjectError('Controlled OCR failure')):
            self.select_text('Hello')
            self.dialog.retry_region()
            self.until(lambda: self.dialog.pending_job is not None and self.dialog.ready)
        self.assertTrue(self.dialog.language_select.instate(['readonly']))
        self.flow.ocr_models.return_value = dict(READY, ready=False, missing=['chi_sim'], download_bytes=100)
        self.dialog.language_select.set('簡中＋英文')
        self.dialog.language_select.event_generate('<<ComboboxSelected>>')
        self.until(lambda: self.dialog.ready and not self.dialog.ocr_info_pending)
        self.assertFalse(self.dialog.install_button.instate(['disabled']))
        self.assertIn('下載缺少的模型', self.dialog.install_button.cget('text'))

    def test_real_ocr_job_displays_indeterminate_busy_feedback(self):
        release = threading.Event()
        def recognition(*_args, **_kwargs):
            release.wait(5)
            return dict(text='Corrected', selected_language='eng', confidence=95)
        with patch('ebook2mp4.pdf.PdfExtraction.ocr_settings', return_value={'language': 'eng'}), \
                patch('ebook2mp4.ocr.recognize_page', side_effect=recognition):
            self.select_text('Hello')
            self.dialog.retry_region()
            try:
                self.root.update()
                self.assertTrue(self.dialog.busy_bar.winfo_ismapped())
                self.assertEqual(str(self.dialog.busy_bar.cget('mode')), 'indeterminate')
            finally:
                release.set()
                self.until(lambda: self.dialog.pending_job is not None and self.dialog.ready)
        self.assertFalse(self.dialog.busy_bar.winfo_ismapped())

    def test_two_regions_accumulate_then_publish_one_batch(self):
        with patch('ebook2mp4.pdf.PdfExtraction.ocr_settings', return_value={'language': 'eng'}), \
                patch('ebook2mp4.ocr.recognize_page', side_effect=[
                    dict(text='Corrected', selected_language='eng', confidence=95),
                    dict(text='3.14159', selected_language='eng', confidence=95)]):
            self.select_text('Hello')
            self.dialog.retry_region()
            self.until(lambda: self.dialog.pending_job is not None and self.dialog.ready)
            self.assertIn('Corrected', self.dialog.text.get('1.0', 'end-1c'))
            self.dialog.state('normal')
            self.dialog.geometry('740x570+20+20')
            self.root.update()
            for control in (self.dialog.continue_button, self.dialog.accept_button,
                            self.dialog.cancel_button, self.dialog.adopt_check, self.dialog.original_choice):
                self.assertTrue(control.winfo_ismapped())
                self.assertLessEqual(control.winfo_rootx()+control.winfo_width(), self.dialog.winfo_rootx()+self.dialog.winfo_width())
                self.assertLessEqual(control.winfo_rooty()+control.winfo_height(), self.dialog.winfo_rooty()+self.dialog.winfo_height())
            self.dialog.continue_button.invoke()
            self.until(lambda: self.dialog.ready)
            self.assertTrue(self.dialog.region_button.winfo_ismapped())
            self.assertEqual(self.dialog.region_button.winfo_y(), self.dialog.accept_button.winfo_y())
            self.assertFalse(self.dialog.retain_button.winfo_ismapped())
            self.assertFalse(self.dialog.skip_button.winfo_ismapped())
            self.select_text('3.14')
            self.dialog.retry_region()
            self.until(lambda: self.dialog.pending_job is not None and self.dialog.ready)
            current = self.dialog.text.get('1.0', 'end-1c')
            self.assertIn('Corrected', current)
            self.assertIn('3.14159', current)
            self.assertEqual(len(self.flow.state['batches']), 1)
            self.dialog.accept_button.invoke()
            self.until(lambda: self.app.pdf_dialog is None)
        self.assertEqual(len(self.flow.state['batches']), 2)
        self.assertEqual(self.flow.pdf_pages(self.batch)[0]['text'], self.original)
        self.assertIn('Corrected', self.app.current_text)
        self.assertIn('3.14159', self.app.current_text)

    def test_keep_original_choice_resets_selection_baseline_before_next_region(self):
        with patch('ebook2mp4.pdf.PdfExtraction.ocr_settings', return_value={'language': 'eng'}), \
                patch('ebook2mp4.ocr.recognize_page', side_effect=[
                    dict(text='Long replacement', selected_language='eng', confidence=95),
                    dict(text='3.14159', selected_language='eng', confidence=95)]):
            self.select_text('Hello')
            self.dialog.retry_region()
            self.until(lambda: self.dialog.pending_job is not None and self.dialog.ready)
            self.dialog.adopt_page.set(False)
            self.dialog.choose_page()
            self.dialog.continue_button.invoke()
            self.until(lambda: self.dialog.ready)
            self.assertEqual(self.dialog.text.get('1.0', 'end-1c'), self.original)
            self.select_text('3.14')
            self.dialog.retry_region()
            self.until(lambda: self.dialog.pending_job is not None and self.dialog.ready)
            current = self.dialog.text.get('1.0', 'end-1c')
            self.assertIn('Hello', current)
            self.assertNotIn('Long replacement', current)
            self.assertIn('3.14159', current)

    def test_reject_third_region_keeps_first_two_when_recognizing_fourth(self):
        with patch('ebook2mp4.pdf.PdfExtraction.ocr_settings', return_value={'language': 'eng'}), \
                patch('ebook2mp4.ocr.recognize_page', side_effect=[
                    dict(text='First accepted correction', confidence=95),
                    dict(text='Second accepted correction', confidence=95),
                    dict(text='WRONG THIRD RESULT', confidence=95),
                    dict(text='Fourth accepted correction', confidence=95)]):
            for target in ('Hello', '3.14', 'U.S.A.'):
                self.select_text(target)
                self.dialog.retry_region()
                self.until(lambda: self.dialog.pending_job is not None and self.dialog.ready)
                if target != 'U.S.A.':
                    self.dialog.continue_button.invoke()
                    self.until(lambda: self.dialog.ready)
            self.dialog.original_choice.invoke()
            self.dialog.continue_button.invoke()
            self.until(lambda: self.dialog.ready)
            before_fourth = self.dialog.text.get('1.0', 'end-1c')
            self.assertIn('First accepted correction', before_fourth)
            self.assertIn('Second accepted correction', before_fourth)
            self.assertIn('U.S.A.', before_fourth)
            self.assertNotIn('WRONG THIRD RESULT', before_fourth)
            self.select_text('original text')
            self.dialog.retry_region()
            self.until(lambda: self.dialog.pending_job is not None and self.dialog.ready)
            self.dialog.accept_button.invoke()
            self.until(lambda: self.app.pdf_dialog is None)
        self.assertIn('First accepted correction', self.app.current_text)
        self.assertIn('Second accepted correction', self.app.current_text)
        self.assertIn('Fourth accepted correction', self.app.current_text)
        self.assertIn('U.S.A.', self.app.current_text)
        self.assertNotIn('WRONG THIRD RESULT', self.app.current_text)
        self.assertEqual(len(self.flow.state['batches']), 2)
        self.assertEqual(self.flow.pdf_pages(self.batch)[0]['text'], self.original)

