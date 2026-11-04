"""Optional voice-package management inside the incumbent production workspace."""
import tkinter as tk
from tkinter import ttk,filedialog
from .workflow import ProjectError


class PackagePage(ttk.Frame):
    kind='local-package'
    def __init__(self,owner):
        super().__init__(owner.app.production.host,padding=8)
        self.owner=owner;self.app=owner.app;self.flow=owner.flow
        ttk.Style(self).configure('KokoroDanger.TButton',foreground='#963b32')
        self.job=None;self.timer=None;self.closing=False
        self.columnconfigure(0,weight=1);self.rowconfigure(4,weight=1)
        ttk.Label(self,text='本機語音包',style='Heading.TLabel').grid(row=0,column=0,sticky='w',pady=(0,8))
        self.summary=ttk.Label(self,text='',wraplength=650)
        self.summary.grid(row=1,column=0,sticky='ew',pady=8)
        row=ttk.Frame(self);row.grid(row=2,column=0,sticky='ew',pady=8);row.columnconfigure(0,weight=1)
        self.path=tk.StringVar()
        self.entry=ttk.Entry(row,textvariable=self.path,width=24);self.entry.grid(row=0,column=0,sticky='ew')
        self.choose_button=ttk.Button(row,text='選擇離線語音包…',command=self.choose)
        self.choose_button.grid(row=0,column=1,padx=(8,0))
        actions=ttk.Frame(self);actions.grid(row=3,column=0,sticky='ew',pady=8)
        self.import_button=ttk.Button(actions,text='檢查並匯入',command=self.install,style='Primary.TButton')
        self.import_button.grid(row=0,column=0)
        self.cancel_button=ttk.Button(actions,text='取消匯入',command=self.cancel)
        self.cancel_button.grid(row=0,column=1,padx=8)
        self.remove_button=ttk.Button(actions,text='移除語音包…',command=self.confirm_remove)
        self.remove_button.grid(row=0,column=2)
        details=ttk.Frame(self);details.grid(row=4,column=0,sticky='nsew',pady=8)
        details.columnconfigure(0,weight=1);details.rowconfigure(1,weight=1)
        ttk.Button(details,text='版本、音色與授權詳情',command=self.toggle_details).grid(row=0,column=0,sticky='w')
        self.detail_frame=ttk.Frame(details);self.detail_frame.grid(row=1,column=0,sticky='nsew')
        self.detail_frame.columnconfigure(0,weight=1);self.detail_frame.rowconfigure(0,weight=1)
        self.detail_text=tk.Text(self.detail_frame,height=5,width=1,wrap='word',state='disabled')
        self.detail_text.grid(row=0,column=0,sticky='nsew')
        bar=ttk.Scrollbar(self.detail_frame,command=self.detail_text.yview);bar.grid(row=0,column=1,sticky='ns')
        self.detail_text.configure(yscrollcommand=bar.set)
        self.detail_frame.grid_remove()
        self.confirm=ttk.Frame(self)
        self.confirm.grid(row=5,column=0,sticky='ew',pady=8)
        ttk.Label(self.confirm,text='只移除所選語音包。保留書稿、有效快取與完成成品。',wraplength=650).grid(row=0,column=0,columnspan=2,sticky='w')
        ttk.Button(self.confirm,text='取消移除',command=self.confirm.grid_remove).grid(row=1,column=0,sticky='w',pady=6)
        ttk.Button(self.confirm,text='確認移除',command=self.remove,style='KokoroDanger.TButton').grid(row=1,column=1,sticky='e')
        self.confirm.grid_remove()
        self.status=ttk.Label(self,text='只匯入已下載的離線包，不上傳書稿。',wraplength=650)
        self.status.grid(row=6,column=0,sticky='ew',pady=8)
        self.progress=ttk.Progressbar(self,mode='indeterminate');self.progress.grid(row=7,column=0,sticky='ew')
        self.progress.grid_remove()
        self.back_button=ttk.Button(self,text='← 返回語音設定',command=self.back)
        self.back_button.grid(row=8,column=0,sticky='w',pady=8)
        self.bind('<Configure>',self.resize,add='+')
        self.refresh()

    def resize(self,event):
        if event.widget is self:
            self.summary.configure(wraplength=max(200,event.width-24))
            self.status.configure(wraplength=max(200,event.width-24))

    def refresh(self):
        packages=self.flow.local_voice_packages()
        self.summary.configure(text='Kokoro 官方中文模型 · CPU · 已安裝 · 100 種中文音色' if packages else '尚未安裝可用語音包。請選擇與主程式相符的完整 ZIP。')
        busy=self.job is not None
        self.import_button.configure(state='disabled' if busy else 'normal')
        self.choose_button.configure(state='disabled' if busy else 'normal')
        self.entry.configure(state='disabled' if busy else 'normal')
        self.remove_button.configure(state='disabled' if busy or not packages else 'normal')
        self.back_button.configure(state='disabled' if busy else 'normal')
        if busy:self.cancel_button.grid();self.progress.grid();self.progress.start(12)
        else:self.cancel_button.grid_remove();self.progress.stop();self.progress.grid_remove()

    def toggle_details(self):
        if self.detail_frame.winfo_ismapped():self.detail_frame.grid_remove();return
        from .kokoro_packages import release
        try:
            value=release()
            text=f"模型：{value['model']}\n語音包：{value['id']}\n引擎：{value['engine']}\n前處理：{value['processing']}\n人工品質驗證：尚無\n授權通知保留在語音包 notices 目錄。\n\n音色："+'、'.join(v['id'] for v in value['voices'])
            self.detail_text.configure(state='normal');self.detail_text.delete('1.0','end');self.detail_text.insert('1.0',text);self.detail_text.configure(state='disabled')
            self.detail_frame.grid()
        except ProjectError as error:self.status.configure(text=str(error))

    def choose(self):
        path=filedialog.askopenfilename(parent=self,title='匯入離線語音包',filetypes=[('Kokoro 語音包','*.zip')])
        if path:self.path.set(path)

    def install(self):
        from pathlib import Path
        if self.job:return
        try:
            self.confirm.grid_remove()
            self.job=self.flow.start_voice_package_import(Path(self.path.get()))
            self.status.configure(text='正在檢查與匯入語音包…可取消。')
            self.refresh();self.timer=self.after(100,self.poll)
        except ProjectError as error:self.status.configure(text=str(error))

    def poll(self):
        self.timer=None
        if self.job is None:return
        if not self.job.wait(0):self.timer=self.after(100,self.poll);return
        state=self.job.state;self.job=None;self.refresh()
        self.status.configure(text='語音包已就緒，可返回選擇音色。' if state['status']=='completed' else '已取消匯入；原有效安裝保留。' if state['status']=='cancelled' else state['error'])
        if self.closing:self.close()

    def cancel(self):
        if self.job:self.job.cancel();self.status.configure(text='取消中，正在清理未完成安裝…')

    def confirm_remove(self):
        if not self.job:self.confirm.grid()

    def remove(self):
        try:
            packages=self.flow.local_voice_packages()
            if packages:self.flow.remove_voice_package(packages[0]['id'])
            self.confirm.grid_remove();self.refresh();self.status.configure(text='語音包已移除；書稿、快取與成品保留。')
        except ProjectError as error:self.status.configure(text=str(error))

    def back(self):
        if self.job:return
        self.owner.reload_services();self.owner.load_catalog();self.owner.update_controls()
        self.app.production.activate(self.owner)

    def close(self):
        if self.job:
            self.closing=True;self.cancel();return
        if self.timer:self.after_cancel(self.timer);self.timer=None
        self.progress.stop();self.destroy()
