"""Task-specific line-break review; the source extraction UI is independent."""
from difflib import unified_diff
import tkinter as tk
from tkinter import ttk

from .workflow import ProjectError, ProjectWorkflow
from .desktop_shell import ActionSpec, PagePresentation


class LineBreakPreview(ttk.Frame):
    page_id = 'manuscript.line-break-preview'

    def __init__(self, app, host):
        super().__init__(host.content, padding=(20, 10), style='Tool.TFrame')
        self.app = app
        self.host = host
        self.identity = None
        self.base = self.candidate = ''
        self.context_text = self.message = ''
        self.stale = False
        self.error = False
        self.change_count = 0
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        ttk.Label(self, text='整理前後比較', style='Tool.Heading.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 8))
        self.empty = ttk.Label(self, text='目前沒有需要整理的換行，文稿未變更。', wraplength=600, anchor='nw', style='Tool.TLabel')
        self.diff = tk.Text(self, wrap='word', state='disabled', width=1, height=1,
            font=('Microsoft JhengHei', 12), relief='flat', padx=4, pady=4,
            background='#ffffff', foreground='#263d34', exportselection=False)
        self.diff.tag_configure('added', background='#e7efe4')
        self.diff.tag_configure('removed', background='#f8e8e3')
        self.scroll = ttk.Scrollbar(self, command=self.diff.yview)
        self.diff.configure(yscrollcommand=self.scroll.set)
        self.bind('<Configure>', lambda e: self.empty.configure(wraplength=max(1, e.width-40)))

    def describe(self):
        actions = [ActionSpec('manuscript.cleanup.back', '← 返回文稿', 'back', self.app.close_tools)]
        if self.change_count:
            actions.append(ActionSpec('manuscript.cleanup.apply', '套用換行整理', 'primary', self.apply,
                                      enabled=not self.stale))
        return (PagePresentation(1, '整理換行預覽', self.message, tuple(actions),
                                 busy=bool(self.app.workspace_busy or self.app.source_pending),
                                 message_kind='error' if self.error else 'normal'), self.context_text)

    def prepare(self):
        app = self.app
        self.identity = (app.flow, app.batch_id)
        self.base = app.current_text
        self.candidate = ProjectWorkflow.preview_line_breaks(self.base)
        normalized = self.base.replace('\r\n', '\n').replace('\r', '\n')
        self.change_count = max(1, normalized.count('\n')-self.candidate.count('\n')) if self.base != self.candidate else 0
        self.stale = False
        self.error = False
        batch = app.flow._batch(app.batch_id)
        self.context_text = f'目前文件 · {batch["name"]}'
        try:
            size = int(app.font_size.get())
            if not 8 <= size <= 32:
                raise ValueError
        except ValueError:
            self.diff.configure(font=app.editor.cget('font'))
        else:
            self.diff.configure(font=('Microsoft JhengHei', size))
        self.diff.grid_remove()
        self.scroll.grid_remove()
        self.empty.grid_remove()
        if self.change_count:
            self.diff.grid(row=1, column=0, sticky='nsew')
            self.scroll.grid(row=1, column=1, sticky='ns')
            diff = ''.join(unified_diff(self.base.splitlines(True), self.candidate.splitlines(True),
                fromfile='目前文稿', tofile='整理結果'))
            self.diff.configure(state='normal')
            self.diff.delete('1.0', 'end')
            self.diff.insert('1.0', diff)
            for number, line in enumerate(diff.splitlines(), 1):
                if line.startswith('+') and not line.startswith('+++'):
                    self.diff.tag_add('added', f'{number}.0', f'{number}.end')
                elif line.startswith('-') and not line.startswith('---'):
                    self.diff.tag_add('removed', f'{number}.0', f'{number}.end')
            self.diff.configure(state='disabled')
            self.diff.yview_moveto(0)
            self.message = f'{self.change_count} 處變更 · 原稿尚未變更'
        else:
            self.empty.grid(row=1, column=0, sticky='new')
            self.message = '無須整理 · 原稿未變更'
        self.host.refresh(self.page_id)

    def apply(self):
        app = self.app
        if not self.change_count or self.candidate == self.base:
            return False
        if (self.identity != (app.flow, app.batch_id) or app.current_text != self.base
                or app.workspace_busy or app.source_pending):
            self.message = '文稿已變更。請返回後重新預覽；現稿保留。'
            self.stale = True
            self.error = True
            self.host.refresh(self.page_id)
            return False
        try:
            # Persist first. Failure keeps both the displayed text and readiness.
            app.flow.backup_manuscript(app.batch_id, self.base, label='換行整理前編輯稿')
            app.flow.save_workspace(app.batch_id, self.candidate,
                review_id=app.workspace_review, allow_partial=app.allow_partial)
        except ProjectError as error:
            self.message = str(error)
            self.error = True
            self.host.refresh(self.page_id)
            return False
        app.set_editor(self.candidate)
        app.mark_diff()
        app.close_tools()
        app.status.configure(text='已套用換行整理 · 可按 Ctrl+Z 復原。')
        return True

    def clear(self):
        self.identity = None
