"""Runnable native Tkinter layout mock. Synthetic text; memory-only actions.

Run: python -B -m ebook2mp4.ui_mock
This is an independent design artifact, not a production application entry point.
"""
import argparse
import difflib
import re
import tkinter as tk
from tkinter import ttk, messagebox

from .desktop import BG, GREEN, INK, MUTED, text_pane

PAPER = '#fffef9'
LINE = '#dfe5dd'
ERROR = '#963b32'
SOURCE = '''第一章　風與樹

清晨，山谷裡的風帶著露水的氣息。
他推開窗，看見樹影落在書頁上。

「今天就從這一頁開始吧。」她說。

他把書放在桌上，沿著文字慢慢往下讀。
窗外的樹葉輕輕晃動，陽光停在紙上。

校對並不急著改變每一句話，而是先看清楚原文。
遇到不確定的地方，他會留下一個記號，
再回到原頁，核對字形與上下文。

有些段落需要保留原有的節奏。
有些斷行，則只是排版留下的痕跡。

讀到這裡，她停了一下，重新看向窗外。
風仍然吹著，書頁也仍然攤開。

Hello, world! 數字 3.14、姓名與標點都保留。

這份合成書稿只用來檢視閱讀與校對的介面。
所有示範操作都留在記憶體，不會修改書籍專案。'''


def fill(widget, value, editable=False):
    widget.configure(state='normal')
    widget.delete('1.0', 'end')
    widget.insert('1.0', value)
    widget.configure(state='normal' if editable else 'disabled')


def menu(parent, title, commands):
    button = ttk.Menubutton(parent, text=title, style='Tool.TMenubutton')
    popup = tk.Menu(button, tearoff=False)
    for label, command in commands:
        if label is None:
            popup.add_separator()
        else:
            popup.add_command(label=label, command=command)
    button.configure(menu=popup)
    return button


def button(parent, title, command, primary=False, **kwargs):
    return ttk.Button(parent, text=title, command=command,
                      style='Primary.TButton' if primary else 'TButton', **kwargs)


def styles(root):
    root.configure(background=BG)
    root.option_add('*Font', ('Microsoft JhengHei', 10))
    s = ttk.Style(root)
    s.theme_use('clam')
    s.configure('.', font=('Microsoft JhengHei', 10), background=BG, foreground=INK)
    s.configure('TButton', padding=(10, 7), background='#ffffff', bordercolor='#c7d2c6')
    s.map('TButton', background=[('active', '#e9f0e5')], foreground=[('disabled', '#68736c')])
    s.configure('Tool.TMenubutton', padding=(10, 7), background='#ffffff')
    s.configure('Primary.TButton', background=GREEN, foreground='#ffffff')
    s.map('Primary.TButton', background=[('disabled', '#e1e5de'), ('active', '#264d35')],
          foreground=[('disabled', '#68736c')])
    s.configure('Heading.TLabel', font=('Microsoft JhengHei', 11, 'bold'))
    s.configure('Book.TLabel', font=('Microsoft JhengHei', 13, 'bold'))
    s.configure('Muted.TLabel', foreground=MUTED)
    s.configure('Treeview', rowheight=32, background='#ffffff', fieldbackground='#ffffff')
    s.map('Treeview', background=[('selected', GREEN)], foreground=[('selected', '#ffffff')])
    s.configure('TNotebook', tabmargins=(0, 0, 0, 0))
    s.configure('TNotebook.Tab', padding=(12, 7))


