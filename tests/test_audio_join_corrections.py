"""Regression for the two shell anchors, source endpoints and saved state."""
import json
import os
import time
from pathlib import Path
from tkinter import ttk
from unittest.mock import patch

import test_audio_join_workspace as fixture
from ebook2mp4.workflow import ProjectError

EVIDENCE = Path(os.environ.get('JOIN_QA_EVIDENCE', 'docs/verification/audio-join-corrections'))


class JoinCorrections(fixture.AudioJoinWorkspace):
    def setUp(self):
        super().setUp()
        # Never write a fixture into the user's remembered-session file.
        self.app.remember_project=lambda:None

    def shutdown(self):
        # The tests deliberately leave settings dirty and exercise failures.
        # Permit normal owned-window shutdown without a discard modal.
        with patch('tkinter.messagebox.askyesnocancel', return_value=False):
            super().shutdown()
    def settle(self):
        deadline = time.monotonic()+.45
        while time.monotonic() < deadline:
            self.root.update()
            time.sleep(.015)

    def anchors(self, j):
        def box(w):
            return [w.winfo_rootx(), w.winfo_rooty(), w.winfo_width(), w.winfo_height()]
        return dict(left_header=box(self.app.list_header), right_header=box(j.workspace.header),
                    title=box(j.workspace.title), left_content=box(self.app.shell.documents.batch_view),
                    right_content=box(j.workspace.main))

    def test_shared_header_and_content_anchors(self):
        ids=self.pdf_batches();self.narrate(ids)
        self.app.batch_id=ids[0];self.app.refresh()
        p,j = self.open_join()
        records=[]
        failures=[]
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        for size in ('zoomed','1360x820','1280x720','900x640'):
            for points in (10,13):
                if size == 'zoomed':
                    self.root.state('zoomed')
                else:
                    self.root.state('normal'); self.root.geometry(size)
                ttk.Style(self.root).configure('.', font=('Microsoft JhengHei',points))
                self.settle()
                for files in (True, False, True):
                    if self.app.focus_mode == files:
                        self.app.toggle_focus()
                    # Exercise the outer layout last; never mask it with a
                    # manual call to the inner workspace's resized handler.
                    for _ in range(2):
                        self.app.layout_workspace();self.settle()
                    b=self.anchors(j)
                    record=dict(size=size,font=points,files=files,boxes=b,
                                actual_size=f'{self.root.winfo_width()}x{self.root.winfo_height()}',
                                dpi=self.root.winfo_fpixels('1i'),scaling=float(self.root.tk.call('tk', 'scaling')),
                                max_difference=2)
                    records.append(record)
                    if files and self.app.shell.documents.winfo_ismapped():
                        lh,rh=b['left_header'],b['right_header']
                        lc,rc=b['left_content'],b['right_content']
                        delta=[rh[1]-lh[1],rh[3]-lh[3],rc[1]-lc[1]]
                        title_center=b['title'][1]+b['title'][3]/2
                        control=self.app.shell.documents.import_control
                        control_center=control.winfo_rooty()+control.winfo_height()/2
                        record['deltas']=delta+[title_center-control_center]
                        if max(abs(v) for v in record['deltas'])>2:
                            failures.append(record)
        (EVIDENCE/'shell-anchors.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
        self.assertEqual(failures,[],str(failures[:2]))

    def test_initial_endpoints_and_retained_reading(self):
        p,j=self.open_join()
        ids=self.pdf_batches();self.narrate(ids)
        p.selected=ids;j.load();self.wait_join(j)
        # Long real source data passed through the renderer, not direct yview
        # assertions on manually filled readers.
        for join in j.joins:
            for side in ('left','right'):
                join[side]['text']='\n'.join(f'{side} 第 {i} 行' for i in range(180))
        j.render();self.settle()
        self.assertAlmostEqual(j.left_text.yview()[1],1.)
        self.assertEqual(j.right_text.yview()[0],0.)
        j.cancel_reading_restore()
        j.left_text.yview_moveto(.4);j.right_text.yview_moveto(.2);self.settle()
        positions=(j.left_text.yview()[0],j.right_text.yview()[0])
        j.next.invoke();self.settle()
        self.assertAlmostEqual(j.left_text.yview()[1],1.)
        self.assertEqual(j.right_text.yview()[0],0.)
        j.previous.invoke();self.settle()
        for actual,expected in zip((j.left_text.yview()[0],j.right_text.yview()[0]),positions):
            self.assertAlmostEqual(actual,expected,places=3)
        j.workspace.toggle_details();self.settle()
        j.workspace.toggle_details();self.settle()
        self.assertAlmostEqual(j.left_text.yview()[0],positions[0],places=3)

    def test_first_load_long_real_sources_after_footer_layout(self):
        ids=self.pdf_batches()
        for i,b in enumerate(ids):
            self.flow.save_draft(b,'\n'.join(f'第{i+1}章第{n+1}行，接點閱讀與捲動檢查。' for n in range(90)))
        self.narrate(ids)
        self.flow.save_assembly_settings(ids)
        self.app.batch_id=ids[0];self.app.refresh()
        self.root.state('normal');self.root.geometry('1360x820');self.settle()
        self.app.total_audio();p=self.app.production.current;self.wait_page(p)
        p.join_button.invoke();j=p.join_page;self.wait_join(j);self.settle()
        record=dict(left=j.left_text.yview(),right=j.right_text.yview(),
                    last_line=j.left_text.dlineinfo('end-1c'),height=j.left_text.winfo_height(),
                    pending=j._reading_timer,font=j.left_text.cget('font'))
        (EVIDENCE/'first-load-endpoints.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
        self.assertAlmostEqual(j.left_text.yview()[1],1.)
        self.assertEqual(j.right_text.yview()[0],0.)
        line=j.left_text.dlineinfo('end-1c')
        self.assertIsNotNone(line)
        self.assertLessEqual(line[1]+line[3],j.left_text.winfo_height())

    def test_release_cancels_pending_reading_callback(self):
        p,j=self.open_join()
        j.joins[0]['left']['text']='\n'.join(f'前批第{i}行' for i in range(180))
        j.render()
        timer=j._reading_timer
        self.assertIsNotNone(timer)
        self.assertIn(timer,self.root.tk.call('after','info'))
        j.release()
        self.assertIsNone(j._reading_timer)
        self.assertIsNone(j._reading_restore)
        self.assertNotIn(timer,self.root.tk.call('after','info'))

    def test_saved_dirty_reverted_failed_and_reloaded(self):
        p,j=self.open_join()
        self.assertIn('尚未儲存',j.workspace.saved.cget('text'))
        j.save_button.invoke();self.wait_page(p)
        p.join_button.invoke();self.wait_join(j);self.settle()
        self.assertIn('已儲存',j.workspace.saved.cget('text'))
        p.pause.set('0.123');self.settle()
        self.assertIn('尚未儲存',j.workspace.saved.cget('text'))
        p.pause.set('0.5');self.settle()
        self.assertIn('已儲存',j.workspace.saved.cget('text'))
        p.pause.set('0.123');self.settle()
        with patch.object(p,'save_settings',side_effect=ProjectError('磁碟已滿')):
            j.save_button.invoke();self.settle()
        self.assertIn('儲存失敗',j.workspace.saved.cget('text'))
        self.assertTrue(j.winfo_ismapped())
        self.assertEqual(p.pause.get(),'0.123')
        j.save_button.invoke();self.wait_page(p)
        p.join_button.invoke();self.wait_join(j);self.settle()
        self.assertIn('已儲存',j.workspace.saved.cget('text'))
        self.assertNotIn('重試',j.save_button.cget('text'))
        p.pause.set('0.234');self.settle()
        with patch.object(p,'save_settings',side_effect=ProjectError('磁碟已滿')):
            j.save_button.invoke();self.settle()
        j.back_button.invoke();self.settle()
        p.save_button.invoke();self.wait_page(p)
        p.join_button.invoke();self.wait_join(j);self.settle()
        self.assertIn('已儲存',j.workspace.saved.cget('text'))
        self.assertNotIn('重試',j.save_button.cget('text'))
