"""Version review content and presentation for the shared inner-page host."""
import tkinter as tk
from tkinter import ttk
from .desktop_shell import ActionSpec, PagePresentation


class VersionPage(ttk.Frame):
    page_id = 'manuscript.versions'
    show_context = False

    def __init__(self, app, host):
        super().__init__(host.content, padding=(20, 10))
        self.app, self.host = app, host
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        selector_row = ttk.Frame(self)
        selector_row.grid(row=0, column=0, columnspan=2, sticky='ew')
        selector_row.columnconfigure(1, minsize=400)
        selector_row.columnconfigure(2, weight=1)
        ttk.Label(selector_row, text='選擇版本').grid(row=0, column=0, padx=(0,12))
        app.version_selector = ttk.Combobox(selector_row, state='readonly', width=20, style='Workspace.TCombobox')
        app.version_selector.grid(row=0, column=1, sticky='ew')
        app.version_selector.bind('<<ComboboxSelected>>', self.select)
        app.version_basis = ttk.Label(self, text='目前編輯稿 → 所選版本')
        app.version_basis.grid(row=1, column=0, sticky='w', pady=(16,8))
        app.version_diff = tk.Text(self, wrap='word', width=1, height=1, state='disabled',
            font=('Microsoft JhengHei',12), relief='flat', padx=4, pady=4,
            background='white', foreground='#263d34', exportselection=False)
        app.version_diff.grid(row=2, column=0, sticky='nsew')
        app.version_diff.tag_configure('added', background='#e7efe4')
        app.version_diff.tag_configure('removed', background='#f8e8e3')
        self.scroll = ttk.Scrollbar(self, command=app.version_diff.yview)
        self.scroll.grid(row=2, column=1, sticky='ns')
        def view(first,last):
            self.scroll.set(first,last)
            self.scroll.grid_remove() if float(first)<=0 and float(last)>=1 else self.scroll.grid()
        app.version_diff.configure(yscrollcommand=view)
        app.version_rows, app.version_labels = [], []
        app.version_can_delete = False

    def prepare(self):
        self.app.version_diff.configure(font=self.app.editor.cget('font'))
        self.app.refresh_versions()

    def select(self, event=None):
        self.app.preview_version(event)
        self.host.refresh(self.page_id)

    def decorate(self):
        text = self.app.version_diff
        for tag in ('added','removed'):text.tag_remove(tag,'1.0','end')
        for number,line in enumerate(text.get('1.0','end-1c').splitlines(),1):
            if line.startswith('+') and not line.startswith('+++'):text.tag_add('added',f'{number}.0',f'{number}.end')
            if line.startswith('-') and not line.startswith('---'):text.tag_add('removed',f'{number}.0',f'{number}.end')

    def command(self, callback):
        callback()
        self.host.refresh(self.page_id)

    def describe(self):
        app=self.app
        actions=[ActionSpec('versions.back','← 返回文稿','back',app.close_tools)]
        if app.version_rows:
            if app.version_can_delete:
                actions.append(ActionSpec('versions.delete','刪除此朗讀版本','destructive',lambda:self.command(app.delete_reading_version)))
            actions.append(ActionSpec('versions.restore','還原到編輯稿','primary',lambda:self.command(app.restore_version)))
        app.version_selector.configure(state='disabled' if app.workspace_busy else 'readonly')
        return PagePresentation(1,'版本紀錄','所選版本唯讀 · 還原前會備份現稿' if app.version_rows else '尚無版本',
                                tuple(actions),busy=bool(app.workspace_busy)), ''
