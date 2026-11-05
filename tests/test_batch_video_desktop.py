"""Two entry points share the same native page with isolated targets."""
from unittest.mock import patch
from PIL import Image
import test_total_video_desktop as fixture


class BatchVideoDesktop(fixture.TotalVideoDesktop):
    def test_batch_entry_render_return_isolation_and_sizes(self):
        self.errors=[]
        self.root.report_callback_exception=lambda *e:self.errors.append(e)
        self.app.narration()
        narration=self.app.production.current
        narration.video_button.invoke()
        page=self.app.production.current
        self.wait_page(page)
        self.assertEqual(page.batch_id,self.batch)
        self.assertIn('本批',page.source_info.cget('text'))
        source=self.path/'圖片.png'
        Image.new('RGBA',(80,120),(255,0,0,128)).save(source)
        with patch('tkinter.filedialog.askopenfilename',return_value=str(source)):
            page.choose_button.invoke();self.wait_page(page)
        page.resolution.set('720p')
        page.back_button.invoke()
        self.assertIs(self.app.production.current,narration)
        narration.video_button.invoke();self.wait_page(page)
        self.assertEqual(page.resolution.get(),'720p')
        with patch('edge_tts.Communicate',side_effect=AssertionError('no TTS')):
            page.start_button.invoke();self.wait_page(page)
        self.assertIsNotNone(self.flow.batch_video_target(self.batch).total_video())
        self.app.total_video();book=self.app.production.current;self.wait_page(book)
        self.assertIs(type(book),type(page))
        self.assertIsNone(book.product)
        self.app.batch_video();self.wait_page(page)
        self.root.state('normal')
        for size in ('1040x640','1360x800'):
            self.root.geometry(size);self.root.update()
            for widget in (page.start_button,page.back_button,page.choose_button,page.outputs_button):
                self.assertTrue(widget.winfo_viewable())
                self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(),self.root.winfo_rootx()+self.root.winfo_width())
                self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),self.root.winfo_rooty()+self.root.winfo_height())
        self.assertEqual(self.errors,[])
