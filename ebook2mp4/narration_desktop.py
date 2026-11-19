"""Native confirmed-draft production dialog with explicit online consent."""
from __future__ import annotations

import os
import asyncio
import math
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .workflow import ProjectError
from .voice_media import PreviewPlayer
from .ui_controls import AutoHideScrollbar, CellTooltip, MessageLine

STATUS_LABELS = {'interrupted':'已中斷','cancelled':'已取消','failed':'失敗','completed':'已完成',
                 'running':'執行中','pending':'等待','cancelling':'取消中'}


class NarrationDialog(ttk.Frame):
    page_id = 'audio.production'
    def __init__(self, app):
        super().__init__(app.production.host)
        self.app, self.flow, self.batch_id = app, app.flow, app.batch_id
        self.job, self.timer = None, None
        self.closing = False
        self.player = PreviewPlayer()
        self.playback_active = False
        self.production_busy = False
        self.run = None
        self.runs = []
        self.inspection: dict | None = None
        self.source_text = ''
        self.source_settings: dict | None = None
        self.check_job = None
        self.check_timer = None
        self.columnconfigure(0, weight=1)
        # Only this content row grows. Source inspection replaces the list in
        # place and retains each pane's selection and scroll position.
        self.rowconfigure(1, weight=1)
        self.toolbar=toolbar=ttk.Frame(self)
        toolbar.grid(row=0,column=0,sticky='ew',pady=(0,8))
        toolbar.columnconfigure(2,weight=1)
        self.files_button=ttk.Button(toolbar,text='>',width=2,style='Workspace.TButton',command=self.toggle_files)
        self.files_button.grid(row=0,column=0,padx=(0,8))
        self.files_hint=CellTooltip(self.files_button,lambda x,y: ('files','顯示文件列表（F6）'))
        self.files_button.bind('<FocusIn>',lambda e:self.files_hint.motion(type('Focus',(),{'x':0,'y':0})()),add='+')
        self.files_button.bind('<FocusOut>',self.files_hint.hide,add='+')
        ttk.Label(toolbar,text='製作任務').grid(row=0,column=1,padx=(0,8))
        self.run_choice=tk.StringVar()
        self.run_control=ttk.Combobox(toolbar,textvariable=self.run_choice,state='readonly',width=1,style='Workspace.TCombobox')
        self.run_control.grid(row=0,column=2,sticky='ew')
        self.run_control.bind('<<ComboboxSelected>>',self.select_run)
        self.info_button=ttk.Button(toolbar,text='朗讀稿與任務設定 ▸',command=self.toggle_info)
        self.info_button.grid(row=0,column=3,padx=(8,0))
        self.restore_button=ttk.Button(toolbar,text='恢復原任務設定',command=self.restore_settings)
        self.restore_button.grid(row=0,column=4,padx=(8,0))
        self.table_frame=ttk.Frame(self)
        self.table_frame.grid(row=1,column=0,sticky='nsew')
        self.table_frame.columnconfigure(0,weight=1)
        self.table_frame.rowconfigure(0,weight=1)
        self.details=ttk.Treeview(self.table_frame,columns=('block','status','attempts','reason'),show='headings',height=8)
        for key,label,width in (('block','區塊',64),('status','狀態',120),('attempts','嘗試次數',90),('reason','說明',300)):
            self.details.heading(key,text=label)
            self.details.column(key,width=width,minwidth=40,stretch=key=='reason')
        self.details.grid(row=0,column=0,sticky='nsew')
        scroll=AutoHideScrollbar(self.table_frame,command=self.details.yview)
        scroll.grid(row=0,column=1,sticky='ns')
        self.details.configure(yscrollcommand=scroll.set)
        self.details.bind('<<TreeviewSelect>>',self.show_block_error)
        for sequence,last in (('<Home>',False),('<Control-Home>',False),('<End>',True),('<Control-End>',True)):
            self.details.bind(sequence,lambda event,last=last:self.move_to_boundary(last))

        self.info_frame=ttk.Frame(self)
        self.info_frame.columnconfigure(0,weight=1)
        self.info_frame.rowconfigure(0,weight=1)
        self.info_tabs=ttk.Notebook(self.info_frame)
        self.info_tabs.grid(row=0,column=0,sticky='nsew')
        self.info_tabs.enable_traversal()
        self.preview_frame=ttk.Frame(self.info_tabs,padding=8)
        self.preview_frame.columnconfigure(0,weight=1)
        self.preview_frame.rowconfigure(2,weight=1)
        self.source_info=ttk.Label(self.preview_frame,text='',wraplength=650)
        self.source_info.grid(row=0,column=0,columnspan=2,sticky='ew',pady=(0,4))
        self.run_summary=ttk.Label(self.preview_frame,text='',width=1)
        self.run_summary.grid(row=1,column=0,columnspan=2,sticky='ew',pady=(0,8))
        self.outgoing=tk.Text(self.preview_frame,wrap='word',height=4,width=1,font=('Microsoft JhengHei',11))
        self.outgoing.grid(row=2,column=0,sticky='nsew')
        scroll=AutoHideScrollbar(self.preview_frame,command=self.outgoing.yview)
        scroll.grid(row=2,column=1,sticky='ns')
        self.outgoing.configure(yscrollcommand=scroll.set)
        self.info_tabs.add(self.preview_frame,text='朗讀稿與設定')
        self.message_frame=ttk.Frame(self.info_tabs,padding=8)
        self.message_frame.columnconfigure(0,weight=1)
        self.message_frame.rowconfigure(0,weight=1)
        self.message_text=tk.Text(self.message_frame,wrap='word',height=4,width=1,font=('Microsoft JhengHei',11),state='disabled')
        self.message_text.grid(row=0,column=0,sticky='nsew')
        scroll=AutoHideScrollbar(self.message_frame,command=self.message_text.yview)
        scroll.grid(row=0,column=1,sticky='ns')
        self.message_text.configure(yscrollcommand=scroll.set)
        self.info_tabs.add(self.message_frame,text='狀態與錯誤詳情')
        self.info_tabs.bind('<<NotebookTabChanged>>',self.info_tab_changed)
        self.info_open=False

        self.status_row=status_row=ttk.Frame(self)
        status_row.grid(row=2,column=0,sticky='ew',pady=(6,4))
        status_row.columnconfigure(0,weight=1)
        # A bounded single line cannot let a verbose server error squeeze the
        # list. The adjacent button exposes the complete, selectable message.
        self.status=MessageLine(status_row,text='')
        self.status.grid(row=0,column=0,sticky='ew')
        self.progress=ttk.Progressbar(status_row,mode='indeterminate',length=96)
        self.progress.grid(row=0,column=1,padx=8)
        self.status_controls=ttk.Frame(status_row)
        self.status_controls.grid(row=0,column=2,sticky='e',padx=(8,0))
        self.context=context=ttk.Frame(self.status_controls)
        context.grid(row=0,column=0,sticky='w',padx=(0,12))
        self.consent=tk.BooleanVar(value=True)
        self.consent_control=ttk.Checkbutton(context,text='同意傳送待處理文字（可能計費）',variable=self.consent)
        self.consent_control.grid(row=0,column=0,sticky='w')
        self.local_notice=ttk.Label(context,text='本機 CPU 處理，不傳送文字。')
        # Product metadata remains available in the inspection page and full
        # status details, without reserving a separate line below the controls.
        self.result_info=ttk.Label(self.preview_frame,text='',width=1)
        self.result_info.grid(row=3,column=0,columnspan=2,sticky='ew',pady=(4,0))
        self.reload_button=ttk.Button(self.status_controls,text='重新檢查目前稿件與設定',command=self.recheck)
        self.reload_button.grid(row=0,column=2)
        self.status_button=ttk.Button(self.status_controls,text='狀態詳情',command=self.show_status)
        self.status_button.grid(row=0,column=1,padx=(0,8))
        # Owned by the stable footer so the audio actions can span the document
        # rail as well as the content. Visibility follows the active audio page.
        self.actions=app.shell.create_footer(self)
        self.actions.columnconfigure(1,weight=1)
        previous=self.previous_actions=ttk.Frame(self.actions)
        previous.grid(row=0,column=0,sticky='w')
        self.back_button=self.actions.button('← 語音設定',self.app.voice_settings,parent=previous,role='back')
        self.back_button.pack(side='left')
        self.restart_button=self.actions.button('重新開始…',self.restart,parent=previous)
        self.restart_button.pack(side='left',padx=(8,0))
        self.outputs=ttk.Frame(self.actions)
        self.outputs.grid(row=0,column=1,sticky='e',padx=12)
        self.play_button=self.actions.button('播放成品',self.play,parent=self.outputs)
        self.stop_button=self.actions.button('停止播放',self.stop,parent=self.outputs)
        self.export_button=self.actions.button('另存 MP3／SRT',self.export,parent=self.outputs)
        self.folder_button=self.actions.button('開啟資料夾',self.open_folder,parent=self.outputs)
        self.video_button=self.actions.button('製作 MP4 →',self.app.batch_video,parent=self.outputs)
        self.output_button=ttk.Menubutton(self.outputs,text='成品操作')
        self.output_menu=tk.Menu(self.output_button,tearoff=False)
        self.output_button.configure(menu=self.output_menu)
        for button in (self.play_button,self.stop_button,self.export_button,self.folder_button):
            self.output_menu.add_command(label=button.cget('text'),command=button.invoke)
        self.output_menu.add_separator()
        self.output_menu.add_command(label='加入素材，製作 MP4 →',command=self.video_button.invoke)
        primary=self.primary_actions=ttk.Frame(self.outputs)
        self.cancel_button=self.actions.button('取消任務',self.cancel,parent=primary,state='disabled')
        self.cancel_button.grid(row=0,column=0,padx=(0,8))
        self.start_button=self.actions.button('開始製作 MP3／SRT',self.start,parent=primary,role='primary')
        self.start_button.grid(row=0,column=1)
        self.output_layout=None
        self.bind('<Configure>',self.resize_info,add='+')
        self.bind('<Destroy>',self.destroy_actions,add='+')
        self.load_source()
        self.load_result()

    def toggle_info(self):
        self.info_open=not self.info_open
        self.table_frame.grid_remove() if self.info_open else self.info_frame.grid_remove()
        (self.info_frame if self.info_open else self.table_frame).grid(row=1,column=0,sticky='nsew')
        self.info_button.configure(text='← 返回區塊清單' if self.info_open else '朗讀稿與任務設定 ▸')

    def show_status(self):
        if not self.info_open:
            self.toggle_info()
        self.refresh_status_text()
        self.info_tabs.select(self.message_frame)

    def info_tab_changed(self,_event=None):
        if self.info_tabs.select()==str(self.message_frame):
            self.refresh_status_text()

    def refresh_status_text(self):
        message=self.status.full_text
        result=self.result_info.cget('text')
        if result:
            message+='\n\n'+result
        if self.run is not None:
            errors=[f'第 {i+1} 塊：{chunk["error"]}' for i,chunk in enumerate(self.run.get('progress',{}).get('chunks',[]))
                    if chunk.get('error')]
            if errors:
                message+='\n\n'+'\n\n'.join(errors)
        if self.message_text.get('1.0','end-1c') != message:
            position=self.message_text.yview()[0]
            self.message_text.configure(state='normal')
            self.message_text.delete('1.0','end')
            self.message_text.insert('1.0',message)
            self.message_text.configure(state='disabled')
            self.message_text.yview_moveto(position)

    def resize_info(self,event):
        if event.widget is self:
            self.sync_files_button()
            self.source_info.configure(wraplength=max(180,event.width-48))
            self.layout_status()
            self.layout_actions()

    def layout_status(self):
        width=self.winfo_width()
        controls=self.status_controls
        # Keep the status tools together; only the status summary moves above
        # the group at the supported minimum size.
        required=sum(w.winfo_reqwidth() for w in (self.context,self.reload_button,self.status_button))+28
        stacked=required>width
        self.context.grid_configure(row=0,column=0,columnspan=3 if stacked else 1,pady=(0,4) if stacked else 0)
        self.status_button.grid_configure(row=1 if stacked else 0,column=1)
        self.reload_button.grid_configure(row=1 if stacked else 0,column=2)
        narrow=width<required+220 or stacked
        controls.grid_configure(row=1 if narrow else 0,column=0 if narrow else 2,
                                columnspan=2 if narrow else 1,padx=0 if narrow else (8,0),pady=(4,0) if narrow else 0)
        restore_visible=bool(self.restore_button.winfo_manager())
        restore_width=self.restore_button.winfo_reqwidth() if restore_visible else 0
        restore_wrap=width<self.info_button.winfo_reqwidth()+restore_width+260
        self.restore_button.grid_configure(row=1 if restore_wrap else 0,column=3 if restore_wrap else 4,
                                          pady=(4,0) if restore_wrap else 0)
        if not restore_visible:
            self.restore_button.grid_remove()

    def layout_actions(self):
        for child in self.outputs.winfo_children():
            child.pack_forget()
        for button in (self.play_button,self.primary_actions,self.output_button,self.video_button):
            button.pack(side='left',padx=(0,6))
        required=sum(w.winfo_reqwidth() for w in (self.previous_actions,self.outputs))+16
        narrow=self.actions.winfo_width()<required
        self.previous_actions.grid(row=0,column=0,sticky='w')
        self.outputs.grid(row=1 if narrow else 0,column=0 if narrow else 1,
                          columnspan=2 if narrow else 1,sticky='e',padx=(8,0),pady=(4,0) if narrow else 0)

    def destroy_actions(self,event):
        if event.widget is self and self.actions.winfo_exists():
            self.actions.destroy()

    def sync_files_button(self):
        self.files_button.grid() if self.app.focus_mode else self.files_button.grid_remove()

    def toggle_files(self):
        self.app.toggle_focus()
        self.sync_files_button()

    def show_source_context(self):
        local=bool(self.source_settings and self.source_settings['provider']=='kokoro')
        if local:
            self.consent_control.grid_remove()
            self.local_notice.grid(row=0,column=0,sticky='w')
        else:
            self.local_notice.grid_remove()
            self.consent_control.grid()
        if self.outgoing.get('1.0','end-1c') != self.source_text:
            self.outgoing.configure(state='normal')
            self.outgoing.delete('1.0','end')
            self.outgoing.insert('1.0',self.source_text)
        self.outgoing.configure(state='disabled')

    def move_to_boundary(self,last):
        rows=self.details.get_children()
        if rows:
            row=rows[-1] if last else rows[0]
            self.details.selection_set(row)
            self.details.focus(row)
            self.details.see(row)
        return 'break'

    def review_current(self):
        self.recheck()

    def recheck(self):
        if self.job is not None or self.check_job is not None:
            return
        self.run=None
        self.run_control.current(0)
        self.load_source()
        self.load_runs(keep_current=True)

    def show_block_error(self,_event=None):
        if self.job is not None:
            return
        selected=self.details.selection()
        if not selected or self.run is None:
            return
        index=self.details.index(selected[0])
        chunks=self.run['progress'].get('chunks',[])
        if index>=len(chunks) or chunks[index].get('status')!='failed':
            return
        error=chunks[index].get('error') or self.run['progress'].get('error') or '未保存詳細原因，請檢查連線與服務設定。'
        prefix='稿件或設定已變更，請先核對。' if self.run.get('stale') else ''
        self.status.configure(text=f'{prefix}第 {index+1} 塊：{error}')

    def load_runs(self, *, keep_current=False):
        if self.check_job is not None or self.job is not None:
            return
        from .voice import VoiceJob
        flow,batch_id=self.flow,self.batch_id
        async def inspect():
            runs = await asyncio.to_thread(flow.narration_runs,batch_id)
            try:
                inspection = await asyncio.to_thread(flow.inspect_narration, batch_id)
            except ProjectError:
                inspection = None
            return runs, inspection
        self.keep_current = keep_current
        self.check_job=VoiceJob(inspect,timeout=None)
        self.status.configure(text='正在檢查保存進度與音訊區塊…')
        self.update_controls()
        self.check_timer=self.after(100,self.poll_runs)

    def poll_runs(self):
        self.check_timer=None
        job=self.check_job
        if job is None:
            return
        if not job.wait(0):
            self.check_timer=self.after(100,self.poll_runs)
            return
        try:
            self.runs, self.inspection = job.result
            self.run_control.configure(values=['目前確認稿（新任務）'] + [
                f'第 {index} 次 · {r["snapshot"]["created_at"][:19]} · {STATUS_LABELS.get(r["progress"]["status"], "待檢查")}' for index,r in enumerate(self.runs,1)])
            pending = [r for r in self.runs if not r['published']]
            preferred = getattr(self, 'preferred_run_id', None)
            if preferred:
                self.run = next((r for r in self.runs if r['snapshot']['id'] == preferred), self.run)
                self.preferred_run_id = None
            if self.run is not None:
                self.run = next((r for r in self.runs if r['snapshot']['id'] == self.run['snapshot']['id']), None)
            elif pending and not self.keep_current:
                self.run = pending[-1]
            self.run_control.current(self.runs.index(self.run)+1 if self.run is not None else 0)
            self.display_run()
        except ProjectError as error:
            self.status.configure(text=str(error))
        finally:
            self.check_job=None
            self.update_controls()
        if self.closing and self.job is None:
            self.release()

    def select_run(self, _event=None):
        index=self.run_control.current()
        self.run=self.runs[index-1] if index>0 else None
        self.display_run()

    def restore_settings(self):
        if self.job or self.check_job or self.run is None: return
        try:
            voice = self.app.production.pages.get((id(self.flow), self.batch_id, 'voice'))
            if voice is not None and voice.settings_dirty():
                if not messagebox.askyesno('恢復設定', '取代尚未儲存的語音調整？', parent=self): return
            self.flow.restore_narration_settings(self.batch_id, self.run['snapshot']['id'])
            if voice is not None:
                voice.scope.set('本批次')
                voice.stop()
                voice.load_settings()
                voice.play_button.configure(state='disabled')
                voice.refresh_setting_sources()
            self.load_runs()
            self.load_result()
            self.status.configure(text='已恢復原任務設定。正在檢查稿件與區塊。')
        except ProjectError as error:
            self.status.configure(text=str(error))

    def display_run(self):
        if self.run is None:
            self.load_source()
        key=(('run',self.run['snapshot']['id']) if self.run is not None else
             ('current',self.source_text,tuple(sorted((self.source_settings or {}).items()))))
        preserve=getattr(self,'displayed_run_id',object())==key
        selected=[self.details.index(row) for row in self.details.selection()] if preserve else []
        position=self.details.yview()[0] if preserve else 0
        self.displayed_run_id=key
        self.details.delete(*self.details.get_children())
        if self.run is None:
            self.run_summary.configure(text='新任務：核對目前確認稿與語音設定。')
            inspection = self.inspection
            if (inspection is not None and inspection['snapshot']['text'] == self.source_text
                    and inspection['snapshot']['settings'] == self.source_settings):
                self.run_summary.configure(text=f'可重用 {inspection["reusable"]} 塊 · 需合成 {inspection["remaining"]} 塊')
                self.status.configure(text='請核對目前版本後更新；舊成品保留。' if inspection['remaining'] else
                                      '全部區塊有效。本次只在本機組裝，不傳送文字。')
                for index, chunk in enumerate(inspection['chunks'], 1):
                    self.details.insert('', 'end', values=(index, '重用' if chunk['reusable'] else '需合成', 0,
                        '原音已驗證' if chunk['reusable'] else '文字／設定不同或原音無效'))
        else:
            snapshot=self.run['snapshot']
            self.source_text,self.source_settings=snapshot['text'],snapshot['settings']
            self.source_info.configure(text=f'任務 {snapshot["id"][:8]} · 朗讀稿 {snapshot["reading_id"][:8]} · '
                f'{self.source_settings["provider"]} {self.source_settings.get("model", "")} · {self.source_settings["voice"]} · '
                f'{self.source_settings["rate"]} · 句尾 {self.source_settings["sentence_pause_ms"]}／段落 {self.source_settings["paragraph_pause_ms"]} ms')
            self.show_source_context()
            status=STATUS_LABELS.get(self.run['progress']['status'],'待檢查')
            self.run_summary.configure(text=f'{status} · 共 {len(snapshot["chunks"])} 塊 · 可重用 {self.run["reusable"]} · 待處理 {self.run["remaining"]}')
            self.status.configure(text='朗讀稿已變更；請核對稿件。' if self.run.get('reading_changed') else
                '語音設定不同；請按「恢復原任務設定」。' if self.run.get('settings_changed') else
                'MP3／SRT 已完成並保存。請使用下方成功成品。' if self.run['published'] else
                self.run['progress'].get('error') or '已保留原任務快照，可繼續未完成區塊。')
            for index,chunk in enumerate(self.run['progress'].get('chunks',[])):
                self.details.insert('','end',values=(index+1,STATUS_LABELS.get(chunk['status'],'待檢查'),chunk.get('attempts',0),'查看原因' if chunk['status']=='failed' else '—'))
            if not self.run['remaining'] and not self.run['published']:
                self.status.configure(text='全部區塊有效。本次只在本機組裝，不傳送文字。' if not self.run['stale'] else self.status.cget('text'))
        rows=self.details.get_children()
        self.details.selection_set([rows[index] for index in selected if index<len(rows)])
        self.details.yview_moveto(position)
        self.update_controls()

    def restart(self):
        if self.job is not None:
            return
        if messagebox.askyesno('另建製作任務','重新核對目前確認稿與設定？舊進度與成功成品會保留。',parent=self):
            self.recheck()

    def load_source(self):
        self.source_text, self.source_settings = '', None
        try:
            self.source_text = self.flow.reading_text(self.batch_id)
            self.source_settings = self.flow.voice_settings(self.batch_id)
            self.source_info.configure(text=f'{len(self.source_text):,} 字元 · {self.source_settings["voice"] or "尚未選音色"} · '
                                       f'{self.source_settings["provider"]} {self.source_settings.get("model", "")} · {self.source_settings["rate"]} · 句尾 {self.source_settings["sentence_pause_ms"]} ms ／ '
                                       f'段落 {self.source_settings["paragraph_pause_ms"]} ms · 請先儲存本批設定。')
            local=self.source_settings['provider']=='kokoro'
            self.status.configure(text='請核對朗讀稿與任務設定，再開始本機製作。' if local else '請核對朗讀稿與任務設定，再開始製作。')
        except ProjectError as error:
            self.source_info.configure(text='目前沒有可合成的已確認稿。')
            self.status.configure(text=str(error))
        self.show_source_context()

    def start(self):
        try:
            if self.check_job is not None:
                return
            if self.job is not None:
                if self.job.wait(0) and self.job.state['status'] == 'completed':
                    self.publish()
                return
            if self.app.flow is not self.flow or self.app.batch_id != self.batch_id:
                raise ProjectError('主視窗已換書籍或批次，請關閉後從目前批次重開。')
            if self.run is not None and self.run['stale']:
                raise ProjectError('稿件或設定已變更；請返回核對新版本，再重新開始。')
            remaining = self.run['remaining'] if self.run is not None else (
                self.inspection['remaining'] if self.inspection is not None else 1)
            local=bool(self.source_settings and self.source_settings['provider']=='kokoro')
            if not local and not self.consent.get() and remaining:
                raise ProjectError('請先核對並勾選同意將確認稿傳送至線上語音服務。')
            if (self.flow.reading_text(self.batch_id) != self.source_text or
                    self.flow.voice_settings(self.batch_id) != self.source_settings):
                self.load_source()
                raise ProjectError('確認稿或設定已變更。已重讀，請重新核對並勾選同意。')
            self.stop()
            allow_network = not local and bool(remaining) and self.consent.get()
            self.job = (self.flow.resume_narration(self.batch_id,self.run['snapshot']['id'],allow_network=allow_network) if self.run is not None
                        else self.flow.start_narration(self.batch_id, allow_network=allow_network))
            state = self.job.state
            state.setdefault('total', len(self.job.snapshot['chunks']))
            state.setdefault('chunks', [dict(chunk, status='pending', attempts=0)
                                        for chunk in self.job.snapshot['chunks']])
            self.display_progress(state)
            self.update_controls()
            self.schedule()
        except ProjectError as error:
            self.status.configure(text=str(error))

    def schedule(self):
        if self.timer is not None:
            self.after_cancel(self.timer)
        self.timer = self.after(100, self.poll)

    def publish(self):
        product=self.flow.finish_narration(self.job)
        self.job = None
        self.run=dict(snapshot=product)
        self.load_result()
        self.load_runs()
        self.status.configure(text='MP3／SRT 已完成並保存。請播放檢查聽感與字幕。')

    def display_progress(self, state):
        phase = state.get('phase', '準備')
        deadline = state.get('retry_deadline')
        if deadline is not None:
            phase = f'等待 {max(0, math.ceil(deadline - time.monotonic()))} 秒後重試'
        self.status.configure(text=f'{phase} · 區塊 {state.get("current", 0)}/{state.get("total", 0)} · '
                                   f'完成 {state.get("completed", 0)} · 失敗 {state.get("failed", 0)}')
        self.run_summary.configure(text=f'執行中 · 完成 {state.get("completed", 0)}/{state.get("total", 0)} 塊')
        if self.info_open and self.info_tabs.select()==str(self.message_frame):
            self.refresh_status_text()
        chunks = state.get('chunks', [])
        rows = self.details.get_children()
        if len(rows) != len(chunks):
            self.details.delete(*rows)
            rows = tuple(self.details.insert('', 'end') for chunk in chunks)
        for row, chunk in zip(rows, chunks):
            values = (chunk['order'] + 1, STATUS_LABELS.get(chunk['status'], '待檢查'),
                      chunk.get('attempts', 0), '查看原因' if chunk['status'] == 'failed' else '—')
            if tuple(map(str, self.details.item(row, 'values'))) != tuple(map(str, values)):
                self.details.item(row, values=values)

    def poll(self):
        self.timer = None
        # Playback may finish while a new synthesis is still running. Observe
        # it before the job's early return so the visible stop action is real.
        if self.playback_active:
            try:
                self.playback_active = self.player.playing()
                self.sync_play_button()
            except ProjectError as error:
                self.status.configure(text=str(error))
                self.stop()
        if self.job is not None:
            if not self.job.wait(0):
                state = self.job.state
                if (self.source_settings and self.source_settings['provider']=='kokoro'
                        and state['status']=='running' and state.get('phase')=='本機合成'):
                    state['phase']=self.flow.local_voice_status()['phase']
                self.display_progress(state)
                self.schedule()
                return
            state = self.job.state
            try:
                if self.closing:
                    self.flow.discard_narration(self.job)
                    self.job = None
                elif state['status'] == 'completed':
                    self.publish()
                else:
                    self.flow.discard_narration(self.job)
                    self.job = None
                    self.load_runs()
                    self.status.configure(text='已取消；上一份成功成品保留。' if state['status'] == 'cancelled' else state['error'])
            except ProjectError as error:
                self.closing = False
                self.status.configure(text=str(error) + ' 請重試保存，或關閉以捨棄本次結果。')
        self.update_controls()
        if self.closing and self.job is None:
            self.release()
            return
        if self.playback_active:
            self.schedule()

    def update_controls(self):
        busy = self.job is not None
        stopped = self.job is not None and self.job.wait(0)
        can_save = stopped and self.job is not None and self.job.state['status'] == 'completed'
        stale = self.run is not None and self.run.get('stale', False)
        restore = self.run is not None and self.run.get('settings_changed', False)
        self.restore_button.grid() if restore else self.restore_button.grid_remove()
        self.restore_button.configure(state='disabled' if busy or self.check_job else 'normal')
        published = self.run is not None and self.run.get('published', False) and not stale
        blocked = self.check_job is not None or self.production_busy and not busy
        incremental = self.run is None and self.inspection is not None and self.inspection['reusable'] > 0
        self.start_button.configure(state='normal' if can_save or not busy and not blocked else 'disabled',
                                    command=self.review_current if stale and not busy else self.app.total_audio if published and not busy else self.start,
                                    text='核對稿件與設定 →' if stale and not busy else '重試保存' if stopped else '全書合併 →' if published and not busy else '繼續未完成區塊' if self.run is not None else
                                    '重新組裝 MP3／SRT →' if incremental and self.inspection is not None and not self.inspection['remaining'] else
                                    '更新 MP3／SRT' if incremental else '開始製作 MP3／SRT')
        self.run_control.configure(state='disabled' if busy or self.check_job is not None else 'readonly')
        self.restart_button.configure(state='disabled' if busy or self.check_job is not None or self.production_busy else 'normal')
        self.cancel_button.configure(state='normal' if busy and not stopped else 'disabled')
        self.reload_button.configure(state='disabled' if busy or self.check_job or self.production_busy else 'normal')
        self.consent_control.configure(state='disabled' if busy else 'normal')
        self.cancel_button.grid() if busy and not stopped else self.cancel_button.grid_remove()
        if busy and not stopped:
            self.progress.grid()
            self.progress.start(12)
        else:
            self.progress.stop()
            self.progress.grid_remove()
        if self.info_open and self.info_tabs.select()==str(self.message_frame):
            self.refresh_status_text()
        self.layout_actions()
        self.layout_status()

    def set_production_busy(self, busy):
        if self.production_busy != busy:
            self.production_busy = busy
            self.update_controls()

    def load_result(self):
        try:
            product = self.flow.narration(self.batch_id)
            batch = next(b for b in self.flow.state['batches'] if b['id'] == self.batch_id)
            stale = product is not None and (batch.get('current_reading') != product['reading_id'] or
                                             self.flow.voice_settings(self.batch_id) != product['settings'])
            for button in (self.play_button, self.stop_button, self.export_button, self.folder_button):
                button.configure(state='normal' if product else 'disabled')
            for index in (0,1,2,3):
                self.output_menu.entryconfigure(index,state='normal' if product else 'disabled')
            self.result_info.configure(text=f'{"待更新 · 上一版" if stale else "目前成品"}：{product["completed_at"][:19].replace("T", " ")} · '
                                       f'{product["settings"]["voice"]} · {product["settings"]["rate"]} · '
                                       f'{product["duration_ms"]/1000:.3f} 秒' if product else '尚無成功的批次成品。')
        except ProjectError as error:
            self.result_info.configure(text=str(error))
            for button in (self.play_button, self.stop_button, self.export_button, self.folder_button):
                button.configure(state='disabled')
            for index in (0,1,2,3):
                self.output_menu.entryconfigure(index,state='disabled')
        self.sync_play_button()

    def sync_play_button(self):
        self.play_button.configure(text='停止播放' if self.playback_active else '播放成品',
                                   command=self.stop if self.playback_active else self.play,
                                   style='Primary.TButton' if self.playback_active else 'Workspace.TButton')
        # The menu starts playback explicitly; its separate stop entry remains
        # useful when keyboard users open the product menu during playback.
        self.output_menu.entryconfigure(0, command=self.play)

    def play(self):
        try:
            self.player.play(self.flow.narration_path(self.batch_id))
            self.playback_active = True
            self.sync_play_button()
            self.schedule()
        except ProjectError as error:
            self.status.configure(text=str(error))
            self.stop()

    def stop(self):
        try:
            self.player.stop()
        except ProjectError as error:
            self.status.configure(text=str(error))
        finally:
            self.playback_active = False
            self.sync_play_button()

    def export(self):
        name = filedialog.asksaveasfilename(parent=self, title='另存至新資料夾', initialfile='批次音訊與字幕', filetypes=[('新資料夾', '*')])
        if name:
            try:
                self.flow.export_narration(self.batch_id, name)
                self.status.configure(text='MP3 與 SRT 已另存至新資料夾。')
            except ProjectError as error:
                self.status.configure(text=str(error))

    def open_folder(self):
        try:
            os.startfile(self.flow.narration_path(self.batch_id).parent)
        except (OSError, ProjectError):
            self.status.configure(text='無法開啟成品資料夾，請從專案位置手動開啟。')

    def cancel(self):
        if self.job is not None:
            self.job.cancel()
            self.status.configure(text='取消中，正在釋放連線與媒體程序…')

    def close(self):
        self.stop()
        self.closing = True
        if self.check_job is not None:
            self.check_job.cancel()
            return
        if self.job is not None:
            self.cancel()
            self.schedule()
        else:
            self.release()

    def release(self):
        if self.check_timer is not None:
            self.after_cancel(self.check_timer)
            self.check_timer=None
        if self.timer is not None:
            self.after_cancel(self.timer)
            self.timer = None
        self.progress.stop()
        self.app.narration_dialog = None
        self.destroy()
