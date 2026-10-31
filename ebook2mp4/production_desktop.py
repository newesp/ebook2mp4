"""Single-window production pages, independent from background task lifetime."""
from tkinter import ttk
import tkinter as tk
from typing import Any


class ScrollPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, highlightthickness=0, background='#f5f6f2', width=1, height=1)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        scrollbar = ttk.Scrollbar(self, command=self.canvas.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.content = ttk.Frame(self.canvas)
        item = self.canvas.create_window(0, 0, anchor='nw', window=self.content)
        self.content.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfigure(item, width=e.width))

    def bind_scroll(self):
        from .desktop import bind_canvas_wheel
        bind_canvas_wheel(self.canvas, self.content)


class ProductionWorkspace(ttk.Frame):
    def __init__(self, app):
        super().__init__(app.body)
        self.app = app
        self.pages: dict[tuple, Any] = {}
        self.current = None
        self.service_page = None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        tabs = ttk.Frame(self)
        tabs.grid(row=0, column=0, sticky='ew', pady=(0, 8))
        self.voice_tab = ttk.Button(tabs, text='語音設定與試聽', command=app.voice_settings)
        self.voice_tab.pack(side='left')
        ttk.Label(tabs, text=' → ').pack(side='left')
        self.narration_tab = ttk.Button(tabs, text='製作與成品', command=app.narration)
        self.narration_tab.pack(side='left')
        ttk.Label(tabs, text=' → ').pack(side='left')
        self.assembly_tab = ttk.Button(tabs, text='全書合併', command=app.total_audio)
        self.assembly_tab.pack(side='left')
        self.host = ttk.Frame(self)
        self.host.grid(row=1, column=0, sticky='nsew')
        self.host.columnconfigure(0, weight=1)
        self.host.rowconfigure(0, weight=1)
        self.task_button = ttk.Button(app, text='', command=self.show_active)
        self.timer: str | None = self.after(200, self.poll)
        self.bind('<Destroy>', self.destroyed, add='+')

    def destroyed(self, event):
        if event.widget is self and self.timer is not None:
            self.after_cancel(self.timer)
            self.timer = None

    def activate(self, page):
        if self.current is not None and self.current.winfo_exists():
            if hasattr(self.current, 'stop'):
                self.current.stop()
            self.current.grid_remove()
        self.current = page
        page.grid(row=0, column=0, sticky='nsew')
        self.refresh_task_controls()
        kind = 'assembly' if getattr(page, 'kind', None) == 'assembly' else 'voice' if hasattr(page, 'kind') or page is self.service_page else 'narration'
        self.voice_tab.configure(style='CompactActive.TButton' if kind == 'voice' else 'Compact.TButton')
        self.narration_tab.configure(style='CompactActive.TButton' if kind == 'narration' else 'Compact.TButton')
        self.assembly_tab.configure(style='CompactActive.TButton' if kind == 'assembly' else 'Compact.TButton')

    def show(self, kind):
        app = self.app
        key = (id(app.flow), None if kind == 'assembly' else app.batch_id, kind)
        page: Any = self.pages.get(key)
        if page is None or not page.winfo_exists():
            if kind == 'assembly':
                from .assembly_desktop import AssemblyPage
                page = AssemblyPage(app)
            elif kind == 'voice':
                from .voice_desktop import VoiceDialog
                page = VoiceDialog(app)
            else:
                from .narration_desktop import NarrationDialog
                page = NarrationDialog(app)
            self.pages[key] = page
        app.voice_dialog = self.pages.get((id(app.flow), app.batch_id, 'voice'))
        app.narration_dialog = self.pages.get((id(app.flow), app.batch_id, 'narration'))
        self.activate(page)
        if kind == 'narration' and page.job is None:
            page.load_runs()
            page.load_result()
        if kind == 'assembly':
            page.recheck()
        return page

    def manage_services(self, owner):
        from .service_desktop import ServiceDialog
        if self.service_page is not None and self.service_page.winfo_exists():
            self.service_page.owner = owner
            self.service_page.on_return = self.app.voice_settings
            self.activate(self.service_page)
            return
        self.service_page = ServiceDialog(owner, parent=self.host, on_return=self.app.voice_settings)
        self.activate(self.service_page)

    def hide(self):
        if self.current is not None and self.current.winfo_exists() and hasattr(self.current, 'stop'):
            self.current.stop()
        self.grid_remove()

    def active_page(self):
        return next((p for k, p in self.pages.items() if k[2] in ('narration', 'assembly') and p.winfo_exists() and p.job is not None), None)

    def show_active(self):
        page = self.active_page()
        if page is None:
            return
        app = self.app
        if getattr(page, 'kind', None) == 'assembly':
            if app.flow is not page.flow:
                if not app.may_leave():
                    return
                app.flow, app.batch_id = page.flow, next((b['id'] for b in page.flow.state['batches']), None)
                app.refresh()
            app.total_audio()
            return
        if app.flow is not page.flow or app.batch_id != page.batch_id:
            if not app.may_leave():
                return
            app.flow, app.batch_id = page.flow, page.batch_id
            app.refresh()
        app.narration()

    def poll(self):
        self.timer = None
        page = self.active_page()
        if page is not None:
            state = page.job.state
            batch = '全書合併' if getattr(page, 'kind', None) == 'assembly' else next((b['name'] for b in page.flow.state['batches'] if b['id'] == page.batch_id), '原批次')
            self.task_button.configure(text=f'{batch}｜{state.get("phase", "製作中")}｜完成 {state.get("completed", 0)}/{state.get("total", 0)} · 返回任務 →')
            self.task_button.grid(row=4, column=0, sticky='ew')
        else:
            self.task_button.grid_remove()
        self.refresh_task_controls()
        self.timer = self.after(200, self.poll)

    @staticmethod
    def busy_for(flow):
        from .production_lock import production_active
        from .workflow import ProjectError
        try:
            return production_active(flow.root / '.production.lock')
        except ProjectError:
            return True

    def refresh_task_controls(self):
        page = self.current
        if page is not None and page.winfo_exists() and hasattr(page, 'set_production_busy'):
            page.set_production_busy(self.busy_for(page.flow))

    def shutdown(self):
        pages = list(self.pages.values())
        if self.service_page is not None:
            self.service_page.on_return = None
            pages.insert(0, self.service_page)
        for page in pages:
            if page.winfo_exists():
                if page.close() is False:
                    return 'cancelled'
        if any(p.winfo_exists() for p in pages):
            return 'pending'
        return 'complete'
