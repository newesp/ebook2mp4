"""Local service editor in the production workspace, with explicit save/delete."""
import tkinter as tk
from tkinter import ttk
from .workflow import ProjectError
from .tts_services import profiles, save_profile, delete_profile, credential, check_service
from .production_desktop import ScrollPage


PROVIDERS = {'Google Gemini TTS': 'gemini-tts', 'Fish Audio': 'fish-audio'}


class ServiceDialog(ttk.Frame):
    page_id = 'voice.services'
    def __init__(self, owner, *, parent=None, on_return=None, profile_id=None):
        super().__init__(parent if parent is not None else owner, padding=0 if hasattr(owner,'app') else 12)
        self.owner, self.on_return = owner, on_return
        self.workspace = owner.app.production if hasattr(owner, 'app') else None
        self.app = owner.app if hasattr(owner,'app') else None
        self.flow = getattr(owner, 'flow', None)
        self.job = self.timer = None
        self.closing = False
        self.identity = None
        self.manual_key = ''
        self.baseline = None
        self.pending = None
        self.profile_unavailable = False
        if parent is None: self.pack(fill='both', expand=True)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        ttk.Style(self).configure('ServiceDanger.TButton', foreground='#963b32')
        self.title = ttk.Label(self, style='Heading.TLabel')
        self.shell_header = self.title
        self.title.grid(row=0, column=0, sticky='w', pady=(0,12))
        body = ttk.Frame(self,padding=(12,0))
        body.grid(row=1, column=0, sticky='nsew')
        body.columnconfigure(0, weight=3, uniform='service-editor')
        body.columnconfigure(1, weight=1, uniform='service-editor')
        body.rowconfigure(0, weight=1)
        self.scroll = ScrollPage(body)
        self.scroll.grid(row=0, column=0, sticky='nsew', padx=(0,16))
        form = self.scroll.content
        form.columnconfigure(0, weight=1)
        self.provider = tk.StringVar(value='Google Gemini TTS')
        self.name = tk.StringVar(value='Google Gemini TTS')
        self.key = tk.StringVar()
        self.reuse = tk.BooleanVar(value=False)
        ttk.Label(form,text='服務類型').grid(row=0,column=0,sticky='w')
        self.provider_control = ttk.Combobox(form,textvariable=self.provider,values=tuple(PROVIDERS),state='readonly',width=1)
        self.provider_control.grid(row=1,column=0,sticky='ew',pady=(4,4))
        self.provider_control.bind('<<ComboboxSelected>>',self.provider_changed)
        self.provider_help = ttk.Label(form,wraplength=500)
        self.provider_help.grid(row=2,column=0,sticky='ew',pady=(0,12))
        ttk.Label(form,text='顯示名稱').grid(row=3,column=0,sticky='w')
        self.name_entry = ttk.Entry(form,textvariable=self.name,width=1)
        self.name_entry.grid(row=4,column=0,sticky='ew',pady=(4,12))
        self.key_label = ttk.Label(form)
        self.key_label.grid(row=5,column=0,sticky='w')
        key_row = ttk.Frame(form)
        key_row.grid(row=6,column=0,sticky='ew',pady=(4,4))
        key_row.columnconfigure(0,weight=1)
        self.key_entry = ttk.Entry(key_row,textvariable=self.key,show='•',width=1)
        self.key_entry.grid(row=0,column=0,sticky='ew')
        self.show_button = ttk.Button(key_row,text='顯示',command=self.toggle_key,width=5)
        self.show_button.grid(row=0,column=1,padx=(8,0))
        self.key_help = ttk.Label(form,wraplength=500)
        self.key_help.grid(row=7,column=0,sticky='ew',pady=(0,8))
        # Status stays near the credential fields and is visible in narrow windows.
        self.status = ttk.Label(form,text='',wraplength=500)
        self.status.grid(row=8,column=0,sticky='ew',pady=4)
        self.reuse_check = ttk.Checkbutton(form,text='沿用本機 Gemini 校對金鑰',variable=self.reuse,command=self.reuse_changed)
        self.reuse_check.grid(row=9,column=0,sticky='w',pady=(0,8))
        self.check_button = ttk.Button(form,text='檢查連線與音色（不產生語音）',command=self.check)
        self.check_button.grid(row=10,column=0,sticky='w',pady=4)
        self.discard_frame = ttk.LabelFrame(form,text='要放棄尚未儲存的修改嗎？',padding=8)
        self.discard_frame.grid(row=11,column=0,sticky='ew',pady=12)
        self.keep_button = ttk.Button(self.discard_frame,text='繼續編輯',command=self.keep_editing)
        self.keep_button.pack(side='left')
        self.discard_button = ttk.Button(self.discard_frame,text='放棄修改',command=self.discard)
        self.discard_button.pack(side='right')
        self.discard_frame.grid_remove()
        self.delete_frame = ttk.LabelFrame(form,text='刪除此服務？',padding=8)
        self.delete_frame.grid(row=12,column=0,sticky='ew',pady=12)
        self.delete_frame.columnconfigure(0,weight=1)
        self.delete_text = ttk.Label(self.delete_frame,wraplength=500)
        self.delete_text.grid(row=0,column=0,columnspan=2,sticky='ew')
        self.cancel_delete_button = ttk.Button(self.delete_frame,text='保留服務',command=self.cancel_delete)
        self.cancel_delete_button.grid(row=1,column=0,sticky='w',pady=(8,0))
        self.confirm_delete_button = ttk.Button(self.delete_frame,text='確認刪除服務',command=self.delete,style='ServiceDanger.TButton')
        self.confirm_delete_button.grid(row=1,column=1,sticky='e',pady=(8,0))
        self.delete_frame.grid_remove()
        aside = ttk.Frame(body,padding=8)
        aside.grid(row=0,column=1,sticky='new')
        aside.columnconfigure(0,weight=1)
        self.help = ttk.Label(aside,text='修改後，回到原來的試聽頁\n\n儲存後選用此服務，保留試聽文字及節奏設定。\n\n金鑰只在本機加密保存。儲存不送出文字；請返回後重新試聽。',wraplength=220,justify='left')
        self.help.grid(row=0,column=0,sticky='ew')
        self.details_button = ttk.Button(aside,text='查看設定檔識別碼',command=self.toggle_details)
        self.details_button.grid(row=1,column=0,sticky='w',pady=12)
        self.details = ttk.Label(aside,text='',wraplength=220)
        self.details.grid(row=2,column=0,sticky='ew')
        self.details.grid_remove()
        if self.app is not None:
            self.shell_footer = footer = self.app.shell.create_footer(self,workspace_aligned=True)
        else:
            footer=ttk.Frame(self)
            footer.grid(row=2,column=0,sticky='ew',pady=(12,0))
        footer.columnconfigure(1,weight=1)
        self.back_button = footer.button('← 取消並返回試聽',self.request_return,role='back') if self.app else ttk.Button(footer,text='← 取消並返回試聽',command=self.request_return)
        self.back_button.grid(row=0,column=0,sticky='w')
        self.delete_button = footer.button('刪除此服務…',self.confirm_delete,role='destructive') if self.app else ttk.Button(footer,text='刪除此服務…',command=self.confirm_delete,style='ServiceDanger.TButton')
        self.delete_button.grid(row=0,column=2,padx=8)
        self.save_button = footer.button('儲存並返回試聽 →',self.save,role='primary') if self.app else ttk.Button(footer,text='儲存並返回試聽 →',command=self.save,style='Primary.TButton')
        self.save_button.grid(row=0,column=3,sticky='e')
        self.scroll.bind_scroll()
        form.bind('<Configure>',self.resize,add='+')
        aside.bind('<Configure>',lambda e:[label.configure(wraplength=max(1,e.width-16)) for label in (self.help,self.details)],add='+')
        self.load_profile(profile_id)

    def resize(self, event):
        width=max(180,event.width-20)
        for label in (self.status,self.key_help,self.provider_help,self.delete_text):
            label.configure(wraplength=width)

    def snapshot(self):
        return self.provider.get(),self.name.get(),self.key.get(),self.reuse.get()

    def load_profile(self, identity):
        try:
            value=profiles().get(identity) if identity else None
            if identity and not value: raise ProjectError('此服務已被移除；請返回後重新選擇服務。')
        except ProjectError as error:
            self.profile_unavailable=True
            self.identity=identity
            self.status.configure(text=str(error))
            self.save_button.configure(state='disabled')
            return
        self.profile_unavailable=False
        self.identity=identity
        self.key.set('');self.manual_key=''
        self.provider.set(next(k for k,v in PROVIDERS.items() if v==value['provider']) if value else 'Google Gemini TTS')
        self.name.set(value['name'] if value else self.provider.get())
        self.reuse.set(bool(value and value.get('reuse')))
        self.title.configure(text='編輯服務' if identity else '新增服務')
        self.provider_help.configure(text='既有服務類型固定。如需更換類型，請新增服務。' if identity else '選擇服務類型，再填名稱與金鑰。')
        self.key_label.configure(text='更換 API 金鑰' if identity else 'API 金鑰')
        self.details.configure(text=identity or '儲存後建立識別碼。')
        self.details.grid_remove()
        self.delete_button.grid() if identity else self.delete_button.grid_remove()
        self.delete_frame.grid_remove();self.discard_frame.grid_remove()
        self.status.configure(text='')
        self.key_entry.configure(show='•');self.show_button.configure(text='顯示')
        self.update_provider();self.update_controls()
        self.baseline=self.snapshot()
        self.scroll.canvas.yview_moveto(0)

    def request_profile(self, identity):
        self.flow=getattr(self.owner,'flow',None)
        if identity==self.identity: return
        if self.job:
            self.status.configure(text='請先取消服務檢查。');return
        self.request_action(lambda:self.load_profile(identity))

    def request_action(self, action):
        if self.baseline is not None and self.snapshot()!=self.baseline:
            self.pending=action
            self.delete_frame.grid_remove();self.discard_frame.grid()
            self.keep_button.focus_set();self.reveal_confirmation()
        else: action()

    def request_return(self):
        if not self.job: self.request_action(self.close)

    def keep_editing(self):
        self.pending=None;self.discard_frame.grid_remove()

    def discard(self):
        action=self.pending
        self.keep_editing()
        if action: action()

    def toggle_details(self):
        self.details.grid_remove() if self.details.winfo_manager() else self.details.grid()

    def toggle_key(self):
        show=bool(self.key_entry.cget('show'))
        self.key_entry.configure(show='' if show else '•')
        self.show_button.configure(text='隱藏' if show else '顯示')

    def provider_changed(self, _event=None):
        self.name.set(self.provider.get());self.reuse.set(False)
        self.manual_key='';self.key.set('');self.update_provider()

    def update_provider(self):
        self.reuse_check.grid() if self.provider.get()=='Google Gemini TTS' else self.reuse_check.grid_remove()
        self.key_help.configure(text='已保存金鑰。留白則保留原金鑰。' if self.identity else '請輸入 API 金鑰。金鑰只在本機加密保存。')
        self.update_controls()

    def reuse_changed(self):
        if self.reuse.get():
            from .gemini import load_settings
            try:
                key=load_settings()['key']
                if not key: raise ProjectError('尚未設定 Gemini 校對金鑰；請先設定或自行輸入。')
            except ProjectError as error:
                self.reuse.set(False);self.status.configure(text=str(error));return
            self.manual_key=self.key.get();self.key.set(key)
        else:
            self.key.set(self.manual_key);self.manual_key=''
        self.update_controls()

    def mutation_busy(self):
        return bool(self.workspace and self.workspace.service_changes_busy())

    def set_production_busy(self, _busy):
        self.update_controls()

    def update_controls(self):
        busy=self.job is not None
        blocked=busy or self.profile_unavailable or self.mutation_busy()
        for control in (self.name_entry,self.reuse_check,self.show_button):
            control.configure(state='disabled' if busy else 'normal')
        self.provider_control.configure(state='disabled' if busy or self.identity else 'readonly')
        self.key_entry.configure(state='disabled' if busy else 'readonly' if self.reuse.get() else 'normal')
        for control in (self.save_button,self.delete_button,self.confirm_delete_button):
            control.configure(state='disabled' if blocked else 'normal')
        self.back_button.configure(state='disabled' if busy else 'normal')
        self.check_button.configure(text='取消檢查' if busy else '檢查連線與音色（不產生語音）')

    def ensure_mutable(self):
        if self.profile_unavailable:
            self.status.configure(text='服務設定無法讀取；請返回後重新選擇服務。')
            return False
        if self.job or self.mutation_busy():
            self.status.configure(text='請先完成或取消進行中的語音任務，再儲存或刪除服務。')
            return False
        return True

    def save(self):
        if not self.ensure_mutable(): return
        try:
            identity=save_profile(self.name.get(),PROVIDERS[self.provider.get()],'' if self.reuse.get() else self.key.get(),self.reuse.get(),self.identity)
            self.identity=identity
            if self.workspace:
                self.workspace.refresh_services(identity)
            else:
                self.owner.reload_services();self.owner.service.set(self.owner.service_labels[identity]);self.owner.change_service()
            self.owner.status.configure(text='服務已儲存。請重新試聽。')
            self.close()
        except (ProjectError,OSError) as error:
            self.status.configure(text=str(error) if isinstance(error,ProjectError) else '無法儲存本機服務設定；原設定保留，請重試。')

    def reveal_confirmation(self):
        self.update_idletasks();self.scroll.canvas.yview_moveto(1)

    def confirm_delete(self):
        if not self.identity or not self.ensure_mutable(): return
        try:
            stored=profiles().get(self.identity)
            if not stored: raise ProjectError('此服務不存在或已被移除。')
        except ProjectError as error:
            self.status.configure(text=str(error));return
        self.delete_text.configure(text=f'將刪除「{stored["name"]}」的本機設定與此設定保存的金鑰。\n返回後改用 Edge-TTS，請重新選音色。\n既有音訊、字幕與稿件保留。其他引用此服務的批次下次使用前須重新選服務。共用的 Gemini 校對金鑰保留。')
        self.discard_frame.grid_remove();self.delete_frame.grid()
        self.scroll.reveal(self.delete_frame)
        self.cancel_delete_button.focus_set();self.reveal_confirmation()

    def cancel_delete(self):
        self.delete_frame.grid_remove();self.delete_button.focus_set()

    def delete(self):
        if not self.identity or not self.delete_frame.winfo_manager() or not self.ensure_mutable(): return
        try:
            identity=self.identity
            delete_profile(identity)
            if self.workspace: self.workspace.refresh_services(deleted=identity)
            else:
                self.owner.reload_services();self.owner.service.set('Edge-TTS');self.owner.change_service()
            self.owner.status.configure(text='服務已刪除。已切換至 Edge-TTS；請重新選音色。')
            self.close()
        except (ProjectError,OSError) as error:
            self.status.configure(text=str(error) if isinstance(error,ProjectError) else '無法刪除本機服務設定；請重試。')

    def check(self):
        if self.job:
            self.job.cancel();self.status.configure(text='正在取消檢查…');return
        try:
            provider=PROVIDERS[self.provider.get()]
            if not self.name.get().strip(): raise ProjectError('請填服務名稱。')
            key=self.key.get()
            if self.reuse.get():
                from .gemini import load_settings
                key=load_settings()['key']
            elif not key.strip() and self.identity:
                key=credential(dict(profile=self.identity,provider=provider))
            if not key.strip(): raise ProjectError('請輸入 API 金鑰。')
            if '\n' in key or '\r' in key: raise ProjectError('金鑰不可含換行。')
            from .voice import VoiceJob
            self.job=VoiceJob(lambda:check_service(provider,key))
            self.status.configure(text='正在檢查連線與音色…尚未儲存修改。')
            self.update_controls();self.timer=self.after(100,self.poll)
        except (ProjectError,OSError) as error:
            self.status.configure(text=str(error) if isinstance(error,ProjectError) else '無法讀取本機服務設定。')

    def poll(self):
        self.timer=None
        if not self.job: return
        if not self.job.wait(0): self.timer=self.after(100,self.poll);return
        self.status.configure(text=(self.job.result+' 尚未儲存修改。') if self.job.state['status']=='completed' else
                              '已取消檢查。尚未儲存修改。' if self.job.state['status']=='cancelled' else self.job.state['error'] or '檢查失敗。')
        self.job=None;self.update_controls()
        if self.closing: self.close()

    def close(self):
        if not self.winfo_exists(): return
        if self.timer is not None: self.after_cancel(self.timer);self.timer=None
        if self.job:
            self.closing=True;self.job.cancel()
            if not self.job.wait(0): self.timer=self.after(100,self.close);return
            self.job=None
        self.key.set('');self.manual_key='';self.baseline=None;self.pending=None
        self.destroy()
        if self.on_return is not None: self.on_return()
