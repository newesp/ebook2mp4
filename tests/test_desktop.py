"""Native import, source protection and recovery in the unified workspace."""
from unittest.mock import patch
import tkinter as tk
import unittest
import test_unified_manuscript as fixture
from ebook2mp4.workflow import ProjectWorkflow, ProjectError
from test_pdf import pdf_bytes


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


class DesktopJourney(unittest.TestCase):
    setUp = fixture.ManuscriptTests.setUp
    app = fixture.ManuscriptTests.app
    spin = fixture.ManuscriptTests.spin
    def test_pdf_import_page_compare_and_manual_mapping(self):
        root, app = self.app()
        path = self.folder/'book.pdf'
        path.write_bytes(pdf_bytes(3))
        with patch('ebook2mp4.manuscript_source.filedialog.askopenfilename', return_value=str(path)):
            app.import_pdf()
        app.source_tools.mode.set('文字層')
        app.source_tools.extract()
        self.spin(root, lambda: app.source_job is None)
        self.assertEqual(app.flow._batch(app.batch_id)['kind'], 'pdf')
        self.assertIn('Chapter 3', app.current_text)
        self.spin(root, lambda: app.source_tools.image_future is None)
        self.assertTrue(app.image_canvas.find_all())
        self.assertFalse([w for w in root.winfo_children() if isinstance(w, tk.Toplevel)])
        app.editor.insert('end', 'manual correction')
        root.update()
        self.assertIn('無精確對應', app.source_meta.cget('text'))
        app.confirm_reading()
        self.assertEqual(app.flow.reading_text(app.batch_id), app.current_text)

    def test_pdf_reextraction_previews_and_keeps_human_original(self):
        root, app = self.app()
        path = self.folder/'book.pdf'
        path.write_bytes(pdf_bytes(2))
        job = app.flow.start_pdf_extraction(app.flow.inspect_pdf(path), 1, 2)
        self.assertTrue(job.wait(5))
        app.batch_id = app.flow.finish_pdf_extraction(job)
        app.refresh()
        original_batch = app.batch_id
        app.editor.insert('end', '人工修正必須保留')
        root.update()
        human = app.current_text
        app.open_tools(2)
        app.source_tools.mode.set('文字層')
        app.source_tools.extract()
        self.spin(root, lambda: app.source_pending is not None)
        self.assertEqual(app.current_text, human)
        app.source_tools.apply()
        self.assertNotEqual(app.batch_id, original_batch)
        self.assertTrue(app.flow.workspace_state(original_batch)['text'].endswith('人工修正必須保留'))

    def test_pdf_failed_render_clears_previous_page(self):
        root, app = self.app()
        path = self.folder/'book.pdf'
        path.write_bytes(pdf_bytes(2))
        job = app.flow.start_pdf_extraction(app.flow.inspect_pdf(path), 1, 2)
        job.wait(5)
        app.batch_id = app.flow.finish_pdf_extraction(job)
        app.refresh()
        app.toggle_source()
        self.spin(root, lambda: app.source_tools.image_future is None)
        self.assertTrue(app.image_canvas.find_all())
        with patch('ebook2mp4.pdf.render', side_effect=ProjectError('無法產生預覽')):
            app.change_source_page(1)
            self.spin(root, lambda: app.source_tools.image_future is None)
        self.assertFalse(app.image_canvas.find_all())
        self.assertIn('無法', app.source_tools.detail.cget('text'))

    def test_cp950_recovery_stays_in_main_workspace(self):
        root, app = self.app()
        source = self.folder/'cp950.txt'
        source.write_bytes('第二章，碁。'.encode('cp950'))
        with patch('ebook2mp4.manuscript_source.filedialog.askopenfilename', return_value=str(source)):
            app.import_txt()
        self.assertEqual(len(app.flow.state['batches']), 1)
        app.source_tools.encoding.set('CP950')
        app.source_tools.load_txt()
        app.source_tools.apply()
        self.assertEqual(app.current_text, '第二章，碁。')
        self.assertEqual(app.flow._batch(app.batch_id)['source']['encoding'], 'CP950')

    def test_failed_autosave_blocks_batch_switch(self):
        root, app = self.app()
        first = app.batch_id
        second = app.flow.import_txt(app.flow.inspect_txt(self.source))
        app.refresh()
        app.editor.insert('end', '尚未暫存')
        root.update()
        with patch('ebook2mp4.workflow.os.replace', side_effect=OSError()):
            app.batch_list.selection_set(second)
            app.select_batch()
        self.assertEqual(app.batch_id, first)
        self.assertTrue(app.current_text.endswith('尚未暫存'))

    def test_native_file_drop_imports_supported_source(self):
        root, app = self.app()
        app.file_drop.import_path(str(self.source))
        self.assertEqual(len(app.flow.state['batches']), 2)
        self.assertFalse([w for w in root.winfo_children() if isinstance(w, tk.Toplevel)])

    def test_failed_pdf_import_publication_retains_candidate_for_retry(self):
        root, app = self.app()
        path = self.folder/'book.pdf'
        path.write_bytes(pdf_bytes(2))
        with patch('ebook2mp4.manuscript_source.filedialog.askopenfilename', return_value=str(path)):
            app.import_pdf()
        app.source_tools.mode.set('文字層')
        app.source_tools.extract()
        self.assertTrue(app.source_job.wait(5))
        with patch.object(app.flow, '_commit', side_effect=ProjectError('controlled publication failure')):
            self.spin(root, lambda: app.source_pending is not None)
        self.assertEqual(len(app.flow.state['batches']), 1)
        self.assertIsNotNone(app.source_pending)
        app.source_tools.apply()
        self.assertIsNone(app.source_pending)
        self.assertEqual(app.flow._batch(app.batch_id)['kind'], 'pdf')
        self.assertIn('Chapter 2', app.current_text)