class WorkbenchMock:
    def __init__(self, root, narrow=False):
        self.root = root
        styles(root)
        root.title('風與樹 — 書籍製作工作台 · UI Mock')
        root.geometry('1040x640+20+20' if narrow else '1360x820+20+20')
        root.minsize(1040, 640)
        self.saved = SOURCE
        self.confirmed = False
        self.messages = []
        self.children = []
        self.focused = False
        self.font_size = tk.StringVar(value='12')
        self.frame = ttk.Frame(root, padding=12)
        self.frame.pack(fill='both', expand=True)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(2, weight=1)
        self.build_top()
        self.build_body()
        self.build_footer()
        root.bind('<Control-s>', lambda e: self.save())
        root.bind('<Control-f>', self.focus_search)
        root.bind('<F6>', lambda e: self.toggle_focus())
        root.bind('<Control-plus>', lambda e: self.set_font(1))
        root.bind('<Control-minus>', lambda e: self.set_font(-1))
        root.protocol('WM_DELETE_WINDOW', root.destroy)
        self.update_state()
        self.say('合成書稿已載入。可切換工具頁籤，或從「原稿工具」開啟兩個閱讀視窗。')

    def build_top(self):
        top = ttk.Frame(self.frame)
        top.grid(row=0, column=0, sticky='ew', pady=(0, 8))
        top.columnconfigure(0, weight=1)
        ttk.Label(top, text='風與樹', style='Book.TLabel').grid(row=0, column=0, sticky='w')
        menu(top, '專案', [(t, lambda title=t: self.say('示範選單：' + title)) for t in
                          ('建立書籍專案', '開啟專案', '開啟專案資料夾')]).grid(row=0, column=1, padx=3)
        menu(top, '版本與檔案', [('匯出目前校對稿 TXT', lambda: self.say('示範：匯出入口；不寫入任何檔案。')),
             ('重載外部校對稿', lambda: self.say('示範：外部重載入口；原稿保留。')),
             (None, None), ('保存版本與副本', self.open_versions)]).grid(row=0, column=2, padx=3)
        self.focus_button = button(top, '專注閱讀  F6', self.toggle_focus)
        self.focus_button.grid(row=0, column=3, padx=3)
        button(top, '儲存校對稿  Ctrl+S', self.save, primary=True).grid(row=0, column=4, padx=(3, 0))
        stages = ttk.Frame(self.frame)
        stages.grid(row=1, column=0, sticky='ew', pady=(0, 8))
        ttk.Label(stages, text='來源  /  校對', foreground=GREEN).pack(side='left')
        ttk.Label(stages, text='語音、影片尚未提供', style='Muted.TLabel').pack(side='left', padx=20)
        ttk.Label(stages, text='UI Mock · 合成內容', style='Muted.TLabel').pack(side='right')

    def build_body(self):
        self.body = body = ttk.Frame(self.frame)
        body.grid(row=2, column=0, sticky='nsew')
        body.rowconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        self.left = left = ttk.Frame(body, width=176, padding=(0, 6, 12, 0))
        left.grid(row=0, column=0, sticky='nsew')
        left.columnconfigure(0, weight=1)
        left.rowconfigure(2, weight=1)
        ttk.Label(left, text='書籍與製作批次', style='Heading.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 4))
        ttk.Label(left, text='3 個批次 · 1 個已確認', style='Muted.TLabel').grid(row=1, column=0, sticky='w', pady=(0, 10))
        listing = ttk.Frame(left)
        listing.grid(row=2, column=0, sticky='nsew')
        listing.columnconfigure(0, weight=1)
        listing.rowconfigure(0, weight=1)
        self.batches = ttk.Treeview(listing, show='tree', height=6, selectmode='browse')
        self.batches.column('#0', width=168, minwidth=120, stretch=True)
        self.batches.grid(row=0, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(listing, command=self.batches.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        self.batches.configure(yscrollcommand=scroll.set)
        for i, title in enumerate(('第一章 · 未確認', '第二章 · 待檢查 2 頁', '第三章 · 已確認')):
            self.batches.insert('', 'end', iid=str(i), text=title)
        self.batches.selection_set('0')
        self.batches.bind('<<TreeviewSelect>>', lambda e: self.say('就緒 · 可直接編輯校對稿，原始來源保持唯讀。'))
        menu(left, '新增批次', [('新增 TXT 批次', lambda: self.say('示範：新增 TXT 匯入預覽入口。')),
                              ('新增 PDF 文件', self.open_pdf)]).grid(row=3, column=0, sticky='ew', pady=(10, 5))
        menu(left, '批次管理', [(t, lambda title=t: self.say('示範批次操作：' + title)) for t in
                              ('命名批次', '上移', '下移', '移除目前 PDF 批次')]).grid(row=4, column=0, sticky='ew')
        center = ttk.Frame(body)
        center.grid(row=0, column=1, sticky='nsew')
        center.rowconfigure(1, weight=1)
        center.columnconfigure(0, weight=1)
        meta = ttk.Frame(center, padding=(12, 0, 12, 4))
        meta.grid(row=0, column=0, sticky='ew')
        meta.columnconfigure(0, weight=1)
        self.document_name = ttk.Label(meta, text='第一章　風與樹 · PDF 1–9 頁', style='Heading.TLabel')
        self.document_name.grid(row=0, column=0, sticky='w')
        menu(meta, '原稿工具', [('逐頁原稿／頁圖', self.open_pdf), ('預覽換行整理', self.open_breaks),
                              (None, None), ('來源詳細資訊', lambda: self.say('示範來源：合成 PDF · 9 頁 · 原始來源不覆寫。'))]).grid(row=0, column=1, padx=4)
        zoom = ttk.Combobox(meta, textvariable=self.font_size, values=('10', '12', '14', '16', '18'), width=3, state='readonly')
        zoom.grid(row=0, column=2)
        zoom.bind('<<ComboboxSelected>>', lambda e: self.apply_font())
        ttk.Label(meta, text='pt', style='Muted.TLabel').grid(row=0, column=3, padx=(4, 0))
        self.panes = panes = ttk.Panedwindow(center, orient='horizontal')
        panes.grid(row=1, column=0, sticky='nsew')
        a, self.source = text_pane(panes, '來源原文 · 唯讀')
        b, self.editor = text_pane(panes, '校對稿 · 可編輯', True)
        panes.add(a, weight=1)
        panes.add(b, weight=1)
        fill(self.source, SOURCE)
        fill(self.editor, SOURCE, True)
        self.editor.edit_reset()
        self.editor.edit_modified(False)
        self.editor.bind('<<Modified>>', self.edited)
        self.editor.configure(exportselection=False)
        self.right = right = ttk.Frame(body, width=240, padding=(12, 4, 0, 0))
        right.grid(row=0, column=2, sticky='nsew')
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        self.tools = ttk.Notebook(right, width=224)
        self.tools.grid(row=0, column=0, sticky='nsew')
        self.tool_pages = []
        for name in ('編輯', 'AI 校對', '確認'):
            frame = ttk.Frame(self.tools, padding=12)
            self.tools.add(frame, text=name)
            self.tool_pages.append(frame)
        self.build_edit(self.tool_pages[0])
        self.build_ai(self.tool_pages[1])
        self.build_confirm(self.tool_pages[2])
        self.tools.bind('<<NotebookTabChanged>>', lambda e: None)

    def build_edit(self, parent):
        ttk.Label(parent, text='搜尋文字').pack(anchor='w')
        self.find_var = tk.StringVar()
        self.find_entry = ttk.Entry(parent, textvariable=self.find_var, width=16)
        self.find_entry.pack(fill='x', pady=(5, 6))
        self.find_entry.bind('<Return>', lambda e: self.find_next())
        button(parent, '尋找下一個', self.find_next).pack(fill='x')
        ttk.Separator(parent).pack(fill='x', pady=16)
        ttk.Label(parent, text='取代為').pack(anchor='w')
        self.replace_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.replace_var, width=16).pack(fill='x', pady=(5, 6))
        row = ttk.Frame(parent)
        row.pack(fill='x')
        row.columnconfigure((0, 1), weight=1, uniform='replace')
        button(row, '取代一處', self.replace_one, width=6).grid(row=0, column=0, sticky='ew', padx=(0, 3))
        button(row, '全部取代', self.replace_all, width=6).grid(row=0, column=1, sticky='ew', padx=(3, 0))
        button(parent, '復原  Ctrl+Z', self.undo).pack(fill='x', pady=(12, 0))

    def build_ai(self, parent):
        ttk.Label(parent, text='送出範圍').pack(anchor='w')
        self.scope = tk.StringVar(value='整批文字')
        ttk.Combobox(parent, textvariable=self.scope, values=('整批文字', '選取文字'), state='readonly', width=16).pack(fill='x', pady=(5, 14))
        ttk.Label(parent, text='繁簡統一').pack(anchor='w')
        ttk.Combobox(parent, values=('自動判斷', '繁體', '簡體', '保留原樣'), state='readonly', width=16).pack(fill='x', pady=(5, 8))
        parent.winfo_children()[-1].current(0)
        self.normalize_punctuation = tk.BooleanVar(value=True)
        ttk.Checkbutton(parent, text='統一中文全形標點', variable=self.normalize_punctuation).pack(anchor='w', pady=4)
        button(parent, '開始校對', lambda: self.say('示範：送出前會確認範圍；此 mock 不連線、不送出文字。'), primary=True).pack(fill='x', pady=(12, 6))
        button(parent, '審閱候選差異', self.open_review).pack(fill='x', pady=3)
        ttk.Separator(parent).pack(fill='x', pady=14)
        button(parent, 'Gemini 設定', self.open_settings).pack(fill='x')

    def build_confirm(self, parent):
        ttk.Label(parent, text='目前批次', style='Heading.TLabel').pack(anchor='w', pady=(0, 10))
        ttk.Label(parent, text='來源異常：0 項', wraplength=190).pack(anchor='w')
        self.confirm_summary = ttk.Label(parent, text='朗讀稿尚未確認', wraplength=190)
        self.confirm_summary.pack(anchor='w', pady=10)
        button(parent, '查看來源檢查', self.open_pdf).pack(fill='x', pady=5)
        button(parent, '保存版本與副本', self.open_versions).pack(fill='x', pady=5)
        ttk.Separator(parent).pack(fill='x', pady=14)
        ttk.Label(parent, text='確認後保存獨立朗讀稿；\n後續修改須重新確認。', wraplength=190, style='Muted.TLabel').pack(anchor='w')

    def build_footer(self):
        footer = ttk.Frame(self.frame, padding=(8, 8, 0, 0))
        footer.grid(row=3, column=0, sticky='ew')
        footer.columnconfigure(0, weight=1)
        ttk.Separator(footer).grid(row=0, column=0, columnspan=3, sticky='ew', pady=(0, 6))
        self.state_label = ttk.Label(footer)
        self.state_label.grid(row=1, column=0, sticky='w')
        self.confirm_action = button(footer, '確認朗讀稿', self.confirm, primary=True)
        self.confirm_action.grid(row=1, column=2, rowspan=2, padx=(10, 0))
        self.message = ttk.Label(footer, text='', foreground=MUTED)
        self.message.grid(row=2, column=0, sticky='ew', pady=(4, 0))
        button(footer, '訊息記錄', self.show_messages).grid(row=1, column=1, rowspan=2, padx=(8, 0))
        footer.bind('<Configure>', lambda e: self.message.configure(wraplength=max(240, e.width - 300)))

    def say(self, value):
        self.messages.append(value)
        self.message.configure(text=value)

    def show_messages(self):
        self.open_text('訊息記錄', '\n\n'.join(self.messages))

    def update_state(self):
        if not hasattr(self, 'state_label'):
            return
        dirty = self.editor.get('1.0', 'end-1c') != self.saved
        content = self.editor.get('1.0', 'end-1c')
        self.state_label.configure(text=f'{len(content):,} 字元 · 校對稿 v3 · ' + ('未儲存' if dirty else '已儲存') +
                                   ' · 來源異常 0 · ' + ('朗讀稿已確認' if self.confirmed else '朗讀稿未確認'))
        self.confirm_action.configure(text='儲存並確認朗讀稿' if dirty else '確認朗讀稿', state='normal' if content.strip() else 'disabled')
        self.confirm_summary.configure(text='朗讀稿已確認（示範）' if self.confirmed else '朗讀稿尚未確認')

    def edited(self, _event=None):
        if self.editor.edit_modified():
            self.editor.edit_modified(False)
            self.confirmed = False
            self.update_state()

    def save(self):
        self.saved = self.editor.get('1.0', 'end-1c')
        self.update_state()
        self.say('示範：目前文字已保存在記憶體；未寫入正式書籍專案。')

    def confirm(self):
        if messagebox.askyesno('確認朗讀稿 · UI Mock', '示範將目前文字確認為朗讀稿？\n本次僅改變記憶體狀態，不建立正式快照。', parent=self.root):
            self.saved = self.editor.get('1.0', 'end-1c')
            self.confirmed = True
            self.update_state()
            self.say('示範：朗讀稿已確認；編輯文字後會恢復未確認狀態。')

    def focus_search(self, _event=None):
        if self.focused:
            self.toggle_focus()
        self.tools.select(0)
        self.find_entry.focus_set()
        return 'break'

    def find_next(self):
        value = self.find_var.get()
        if not value:
            self.say('請先輸入搜尋文字。')
            return False
        found = self.editor.search(value, self.editor.index('insert'), stopindex='end', exact=True)
        found = found or self.editor.search(value, '1.0', stopindex='end', exact=True)
        if not found:
            self.say('找不到完全相符的文字。')
            return False
        end = f'{found}+{len(value)}c'
        self.editor.tag_remove('sel', '1.0', 'end')
        self.editor.tag_add('sel', found, end)
        self.editor.mark_set('insert', end)
        self.editor.see(found)
        self.say('已找到「' + value + '」。')
        return True

    def replace_one(self):
        if self.find_next():
            start, end = self.editor.tag_ranges('sel')
            self.editor.edit_separator()
            self.editor.delete(start, end)
            self.editor.insert(start, self.replace_var.get())
            self.editor.edit_separator()
            self.say('已取代一處；可按 Ctrl+Z 復原。')

    def replace_all(self):
        old = self.find_var.get()
        if not old:
            return self.say('請先輸入搜尋文字。')
        content = self.editor.get('1.0', 'end-1c')
        count = content.count(old)
        self.editor.edit_separator()
        self.editor.delete('1.0', 'end')
        self.editor.insert('1.0', content.replace(old, self.replace_var.get()))
        self.editor.edit_separator()
        self.say(f'已取代 {count} 處；可按 Ctrl+Z 復原。')

    def undo(self):
        try:
            self.editor.edit_undo()
        except tk.TclError:
            self.say('目前沒有可復原的編輯。')

    def toggle_focus(self):
        self.focused = not self.focused
        for panel in (self.left, self.right):
            panel.grid_remove() if self.focused else panel.grid()
        self.focus_button.configure(text='返回工作台  F6' if self.focused else '專注閱讀  F6')

    def set_font(self, change):
        self.font_size.set(str(max(10, min(20, int(self.font_size.get()) + change))))
        self.apply_font()

    def apply_font(self):
        for text in (self.source, self.editor):
            text.configure(font=('Microsoft JhengHei', int(self.font_size.get())))

    def open_pdf(self):
        return PdfMock(self)

    def open_breaks(self):
        return BreaksMock(self)

    def open_review(self):
        return ReviewMock(self)

    def open_versions(self):
        return self.open_text('保存版本與副本 · UI Mock', SOURCE, '朗讀稿 v2 · 2026/10/26 14:30 · 合成歷史版本')

    def open_text(self, title, text, summary='合成內容 · 唯讀'):
        window = DocumentMock(self, title, summary)
        frame, display = text_pane(window.content, summary)
        frame.pack(fill='both', expand=True)
        fill(display, text)
        return window

    def open_settings(self):
        window = tk.Toplevel(self.root)
        window.title('Gemini 設定 · UI Mock')
        window.geometry('540x350')
        window.minsize(500, 320)
        window.transient(self.root)
        window.grab_set()
        frame = ttk.Frame(window, padding=20)
        frame.pack(fill='both', expand=True)
        frame.columnconfigure(0, weight=1)
        ttk.Label(frame, text='API Key（此 mock 不讀取或保存金鑰）').grid(row=0, column=0, sticky='w')
        ttk.Entry(frame, show='●').grid(row=1, column=0, sticky='ew', pady=(6, 14))
        ttk.Label(frame, text='Gemini 模型 ID').grid(row=2, column=0, sticky='w')
        model = ttk.Entry(frame)
        model.insert(0, 'gemini-3.8-flash')
        model.grid(row=3, column=0, sticky='ew', pady=6)
        state = ttk.Label(frame, text='僅展示設定表單，不會連線。', style='Muted.TLabel')
        state.grid(row=4, column=0, sticky='w', pady=14)
        actions = ttk.Frame(frame)
        actions.grid(row=5, column=0, sticky='ew')
        button(actions, '保存設定', lambda: state.configure(text='示範：設定已更新，未寫入磁碟。')).pack(side='left')
        button(actions, '測試連線', lambda: state.configure(text='示範：此 mock 不執行連線測試。')).pack(side='left', padx=5)
        button(actions, '關閉', window.destroy).pack(side='right')
        window.bind('<Escape>', lambda e: window.destroy())


class DocumentMock(tk.Toplevel):
    def __init__(self, app, title, subtitle):
        super().__init__(app.root)
        self.app = app
        self.title(title + ' · UI Mock' if 'UI Mock' not in title else title)
        self.geometry('1200x780+20+20')
        self.minsize(740, 570)
        self.grab_set()
        self.shell = shell = ttk.Frame(self, padding=12)
        shell.pack(fill='both', expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(2, weight=1)
        self.header = ttk.Frame(shell)
        self.header.grid(row=0, column=0, sticky='ew', pady=(0, 8))
        self.header.columnconfigure(0, weight=1)
        self.heading = ttk.Label(self.header, text=subtitle, style='Heading.TLabel')
        self.heading.grid(row=0, column=0, sticky='w')
        self.toolbar = ttk.Frame(shell)
        self.toolbar.grid(row=1, column=0, sticky='ew', pady=(0, 8))
        self.content = ttk.Frame(shell)
        self.content.grid(row=2, column=0, sticky='nsew')
        self.footer = ttk.Frame(shell, padding=(0, 8, 0, 0))
        self.footer.grid(row=3, column=0, sticky='ew')
        self.footer.columnconfigure(0, weight=1)
        ttk.Separator(self.footer).grid(row=0, column=0, columnspan=4, sticky='ew', pady=(0, 7))
        self.status = ttk.Label(self.footer, text='合成示例 · 不處理正式書稿', foreground=MUTED)
        self.status.grid(row=1, column=0, columnspan=4, sticky='ew', pady=(0, 6))
        self.footer.bind('<Configure>', lambda e: self.status.configure(wraplength=max(300, e.width - 24)))
        self.actions = ttk.Frame(self.footer)
        self.actions.grid(row=2, column=0, columnspan=4, sticky='ew')
        self.actions.columnconfigure(0, weight=1)
        self.close_button = button(self.actions, '關閉', self.destroy)
        self.close_button.grid(row=0, column=1, padx=3)
        self.bind('<Escape>', lambda e: self.destroy())
        self.after_idle(lambda: self.state('zoomed'))
        app.children.append(self)


class PdfMock(DocumentMock):
    def __init__(self, app):
        super().__init__(app, '逐頁原稿／頁圖', '第一章　風與樹.pdf · 9 頁')
        self.candidate = False
        self.pending = True
        self.region_mode = False
        self.region = None
        self.zoom = tk.StringVar(value='適合整頁')
        self.page = tk.StringVar(value='1')
        self.rotation = tk.StringVar(value='0°')
        menu(self.header, 'OCR 設定', [('範圍、語言與版面', self.settings),
                                   ('模型與下載', self.settings)]).grid(row=0, column=1, padx=3)
        button(self.header, '詳細資訊', lambda: self.say('合成 PDF · 逐頁原稿與校對全文分開保存；此 mock 不執行 OCR。')).grid(row=0, column=2)
        self.toolbar.columnconfigure(3, weight=1)
        button(self.toolbar, '上一頁', lambda: self.change_page(-1)).grid(row=0, column=0)
        page_box = ttk.Frame(self.toolbar)
        page_box.grid(row=0, column=1, padx=6)
        ttk.Label(page_box, text='第').pack(side='left')
        selector = ttk.Combobox(page_box, textvariable=self.page, values=tuple(map(str, range(1, 10))), width=3, state='readonly')
        selector.pack(side='left', padx=4)
        selector.bind('<<ComboboxSelected>>', lambda e: self.redraw())
        ttk.Label(page_box, text='/ 9 頁').pack(side='left')
        button(self.toolbar, '下一頁', lambda: self.change_page(1)).grid(row=0, column=2)
        self.page_state = ttk.Label(self.toolbar, text='自動中英 · 待檢查', foreground=ERROR)
        self.page_state.grid(row=0, column=3, sticky='w', padx=16)
        menu(self.toolbar, '旋轉', [(v, lambda angle=v: self.rotate(angle)) for v in ('0°', '90°', '180°', '270°')]).grid(row=0, column=4, padx=3)
        menu(self.toolbar, '重辨', [('本頁強制 OCR', self.make_candidate), ('框選區域重辨', self.begin_region_mode),
                                 ('只重試失敗頁', self.make_candidate)]).grid(row=0, column=5, padx=3)
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)
        self.panes = ttk.Panedwindow(self.content, orient='horizontal')
        self.panes.grid(row=0, column=0, sticky='nsew')
        left = ttk.Frame(self.panes, padding=(0, 0, 10, 0))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        self.image_tools = ttk.Frame(left)
        self.image_tools.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 6))
        self.image_tools.columnconfigure(0, weight=1)
        ttk.Label(self.image_tools, text='來源頁圖', style='Heading.TLabel').grid(row=0, column=0, sticky='w')
        size = ttk.Combobox(self.image_tools, textvariable=self.zoom,
                            values=('適合整頁', '適合寬度', '100%', '150%'), width=10, state='readonly')
        size.grid(row=0, column=1)
        size.bind('<<ComboboxSelected>>', lambda e: self.redraw())
        self.canvas = tk.Canvas(left, bg='#e4e8e0', highlightthickness=0, width=320)
        self.canvas.grid(row=1, column=0, sticky='nsew')
        sy = ttk.Scrollbar(left, command=self.canvas.yview)
        sy.grid(row=1, column=1, sticky='ns')
        sx = ttk.Scrollbar(left, orient='horizontal', command=self.canvas.xview)
        sx.grid(row=2, column=0, sticky='ew')
        self.canvas.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.canvas.bind('<Configure>', lambda e: self.redraw())
        self.canvas.bind('<MouseWheel>', lambda e: self.canvas.yview_scroll(-int(e.delta / 120), 'units'))
        self.canvas.bind('<ButtonPress-1>', self.start_region)
        self.canvas.bind('<B1-Motion>', self.drag_region)
        self.canvas.bind('<ButtonRelease-1>', self.end_region)
        self.tabs = ttk.Notebook(self.panes)
        self.texts = []
        for title in ('本次文字', '原逐頁原稿', '原批校對全文'):
            frame, text = text_pane(self.tabs, title + ' · 唯讀')
            self.tabs.add(frame, text=title)
            fill(text, SOURCE if title == '原批校對全文' else SOURCE.split('Hello, world!')[0])
            text.configure(exportselection=False)
            self.texts.append(text)
        self.panes.add(left, weight=1)
        self.panes.add(self.tabs, weight=1)
        self.page_actions = ttk.Frame(self.actions)
        self.page_actions.grid(row=0, column=0, sticky='w')
        self.disposition = ttk.Label(self.page_actions, text='本頁：待檢查', foreground=ERROR)
        self.disposition.pack(side='left', padx=(0, 12))
        button(self.page_actions, '確認保留', self.retain).pack(side='left', padx=3)
        button(self.page_actions, '略過本頁', self.skip).pack(side='left', padx=3)
        self.accept_var = tk.BooleanVar(value=True)
        self.adopt_check = ttk.Checkbutton(self.page_actions, text='採用本頁候選', variable=self.accept_var)
        self.adopt_button = button(self.actions, '採用為新批次', self.adopt, primary=True)
        self.region_execute = button(self.actions, '重辨框選區域', self.make_candidate, primary=True)
        self.say('合成頁圖與文字 · 選擇「重辨」可預覽候選操作；此 mock 不執行辨識。')

    def say(self, value):
        self.status.configure(text=value)

    def change_page(self, increment):
        self.page.set(str(max(1, min(9, int(self.page.get()) + increment))))
        self.redraw()

    def rotate(self, angle):
        self.rotation.set(angle)
        self.say('已選重辨旋轉：' + angle + '。合成頁圖保持正向，方便比較元件配置。')

    def redraw(self):
        if not hasattr(self, 'canvas'):
            return
        c = self.canvas
        c.delete('all')
        width, height = max(100, c.winfo_width()), max(100, c.winfo_height())
        if self.zoom.get() == '適合整頁':
            scale = min((width - 32) / 600, (height - 32) / 800)
        elif self.zoom.get() == '適合寬度':
            scale = (width - 32) / 600
        else:
            scale = float(self.zoom.get().strip('%')) / 100
        scale = max(.15, scale)
        page_w, page_h = 600 * scale, 800 * scale
        x, y = max(16, (width - page_w) / 2), 16
        self.page_rect = (x, y, page_w, page_h)
        c.create_rectangle(x, y, x + page_w, y + page_h, fill=PAPER, outline='#c7d2c6')
        c.create_text(x + 60 * scale, y + 65 * scale, text='第一章　風與樹', anchor='nw', fill=INK,
                      font=('Microsoft JhengHei', max(10, int(22 * scale)), 'bold'))
        paragraphs = ['清晨，山谷裡的風帶著露水的氣息。', '他推開窗，看見樹影落在書頁上。', '',
                      '「今天就從這一頁開始吧。」她說。', '', '他把書放在桌上，沿著文字慢慢往下讀。',
                      '窗外的樹葉輕輕晃動，陽光停在紙上。', '', '校對時，先看清楚原文。',
                      '遇到不確定的地方，再回到原頁，', '核對字形與上下文。', '', '有些斷行，只是排版留下的痕跡。',
                      '讀到這裡，她停了一下。', '風仍然吹著，書頁也仍然攤開。']
        for i, line in enumerate(paragraphs):
            c.create_text(x + 60 * scale, y + (140 + 34 * i) * scale, text=line, anchor='nw', fill=INK,
                          font=('Microsoft JhengHei', max(8, int(15 * scale))))
        c.create_text(x + page_w / 2, y + 758 * scale, text=f'— {self.page.get()} —', fill=MUTED,
                      font=('Microsoft JhengHei', max(8, int(12 * scale))))
        c.configure(scrollregion=(0, 0, max(width, page_w + 32), max(height, page_h + 32)))
        c.xview_moveto(0)
        c.yview_moveto(0)
        self.region = None

    def begin_region_mode(self):
        self.region_mode = True
        self.tabs.select(0)
        self.region_execute.grid(row=0, column=2, padx=3)
        self.adopt_button.grid_remove()
        self.say('區域重辨：① 在左側框選圖片　② 在本次文字反白原文　③ 按「重辨框選區域」。')

    def start_region(self, event):
        if self.region_mode:
            self.region_origin = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
            self.canvas.delete('region')

    def drag_region(self, event):
        if self.region_mode and hasattr(self, 'region_origin'):
            self.canvas.delete('region')
            self.canvas.create_rectangle(*self.region_origin, self.canvas.canvasx(event.x), self.canvas.canvasy(event.y), outline=GREEN, width=2, tags='region')

    def end_region(self, event):
        if self.region_mode and hasattr(self, 'region_origin'):
            self.region = (*self.region_origin, self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
            del self.region_origin
            self.say('① 已框選圖片。請在右側「本次文字」反白原文，再按「重辨框選區域」。')

    def make_candidate(self):
        if self.region_mode and (not self.region or not self.texts[0].tag_ranges('sel')):
            return self.say('請先框選圖片，並在「本次文字」反白要替換的原文。')
        self.region_mode = False
        self.candidate = True
        self.region_execute.grid_remove()
        self.adopt_check.pack(side='left', padx=12)
        self.adopt_button.grid(row=0, column=2, padx=3)
        self.close_button.configure(text='捨棄候選並關閉')
        fill(self.texts[0], SOURCE.split('Hello, world!')[0].replace('慢慢往下讀', '緩緩往下讀'))
        self.tabs.select(0)
        self.page_state.configure(text='示範候選 · 待採用')
        self.say('示範候選已產生。採用將建立新批次；原批人工校對不帶入。本次僅更新 mock。')

    def retain(self):
        self.pending = False
        self.disposition.configure(text='本頁：已處理', foreground=GREEN)
        self.page_state.configure(text='自動中英 · 已確認保留', foreground=GREEN)
        self.say('示範：本頁來源疑點已確認保留；候選採用仍為獨立操作。')

    def skip(self):
        if messagebox.askyesno('略過本頁 · UI Mock', '示範明確略過本頁來源疑點？\n不會刪除原文，也不會採用候選。', parent=self):
            self.disposition.configure(text='本頁：已略過', foreground=MUTED)
            self.say('示範：已明確略過本頁來源疑點。')

    def adopt(self):
        self.app.say('示範：已採用候選為新批次；未寫入正式專案。')
        self.destroy()

    def settings(self):
        window = tk.Toplevel(self)
        window.title('範圍與 OCR 設定 · UI Mock')
        window.geometry('560x440')
        window.transient(self)
        window.grab_set()
        frame = ttk.Frame(window, padding=20)
        frame.pack(fill='both', expand=True)
        frame.columnconfigure(1, weight=1)
        for i, (label, values) in enumerate((('擷取頁範圍', ('1–9（全部）', '僅本頁')),
                 ('擷取方式', ('自動', '文字層', '全部強制 OCR')), ('辨識語言', ('自動中英', '繁中＋英文', '簡中＋英文', '英文')),
                 ('辨識版面', ('自動版面', '單一區塊', '單行標題')))):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky='w', padx=(0, 15), pady=10)
            control = ttk.Combobox(frame, values=values, state='readonly')
            control.current(0)
            control.grid(row=i, column=1, sticky='ew', pady=10)
        ttk.Label(frame, text='合成示範：模型狀態與下載不會連線。', style='Muted.TLabel').grid(row=4, column=0, columnspan=2, pady=14)
        button(frame, '模型與下載', lambda: self.say('示範：此 mock 不下載模型。')).grid(row=5, column=0, sticky='w')
        button(frame, '完成', window.destroy, primary=True).grid(row=5, column=1, sticky='e')
        window.bind('<Destroy>', lambda e: self.grab_set() if e.widget is window and self.winfo_exists() else None)
        window.bind('<Escape>', lambda e: window.destroy())


