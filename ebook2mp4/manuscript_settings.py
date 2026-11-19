"""AI preferences content for the shared manuscript inner-page host."""
import tkinter as tk
from tkinter import ttk
from .desktop_shell import ActionSpec, PagePresentation
from .workflow import ProjectWorkflow, ProjectError


class AiSettingsPage(ttk.Frame):
    page_id = 'manuscript.ai-settings'

    def __init__(self, app, host):
        super().__init__(host.content, padding=(20, 10))
        self.app, self.host = app, host
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        from .production_desktop import ScrollPage
        self.scroll = app.settings_scroll = ScrollPage(self)
        self.scroll.grid(row=0, column=0, sticky='nsew')
        bar = next(w for w in self.scroll.winfo_children() if isinstance(w, ttk.Scrollbar))
        def view(first, last):
            bar.set(first, last)
            bar.grid_remove() if float(first) <= 0 and float(last) >= 1 else bar.grid()
        self.scroll.canvas.configure(yscrollcommand=view)
        self.content = content = self.scroll.content
        content.columnconfigure((0, 1), weight=1, uniform='ai-field')
        app.settings_status = ttk.Label(self, text='偏好設定變更即保存')
        app.font_size = tk.StringVar(value='12')
        app.script = tk.StringVar(value='自動')
        app.normalize_punctuation = tk.BooleanVar(value=True)
        app.model = tk.StringVar(value='gemini-2.5-flash')
        app.api_key = tk.StringVar()
        try:
            connection = ProjectWorkflow.gemini_settings()
            app.model.set(connection['model'])
            app.api_key.set(connection['key'])
        except ProjectError:
            pass
        self.controls = []
        self.service = tk.StringVar(value='Gemini')
        for i, (label, variable, values) in enumerate((
                ('AI 校對服務', self.service, ('Gemini',)),
                ('模型（可手動輸入）', app.model, ('gemini-3.8-flash','gemini-2.5-flash','gemini-2.5-pro')),
                ('校對文字', app.script, ('自動','繁體','簡體','保留原樣')),
                ('編輯器字級', app.font_size, ('10','12','14','16','18','20','24')))):
            field = ttk.Frame(content)
            field.grid(row=i//2, column=i%2, sticky='ew', padx=(0,12), pady=(0,12))
            field.columnconfigure(0, weight=1)
            ttk.Label(field, text=label).grid(row=0, column=0, sticky='w', pady=(0,8))
            combo = ttk.Combobox(field, textvariable=variable, values=values, width=12,
                state='normal' if variable is app.model else 'readonly', style='Workspace.TCombobox')
            combo.grid(row=1, column=0, sticky='ew')
            for event in ('<<ComboboxSelected>>','<FocusOut>','<Return>'):
                combo.bind(event, self.save_preferences)
            self.controls.append(combo)
        ttk.Checkbutton(content, text='統一中文全形標點', variable=app.normalize_punctuation,
            command=self.save_preferences).grid(row=2, column=0, sticky='w', pady=8)
        self.toggle = ttk.Button(content, text='服務連線設定（展開）', command=self.toggle_connection,
                                 style='Workspace.TButton')
        self.toggle.grid(row=2, column=1, sticky='ew', padx=(0,12), pady=8)
        app.connection_frame = self.connection = ttk.Frame(content)
        self.connection.columnconfigure(0, weight=1)
        ttk.Label(self.connection, text='Gemini API Key（僅儲存在本機）').grid(row=0, column=0, sticky='w', pady=(0,8))
        self.key_entry = ttk.Entry(self.connection, textvariable=app.api_key, show='●', style='Workspace.TEntry')
        self.key_entry.grid(row=1, column=0, sticky='ew')
        self.expanded = False
        self.scroll.bind_scroll()

    def save_preferences(self, event=None):
        self.app.save_manuscript_settings(event)
        self.host.refresh(self.page_id)

    def toggle_connection(self):
        self.expanded = not self.expanded
        if self.expanded:
            self.connection.grid(row=3, column=0, columnspan=2, sticky='ew', padx=(0,12), pady=(12,0))
        else:
            self.connection.grid_remove()
        self.toggle.configure(text='服務連線設定（收合）' if self.expanded else '服務連線設定（展開）')

    def command(self, callback):
        callback()
        self.host.refresh(self.page_id)

    def describe(self):
        app = self.app
        busy = bool(app.workspace_busy)
        for i, control in enumerate(self.controls):
            control.configure(state='disabled' if busy else 'normal' if i == 1 else 'readonly')
        self.key_entry.configure(state='disabled' if busy else 'normal')
        self.toggle.configure(state='disabled' if busy else 'normal')
        batch = app.flow._batch(app.batch_id) if app.flow and app.batch_id else None
        return PagePresentation(1, 'AI 設定', app.settings_status.cget('text'), (
            ActionSpec('ai.back', '← 返回文稿', 'back', app.close_tools),
            ActionSpec('ai.test-connection', '測試連線', 'secondary', lambda:self.command(app.test_connection)),
            ActionSpec('ai.save-settings', '儲存設定', 'primary', lambda:self.command(app.save_connection))),
            busy=busy), '目前文件 · '+batch['name'] if batch else 'AI 校對設定'
