"""Traditional Chinese A-layout desktop workbench. No browser or server."""
from pathlib import Path
from functools import partial
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from .workflow import ImportPreview, ProjectError, ProjectWorkflow


INK = '#263d34'
GREEN = '#315d43'
BG = '#f5f6f2'
MUTED = '#58695f'


def bind_canvas_wheel(canvas, widget=None):
    """Keep local scroll areas usable with both wheel and small touchpad deltas."""
    def scroll(event):
        if event.delta:
            units = -int(event.delta / 120) if abs(event.delta) >= 120 else (-1 if event.delta > 0 else 1)
            canvas.yview_scroll(units, 'units')
        return 'break'
    widget = canvas if widget is None else widget
    widget.bind('<MouseWheel>', scroll)
    for child in widget.winfo_children():
        bind_canvas_wheel(canvas, child)


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
        self.flow: ProjectWorkflow | None = None
        self.batch_id: str | None = None
        self.saved_text = ''
        self.step = 1
        self._loading = False
        self.pdf_dialog = None
        self.pack(fill='both', expand=True)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        self._build()
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.bind('<Control-s>', lambda e: self.save())
        self.root.bind('<Control-f>', lambda e: self.find_entry.focus_set())
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
            button = ttk.Button(nav, text=f'{index}  {name}', command=partial(self.show_step, index))
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
        left.rowconfigure(2, weight=1, minsize=80)
        left.rowconfigure(3, weight=1, minsize=160)
        ttk.Label(left, text='書籍與製作批次', style='Heading.TLabel').grid(row=0, column=0, sticky='w')
        self.book = ttk.Label(left, wraplength=175, text='', style='Book.TLabel')
        self.book.grid(row=1, column=0, sticky='w', pady=(20, 10))
        batch_panel = ttk.Frame(left)
        batch_panel.grid(row=2, column=0, sticky='nsew', pady=6)
        batch_panel.rowconfigure(0, weight=1)
        batch_panel.columnconfigure(0, weight=1)
        self.batch_list = ttk.Treeview(batch_panel, show='tree', selectmode='browse', height=4)
        self.batch_list.column('#0', width=155, minwidth=100)
        self.batch_list.grid(row=0, column=0, sticky='nsew')
        batch_scroll = ttk.Scrollbar(batch_panel, command=self.batch_list.yview)
        batch_scroll.grid(row=0, column=1, sticky='ns')
        self.batch_list.configure(yscrollcommand=batch_scroll.set)
        self.batch_list.bind('<<TreeviewSelect>>', self.select_batch)
        tool_canvas = tk.Canvas(left, width=175, height=250, bg=BG, highlightthickness=0)
        tool_canvas.grid(row=3, column=0, sticky='nsew')
        left_scroll = ttk.Scrollbar(left, command=tool_canvas.yview)
        left_scroll.grid(row=3, column=1, sticky='ns')
        tool_canvas.configure(yscrollcommand=left_scroll.set)
        tools = ttk.Frame(tool_canvas)
        tools.columnconfigure(0, weight=1)
        tool_window = tool_canvas.create_window(0, 0, window=tools, anchor='nw')
        tool_canvas.bind('<Configure>', lambda e: tool_canvas.itemconfigure(tool_window, width=e.width))
        tools.bind('<Configure>', lambda e: tool_canvas.configure(scrollregion=tool_canvas.bbox('all')))
        batch_actions = ttk.Frame(tools)
        batch_actions.grid(row=0, column=0, sticky='ew')
        for col in range(3):
            batch_actions.columnconfigure(col, weight=1)
        self.rename_button = ttk.Button(batch_actions, text='命名', width=3, command=self.rename_batch)
        self.rename_button.grid(row=0, column=0, sticky='ew')
        self.up_button = ttk.Button(batch_actions, text='上移', width=3, command=partial(self.move_batch, -1))
        self.up_button.grid(row=0, column=1, sticky='ew')
        self.down_button = ttk.Button(batch_actions, text='下移', width=3, command=partial(self.move_batch, 1))
        self.down_button.grid(row=0, column=2, sticky='ew')
        self.import_button = ttk.Button(tools, text='新增 TXT 批次', command=self.import_txt)
        self.import_button.grid(row=1, column=0, sticky='ew', pady=(6, 12))
        pdf_actions = ttk.Frame(tools)
        pdf_actions.grid(row=2, column=0, sticky='ew', pady=8)
        self.pdf_button = ttk.Button(pdf_actions, text='新增 PDF 範圍', command=self.import_pdf)
        self.pdf_button.pack(fill='x')
        self.pages_button = ttk.Button(pdf_actions, text='逐頁原稿／頁圖', command=self.compare_pdf_pages)
        self.pages_button.pack(fill='x', pady=4)
        self.cleanup_button = ttk.Button(pdf_actions, text='預覽換行整理', command=self.cleanup_line_breaks)
        self.cleanup_button.pack(fill='x')
        ttk.Label(tools, text='專案位置', style='Heading.TLabel').grid(row=3, column=0, sticky='w')
        self.project_location = tk.Text(tools, width=21, height=4, wrap='char', relief='flat', bg=BG,
                                fg=MUTED, font=('Microsoft JhengHei', 10), takefocus=True)
        self.project_location.grid(row=4, column=0, sticky='ew', pady=8)
        self.folder_button = ttk.Button(tools, text='開啟專案資料夾', command=self.open_folder)
        self.folder_button.grid(row=5, column=0, sticky='ew')
        bind_canvas_wheel(tool_canvas)

        center = ttk.Frame(body)
        center.grid(row=0, column=1, sticky='nsew')
        center.rowconfigure(1, weight=1)
        center.columnconfigure(0, weight=1)
        self.source_meta = ttk.Label(center, text='', padding=(12, 8), wraplength=500)
        self.source_meta.grid(row=0, column=0, sticky='ew')
        panes = ttk.Panedwindow(center, orient='horizontal')
        panes.grid(row=1, column=0, sticky='nsew')
        source_frame, self.source = text_pane(panes, '來源原文 · TXT')
        self.source_heading = source_frame.grid_slaves(row=0)[0]
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
        ttk.Label(right, text='搜尋文字（完全相符）').pack(anchor='w')
        self.find_text = tk.StringVar()
        self.find_entry = ttk.Entry(right, textvariable=self.find_text, width=18)
        self.find_entry.pack(fill='x', pady=4)
        self.find_entry.bind('<Return>', lambda e: self.find_next())
        self.find_button = ttk.Button(right, text='尋找下一個  Ctrl+F', command=self.find_next)
        self.find_button.pack(fill='x', pady=(0, 8))
        ttk.Label(right, text='取代為').pack(anchor='w')
        self.replace_text = tk.StringVar()
        ttk.Entry(right, textvariable=self.replace_text, width=18).pack(fill='x', pady=4)
        replacements = ttk.Frame(right)
        replacements.pack(fill='x')
        replacements.columnconfigure((0, 1), weight=1, uniform='replace')
        self.replace_button = ttk.Button(replacements, text='取代一處', width=6, command=self.replace_one)
        self.replace_button.grid(row=0, column=0, sticky='ew', padx=(0, 2))
        self.replace_all_button = ttk.Button(replacements, text='全部取代', width=6, command=self.replace_all)
        self.replace_all_button.grid(row=0, column=1, sticky='ew', padx=(2, 0))
        self.undo_button = ttk.Button(right, text='復原  Ctrl+Z', command=self.undo)
        self.undo_button.pack(fill='x', pady=(6, 8))
        self.export_button = ttk.Button(right, text='匯出目前校對稿 TXT', command=self.export_txt)
        self.export_button.pack(fill='x', pady=3)
        self.reload_button = ttk.Button(right, text='重載外部校對稿', command=partial(self.import_txt, True))
        self.reload_button.pack(fill='x', pady=3)
        ttk.Label(right, text='朗讀稿確認', style='Heading.TLabel').pack(anchor='w', pady=(16, 8))
        self.reading_status = ttk.Label(right, text='', wraplength=220, foreground=MUTED)
        self.reading_status.pack(anchor='w')
        self.confirm_button = ttk.Button(right, text='確認朗讀稿', command=self.confirm_reading, style='Primary.TButton')
        self.confirm_button.pack(fill='x', pady=(8, 4))
        self.issues_button = ttk.Button(right, text='檢查／略過來源異常', command=self.review_source_issues)
        self.issues_button.pack(fill='x', pady=3)
        self.versions_button = ttk.Button(right, text='檢視保存版本與副本', command=self.show_versions)
        self.versions_button.pack(fill='x', pady=(3, 16))
        for title, reason, action in (
            ('Gemini 校對', 'T07 將提供金鑰設定與候選差異。\n目前可直接人工編輯校對稿。', '提出校對建議'),
            ('語音與影片', 'T09 起提供語音，T16 起提供影片。\n目前尚無有效音訊。', '產生成品'),
        ):
            ttk.Label(right, text=title, style='Heading.TLabel').pack(anchor='w', pady=(0, 8))
            ttk.Label(right, text=reason, wraplength=220, foreground=MUTED).pack(anchor='w')
            ttk.Button(right, text=action, state='disabled').pack(fill='x', pady=(10, 24))

        bind_canvas_wheel(canvas)

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
                if self.flow and self.batch_id:
                    try:
                        self.flow.invalidate_reading(self.batch_id)
                    except ProjectError as e:
                        self.report(e)
                self.update_stats()
                self.update_source_metadata()

    def update_stats(self):
        text = self.current_text if self.batch_id else ''
        import re
        paragraphs = len([p for p in re.split(r'\r?\n\s*\r?\n', text) if p.strip()])
        batch = next((b for b in self.flow.state['batches'] if b['id'] == self.batch_id), None) if self.flow else None
        revision = batch['revision'] if batch else 0
        self.stats.configure(text=f'{len(text):,} 字元 · {paragraphs:,} 段 · 版本 {revision} · '
                             + ('尚未儲存' if self.dirty else '已儲存' if self.batch_id else '等待匯入'))
        self.save_button.configure(state='normal' if self.dirty else 'disabled')
        enabled = 'normal' if batch else 'disabled'
        for button in (self.find_button, self.replace_button, self.replace_all_button, self.undo_button,
                       self.export_button, self.reload_button, self.versions_button):
            button.configure(state=enabled)
        blockers = self.flow.confirmation_blockers(self.batch_id) if batch and self.flow and self.batch_id else []
        self.confirm_button.configure(state='normal' if batch and text.strip() and not blockers else 'disabled',
                                      text='儲存並確認朗讀稿' if self.dirty else '確認朗讀稿')
        self.issues_button.configure(state='normal' if blockers else 'disabled')
        snapshot = next((s for s in batch.get('readings', []) if s['id'] == batch.get('current_reading')), None) if batch else None
        reading = ('已確認 · 校對稿 v' + str(snapshot['revision']) + '\nSHA-256 ' + snapshot['sha256'][:16]
                   if snapshot and not self.dirty else '尚未確認目前朗讀稿\n修改後須重新確認；舊快照保留。')
        if blockers:
            reading = '來源異常阻擋確認：\n' + '\n'.join(blockers)
        self.reading_status.configure(text=reading if batch else '匯入批次後可確認朗讀稿。')
        self.root.title(('＊' if self.dirty else '') + (self.flow.state['name'] if self.flow else '書籍製作工作台') + ' — ebook2mp4')

    def show_step(self, n):
        self.step = n
        reasons = {
            1: '來源：新增 TXT 或 PDF 範圍批次。PDF 依實際頁次選頁，與印刷頁碼可能不同；OCR 將於 T05 提供。',
            2: '校對：對照來源原文編輯，Ctrl+S 儲存。右側可搜尋取代、匯出／重載及明確確認朗讀稿；工具區可向下捲動。',
            3: '語音尚未提供：T09 將接入語音服務。請先確認朗讀稿；可返回來源或校對繼續編輯。',
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
        self.fill(self.project_location, str(self.flow.root) if self.flow else '建立後顯示保存位置')
        self.folder_button.configure(state='normal' if self.flow else 'disabled')
        self.import_button.configure(state='normal' if self.flow else 'disabled')
        self.pdf_button.configure(state='normal' if self.flow else 'disabled')
        self.cleanup_button.configure(state='normal' if batches else 'disabled')
        selected = next((b for b in batches if b['id'] == self.batch_id), batches[0] if batches else {})
        self.pages_button.configure(state='normal' if selected.get('kind') == 'pdf' else 'disabled')
        self.batch_list.delete(*self.batch_list.get_children())
        for item in batches:
            self.batch_list.insert('', 'end', iid=item['id'], text=f'{item["name"]} · v{item["revision"]}')
        if batches and self.flow:
            batch = next((b for b in batches if b['id'] == self.batch_id), batches[0])
            self.batch_id = batch['id']
            original, draft = self.flow.texts(self.batch_id)
            self.saved_text = draft
            self.batch_list.selection_set(batch['id'])
            self.batch_list.see(batch['id'])
            self.update_source_metadata()
            self.fill(self.source, original)
            self.fill(self.editor, draft, True)
            self.editor.edit_reset()
        else:
            self.batch_id = None
            self.saved_text = ''
            self.source_meta.configure(text='建立專案後新增 TXT 批次；原文與校對稿分開保存。')
            self.fill(self.source, '匯入後在此查看來源原文。')
            self.fill(self.editor, '')
        self.editor.edit_modified(False)
        self.update_batch_actions()
        self._loading = False
        self.update_source_metadata()
        self.update_stats()
        self.show_step(self.step)
        self.status.configure(text='所有書稿資料保存在本機。' if not self.flow else '已載入專案 · 原始來源檔不會被改寫')

    def update_source_metadata(self):
        if not self.flow or not self.batch_id:
            return
        batch = next(b for b in self.flow.state['batches'] if b['id'] == self.batch_id)
        source = batch['source']
        self.source_heading.configure(text='逐頁擷取原稿 · 合併檢視' if batch['kind'] == 'pdf' else '來源原文 · TXT')
        if batch['kind'] == 'pdf':
            pdf = batch['pdf']
            mapping = '精確對應原始頁次' if pdf['mapping_valid'] and not self.dirty else '無精確對應（全文／外部編輯）；逐頁原稿仍可查閱'
            self.source_meta.configure(text=f'{batch["name"]} · 校對稿 v{batch["revision"]}\n{source["original_name"]} · {source["size"]:,} 位元組 · PDF 共 {pdf["page_count"]} 頁\n範圍 {pdf["start"]}–{pdf["end"]}（含兩端）· {mapping}')
            return
        self.source_meta.configure(text=f'{batch["name"]} · 校對稿 v{batch["revision"]}\n{source["original_name"]} · {source["size"]:,} 位元組 · {source["encoding"]} · 可讀\nTXT 來源，無 PDF 頁碼')

    def update_batch_actions(self):
        ids = [b['id'] for b in self.flow.state['batches']] if self.flow else []
        index = ids.index(self.batch_id) if self.batch_id in ids else -1
        self.rename_button.configure(state='normal' if index >= 0 else 'disabled')
        self.up_button.configure(state='normal' if index > 0 else 'disabled')
        self.down_button.configure(state='normal' if 0 <= index < len(ids) - 1 else 'disabled')

    def select_batch(self, _event=None):
        selection = self.batch_list.selection()
        if self._loading or not self.flow or not selection or selection[0] == self.batch_id:
            return
        if not self.may_leave():
            if self.batch_id:
                self.batch_list.selection_set(self.batch_id)
            return
        try:
            self.flow.texts(selection[0])
            self.batch_id = selection[0]
            self.refresh()
        except ProjectError as e:
            if self.batch_id:
                self.batch_list.selection_set(self.batch_id)
            self.report(e)

    def rename_batch(self):
        if not self.flow or not self.batch_id:
            return
        batch = next(b for b in self.flow.state['batches'] if b['id'] == self.batch_id)
        name = simpledialog.askstring('製作批次命名', '批次名稱：', initialvalue=batch['name'], parent=self.root)
        if name is None:
            return
        try:
            self.flow.rename_batch(self.batch_id, name)
            self.batch_list.item(self.batch_id, text=f'{name.strip()} · v{batch["revision"]}')
            self.update_source_metadata()
        except ProjectError as e:
            self.report(e)

    def move_batch(self, direction):
        if not self.flow or not self.batch_id:
            return
        ids = [b['id'] for b in self.flow.state['batches']]
        index = ids.index(self.batch_id)
        target = index + direction
        if not 0 <= target < len(ids):
            return
        ids[index], ids[target] = ids[target], ids[index]
        try:
            self.flow.reorder_batches(ids)
            self.batch_list.move(self.batch_id, '', target)
            self.update_batch_actions()
        except ProjectError as e:
            self.report(e)

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
            self.batch_id = None
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
            self.batch_id = None
            self.step = 2 if flow.state['batches'] else 1
            self.refresh()
        except ProjectError as e:
            self.report(e)

    def import_txt(self, reload=False):
        if not self.flow or (reload and not self.batch_id) or (not reload and not self.may_leave()):
            return
        flow = self.flow
        batch_id = self.batch_id
        path = filedialog.askopenfilename(title='選擇外部校對稿' if reload else '選擇 TXT 新增製作批次', filetypes=[('文字檔', '*.txt')], parent=self.root)
        if not path:
            return
        preview: ImportPreview | None = None
        enough = False
        dialog = tk.Toplevel(self.root)
        dialog.title('重載前預覽' if reload else '匯入前預覽')
        dialog.geometry('760x680')
        dialog.minsize(640, 580)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(2, weight=1)
        options = ttk.Frame(dialog, padding=12)
        options.grid(row=0, column=0, sticky='ew')
        ttk.Label(options, text='來源編碼').pack(side='left', padx=(0, 12))
        encoding = ttk.Combobox(options, state='readonly', width=27,
                                values=('自動（UTF-8／BOM）', 'UTF-8', 'UTF-8 BOM', 'UTF-16 BOM', 'Big5', 'CP950'))
        encoding.set('自動（UTF-8／BOM）')
        encoding.pack(side='left')
        detail_label = ttk.Label(dialog, wraplength=700, padding=(16, 4))
        detail_label.grid(row=1, column=0, sticky='ew')
        dialog.bind('<Configure>', lambda e: detail_label.configure(wraplength=max(200, dialog.winfo_width() - 40)))
        frame, text = text_pane(dialog, '外部校對稿預覽 · 確認後取消目前朗讀確認' if reload else '來源預覽 · 請核對文字，確認後建立新批次')
        frame.grid(row=2, column=0, sticky='nsew')
        warning_accepted = tk.BooleanVar(value=False)
        warning_check = ttk.Checkbutton(dialog, text='已核對異常字元，確認原文確實如此', variable=warning_accepted)
        warning_check.grid(row=3, column=0, sticky='w', padx=16)
        actions = ttk.Frame(dialog, padding=12)
        actions.grid(row=4, column=0, sticky='ew')
        ttk.Button(actions, text='取消', command=dialog.destroy).pack(side='left')

        def commit():
            if not preview or not enough or (preview.warnings and not warning_accepted.get()):
                return
            try:
                if reload:
                    assert batch_id is not None
                    conflict = 'cancel'
                    if self.dirty:
                        answer = messagebox.askyesnocancel(
                            '重載遇到未存校對稿', '是否保留未存編輯的副本？\n是：將副本存入專案後重載。\n否：明確捨棄未存編輯並以外部稿取代。\n取消：保留目前內容，不重載。', parent=dialog)
                        if answer is None:
                            return
                        conflict = 'keep-copy' if answer else 'replace'
                    flow.reload_draft(batch_id, preview, unsaved_text=self.current_text,
                                      conflict=conflict, accept_warnings=warning_accepted.get())
                else:
                    self.batch_id = flow.import_txt(preview, accept_warnings=warning_accepted.get())
                dialog.destroy()
                self.step = 2
                self.refresh()
            except ProjectError as e:
                self.report(e)

        confirm = ttk.Button(actions, text='確認重載' if reload else '確認匯入', command=commit, style='Primary.TButton', state='disabled')
        confirm.pack(side='right')

        def update_confirm(*_args):
            ready = preview is not None and enough and (not preview.warnings or warning_accepted.get())
            confirm.configure(state='normal' if ready else 'disabled')

        def update_preview(_event=None):
            nonlocal preview, enough
            preview, enough = None, False
            warning_accepted.set(False)
            self.fill(text, '')
            try:
                selection = 'auto' if encoding.current() == 0 else encoding.get()
                preview = flow.inspect_txt(path, encoding=selection)
                info = flow.import_requirements(preview)
                if reload and self.dirty:
                    info['required_bytes'] += len(self.current_text.encode('utf-8'))
                enough = info['free_bytes'] >= info['required_bytes'] + 65536
                details = (f'檔名：{preview.path.name}\n大小：{preview.size:,} 位元組 · {preview.encoding} · 可讀\n'
                           f'專案位置：{info["project_location"]}\n' + ('重載只更新校對稿，未存稿可保留副本。\n' if reload else f'來源副本所需空間：{preview.size:,} 位元組\n') +
                           f'本次保存估計：{info["required_bytes"]:,} 位元組 + 65,536 安全餘額\n'
                           f'磁碟可用：{info["free_bytes"]:,} 位元組 · 原始來源檔保持不變。')
                if not enough:
                    details += '\n空間不足，請先釋放空間再重新預覽。'
                if preview.warnings:
                    details += '\n' + '\n'.join(preview.warnings)
                detail_label.configure(text=details, foreground=MUTED)
                warning_check.configure(state='normal' if preview.warnings else 'disabled')
                self.fill(text, preview.text)
            except (ProjectError, OSError) as e:
                preview = None
                detail_label.configure(text=f'檔名：{Path(path).name}\n專案位置：{flow.root}\n無法讀取：{e}\n請切換編碼重新預覽；尚未匯入任何內容。', foreground='#963b32')
                warning_check.configure(state='disabled')
            update_confirm()

        warning_accepted.trace_add('write', update_confirm)
        encoding.bind('<<ComboboxSelected>>', update_preview)
        update_preview()
        dialog.bind('<Escape>', lambda e: dialog.destroy())

    def import_pdf(self):
        if not self.flow or not self.may_leave():
            return
        path = filedialog.askopenfilename(title='選擇 PDF（可在預覽內更換）',
                                          filetypes=[('PDF', '*.pdf')], parent=self.root)
        if path:
            from .pdf_desktop import PdfDialog
            self.pdf_dialog = PdfDialog(self, path=path)

    def compare_pdf_pages(self):
        if self.flow and self.batch_id:
            from .pdf_desktop import PdfDialog
            self.pdf_dialog = PdfDialog(self, batch_id=self.batch_id)

    def cleanup_line_breaks(self):
        if not self.flow or not self.batch_id:
            return
        original = self.current_text
        candidate = self.flow.preview_line_breaks(original)
        dialog = tk.Toplevel(self.root)
        dialog.title('換行整理預覽 · 套用後可復原')
        dialog.geometry('760x600')
        dialog.minsize(600, 450)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(1, weight=1)
        ttk.Label(dialog, text='只將單一斷行換成空格；保留空白行與所有原字元。\n不刪頁首頁尾、不修正跨行連字號。請先核對。', padding=12).grid(row=0, column=0, sticky='w')
        frame, text = text_pane(dialog, '候選預覽 · 尚未變更校對稿')
        frame.grid(row=1, column=0, sticky='nsew')
        self.fill(text, candidate)
        actions = ttk.Frame(dialog, padding=12)
        actions.grid(row=2, column=0, sticky='ew')
        ttk.Button(actions, text='原始換行', command=lambda: self.fill(text, original)).pack(side='left')
        ttk.Button(actions, text='整理預覽', command=lambda: self.fill(text, candidate)).pack(side='left', padx=4)
        ttk.Button(actions, text='取消', command=dialog.destroy).pack(side='left')
        def apply():
            selected = text.get('1.0', 'end-1c')
            if self.current_text != original:
                self.report(ProjectError('編輯內容已變更，請重新預覽。'))
                return
            self.editor.edit_separator()
            self.editor.configure(autoseparators=False)
            self.editor.delete('1.0', 'end')
            self.editor.insert('1.0', selected)
            self.editor.edit_separator()
            self.editor.configure(autoseparators=True)
            dialog.destroy()
        ttk.Button(actions, text='套用整理', command=apply, style='Primary.TButton').pack(side='right')
        dialog.bind('<Escape>', lambda e: dialog.destroy())

    def find_next(self):
        needle = self.find_text.get()
        if not self.batch_id or not needle:
            return False
        start = self.editor.index('insert')
        found = self.editor.search(needle, start, stopindex='end', exact=True)
        if not found:
            found = self.editor.search(needle, '1.0', stopindex='end', exact=True)
        self.editor.tag_remove('sel', '1.0', 'end')
        if not found:
            self.status.configure(text='找不到完全相符的文字。')
            return False
        end = f'{found}+{len(needle)}c'
        self.editor.tag_add('sel', found, end)
        self.editor.mark_set('insert', end)
        self.editor.see(found)
        return True

    def replace_one(self):
        if not self.batch_id or not self.find_text.get():
            return
        selected = self.editor.tag_ranges('sel')
        if not selected or self.editor.get(*selected) != self.find_text.get():
            if not self.find_next():
                return
            selected = self.editor.tag_ranges('sel')
        self.editor.edit_separator()
        self.editor.configure(autoseparators=False)
        self.editor.delete(*selected)
        self.editor.insert(selected[0], self.replace_text.get())
        self.editor.configure(autoseparators=True)
        self.editor.edit_separator()
        self.edited()

    def replace_all(self):
        needle = self.find_text.get()
        if not self.batch_id or not needle:
            return
        text = self.current_text
        count = text.count(needle)
        if count:
            self.editor.edit_separator()
            self.editor.configure(autoseparators=False)
            self.editor.delete('1.0', 'end')
            self.editor.insert('1.0', text.replace(needle, self.replace_text.get()))
            self.editor.configure(autoseparators=True)
            self.editor.edit_separator()
            self.edited()
        self.status.configure(text=f'已取代 {count:,} 處；可按 Ctrl+Z 復原。')

    def undo(self):
        try:
            self.editor.edit_undo()
            self.edited()
        except tk.TclError:
            self.status.configure(text='目前沒有可復原的編輯。')

    def export_txt(self):
        if not self.flow or not self.batch_id:
            return
        path = filedialog.asksaveasfilename(title='匯出目前校對稿（請用新檔名）', defaultextension='.txt',
                                          filetypes=[('UTF-8 文字檔', '*.txt')], parent=self.root)
        if path:
            try:
                self.flow.export_txt(self.batch_id, path, text=self.current_text)
                self.status.configure(text=f'已匯出 UTF-8 TXT：{path}；專案儲存狀態不變。', foreground=GREEN)
            except ProjectError as e:
                self.report(e)

    def confirm_reading(self):
        if not self.flow or not self.batch_id:
            return
        if not messagebox.askyesno('確認朗讀稿', '確認目前完整文字供朗讀使用？\n將先儲存校對稿，再建立不可變快照。後續修改須重新確認。', parent=self.root):
            return
        if not self.save():
            return
        try:
            self.flow.confirm_reading(self.batch_id)
            self.update_stats()
            self.status.configure(text='朗讀稿已確認；快照與完整雜湊可由「檢視保存版本與副本」查閱。', foreground=GREEN)
        except ProjectError as e:
            self.report(e)

    def review_source_issues(self):
        if not self.flow or not self.batch_id:
            return
        batch = next(b for b in self.flow.state['batches'] if b['id'] == self.batch_id)
        for index, issue in enumerate(batch.get('source_issues', [])):
            if issue['status'] == 'pending' and messagebox.askyesno(
                    '明確略過來源異常', f'{issue["reason"]}\n\n已核對來源，仍要略過此異常？', parent=self.root):
                try:
                    self.flow.resolve_source_issue(self.batch_id, index, 'skipped')
                except ProjectError as e:
                    self.report(e)
                    break
        self.update_stats()

    def show_versions(self):
        if not self.flow or not self.batch_id:
            return
        flow, batch_id = self.flow, self.batch_id
        batch = next(b for b in flow.state['batches'] if b['id'] == batch_id)
        versions = [(f'朗讀稿 · 校對 v{s["revision"]} · {s["confirmed_at"]}', s, True)
                    for s in batch.get('readings', [])]
        versions += [(f'未存稿副本 · {s["created_at"]}', s, False) for s in batch.get('draft_copies', [])]
        if not versions:
            messagebox.showinfo('保存版本與副本', '尚無已確認的朗讀稿或重載保留的未存稿副本。', parent=self.root)
            return
        dialog = tk.Toplevel(self.root)
        dialog.title('保存版本與副本 · 唯讀')
        dialog.geometry('760x580')
        dialog.minsize(600, 420)
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(2, weight=1)
        selector = ttk.Combobox(dialog, values=[v[0] for v in versions], state='readonly')
        selector.grid(row=0, column=0, sticky='ew', padx=12, pady=12)
        details = ttk.Label(dialog, wraplength=700, padding=12)
        details.grid(row=1, column=0, sticky='ew')
        dialog.bind('<Configure>', lambda e: details.configure(wraplength=max(200, dialog.winfo_width() - 40)))
        frame, text = text_pane(dialog, '保存文字 · 可選取複製')
        frame.grid(row=2, column=0, sticky='nsew')
        def select(_event=None):
            _, ref, reading = versions[selector.current()]
            try:
                content = (flow.reading_text(batch_id, ref['id']) if reading
                           else flow.draft_copy_text(batch_id, ref['id']))
                self.fill(text, content)
                details.configure(text=f'{ref["path"]}\nSHA-256：{ref["sha256"]}')
            except ProjectError as e:
                self.fill(text, '')
                details.configure(text=str(e))
        selector.bind('<<ComboboxSelected>>', select)
        selector.current(len(versions) - 1)
        select()

    def save(self):
        if not self.batch_id or not self.flow:
            return True
        try:
            self.flow.save_draft(self.batch_id, self.current_text)
            self.saved_text = self.current_text
            self.update_stats()
            batch = next(b for b in self.flow.state['batches'] if b['id'] == self.batch_id)
            self.batch_list.item(self.batch_id, text=f'{batch["name"]} · v{batch["revision"]}')
            self.update_source_metadata()
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
        if self.pdf_dialog is not None and self.pdf_dialog.winfo_exists():
            self.pdf_dialog.close()
            return
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
    style.configure('Treeview', background='#ffffff', fieldbackground='#ffffff', rowheight=25)
    style.map('Treeview', background=[('selected', GREEN)], foreground=[('selected', '#ffffff')])
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