class BreaksMock(DocumentMock):
    def __init__(self, app):
        super().__init__(app, '預覽換行整理', '換行整理 · 第一章　風與樹')
        button(self.header, '規則說明', lambda: self.status.configure(text='只將單一斷行換成空格；保留空白行，不刪頁首頁尾，不處理跨行連字號。')).grid(row=0, column=1)
        self.original = app.editor.get('1.0', 'end-1c')
        self.candidate = re.sub(r'(?<!\n)\n(?!\n)', ' ', self.original)
        ttk.Label(self.toolbar, text='對照原始換行與整理候選 · 套用後可一次復原', foreground=MUTED).pack(side='left')
        self.layout = tk.StringVar(value='並排對照')
        mode = ttk.Combobox(self.toolbar, textvariable=self.layout, values=('並排對照', '只看候選'), state='readonly', width=12)
        mode.pack(side='right')
        mode.bind('<<ComboboxSelected>>', lambda e: self.toggle())
        self.panes = ttk.Panedwindow(self.content, orient='horizontal')
        self.panes.pack(fill='both', expand=True)
        self.original_frame, original_text = text_pane(self.panes, '原始換行 · 唯讀')
        self.candidate_frame, candidate_text = text_pane(self.panes, '整理候選 · 標色為變更')
        self.panes.add(self.original_frame, weight=1)
        self.panes.add(self.candidate_frame, weight=1)
        fill(original_text, self.original)
        fill(candidate_text, self.candidate)
        candidate_text.tag_configure('diff', background='#f7dfad', foreground='#332b1b')
        for tag, a, b, c, d in difflib.SequenceMatcher(None, self.original, self.candidate, autojunk=False).get_opcodes():
            if tag != 'equal':
                candidate_text.tag_add('diff', f'1.0+{c}c', f'1.0+{d}c')
        count = sum(1 for m in re.finditer(r'(?<!\n)\n(?!\n)', self.original))
        self.status.configure(text=f'待套用：{count} 處單一換行 · 原稿尚未變更 · 合成示例')
        self.close_button.configure(text='取消')
        button(self.actions, '套用整理', self.apply, primary=True).grid(row=0, column=2, padx=3)

    def toggle(self):
        if self.layout.get() == '只看候選':
            self.panes.forget(self.original_frame)
        elif str(self.original_frame) not in self.panes.panes():
            self.panes.insert(0, self.original_frame, weight=1)

    def apply(self):
        if self.app.editor.get('1.0', 'end-1c') != self.original:
            self.status.configure(text='目前編輯已變更，請關閉後重新預覽。')
            return
        editor = self.app.editor
        editor.edit_separator()
        editor.configure(autoseparators=False)
        editor.delete('1.0', 'end')
        editor.insert('1.0', self.candidate)
        editor.configure(autoseparators=True)
        editor.edit_separator()
        self.app.say('已對合成書稿套用整理候選；可按 Ctrl+Z 復原。')
        self.destroy()


