"""Native confirmed-draft production dialog with explicit online consent."""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, ttk

from .workflow import ProjectError
from .voice_media import PreviewPlayer


class NarrationDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app, self.flow, self.batch_id = app, app.flow, app.batch_id
        self.job, self.timer = None, None
        self.closing = False
        self.player = PreviewPlayer()
        self.title('批次 MP3／SRT')
        self.geometry('800x620')
        self.minsize(700, 580)
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        header = ttk.Frame(self, padding=(16, 12, 16, 4))
        header.grid(row=0, column=0, sticky='ew')
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text='已確認朗讀稿 → 批次 MP3／SRT', style='Heading.TLabel').grid(row=0, column=0, sticky='w')
        batch = next(b for b in self.flow.state['batches'] if b['id'] == self.batch_id)
        ttk.Label(header, text=f'{self.flow.state["name"]} ／ {batch["name"]}', wraplength=650).grid(row=1, column=0, sticky='ew', pady=5)
        self.source_info = ttk.Label(header, text='', wraplength=650)
        self.source_info.grid(row=2, column=0, sticky='ew')
        text_frame = ttk.Frame(self, padding=(16, 4))
        text_frame.grid(row=1, column=0, sticky='nsew')
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        self.outgoing = tk.Text(text_frame, wrap='word', height=5, width=1, font=('Microsoft JhengHei', 11))
        self.outgoing.grid(row=0, column=0, sticky='nsew')
        scrollbar = ttk.Scrollbar(text_frame, command=self.outgoing.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.outgoing.configure(yscrollcommand=scrollbar.set)
        controls = ttk.Frame(self, padding=(16, 6, 16, 16))
        controls.grid(row=2, column=0, sticky='ew')
        controls.columnconfigure(0, weight=1)
        self.reload_button = ttk.Button(controls, text='重讀目前確認稿與設定', command=self.load_source)
        self.reload_button.grid(row=0, column=0, sticky='w')
        ttk.Label(controls, text='保留原文。非零句尾按安全句界合成；同邊界取較長值；最後不補靜音。\n'
                  '字幕以完整區塊實測時長顯示。長區塊字幕可能有多行。', wraplength=650,
                  foreground='#58695f').grid(row=1, column=0, sticky='ew', pady=6)
        self.consent = tk.BooleanVar(value=True)
        self.consent_control = ttk.Checkbutton(controls, text='我同意將上方已確認稿傳送至所選 TTS 服務（可能計費）', variable=self.consent)
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
        self.result_info = ttk.Label(controls, text='', wraplength=650, foreground='#58695f')
        self.result_info.grid(row=6, column=0, sticky='ew', pady=8)
        outputs = ttk.Frame(controls)
        outputs.grid(row=7, column=0, sticky='ew')
        self.play_button = ttk.Button(outputs, text='播放成品', command=self.play)
        self.stop_button = ttk.Button(outputs, text='停止播放', command=self.stop)
        self.export_button = ttk.Button(outputs, text='另存 MP3／SRT', command=self.export)
        self.folder_button = ttk.Button(outputs, text='開啟資料夾', command=self.open_folder)
        for index, button in enumerate((self.play_button, self.stop_button, self.export_button, self.folder_button)):
            button.grid(row=0, column=index, padx=(0, 6))
        ttk.Button(outputs, text='關閉', command=self.close).grid(row=1, column=0, sticky='w', pady=(8, 0))
        self.load_source()
        self.load_result()

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
            if self.job is not None:
                if self.job.wait(0) and self.job.state['status'] == 'completed':
                    self.publish()
                return
            if self.app.flow is not self.flow or self.app.batch_id != self.batch_id:
                raise ProjectError('主視窗已換書籍或批次，請關閉後從目前批次重開。')
            if not self.consent.get():
                raise ProjectError('請先核對並勾選同意將確認稿傳送至線上語音服務。')
            if (self.flow.reading_text(self.batch_id) != self.source_text or
                    self.flow.voice_settings(self.batch_id) != self.source_settings):
                self.load_source()
                self.consent.set(False)
                raise ProjectError('確認稿或設定已變更。已重讀，請重新核對並勾選同意。')
            self.stop()
            self.job = self.flow.start_narration(self.batch_id)
            self.update_controls()
            self.schedule()
        except ProjectError as error:
            self.status.configure(text=str(error))

    def schedule(self):
        if self.timer is not None:
            self.after_cancel(self.timer)
        self.timer = self.after(100, self.poll)

    def publish(self):
        self.flow.finish_narration(self.job)
        self.job = None
        self.load_result()
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
        self.start_button.configure(state='normal' if not busy or can_save else 'disabled',
                                    text='重試保存' if stopped else '產生 MP3／SRT')
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
        if self.job is not None:
            self.cancel()
            self.schedule()
        else:
            self.release()

    def release(self):
        if self.timer is not None:
            self.after_cancel(self.timer)
            self.timer = None
        self.progress.stop()
        self.app.narration_dialog = None
        self.destroy()
