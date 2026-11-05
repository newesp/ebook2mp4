"""Approved T19 mode selection and merge journey in the actual native window."""
import time
import tkinter as tk
import unittest
from unittest.mock import patch
import test_video_merge as core
import test_total_audio_desktop as gui
from ebook2mp4.desktop import make_app

class MergeVideoDesktop(unittest.TestCase):
    setUp=core.MergeVideoJourney.setUp
    prepare=core.MergeVideoJourney.prepare
    refresh_voices=core.MergeVideoJourney.refresh_voices
    audio=core.MergeVideoJourney.audio
    picture=core.MergeVideoJourney.picture
    movies=core.MergeVideoJourney.movies
    shutdown=gui.TotalAudioDesktop.shutdown
    wait_page=gui.TotalAudioDesktop.wait_page

    def test_switch_shared_selection_merge_preview_and_restore(self):
        ids=self.movies()
        self.root,self.app=make_app();self.addCleanup(self.shutdown)
        self.errors=[];self.root.report_callback_exception=lambda *e:self.errors.append(str(e))
        self.app.flow,self.app.batch_id=self.flow,self.batch;self.app.refresh();self.root.update()
        self.app.total_audio();audio=self.app.production.current;self.wait_page(audio)
        audio.select_button.invoke();audio.pause.set('1.25')
        workspace=self.app.production
        workspace.method.set('合併既有批次影片');workspace.method_control.event_generate('<<ComboboxSelected>>')
        page=workspace.current;self.wait_page(page)
        self.assertTrue(page.movie)
        self.assertEqual(page.selected,ids)
        self.assertEqual(page.pause.get(),'1.25')
        page.resolution.set('720p');page.start_button.invoke();self.wait_page(page)
        self.assertEqual(self.flow.total_video()['method'],'batch-videos')
        self.assertIsNone(self.flow.total_audio())
        page.resolution.set('1080p');self.root.update()
        self.assertIn('待更新',page.result_info.cget('text'))
        page.resolution.set('720p')
        page.join_button.invoke();join=page.join_page
        deadline=time.monotonic()+10
        while join.info_job is not None and time.monotonic()<deadline:self.root.update();time.sleep(.02)
        self.assertEqual(len(join.joins),1)
        self.assertEqual(len(join.frame_photos),2)
        self.root.state('normal')
        for size in ('1040x640','1360x800'):
            self.root.geometry(size);self.root.update()
            for widget in (join.play_button,join.back_button,join.save_button,join.pause_control,join.clip_control):
                self.assertTrue(widget.winfo_viewable())
                self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(),self.root.winfo_rootx()+self.root.winfo_width())
                self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),self.root.winfo_rooty()+self.root.winfo_height())
        join.play_button.invoke()
        deadline=time.monotonic()+40
        while (join.job is not None or join.movie_player and join.movie_player.has_work()) and time.monotonic()<deadline:
            self.root.update();time.sleep(.02)
        self.assertIsNone(join.job,join.status.cget('text'))
        self.assertIsNotNone(join.movie_player)
        self.assertIsNone(join.movie_player.folder)
        join.back_button.invoke()
        self.root.state('normal')
        for size in ('1040x640','1360x800'):
            self.root.geometry(size);self.root.update()
            for widget in (workspace.method_control,page.start_button,page.pause_control,page.resolution_control,page.back_button,page.outputs_button):
                self.assertTrue(widget.winfo_viewable(),str(widget))
                self.assertLessEqual(widget.winfo_rootx()+widget.winfo_width(),self.root.winfo_rootx()+self.root.winfo_width())
                self.assertLessEqual(widget.winfo_rooty()+widget.winfo_height(),self.root.winfo_rooty()+self.root.winfo_height())
        workspace.method.set('總音訊製片');workspace.method_control.event_generate('<<ComboboxSelected>>')
        self.assertIs(workspace.current,audio);self.wait_page(audio)
        self.assertEqual(audio.pause.get(),'1.25')
        self.assertEqual(self.errors,[])


    def test_switch_from_total_video_keeps_latest_shared_draft(self):
        ids=self.movies()
        self.root,self.app=make_app();self.addCleanup(self.shutdown)
        self.app.flow,self.app.batch_id=self.flow,self.batch;self.app.refresh();self.root.update()
        self.app.total_audio();audio=self.app.production.current;self.wait_page(audio)
        workspace=self.app.production
        workspace.method.set('合併既有批次影片');workspace.change_method()
        merge=workspace.current;self.wait_page(merge)
        merge.select_button.invoke()
        workspace.method.set('總音訊製片');workspace.change_method();self.wait_page(audio)
        audio.selected=ids[::-1];audio.pause.set('1.25');audio.save_button.invoke();self.wait_page(audio)
        self.app.total_video();video=workspace.current;self.wait_page(video)
        workspace.method.set('合併既有批次影片');workspace.change_method();self.wait_page(merge)
        self.assertIs(workspace.current,merge)
        self.assertEqual(merge.selected,ids[::-1])
        self.assertEqual(merge.pause.get(),'1.25')
