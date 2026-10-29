"""Native confirmed-draft production dialog with explicit online consent."""
from __future__ import annotations

import os
import asyncio
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .workflow import ProjectError
from .voice_media import PreviewPlayer
from .production_desktop import ScrollPage

STATUS_LABELS = {'interrupted':'已中斷','cancelled':'已取消','failed':'失敗','completed':'已完成',
                 'running':'執行中','pending':'等待','cancelling':'取消中'}


class NarrationDialog(ScrollPage):
    def __init__(self, app):
        super().__init__(app.production.host)
        self.app, self.flow, self.batch_id = app, app.flow, app.batch_id
        self.job, self.timer = None, None
        self.closing = False
        self.player = PreviewPlayer()
        self.run = None
        self.runs = []
        self.check_job = None
        self.check_timer = None
        self.content.columnconfigure(0, weight=1)
        header = ttk.Frame(self.content, padding=(12, 12, 12, 4))
        header.grid(row=0, column=0, sticky='ew')
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text='已確認朗讀稿 → 批次 MP3／SRT', style='Heading.TLabel').grid(row=0, column=0, sticky='w')
        batch = next(b for b in self.flow.state['batches'] if b['id'] == self.batch_id)
        ttk.Label(header, text=f'{self.flow.state["name"]} ／ {batch["name"]}', wraplength=650).grid(row=1, column=0, sticky='ew', pady=5)
        self.source_info = ttk.Label(header, text='', wraplength=650)
        self.source_info.grid(row=2, column=0, sticky='ew')
        text_frame = ttk.Frame(self.content, padding=(12, 4))
        text_frame.grid(row=1, column=0, sticky='nsew')
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        self.outgoing = tk.Text(text_frame, wrap='word', height=5, width=1, font=('Microsoft JhengHei', 11))
        self.outgoing.grid(row=0, column=0, sticky='nsew')
        scrollbar = ttk.Scrollbar(text_frame, command=self.outgoing.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.outgoing.configure(yscrollcommand=scrollbar.set)
        controls = ttk.Frame(self, padding=(12, 6, 12, 12))
        controls.grid(row=1, column=0, columnspan=2, sticky='ew')
        controls.columnconfigure(0, weight=1)
        self.reload_button = ttk.Button(controls, text='重讀目前確認稿與設定', command=self.load_source)
        self.reload_button.grid(row=0, column=0, sticky='w')
        ttk.Label(controls, text='保留原文。非零句尾按安全句界合成；同邊界取較長值；最後不補靜音。\n'
                  '字幕以完整區塊實測時長顯示。長區塊字幕可能有多行。', wraplength=650,
                  foreground='#58695f').grid(row=1, column=0, sticky='ew', pady=6)
        self.consent = tk.BooleanVar(value=True)
        self.consent_control = ttk.Checkbutton(controls, text='我同意將待處理文字傳送至本次 TTS 服務（可能計費）', variable=self.consent)
        self.consent_control.grid(row=2, column=0, sticky='w', pady=4)
        actions = ttk.Frame(controls)
        actions.grid(row=3, column=0, sticky='ew', pady=5)
        self.start_button = ttk.Button(actions, text='產生 MP3／SRT', command=self.start, style='Primary.TButton')
        self.start_button.grid(row=0, column=0, padx=(0, 8))
        self.cancel_button = ttk.Button(actions, text='取消任務', command=self.cancel, state='disabled')
        self.cancel_button.grid(row=0, column=1)
        self.status = ttk.Label(controls, text='', wraplength=650)
        self.status.grid(row=4, column=0, sticky='ew', pady=5)
        self.progress = ttk.Progressbar(controls, mode='indeterminate')
        self.progress.grid(row=5, column=0, sticky='ew')
        self.result_info = ttk.Label(self.content, text='', wraplength=650, foreground='#58695f')
        self.result_info.grid(row=5, column=0, sticky='ew', padx=12,pady=8)
        outputs = ttk.Frame(self.content)
        outputs.grid(row=6, column=0, sticky='ew',padx=12,pady=8)
        self.play_button = ttk.Button(outputs, text='播放成品', command=self.play)
        self.stop_button = ttk.Button(outputs, text='停止播放', command=self.stop)
        self.export_button = ttk.Button(outputs, text='另存 MP3／SRT', command=self.export)
        self.folder_button = ttk.Button(outputs, text='開啟資料夾', command=self.open_folder)
        for index, button in enumerate((self.play_button, self.stop_button, self.export_button, self.folder_button)):
            button.grid(row=index//2, column=index%2, sticky='ew',padx=(0, 6),pady=4)
        ttk.Button(actions,text='← 返回語音設定',command=self.app.voice_settings).grid(row=1,column=0,sticky='w',pady=8)
        self.restart_button=ttk.Button(actions,text='重新開始…',command=self.restart)
        self.restart_button.grid(row=1,column=1,sticky='w',padx=8,pady=8)
        self.run_choice=tk.StringVar()
        self.run_control=ttk.Combobox(self.content,textvariable=self.run_choice,state='readonly',width=1)
        self.run_control.grid(row=2,column=0,sticky='ew',padx=12,pady=8)
        self.run_control.bind('<<ComboboxSelected>>',self.select_run)
        self.run_summary=ttk.Label(self.content,text='',wraplength=650)
        self.run_summary.grid(row=3,column=0,sticky='ew',padx=12,pady=4)
        self.details=ttk.Treeview(self.content,columns=('block','status','attempts'),show='headings',height=5)
        for key,label,width in (('block','區塊',80),('status','狀態',250),('attempts','嘗試次數',100)):
            self.details.heading(key,text=label)
            self.details.column(key,width=width,minwidth=40)
        self.details.grid(row=4,column=0,sticky='ew',padx=12,pady=4)
        self.bind_scroll()
        self.load_source()
        self.load_result()

    def load_runs(self):
        if self.check_job is not None or self.job is not None:
            return
        from .voice import VoiceJob
        async def inspect():
            return await asyncio.to_thread(self.flow.narration_runs,self.batch_id)
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
            self.runs = job.result
            self.run_control.configure(values=['目前確認稿（新任務）'] + [
                f'{r["snapshot"]["created_at"][:19]} · {STATUS_LABELS.get(r["progress"]["status"], "待檢查")} · {r["snapshot"]["id"][:8]}' for r in self.runs])
            pending = [r for r in self.runs if not r['published']]
            if self.run is not None:
                self.run = next((r for r in self.runs if r['snapshot']['id'] == self.run['snapshot']['id']), None)
            elif pending:
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
        self.consent.set(False)

    def display_run(self):
        self.details.delete(*self.details.get_children())
        if self.run is None:
            self.load_source()
            self.run_summary.configure(text='新任務：核對目前確認稿與語音設定。')
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
                self.details.insert('','end',values=(index+1,STATUS_LABELS.get(chunk['status'],'待檢查'),chunk.get('attempts',0)))
            if not self.run['remaining'] and not self.run['published']:
                self.status.configure(text='全部區塊有效。本次只在本機組裝，不傳送文字。' if not self.run['stale'] else self.status.cget('text'))
        self.update_controls()

    def restart(self):
        if self.job is not None:
            return
        if messagebox.askyesno('另建製作任務','重新核對目前確認稿與設定？舊進度與成功成品會保留。',parent=self):
            self.run=None
            self.run_control.current(0)
            self.display_run()
            self.consent.set(False)

    def load_source(self):
        self.source_text, self.source_settings = '', None
        try:
            self.source_text = self.flow.reading_text(self.batch_id)
            self.source_settings = self.flow.voice_settings(self.batch_id)
            self.source_info.configure(text=f'{len(self.source_text):,} 字元 · {self.source_settings["voice"] or "尚未選音色"} · '
                                       f'{self.source_settings["provider"]} {self.source_settings.get("model", "")} · {self.source_settings["rate"]} · 句尾 {self.source_settings["sentence_pause_ms"]} ms ／ '
                                       f'段落 {self.source_settings["paragraph_pause_ms"]} ms · 請先儲存本批設定。')
            self.status.configure(text='請核對上方確認稿與音色，再勾選同意並產生。')
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
            if not self.consent.get() and (self.run is None or self.run['remaining']):
                raise ProjectError('請先核對並勾選同意將確認稿傳送至線上語音服務。')
            if (self.flow.reading_text(self.batch_id) != self.source_text or
                    self.flow.voice_settings(self.batch_id) != self.source_settings):
                self.load_source()
                self.consent.set(False)
                raise ProjectError('確認稿或設定已變更。已重讀，請重新核對並勾選同意。')
            self.stop()
            self.job = (self.flow.resume_narration(self.batch_id,self.run['snapshot']['id'],allow_network=self.consent.get()) if self.run is not None
                        else self.flow.start_narration(self.batch_id))
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
        blocked = self.check_job is not None or self.run is not None and (self.run['stale'] or self.run['published'])
        self.start_button.configure(state='normal' if can_save or not busy and not blocked else 'disabled',
                                    text='重試保存' if stopped else '繼續未完成區塊 →' if self.run is not None else '開始製作 MP3／SRT')
        self.run_control.configure(state='disabled' if busy or self.check_job is not None else 'readonly')
        self.restart_button.configure(state='disabled' if busy or self.check_job is not None else 'normal')
        self.cancel_button.configure(state='normal' if busy and not stopped else 'disabled')
        self.reload_button.configure(state='disabled' if busy else 'normal')
        self.consent_control.configure(state='disabled' if busy else 'normal')
        if busy and not stopped:
            self.progress.start(12)
        else:
            self.progress.stop()

    def load_result(self):
        try:
            product = self.flow.narration(self.batch_id)
            for button in (self.play_button, self.export_button, self.folder_button):
                button.configure(state='normal' if product else 'disabled')
            self.result_info.configure(text=f'上次成品：{product["completed_at"]} · {product["settings"]["voice"]} · '
                                       f'{product["duration_ms"]/1000:.3f} 秒 · {len(product["chunks"])} 區塊' if product else '尚無成功的批次成品。')
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
