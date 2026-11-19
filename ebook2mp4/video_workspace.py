"""Shared presentation for video routes; jobs and persisted products stay on owners."""
import tkinter as tk
from tkinter import ttk

from .ui_controls import AutoHideScrollbar


class VideoTabs(ttk.Notebook):
    def __init__(self, parent):
        super().__init__(parent, takefocus=True)
        self.panels = []
        for title in ('畫面與素材', '來源與順序', '任務與成品'):
            panel = ttk.Frame(self, padding=(0, 8, 0, 0))
            panel.columnconfigure(0, weight=1)
            panel.rowconfigure(0, weight=1)
            self.add(panel, text=title)
            self.panels.append(panel)
        self.enable_traversal()
        # Tk's native Notebook supports Ctrl+Tab; also offer direct tab arrows.
        for key, delta in (('<Left>', -1), ('<Right>', 1)):
            self.bind(key, lambda event, delta=delta: self.cycle(delta))
        self.bind('<Home>', lambda event: self.choose(0))
        self.bind('<End>', lambda event: self.choose(2))

    def choose(self, index):
        self.select(index)
        self.focus_set()
        return 'break'

    def cycle(self, delta):
        return self.choose((self.index(self.select()) + delta) % 3)


def readonly_text(parent):
    frame = ttk.Frame(parent)
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)
    text = tk.Text(frame, width=1, height=1, wrap='word', relief='flat',
                   font=('Microsoft JhengHei', 10), padx=12, pady=10, state='disabled')
    text.grid(row=0, column=0, sticky='nsew')
    scroll = AutoHideScrollbar(frame, command=text.yview)
    scroll.grid(row=0, column=1, sticky='ns')
    text.configure(yscrollcommand=scroll.set)
    return frame, text


def replace_text(widget, value):
    if widget.get('1.0', 'end-1c') == value:
        return
    position = widget.yview()[0]
    widget.configure(state='normal')
    widget.delete('1.0', 'end')
    widget.insert('1.0', value)
    widget.configure(state='disabled')
    widget.yview_moveto(position)


def workspace_styles(widget):
    """Use the application's existing size roles and native menu indicators."""
    for child in widget.winfo_children():
        if isinstance(child, ttk.Combobox):
            child.configure(style='Workspace.TCombobox')
        elif isinstance(child, ttk.Button) and child.cget('style') != 'Primary.TButton':
            child.configure(style='Workspace.TButton')
        elif isinstance(child, ttk.Menubutton):
            child.configure(text=child.cget('text').replace(' ▾', '').replace(' ▸', ''))
        workspace_styles(child)
