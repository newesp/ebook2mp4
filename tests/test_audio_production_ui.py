"""Audio workspace space budgets, retained inspection and task safety."""
import copy
import time
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
import unittest
from unittest.mock import patch

import test_narration_desktop as fixture
from ebook2mp4.workflow import ProjectError


class AudioProductionWorkspace(unittest.TestCase):
    setUp=fixture.NarrationDesktop.setUp
    poll=fixture.NarrationDesktop.poll

    def long_source(self):
        self.flow.save_draft(self.batch,'\n\n'.join(f'第 {i:03d} 段。這是長稿件的獨立區塊。' for i in range(1,174)))
        self.flow.confirm_reading(self.batch)
        self.dialog.reload_button.invoke()
        self.poll()
        self.assertEqual(len(self.dialog.details.get_children()),173)

    def assert_inside(self,widget):
        self.assertTrue(widget.winfo_ismapped(),str(widget))
        self.assertGreaterEqual(widget.winfo_rootx(),self.root.winfo_rootx())
        self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(),self.root.winfo_rootx()+self.root.winfo_width())
        self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),self.root.winfo_rooty()+self.root.winfo_height())

    def test_toolbar_controls_align_and_product_menu_has_one_native_indicator(self):
        for width,height in ((1536,864),(1280,720),(900,640)):
            with self.subTest(width=width,height=height):
                self.root.state('normal')
                self.root.geometry(f'{width}x{height}+0+0')
                self.root.update()
                choice,peer=self.dialog.run_control,self.dialog.info_button
                self.assert_inside(choice)
                self.assert_inside(peer)
                self.assertLessEqual(abs(choice.winfo_height()-peer.winfo_height()),2)
                self.assertLessEqual(abs(choice.winfo_rooty()-peer.winfo_rooty()),2)
                self.assertLessEqual(abs(choice.winfo_rooty()+choice.winfo_height()-
                                         peer.winfo_rooty()-peer.winfo_height()),2)
                self.assertEqual(choice.cget('style'),'Workspace.TCombobox')
                menu=self.dialog.output_button
                self.assert_inside(menu)
                # Inspect the rendered native element hit regions, rather than
                # assuming a plain label implies that an arrow was drawn.
                indicators=['indicator' in str(menu.identify(x,menu.winfo_height()//2)).lower()
                            for x in range(menu.winfo_width())]
                groups=sum(value and (index==0 or not indicators[index-1])
                           for index,value in enumerate(indicators))
                self.assertEqual(groups,1)
                label=str(menu.cget('text'))
                manual_indicators=sum(label.count(glyph) for glyph in '▾▿▼▽⌄')
                self.assertEqual(groups+manual_indicators,1)
                self.assertEqual(label,'成品操作')

    def test_approved_header_footer_and_notebook_at_supported_sizes(self):
        self.long_source()
        for width,height in ((1360,820),(900,640)):
            with self.subTest(width=width):
                self.root.state('normal')
                self.root.geometry(f'{width}x{height}+0+0')
                self.root.update()
                self.app.layout_workspace()
                self.root.update()
                peers=(self.app.production.voice_tab,self.app.production.narration_tab,
                       self.app.production.assembly_tab,self.app.steps[1],self.app.focus_button)
                heights=[w.winfo_height() for w in peers]
                self.assertLessEqual(max(heights)-min(heights),2)
                if width==1360:
                    self.assertAlmostEqual(peers[0].winfo_rooty(),self.app.steps[1].winfo_rooty(),delta=2)
                self.assertAlmostEqual(self.dialog.run_control.winfo_rooty(),self.app.focus_button.winfo_rooty(),delta=2)
                self.assertLess(self.dialog.actions.winfo_rootx(),self.dialog.winfo_rootx())
                for widget in (self.dialog.play_button,self.dialog.output_button,self.dialog.video_button,
                               self.dialog.start_button,self.dialog.back_button):
                    self.assert_inside(widget)
                order=(self.dialog.play_button,self.dialog.start_button,self.dialog.output_button,self.dialog.video_button)
                for left,right in zip(order,order[1:]):
                    self.assertLessEqual(left.winfo_rootx()+left.winfo_width(),right.winfo_rootx())
                self.dialog.info_button.invoke()
                self.root.update()
                self.assertIsInstance(self.dialog.info_tabs,ttk.Notebook)
                self.assertEqual(self.dialog.info_button.cget('text'),'← 返回區塊清單')
                self.assertEqual([w for w in self.dialog.winfo_children()
                                  if isinstance(w,ttk.Button) and '返回區塊清單' in w.cget('text')],[])
                consent,recheck,details=self.dialog.consent_control,self.dialog.reload_button,self.dialog.status_button
                self.assertLess(consent.winfo_rootx()+consent.winfo_width(),details.winfo_rootx())
                self.assertLess(details.winfo_rootx(),recheck.winfo_rootx())
                self.assertAlmostEqual(consent.winfo_rooty()+consent.winfo_height()/2,
                                       recheck.winfo_rooty()+recheck.winfo_height()/2,delta=2)
                for widget in (consent,recheck,details,self.dialog.outgoing):
                    self.assert_inside(widget)
                font=tkfont.Font(font=self.dialog.outgoing.cget('font'))
                self.assertGreaterEqual(self.dialog.outgoing.winfo_height(),8*font.metrics('linespace'))
                # The reclaimed region belongs to the editor, not an empty row.
                self.assertLessEqual(self.dialog.info_frame.winfo_rooty()+self.dialog.info_frame.winfo_height(),
                                     self.dialog.status_row.winfo_rooty())
                self.assertLessEqual(self.dialog.status_row.winfo_rooty()+self.dialog.status_row.winfo_height(),
                                     self.app.actions.winfo_rooty())
                self.dialog.info_button.invoke()

    def test_same_play_button_stops_finishes_and_recovers_from_failure(self):
        player=self.dialog.player
        self.dialog.play_button.configure(state='normal')
        with patch.object(self.flow,'narration_path',return_value=self.path/'fixture.mp3'), \
             patch.object(player,'play') as play,patch.object(player,'stop') as stop, \
             patch.object(player,'playing',return_value=True) as playing:
            self.dialog.play_button.invoke()
            self.assertEqual(self.dialog.play_button.cget('text'),'停止播放')
            self.dialog.play_button.invoke()
            stop.assert_called_once()
            self.assertEqual(self.dialog.play_button.cget('text'),'播放成品')
            self.dialog.play_button.invoke()
            self.dialog.info_button.invoke()
            self.dialog.info_tabs.select(self.dialog.message_frame)
            self.root.update()
            self.assertEqual(self.dialog.play_button.cget('text'),'停止播放')
            playing.return_value=False
            class Running:
                state=dict(status='running',chunks=[])
                def wait(self,timeout): return False
            self.dialog.job=Running()
            try:
                self.dialog.poll()
            finally:
                self.dialog.job=None
            self.assertEqual(self.dialog.play_button.cget('text'),'播放成品')
            play.side_effect=ProjectError('模擬播放失敗')
            self.dialog.play_button.invoke()
            self.assertEqual(self.dialog.play_button.cget('text'),'播放成品')
            self.assertIn('播放失敗',self.dialog.status.cget('text'))
            self.assertFalse(self.dialog.playback_active)
        self.app.voice_settings()
        self.root.update()
        self.assertFalse(self.dialog.actions.winfo_ismapped())
        self.app.narration()
        self.poll()
        self.assertTrue(self.dialog.actions.winfo_ismapped())

    def test_summary_reclaims_status_column_but_keeps_errors_visible(self):
        self.app.status.configure(text='已載入專案 · 原始來源檔不會被改寫')
        self.root.update()
        self.assertFalse(self.app.status.winfo_ismapped())
        self.assertEqual(int(self.app.stats.grid_info()['columnspan']),2)
        self.app.report(ProjectError('模擬儲存失敗，請檢查資料夾。'))
        self.root.update()
        self.assertTrue(self.app.status.winfo_ismapped())
        self.assertEqual(int(self.app.status.grid_info()['columnspan']),2)
        self.assertLessEqual(self.app.status.winfo_rooty()+self.app.status.winfo_height(),
                             self.dialog.actions.winfo_rooty())
        self.assertIn('模擬儲存失敗',self.app.status.history[-1])

    def test_background_task_track_never_covers_footer_and_releases_space(self):
        class Active:
            state=dict(status='running',phase='驗證音訊區塊',completed=134,total=251)
            def wait(self,timeout): return False
        production=self.app.production
        self.dialog.job=Active()
        try:
            production.refresh_task_banner()
            self.root.update()
            self.assertFalse(production.task_button.winfo_ismapped())
            self.app.show_step(1)
            self.root.update()
            self.assertTrue(production.task_button.winfo_ismapped())
            self.assertLessEqual(production.task_bar.winfo_rooty()+production.task_bar.winfo_height(),
                                 self.app.actions.winfo_rooty())
            height=self.app.body.winfo_height()
            self.dialog.job=None
            production.refresh_task_banner()
            self.root.update()
            self.assertFalse(production.task_bar.winfo_ismapped())
            self.assertGreater(self.app.body.winfo_height(),height)
            self.app.narration()
            self.poll()
        finally:
            self.dialog.job=None

    def test_primary_list_budget_busy_controls_and_minimum_fallback(self):
        self.long_source()
        class Active:
            state=dict(status='running')
            def wait(self,timeout): return False
        self.dialog.job=Active()
        try:
            self.dialog.update_controls()
            for width,height,minimum in ((1536,864,6),(1280,720,4),(900,640,1)):
                with self.subTest(width=width,height=height):
                    self.root.state('normal')
                    self.root.geometry(f'{width}x{height}+0+0')
                    self.root.update()
                    table=self.dialog.details
                    full=[row for row in table.get_children() if table.bbox(row)
                          and table.bbox(row)[1]+table.bbox(row)[3]<=table.winfo_height()]
                    self.assertGreaterEqual(len(full),minimum)
                    for widget in (table,self.dialog.start_button,self.dialog.cancel_button,
                                   self.dialog.output_button,self.dialog.back_button,self.dialog.restart_button,
                                   self.dialog.consent_control):
                        self.assert_inside(widget)
                    self.assertEqual(table.xview(),(0.0,1.0))
            self.dialog.run=dict(snapshot=self.dialog.inspection['snapshot'],published=False,stale=True,settings_changed=True)
            self.dialog.update_controls()
            self.root.update()
            for widget in (self.dialog.restore_button,self.dialog.run_control,self.dialog.info_button):
                self.assert_inside(widget)
            self.assertGreater(self.dialog.run_control.winfo_width(),80)
        finally:
            self.dialog.job=None
            self.dialog.run=None
            self.dialog.update_controls()

    def test_source_and_navigation_retain_selection_scroll_and_parent_tab(self):
        self.long_source()
        table=self.dialog.details
        table.selection_set(table.get_children()[119])
        table.see(table.get_children()[119])
        self.root.update()
        selected_index=table.index(table.selection()[0])
        position=table.yview()[0]
        for _ in range(2):
            self.dialog.info_button.invoke()
            self.root.update()
            self.assertTrue(self.dialog.outgoing.winfo_ismapped())
            self.assertFalse(table.winfo_ismapped())
            self.assertEqual(self.app.production.narration_tab.cget('style'),'Primary.TButton')
            self.assertEqual(self.dialog.outgoing.get('1.0','end-1c'),self.flow.reading_text(self.batch))
            self.dialog.outgoing.yview_moveto(.75)
            self.root.update()
            source_position=self.dialog.outgoing.yview()[0]
            self.dialog.info_button.invoke()
            self.root.update()
            self.assertEqual(table.index(table.selection()[0]),selected_index)
            self.assertAlmostEqual(table.yview()[0],position,places=2)
        self.dialog.info_button.invoke()
        self.root.update()
        self.assertAlmostEqual(self.dialog.outgoing.yview()[0],source_position,places=2)
        self.dialog.info_button.invoke()
        self.app.voice_settings()
        self.app.narration()
        self.poll()
        self.assertEqual(table.index(table.selection()[0]),selected_index)
        self.assertAlmostEqual(table.yview()[0],position,places=2)
        self.root.update()
        table.focus_force()
        table.event_generate('<Control-End>')
        self.root.update()
        self.assertTrue(table.bbox(table.get_children()[-1]))
        table.event_generate('<Control-Home>')
        self.root.update()
        table.event_generate('<MouseWheel>',delta=-1200)
        self.root.update()
        self.assertGreater(table.yview()[0],0)
        self.flow.save_voice_settings('zh-TW-TestNeural','+10%',batch_id=self.batch)
        self.app.voice_settings()
        self.app.narration()
        self.poll()
        self.assertEqual(table.selection(),())
        self.assertEqual(table.yview()[0],0)

    def test_sidebar_releases_track_and_reopens_from_audio_page(self):
        self.root.state('normal')
        self.root.geometry('1280x720+0+0')
        self.root.update()
        before=self.dialog.winfo_width()
        self.app.toggle_focus()
        self.root.update()
        self.assertGreater(self.dialog.winfo_width(),before+100)
        self.assertFalse(self.app.left_panel.winfo_ismapped())
        self.assert_inside(self.dialog.files_button)
        self.dialog.files_button.invoke()
        self.root.update()
        self.assertTrue(self.app.left_panel.winfo_ismapped())
        self.assertFalse(self.dialog.files_button.winfo_ismapped())
        self.assertAlmostEqual(self.dialog.winfo_width(),before,delta=2)

    def test_multiline_failure_stays_one_line_and_full_message_is_reachable(self):
        self.long_source()
        self.root.update()
        height=self.dialog.details.winfo_height()
        message='模擬保存失敗。\n'+('請保留已完成區塊。\n'*30)
        self.dialog.status.configure(text=message)
        self.root.update()
        self.assertEqual(self.dialog.details.winfo_height(),height)
        self.dialog.info_button.invoke()
        self.dialog.info_tabs.select(self.dialog.message_frame)
        self.root.update()
        self.assertTrue(self.dialog.message_text.get('1.0','end-1c').startswith(message))
        self.dialog.info_button.invoke()
        self.dialog.status_button.invoke()
        self.root.update()
        self.assertTrue(self.dialog.message_text.get('1.0','end-1c').startswith(message))
        self.assertEqual(self.app.production.narration_tab.cget('style'),'Primary.TButton')
        self.dialog.info_button.invoke()
        self.root.update()
        self.assertTrue(self.dialog.details.winfo_ismapped())

    def test_audio_owns_primary_action_and_other_pages_restore_shared_action(self):
        self.assertFalse(self.app.next_button.winfo_ismapped())
        self.dialog.info_button.invoke()
        self.root.update()
        self.assertFalse(self.app.next_button.winfo_ismapped())
        self.app.voice_settings()
        self.root.update()
        self.assertFalse(self.app.next_button.winfo_ismapped())
        self.assertTrue(self.app.voice_dialog.voice_footer.winfo_ismapped())
        self.assertEqual(self.app.voice_dialog.produce_button.cget('text'),'前往音訊製做 →')
        self.assertEqual(self.app.production.narration_tab.cget('text'),'音訊製做')
        self.app.narration()
        self.poll()
        self.assertFalse(self.app.next_button.winfo_ismapped())
        self.app.show_step(1)
        self.root.update()
        self.assertTrue(self.app.next_button.winfo_ismapped())

    def test_no_product_keeps_video_entry_and_product_menu_gates_media(self):
        self.assertIsNone(self.flow.narration(self.batch))
        for index in (0,1,2,3):
            self.assertEqual(self.dialog.output_menu.entrycget(index,'state'),'disabled')
        self.assertEqual(self.dialog.output_menu.entrycget(5,'state'),'normal')
        self.assertFalse(self.dialog.video_button.instate(['disabled']))
        with patch.object(self.app,'batch_video') as navigate:
            # The button's existing callback is intentionally a real navigation
            # route; replace its command to verify the menu dispatches it.
            self.dialog.video_button.configure(command=navigate)
            self.dialog.output_menu.invoke(5)
            navigate.assert_called_once()

    def test_historical_snapshot_stale_guard_and_local_consent_context(self):
        self.flow.confirm_reading(self.batch)
        self.dialog.reload_button.invoke()
        self.poll()
        original_text=self.dialog.source_text
        original_settings=copy.deepcopy(self.dialog.source_settings)
        run=dict(snapshot=dict(id='snapshot-id',reading_id='reading-id',text=original_text,
                 settings=original_settings,chunks=[dict(text=original_text)]),
                 progress=dict(status='cancelled',chunks=[dict(status='pending',attempts=0)]),
                 reusable=0,remaining=1,published=False,stale=True,reading_changed=True,settings_changed=False)
        self.dialog.run=run
        self.flow.save_draft(self.batch,'目前稿件已改變。')
        self.dialog.display_run()
        self.assertEqual(self.dialog.source_text,original_text)
        self.assertEqual(self.dialog.outgoing.get('1.0','end-1c'),original_text)
        with patch.object(self.flow,'resume_narration') as resume:
            self.dialog.start()
            resume.assert_not_called()
        self.assertIn('已變更',self.dialog.status.cget('text'))
        self.assertEqual(run['snapshot']['text'],original_text)
        run['snapshot']['settings']=dict(original_settings,provider='kokoro')
        self.dialog.display_run()
        self.root.update()
        self.assertFalse(self.dialog.consent_control.winfo_ismapped())
        self.assertTrue(self.dialog.local_notice.winfo_ismapped())
        self.assertTrue(self.dialog.consent.get())

    def test_cancelled_cloud_consent_survives_recheck_and_blocks_dispatch(self):
        self.flow.confirm_reading(self.batch)
        self.dialog.consent.set(False)
        self.dialog.recheck()
        self.poll()
        self.assertFalse(self.dialog.consent.get())
        with patch.object(self.flow,'start_narration') as start,patch.object(self.flow,'resume_narration') as resume:
            self.dialog.start_button.invoke()
            start.assert_not_called()
            resume.assert_not_called()
        self.assertIsNone(self.dialog.job)
        self.assertIn('勾選',self.dialog.status.cget('text'))

    def test_save_retry_keeps_previous_product_and_does_not_repeat_synthesis(self):
        self.flow.confirm_reading(self.batch)
        self.dialog.reload_button.invoke()
        self.poll()
        audio=fixture.fixture.VoiceJourney.audio(self)
        requests=[]
        class Service:
            def __init__(self,text,*args,**kwargs): requests.append(text)
            async def stream(self): yield dict(type='audio',data=audio)
        with patch('edge_tts.Communicate',Service):
            self.dialog.start_button.invoke()
            self.poll()
            old=self.flow.narration(self.batch)
            self.flow.save_draft(self.batch,'新的第一段。\n\n新的第二段。')
            self.flow.confirm_reading(self.batch)
            self.dialog.recheck()
            self.poll()
            requests.clear()
            with patch.object(self.flow,'finish_narration',side_effect=ProjectError('模擬成品保存失敗。')):
                self.dialog.start_button.invoke()
                deadline=time.monotonic()+15
                while self.dialog.start_button.cget('text')!='重試保存' and time.monotonic()<deadline:
                    self.root.update();time.sleep(.02)
                self.assertEqual(self.dialog.start_button.cget('text'),'重試保存')
                self.assertEqual(self.flow.narration(self.batch)['id'],old['id'])
                self.assertIn('重試保存',self.dialog.status.cget('text'))
            completed_requests=list(requests)
            self.dialog.start_button.invoke()
            self.poll()
            self.assertEqual(requests,completed_requests)
            self.assertNotEqual(self.flow.narration(self.batch)['id'],old['id'])
            self.assertFalse((self.flow.root/'.production.lock').exists())


if __name__=='__main__':
    unittest.main()
