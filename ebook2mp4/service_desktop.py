"""Local credential setup, separate from daily synthesis controls."""
import tkinter as tk
from tkinter import ttk
from .workflow import ProjectError
from .tts_services import profiles, save_profile


class ServiceDialog(ttk.Frame):
    def __init__(self, owner, *, parent=None, on_return=None):
        super().__init__(parent if parent is not None else owner)
        self.on_return=on_return;self.owner=owner;self.job=None;self.identity=None;self.timer=None
        if parent is None:
            self.pack(fill='both',expand=True)
        self.columnconfigure(0,weight=1)
        form=ttk.Frame(self,padding=20);form.grid(sticky='nsew');form.columnconfigure(1,weight=1)
        ttk.Label(form,text='1 選服務 → 2 填資料 → 3 檢查服務並返回試聽',style='Heading.TLabel').grid(row=0,column=0,columnspan=2,pady=12)
        self.existing=tk.StringVar(value='新增服務')
        self.items={'新增服務':None};self.items.update({v['name']+' · '+k[:6]:k for k,v in profiles().items()})
        combo=ttk.Combobox(form,textvariable=self.existing,values=tuple(self.items),state='readonly');combo.grid(row=1,column=1,sticky='ew',pady=8)
        ttk.Label(form,text='設定檔').grid(row=1,column=0,sticky='w');combo.bind('<<ComboboxSelected>>',self.load)
        self.provider=tk.StringVar(value='Google Gemini TTS');self.name=tk.StringVar(value='Google Gemini TTS');self.key=tk.StringVar();self.reuse=tk.BooleanVar(value=False)
        ttk.Label(form,text='服務類型').grid(row=2,column=0,sticky='w')
        self.provider_control=ttk.Combobox(form,textvariable=self.provider,values=('Google Gemini TTS','Fish Audio'),state='readonly')
        self.provider_control.grid(row=2,column=1,sticky='ew',pady=8)
        self.provider_control.bind('<<ComboboxSelected>>',self.provider_changed)
        ttk.Label(form,text='顯示名稱').grid(row=3,column=0,sticky='w');ttk.Entry(form,textvariable=self.name).grid(row=3,column=1,sticky='ew',pady=8)
        ttk.Label(form,text='API 金鑰').grid(row=4,column=0,sticky='w');self.key_entry=ttk.Entry(form,textvariable=self.key,show='•');self.key_entry.grid(row=4,column=1,sticky='ew',pady=8)
        self.reuse_check=ttk.Checkbutton(form,text='Google：沿用本機 Gemini 校對金鑰',variable=self.reuse,command=self.reuse_changed)
        self.reuse_check.grid(row=5,column=1,sticky='w')
        self.manual_key='' 
        ttk.Label(form,text='金鑰只在本機加密保存；編輯時留空保留原金鑰。\n儲存不會送出文字。返回後請選模型與音色，再按試聽驗證。\n本版支援 Gemini API 與 Fish 原生 API；尚不支援任意相容端點。',wraplength=600).grid(row=6,column=0,columnspan=2,sticky='w',pady=16)
        self.check_button=ttk.Button(form,text='檢查連線與音色（不產生語音）',command=self.check)
        self.check_button.grid(row=7,column=0,columnspan=2,sticky='ew',pady=8)
        self.status=ttk.Label(form,text='',wraplength=600);self.status.grid(row=8,column=0,columnspan=2,sticky='ew')
        ttk.Button(form,text='取消',command=self.close).grid(row=9,column=0,pady=16)
        ttk.Button(form,text='儲存並返回試聽 →',command=self.save,style='Primary.TButton').grid(row=9,column=1,sticky='e')

    def load(self,_event=None):
        self.identity=self.items[self.existing.get()]
        value=profiles().get(self.identity)
        self.key.set('')
        self.manual_key=''
        if value:
            self.name.set(value['name']);self.provider.set({'gemini-tts':'Google Gemini TTS','fish-audio':'Fish Audio'}[value['provider']]);self.reuse.set(value.get('reuse',False))
        else:
            self.provider.set('Google Gemini TTS');self.name.set('Google Gemini TTS');self.reuse.set(False)
        self.update_provider()
        self.reuse_changed()

    def provider_changed(self, _event=None):
        self.name.set(self.provider.get())
        self.reuse.set(False)
        self.manual_key=''
        self.key.set('')
        self.update_provider()
        self.reuse_changed()

    def update_provider(self):
        if self.provider.get() == 'Google Gemini TTS':
            self.reuse_check.grid()
        else:
            self.reuse_check.grid_remove()

    def reuse_changed(self):
        if self.reuse.get() and self.provider.get() == 'Google Gemini TTS':
            from .gemini import load_settings
            try:
                key=load_settings()['key']
                if not key:
                    raise ProjectError('尚未設定 Gemini 校對金鑰；請先設定或自行輸入。')
            except ProjectError as error:
                self.reuse.set(False)
                self.status.configure(text=str(error))
                return
            self.manual_key=self.key.get()
            self.key.set(key)
            self.key_entry.configure(state='readonly')
            self.status.configure(text='已沿用 Gemini 校對金鑰。')
        else:
            self.key_entry.configure(state='normal')
            self.key.set(self.manual_key)
            self.manual_key=''
            self.status.configure(text='')

    def save(self):
        if self.job:
            self.status.configure(text='請等待服務檢查完成。');return
        try:
            identity=save_profile(self.name.get(),{'Google Gemini TTS':'gemini-tts','Fish Audio':'fish-audio'}[self.provider.get()],'' if self.reuse.get() else self.key.get(),self.reuse.get(),self.identity)
            self.identity=identity
            self.key.set('');self.owner.reload_services();self.owner.service.set(self.owner.service_labels[identity]);self.owner.change_service();self.close()
        except (ProjectError,OSError) as error:self.status.configure(text=str(error) if isinstance(error,ProjectError) else '無法儲存本機服務設定。')


    def check(self):
        if self.job:return
        try:
            self.identity=save_profile(self.name.get(),{'Google Gemini TTS':'gemini-tts','Fish Audio':'fish-audio'}[self.provider.get()],'' if self.reuse.get() else self.key.get(),self.reuse.get(),self.identity)
            if not self.reuse.get(): self.key.set('')
            from .voice import VoiceJob
            from .tts_services import check_profile
            self.job=VoiceJob(lambda:check_profile(self.identity))
            self.status.configure(text='已儲存本機設定，正在檢查服務…')
            self.check_button.configure(state='disabled')
            self.timer=self.after(100,self.poll)
        except (ProjectError,OSError) as error:self.status.configure(text=str(error) if isinstance(error,ProjectError) else '本機設定無法儲存。')

    def poll(self):
        self.timer=None
        if not self.job:return
        if not self.job.wait(0):self.timer=self.after(100,self.poll);return
        self.status.configure(text=self.job.result if self.job.state['status']=='completed' else self.job.state['error'] or '已取消')
        self.job=None;self.check_button.configure(state='normal')

    def close(self):
        if self.timer is not None:
            self.after_cancel(self.timer);self.timer=None
        if self.job:
            self.job.cancel()
            if not self.job.wait(0):self.timer=self.after(100,self.close);return
            self.job=None
        self.key.set('');self.destroy()
        if self.on_return is not None:self.on_return()
