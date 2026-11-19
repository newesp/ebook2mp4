"""Approved layout and data retention at the real audio JoinPage seam."""
import json
import os
import time
import unittest
from pathlib import Path
from tkinter import ttk, font
from unittest.mock import patch

from ebook2mp4.workflow import ProjectError, ProjectWorkflow
from ebook2mp4.workspace_layout import TOOLBAR_GAP
from test_assembly_joins_desktop import AssemblyJoinsDesktop

EVIDENCE = Path(os.environ.get('JOIN_QA_EVIDENCE', 'docs/verification/audio-join-workspace'))


class AudioJoinWorkspace(AssemblyJoinsDesktop):
    def setUp(self):
        super().setUp()
        self.callback_errors=[]
        self.root.report_callback_exception=lambda kind,value,tb:self.callback_errors.append(str(value))
        self.addCleanup(lambda:self.assertEqual(self.callback_errors,[]))

    def open_join(self):
        self.app.total_audio()
        p = self.app.production.current
        self.wait_page(p)
        p.select_button.invoke()
        p.join_button.invoke()
        self.wait_join(p.join_page)
        return p, p.join_page

    def test_mock_parent_grid_and_native_red_green(self):
        p, j = self.open_join()
        rows = []
        self.root.state('zoomed');self.root.update()
        for w in (j.left_edit,j.right_edit,j.pause_control,j.play_button,j.save_button):
            self.assertTrue(w.winfo_viewable())
            self.assertLessEqual(w.winfo_rootx()+w.winfo_width(),self.root.winfo_rootx()+self.root.winfo_width())
        from PIL import ImageGrab
        ImageGrab.grab(window=self.root.winfo_id()).save(EVIDENCE/'native-maximized.png')
        for size in ('1360x820', '1280x720', '900x640'):
            for points in (10, 13):
                self.root.state('normal')
                self.root.geometry(size)
                ttk.Style(self.root).configure('.', font=('Microsoft JhengHei', points))
                self.root.update()
                j.workspace.resized()
                self.root.update()
                self.assertEqual(f'{self.root.winfo_width()}x{self.root.winfo_height()}', size)
                peers = (j.pause_control,j.clip_control,j.play_button,j.stop_button)
                sizes = [(w.winfo_width(),w.winfo_height()) for w in peers]
                self.assertEqual(len(set(sizes)),1, (size,points,sizes))
                self.assertEqual(j.left_text.winfo_rooty(),j.right_text.winfo_rooty())
                self.assertEqual(j.left_text.winfo_height(),j.right_text.winfo_height())
                gap = j.stop_button.winfo_rootx()-j.play_button.winfo_rootx()-j.play_button.winfo_width()
                header_gap = j.left_text.winfo_rooty()-j.left_edit.winfo_rooty()-j.left_edit.winfo_height()
                self.assertEqual(gap, TOOLBAR_GAP)
                self.assertEqual(header_gap, 2 * TOOLBAR_GAP)
                self.assertEqual(j.play_button.winfo_rootx(),j.right_text.winfo_rootx())
                line = font.Font(font=j.left_text.cget('font')).metrics('linespace')
                self.assertGreaterEqual(j.left_text.winfo_height(),4*line+26,(size,points,j.left_text.winfo_height(),line))
                for w in (*peers,j.save_button,j.workspace.files_button):
                    if w.winfo_ismapped():
                        self.assertLessEqual(w.winfo_rootx()+w.winfo_width(),self.root.winfo_rootx()+self.root.winfo_width()-8)
                rows.append(dict(size=size,font_points=points,peer_sizes=sizes,playback_gap=gap,header_gap=header_gap,reader=j.left_text.winfo_height(),line_height=line,
                                 dpi=self.root.winfo_fpixels('1i'), scaling=float(self.root.tk.call('tk', 'scaling'))))
        # A regression that only checks existence/visibility would miss this.
        j.stop_button.grid_configure(padx=(6,0))
        self.root.update()
        bad = j.stop_button.winfo_rootx()-j.play_button.winfo_rootx()-j.play_button.winfo_width()
        self.assertNotEqual(bad, TOOLBAR_GAP)
        j.stop_button.grid_configure(padx=(TOOLBAR_GAP,0));self.root.update()
        self.assertEqual(j.stop_button.winfo_rootx()-j.play_button.winfo_rootx()-j.play_button.winfo_width(), TOOLBAR_GAP)
        out=EVIDENCE
        (out/'native-layout-regression.json').write_text(json.dumps(dict(rows=rows,injected_bad_gap=bad,fixed_gap=TOOLBAR_GAP),indent=2),encoding='utf-8')

    def test_disclosures_scroll_and_empty_transitions_preserve_context(self):
        p,j=self.open_join()
        self.root.state('normal');self.root.geometry('1360x820');self.root.update()
        # Use actual warning metadata and keep the source/media checks real.
        ids=self.pdf_batches();self.narrate(ids)
        p.selected=ids;j.load();self.wait_join(j)
        long='\n'.join(f'前批第 {i+1} 行' for i in range(180))
        j.fill(j.left_text,long);self.root.update()
        j.left_text.yview_moveto(1);self.root.update()
        pos=j.left_text.yview()
        right=j.right_text.yview()
        j.workspace.disclosure.invoke();self.root.update()
        self.assertFalse(j.workspace.dedicated)
        self.assertEqual(j.right_text.yview(),right)
        j.workspace.disclosure.invoke();self.root.update()
        self.assertEqual(j.left_text.yview(),pos)
        j.workspace.disclosure.invoke();self.root.update()
        j.next.invoke();self.root.update()
        j.workspace.disclosure.invoke();self.root.update()
        self.assertEqual(j.left_text.yview()[1],1.)
        j.previous.invoke();self.root.update()
        self.root.geometry('900x640');self.root.update()
        j.workspace.disclosure.invoke();self.root.update()
        self.assertTrue(j.workspace.dedicated)
        self.assertFalse(j.pair.winfo_ismapped())
        j.workspace.disclosure.invoke();self.root.update()
        before=j.left_text.yview()
        j.workspace.files_button.invoke();self.root.update()
        self.assertTrue(j.workspace.files_open)
        self.assertFalse(j.save_button.winfo_ismapped())
        j.back_button.invoke();self.root.update()
        self.assertEqual(j.left_text.yview(),before)
        self.assertEqual(p.selected,ids)
        j.fill(j.left_text,'短文');self.root.update()
        self.assertFalse(j.workspace.panes[0].scroll.winfo_ismapped())
        self.assertEqual(j.left_text.yview(),(0.,1.))
        saved=j.joins;j.joins=[];j.render();self.root.update()
        self.assertTrue(j.workspace.empty.winfo_ismapped())
        self.assertFalse(j.workspace.options.winfo_ismapped())
        self.assertFalse(j.workspace.panes[0].scroll.winfo_ismapped())
        j.joins=saved;j.render();self.root.update()
        self.assertTrue(j.pair.winfo_ismapped())

    def test_preview_content_scope_stop_on_edit_and_save_failure(self):
        p,j=self.open_join()
        j.workspace.pause_display.set('0.123 秒')
        self.assertEqual(p.pause_ms(),123)
        with patch('ebook2mp4.voice_media.PreviewPlayer._send', return_value='playing'):
            j.play_button.invoke()
            deadline=time.monotonic()+20
            while not j.playing and time.monotonic()<deadline:
                self.root.update();time.sleep(.02)
            self.assertTrue(j.playing,j.status.cget('text'))
            self.assertEqual(j.content_kind,'subtitle')
            j.stop_button.invoke();self.root.update()
            self.assertIn('字幕',j.headings[0].cget('text'))
            j.play_button.invoke()
            while not j.playing and time.monotonic()<deadline:
                self.root.update();time.sleep(.02)
            j.workspace.pause_display.set('0.5 秒')
            self.assertFalse(j.playing)
            self.assertIsNone(j.player.alias)
        with patch.object(p,'save_settings',side_effect=ProjectError('磁碟已滿')):
            j.save_button.invoke();self.root.update()
        self.assertTrue(j.winfo_ismapped())
        self.assertEqual(p.pause.get(),'0.5')
        self.assertIn('重試',j.save_button.cget('text'))
        from PIL import ImageGrab
        ImageGrab.grab(window=self.root.winfo_id()).save(EVIDENCE/'native-save-failed.png')
        j.workspace.pause_display.set('5.001 秒');self.root.update()
        self.assertTrue(j.save_button.instate(['disabled']))
        self.assertTrue(j.play_button.instate(['disabled']))
        j.workspace.pause_display.set('0.123 秒');self.root.update()
        j.save_button.invoke();self.wait_page(p)
        self.assertEqual(ProjectWorkflow.open(self.flow.root).assembly_settings()['pause_ms'],123)

    def test_native_scroll_owners_and_short_fit_overflow_contract(self):
        p,j=self.open_join();ws=j.workspace
        j.cancel_reading_restore()
        self.root.state('normal');self.root.geometry('900x640');self.root.update()
        size = f'{self.root.winfo_width()}x{self.root.winfo_height()}'
        self.assertEqual(size, '900x640')
        records=[]
        def exercise(text,scroll,owner):
            line=font.Font(font=text.cget('font')).metrics('linespace')
            outer=text.winfo_height()-2*int(text.cget('borderwidth'))
            padding=2*int(text.cget('pady'))
            viewport=outer-padding
            fit=max(1,viewport//line)
            for state,count in [('short',1),('fit',fit),('overflow',fit+1),('long',180)]:
                j.fill(text,'\n'.join(f'{owner}第 {i+1} 行' for i in range(count)))
                text.yview_moveto(0);self.root.update()
                measured=text.count('1.0','end','update','ypixels')
                content=measured[0] if isinstance(measured,tuple) else measured
                visible=bool(scroll.winfo_ismapped())
                self.assertEqual(visible,content>viewport,(owner,state,viewport,content))
                start=text.yview();text.yview_moveto(1);self.root.update()
                self.assertEqual(text.yview()[1],1.)
                records.append(dict(owner=owner,state=state,viewport_height=viewport,content_height=content,scrollbar_visible=visible,first=start,end=text.yview()))
        for pane,label in zip(ws.panes,('前批','後批')):exercise(pane.text,pane.scroll,label)
        j.fill(j.left_text,'短文');j.fill(j.right_text,'短文');self.root.update()
        self.assertFalse(ws.panes[0].scroll.winfo_ismapped())
        ws.warning_data={'kind':'overlap'};ws.details_open=True;ws.resized();self.root.update()
        exercise(ws.detail_text,ws.detail_scroll,'警告詳情')
        ws.show_files();self.root.update()
        row=int(ttk.Style(self.root).lookup('Manuscript.Treeview','rowheight'))
        fit=max(1,(ws.file_list.winfo_height()-4)//row)
        for state,count in [('short',1),('fit',fit),('overflow',fit+1),('long',40)]:
            ws.file_list.delete(*ws.file_list.get_children())
            for i in range(count):ws.file_list.insert('','end',text=f'第 {i+1} 章')
            self.root.update();visible=bool(ws.file_scroll.winfo_ismapped())
            self.assertEqual(visible,state in ('overflow','long'))
            start=ws.file_list.yview();ws.file_list.yview_moveto(1);self.root.update()
            self.assertEqual(ws.file_list.yview()[1],1.)
            records.append(dict(owner='文件列表',state=state,rows=count,rowheight=row,viewport_height=fit*row,content_height=count*row,widget_height=ws.file_list.winfo_height(),scrollbar_visible=visible,first=start,end=ws.file_list.yview()))
        (EVIDENCE/'native-scroll.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
        regions=[]
        for r in records:
            item=dict(page='檢查接點',size=size,state=r['state'],owner=r['owner'],direction='vertical',
                      viewport_height=r['viewport_height'],content_height=r['content_height'],scrollbar_visible=r['scrollbar_visible'],
                      max_offset=r['end'][0]*r['content_height'],measurement_source='test_audio_join_workspace: native Text.count(ypixels), padding and font; Treeview whole-row viewport; actual Tk yview',
                      dpi=self.root.winfo_fpixels('1i'),scaling=float(self.root.tk.call('tk', 'scaling')))
            if r['scrollbar_visible']:
                item['thumb_fraction']=r['first'][1]-r['first'][0]
                self.assertAlmostEqual(item['thumb_fraction'],r['viewport_height']/r['content_height'])
            regions.append(item)
        (EVIDENCE/'scroll-contract.json').write_text(json.dumps(dict(coverage_complete=True,regions=regions),ensure_ascii=False,indent=2),encoding='utf-8')

    def test_file_selection_uses_existing_document_command_without_changing_join_order(self):
        p,j=self.open_join();order=list(p.selected)
        j.workspace.show_files();self.root.update()
        j.workspace.file_list.selection_set(self.ids[1]);self.root.update()
        self.assertEqual(self.app.batch_id,self.ids[1])
        self.assertEqual(p.selected,order)
        self.assertTrue(j.workspace.files_open)
        j.back_button.invoke();self.root.update()
        self.assertTrue(j.pair.winfo_ismapped())


if __name__=='__main__':unittest.main()
