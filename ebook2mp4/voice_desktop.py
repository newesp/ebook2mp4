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
        self.minsize(1100, 740)
        from .tts_services import MODELS
        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=3)
        self.columnconfigure(2, weight=4)
        self.rowconfigure(1, weight=1)
        ttk.Label(self, text='語音設定與試聽 · 由左往右設定，再往下製作', style='Heading.TLabel').grid(row=0,column=0,columnspan=3,sticky='w',padx=16,pady=16)
        left=ttk.LabelFrame(self,text='1 選擇服務',padding=16)
        left.grid(row=1,column=0,sticky='nsew',padx=(16,8))
        left.columnconfigure(0,weight=1)
        self.service=tk.StringVar(value='edge-tts')
        self.service_control=ttk.Combobox(left,textvariable=self.service,state='readonly',width=28)
        self.service_control.grid(row=0,column=0,sticky='ew',pady=6)
        self.service_control.bind('<<ComboboxSelected>>',self.change_service)
        self.manage_button=ttk.Button(left,text='新增／管理服務…',command=self.manage_services)
        self.manage_button.grid(row=1,column=0,sticky='ew',pady=8)
        ttk.Label(left,text='模型（可選擇或直接輸入）').grid(row=2,column=0,sticky='w',pady=(18,4))
        self.model=tk.StringVar()
        self.model_control=ttk.Combobox(left,textvariable=self.model,values=MODELS,width=28)
        self.model_control.grid(row=3,column=0,sticky='ew')
        ttk.Label(left,text='新模型可直接輸入 ID。\n試聽可能產生費用；不自動換模型。',wraplength=260).grid(row=4,column=0,sticky='w',pady=8)
        self.refresh_button=ttk.Button(left,text='更新 Edge 線上音色',command=self.refresh_voices)
        self.refresh_button.grid(row=5,column=0,sticky='ew',pady=8)
        self.cache_info=ttk.Label(left,text='',wraplength=260)
        self.cache_info.grid(row=6,column=0,sticky='ew')
        middle=ttk.LabelFrame(self,text='2 選擇聲音與節奏',padding=16)
        middle.grid(row=1,column=1,sticky='nsew',padx=8)
        middle.columnconfigure(0,weight=1)
        middle.rowconfigure(1,weight=1)
        self.locale=tk.StringVar(value='全部語系')
        self.filter=ttk.Combobox(middle,textvariable=self.locale,values=('全部語系','台灣華語','中國普通話','英文'),state='readonly')
        self.filter.grid(row=0,column=0,sticky='ew',pady=4)
        self.filter.bind('<<ComboboxSelected>>',lambda e:self.load_catalog())
        self.voices=ttk.Treeview(middle,columns=('name','locale','gender'),show='headings',height=5,selectmode='browse')
        for key,label,width in (('name','音色',200),('locale','語系',70),('gender','性別',60)):
            self.voices.heading(key,text=label)
            self.voices.column(key,width=width,minwidth=40)
        self.voices.grid(row=1,column=0,sticky='nsew')
        self.voices.bind('<<TreeviewSelect>>',self.choose_voice)
        self.voice=tk.StringVar()
        ttk.Label(middle,text='音色 ID（可直接輸入）').grid(row=2,column=0,sticky='w',pady=(8,0))
        self.voice_entry=ttk.Entry(middle,textvariable=self.voice)
        self.voice_entry.grid(row=3,column=0,sticky='ew',pady=4)
        self.rate=tk.StringVar(value='正常')
        ttk.Label(middle,text='語速（Gemini 以風格指示控制，實際聽感須試聽）',wraplength=340).grid(row=4,column=0,sticky='w')
        self.rate_control=ttk.Combobox(middle,textvariable=self.rate,values=('-20%','-10%','正常','+10%','+20%'),state='readonly')
        self.rate_control.grid(row=5,column=0,sticky='ew',pady=4)
        self.rhythm=tk.StringVar(value='自然')
        self.rhythm_control=ttk.Combobox(middle,textvariable=self.rhythm,values=('自然','舒緩','自訂'),state='readonly')
        self.rhythm_control.grid(row=6,column=0,sticky='ew',pady=8)
        self.rhythm_control.bind('<<ComboboxSelected>>',self.apply_rhythm)
        pauses=ttk.Frame(middle);pauses.grid(row=7,column=0,sticky='ew')
        self.sentence_pause=tk.StringVar(value='0');self.paragraph_pause=tk.StringVar(value='500')
        ttk.Label(pauses,text='句尾 ms').grid(row=0,column=0)
        self.sentence_control=ttk.Spinbox(pauses,from_=0,to=1500,textvariable=self.sentence_pause,width=6)
        self.sentence_control.grid(row=0,column=1,padx=4)
        ttk.Label(pauses,text='段落 ms').grid(row=1,column=0)
        self.paragraph_control=ttk.Spinbox(pauses,from_=0,to=3000,textvariable=self.paragraph_pause,width=6)
        self.paragraph_control.grid(row=1,column=1,padx=4,pady=4)
        controls=ttk.LabelFrame(self,text='3 編輯文字並試聽',padding=16)
        controls.grid(row=1,column=2,sticky='nsew',padx=(8,16))
        controls.columnconfigure(0,weight=1);controls.rowconfigure(0,weight=1)
        self.outgoing=tk.Text(controls,height=8,width=20,wrap='word',font=('Microsoft JhengHei',11))
        self.outgoing.insert('1.0',EXAMPLE);self.outgoing.bind('<<Modified>>',self.text_changed)
        self.outgoing.grid(row=0,column=0,sticky='nsew')
        self.text_info=ttk.Label(controls,text='',wraplength=400);self.text_info.grid(row=1,column=0,sticky='ew',pady=6)
        self.rules_info=ttk.Label(controls,text='試聽不改校對稿。相同邊界取較長停頓，最後不補靜音。',wraplength=400)
        self.rules_info.grid(row=2,column=0,sticky='ew',pady=6)
        self.consent=tk.BooleanVar(value=True)
        self.consent_control=ttk.Checkbutton(controls,text='同意將試聽文字傳送至所選服務（可能計費）',variable=self.consent)
        self.consent_control.grid(row=3,column=0,sticky='w',pady=6)
        actions=ttk.Frame(controls);actions.grid(row=4,column=0,sticky='ew')
        self.preview_button=ttk.Button(actions,text='產生並播放試聽',command=self.preview,style='Primary.TButton');self.preview_button.grid(row=0,column=0,pady=4,sticky='w')
        self.cancel_button=ttk.Button(actions,text='取消',command=self.cancel,state='disabled');self.cancel_button.grid(row=0,column=1,padx=4)
        self.play_button=ttk.Button(actions,text='重播上次結果',command=self.play);self.play_button.grid(row=1,column=0,pady=4)
        self.stop_button=ttk.Button(actions,text='停止播放',command=self.stop);self.stop_button.grid(row=1,column=1,padx=4)
        self.result_info=ttk.Label(controls,text='',wraplength=400);self.result_info.grid(row=5,column=0,sticky='ew',pady=6)
        self.status=ttk.Label(controls,text='請選擇服務與音色。',wraplength=400);self.status.grid(row=6,column=0,sticky='ew')
        self.progress=ttk.Progressbar(controls,mode='indeterminate');self.progress.grid(row=7,column=0,sticky='ew',pady=6)
        footer=ttk.LabelFrame(self,text='4 儲存設定，前往製作',padding=12)
        footer.grid(row=2,column=0,columnspan=3,sticky='ew',padx=16,pady=16)
        self.scope=tk.StringVar(value='本批次' if self.batch_id else '全書預設')
        self.scope_control=ttk.Combobox(footer,textvariable=self.scope,values=('本批次','全書預設') if self.batch_id else ('全書預設',),state='readonly',width=12)
        self.scope_control.pack(side='left');self.scope_control.bind('<<ComboboxSelected>>',lambda e:self.load_settings())
        self.save_button=ttk.Button(footer,text='只儲存設定',command=self.save);self.save_button.pack(side='left',padx=8)
        ttk.Button(footer,text='關閉',command=self.close).pack(side='right')
        self.produce_button=ttk.Button(footer,text='儲存並前往製作 →',command=self.save_and_produce,style='Primary.TButton');self.produce_button.pack(side='right',padx=8)
        self.rhythm_traces = [(variable, variable.trace_add('write', self.rhythm_changed))
                              for variable in (self.sentence_pause, self.paragraph_pause)]
        self.load_settings()
        self.load_catalog()
        self.prepare_text()
        self.load_result()
        self.update_controls()
        self.after_idle(lambda: self.state('zoomed') if self.winfo_exists() else None)

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
        from .service_desktop import ServiceDialog
        ServiceDialog(self)

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
            from .tts_services import VOICES
            identity=self.service_ids.get(self.service.get(),'edge-tts')
            provider=self.provider_name()
            self.model_control.configure(values=('s2.1-pro','s2.1-pro-free') if provider=='fish-audio' else ('gemini-3.8-flash-lite-tts','gemini-3.8-flash-tts'))
            catalog: dict = self.flow.voice_catalog() if identity=='edge-tts' else dict(updated_at='內建候選；亦可手填音色ID',voices=[dict(id=v,name=v,locale='',gender='') for v in VOICES] if self.provider_name()=='gemini-tts' else [])
            self.voices.delete(*self.voices.get_children())
            locale = {'台灣華語': 'zh-TW', '中國普通話': 'zh-CN', '英文': 'en-'}.get(self.locale.get(), '')
            for voice in catalog['voices']:
                if identity!='edge-tts' or voice['locale'].startswith(locale):
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
        value = self.outgoing.get('1.0', 'end-1c')
        self.text_info.configure(text=f'{len(value):,} 字元 · 上限 3,000 字元。編輯後按「產生並播放試聽」。')
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
                if state['status'] == 'completed' and self.kind == 'preview' and not self.closing:
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
                self.result_info.configure(text=f'上次成功（可能與目前設定不同）：{value["provider"]} {value.get("model", "")} · {value["voice"]} · {value["rate"]} · {value["sentence_pause_ms"]}/{value["paragraph_pause_ms"]} ms · {len(preview["text"])} 字元')
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
        for variable, token in self.rhythm_traces:
            variable.trace_remove('write', token)
        self.rhythm_traces.clear()
        if self.timer is not None:
            self.after_cancel(self.timer)
            self.timer = None
        self.progress.stop()
        self.app.voice_dialog = None
        self.destroy()
