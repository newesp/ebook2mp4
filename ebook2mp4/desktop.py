"""Traditional Chinese A-layout desktop workbench. No browser or server."""
from pathlib import Path
from functools import partial
from typing import Any
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
        self.focus_mode = False
        self.tools_open = False
        self.pdf_dialog = None
        self.gemini_dialog = None
        self.gemini_settings_dialog = None
        self.voice_dialog = None
        self.narration_dialog = None
        self._closing = False
        self._closing_text = ''
        self.pack(fill='both', expand=True)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self._build()
        from .production_desktop import ProductionWorkspace
        self.production = ProductionWorkspace(self)
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.bind('<Control-s>', lambda e: self.save())
        self.root.bind('<Control-f>', self.focus_search)
        self.root.bind('<F6>', self.toggle_focus)
        self.refresh()

    def _build(self):
        from .ui_controls import CellTooltip, MenuAction, MessageLine, command_menu
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky='ew', pady=(0, 8))
        top.columnconfigure(0, weight=1)
        self.book = ttk.Label(top, text='書籍製作工作台', style='Book.TLabel', width=16)
        self.book.grid(row=0, column=0, sticky='ew')
        project_control, project_menu = command_menu(top, '專案')
        project_control.grid(row=0, column=1, padx=3)
        MenuAction(project_menu, '建立書籍專案', self.create)
        MenuAction(project_menu, '開啟專案', self.open)
        project_menu.add_separator()
        self.folder_button = MenuAction(project_menu, '開啟專案資料夾', self.open_folder)
        MenuAction(project_menu, '專案位置與來源資訊', self.show_source_info)
        file_control, file_menu = command_menu(top, '版本與檔案')
        file_control.grid(row=0, column=2, padx=3)
        self.export_button = MenuAction(file_menu, '匯出目前校對稿 TXT', self.export_txt)
        self.reload_button = MenuAction(file_menu, '重載外部校對稿', partial(self.import_txt, True))
        file_menu.add_separator()
        self.history_action = MenuAction(file_menu, '朗讀稿與重載備份', self.show_versions)
        self.focus_button = ttk.Button(top, text='專注閱讀  F6', command=self.toggle_focus)
        self.focus_button.grid(row=0, column=3, padx=3)
        self.save_button = ttk.Button(top, text='儲存校對稿  Ctrl+S', command=self.save)
        self.save_button.grid(row=0, column=4, padx=(3, 0))

        nav = ttk.Frame(self)
        nav.grid(row=1, column=0, sticky='ew', pady=(0, 8))
        nav.columnconfigure(4, weight=1)
        self.steps = []
        for index, name in enumerate(('1  匯入來源', '2  校對文字', '3  確認朗讀稿', '4  試聽與製作'), 1):
            control = ttk.Button(nav, text=name, command=partial(self.show_step, index), style='Compact.TButton')
            control.grid(row=0, column=index-1, padx=(0, 4))
            self.steps.append(control)

        self.body = body = ttk.Frame(self)
        body.grid(row=2, column=0, sticky='nsew')
        body.rowconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        self.left_panel = left = ttk.Frame(body, padding=(0, 4, 12, 0))
        left.grid(row=0, column=0, sticky='nsew')
        left.columnconfigure(0, weight=1)
        left.rowconfigure(2, weight=1)
        ttk.Label(left, text='書籍與製作批次', style='Heading.TLabel').grid(row=0, column=0, sticky='w')
        self.batch_summary = ttk.Label(left, text='', foreground=MUTED)
        self.batch_summary.grid(row=1, column=0, sticky='w', pady=(6, 10))
        batch_panel = ttk.Frame(left)
        batch_panel.grid(row=2, column=0, sticky='nsew')
        batch_panel.rowconfigure(0, weight=1)
        batch_panel.columnconfigure(0, weight=1)
        self.batch_list = ttk.Treeview(batch_panel, columns=('status',), show='tree', selectmode='browse', height=4)
        self.batch_list.column('#0', width=100, minwidth=60)
        self.batch_list.column('status', width=75, minwidth=75, stretch=False, anchor='w')
        self.batch_list.grid(row=0, column=0, sticky='nsew')
        batch_scroll = ttk.Scrollbar(batch_panel, command=self.batch_list.yview)
        batch_scroll.grid(row=0, column=1, sticky='ns')
        self.batch_list.configure(yscrollcommand=batch_scroll.set)
        self.batch_list.bind('<<TreeviewSelect>>', self.select_batch)
        self.batch_tooltip = CellTooltip(self.batch_list, self.batch_status_help)
        add_control, add_menu = command_menu(left, '新增批次')
        add_control.grid(row=3, column=0, sticky='ew', pady=(10, 5))
        self.import_button = MenuAction(add_menu, '新增 TXT 批次', self.import_txt)
        self.pdf_button = MenuAction(add_menu, '新增 PDF 文件', self.import_pdf)
        manage_control, manage_menu = command_menu(left, '批次管理')
        manage_control.grid(row=4, column=0, sticky='ew')
        self.rename_button = MenuAction(manage_menu, '命名批次', self.rename_batch)
        self.up_button = MenuAction(manage_menu, '上移', partial(self.move_batch, -1))
        self.down_button = MenuAction(manage_menu, '下移', partial(self.move_batch, 1))
        manage_menu.add_separator()
        self.remove_pdf_button = MenuAction(manage_menu, '移除 PDF 批次', self.remove_pdf)

        self.center = center = ttk.Frame(body)
        center.grid(row=0, column=1, sticky='nsew')
        center.rowconfigure(1, weight=1)
        center.columnconfigure(0, weight=1)
        self.metadata = metadata = ttk.Frame(center, padding=(12, 0, 12, 4))
        metadata.grid(row=0, column=0, sticky='ew')
        metadata.columnconfigure(0, weight=1)
        self.source_meta = ttk.Label(metadata, text='', width=1, anchor='w')
        self.source_meta.grid(row=0, column=0, sticky='ew')
        tools_control, tools_menu = command_menu(metadata, '校對工具')
        tools_control.grid(row=0, column=1, padx=4)
        self.pages_button = MenuAction(tools_menu, 'PDF 原頁與文字對照', self.compare_pdf_pages)
        self.cleanup_button = MenuAction(tools_menu, '預覽換行整理', self.cleanup_line_breaks)
        tools_menu.add_separator()
        MenuAction(tools_menu, '來源詳細資訊', self.show_source_info)
        tools_menu.add_separator()
        MenuAction(tools_menu, '搜尋與取代  Ctrl+F', self.focus_search)
        MenuAction(tools_menu, 'AI 校對（選用）', partial(self.open_tools, 1))
        self.ai_tools_button = ttk.Button(metadata, text='AI 校對（選用）', command=partial(self.open_tools, 1))
        self.ai_tools_button.grid(row=0, column=4, padx=(8, 0))
        self.font_size = tk.StringVar(value='12')
        font_control = ttk.Combobox(metadata, textvariable=self.font_size, values=('10', '12', '14', '16', '18'), width=3, state='readonly')
        font_control.grid(row=0, column=2)
        font_control.bind('<<ComboboxSelected>>', self.change_font)
        ttk.Label(metadata, text='pt', foreground=MUTED).grid(row=0, column=3, padx=(3, 0))
        self.panes = panes = ttk.Panedwindow(center, orient='horizontal')
        panes.grid(row=1, column=0, sticky='nsew')
        self.source_frame, self.source = text_pane(panes, '來源原文 · TXT')
        source_frame = self.source_frame
        self.source_heading = source_frame.grid_slaves(row=0)[0]
        self.editor_frame, self.editor = text_pane(panes, '校對稿 · 可編輯', True)
        editor_frame = self.editor_frame
        self.editor_heading = editor_frame.grid_slaves(row=0)[0]
        panes.add(source_frame, weight=1)
        panes.add(editor_frame, weight=1)
        self.editor.configure(exportselection=False)
        self.editor.bind('<<Modified>>', self.edited)

        self.right_panel = right = ttk.Frame(body, padding=(12, 0, 0, 0))
        right.grid(row=0, column=2, sticky='nsew')
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        self.tool_tabs = ttk.Notebook(right, width=225)
        self.tool_tabs.grid(row=0, column=0, sticky='nsew')
        edit, ai = (ttk.Frame(self.tool_tabs, padding=12) for _ in range(2))
        self.confirm_panel = confirm = ttk.Frame(right, padding=12, width=250)
        for frame, title in ((edit, '搜尋取代'), (ai, 'AI 校對（選用）')):
            self.tool_tabs.add(frame, text=title)
        ttk.Label(edit, text='搜尋文字（完全相符）').pack(anchor='w')
        self.find_text = tk.StringVar()
        self.find_entry = ttk.Entry(edit, textvariable=self.find_text, width=18)
        self.find_entry.pack(fill='x', pady=(5, 6))
        self.find_entry.bind('<Return>', lambda e: self.find_next())
        self.find_button = ttk.Button(edit, text='尋找下一個', command=self.find_next)
        self.find_button.pack(fill='x')
        ttk.Separator(edit).pack(fill='x', pady=14)
        ttk.Label(edit, text='取代為').pack(anchor='w')
        self.replace_text = tk.StringVar()
        ttk.Entry(edit, textvariable=self.replace_text, width=18).pack(fill='x', pady=(5, 6))
        replacements = ttk.Frame(edit)
        replacements.pack(fill='x')
        replacements.columnconfigure((0, 1), weight=1, uniform='replace')
        self.replace_button = ttk.Button(replacements, text='取代一處', width=6, command=self.replace_one)
        self.replace_button.grid(row=0, column=0, sticky='ew', padx=(0, 3))
        self.replace_all_button = ttk.Button(replacements, text='全部取代', width=6, command=self.replace_all)
        self.replace_all_button.grid(row=0, column=1, sticky='ew', padx=(3, 0))
        self.undo_button = ttk.Button(edit, text='復原  Ctrl+Z', command=self.undo)
        self.undo_button.pack(fill='x', pady=(12, 0))

        ttk.Label(ai, text='送出範圍').pack(anchor='w')
        self.gemini_scope_choice = tk.StringVar(value='整批文字')
        ttk.Combobox(ai, textvariable=self.gemini_scope_choice, values=('整批文字', '選取文字'), state='readonly', width=18).pack(fill='x', pady=(5, 12))
        ttk.Label(ai, text='繁簡統一').pack(anchor='w')
        self.script = tk.StringVar(value='自動')
        ttk.Combobox(ai, textvariable=self.script, values=('自動', '繁體', '簡體', '保留原樣'), state='readonly', width=18).pack(fill='x', pady=(5, 6))
        self.normalize_punctuation = tk.BooleanVar(value=True)
        ttk.Checkbutton(ai, text='統一中文全形標點', variable=self.normalize_punctuation).pack(anchor='w', pady=3)
        self.gemini_start_button = ttk.Button(ai, text='開始校對', command=lambda: self.gemini_review(self.gemini_scope_choice.get() == '選取文字'), style='Primary.TButton')
        self.gemini_start_button.pack(fill='x', pady=(12, 6))
        self.gemini_history_button = ttk.Button(ai, text='審閱候選差異', command=self.gemini_history)
        self.gemini_history_button.pack(fill='x', pady=3)
        ai_menu_control, ai_menu = command_menu(ai, '範圍操作')
        ai_menu_control.pack(fill='x', pady=3)
        self.gemini_all_button = MenuAction(ai_menu, '校對整批文字', self.gemini_review)
        self.gemini_selected_button = MenuAction(ai_menu, '校對選取文字', partial(self.gemini_review, True))
        ttk.Separator(ai).pack(fill='x', pady=12)
        ttk.Button(ai, text='Gemini 設定', command=self.gemini_settings).pack(fill='x')

        ttk.Label(confirm, text='確認本批朗讀內容', style='Heading.TLabel').pack(anchor='w', pady=(0, 12))
        ttk.Label(confirm, text='1. 閱讀左側完整文字。\n2. 直接修改需要調整的內容。\n3. 確認後前往選聲音與試聽。', wraplength=220, foreground=MUTED).pack(anchor='w', pady=(0, 16))
        self.reading_status = ttk.Label(confirm, text='', wraplength=220, foreground=MUTED)
        self.reading_status.pack(anchor='w', pady=(0, 12))
        self.issues_button = ttk.Button(confirm, text='檢查來源異常', command=self.review_source_issues)
        self.issues_button.pack(fill='x', pady=3)
        self.versions_button = ttk.Button(confirm, text='朗讀稿與重載備份', command=self.show_versions)
        self.versions_button.pack(fill='x', pady=3)
        ttk.Label(confirm, text='確認時會儲存目前編輯。\n確認後再修改，必須重新確認。\n舊朗讀稿與成品仍會保留。', wraplength=220, foreground=MUTED).pack(anchor='w', pady=(20, 0))
        self.close_tools_button = ttk.Button(right, text='收起工具', command=self.close_tools)
        self.close_tools_button.grid(row=1, column=0, sticky='ew', pady=(6, 0))

        self.import_panel = welcome = ttk.Frame(center, padding=32)
        welcome.columnconfigure(0, weight=1)
        ttk.Label(welcome, text='先建立專案，再加入要朗讀的內容', style='Title.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 16))
        ttk.Label(welcome, text='每份 TXT 或一段 PDF 頁碼會成為一個批次。\n加入後，從左側選擇批次，再進行校對。', foreground=MUTED).grid(row=1, column=0, sticky='w', pady=(0, 24))
        project_actions = ttk.Frame(welcome)
        project_actions.grid(row=2, column=0, sticky='w', pady=(0, 20))
        ttk.Button(project_actions, text='建立書籍專案', command=self.create).pack(side='left', padx=(0, 8))
        ttk.Button(project_actions, text='開啟既有專案', command=self.open).pack(side='left')
        import_actions = ttk.Frame(welcome)
        import_actions.grid(row=3, column=0, sticky='w')
        self.import_pdf_cta = ttk.Button(import_actions, text='加入 PDF 文件', command=self.pdf_button.invoke, style='Primary.TButton')
        self.import_pdf_cta.pack(side='left', padx=(0, 8))
        self.import_txt_cta = ttk.Button(import_actions, text='加入 TXT 批次', command=self.import_button.invoke)
        self.import_txt_cta.pack(side='left')

        self.actions = actions = ttk.Frame(center, padding=(12, 8))
        actions.grid(row=2, column=0, sticky='ew')
        actions.columnconfigure(1, weight=1)
        self.back_button = ttk.Button(actions, text='← 返回校對文字', command=partial(self.show_step, 2))
        self.back_button.grid(row=0, column=0, sticky='w')
        self.next_button = ttk.Button(actions, text='儲存並前往確認朗讀稿 →', command=self.save_and_review, style='Primary.TButton')
        self.next_button.grid(row=0, column=2, sticky='e')
        self.confirm_button = ttk.Button(actions, text='確認朗讀稿並前往語音設定 →', command=self.confirm_and_continue, style='Primary.TButton')
        self.confirm_button.grid(row=0, column=2, sticky='e')

        footer = ttk.Frame(self, padding=(8, 8, 0, 0))
        footer.grid(row=3, column=0, sticky='ew')
        footer.columnconfigure(0, weight=1)
        ttk.Separator(footer).grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 6))
        self.stats = ttk.Label(footer, text='', width=1)
        self.stats.grid(row=1, column=0, sticky='ew')
        self.status = MessageLine(footer, text='', foreground=MUTED)
        self.status.grid(row=2, column=0, sticky='ew', pady=(4, 0))
        ttk.Button(footer, text='訊息記錄', command=self.show_messages).grid(row=1, column=1, rowspan=2, padx=(8, 0))
        self.notice = self.status

    def focus_search(self, _event=None):
        self.open_tools(0)
        self.find_entry.focus_set()
        return 'break'

    def open_tools(self, index=0):
        if self.focus_mode:
            self.toggle_focus()
        if self.step != 2:
            self.show_step(2)
        self.tools_open = True
        self.tool_tabs.select(index)
        self.render_step()

    def close_tools(self):
        self.tools_open = False
        self.render_step()

    def toggle_focus(self, _event=None):
        self.focus_mode = not self.focus_mode
        self.render_step()
        self.focus_button.configure(text='返回工作台  F6' if self.focus_mode else '專注閱讀  F6')

    def change_font(self, _event=None):
        for text in (self.source, self.editor):
            text.configure(font=('Microsoft JhengHei', int(self.font_size.get())))

    def show_messages(self):
        dialog = tk.Toplevel(self.root)
        dialog.title('操作訊息記錄')
        dialog.geometry('760x480')
        dialog.minsize(500, 320)
        dialog.rowconfigure(0, weight=1)
        dialog.columnconfigure(0, weight=1)
        frame, text = text_pane(dialog, '最近操作 · 可選取複製')
        frame.grid(row=0, column=0, sticky='nsew')
        self.fill(text, '\n\n'.join(self.status.history) or '尚無操作記錄。')
        ttk.Button(dialog, text='關閉', command=dialog.destroy).grid(row=1, column=0, sticky='e', padx=12, pady=12)
        dialog.bind('<Escape>', lambda e: dialog.destroy())

    def notify(self, text, *, owner=None, kind='success', detail=None):
        from .ui_controls import notify
        owner = self.root if owner is None else owner
        owner = owner.winfo_toplevel()
        full = detail or text
        self.status.remember(full if owner is self.root else f'[{owner.title()}] {full}')
        if len(text) > 80:
            text = text[:60] + '…（詳見訊息記錄）'
        return notify(owner, text, kind)

    def show_source_info(self):
        batch = next((b for b in self.flow.state['batches'] if b['id'] == self.batch_id), None) if self.flow else None
        detail = f'專案位置：{self.flow.root}' if self.flow else '尚未建立書籍專案。'
        if batch:
            source = batch['source']
            detail += f'\n來源：{source["original_name"]}\n大小：{source["size"]:,} 位元組\n'
            detail += self.source_meta.cget('text')
        messagebox.showinfo('專案與來源資訊', detail, parent=self.root)

    def batch_label(self, batch):
        return batch['name']

    def batch_status(self, batch):
        count = sum(issue['status'] == 'pending' for issue in batch.get('source_issues', []))
        return f'待檢查 {count}' if count else '已確認' if batch.get('current_reading') else '未確認'

    def batch_status_help(self, x: int, y: int) -> tuple[str, str] | None:
        tree = self.batch_list
        row = tree.identify_row(y)
        if not row or tree.identify_column(x) != '#1' or tree.identify_region(x, y) != 'cell':
            return None
        status = tree.set(row, 'status')
        if status == '未確認':
            return f'{row}:{status}', '確認朗讀稿'
        if status.startswith('待檢查 '):
            count = status.removeprefix('待檢查 ')
            return f'{row}:{status}', f'有 {count} 項來源／OCR 異常尚未處理'
        return None

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
        self.batch_tooltip.hide()
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
                       self.export_button, self.reload_button, self.versions_button,
                       self.gemini_all_button, self.gemini_selected_button, self.gemini_history_button,
                       self.gemini_start_button, self.history_action):
            button.configure(state=enabled)
        blockers = self.flow.confirmation_blockers(self.batch_id) if batch and self.flow and self.batch_id else []
        self.next_button.configure(state='normal' if batch and text.strip() else 'disabled')
        self.confirm_button.configure(state='normal' if batch and text.strip() and not blockers else 'disabled')
        for button in (self.import_pdf_cta, self.import_txt_cta):
            button.configure(state='normal' if self.flow else 'disabled')
        self.issues_button.configure(state='normal' if blockers else 'disabled')
        snapshot = next((s for s in batch.get('readings', []) if s['id'] == batch.get('current_reading')), None) if batch else None
        reading = ('已確認 · 校對稿 v' + str(snapshot['revision']) + '\nSHA-256 ' + snapshot['sha256'][:16]
                   if snapshot and not self.dirty else '尚未確認目前朗讀稿\n修改後須重新確認；舊朗讀稿保留。')
        if blockers:
            reading = f'來源異常 {len(blockers)} 項，暫不能確認。\n請開啟清單核對並處理。'
        self.reading_status.configure(text=reading if batch else '匯入批次後可確認朗讀稿。')
        self.stats.configure(text=self.stats.cget('text') + (' · 來源異常 ' + str(len(blockers)) if blockers else '') + (' · 朗讀稿已確認' if snapshot and not self.dirty else ' · 朗讀稿未確認'))
        if self.flow:
            for item in self.flow.state['batches']:
                if self.batch_list.exists(item['id']):
                    self.batch_list.item(item['id'], text=self.batch_label(item), values=(self.batch_status(item),))
            confirmed = sum(bool(item.get('current_reading')) for item in self.flow.state['batches'])
            self.batch_summary.configure(text=f'{len(self.flow.state["batches"])} 個批次 · {confirmed} 個已確認')
        else:
            self.batch_summary.configure(text='新增批次後開始校對')
        self.steps[2].configure(text=f'3  確認朗讀稿（{len(blockers)} 項待檢查）' if blockers else '3  確認朗讀稿')
        self.root.title(('＊' if self.dirty else '') + (self.flow.state['name'] if self.flow else '書籍製作工作台') + ' — ebook2mp4')

    def show_step(self, n):
        if n != 4:
            self.production.hide()
        self.step = n
        self.render_step()
        if n == 4:
            self.center.grid_remove()
            self.voice_settings()

    def render_step(self):
        """Change page layout without reloading or replacing the editor buffer."""
        n = self.step
        self.import_panel.grid_remove()
        self.panes.grid_remove()
        self.actions.grid_remove()
        self.metadata.grid_remove()
        self.right_panel.grid_remove()
        self.tool_tabs.grid_remove()
        self.confirm_panel.grid_remove()
        self.close_tools_button.grid_remove()
        self.left_panel.grid_remove() if self.focus_mode else self.left_panel.grid()
        if n == 4:
            self.production.grid(row=0, column=1, rowspan=2, sticky='nsew')
            self.steps[3].configure(style='CompactActive.TButton')
            for button in self.steps[:3]:
                button.configure(style='Compact.TButton')
            self.notice.configure(text='步驟 4：設定語音與試聽，再前往製作與成品。')
            current = self.production.current
            if self.flow and (current is None or not current.winfo_exists() or
                    getattr(current, 'flow', None) is not self.flow or
                    getattr(current, 'kind', None) != 'assembly' and getattr(current, 'batch_id', None) != self.batch_id):
                self.production.show('voice')
            return
        if hasattr(self, 'production'):
            self.production.hide()
        self.center.grid()
        if n == 1:
            self.import_panel.grid(row=1, column=0, sticky='nsew')
        else:
            self.metadata.grid()
            self.panes.grid()
            self.actions.grid()
            has_source = str(self.source_frame) in self.panes.panes()
            if n == 2 and not has_source:
                self.panes.insert(0, self.source_frame, weight=1)
            elif n != 2 and has_source:
                self.panes.forget(self.source_frame)
            self.editor_heading.configure(text='校對稿 · 可編輯' if n == 2 else '待確認朗讀內容 · 可直接編輯')
            self.next_button.grid_remove()
            self.confirm_button.grid_remove()
            self.back_button.grid_remove()
            if n == 2:
                self.next_button.configure(text='儲存並前往確認朗讀稿 →', command=self.save_and_review)
                self.next_button.grid()
                if self.tools_open and not self.focus_mode:
                    self.right_panel.grid()
                    self.tool_tabs.grid()
                    self.close_tools_button.grid()
            else:
                self.back_button.grid()
                if n == 3:
                    self.confirm_button.grid()
                else:
                    self.next_button.configure(text='開啟語音設定與試聽 →', command=self.voice_settings)
                    self.next_button.grid()
                if not self.focus_mode:
                    self.right_panel.grid()
                    self.confirm_panel.grid(row=0, column=0, sticky='nsew')
        reasons = {
            1: '步驟 1：建立或開啟專案，再加入 PDF／TXT。',
            2: '步驟 2：對照來源、編輯校對稿；完成後，儲存並前往確認朗讀稿。',
            3: '步驟 3：檢查完整內容；可直接編輯，確認後再設定聲音。',
            4: '步驟 4：選服務與聲音、編輯試聽；正式製作須使用已確認朗讀稿。',
        }
        self.notice.configure(text=reasons[n])
        for i, button in enumerate(self.steps, 1):
            button.configure(style='CompactActive.TButton' if i == n else 'Compact.TButton')

    def save_and_review(self):
        if self.batch_id and self.save(announce=False):
            self.show_step(3)

    def confirm_and_continue(self):
        if self.confirm_reading():
            self.show_step(4)

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
        self.folder_button.configure(state='normal' if self.flow else 'disabled')
        self.import_button.configure(state='normal' if self.flow else 'disabled')
        self.pdf_button.configure(state='normal' if self.flow else 'disabled')
        self.cleanup_button.configure(state='normal' if batches else 'disabled')
        selected = next((b for b in batches if b['id'] == self.batch_id), batches[0] if batches else {})
        self.pages_button.configure(state='normal' if selected.get('kind') == 'pdf' else 'disabled')
        self.remove_pdf_button.configure(state='normal' if selected.get('kind') == 'pdf' else 'disabled')
        self.batch_list.delete(*self.batch_list.get_children())
        for item in batches:
            self.batch_list.insert('', 'end', iid=item['id'], text=self.batch_label(item), values=(self.batch_status(item),))
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
            self.source_heading.configure(text='來源原文 · TXT')
            self.source_meta.configure(text='建立專案後新增 TXT 批次；原文與校對稿分開保存。')
            self.fill(self.source, '匯入後在此查看來源原文。')
            self.fill(self.editor, '')
        self.editor.edit_modified(False)
        self.update_batch_actions()
        self._loading = False
        self.update_source_metadata()
        self.update_stats()
        if self.step == 1 and batches:
            self.step = 2
        self.render_step()
        self.status.configure(text='所有書稿資料保存在本機。' if not self.flow else '已載入專案 · 原始來源檔不會被改寫')

    def update_source_metadata(self):
        if not self.flow or not self.batch_id:
            return
        batch = next(b for b in self.flow.state['batches'] if b['id'] == self.batch_id)
        source = batch['source']
        self.source_heading.configure(text='本批次擷取原文 · 合併檢視' if batch['kind'] == 'pdf' else '來源原文 · TXT')
        if batch['kind'] == 'pdf':
            pdf = batch['pdf']
            mapping = '精確對應原始頁次' if pdf['mapping_valid'] and not self.dirty else '無精確對應（全文／外部編輯）；擷取原文仍可查閱'
            self.source_meta.configure(text=f'{batch["name"]} · 校對稿 v{batch["revision"]} · PDF {pdf["start"]}–{pdf["end"]} · {mapping}')
            return
        self.source_meta.configure(text=f'{batch["name"]} · 校對稿 v{batch["revision"]} · {source["encoding"]} · 無 PDF 頁碼')

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
            batch = next(b for b in self.flow.state['batches'] if b['id'] == self.batch_id)
            self.batch_list.item(self.batch_id, text=self.batch_label(batch))
            self.update_source_metadata()
            self.notify('批次名稱已儲存。')
        except ProjectError as e:
            self.report(e)

    def remove_pdf(self):
        if not self.flow or not self.batch_id:
            return
        batches = self.flow.state['batches']
        selected = next(b for b in batches if b['id'] == self.batch_id)
        if selected['kind'] != 'pdf':
            return
        pdf = selected['pdf']
        warning = '\n目前未儲存的編輯也會捨棄。' if self.dirty else ''
        if not messagebox.askyesno('移除 PDF 批次',
                f'從專案移除所選批次？\n{selected["name"]}\n'
                f'{selected["source"]["original_name"]} · 第 {pdf["start"]}–{pdf["end"]} 頁\n'
                '此批次的校對稿與朗讀確認將不再列出；專案內歷史檔案保留。\n'
                '外部原始 PDF、其他批次與匯出檔案保留。' + warning,
                parent=self.root, icon='warning', default='no'):
            return
        try:
            index = next(i for i, b in enumerate(batches) if b['id'] == self.batch_id)
            self.flow.remove_pdf_batch(self.batch_id)
            remaining = self.flow.state['batches']
            self.batch_id = remaining[min(index, len(remaining) - 1)]['id'] if remaining else None
            self.refresh()
            self.status.configure(text='已從專案移除所選 PDF 批次；原始 PDF 與其他批次保留。')
            self.notify('已移除 PDF 批次；原始 PDF 保留。')
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
        layer = getattr(self.root, '_notification_layer', None)
        if layer is not None:
            layer.dismiss()
        self.status.configure(text=str(error), foreground='#963b32')
        messagebox.showerror('操作未完成', str(error), parent=self.root)

    def may_leave(self):
        if not self.dirty:
            return True
        answer = messagebox.askyesnocancel('校對稿尚未儲存', '是否先儲存校對稿？\n選「否」會捨棄本次未存的編輯；取消則留在目前專案。', parent=self.root)
        if answer is None:
            return False
        return self.save(announce=False) if answer else True

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
            self.notify('書籍專案已建立。')
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
            self.notify('書籍專案已開啟。')
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
                            '重載遇到未存校對稿', '是否將未存編輯保留為重載備份？\n是：將重載備份存入專案後重載。\n否：明確捨棄未存編輯並以外部稿取代。\n取消：保留目前內容，不重載。', parent=dialog)
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
                self.notify('TXT 已重載。' if reload else 'TXT 已匯入。')
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
                           f'專案位置：{info["project_location"]}\n' + ('重載只更新校對稿，未存編輯可保留為重載備份。\n' if reload else f'來源副本所需空間：{preview.size:,} 位元組\n') +
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
        import difflib
        original = self.current_text
        candidate = self.flow.preview_line_breaks(original)
        dialog = tk.Toplevel(self.root)
        dialog.title('換行整理預覽 · 套用後可復原')
        dialog.geometry('1100x740')
        dialog.minsize(740, 570)
        dialog.grab_set()
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(1, weight=1)
        header = ttk.Frame(dialog, padding=12)
        header.grid(row=0, column=0, sticky='ew')
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text='換行整理 · 原稿與候選比較', style='Heading.TLabel').grid(row=0, column=0, sticky='w')
        mode = tk.StringVar(value='並排對照')
        selector = ttk.Combobox(header, textvariable=mode, values=('並排對照', '只看候選'), width=12, state='readonly')
        selector.grid(row=0, column=1, padx=6)
        ttk.Button(header, text='規則說明', command=lambda: messagebox.showinfo('換行整理規則',
                   '只整理單一斷行；保留空白行與原字元，不刪頁首頁尾、不處理跨行連字號。套用後可一次復原。', parent=dialog)).grid(row=0, column=2)
        panes = ttk.Panedwindow(dialog, orient='horizontal')
        panes.grid(row=1, column=0, sticky='nsew', padx=12)
        original_frame, original_view = text_pane(panes, '原始換行 · 唯讀')
        candidate_frame, candidate_view = text_pane(panes, '整理候選 · 標色為變更')
        panes.add(original_frame, weight=1)
        panes.add(candidate_frame, weight=1)
        self.fill(original_view, original)
        self.fill(candidate_view, candidate)
        original_view.tag_configure('diff', background='#f7dfad', foreground='#332b1b')
        candidate_view.tag_configure('diff', background='#f7dfad', foreground='#332b1b')
        changes = 0
        for operation, a, b, c, d in difflib.SequenceMatcher(None, original, candidate, autojunk=False).get_opcodes():
            if operation != 'equal':
                changes += 1
                original_view.tag_add('diff', f'1.0+{a}c', f'1.0+{b}c')
                candidate_view.tag_add('diff', f'1.0+{c}c', f'1.0+{d}c')
        def change_view(_event=None):
            if mode.get() == '只看候選':
                panes.forget(original_frame)
            elif str(original_frame) not in panes.panes():
                panes.insert(0, original_frame, weight=1)
        selector.bind('<<ComboboxSelected>>', change_view)
        footer = ttk.Frame(dialog, padding=12)
        footer.grid(row=2, column=0, sticky='ew')
        footer.columnconfigure(0, weight=1)
        result = ttk.Label(footer, text=f'{changes} 處變更 · 原稿尚未變更' if changes else '無需整理，原稿與候選相同。', width=1)
        result.grid(row=0, column=0, sticky='ew', padx=(0, 12))
        ttk.Button(footer, text='取消', command=dialog.destroy).grid(row=0, column=1, padx=4)
        def apply():
            if self.current_text != original:
                result.configure(text='編輯內容已變更，請關閉後重新預覽。', foreground='#963b32')
                return
            self.editor.edit_separator()
            self.editor.configure(autoseparators=False)
            self.editor.delete('1.0', 'end')
            self.editor.insert('1.0', candidate)
            self.editor.edit_separator()
            self.editor.configure(autoseparators=True)
            self.edited()
            self.status.configure(text='已套用換行整理；可按 Ctrl+Z 一次復原。')
            dialog.destroy()
            self.notify('已套用換行整理；可按 Ctrl+Z 復原。')
        ttk.Button(footer, text='套用整理', command=apply, style='Primary.TButton', state='normal' if changes else 'disabled').grid(row=0, column=2)
        dialog.bind('<Escape>', lambda e: dialog.destroy())
        dialog.state('zoomed')

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
            self.notify('找不到完全相符的文字。', kind='info')
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
        self.notify(f'已取代 {count:,} 處；可按 Ctrl+Z 復原。', kind='success' if count else 'info')

    def undo(self):
        try:
            self.editor.edit_undo()
            self.edited()
        except tk.TclError:
            self.status.configure(text='目前沒有可復原的編輯。')
            self.notify('目前沒有可復原的編輯。', kind='info')

    def export_txt(self):
        if not self.flow or not self.batch_id:
            return
        path = filedialog.asksaveasfilename(title='匯出目前校對稿（請用新檔名）', defaultextension='.txt',
                                          filetypes=[('UTF-8 文字檔', '*.txt')], parent=self.root)
        if path:
            try:
                self.flow.export_txt(self.batch_id, path, text=self.current_text)
                self.status.configure(text=f'已匯出 UTF-8 TXT：{path}；專案儲存狀態不變。', foreground=GREEN)
                self.notify(f'已匯出 {Path(path).name}。', detail=self.status.full_text)
            except ProjectError as e:
                self.report(e)

    def confirm_reading(self):
        if not self.flow or not self.batch_id:
            return
        if not messagebox.askyesno('確認朗讀稿', '確認目前完整文字供朗讀使用？\n將先儲存校對稿，再建立不可變快照。後續修改須重新確認。', parent=self.root):
            return
        if not self.save(announce=False):
            return
        try:
            self.flow.confirm_reading(self.batch_id)
            self.update_stats()
            self.status.configure(text='朗讀稿已確認；已確認版本與完整雜湊可由「朗讀稿與重載備份」查閱。', foreground=GREEN)
            self.notify('朗讀稿已儲存並確認。', detail=self.status.full_text)
            return True
        except ProjectError as e:
            self.report(e)

    def review_source_issues(self):
        if not self.flow or not self.batch_id:
            return
        flow, batch_id = self.flow, self.batch_id
        dialog = tk.Toplevel(self.root)
        dialog.title('來源異常檢查')
        dialog.geometry('820x500')
        dialog.minsize(600, 400)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(0, weight=1)
        body = ttk.Frame(dialog, padding=12)
        body.grid(row=0, column=0, sticky='nsew')
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        listing = ttk.Treeview(body, columns=('page', 'reason'), show='headings', selectmode='browse')
        listing.heading('page', text='頁次')
        listing.heading('reason', text='待檢查原因')
        listing.column('page', width=65, stretch=False)
        listing.column('reason', width=600)
        listing.grid(row=0, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(body, command=listing.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        listing.configure(yscrollcommand=scroll.set)
        details = tk.Text(body, height=3, wrap='word', relief='flat', bg=BG, fg=INK, font=('Microsoft JhengHei', 10))
        details.grid(row=1, column=0, columnspan=2, sticky='ew', pady=8)
        actions = ttk.Frame(body)
        actions.grid(row=2, column=0, columnspan=2, sticky='ew')
        actions.columnconfigure(0, weight=1)
        def issues():
            batch: dict[str, Any] = next((b for b in flow.state['batches'] if b['id'] == batch_id), {})
            return batch.get('source_issues', [])
        def selected():
            selection = listing.selection()
            return int(selection[0]) if selection else None
        def refresh():
            listing.delete(*listing.get_children())
            for index, issue in enumerate(issues()):
                if issue['status'] == 'pending':
                    listing.insert('', 'end', iid=str(index), values=(issue.get('page', '批次'), issue['reason']))
            rows = listing.get_children()
            if rows:
                listing.selection_set(rows[0])
            self.fill(details, '請核對來源後確認處理，或明確略過；略過不會自動刪除正文。' if rows else '來源異常已處理完成。')
            for control in (resolve, skip, resolve_all, skip_all):
                control.configure(state='normal' if rows else 'disabled')
        def select(_event=None):
            index = selected()
            current = issues()
            if index is not None and index < len(current):
                self.fill(details, current[index]['reason'])
            elif index is not None:
                refresh()
        def decide(disposition):
            index = selected()
            current = issues()
            if index is None or index >= len(current):
                refresh()
                return
            issue = current[index]
            if not messagebox.askyesno('確認來源異常處理', issue['reason'] +
                    ('\n已核對並明確略過此異常？正文不會自動刪除。' if disposition == 'skipped' else '\n已核對來源，確認保留目前內容並標為已處理？'), parent=dialog):
                return
            try:
                flow.resolve_source_issue(batch_id, index, disposition)
                if self.flow is flow and self.batch_id == batch_id:
                    self.update_stats()
                refresh()
                self.notify('來源異常已略過。' if disposition == 'skipped' else '來源異常已標為已處理。', owner=dialog)
            except ProjectError as e:
                self.fill(details, str(e))
        def decide_all(disposition):
            count = sum(issue['status'] == 'pending' for issue in issues())
            if not count:
                refresh()
                return
            question = (f'共有 {count} 項待檢查的來源異常。\n'
                        + ('已核對並明確略過全部異常？正文不會自動刪除。' if disposition == 'skipped'
                           else '已核對來源，確認保留目前內容並將全部異常標為已處理？'))
            if not messagebox.askyesno('確認全部來源異常處理', question, parent=dialog):
                return
            try:
                flow.resolve_all_source_issues(batch_id, disposition)
                if self.flow is flow and self.batch_id == batch_id:
                    self.update_stats()
                refresh()
                self.notify(f'已略過 {count} 項來源異常。' if disposition == 'skipped'
                            else f'已將 {count} 項來源異常標為已處理。', owner=dialog)
            except ProjectError as e:
                self.fill(details, str(e))
        def view_page():
            index = selected()
            current = issues()
            issue = current[index] if index is not None and index < len(current) else {}
            if not issue.get('page'):
                self.fill(details, '這是批次層級異常，請核對來源與完整校對稿。')
                return
            if self.flow is not flow or self.batch_id != batch_id:
                self.fill(details, '目前批次已切換，請回原批次後再開啟頁圖。')
                return
            dialog.destroy()
            self.compare_pdf_pages()
            if self.pdf_dialog is not None:
                self.pdf_dialog.page.set(str(issue['page']))
        listing.bind('<<TreeviewSelect>>', select)
        ttk.Button(actions, text='前往來源頁', command=view_page).grid(row=0, column=0, sticky='w')
        resolve = ttk.Button(actions, text='確認已處理', command=lambda: decide('resolved'))
        resolve.grid(row=0, column=1, padx=4)
        skip = ttk.Button(actions, text='明確略過', command=lambda: decide('skipped'))
        skip.grid(row=0, column=2, padx=4)
        ttk.Button(actions, text='稍後處理／關閉', command=dialog.destroy).grid(row=0, column=3, padx=4)
        resolve_all = ttk.Button(actions, text='全部已處理', command=lambda: decide_all('resolved'))
        resolve_all.grid(row=1, column=1, padx=4, pady=(8, 0))
        skip_all = ttk.Button(actions, text='全部略過', command=lambda: decide_all('skipped'))
        skip_all.grid(row=1, column=2, padx=4, pady=(8, 0))
        dialog.bind('<Escape>', lambda e: dialog.destroy())
        refresh()

    def show_versions(self):
        if not self.flow or not self.batch_id:
            return
        flow, batch_id = self.flow, self.batch_id
        batch = next(b for b in flow.state['batches'] if b['id'] == batch_id)
        versions = [(f'朗讀稿 · 校對 v{s["revision"]} · {s["confirmed_at"]}', s, True)
                    for s in batch.get('readings', [])]
        versions += [(f'重載備份 · {s["created_at"]}', s, False) for s in batch.get('draft_copies', [])]
        if not versions:
            self.notify('尚無已確認的朗讀稿或重載備份。', kind='info')
            return
        dialog = tk.Toplevel(self.root)
        dialog.title('朗讀稿與重載備份')
        dialog.geometry('760x580')
        dialog.minsize(600, 420)
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(2, weight=1)
        selector = ttk.Combobox(dialog, values=[v[0] for v in versions], state='readonly')
        selector.grid(row=0, column=0, sticky='ew', padx=12, pady=12)
        details = ttk.Label(dialog, wraplength=700, padding=12)
        details.grid(row=1, column=0, sticky='ew')
        dialog.bind('<Configure>', lambda e: details.configure(wraplength=max(200, dialog.winfo_width() - 40)))
        frame, text = text_pane(dialog, '已保存文字 · 可選取複製')
        text_heading = frame.grid_slaves(row=0, column=0)[0]
        frame.grid(row=2, column=0, sticky='nsew')
        actions = ttk.Frame(dialog, padding=12)
        actions.grid(row=3, column=0, sticky='ew')
        actions.columnconfigure(0, weight=1)
        delete_button = ttk.Button(actions, text='刪除所選朗讀稿', style='Destructive.TButton')
        delete_button.grid(row=0, column=0, sticky='w')
        ttk.Button(actions, text='關閉', command=dialog.destroy).grid(row=0, column=1, sticky='e')
        def select(_event=None):
            if not versions or selector.current() < 0:
                self.fill(text, '')
                text_heading.configure(text='已保存文字 · 可選取複製')
                details.configure(text='已無朗讀稿或重載備份；目前校對稿與來源文件仍保留。')
                delete_button.configure(state='disabled')
                return
            _, ref, reading = versions[selector.current()]
            text_heading.configure(text='朗讀稿 · 已確認供朗讀的版本' if reading else '重載備份 · 重載前保留的未存校對文字')
            delete_button.configure(state='normal' if reading else 'disabled')
            try:
                content = (flow.reading_text(batch_id, ref['id']) if reading
                           else flow.draft_copy_text(batch_id, ref['id']))
                self.fill(text, content)
                details.configure(text=f'{ref["path"]}\nSHA-256：{ref["sha256"]}')
            except ProjectError as e:
                self.fill(text, '')
                details.configure(text=str(e))
        def delete():
            index = selector.current()
            if index < 0 or not versions or not versions[index][2]:
                return
            label, ref, _reading = versions[index]
            selected_batch = next((b for b in flow.state['batches'] if b['id'] == batch_id), None)
            if selected_batch is None:
                details.configure(text='原批次已移除，請關閉此版本視窗。')
                delete_button.configure(state='disabled')
                return
            current = selected_batch.get('current_reading')
            warning = '\n此版本是目前確認的朗讀稿；刪除後須重新確認朗讀稿。' if current == ref['id'] else ''
            if not messagebox.askyesno('刪除朗讀稿版本',
                    f'刪除以下已確認的朗讀稿歷史版本？\n{label}\n'
                    '此操作無法復原。校對稿、原始來源及其他版本保留。' + warning,
                    parent=dialog, icon='warning', default='no'):
                return
            try:
                cleanup_warning = flow.delete_reading(batch_id, ref['id'])
            except ProjectError as e:
                self.report(e)
                return
            versions.pop(index)
            selector.configure(values=[v[0] for v in versions])
            if versions:
                selector.current(min(index, len(versions) - 1))
            else:
                selector.set('')
            select()
            if cleanup_warning:
                details.configure(text=cleanup_warning)
            if self.flow is flow and self.batch_id == batch_id:
                self.update_stats()
            self.status.configure(text=cleanup_warning or '已刪除所選朗讀稿版本；校對稿與來源保留。')
            self.notify(cleanup_warning or '已刪除朗讀稿版本；校對稿與來源保留。', owner=dialog,
                        kind='warning' if cleanup_warning else 'success')
        delete_button.configure(command=delete)
        selector.bind('<<ComboboxSelected>>', select)
        selector.current(len(versions) - 1)
        select()

    def save(self, *, announce=True):
        if not self.batch_id or not self.flow:
            return True
        try:
            self.flow.save_draft(self.batch_id, self.current_text)
            self.saved_text = self.current_text
            self.update_stats()
            batch = next(b for b in self.flow.state['batches'] if b['id'] == self.batch_id)
            self.batch_list.item(self.batch_id, text=self.batch_label(batch))
            self.update_source_metadata()
            self.status.configure(text='校對稿已儲存 · 可關閉並重新開啟繼續', foreground=GREEN)
            if announce:
                self.notify('校對稿已儲存。', detail=self.status.full_text)
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
        if (not self._closing or self.current_text != self._closing_text) and not self.may_leave():
            self._closing = False
            return
        self._closing = True
        self._closing_text = self.current_text
        shutdown = self.production.shutdown()
        if shutdown == 'cancelled':
            self._closing = False
            return
        if shutdown == 'pending':
            self.root.after(100, self.close)
            return
        for dialog in (self.gemini_dialog, self.gemini_settings_dialog):
            if dialog is not None and dialog.winfo_exists():
                dialog.close()
                self._closing = False
                return
        if self.pdf_dialog is not None and self.pdf_dialog.winfo_exists():
            self.pdf_dialog.close()
            self._closing = False
            return
        self.root.destroy()

    def voice_settings(self):
        if not self.flow:
            self.notice.configure(text='請先建立或開啟書籍專案，再設定語音。')
            return
        self.step = 4
        self.render_step()
        self.production.show('voice')

    def narration(self):
        if not self.flow or not self.batch_id:
            self.notice.configure(text='請先選擇批次，並確認朗讀稿。')
            return
        self.step = 4
        self.render_step()
        self.production.show('narration')

    def total_audio(self):
        if not self.flow:
            self.notice.configure(text='請先建立或開啟書籍專案，再進行全書合併。')
            return
        self.step = 4
        self.render_step()
        self.production.show('assembly')

    def total_video(self):
        if not self.flow:
            return
        self.step = 4
        self.render_step()
        self.production.show('video')

    def gemini_settings(self):
        from .gemini_desktop import SettingsDialog
        if self.gemini_settings_dialog is not None:
            self.gemini_settings_dialog.lift()
            return
        try:
            self.gemini_settings_dialog = SettingsDialog(self)
        except ProjectError as e:
            self.report(e)

    def gemini_review(self, selected=False):
        from .gemini_desktop import ReviewDialog
        if not self.flow or not self.batch_id:
            return
        if self.gemini_dialog is not None:
            self.gemini_dialog.lift()
            return
        start, end = 0, len(self.current_text)
        if selected:
            ranges = self.editor.tag_ranges('sel')
            if not ranges:
                self.report(ProjectError('請先在校對稿選取要送出的文字。'))
                return
            start = len(self.editor.get('1.0', ranges[0]))
            end = len(self.editor.get('1.0', ranges[1]))
        if self.dirty:
            if not messagebox.askyesno('儲存送出版本', '先保存目前編輯，作為本次 Gemini 校對原版本？', parent=self.root) or not self.save(announce=False):
                return
        try:
            from .proofreading import describe
            script = {'自動': 'auto', '繁體': 'traditional', '簡體': 'simplified', '保留原樣': 'preserve'}[self.script.get()]
            punctuation = self.normalize_punctuation.get()
            scope = self.flow.gemini_scope(self.batch_id, start=start, end=end, script=script, punctuation=punctuation)
            if not messagebox.askyesno('送出校對範圍',
                    f'服務：Gemini\n模型：{scope["model"]}\n校對稿 v{scope["revision"]}\n'
                    f'範圍：第 {start+1}～{end} 字元，共 {scope["characters"]:,} 字元\n'
                    + describe(scope['normalization']) + '\n只送上述文字；不傳 PDF 或素材。\n字體／標點統一納入候選，仍須採用才改稿。送出？', parent=self.root):
                return
            job = self.flow.start_gemini_review(self.batch_id, start=start, end=end, script=script, punctuation=punctuation)
            self.gemini_dialog = ReviewDialog(self, job=job)
        except ProjectError as e:
            self.report(e)

    def gemini_history(self):
        from .gemini_desktop import ReviewDialog
        if not self.flow or not self.batch_id:
            return
        if self.gemini_dialog is not None:
            self.gemini_dialog.lift()
            return
        try:
            self.gemini_dialog = ReviewDialog(self)
        except ProjectError as e:
            self.report(e)


def make_app():
    root = tk.Tk()
    from .window_layout import install_dialog_placement
    install_dialog_placement(root)
    root.geometry('1360x820')
    root.minsize(1040, 640)
    root.configure(background=BG)
    root.option_add('*Font', ('Microsoft JhengHei', 10))
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('.', font=('Microsoft JhengHei', 10), background=BG, foreground=INK)
    style.configure('TButton', padding=(10, 7), background='#ffffff', bordercolor='#c7d2c6')
    style.configure('TMenubutton', padding=(10, 7), background='#ffffff')
    style.configure('Compact.TButton', padding=(10, 3))
    style.configure('CompactActive.TButton', padding=(10, 3), background='#315d43', foreground='#ffffff')
    style.configure('TNotebook.Tab', padding=(10, 6))
    style.configure('Treeview', background='#ffffff', fieldbackground='#ffffff', rowheight=25)
    style.map('Treeview', background=[('selected', GREEN)], foreground=[('selected', '#ffffff')])
    style.map('TButton', background=[('active', '#e9f0e5')], foreground=[('disabled', '#68736c')])
    style.map('CompactActive.TButton', background=[('active', '#264d35')], foreground=[('active', '#ffffff')])
    style.configure('Primary.TButton', background=GREEN, foreground='#ffffff')
    style.configure('Destructive.TButton', foreground='#963b32')
    style.map('Primary.TButton', background=[('disabled', '#e1e5de'), ('active', '#264d35')],
              foreground=[('disabled', '#68736c')])
    style.configure('Title.TLabel', font=('Microsoft JhengHei', 19, 'bold'))
    style.configure('Heading.TLabel', font=('Microsoft JhengHei', 11, 'bold'))
    style.configure('Book.TLabel', font=('Microsoft JhengHei', 13, 'bold'))
    def maximize_on_first_map(event):
        if event.widget is root:
            root.unbind('<Map>', startup_binding)
            root.after_idle(lambda: root.state('zoomed') if root.winfo_exists() else None)
    startup_binding = root.bind('<Map>', maximize_on_first_map)
    return root, Workbench(root)


def main():
    root, _app = make_app()
    root.mainloop()