class ReviewMock(DocumentMock):
    old: tk.Text
    new: tk.Text

    def __init__(self, app):
        super().__init__(app, 'Gemini 候選差異', '候選審閱 · 合成示例')
        self.part = 0
        self.decisions = ['待確認'] * 5
        self.paragraphs = [p for p in SOURCE.split('\n\n') if p.strip()][:5]
        self.toolbar.columnconfigure(2, weight=1)
        button(self.toolbar, '上一段', lambda: self.change(-1)).grid(row=0, column=0)
        button(self.toolbar, '下一待確認', self.next_pending).grid(row=0, column=1, padx=6)
        self.progress = ttk.Label(self.toolbar)
        self.progress.grid(row=0, column=2, sticky='w', padx=12)
        menu(self.toolbar, '批次操作', [('採用全部待確認段', self.accept_all), ('撤回本次全部採用', self.reset)]).grid(row=0, column=3)
        panes = ttk.Panedwindow(self.content, orient='horizontal')
        panes.pack(fill='both', expand=True)
        for title, attr in (('送出時原文 · 唯讀', 'old'), ('候選文字 · 標色為差異', 'new')):
            frame, text = text_pane(panes, title)
            panes.add(frame, weight=1)
            setattr(self, attr, text)
        button(self.actions, '拒絕本段', lambda: self.decide('已拒絕')).grid(row=0, column=0, sticky='w')
        button(self.actions, '採用本段', lambda: self.decide('已採用'), primary=True).grid(row=0, column=2, padx=3)
        self.load()

    def load(self):
        text = self.paragraphs[self.part]
        candidate = text.replace('慢慢', '緩緩').replace('今天', '今日')
        fill(self.old, text)
        fill(self.new, candidate)
        self.new.tag_configure('diff', background='#f7dfad', foreground='#332b1b')
        for tag, a, b, c, d in difflib.SequenceMatcher(None, text, candidate, autojunk=False).get_opcodes():
            if tag != 'equal':
                self.new.tag_add('diff', f'1.0+{c}c', f'1.0+{d}c')
        self.progress.configure(text=f'第 {self.part+1} / 5 段 · 待確認 {self.decisions.count("待確認")} · 已採用 {self.decisions.count("已採用")}')
        self.status.configure(text=f'本段：{self.decisions[self.part]} · 示範候選，未連線 Gemini、未改動校對稿。')

    def change(self, value):
        self.part = (self.part + value) % 5
        self.load()

    def next_pending(self):
        for step in range(1, 6):
            index = (self.part + step) % 5
            if self.decisions[index] == '待確認':
                self.part = index
                break
        self.load()

    def decide(self, value):
        self.decisions[self.part] = value
        self.load()

    def accept_all(self):
        self.decisions = ['已採用' if x == '待確認' else x for x in self.decisions]
        self.load()

    def reset(self):
        self.decisions = ['待確認'] * 5
        self.load()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screen', choices=('main', 'pdf', 'breaks', 'review', 'ai'), default='main')
    parser.add_argument('--narrow', action='store_true')
    parser.add_argument('--auto-close', type=int, default=0, help='Optional QA timeout in seconds')
    args = parser.parse_args()
    root = tk.Tk()
    app = WorkbenchMock(root, args.narrow)
    if not args.narrow:
        root.after_idle(lambda: root.state('zoomed'))
    if args.screen == 'ai':
        app.tools.select(1)
    elif args.screen != 'main':
        root.after(200, {'pdf': app.open_pdf, 'breaks': app.open_breaks, 'review': app.open_review}[args.screen])
    if args.auto_close:
        root.after(args.auto_close * 1000, root.destroy)
    root.mainloop()


if __name__ == '__main__':
    main()
