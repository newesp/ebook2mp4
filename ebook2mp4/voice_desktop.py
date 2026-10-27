"""Native voice chooser and preview; no editor lock or automatic voice choice."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .workflow import ProjectError
from .voice import EXAMPLE, RATES
from .voice_media import PreviewPlayer


class VoiceDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app, self.flow, self.batch_id = app, app.flow, app.batch_id
        self.job = None
        self.kind = ''
        self.timer = None
        self.closing = False
        self.player = PreviewPlayer()
        self.title('語音設定與短文試聽')
        self.geometry('820x730')
        self.minsize(740, 650)
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        header = ttk.Frame(self, padding=(16, 12, 16, 0))
        header.grid(row=0, column=0, sticky='ew')
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text='Edge-TTS · 線上語音', style='Heading.TLabel').grid(row=0, column=0, sticky='w')
        self.refresh_button = ttk.Button(header, text='更新線上音色', command=self.refresh_voices)
        self.refresh_button.grid(row=0, column=1)
        batch = next((b['name'] for b in self.flow.state['batches'] if b['id'] == self.batch_id), '全書預設')
        ttk.Label(header, text=f'所屬：{self.flow.state["name"]} ／ {batch}', wraplength=680).grid(
            row=1, column=0, columnspan=2, sticky='ew', pady=4)
        self.cache_info = ttk.Label(header, text='', foreground='#58695f')
        self.cache_info.grid(row=2, column=0, columnspan=2, sticky='ew', pady=5)
        self.locale = tk.StringVar(value='全部語系')
        self.filter = ttk.Combobox(header, textvariable=self.locale,
                                  values=('全部語系', '台灣華語', '中國普通話', '英文'), state='readonly', width=18)
        self.filter.grid(row=3, column=0, sticky='w', pady=(0, 5))
        ttk.Button(header, text='批次 MP3／SRT…', command=self.app.narration).grid(row=3, column=1, sticky='e')
        self.filter.bind('<<ComboboxSelected>>', lambda e: self.load_catalog())
        table = ttk.Frame(self, padding=(16, 0))
        table.grid(row=1, column=0, sticky='nsew')
        table.columnconfigure(0, weight=1)
        table.rowconfigure(0, weight=1)
        self.voices = ttk.Treeview(table, columns=('name', 'locale', 'gender'), show='headings', selectmode='browse', height=5)
        for key, label, width in (('name', '名稱', 380), ('locale', '語系', 90), ('gender', '性別（服務提供）', 145)):
            self.voices.heading(key, text=label)
            self.voices.column(key, width=width, minwidth=70, stretch=key == 'name')
        self.voices.grid(row=0, column=0, sticky='nsew')
        scrollbar = ttk.Scrollbar(table, command=self.voices.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.voices.configure(yscrollcommand=scrollbar.set)
        self.voices.bind('<<TreeviewSelect>>', self.choose_voice)
        controls = ttk.Frame(self, padding=(16, 8, 16, 12))
        controls.grid(row=2, column=0, sticky='ew')
        controls.columnconfigure(0, weight=1)
        self.voice = tk.StringVar()
        self.voice_info = ttk.Label(controls, textvariable=self.voice, wraplength=680)
        self.voice_info.grid(row=0, column=0, sticky='w')
        settings_row = ttk.Frame(controls)
        settings_row.grid(row=1, column=0, sticky='ew', pady=6)
        self.scope = tk.StringVar(value='本批次' if self.batch_id else '全書預設')
        self.scope_control = ttk.Combobox(settings_row, textvariable=self.scope, state='readonly', width=12,
                                         values=('本批次', '全書預設') if self.batch_id else ('全書預設',))
        self.scope_control.pack(side='left')
        self.scope_control.bind('<<ComboboxSelected>>', lambda e: self.load_settings())
        ttk.Label(settings_row, text='語速').pack(side='left', padx=(16, 5))
        self.rate = tk.StringVar(value='正常')
        self.rate_control = ttk.Combobox(settings_row, textvariable=self.rate, values=('-20%', '-10%', '正常', '+10%', '+20%'), state='readonly', width=8)
        self.rate_control.pack(side='left')
        self.save_button = ttk.Button(settings_row, text='儲存設定', command=self.save)
        self.save_button.pack(side='right')
        ttk.Label(controls, text='全書預設只供新批次沿用；既有批次請選「本批次」明確儲存。',
                  foreground='#58695f', wraplength=680).grid(row=2, column=0, sticky='w')
        ttk.Separator(controls).grid(row=3, column=0, sticky='ew', pady=8)
        self.source = tk.StringVar(value='固定範例')
        source_row = ttk.Frame(controls)
        source_row.grid(row=4, column=0, sticky='ew')
        for label in ('固定範例', '校對稿選取文字'):
            ttk.Radiobutton(source_row, text=label, value=label, variable=self.source, command=self.prepare_text).pack(side='left', padx=(0, 14))
        self.outgoing = tk.Text(controls, height=3, wrap='word', font=('Microsoft JhengHei', 10), state='disabled')
        self.outgoing.grid(row=5, column=0, sticky='ew', pady=5)
        self.text_info = ttk.Label(controls, text='', foreground='#58695f', wraplength=680)
        self.text_info.grid(row=6, column=0, sticky='w')
        ttk.Label(controls, text='不轉字、不改標點；保留引擎韻律。句尾額外 0 ms，空白行段落額外 500 ms，末段不補。',
                  wraplength=680, foreground='#58695f').grid(row=7, column=0, sticky='w', pady=4)
        self.consent = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls, text='我同意將上方試聽文字傳送至 Microsoft Edge 線上語音服務（需網路，不需 GPU）',
                        variable=self.consent).grid(row=8, column=0, sticky='w', pady=4)
        actions = ttk.Frame(controls)
        actions.grid(row=9, column=0, sticky='ew', pady=5)
        self.preview_button = ttk.Button(actions, text='儲存本批設定並試聽', command=self.preview, style='Primary.TButton')
        self.preview_button.pack(side='left')
        self.cancel_button = ttk.Button(actions, text='取消', command=self.cancel, state='disabled')
        self.cancel_button.pack(side='left', padx=5)
        self.play_button = ttk.Button(actions, text='播放上次結果', command=self.play)
        self.play_button.pack(side='left')
        self.stop_button = ttk.Button(actions, text='停止播放', command=self.stop)
        self.stop_button.pack(side='left', padx=5)
        ttk.Button(actions, text='關閉', command=self.close).pack(side='right')
        self.result_info = ttk.Label(controls, text='', wraplength=680, foreground='#58695f')
        self.result_info.grid(row=10, column=0, sticky='w', pady=4)
        self.status = ttk.Label(controls, text='請更新音色清單並明確選擇音色。', wraplength=680)
        self.status.grid(row=11, column=0, sticky='w')
        self.progress = ttk.Progressbar(controls, mode='indeterminate')
        self.progress.grid(row=12, column=0, sticky='ew', pady=(4, 0))
        self.load_settings()
        self.load_catalog()
        self.prepare_text()
        self.load_result()
        self.update_controls()

    def load_settings(self):
        value = self.flow.voice_settings(self.batch_id if self.scope.get() == '本批次' else None)
        self.voice.set(value['voice'])
        self.rate.set('正常' if value['rate'] == '+0%' else value['rate'])
        self.load_catalog()
        self.update_controls()

    def load_catalog(self):
        try:
            catalog = self.flow.voice_catalog()
            self.voices.delete(*self.voices.get_children())
            locale = {'台灣華語': 'zh-TW', '中國普通話': 'zh-CN', '英文': 'en-'}.get(self.locale.get(), '')
            for voice in catalog['voices']:
                if voice['locale'].startswith(locale):
                    self.voices.insert('', 'end', iid=voice['id'], values=(voice['name'], voice['locale'], voice['gender']))
            self.cache_info.configure(text='快取更新：' + (catalog['updated_at'] or '尚未取得；更新只取得音色清單，不傳送書稿。'))
            if self.voice.get() and self.voices.exists(self.voice.get()):
                self.voices.selection_set(self.voice.get())
                self.voices.see(self.voice.get())
        except ProjectError as error:
            self.status.configure(text=str(error))

    def choose_voice(self, _event=None):
        selection = self.voices.selection()
        if selection:
            self.voice.set(selection[0])

    def prepare_text(self):
        self.selected_text, self.selected_start, self.selected_end = None, None, None
        value = EXAMPLE
        if self.source.get() != '固定範例':
            if self.app.flow is not self.flow or self.app.batch_id != self.batch_id:
                value = ''
            else:
                ranges = self.app.editor.tag_ranges('sel')
                if ranges:
                    self.selected_text = self.app.current_text
                    self.selected_start = len(self.app.editor.get('1.0', ranges[0]))
                    self.selected_end = len(self.app.editor.get('1.0', ranges[1]))
                    value = self.selected_text[self.selected_start:self.selected_end]
                else:
                    value = ''
        self.outgoing.configure(state='normal')
        self.outgoing.delete('1.0', 'end')
        self.outgoing.insert('1.0', value)
        self.outgoing.configure(state='disabled')
        self.text_info.configure(text=f'{len(value):,} 字元 · 試聽上限 3,000 字元，不會自動截斷。' if value else '請回校對稿反白文字，再選「校對稿選取文字」。')
        return value

    def save(self):
        if self.app.flow is not self.flow or self.app.batch_id != self.batch_id:
            self.status.configure(text='主視窗的書籍或批次已切換；請關閉本視窗，回目前批次重新開啟語音設定。')
            return False
        try:
            self.flow.save_voice_settings(self.voice.get(), '+0%' if self.rate.get() == '正常' else self.rate.get(),
                                          batch_id=self.batch_id if self.scope.get() == '本批次' else None)
            self.status.configure(text='語音設定已儲存。')
            return True
        except ProjectError as error:
            self.status.configure(text=str(error))
            return False

    def refresh_voices(self):
        if self.job:
            return
        self.job, self.kind = self.flow.start_voice_refresh(), 'catalog'
        self.status.configure(text='正在取得線上音色清單…')
        self.schedule()

    def preview(self):
        if self.job or not self.batch_id:
            return
        if not self.consent.get():
            self.status.configure(text='請先勾選同意將試聽文字傳送至線上語音服務。')
            return
        value = self.prepare_text()
        if not value.strip() or len(value) > 3000:
            self.status.configure(text='請選取 1～3,000 字元後再試聽。')
            return
        if not self.save():
            return
        try:
            self.stop()
            options = {} if self.source.get() == '固定範例' else dict(text=self.selected_text, start=self.selected_start, end=self.selected_end)
            self.job = self.flow.start_voice_preview(self.batch_id, **options)
            self.kind = 'preview'
            self.status.configure(text='正在產生試聽…可繼續在主視窗校對，或取消。')
            self.schedule()
        except ProjectError as error:
            self.status.configure(text=str(error))

    def schedule(self):
        if self.timer is not None:
            self.after_cancel(self.timer)
        self.update_controls()
        self.timer = self.after(100, self.poll)

    def poll(self):
        self.timer = None
        if self.job is not None:
            if not self.job.wait(0):
                self.schedule()
                return
            state = self.job.state
            try:
                if self.kind == 'preview':
                    if state['status'] == 'completed':
                        self.flow.finish_voice_preview(self.job)
                    else:
                        self.flow.discard_voice_preview(self.job)
                self.job = None
                self.load_catalog()
                self.load_result()
                self.status.configure(text='試聽已完成，請按播放聆聽。' if state['status'] == 'completed' and self.kind == 'preview'
                                      else '音色清單已更新；請明確選擇音色。' if state['status'] == 'completed'
                                      else '已取消；上一份成功結果保留。' if state['status'] == 'cancelled' else state['error'])
            except ProjectError as error:
                self.status.configure(text=str(error) + ' 可重試儲存，或關閉並捨棄本次結果。')
                self.closing = False
        try:
            if self.player.playing():
                self.schedule()
                return
        except ProjectError as error:
            self.status.configure(text=str(error))
            self.stop()
        self.update_controls()
        if self.closing and self.job is None:
            self.release()

    def update_controls(self):
        busy = self.job is not None
        for control in (self.refresh_button, self.save_button):
            control.configure(state='disabled' if busy else 'normal')
        self.scope_control.configure(state='disabled' if busy else 'readonly')
        self.rate_control.configure(state='disabled' if busy else 'readonly')
        self.preview_button.configure(state='normal' if not busy and self.batch_id and self.scope.get() == '本批次' else 'disabled')
        self.cancel_button.configure(state='normal' if busy else 'disabled')
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()

    def load_result(self):
        try:
            preview = self.flow.voice_preview(self.batch_id) if self.batch_id else None
            self.play_button.configure(state='normal' if preview else 'disabled')
            if preview:
                value = preview['settings']
                self.result_info.configure(text=f'上次成功：{value["voice"]} · {value["rate"]} · {len(preview["text"])} 字元 · {preview["source"]}')
            else:
                self.result_info.configure(text='尚無成功試聽。正式合成請按上方「批次 MP3／SRT」。')
        except ProjectError as error:
            self.result_info.configure(text=str(error))
            self.play_button.configure(state='disabled')

    def play(self):
        try:
            self.player.play(self.flow.voice_preview_path(self.batch_id))
            self.status.configure(text='正在播放上次成功試聽。')
            self.schedule()
        except ProjectError as error:
            self.status.configure(text=str(error))

    def stop(self):
        try:
            self.player.stop()
        except ProjectError as error:
            self.status.configure(text=str(error))

    def cancel(self):
        if self.job is not None:
            if self.job.wait(0) and self.kind == 'preview' and self.job.state['status'] == 'completed':
                self.poll()
                return
            self.job.cancel()
            self.status.configure(text='取消中，正在釋放連線與音訊資源…')

    def close(self):
        self.stop()
        if self.job is not None:
            if not self.job.wait(0):
                self.closing = True
                self.cancel()
                self.schedule()
                return
            if self.kind == 'preview':
                if not messagebox.askyesno('捨棄本次試聽', '關閉並捨棄本次尚未保存的試聽？上一份成功結果保留。', parent=self):
                    return
                self.flow.discard_voice_preview(self.job)
            self.job = None
        self.release()

    def release(self):
        self.stop()
        if self.timer is not None:
            self.after_cancel(self.timer)
            self.timer = None
        self.progress.stop()
        self.app.voice_dialog = None
        self.destroy()
