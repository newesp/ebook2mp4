"""Native confirmed-draft production dialog with explicit online consent."""
from __future__ import annotations

import os
import asyncio
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .workflow import ProjectError
from .voice_media import PreviewPlayer

STATUS_LABELS = {'interrupted':'已中斷','cancelled':'已取消','failed':'失敗','completed':'已完成',
                 'running':'執行中','pending':'等待','cancelling':'取消中'}


class NarrationDialog(ttk.Frame):
    def __init__(self, app):
        super().__init__(app.production.host)
        self.app, self.flow, self.batch_id = app, app.flow, app.batch_id
        self.job, self.timer = None, None
        self.closing = False
        self.player = PreviewPlayer()
        self.run = None
        self.runs = []
        self.inspection: dict | None = None
        self.source_text = ''
        self.source_settings: dict | None = None
        self.check_job = None
        self.check_timer = None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1, minsize=60)
        self.rowconfigure(3, weight=3, minsize=60)
        header=ttk.Frame(self)
        header.grid(row=0,column=0,sticky='ew',pady=(4,4))
        header.columnconfigure(0,weight=1)
        ttk.Label(header,text='朗讀稿預覽',style='Heading.TLabel').grid(row=0,column=0,sticky='w')
        self.info_button=ttk.Button(header,text='任務與設定詳情 ▸',command=self.toggle_info)
        self.info_button.grid(row=0,column=1,sticky='e')
        self.preview_frame=ttk.Frame(self)
        self.preview_frame.grid(row=1,column=0,sticky='nsew')
        self.preview_frame.columnconfigure(0,weight=1)
        self.preview_frame.rowconfigure(0,weight=1)
        self.outgoing=tk.Text(self.preview_frame,wrap='word',height=3,width=1,font=('Microsoft JhengHei',11))
        self.outgoing.grid(row=0,column=0,sticky='nsew')
        scroll=ttk.Scrollbar(self.preview_frame,command=self.outgoing.yview)
        scroll.grid(row=0,column=1,sticky='ns')
        self.outgoing.configure(yscrollcommand=scroll.set)
        self.info_frame=ttk.Frame(self)
        self.info_frame.columnconfigure(0,weight=1)
        self.info_frame.rowconfigure(0,weight=1)
        self.source_info=ttk.Label(self.info_frame,text='',wraplength=650)
        self.source_info.grid(row=0,column=0,sticky='nw')
        self.reload_button=ttk.Button(self.info_frame,text='重新檢查目前稿件與設定',command=self.recheck)
        self.reload_button.grid(row=1,column=0,sticky='w')
        self.info_open=False
        toolbar=ttk.Frame(self)
        toolbar.grid(row=2,column=0,sticky='ew',pady=6)
        toolbar.columnconfigure(0,weight=1)
        toolbar.columnconfigure(1,weight=1)
        self.run_choice=tk.StringVar()
        self.run_control=ttk.Combobox(toolbar,textvariable=self.run_choice,state='readonly',width=1)
        self.run_control.grid(row=0,column=0,sticky='ew',padx=(0,12))
        self.run_control.bind('<<ComboboxSelected>>',self.select_run)
        self.run_summary=ttk.Label(toolbar,text='',width=1,anchor='e')
        self.run_summary.grid(row=0,column=1,sticky='ew')
        table=ttk.Frame(self)
        table.grid(row=3,column=0,sticky='nsew')
        table.columnconfigure(0,weight=1)
        table.rowconfigure(0,weight=1)
        self.details=ttk.Treeview(table,columns=('block','status','attempts','reason'),show='headings',height=5)
        for key,label,width in (('block','區塊',60),('status','狀態',140),('attempts','嘗試次數',90),('reason','說明',170)):
            self.details.heading(key,text=label)
            self.details.column(key,width=width,minwidth=40)
        self.details.grid(row=0,column=0,sticky='nsew')
        scroll=ttk.Scrollbar(table,command=self.details.yview)
        scroll.grid(row=0,column=1,sticky='ns')
        self.details.configure(yscrollcommand=scroll.set)
        self.details.bind('<<TreeviewSelect>>',self.show_block_error)
        controls=ttk.Frame(self)
        controls.grid(row=4,column=0,sticky='ew',pady=6)
        controls.columnconfigure(0,weight=1)
        self.status=ttk.Label(controls,text='',wraplength=450)
        self.status.grid(row=0,column=0,sticky='ew',padx=(0,12))
        self.start_button=ttk.Button(controls,text='開始製作 MP3／SRT',command=self.start,style='Primary.TButton')
        self.start_button.grid(row=0,column=1,sticky='e')
        self.cancel_button=ttk.Button(controls,text='取消任務',command=self.cancel,state='disabled')
        self.cancel_button.grid(row=0,column=2,padx=(8,0))
        actions=ttk.Frame(controls)
        actions.grid(row=1,column=0,columnspan=3,sticky='ew',pady=(6,0))
        actions.columnconfigure(1,weight=1)
        ttk.Button(actions,text='← 返回語音設定',command=self.app.voice_settings).grid(row=0,column=0,sticky='w')
        self.consent=tk.BooleanVar(value=True)
        self.consent_control=ttk.Checkbutton(actions,text='同意傳送待處理文字（可能計費）',variable=self.consent)
        self.consent_control.grid(row=0,column=1,sticky='w',padx=8)
        self.local_notice=ttk.Label(actions,text='文字僅在本機 CPU 處理，不傳送至雲端。')
        self.restart_button=ttk.Button(actions,text='重新開始…',command=self.restart)
        self.restart_button.grid(row=0,column=2,sticky='e')
        self.progress=ttk.Progressbar(controls,mode='indeterminate')
        self.progress.grid(row=2,column=0,columnspan=3,sticky='ew',pady=(4,0))
        outputs=ttk.Frame(self)
        outputs.grid(row=5,column=0,sticky='ew')
        outputs.columnconfigure(0,weight=1)
        self.result_info=ttk.Label(outputs,text='',width=1)
        self.result_info.grid(row=0,column=0,sticky='ew')
        self.play_button=ttk.Button(outputs,text='播放成品',command=self.play)
        self.stop_button=ttk.Button(outputs,text='停止播放',command=self.stop)
        self.export_button=ttk.Button(outputs,text='另存 MP3／SRT',command=self.export)
        self.folder_button=ttk.Button(outputs,text='開啟資料夾',command=self.open_folder)
        for index,button in enumerate((self.play_button,self.stop_button,self.export_button,self.folder_button)):
            button.grid(row=1,column=index,sticky='w',padx=(0,6),pady=4)
        self.bind('<Configure>',self.resize_info,add='+')
        self.load_source()
        self.load_result()

    def toggle_info(self):
        self.info_open=not self.info_open
        self.preview_frame.grid_remove() if self.info_open else self.info_frame.grid_remove()
        (self.info_frame if self.info_open else self.preview_frame).grid(row=1,column=0,sticky='nsew')
        self.info_button.configure(text='返回朗讀稿 ▾' if self.info_open else '任務與設定詳情 ▸')

    def resize_info(self,event):
        if event.widget is self:
            self.status.configure(wraplength=max(180,event.width-240))
            self.source_info.configure(wraplength=max(180,event.width-24))

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
        self.consent.set(True)

    def display_run(self):
        self.details.delete(*self.details.get_children())
        if self.run is None:
            self.load_source()
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
            self.outgoing.configure(state='normal')
            self.outgoing.delete('1.0','end')
            self.outgoing.insert('1.0',self.source_text)
            self.outgoing.configure(state='disabled')
            status=STATUS_LABELS.get(self.run['progress']['status'],'待檢查')
            self.run_summary.configure(text=f'{status} · 共 {len(snapshot["chunks"])} 塊 · 可重用 {self.run["reusable"]} · 待處理 {self.run["remaining"]}')
            self.status.configure(text='稿件或設定已變更；請返回核對新版本，再重新開始。' if self.run['stale'] else
                'MP3／SRT 已完成並保存。請使用下方成功成品。' if self.run['published'] else
                self.run['progress'].get('error') or '已保留原任務快照，可繼續未完成區塊。')
            for index,chunk in enumerate(self.run['progress'].get('chunks',[])):
                self.details.insert('','end',values=(index+1,STATUS_LABELS.get(chunk['status'],'待檢查'),chunk.get('attempts',0),'查看原因' if chunk['status']=='failed' else '—'))
            if not self.run['remaining'] and not self.run['published']:
                self.status.configure(text='全部區塊有效。本次只在本機組裝，不傳送文字。' if not self.run['stale'] else self.status.cget('text'))
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
            if local:
                self.consent_control.grid_remove();self.local_notice.grid(row=0,column=1,sticky='w',padx=8)
            else:
                self.local_notice.grid_remove();self.consent_control.grid()
            self.status.configure(text='請核對上方確認稿與音色，再開始本機製作。' if local else '請核對上方確認稿與音色，再勾選同意並產生。')
        except ProjectError as error:
            self.source_info.configure(text='目前沒有可合成的已確認稿。')
            self.status.configure(text=str(error))
        self.outgoing.configure(state='normal')
        self.outgoing.delete('1.0', 'end')
        self.outgoing.insert('1.0', self.source_text)
        self.outgoing.configure(state='disabled')
        self.consent.set(True)

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
                self.consent.set(True)
                raise ProjectError('確認稿或設定已變更。已重讀，請重新核對並勾選同意。')
            self.stop()
            allow_network = not local and bool(remaining) and self.consent.get()
            self.job = (self.flow.resume_narration(self.batch_id,self.run['snapshot']['id'],allow_network=allow_network) if self.run is not None
                        else self.flow.start_narration(self.batch_id, allow_network=allow_network))
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

    def poll(self):
        self.timer = None
        if self.job is not None:
            if not self.job.wait(0):
                state = self.job.state
                if (self.source_settings and self.source_settings['provider']=='kokoro'
                        and state['status']=='running' and state.get('phase')=='本機合成'):
                    state['phase']=self.flow.local_voice_status()['phase']
                self.status.configure(text=f'{state.get("phase", "準備")} · 區塊 {state.get("current", 0)}/{state.get("total", 0)} · '
                                      f'完成 {state.get("completed", 0)} · 失敗 {state.get("failed", 0)}')
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
        try:
            if self.player.playing():
                self.schedule()
        except ProjectError as error:
            self.status.configure(text=str(error))
            self.stop()

    def update_controls(self):
        busy = self.job is not None
        stopped = self.job is not None and self.job.wait(0)
        can_save = stopped and self.job is not None and self.job.state['status'] == 'completed'
        stale = self.run is not None and self.run.get('stale', False)
        blocked = self.check_job is not None or self.run is not None and self.run['published'] and not stale
        incremental = self.run is None and self.inspection is not None and self.inspection['reusable'] > 0
        self.start_button.configure(state='normal' if can_save or not busy and not blocked else 'disabled',
                                    command=self.review_current if stale and not busy else self.start,
                                    text='核對稿件與設定 →' if stale and not busy else '重試保存' if stopped else '繼續未完成區塊 →' if self.run is not None else
                                    '重新組裝 MP3／SRT →' if incremental and self.inspection is not None and not self.inspection['remaining'] else
                                    '更新 MP3／SRT →' if incremental else '開始製作 MP3／SRT')
        self.run_control.configure(state='disabled' if busy or self.check_job is not None else 'readonly')
        self.restart_button.configure(state='disabled' if busy or self.check_job is not None else 'normal')
        self.cancel_button.configure(state='normal' if busy and not stopped else 'disabled')
        self.reload_button.configure(state='disabled' if busy else 'normal')
        self.consent_control.configure(state='disabled' if busy else 'normal')
        self.cancel_button.grid() if busy and not stopped else self.cancel_button.grid_remove()
        if busy and not stopped:
            self.progress.grid()
            self.progress.start(12)
        else:
            self.progress.stop()
            self.progress.grid_remove()

    def load_result(self):
        try:
            product = self.flow.narration(self.batch_id)
            batch = next(b for b in self.flow.state['batches'] if b['id'] == self.batch_id)
            stale = product is not None and (batch.get('current_reading') != product['reading_id'] or
                                             self.flow.voice_settings(self.batch_id) != product['settings'])
            for button in (self.play_button, self.export_button, self.folder_button):
                button.configure(state='normal' if product else 'disabled')
            self.result_info.configure(text=f'{"待更新 · 上一版" if stale else "目前成品"}：{product["completed_at"][:19].replace("T", " ")} · '
                                       f'{product["settings"]["voice"]} · {product["settings"]["rate"]} · '
                                       f'{product["duration_ms"]/1000:.3f} 秒' if product else '尚無成功的批次成品。')
        except ProjectError as error:
            self.result_info.configure(text=str(error))
            for button in (self.play_button, self.export_button, self.folder_button):
                button.configure(state='disabled')

    def play(self):
        try:
            self.player.play(self.flow.narration_path(self.batch_id))
            self.schedule()
        except ProjectError as error:
            self.status.configure(text=str(error))

    def stop(self):
        try:
            self.player.stop()
        except ProjectError as error:
            self.status.configure(text=str(error))

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
