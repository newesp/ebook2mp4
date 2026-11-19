"""Native route, retention, geometry and component checks with real local media."""
import json
import time
import tkinter as tk
from pathlib import Path
from unittest.mock import patch
import unittest
from PIL import Image, ImageGrab
import test_total_audio_desktop as fixture


class UnifiedVideoWorkspace(unittest.TestCase):
    setUp = fixture.TotalAudioDesktop.setUp
    prepare = fixture.TotalAudioDesktop.prepare
    refresh_voices = fixture.TotalAudioDesktop.refresh_voices
    audio = fixture.TotalAudioDesktop.audio
    shutdown = fixture.TotalAudioDesktop.shutdown
    wait_page = fixture.TotalAudioDesktop.wait_page

    def inside(self, widget):
        self.assertTrue(widget.winfo_viewable(), str(widget))
        self.assertGreaterEqual(widget.winfo_rootx(), self.root.winfo_rootx())
        self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(), self.root.winfo_rootx()+self.root.winfo_width())
        self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(), self.root.winfo_rooty()+self.root.winfo_height())

    def test_video_text_scrollbars_follow_overflow(self):
        self.app.batch_video()
        page = self.app.production.current
        self.wait_page(page)
        self.root.state('normal')
        self.root.geometry('900x640')
        from ebook2mp4.video_workspace import replace_text

        def show_text(reader, value):
            replace_text(reader, value)
            reader.count('1.0', 'end', 'update', 'ypixels')
            self.root.update()
            self.assertEqual(reader.get('1.0', 'end-1c'), value)

        for index, reader in ((1, page.details_text), (2, page.task_text)):
            with self.subTest(tab=index), patch.object(page, 'refresh_workspace'):
                page.notebook.select(index)
                self.root.update()
                scrollbar = next(widget for widget in reader.master.winfo_children()
                                 if widget.winfo_class() == 'TScrollbar')
                show_text(reader, '尚無成品。')
                self.assertEqual(reader.yview(), (0, 1))
                self.assertFalse(scrollbar.winfo_viewable(), 'Fitting text must not reserve a scrollbar')

                show_text(reader, '\n'.join(f'第 {number} 行' for number in range(300)))
                self.assertLess(reader.yview()[1], 1)
                self.assertTrue(scrollbar.winfo_viewable())
                reader.yview_moveto(1)
                self.root.update()
                self.assertEqual(reader.yview()[1], 1)

                show_text(reader, '尚無成品。')
                self.assertEqual(reader.yview(), (0, 1))
                self.assertFalse(scrollbar.winfo_viewable(), 'Short text must release the previous track')

    def test_routes_keep_drafts_native_tabs_and_real_products(self):
        self.app.batch_video()
        batch = self.app.production.current
        self.wait_page(batch)
        picture = self.path/'native.png'
        Image.new('RGB', (160, 90), 'red').save(picture)
        with patch('tkinter.filedialog.askopenfilename', return_value=str(picture)):
            batch.choose_button.invoke()
            self.wait_page(batch)
        batch.resolution.set('720p')
        batch.notebook.select(2)
        self.root.update()
        self.app.production.scope.set('全書')
        self.app.production.change_scope()
        book = self.app.production.current
        self.wait_page(book)
        self.assertIsNone(book.audio)
        self.assertTrue(book.start_button.instate(['disabled']))
        self.assertFalse(book.choose_button.instate(['disabled']))
        book.resolution.set('1080p')
        self.app.production.scope.set('本批')
        self.app.production.change_scope()
        self.wait_page(batch)
        self.assertIs(self.app.production.current, batch)
        self.assertEqual(batch.notebook.index(batch.notebook.select()), 2)
        self.assertEqual(batch.resolution.get(), '720p')
        self.assertIsNotNone(batch.pending_image)
        batch.notebook.focus_force()
        batch.notebook.event_generate('<Left>')
        self.root.update()
        self.assertEqual(batch.notebook.index(batch.notebook.select()), 1)
        with patch('edge_tts.Communicate', side_effect=AssertionError('No cloud request')):
            batch.start_button.invoke()
            self.wait_page(batch)
        product = self.flow.batch_video_target(self.app.batch_id).total_video()
        self.assertIsNotNone(product)
        self.assertIsNone(self.flow.total_audio())
        target = self.path/'export'
        with patch('tkinter.filedialog.asksaveasfilename', return_value=str(target)):
            batch.export()
            self.wait_page(batch)
        self.assertEqual(len(list(target.glob('*.mp4'))), 1)
        self.assertEqual(len(list(target.glob('*.srt'))), 1)

    def test_native_geometry_components_and_scroll_ownership(self):
        self.app.batch_video()
        page = self.app.production.current
        self.wait_page(page)
        evidence = Path('docs/verification/unified-video')
        measurements = []
        self.root.state('normal')
        self.root.lift()
        self.root.focus_force()
        for size in ('1280x720', '1536x864', '900x640'):
            self.root.geometry(size+'+0+0')
            self.root.update()
            for collapsed in (False, True):
                if self.app.focus_mode != collapsed:
                    self.app.production.toggle_files()
                self.root.update()
                for widget in (page.start_button, page.back_button, page.outputs_button,
                               self.app.production.scope_control):
                    self.inside(widget)
                choice = self.app.production.scope_control
                peer = self.app.production.files_button if collapsed else self.app.focus_button
                self.assertLessEqual(abs(choice.winfo_height()-peer.winfo_height()), 2)
                self.assertLessEqual(abs(choice.winfo_rooty()-peer.winfo_rooty()), 2)
                if size == '1280x720' and not collapsed:
                    choice.configure(style='TCombobox')
                    self.root.update()
                    self.assertGreater(abs(choice.winfo_height()-peer.winfo_height()), 2)
                    choice.configure(style='Workspace.TCombobox')
                    self.root.update()
                self.assertNotIn('▾', page.outputs_button.cget('text'))
                # Geometry alone cannot detect an editor hidden below the notebook.
                stacking = tuple(str(w) for w in page.winfo_children())
                self.assertGreater(stacking.index(str(page.editor)), stacking.index(str(page.notebook)))
                measurements.append(dict(requested=size, collapsed=collapsed,
                    client=[self.root.winfo_width(), self.root.winfo_height()],
                    scaling=float(self.root.tk.call('tk', 'scaling')),
                    scope_height=choice.winfo_height(), peer_height=peer.winfo_height(),
                    content_width=page.winfo_width(), preview=[page.canvas.winfo_width(), page.canvas.winfo_height()]))
                if collapsed:
                    self.root.update()
                    ImageGrab.grab(window=int(self.root.frame(), 16)).save(evidence/f'native-{size}.png')
        page.notebook.select(2)
        self.root.update()
        from ebook2mp4.video_workspace import replace_text
        page.status.configure(text='\n'.join(f'第 {i} 行：來源與任務訊息。' for i in range(300)))
        page.refresh_workspace()
        before = page.start_button.winfo_rooty()
        page.task_text.focus_force()
        page.task_text.event_generate('<Control-End>')
        self.root.update()
        self.assertAlmostEqual(page.task_text.yview()[1], 1, places=2)
        end_position = page.task_text.yview()[0]
        page.task_text.event_generate('<MouseWheel>', delta=120)
        self.root.update()
        self.assertLess(page.task_text.yview()[0], end_position)
        self.assertEqual(before, page.start_button.winfo_rooty())
        from tkinter import ttk
        style = ttk.Style(self.root)
        before_height = self.app.production.scope_control.winfo_height()
        pixels = round(self.root.winfo_fpixels('10p')*1.25)
        for role in ('.', 'TButton', 'TCombobox', 'TLabel', 'TMenubutton', 'TNotebook.Tab', 'Treeview'):
            style.configure(role, font=('Microsoft JhengHei', -pixels))
        # Combobox/Entry have a widget font from the app's option database;
        # changing ttk styles alone does not enlarge their rendered text.
        from tkinter import font as tkfont
        def enlarge(widget):
            for child in widget.winfo_children():
                if 'font' in child.keys() and child.cget('font'):
                    original = tkfont.Font(font=child.cget('font'))
                    size = original.actual('size')
                    physical = size*self.root.winfo_fpixels('1p') if size > 0 else -size
                    child.configure(font=(original.actual('family'), -round(physical*1.25)))
                enlarge(child)
        enlarge(self.app)
        page.notebook.select(0)
        self.root.update()
        for widget in (page.start_button, page.back_button, page.outputs_button, page.resolution_control):
            self.inside(widget)
        self.assertGreater(self.app.production.scope_control.winfo_height(), before_height)
        measurements.append(dict(requested='900x640', text_scale='125%',
            client=[self.root.winfo_width(), self.root.winfo_height()],
            scaling=float(self.root.tk.call('tk', 'scaling'))))
        ImageGrab.grab(window=int(self.root.frame(), 16)).save(evidence/'native-900x640-125.png')
        (evidence/'native-metrics.json').write_text(json.dumps(measurements, indent=2), encoding='utf-8')

    def test_merge_without_total_audio_keeps_task_and_tab_content(self):
        for index, identity in enumerate(self.ids):
            path = self.path/f'cover-{index}.png'
            Image.new('RGB', (160, 90), 'red' if index == 0 else 'blue').save(path)
            target = self.flow.batch_video_target(identity)
            target.save_total_video_settings(image=target.inspect_total_video_image(path), resolution='720p')
            job = target.start_total_video()
            self.assertTrue(job.wait(30), job.state)
            target.finish_total_video(job)
        self.flow.save_total_video_method('batch-videos')
        self.flow.save_video_merge_settings(self.ids, resolution='720p')
        self.flow.save_output_formats(['mp4'])
        self.app.production.open_video()
        page = self.app.production.current
        self.wait_page(page)
        self.assertTrue(page.movie)
        self.assertIsNone(self.flow.total_audio())
        self.root.state('normal')
        evidence = Path('docs/verification/unified-video')
        for size in ('1280x720', '900x640'):
            self.root.geometry(size+'+0+0')
            if not self.app.focus_mode:
                self.app.production.toggle_files()
            self.root.update()
            for tab, controls in ((0, (page.pause_control, page.resolution_control, page.save_button)),
                                  (1, (page.table, page.join_button, page.select_button)),
                                  (2, (page.task_text, page.output_controls.labels['mp4'][3]))):
                page.notebook.select(tab)
                self.root.update()
                for widget in (*controls, page.start_button, page.outputs_button):
                    self.inside(widget)
                ImageGrab.grab(window=int(self.root.frame(), 16)).save(evidence/f'merge-{size}-tab{tab}.png')
        page.start_button.invoke()
        job = page.job
        self.assertIsNotNone(job)
        self.assertFalse(self.app.production.video_switch_allowed())
        self.app.narration()
        self.root.update()
        self.assertIs(page.job, job)
        self.app.production.activate(page)
        self.wait_page(page)
        self.assertIsNotNone(self.flow.total_video(method='batch-videos'))
        self.assertIsNone(self.flow.total_audio())
        page.play()
        deadline = time.monotonic()+15
        while page.movie_player.has_work() and time.monotonic()<deadline:
            self.root.update()
            time.sleep(.02)
        self.assertFalse(page.movie_player.has_work())
        page.movie_player.leave()
        page.notebook.select(1)
        self.root.update()
        self.inside(page.table)
        height = page.table_frame.winfo_height()
        page.toggle_info()
        self.root.update()
        self.assertGreaterEqual(page.info_frame.winfo_height(), height-2)
        page.toggle_info()
        if __import__('os').environ.get('UNIFIED_PACKAGE_FIXTURE'):
            import shutil
            target = Path('.scratch/unified-video-package')
            target.mkdir()
            shutil.copytree(self.flow.root, target/'book')
            home = target/'app'
            home.mkdir()
            (home/'session.json').write_text(json.dumps(dict(last_project=str((target/'book').resolve()))), encoding='utf-8')


if __name__ == '__main__':
    unittest.main()
