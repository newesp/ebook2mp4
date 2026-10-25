"""Traditional Chinese A-layout desktop workbench. No browser or server."""
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from .workflow import ProjectError, ProjectWorkflow


INK = '#263d34'
GREEN = '#315d43'
BG = '#f5f6f2'
MUTED = '#58695f'


def text_pane(parent, heading, editable=False):
    frame = ttk.Frame(parent, padding=12)
    frame.rowconfigure(1, weight=1)
    frame.columnconfigure(0, weight=1)
    ttk.Label(frame, text=heading, style='Heading.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 10))
    text = tk.Text(frame, wrap='word', undo=editable, width=1, height=6,
                   font=('Microsoft JhengHei', 12), bg='#fffef9' if not editable else '#ffffff',
                   fg=INK, insertbackground=GREEN, selectbackground='#c5ddc8',
                   relief='flat', padx=16, pady=16, spacing1=3, spacing3=8,
                   highlightthickness=1, highlightbackground='#dfe5dd', highlightcolor=GREEN)
    text.grid(row=1, column=0, sticky='nsew')
    scroll = ttk.Scrollbar(frame, command=text.yview)
    scroll.grid(row=1, column=1, sticky='ns')
    text.configure(yscrollcommand=scroll.set)
    if not editable:
        text.configure(state='disabled')
    return frame, text


class Workbench(ttk.Frame):
    def __init__(self, root):
        super().__init__(root, padding=16)
        self.root = root
        self.flow = None
        self.batch_id = None
        self.saved_text = ''
        self.step = 1
        self._loading = False
        self.pack(fill='both', expand=True)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        self._build()
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.bind('<Control-s>', lambda e: self.save())
        self.refresh()

    def _build(self):
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky='ew', pady=(0, 16))
        top.columnconfigure(0, weight=1)
        ttk.Label(top, text='書籍製作工作台', style='Title.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Button(top, text='建立書籍專案', command=self.create).grid(row=0, column=1, padx=4)
        ttk.Button(top, text='開啟專案', command=self.open).grid(row=0, column=2, padx=4)
        self.save_button = ttk.Button(top, text='儲存校對稿  Ctrl+S', command=self.save, style='Primary.TButton')
        self.save_button.grid(row=0, column=3, padx=(4, 0))

        nav = ttk.Frame(self)
        nav.grid(row=1, column=0, sticky='ew')
        self.steps = []
        for index, name in enumerate(('來源', '校對', '語音', '影片'), 1):
            nav.columnconfigure(index - 1, weight=1)
            button = ttk.Button(nav, text=f'{index}  {name}', command=lambda n=index: self.show_step(n))
            button.grid(row=0, column=index - 1, sticky='ew', padx=2)
            self.steps.append(button)
        self.notice = ttk.Label(self, text='', wraplength=1000, padding=(8, 12))
        self.notice.grid(row=2, column=0, sticky='ew')

        # Fixed count of columns with explicit minimum widths; manuscript columns flex.
        body = ttk.Frame(self)
        body.grid(row=3, column=0, sticky='nsew')
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, minsize=190)
        body.columnconfigure(1, weight=1, minsize=470)
        body.columnconfigure(2, minsize=240)

        left = ttk.Frame(body, padding=(4, 10, 16, 10))
        left.grid(row=0, column=0, sticky='nsew')
        left.columnconfigure(0, weight=1)
        ttk.Label(left, text='書籍與製作批次', style='Heading.TLabel').grid(row=0, column=0, sticky='w')
        self.book = ttk.Label(left, wraplength=175, text='', style='Book.TLabel')
        self.book.grid(row=1, column=0, sticky='w', pady=(20, 10))
        self.batch = ttk.Button(left, text='尚未匯入 TXT', command=lambda: self.show_step(2))
        self.batch.grid(row=2, column=0, sticky='ew', pady=6)
        self.import_button = ttk.Button(left, text='匯入第一份 TXT', command=self.import_txt)
        self.import_button.grid(row=4, column=0, sticky='ew', pady=(6, 20))
        ttk.Label(left, text='專案位置', style='Heading.TLabel').grid(row=5, column=0, sticky='w')
        self.location = tk.Text(left, width=21, height=7, wrap='char', relief='flat', bg=BG,
                                fg=MUTED, font=('Microsoft JhengHei', 10), takefocus=True)
        self.location.grid(row=6, column=0, sticky='ew', pady=8)
        self.folder_button = ttk.Button(left, text='開啟專案資料夾', command=self.open_folder)
        self.folder_button.grid(row=7, column=0, sticky='ew')

        center = ttk.Frame(body)
        center.grid(row=0, column=1, sticky='nsew')
        center.rowconfigure(1, weight=1)
        center.columnconfigure(0, weight=1)
        self.source_meta = ttk.Label(center, text='', padding=(12, 8), wraplength=500)
        self.source_meta.grid(row=0, column=0, sticky='ew')
        panes = ttk.Panedwindow(center, orient='horizontal')
        panes.grid(row=1, column=0, sticky='nsew')
        source_frame, self.source = text_pane(panes, '來源原文 · TXT')
        editor_frame, self.editor = text_pane(panes, '校對稿 · 可編輯', True)
        panes.add(source_frame, weight=1)
        panes.add(editor_frame, weight=1)
        self.editor.bind('<<Modified>>', self.edited)
        self.stats = ttk.Label(center, text='', padding=(12, 10))
        self.stats.grid(row=2, column=0, sticky='ew')

        inspector = ttk.Frame(body)
        inspector.grid(row=0, column=2, sticky='nsew')
        inspector.rowconfigure(0, weight=1)
        inspector.columnconfigure(0, weight=1)
        canvas = tk.Canvas(inspector, width=240, highlightthickness=0, bg=BG)
        canvas.grid(row=0, column=0, sticky='nsew')
        scrollbar = ttk.Scrollbar(inspector, command=canvas.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        canvas.configure(yscrollcommand=scrollbar.set)
        right = ttk.Frame(canvas, padding=(12, 10, 4, 10))
        window = canvas.create_window(0, 0, anchor='nw', window=right)
        right.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfigure(window, width=e.width))
        ttk.Label(right, text='校對與朗讀確認', style='Heading.TLabel').pack(anchor='w', pady=(0, 20))
        for title, reason, action in (
            ('Gemini 校對', 'T07 將提供金鑰設定與候選差異。\n目前可直接人工編輯校對稿。', '提出校對建議'),
            ('朗讀稿確認', 'T03 將提供確認與版本快照。\n目前保存的是校對稿。', '確認朗讀稿'),
            ('語音與影片', 'T09 起提供語音，T16 起提供影片。\n尚無已確認朗讀稿或有效音訊。', '產生成品'),
        ):
            ttk.Label(right, text=title, style='Heading.TLabel').pack(anchor='w', pady=(0, 8))
            ttk.Label(right, text=reason, wraplength=220, foreground=MUTED).pack(anchor='w')
            ttk.Button(right, text=action, state='disabled').pack(fill='x', pady=(10, 24))

        self.status = ttk.Label(self, text='', padding=(8, 10))
        self.status.grid(row=4, column=0, sticky='ew')
        self.bind('<Configure>', lambda e: self.status.configure(wraplength=max(300, self.winfo_width() - 48)))

    @property
    def current_text(self):
        return self.editor.get('1.0', 'end-1c')

    @property
    def dirty(self):
        return self.batch_id is not None and self.current_text != self.saved_text

    def edited(self, _event=None):
        if self.editor.edit_modified():
            self.editor.edit_modified(False)
            if not self._loading:
                self.update_stats()

    def update_stats(self):
        text = self.current_text if self.batch_id else ''
        import re
        paragraphs = len([p for p in re.split(r'\r?\n\s*\r?\n', text) if p.strip()])
        revision = self.flow.state['batches'][0]['revision'] if self.batch_id else 0
        self.stats.configure(text=f'{len(text):,} 字元 · {paragraphs:,} 段 · 版本 {revision} · '
                             + ('尚未儲存' if self.dirty else '已儲存' if self.batch_id else '等待匯入'))
        self.save_button.configure(state='normal' if self.dirty else 'disabled')
        self.root.title(('＊' if self.dirty else '') + (self.flow.state['name'] if self.flow else '書籍製作工作台') + ' — ebook2mp4')

    def show_step(self, n):
        self.step = n
        reasons = {
            1: '來源：先建立書籍專案，再預覽並匯入 UTF-8 TXT。PDF／OCR 將於 T04／T05 提供。',
            2: '校對：左欄保留來源原文，右欄編輯校對稿。按 Ctrl+S 儲存；朗讀稿確認將於 T03 提供。',
            3: '語音尚未提供：需要 T03 的朗讀稿確認及 T09 的語音服務。可返回來源或校對繼續編輯。',
            4: '影片尚未提供：需要有效音訊與視覺素材，T16 起提供製片。可返回校對，已輸入文字仍保留。',
        }
        self.notice.configure(text=reasons[n])
        for i, button in enumerate(self.steps, 1):
            button.configure(style='Primary.TButton' if i == n else 'TButton')

    @staticmethod
    def fill(widget, content, editable=False):
        widget.configure(state='normal')
        widget.delete('1.0', 'end')
        widget.insert('1.0', content)
        if not editable:
            widget.configure(state='disabled')

    def refresh(self):
        self._loading = True
        manifest = self.flow.state if self.flow else None
        batches = manifest['batches'] if manifest else []
        self.book.configure(text=manifest['name'] if manifest else '尚未建立書籍專案')
        self.fill(self.location, str(self.flow.root) if self.flow else '建立後顯示保存位置')
        self.folder_button.configure(state='normal' if self.flow else 'disabled')
        self.import_button.configure(state='normal' if self.flow and not batches else 'disabled')
        if batches:
            batch = batches[0]
            self.batch_id = batch['id']
            original, draft = self.flow.texts(self.batch_id)
            self.saved_text = draft
            self.batch.configure(text='第一個製作批次', state='normal')
            source = batch['source']
            self.source_meta.configure(text=f'{source["original_name"]} · {source["size"]:,} 位元組 · {source["encoding"]} · 可讀\nTXT 來源，無 PDF 頁碼')
            self.fill(self.source, original)
            self.fill(self.editor, draft, True)
            self.editor.edit_reset()
        else:
            self.batch_id = None
            self.saved_text = ''
            self.batch.configure(text='尚未匯入 TXT', state='disabled')
            self.source_meta.configure(text='建立專案後匯入第一份 TXT；原文與校對稿分開保存。')
            self.fill(self.source, '匯入後在此查看來源原文。')
            self.fill(self.editor, '')
        self.editor.edit_modified(False)
        self._loading = False
        self.update_stats()
        self.show_step(self.step)
        self.status.configure(text='所有書稿資料保存在本機。' if not self.flow else '已載入專案 · 原始來源檔不會被改寫')

    def report(self, error):
        self.status.configure(text=str(error), foreground='#963b32')
        messagebox.showerror('操作未完成', str(error), parent=self.root)

    def may_leave(self):
        if not self.dirty:
            return True
        answer = messagebox.askyesnocancel('校對稿尚未儲存', '是否先儲存校對稿？\n選「否」會捨棄本次未存的編輯；取消則留在目前專案。', parent=self.root)
        if answer is None:
            return False
        return self.save() if answer else True

    def create(self):
        if not self.may_leave():
            return
        name = simpledialog.askstring('建立書籍專案', '書籍名稱：', parent=self.root)
        if not name:
            return
        parent = filedialog.askdirectory(title='選擇新專案的上層資料夾', parent=self.root)
        if not parent:
            return
        folder_name = simpledialog.askstring('專案資料夾', '新資料夾名稱（必須尚不存在或為空）：', initialvalue=name, parent=self.root)
        if not folder_name:
            return
        if folder_name in ('.', '..') or any(c in folder_name for c in '<>:"/\\|?*') or folder_name.endswith((' ', '.')):
            self.report(ProjectError('資料夾名稱不可包含 Windows 保留符號、路徑或結尾空白／句點。請換一個名稱。'))
            return
        try:
            flow = ProjectWorkflow.create(Path(parent) / folder_name, name)
            self.flow = flow
            self.step = 1
            self.refresh()
        except ProjectError as e:
            self.report(e)

    def open(self):
        if not self.may_leave():
            return
        path = filedialog.askopenfilename(title='選擇書籍專案 project.json', filetypes=[('書籍專案', 'project.json')], parent=self.root)
        if not path:
            return
        try:
            flow = ProjectWorkflow.open(path)
            self.flow = flow
            self.step = 2 if flow.state['batches'] else 1
            self.refresh()
        except ProjectError as e:
            self.report(e)

    def import_txt(self):
        if not self.flow:
            return
        path = filedialog.askopenfilename(title='選擇 UTF-8 TXT', filetypes=[('文字檔', '*.txt')], parent=self.root)
        if not path:
            return
        try:
            preview = self.flow.inspect_txt(path)
            info = self.flow.import_requirements(preview)
        except (ProjectError, OSError) as e:
            self.report(e if isinstance(e, ProjectError) else ProjectError('無法讀取專案磁碟資訊，請檢查磁碟後重試。'))
            return
        dialog = tk.Toplevel(self.root)
        dialog.title('匯入前預覽')
        dialog.geometry('720x560')
        dialog.minsize(600, 420)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(1, weight=1)
        enough = info['free_bytes'] >= info['required_bytes'] + 65536
        details = (f'檔名：{preview.path.name}\n大小：{preview.size:,} 位元組 · {preview.encoding} · 可讀\n'
                   f'專案位置：{info["project_location"]}\n來源副本所需空間：{preview.size:,} 位元組\n'
                   f'本次保存估計：{info["required_bytes"]:,} 位元組 + 65,536 安全餘額\n'
                   f'磁碟可用：{info["free_bytes"]:,} 位元組\n原始來源檔保持不變。')
        detail_label = ttk.Label(dialog, text=details, wraplength=660, padding=16)
        detail_label.grid(row=0, column=0, sticky='ew')
        dialog.bind('<Configure>', lambda e: detail_label.configure(wraplength=max(200, dialog.winfo_width() - 40)))
        frame, text = text_pane(dialog, '來源預覽 · 匯入後成為第一個製作批次')
        frame.grid(row=1, column=0, sticky='nsew')
        self.fill(text, preview.text)
        actions = ttk.Frame(dialog, padding=12)
        actions.grid(row=2, column=0, sticky='ew')
        ttk.Button(actions, text='取消', command=dialog.destroy).pack(side='left')

        def commit():
            try:
                self.flow.import_txt(preview)
                dialog.destroy()
                self.step = 2
                self.refresh()
            except ProjectError as e:
                self.report(e)

        ttk.Button(actions, text='確認匯入' if enough else '空間不足，請釋放空間', command=commit,
                   style='Primary.TButton', state='normal' if enough else 'disabled').pack(side='right')
        dialog.bind('<Escape>', lambda e: dialog.destroy())

    def save(self):
        if not self.batch_id:
            return True
        try:
            self.flow.save_draft(self.batch_id, self.current_text)
            self.saved_text = self.current_text
            self.update_stats()
            self.status.configure(text='校對稿已儲存 · 可關閉並重新開啟繼續', foreground=GREEN)
            return True
        except ProjectError as e:
            self.report(e)
            return False

    def open_folder(self):
        import os
        if self.flow:
            try:
                os.startfile(self.flow.root)
            except OSError:
                self.report(ProjectError('無法開啟檔案總管。可從左側複製專案位置後手動開啟。'))

    def close(self):
        if self.may_leave():
            self.root.destroy()


def make_app():
    root = tk.Tk()
    root.geometry('1360x820')
    root.minsize(1040, 640)
    root.configure(background=BG)
    root.option_add('*Font', ('Microsoft JhengHei', 10))
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('.', font=('Microsoft JhengHei', 10), background=BG, foreground=INK)
    style.configure('TButton', padding=(10, 8), background='#ffffff', bordercolor='#c7d2c6')
    style.map('TButton', background=[('active', '#e9f0e5')], foreground=[('disabled', '#68736c')])
    style.configure('Primary.TButton', background=GREEN, foreground='#ffffff')
    style.map('Primary.TButton', background=[('disabled', '#e1e5de'), ('active', '#264d35')],
              foreground=[('disabled', '#68736c')])
    style.configure('Title.TLabel', font=('Microsoft JhengHei', 19, 'bold'))
    style.configure('Heading.TLabel', font=('Microsoft JhengHei', 11, 'bold'))
    style.configure('Book.TLabel', font=('Microsoft JhengHei', 13, 'bold'))
    return root, Workbench(root)


def main():
    root, _app = make_app()
    root.mainloop()
