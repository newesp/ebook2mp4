"""Mock structure, whole-window alignment and retained media controls."""
import json
import os
from pathlib import Path
import shutil
from unittest.mock import patch
from PIL import Image, ImageGrab
import test_unified_video_workspace as baseline


class VideoLayoutRevision(baseline.UnifiedVideoWorkspace):
    # Only this new acceptance case; inherited journeys run in their own suite.
    test_routes_keep_drafts_native_tabs_and_real_products = None
    test_native_geometry_components_and_scroll_ownership = None
    test_merge_without_total_audio_keeps_task_and_tab_content = None

    def test_background_timeline_and_context_fields(self):
        from test_total_video_background import background
        self.app.batch_video()
        page = self.app.production.current
        self.wait_page(page)
        self.root.state('normal')
        self.root.geometry('1280x720+0+0')
        page.source_kind.set('背景影片（MP4）')
        page.kind_changed()
        self.wait_page(page)
        for name, duration, short in (('short', .1, True), ('long', .9, False)):
            path = background(self.path/(name+'.mp4'), duration)
            with patch('tkinter.filedialog.askopenfilename', return_value=str(path)):
                page.choose_button.invoke()
                self.wait_page(page)
            self.root.update()
            self.assertEqual(bool(page.mode_control.winfo_ismapped()), short)
            self.inside(page.seek_control)
            page.seek.set(.08)
            page.scrub()
            self.wait_page(page)
            self.assertIsNotNone(page.preview_image)
            page.preview()
            self.root.update()
            page.stop()
            self.assertIsNone(page.frame_job)
            self.assertFalse(page.preview_playing)
            ImageGrab.grab(window=int(self.root.frame(),16)).save(Path('docs/verification/unified-video')/f'revised-background-{name}.png')

    def test_mock_structure_and_alignment(self):
        self.app.batch_video()
        page = self.app.production.current
        self.wait_page(page)
        picture = self.path/'山林封面.png'
        Image.new('RGB', (960, 540), '#618c76').save(picture)
        with patch('tkinter.filedialog.askopenfilename', return_value=str(picture)):
            page.choose_button.invoke()
            self.wait_page(page)
        evidence = Path('docs/verification/unified-video')
        metrics = []
        self.root.state('normal')
        for size in ('1536x864', '1280x720', '900x640'):
            self.root.geometry(size+'+0+0')
            for collapsed in (False, True):
                if self.app.focus_mode != collapsed:
                    self.app.production.toggle_files()
                self.root.update()
                page.layout_workspace()
                self.app.layout_workspace()
                self.root.update()
                for widget in (page.choose_button, page.resolution_control, page.start_button,
                               page.save_return_button, page.outputs_button):
                    self.inside(widget)
                self.assertLess(page.material.winfo_rooty(), page.canvas.winfo_rooty())
                self.assertGreater(page.canvas.winfo_width(), page.editor.winfo_width()*.95)
                self.assertEqual(bool(self.app.production.files_button.winfo_ismapped()), collapsed)
                if not collapsed:
                    self.assertLessEqual(abs(self.app.list_header.winfo_rooty()-self.app.production.video_toolbar.winfo_rooty()), 2)
                    self.assertLessEqual(abs(self.app.batch_list.winfo_rooty()-page.notebook.winfo_rooty()), 2)
                if size != '900x640':
                    self.assertLessEqual(abs(page.kind_control.winfo_rooty()-page.resolution_control.winfo_rooty()), 2)
                    self.assertLessEqual(abs(page.start_button.winfo_rooty()-page.back_button.winfo_rooty()), 2)
                metrics.append(dict(size=size, collapsed=collapsed, preview=[page.canvas.winfo_width(),page.canvas.winfo_height()],
                    header_y=[self.app.list_header.winfo_rooty(),self.app.production.video_toolbar.winfo_rooty()],
                    content_y=[self.app.batch_list.winfo_rooty(),page.notebook.winfo_rooty()]))
                ImageGrab.grab(window=int(self.root.frame(),16)).save(evidence/f'revised-{size}-{collapsed}.png')
        self.root.geometry('1280x720+0+0')
        self.root.update()
        self.app.total_video()
        book = self.app.production.current
        self.wait_page(book)
        self.root.update()
        self.assertLessEqual(abs(book.kind_control.winfo_rooty()-book.resolution_control.winfo_rooty()), 2)
        self.app.batch_video()
        self.wait_page(page)
        self.assertLessEqual(abs(page.kind_control.winfo_rooty()-page.resolution_control.winfo_rooty()), 2)
        self.app.narration()
        self.root.update()
        self.assertEqual(self.app.narration_dialog.files_button.cget('text'), '>')
        if os.environ.get('VIDEO_LAYOUT_PACKAGE_FIXTURE'):
            target = Path('.scratch/video-layout-package')
            target.mkdir()
            shutil.copytree(self.flow.root, target/'book')
            home = target/'app'
            home.mkdir()
            (home/'session.json').write_text(json.dumps(dict(last_project=str((target/'book').resolve()))), encoding='utf-8')
        (evidence/'revised-metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
