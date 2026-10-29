"""PDF reading layout and real preview-coordinate transformations."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import time
import unittest

from ebook2mp4.desktop import make_app
from ebook2mp4.workflow import ProjectWorkflow
from test_pdf import pdf_bytes


class PdfReadingLayout(unittest.TestCase):
    def setUp(self):
        base = Path('.scratch/test-runs')
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='pdf-layout-', dir=base)
        self.addCleanup(self.temp.cleanup)
        self.root, self.app = make_app()
        self.addCleanup(self.root.destroy)
        folder = Path(self.temp.name)
        source = folder / 'book.pdf'
        source.write_bytes(pdf_bytes(2))
        flow = ProjectWorkflow.create(folder / 'project', 'PDF layout')
        job = flow.start_pdf_extraction(flow.inspect_pdf(source), 1, 2)
        self.assertTrue(job.wait(10))
        self.app.flow = flow
        self.app.batch_id = flow.finish_pdf_extraction(job)
        self.app.refresh()
        self.app.compare_pdf_pages()
        self.dialog = self.app.pdf_dialog
        self.until(lambda: self.dialog.ready and self.dialog.image is not None)

    def until(self, predicate):
        deadline = time.monotonic() + 15
        while not predicate() and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.01)
        self.assertTrue(predicate())

    def restore_small(self):
        self.dialog.state('normal')
        self.dialog.geometry('740x570+20+20')
        self.root.update()
        self.dialog.resize_image()

    def test_standard_maximized_window_and_fixed_actions_at_minimum_size(self):
        dialog = self.dialog
        self.assertEqual(dialog.state(), 'zoomed')
        self.assertEqual(dialog.transient(), '')
        self.assertEqual(dialog.settings_window.state(), 'withdrawn')
        self.restore_small()
        self.assertLessEqual(dialog.image.width() + 16, dialog.canvas.winfo_width())
        self.assertLessEqual(dialog.image.height() + 16, dialog.canvas.winfo_height())
        for widget in (dialog.retain_button, dialog.skip_button, dialog.extract_button,
                       dialog.cancel_button, dialog.page_list, dialog.retry_menu_button):
            self.assertTrue(widget.winfo_ismapped())
            self.assertGreaterEqual(widget.winfo_rootx(), dialog.winfo_rootx())
            self.assertLessEqual(widget.winfo_rootx() + widget.winfo_width(), dialog.winfo_rootx() + dialog.winfo_width())
            self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(), dialog.winfo_rooty() + dialog.winfo_height())
        dialog.settings_button.invoke()
        self.root.update()
        self.assertTrue(dialog.settings_window.winfo_viewable())
        dialog.hide_settings()
        self.assertEqual(dialog.grab_current(), dialog)

    def test_zoom_pan_region_coordinates_survive_resize_and_reset_on_page_change(self):
        dialog = self.dialog
        self.restore_small()
        dialog.zoom.set('150%')
        dialog.resize_image()
        dialog.canvas.xview_moveto(.2)
        dialog.canvas.yview_moveto(.2)
        a, b = SimpleNamespace(x=30, y=30), SimpleNamespace(x=130, y=130)
        left, top = dialog.image_origin
        expected = ((dialog.canvas.canvasx(a.x) - left) / dialog.image.width(),
                    (dialog.canvas.canvasy(a.y) - top) / dialog.image.height(),
                    (dialog.canvas.canvasx(b.x) - left) / dialog.image.width(),
                    (dialog.canvas.canvasy(b.y) - top) / dialog.image.height())
        dialog.begin_region(a)
        dialog.drag_region(b)
        dialog.end_region(b)
        for actual, wanted in zip(dialog.region, expected):
            self.assertAlmostEqual(actual, wanted, places=6)
        region = dialog.region
        dialog.zoom.set('適合整頁')
        dialog.resize_image()
        self.assertEqual(dialog.region, region)
        self.assertTrue(dialog.canvas.find_withtag('region'))
        dialog.next_button.invoke()
        self.until(lambda: dialog.ready and dialog.image is not None)
        self.assertEqual(dialog.page.get(), '2')
        self.assertIsNone(dialog.region)
        self.assertFalse(dialog.canvas.find_withtag('region'))

    def test_source_warning_remains_visible_while_operation_messages_change(self):
        dialog = self.dialog
        self.restore_small()
        dialog.pages[0]['status'] = 'pending'
        dialog.pages[0]['error'] = '文字稀少，請對照頁圖確認。'
        dialog.view()
        self.until(lambda: dialog.ready)
        dialog.progress.configure(text='新的辨識作業進度')
        self.root.update()
        self.assertTrue(dialog.page_error.winfo_ismapped())
        self.assertIn('文字稀少', dialog.page_error.cget('text'))
        self.assertIn('待檢查', dialog.page_info.cget('text'))
        self.assertEqual(dialog.progress.cget('text'), '新的辨識作業進度')
        long_error = '保存失敗：' + '檔案被占用，請釋放後重試。' * 100
        dialog.progress.configure(text=long_error)
        self.root.update()
        self.assertEqual(dialog.progress.full_text, long_error)
        self.assertLess(len(dialog.progress.cget('text')), 220)
        self.assertTrue(dialog.cancel_button.winfo_viewable())
        self.assertLessEqual(dialog.cancel_button.winfo_rooty() + dialog.cancel_button.winfo_height(),
                             dialog.winfo_rooty() + dialog.winfo_height())


if __name__ == '__main__':
    unittest.main()
