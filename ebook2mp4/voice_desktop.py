"""Native voice chooser and preview; no editor lock or automatic voice choice."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .workflow import ProjectError
from .voice import EXAMPLE, RATES
from .voice_media import PreviewPlayer


class VoiceDialog(ttk.Frame):
    def __init__(self, app):
        super().__init__(app.production.host)
        self.app, self.flow, self.batch_id = app, app.flow, app.batch_id
        self.job = None
        self.kind = ''
        self.timer = None
        self.closing = False
        self.player = PreviewPlayer()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        service_panel = ttk.LabelFrame(self, text='1 選擇服務', padding=6)
        service_panel.grid(row=0, column=0, sticky='ew', padx=6, pady=(0, 6))
        service_panel.columnconfigure(1, weight=1)
        service_panel.columnconfigure(3, weight=1)
        ttk.Label(service_panel, text='服務').grid(row=0, column=0, padx=(0, 4))
        self.service = tk.StringVar(value='edge-tts')
        self.service_control = ttk.Combobox(service_panel, textvariable=self.service, state='readonly', width=16)
        self.service_control.grid(row=0, column=1, sticky='ew')
        self.service_control.bind('<<ComboboxSelected>>', self.change_service)
        ttk.Label(service_panel, text='模型（可選或輸入）').grid(row=0, column=2, padx=6)
        self.model = tk.StringVar()
        self.model_control = ttk.Combobox(service_panel, textvariable=self.model, width=16)
        self.model_control.grid(row=0, column=3, sticky='ew')
        self.manage_button = ttk.Button(service_panel, text='新增／管理服務…', command=self.manage_services)
        self.manage_button.grid(row=0, column=4, padx=(6, 0))

        body = ttk.Frame(self)
        body.grid(row=1, column=0, sticky='nsew', padx=6)
        body.columnconfigure(0, weight=2, uniform='voice-body')
        body.columnconfigure(1, weight=4, uniform='voice-body')
        body.rowconfigure(0, weight=1)
        middle = ttk.LabelFrame(body, text='2 設定聲音與節奏', padding=6)
        middle.grid(row=0, column=0, sticky='nsew', padx=(0, 6))
        middle.columnconfigure(0, weight=1)
        self.catalog_actions = ttk.Frame(middle)
        self.catalog_actions.grid(row=0, column=0, sticky='ew', pady=(0, 4))
        self.catalog_actions.columnconfigure(0, weight=1)
        self.locale = tk.StringVar(value='全部語系')
        self.filter = ttk.Combobox(self.catalog_actions, textvariable=self.locale,
                                  values=('全部語系', '台灣華語', '中國普通話', '英文'), state='readonly', width=10)
        self.filter.grid(row=0, column=0, sticky='ew', padx=(0, 4))
        self.filter.bind('<<ComboboxSelected>>', lambda e: self.load_catalog())
        self.refresh_button = ttk.Button(self.catalog_actions, text='更新線上音色', command=self.refresh_voices)
        self.refresh_button.grid(row=0, column=1)
        self.voice = tk.StringVar()
        self.voice_label = ttk.Label(middle, text='音色（可選或輸入 ID）')
        self.voice_label.grid(row=1, column=0, sticky='w')
        self.voice_entry = ttk.Entry(middle, textvariable=self.voice, width=18)
        self.voice_entry.grid(row=2, column=0, sticky='ew', pady=(2, 4))
        self.voice_control = ttk.Combobox(middle, textvariable=self.voice, width=18)
        self.voice_control.grid(row=2, column=0, sticky='ew', pady=(2, 4))
        self.cache_info = ttk.Label(middle, text='', wraplength=260)
        self.cache_info.grid(row=3, column=0, sticky='ew', pady=(0, 6))
        rhythm = ttk.Frame(middle)
        rhythm.grid(row=4, column=0, sticky='ew')
        rhythm.columnconfigure(0, weight=1)
        rhythm.columnconfigure(1, weight=1)
        ttk.Label(rhythm, text='語速').grid(row=0, column=0, sticky='w')
        ttk.Label(rhythm, text='節奏').grid(row=0, column=1, sticky='w', padx=(6, 0))
        self.rate = tk.StringVar(value='正常')
        self.rate_control = ttk.Combobox(rhythm, textvariable=self.rate,
                                        values=('-20%', '-10%', '正常', '+10%', '+20%'), state='readonly', width=7)
        self.rate_control.grid(row=1, column=0, sticky='ew', pady=2)
        self.rhythm = tk.StringVar(value='自然')
        self.rhythm_control = ttk.Combobox(rhythm, textvariable=self.rhythm,
                                          values=('自然', '舒緩', '自訂'), state='readonly', width=7)
        self.rhythm_control.grid(row=1, column=1, sticky='ew', padx=(6, 0), pady=2)
        self.rhythm_control.bind('<<ComboboxSelected>>', self.apply_rhythm)
        ttk.Label(rhythm, text='句尾停頓（ms）').grid(row=2, column=0, sticky='w', pady=(6, 0))
        ttk.Label(rhythm, text='段落停頓（ms）').grid(row=2, column=1, sticky='w', padx=(6, 0), pady=(6, 0))
        self.sentence_pause = tk.StringVar(value='0')
        self.paragraph_pause = tk.StringVar(value='500')
        self.sentence_control = ttk.Spinbox(rhythm, from_=0, to=1500, textvariable=self.sentence_pause, width=6)
        self.sentence_control.grid(row=3, column=0, sticky='ew', pady=2)
        self.paragraph_control = ttk.Spinbox(rhythm, from_=0, to=3000, textvariable=self.paragraph_pause, width=6)
        self.paragraph_control.grid(row=3, column=1, sticky='ew', padx=(6, 0), pady=2)
        self.rules_info = ttk.Label(middle, text='相同邊界取較長停頓；最後不補靜音。', wraplength=260)
        self.rules_info.grid(row=5, column=0, sticky='ew', pady=(6, 0))
        self.rate_info = ttk.Label(middle, text='', wraplength=260)
        self.rate_info.grid(row=6, column=0, sticky='ew', pady=(4, 0))

        controls = ttk.LabelFrame(body, text='3 編輯文字並試聽', padding=6)
        controls.grid(row=0, column=1, sticky='nsew')
        controls.columnconfigure(0, weight=1)
        controls.rowconfigure(0, weight=1)
        text_frame = ttk.Frame(controls)
        text_frame.grid(row=0, column=0, sticky='nsew')
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        self.outgoing = tk.Text(text_frame, height=4, width=20, wrap='word', font=('Microsoft JhengHei', 11))
        self.outgoing.insert('1.0', EXAMPLE)
        self.outgoing.bind('<<Modified>>', self.text_changed)
        self.outgoing.grid(row=0, column=0, sticky='nsew')
        text_scroll = ttk.Scrollbar(text_frame, command=self.outgoing.yview)
        text_scroll.grid(row=0, column=1, sticky='ns')
        self.outgoing.configure(yscrollcommand=text_scroll.set)
        self.text_info = ttk.Label(controls, text='', wraplength=400)
        self.text_info.grid(row=1, column=0, sticky='ew', pady=4)
        self.consent = tk.BooleanVar(value=True)
        self.consent_control = ttk.Checkbutton(controls, text='同意傳送試聽文字（可能計費）', variable=self.consent)
        self.consent_control.grid(row=2, column=0, sticky='w', pady=2)
        actions = ttk.Frame(controls)
        actions.grid(row=3, column=0, sticky='ew')
        self.preview_button = ttk.Button(actions, text='產生並播放試聽', command=self.preview, style='Primary.TButton')
        self.preview_button.grid(row=0, column=0, pady=4)
        self.play_button = ttk.Button(actions, text='重播', command=self.play, width=5)
        self.play_button.grid(row=0, column=1, padx=4)
        self.stop_button = ttk.Button(actions, text='停止', command=self.stop, width=5)
        self.stop_button.grid(row=0, column=2)
        self.cancel_button = ttk.Button(actions, text='取消', command=self.cancel, width=5)
        self.cancel_button.grid(row=0, column=3, padx=(4, 0))
        self.result_info = ttk.Label(controls, text='', wraplength=400)
        self.result_info.grid(row=4, column=0, sticky='ew', pady=2)
        self.status = ttk.Label(controls, text='請選擇服務與音色。', wraplength=400)
        self.status.grid(row=5, column=0, sticky='ew', pady=2)
        self.progress = ttk.Progressbar(controls, mode='indeterminate')
        self.progress.grid(row=6, column=0, sticky='ew', pady=2)

        footer = ttk.Frame(self, padding=6)
        footer.grid(row=2, column=0, sticky='ew')
        footer.columnconfigure(1, weight=1)
        footer.columnconfigure(4, weight=1)
        self.back_button = ttk.Button(footer, text='← 返回確認朗讀稿', command=lambda: self.app.show_step(3))
        self.back_button.grid(row=0, column=0, sticky='w')
        self.scope = tk.StringVar(value='本批次' if self.batch_id else '全書預設')
        self.scope_control = ttk.Combobox(footer, textvariable=self.scope,
            values=('本批次', '全書預設') if self.batch_id else ('全書預設',), state='readonly', width=9)
        self.scope_control.grid(row=0, column=2, padx=6)
        self.scope_control.bind('<<ComboboxSelected>>', lambda e: self.load_settings())
        self.save_button = ttk.Button(footer, text='只儲存設定', command=self.save)
        self.save_button.grid(row=0, column=3)
        self.produce_button = ttk.Button(footer, text='儲存並前往製作 →', command=self.save_and_produce, style='Primary.TButton')
        self.produce_button.grid(row=0, column=5, sticky='e')
        self.apply_defaults_button = ttk.Button(footer, text='套用到既有批次…', command=self.open_defaults)
        self.apply_defaults_button.grid(row=0, column=5, sticky='e')
        self.rhythm_traces = [(variable, variable.trace_add('write', self.rhythm_changed))
                              for variable in (self.sentence_pause, self.paragraph_pause)]
        self.load_settings()
        self.prepare_text()
        self.load_result()
        self.update_controls()
        self.settings_panel, self.preview_panel = middle, controls
        middle.bind('<Configure>', self.reflow)
        controls.bind('<Configure>', self.reflow)

    def reflow(self, event):
        labels = ((self.cache_info, self.rules_info, self.rate_info)
                  if event.widget is self.settings_panel else
                  (self.status, self.result_info, self.text_info))
        for label in labels:
            label.configure(wraplength=max(140, event.width-16))

    def reload_services(self):
        from .tts_services import profiles
        self.service_labels={'edge-tts':'Edge-TTS'}
        self.service_labels.update({k:v['name']+' · '+k[:6] for k,v in profiles().items()})
        self.service_ids={v:k for k,v in self.service_labels.items()}
        self.service_control.configure(values=tuple(self.service_ids))

    def provider_name(self):
        from .tts_services import profiles
        identity=self.service_ids.get(self.service.get(),'edge-tts')
        if identity=='edge-tts': return 'edge-tts'
        value=profiles().get(identity)
        if value is None: raise ProjectError('本機尚未連結此服務，請在管理服務重新設定。')
        return value['provider']

    def change_service(self, _event=None):
        provider=self.provider_name()
        self.voice.set('')
        self.model.set('gemini-3.8-flash-lite-tts' if provider=='gemini-tts' else 's2.1-pro' if provider=='fish-audio' else '')
        self.load_catalog()
        self.update_controls()
        self.status.configure(text='服務已切換；請重新選音色及試聽，尚未儲存。')

    def save_and_produce(self):
        if self.scope.get()!='本批次':
            self.status.configure(text='請選本批次後再前往製作。');return
        try: self.flow.reading_text(self.batch_id)
        except ProjectError as error:
            self.status.configure(text=str(error));return
        if self.save(announce=False): self.app.narration()

    def manage_services(self):
        self.app.production.manage_services(self)

    def open_defaults(self):
        if self.job is not None or self.scope.get() != '全書預設':
            return
        try:
            if self.current_settings() != self.flow.voice_settings():
                raise ProjectError('請先儲存全書預設，再選擇要套用的批次。')
            if self.app.flow is not self.flow or self.app.batch_id != self.batch_id:
                raise ProjectError('書籍或批次已切換，請從目前批次重新開啟。')
            from .voice_defaults_desktop import VoiceDefaultsPage
            key = (id(self.flow), self.batch_id, 'defaults')
            page = self.app.production.pages.get(key)
            if page is None or not page.winfo_exists():
                page = VoiceDefaultsPage(self)
                self.app.production.pages[key] = page
            elif page.value != self.flow.voice_settings():
                page.value = self.flow.voice_settings()
                page.status.configure(text='全書預設已更新。保留批次選取，請重新核對套用後影響。')
            page.refresh()
            self.app.production.activate(page)
        except (ProjectError, ValueError) as error:
            self.status.configure(text=str(error))

    def load_settings(self):
        value = self.flow.voice_settings(self.batch_id if self.scope.get() == '本批次' else None)
        self.reload_services()
        identity=value.get('profile','edge-tts')
        if identity not in self.service_labels:
            self.service_labels[identity]='未連結服務 · '+identity[:6]
            self.service_ids[self.service_labels[identity]]=identity
        self.service.set(self.service_labels[identity])
        self.model.set(value.get('model',''))
        self.voice.set(value['voice'])
        self.rate.set('正常' if value['rate'] == '+0%' else value['rate'])
        self.sentence_pause.set(str(value['sentence_pause_ms']))
        self.paragraph_pause.set(str(value['paragraph_pause_ms']))
        self.status.configure(text='全書預設僅供新批次；既有批次須明確套用。' if self.scope.get() == '全書預設'
                              else '本批次設定獨立保存。')
        self.load_catalog()
        self.update_controls()

    def apply_rhythm(self, _event=None):
        preset = {'自然': (0, 500), '舒緩': (200, 800)}.get(self.rhythm.get())
        if preset:
            self.sentence_pause.set(str(preset[0]))
            self.paragraph_pause.set(str(preset[1]))

    def rhythm_changed(self, *_args):
        pair = (self.sentence_pause.get(), self.paragraph_pause.get())
        self.rhythm.set({('0', '500'): '自然', ('200', '800'): '舒緩'}.get(pair, '自訂'))

    def load_catalog(self):
        try:
            from .tts_services import MODELS, VOICES
            provider = self.provider_name()
            edge = provider == 'edge-tts'
            self.model_control.configure(values=() if edge else
                                         ('s2.1-pro', 's2.1-pro-free') if provider == 'fish-audio' else MODELS)
            if edge:
                self.catalog_actions.grid()
                catalog = self.flow.voice_catalog()
                locale = {'台灣華語': 'zh-TW', '中國普通話': 'zh-CN', '英文': 'en-'}.get(self.locale.get(), '')
                choices = tuple(v['id'] for v in catalog['voices'] if v['locale'].startswith(locale))
                self.cache_info.configure(text='更新：' + (catalog['updated_at'] or '尚未取得音色清單；更新不傳送書稿。'))
            else:
                self.catalog_actions.grid_remove()
                choices = VOICES if provider == 'gemini-tts' else ()
                self.cache_info.configure(text='內建音色候選，亦可手填 ID。' if provider == 'gemini-tts'
                                          else '輸入 Fish Audio 聲音 ID（reference_id）。')
            self.voice_control.configure(values=choices)
            if provider == 'fish-audio':
                self.voice_entry.grid()
                self.voice_control.grid_remove()
            else:
                self.voice_entry.grid_remove()
                self.voice_control.grid()
            self.voice_label.configure(text='聲音 ID（可直接輸入）' if provider == 'fish-audio' else '音色（可選或輸入 ID）')
            self.rate_info.configure(text='Gemini 語速以風格指示控制，請試聽確認。' if provider == 'gemini-tts' else '')
        except ProjectError as error:
            self.status.configure(text=str(error))

    def prepare_text(self):
        value = self.outgoing.get('1.0', 'end-1c')
        self.text_info.configure(text=f'{len(value):,}／3,000 字元 · 試聽不改校對稿。')
        return value

    def text_changed(self, _event=None):
        if self.outgoing.edit_modified():
            self.outgoing.edit_modified(False)
            self.prepare_text()

    def current_settings(self):
        from .voice import settings
        value = self.flow.voice_settings(self.batch_id if self.scope.get() == '本批次' else None)
        value.update(voice=self.voice.get(), rate='+0%' if self.rate.get() == '正常' else self.rate.get(),
                     sentence_pause_ms=int(self.sentence_pause.get()),
                     paragraph_pause_ms=int(self.paragraph_pause.get()))
        provider=self.provider_name()
        value['provider']=provider
        if provider!='edge-tts':
            value.update(profile=self.service_ids.get(self.service.get(),''),model=self.model.get().strip())
        else:
            value.pop('profile',None);value.pop('model',None)
        return settings(value)

    def save(self, *, announce=True):
        if self.app.flow is not self.flow or self.app.batch_id != self.batch_id:
            self.status.configure(text='主視窗的書籍或批次已切換；請關閉本視窗，回目前批次重新開啟語音設定。')
            return False
        try:
            self.flow.save_voice_settings(self.voice.get(), '+0%' if self.rate.get() == '正常' else self.rate.get(),
                                          batch_id=self.batch_id if self.scope.get() == '本批次' else None,
                                          sentence_pause_ms=int(self.sentence_pause.get()),
                                          paragraph_pause_ms=int(self.paragraph_pause.get()),settings_override=self.current_settings())
            self.status.configure(text='語音設定已儲存。')
            if announce:
                self.app.notify('語音設定已儲存。', owner=self)
            return True
        except ValueError:
            self.status.configure(text='請選有效音色與語速；句尾須為 0～1500、段落須為 0～3000 的整數毫秒。')
            return False
        except ProjectError as error:
            self.status.configure(text=str(error))
            return False

    def refresh_voices(self):
        if self.job or self.provider_name() != 'edge-tts':
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
            self.status.configure(text='請輸入 1～3,000 字元後再試聽。')
            return
        if self.app.flow is not self.flow or self.app.batch_id != self.batch_id:
            self.status.configure(text='主視窗的書籍或批次已切換；請關閉本視窗後重新開啟。')
            return
        try:
            value_settings = self.current_settings()
            self.stop()
            self.job = self.flow.start_voice_preview(self.batch_id, text=value, start=0, end=len(value),
                                                      settings_override=value_settings)
            self.kind = 'preview'
            self.status.configure(text='正在產生試聽…可繼續在主視窗校對，或取消。')
            self.schedule()
        except (ProjectError, ValueError) as error:
            self.status.configure(text=str(error) if isinstance(error, ProjectError) else '請輸入有效的整數毫秒。')

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
                self.status.configure(text='試聽已產生。' if state['status'] == 'completed' and self.kind == 'preview'
                                      else '音色清單已更新；請明確選擇音色。' if state['status'] == 'completed'
                                      else '已取消；上一份成功結果保留。' if state['status'] == 'cancelled' else state['error'])
                if state['status'] == 'completed' and self.kind == 'preview' and not self.closing and self.winfo_ismapped():
                    self.play()
                if not self.closing:
                    self.app.notify(self.status.cget('text'), owner=self,
                                    kind='success' if state['status'] == 'completed' else
                                    'info' if state['status'] == 'cancelled' else 'error')
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
        defaults = self.scope.get() == '全書預設'
        self.save_button.configure(text='儲存全書預設' if defaults else '只儲存設定')
        self.apply_defaults_button.grid() if defaults else self.apply_defaults_button.grid_remove()
        self.apply_defaults_button.configure(state='disabled' if busy else 'normal')
        self.set_production_busy(self.app.production.busy_for(self.flow))
        for control in (self.refresh_button, self.save_button):
            control.configure(state='disabled' if busy else 'normal')
        self.scope_control.configure(state='disabled' if busy else 'readonly')
        self.rate_control.configure(state='disabled' if busy else 'readonly')
        self.service_control.configure(state='disabled' if busy else 'readonly')
        self.model_control.configure(state='disabled' if busy or self.service_ids.get(self.service.get())=='edge-tts' else 'normal')
        self.manage_button.configure(state='disabled' if busy else 'normal')
        self.rhythm_control.configure(state='disabled' if busy else 'readonly')
        for spinbox in (self.sentence_control, self.paragraph_control):
            spinbox.configure(state='disabled' if busy else 'normal')
        self.preview_button.configure(state='normal' if not busy and self.batch_id else 'disabled')
        self.cancel_button.configure(state='normal' if busy else 'disabled')
        self.produce_button.configure(state='disabled' if busy else 'normal')
        self.produce_button.grid_remove() if defaults else self.produce_button.grid()
        self.voice_entry.configure(state='disabled' if busy else 'normal')
        self.voice_control.configure(state='disabled' if busy else 'normal')
        self.filter.configure(state='disabled' if busy else 'readonly')
        if busy:
            self.cancel_button.grid()
            self.progress.grid()
            self.progress.start(12)
        else:
            self.cancel_button.grid_remove()
            self.progress.stop()
            self.progress.grid_remove()

    def set_production_busy(self, busy):
        self.apply_defaults_button.configure(state='disabled' if busy or self.job is not None else 'normal')

    def load_result(self):
        try:
            preview = self.flow.voice_preview(self.batch_id) if self.batch_id else None
            self.play_button.configure(state='normal' if preview else 'disabled')
            if preview:
                value = preview['settings']
                self.result_info.configure(text=f'上次成功：{value["voice"]} · {len(preview["text"])} 字元（可能與目前設定不同）')
            else:
                self.result_info.configure(text='尚未產生試聽。')
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
                    return False
                self.flow.discard_voice_preview(self.job)
            self.job = None
        self.release()
        return True

    def release(self):
        self.stop()
        for variable, token in self.rhythm_traces:
            variable.trace_remove('write', token)
        self.rhythm_traces.clear()
        if self.timer is not None:
            self.after_cancel(self.timer)
            self.timer = None
        self.progress.stop()
        self.app.voice_dialog = None
        self.destroy()
