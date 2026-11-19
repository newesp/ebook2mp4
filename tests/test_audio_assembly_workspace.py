"""Regression at the real audio workspace: routing, geometry and publication."""
import json
import time
import unittest
from unittest.mock import patch
from tkinter import ttk,font

from ebook2mp4.workflow import ProjectError, ProjectWorkflow
from test_total_audio_desktop import TotalAudioDesktop


class AudioAssemblyWorkspace(TotalAudioDesktop):
    # Keep inherited media journeys and add assertions across the actual seam.
    def open_audio(self):
        self.app.total_audio()
        page=self.app.production.current
        if page.check_job is not None:self.assertIn('正在檢查',page.assembly_workspace.empty_label.cget('text'))
        self.wait_page(page)
        return page

    def test_video_preferences_cannot_redirect_or_start_video(self):
        self.flow.save_total_video_method('batch-videos')
        self.flow.save_output_formats(['mp4'])
        page=self.open_audio()
        self.assertFalse(page.movie)
        self.assertIsNone(page.output_controls)
        self.assertFalse(self.app.production.method_control.winfo_ismapped())
        page.select_button.invoke();page.save_button.invoke();self.wait_page(page)
        with patch.object(self.flow,'start_outputs',side_effect=AssertionError('no multi-format coordinator')), \
             patch.object(self.flow,'start_video_merge',side_effect=AssertionError('no video merge')), \
             patch.object(self.flow,'start_total_video',side_effect=AssertionError('no video encoder')):
            page.start_button.invoke();self.wait_page(page)
        self.assertIsNotNone(self.flow.total_audio())
        self.root.update()
        menu=page.outputs_button
        needed=font.Font(font=ttk.Style(self.root).lookup(menu.cget('style'),'font')).measure(menu.cget('text'))
        def label_width():return sum(menu.identify(x,menu.winfo_height()//2)=='label' for x in range(menu.winfo_width()))
        actual=label_width()
        self.assertGreaterEqual(actual,needed)
        menu.configure(width=1);self.root.update()
        defective=label_width()
        self.assertLess(defective,needed)
        menu.configure(width=0);self.root.update()
        self.assertGreaterEqual(label_width(),needed)
        print(f'Native menu caption: outer={menu.winfo_width()}, required={needed}, old-label={defective}, fixed-label={actual}',flush=True)
        self.assertEqual(self.flow.output_formats(),['mp4'])
        self.assertEqual(self.flow.state['total_video_method'],'batch-videos')
        self.app.production.video_tab.invoke()
        self.assertTrue(self.app.production.current.movie)
        self.app.production.assembly_tab.invoke()
        self.assertIs(self.app.production.current,page)

    def test_publication_failure_retries_same_completed_media(self):
        page=self.open_audio();page.select_button.invoke()
        original=self.flow.finish_total_audio
        with patch.object(self.flow,'finish_total_audio',side_effect=ProjectError('模擬保存失敗')):
            page.start_button.invoke()
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                self.root.update();time.sleep(.02)
                if page.job is not None and page.job.wait(0) and page.start_button.cget('text')=='重試保存':break
            self.assertIsNotNone(page.job)
            job=page.job
            self.assertEqual(page.start_button.cget('text'),'重試保存')
        with patch.object(self.flow,'start_total_audio',side_effect=AssertionError('must reuse completed job')):
            page.start_button.invoke();self.root.update()
        self.assertIsNone(page.job)
        self.assertIsNotNone(self.flow.total_audio())

    def test_mock_alignment_scroll_geometry_and_footer_at_supported_sizes(self):
        page=self.open_audio();layout=page.assembly_workspace
        for geometry in ('1360x820','1280x720','900x640'):
            self.root.state('normal');self.root.geometry(geometry)
            self.root.update()
            self.app.layout_workspace();self.root.update()
            if not self.app.focus_mode:
                self.assertLessEqual(abs(self.app.batch_list.winfo_rooty()-page.main.winfo_rooty()),2)
            if geometry.startswith('900'):
                self.assertTrue(self.app.focus_mode)
                self.assertTrue(layout.files_button.winfo_ismapped())
            # Full layout geometry, not style names or control-existence checks.
            controls=(*layout.source_buttons,page.pause_control,layout.result_state,page.join_button,layout.detail_button,page.versions_button)
            self.assertLessEqual(max(c.winfo_height() for c in controls)-min(c.winfo_height() for c in controls),2)
            self.assertEqual(page.pause_control.winfo_rootx(),layout.result_state.winfo_rootx())
            self.assertEqual(page.pause_control.winfo_width(),layout.result_state.winfo_width())
            self.assertEqual(page.join_button.winfo_rootx(),layout.detail_button.winfo_rootx())
            for left,right in zip(layout.source_buttons,layout.source_buttons[1:]):
                self.assertEqual(right.winfo_rootx()-left.winfo_rootx()-left.winfo_width(),4)
            self.assertEqual(page.versions_button.winfo_rootx()-layout.detail_button.winfo_rootx()-layout.detail_button.winfo_width(),4)
            self.assertEqual(page.table_frame.winfo_rooty()-layout.toolbar.winfo_rooty()-layout.toolbar.winfo_height(),8)
            self.assertEqual(page.start_button.winfo_rootx()-page.save_button.winfo_rootx()-page.save_button.winfo_width(),4)
            self.assertGreaterEqual(page.table.winfo_height(),180)
            self.assertLessEqual(page.versions_button.winfo_rootx()+page.versions_button.winfo_width(),self.root.winfo_rootx()+self.root.winfo_width())
        self.assertFalse(layout.table_scroll.winfo_ismapped())
        saved=[dict(r) for r in page.rows]
        page.rows=[dict(saved[0],batch_id=f'long-{i}',name=f'第 {i} 章') for i in range(80)]
        page.render_rows();self.root.update()
        self.assertTrue(layout.table_scroll.winfo_ismapped())
        fixed=(page.join_button.winfo_rooty(),page.start_button.winfo_rooty())
        page.table.yview_moveto(1);self.root.update()
        self.assertEqual(page.table.yview()[1],1)
        page.info_button.invoke();page.info_button.invoke();self.root.update()
        self.assertEqual(page.table.yview()[1],1)
        self.assertEqual(fixed,(page.join_button.winfo_rooty(),page.start_button.winfo_rooty()))
        page.rows=saved;page.render_rows();self.root.update()
        self.assertFalse(layout.table_scroll.winfo_ismapped())
        self.assertEqual(page.table.yview(),(0.,1.))
        # Reopening the secondary pane must not clip the primary grid.
        layout.files_button.invoke();self.root.update()
        self.assertFalse(self.app.focus_mode)
        for size in (10,13):
            ttk.Style(self.root).configure('.',font=('Microsoft JhengHei',size))
            self.root.update()
            for widget in (*layout.source_buttons,page.versions_button,page.start_button):
                self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(),self.root.winfo_rootx()+self.root.winfo_width()-8,
                    dict(size=size,text=widget.cget('text'),root=self.root.geometry(),main=page.main.winfo_width(),
                         widths=[b.winfo_width() for b in layout.source_buttons],columns=[layout.toolbar.grid_columnconfigure(c) for c in (0,1,3,5,7)]))
            self.assertGreaterEqual(page.table.winfo_height(),180)
        page.selected=[];page.rows=[];page.render_rows();self.root.update()
        self.assertTrue(layout.empty_label.winfo_ismapped())
        self.assertFalse(layout.table_scroll.winfo_ismapped())
        self.assertEqual(page.table.yview(),(0.,1.))
        documents=self.app.shell.documents
        self.assertIs(self.root.winfo_containing(self.app.batch_list.winfo_rootx()+30,
                                                self.app.batch_list.winfo_rooty()+20),self.app.batch_list)
        original=self.app.batch_list.get_children()
        self.assertFalse(documents.batch_scroll.winfo_ismapped())
        for i in range(40):self.app.batch_list.insert('', 'end',iid=f'scroll-fixture-{i}',text=f'長列表第 {i+1} 章')
        self.root.update()
        self.assertTrue(documents.batch_scroll.winfo_ismapped())
        self.app.batch_list.yview_moveto(1);self.root.update()
        self.assertEqual(self.app.batch_list.yview()[1],1.)
        self.app.batch_list.delete(*(i for i in self.app.batch_list.get_children() if i not in original));self.root.update()
        self.assertFalse(documents.batch_scroll.winfo_ismapped())


if __name__=='__main__':unittest.main()
