"""Audio join layout. Source, preview jobs and persistence stay in JoinPage."""
from functools import partial
import tkinter as tk
from tkinter import ttk, font

from .ui_controls import AutoHideScrollbar, CellTooltip
from .workspace_layout import TOOLBAR_GAP
from .workflow import ProjectError


class JoinTextPane(ttk.Frame):
    """One bounded reader with its local action; no outer wheel binding."""
    def __init__(self, parent, title, command):
        super().__init__(parent, style='Tool.TFrame')
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.header = ttk.Frame(self, style='Tool.TFrame')
        self.header.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 2*TOOLBAR_GAP))
        self.header.columnconfigure(0, weight=1)
        self.heading = ttk.Label(self.header, text=title, width=1, style='Tool.TLabel')
        self.heading.grid(row=0, column=0, sticky='ew')
        self.edit = ttk.Button(self.header, command=command, width=1, style='Workspace.TButton')
        self.edit.grid(row=0, column=1, sticky='nsew')
        self.text = tk.Text(self, width=1, height=2, wrap='word', state='disabled',
                            font=('Microsoft JhengHei', 11), relief='solid', borderwidth=1,
                            padx=12, pady=12, highlightthickness=0)
        self.text.grid(row=1, column=0, sticky='nsew')
        self.scroll = AutoHideScrollbar(self, command=self.text.yview)
        self.scroll.grid(row=1, column=1, sticky='ns')
        self.text.configure(yscrollcommand=self.scroll.set)
        self.help = CellTooltip(self.heading, lambda x, y: ('source', getattr(self.heading, 'full_text', self.heading.cget('text'))))
        self.heading.bind('<FocusIn>', lambda e: self.help.motion(type('Focus', (), {'x':0,'y':0})()), add='+')
        self.heading.bind('<FocusOut>', self.help.hide, add='+')


class AudioJoinWorkspace:
    """Own the approved parent grid and retained secondary views."""
    NORMAL_HINT = '停頓套用全書；實際間隔另含來源頭尾靜音，新增停頓期間字幕留白。'

    def __init__(self, page):
        self.page, self.app = p, app = page, page.app
        self.details_open = self.files_open = self.active = False
        self.dedicated = False
        self.warning_data = None
        self._layout_key = None
        self._pause_sync = False
        self._focus_before_files = None
        self._files_reading = self._detail_reading = None
        self.save_error = False
        p.columnconfigure(0, weight=1)
        p.rowconfigure(1, weight=1)
        self.header = ttk.Frame(p)
        self.header.grid(row=0, column=0, sticky='new', pady=(0, 2*TOOLBAR_GAP))
        self.files_button = self.button(self.header, '文件列表', self.show_files)
        self.files_button.configure(width=0)
        self.title = ttk.Label(self.header, text='檢查接點', style='Heading.TLabel')
        self.title.pack(side='left')
        self.hint = ttk.Label(self.header, text='對照前後文字，調整停頓並試聽')
        self.hint.pack(side='left', padx=20)
        self.main = main = ttk.Frame(p, padding=12, style='Tool.TFrame', borderwidth=1, relief='solid')
        main.grid(row=1, column=0, sticky='nsew')
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)
        self.selection = selection = ttk.Frame(main, style='Tool.TFrame')
        selection.grid(row=0, column=0, sticky='ew', pady=(0, 2*TOOLBAR_GAP))
        selection.columnconfigure(1, weight=1)
        ttk.Label(selection, text='接點', style='Tool.TLabel').grid(row=0, column=0, padx=(0, 16))
        p.pair_control = ttk.Combobox(selection, state='readonly', width=1, style='Workspace.TCombobox')
        p.pair_control.grid(row=0, column=1, sticky='nsew', padx=(0, TOOLBAR_GAP))
        p.pair_control.bind('<<ComboboxSelected>>', p.select_pair)
        p.previous = self.button(selection, '上一個', lambda: p.move(-1))
        p.next = self.button(selection, '下一個', lambda: p.move(1))
        p.previous.grid(row=0, column=2, sticky='nsew', padx=(0, TOOLBAR_GAP))
        p.next.grid(row=0, column=3, sticky='nsew')
        self.body = body = ttk.Frame(main, style='Tool.TFrame')
        body.grid(row=1, column=0, sticky='nsew')
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        p.pair = pair = ttk.Frame(body, style='Tool.TFrame')
        pair.grid(row=0, column=0, sticky='nsew')
        pair.columnconfigure((0, 2), weight=1, uniform='readers')
        pair.columnconfigure(1, minsize=12)
        pair.rowconfigure(0, weight=1)
        self.panes = []
        p.headings, p.frame_labels, p.frame_photos = [], [], []
        for i, side in enumerate(('left', 'right')):
            pane = JoinTextPane(pair, '', partial(p.edit, side))
            pane.grid(row=0, column=i*2, sticky='nsew')
            pane.edit.configure(text='校對前批 →' if i == 0 else '校對後批 →')
            self.panes.append(pane)
            p.headings.append(pane.heading)
            setattr(p, side+'_text', pane.text)
            setattr(p, side+'_edit', pane.edit)
        self.build_details()
        self.build_settings()
        self.build_footer()
        self.build_files()
        self.empty = ttk.Label(main, text='尚無接點可檢查\n\n返回全書合併，選取至少兩個有效批次。',
                               style='Tool.TLabel', anchor='nw', padding=16)
        self.pause_display = tk.StringVar(value=p.owner.pause.get()+' 秒')
        p.pause_control.configure(textvariable=self.pause_display)
        self.pause_display.trace_add('write', self.edit_pause)
        self.pause_trace = p.owner.pause.trace_add('write', self.sync_pause)
        p.pause_control.bind('<FocusOut>', self.sync_pause, add='+')
        p.bind('<Configure>', self.resized, add='+')
        body.bind('<Configure>', self.resized, add='+')
        p.bind('<Map>', self.resized, add='+')

    @staticmethod
    def button(parent, text, command):
        return ttk.Button(parent, text=text, command=command, width=1, style='Workspace.TButton')

    def build_details(self):
        p = self.page
        self.detail_frame = frame = ttk.Frame(self.body, style='Tool.TFrame')
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        self.detail_header = header = ttk.Frame(frame, style='Tool.TFrame')
        header.columnconfigure(0, weight=1)
        p.warning_title = ttk.Label(header, width=1, foreground='#704c14', style='Tool.TLabel')
        p.warning_title.grid(row=0, column=0, sticky='ew')
        self.detail_edits = []
        for i, (label, side) in enumerate((('校對前批 →','left'), ('校對後批 →','right'))):
            b = self.button(header, label, partial(p.edit, side))
            b.grid(row=0, column=i+1, sticky='nsew', padx=(TOOLBAR_GAP, 0))
            self.detail_edits.append(b)
        self.detail_text = tk.Text(frame, width=1, height=2, wrap='word', state='disabled',
                                  relief='solid', borderwidth=1, padx=12, pady=12, highlightthickness=0)
        self.detail_text.grid(row=1, column=0, sticky='nsew')
        self.detail_scroll = AutoHideScrollbar(frame, command=self.detail_text.yview)
        self.detail_scroll.grid(row=1, column=1, sticky='ns')
        self.detail_text.configure(yscrollcommand=self.detail_scroll.set)

    def build_settings(self):
        p = self.page
        self.options = options = ttk.Frame(self.main, style='Tool.TFrame')
        options.grid(row=2, column=0, sticky='ew', pady=(2*TOOLBAR_GAP, 0))
        options.columnconfigure((0, 2), weight=1, uniform='readers')
        options.columnconfigure(1, minsize=12)
        self.fields = fields = ttk.Frame(options, style='Tool.TFrame')
        fields.grid(row=0, column=0, sticky='nsew')
        ttk.Label(fields, text='交接停頓', style='Tool.TLabel').grid(row=0, column=0, sticky='w')
        p.pause_control = ttk.Combobox(fields, values=('0 秒','0.5 秒','1 秒','2 秒','5 秒'),
                                      width=1, style='Workspace.TCombobox')
        p.pause_control.grid(row=0, column=1, sticky='nsew')
        fields.columnconfigure(2, minsize=16)
        ttk.Label(fields, text='前後各播', style='Tool.TLabel').grid(row=0, column=3, sticky='w')
        self.clip_display = tk.StringVar(value=p.clip.get()+' 秒')
        p.clip_control = ttk.Combobox(fields, textvariable=self.clip_display, values=('3 秒','5 秒','10 秒'),
                                     state='readonly', width=1, style='Workspace.TCombobox')
        p.clip_control.grid(row=0, column=4, sticky='nsew')
        p.clip_control.bind('<<ComboboxSelected>>', self.edit_clip)
        self.playback = playback = ttk.Frame(options, style='Tool.TFrame')
        playback.grid(row=0, column=2, sticky='nsew')
        p.play_button = self.button(playback, '播放接點', p.play)
        p.play_button.configure(style='Primary.TButton')
        p.play_button.grid(row=0, column=0, sticky='nsew')
        p.stop_button = self.button(playback, '停止試聽', p.stop)
        p.cancel_button = p.stop_button
        p.stop_button.grid(row=0, column=1, sticky='nsew', padx=(TOOLBAR_GAP, 0))
        self.feedback = ttk.Frame(self.main, style='Tool.TFrame')
        self.feedback.grid(row=3, column=0, sticky='ew', pady=(2*TOOLBAR_GAP, 0))
        self.feedback.columnconfigure(1, weight=1)
        p.progress = ttk.Progressbar(self.feedback, mode='indeterminate', length=112)
        p.status = ttk.Label(self.feedback, text=self.NORMAL_HINT, width=1, style='Tool.TLabel')
        p.status.grid(row=0, column=1, sticky='ew')

    def build_footer(self):
        p = self.page
        self.footer = footer = self.app.shell.create_footer(p)
        footer.columnconfigure(0, weight=1)
        p.warning = warning = ttk.Frame(footer)
        warning.columnconfigure(2, weight=1)
        p.ack_control = ttk.Checkbutton(warning, variable=p.accepted, command=p.acknowledge)
        p.ack_control.grid(row=0, column=0, sticky='nsew')
        self.disclosure = ttk.Button(warning, text='警告詳情 ▾', style='Workspace.TButton', width=0, command=self.toggle_details)
        self.disclosure.grid(row=0, column=1, sticky='nsew', padx=(TOOLBAR_GAP, 0))
        self.warning_state = ttk.Label(warning, foreground='#704c14')
        self.warning_state.grid(row=0, column=2, sticky='w', padx=(16, 0))
        self.actions = actions = ttk.Frame(footer)
        actions.grid(row=1, column=0, sticky='ew')
        actions.columnconfigure(1, weight=1)
        p.back_button = footer.button('← 返回全書合併',p.owner.return_from_joins,parent=actions,role='back',width=1)
        p.back_button.grid(row=0, column=0, sticky='nsew')
        self.saved = ttk.Label(actions, width=1)
        self.saved.grid(row=0, column=1, sticky='ew', padx=12)
        p.save_button = footer.button('儲存並返回',p.save,parent=actions,role='primary',width=1)
        p.save_button.grid(row=0, column=2, sticky='nsew')

    def build_files(self):
        self.files = ttk.Frame(self.main, style='Tool.TFrame')
        self.files.columnconfigure(0, weight=1)
        self.files.rowconfigure(0, weight=1)
        self.file_list = ttk.Treeview(self.files, show='tree', selectmode='browse', height=3, style='Manuscript.Treeview')
        self.file_list.grid(row=0, column=0, sticky='nsew')
        self.file_scroll = AutoHideScrollbar(self.files, command=self.file_list.yview)
        self.file_scroll.grid(row=0, column=1, sticky='ns')
        self.file_list.configure(yscrollcommand=self.file_scroll.set)
        self.file_list.bind('<<TreeviewSelect>>', self.select_document)

    def select_document(self, _event=None):
        p = self.page
        selection = self.file_list.selection()
        if not selection or selection[0] == self.app.batch_id or p.info_job is not None or p.job is not None and not p.playing:
            return
        p.stop()
        self.app.batch_list.selection_set(selection[0])
        self.app.select_batch()
        if self.app.batch_id in self.file_list.get_children() and self.file_list.selection() != (self.app.batch_id,):
            self.file_list.selection_set(self.app.batch_id)

    def show_files(self):
        self.page.cancel_reading_restore()
        self._focus_before_files = self.page.focus_get()
        self._files_reading = self.reading_views()
        source = self.app.batch_list
        ids = source.get_children()
        # Synchronize only on entry; a hide/show does not reset this list's view.
        for identity in self.file_list.get_children():
            if identity not in ids:
                self.file_list.delete(identity)
        for i, identity in enumerate(ids):
            text = source.item(identity, 'text')
            if not self.file_list.exists(identity):
                self.file_list.insert('', 'end', iid=identity, text=text)
            else:
                self.file_list.item(identity, text=text)
            self.file_list.move(identity, '', i)
        self.files_open = True
        self.resized()
        self.file_list.focus_set()

    def hide_files(self):
        self.files_open = False
        self.resized()
        self.restore_reading(self._files_reading)
        if self._focus_before_files and self._focus_before_files.winfo_exists():
            self._focus_before_files.focus_set()

    def toggle_details(self):
        self.page.cancel_reading_restore()
        if not self.details_open:
            self._detail_reading = self.reading_views()
        self.details_open = not self.details_open
        self.disclosure.expanded = self.details_open
        self.resized()
        if not self.details_open:
            self.restore_reading(self._detail_reading)

    def reading_views(self):
        return self.page._displayed_key, tuple(text.yview() for text in (self.page.left_text, self.page.right_text))

    def restore_reading(self, views):
        if not views:
            return
        key, positions = views
        if self.page.winfo_exists() and self.active and self.page._displayed_key == key:
            targets = tuple(1. if view[1] == 1 else view[0] for view in positions)
            self.page.restore_reading_position((key, self.page._source_signature, targets))

    def edit_pause(self, *_):
        if self._pause_sync:
            return
        p = self.page
        if p.playing:
            p.stop()
        self._pause_sync = True
        try:
            p.owner.pause.set(self.pause_display.get().removesuffix('秒').strip())
        finally:
            self._pause_sync = False

    def sync_pause(self, *_):
        if self._pause_sync:
            return
        if self.page.playing:
            self.page.stop()
        self._pause_sync = True
        try:
            self.pause_display.set(self.page.owner.pause.get()+' 秒')
        finally:
            self._pause_sync = False

    def edit_clip(self, *_):
        self.page.stop()
        self.page.clip.set(self.clip_display.get().removesuffix('秒').strip())

    def render(self, join):
        self.warning_data = join['warning'] if join else None
        if join and self.warning_data:
            w = self.warning_data
            label = dict(overlap='頁碼重疊', gap='頁碼缺口', reverse='手動倒序')[w['kind']]
            span = str(w['start']) if w['start'] == w['end'] else f'{w["start"]}～{w["end"]}'
            title = f'{label} · 第 {span} 頁'
            self.page.warning_title.configure(text=title)
            a, b = join['left'], join['right']
            detail = (f'來源：{w["source_name"]}\n前批：{a["name"]} · 物理頁 {a["pages"]["start"]}～{a["pages"]["end"]}'
                      f'\n後批：{b["name"]} · 物理頁 {b["pages"]["start"]}～{b["pages"]["end"]}'
                      f'\n{title}。不自動去重、補頁或補半句。\n文字修正請使用校對入口；修改後需重新製作批次音訊。')
            self.page.fill(self.detail_text, detail)
            self.page.ack_control.configure(text=f'我已檢查第 {span} 頁{label.removeprefix("頁碼")}，保留此接點')
        self.resized()

    def set_active(self, active):
        if self.active and not active:
            self.page.cancel_reading_restore()
        self.active = bool(active)
        if active:
            self.resized()

    def update(self, preparing, busy, valid):
        p = self.page
        if self.active:
            self.app.shell.set_document_commands(self.page,not busy)
        p.stop_button.configure(text='取消準備' if preparing else '停止試聽',
                                state='normal' if p.has_work() else 'disabled')
        for b in self.detail_edits:
            b.configure(state='disabled' if preparing or not p.joins else 'normal')
        saved = self.saved_state()
        self.saved.configure(text=saved)
        self.warning_state.configure(text='此接點已確認' if p.accepted.get() else '未確認將阻擋合併')
        p.save_button.configure(text='重試儲存並返回' if self.save_error else '儲存並返回')
        if preparing:
            p.progress.grid(row=0, column=0, padx=(0, 12))
            p.progress.start(15)
        else:
            p.progress.stop()
            p.progress.grid_remove()
        self.resized()

    def saved_state(self):
        """Compare editable settings with the existing persisted contract."""
        p = self.page
        if self.save_error:
            return '儲存失敗 · 輸入已保留'
        try:
            from .assembly import source_ref
            value = p.flow.assembly_settings()
            keys = {j['key'] for j in p.joins}
            saved = (value['sources'] == [source_ref(p.flow, i, verify_media=False) for i in p.owner.selected]
                     and value['pause_ms'] == p.owner.pause_ms()
                     and set(value.get('accepted_joins', [])) & keys == p.owner.accepted_joins & keys)
        except ProjectError:
            saved = False
        return '合併設定已儲存' if saved else '合併設定尚未儲存'

    def resized(self, event=None):
        p = self.page
        if not self.active or not p.winfo_exists() or p.winfo_width() < 10:
            return
        root = p.winfo_toplevel()
        style_font = ttk.Style(p).lookup('Workspace.TButton', 'font')
        detail_content = self.detail_text.get('1.0', 'end-1c')
        key = (p.winfo_width(), p.winfo_height(), root.winfo_width(), str(style_font),
               self.body.winfo_width(), self.body.winfo_height(), tuple(pane.winfo_width() for pane in self.panes),
               self.details_open, self.files_open, bool(p.joins), p.info_job is not None,
               self.app.shell.documents.grid_rowconfigure(0)['minsize'],
               repr(self.warning_data), self.app.focus_mode, p.progress.winfo_manager(), p.status.cget('text'),
               self.saved.cget('text'),
               detail_content, tuple(getattr(h,'full_text','') for h in p.headings))
        if key == self._layout_key:
            return
        self._layout_key = key
        narrow = root.winfo_width() < 1050
        if self.app.focus_mode and not self.files_open:
            self.files_button.pack(side='left', before=self.title, padx=(0, 12))
        else:
            self.files_button.pack_forget()
        if narrow:
            self.hint.pack_forget()
        elif not self.hint.winfo_manager():
            self.hint.pack(side='left', padx=20)
        f = font.Font(font=style_font)
        fs = abs(int(f.cget('size')))
        text_font = ('Microsoft JhengHei', max(10, fs))
        if getattr(self, '_text_font', None) != text_font:
            self._text_font = text_font
            for pane in self.panes:
                pane.text.configure(font=text_font)
            self.detail_text.configure(font=text_font)
            p.reflow_reading()
        value_w = max(120, f.measure('0.123 秒')+42, f.measure('取消準備')+28)
        edit_w = max(128, f.measure('校對前批 →')+28)
        controls = (p.pause_control, p.clip_control, p.play_button, p.stop_button, p.left_edit, p.right_edit, p.previous, p.next)
        height = max(c.winfo_reqheight() for c in controls)
        self.selection.rowconfigure(0, minsize=height)
        for col in (2, 3):
            self.selection.columnconfigure(col, minsize=max(112, f.measure('上一個')+28))
        for col in (0, 3):
            self.fields.columnconfigure(col, minsize=max(80, f.measure('交接停頓')+8))
        for col in (1, 4):
            self.fields.columnconfigure(col, minsize=value_w)
        self.fields.rowconfigure(0, minsize=height)
        for col in (0, 1):
            self.playback.columnconfigure(col, minsize=value_w+(TOOLBAR_GAP if col else 0))
        self.playback.rowconfigure(0, minsize=height)
        for pane in self.panes:
            pane.header.rowconfigure(0, minsize=height)
            pane.header.columnconfigure(1, minsize=edit_w)
            label = getattr(pane.heading, 'full_text', pane.heading.cget('text'))
            available = max(40, pane.winfo_width()-edit_w-8)
            clipped = label
            while clipped and f.measure(clipped) > available:
                clipped = clipped[:-2]+'…' if len(clipped) > 2 else ''
            pane.heading.configure(text=clipped, wraplength=0)
        self.detail_header.rowconfigure(0, minsize=height)
        for col in (1, 2):
            self.detail_header.columnconfigure(col, minsize=edit_w+TOOLBAR_GAP)
        self.actions.columnconfigure(0, minsize=max(168, f.measure('← 返回全書合併')+28))
        self.actions.columnconfigure(2, minsize=max(196, f.measure('重試儲存並返回')+28))
        self.actions.rowconfigure(0, minsize=height)
        self.saved.configure(wraplength=max(60, self.actions.winfo_width()-
            self.actions.grid_columnconfigure(0)['minsize']-self.actions.grid_columnconfigure(2)['minsize']-24))
        self.disclosure.configure(text='收合詳情 ▴' if self.details_open else '警告詳情 ▾')
        self.disclosure.expanded = self.details_open
        p.status.configure(wraplength=max(100, self.main.winfo_width()-28-(124 if p.progress.winfo_manager() else 0)))
        empty = not p.joins and p.info_job is None
        for w in (self.selection, self.body, self.options, self.feedback):
            w.grid_remove() if empty or self.files_open else w.grid()
        self.empty.grid_remove()
        self.files.grid_remove()
        if self.files_open:
            self.files.grid(row=0, column=0, rowspan=4, sticky='nsew')
        elif empty:
            self.empty.grid(row=0, column=0, rowspan=4, sticky='nsew')
        self.title.configure(text='文件列表' if self.files_open else '檢查接點')
        p.back_button.configure(text='← 返回接點文字' if self.files_open else '← 返回全書合併',
                                command=self.hide_files if self.files_open else p.owner.return_from_joins)
        p.save_button.grid_remove() if empty or self.files_open else p.save_button.grid()
        self.saved.grid_remove() if empty else self.saved.grid()
        p.warning.grid_remove()
        if self.warning_data and not self.files_open:
            p.warning.grid(row=0, column=0, sticky='ew', pady=(0, 4))
        elif not empty:
            self.saved.configure(text='返回會恢復原接點、停頓與閱讀位置。' if self.files_open else self.saved_state())
        show_detail = bool(self.warning_data and self.details_open)
        # Estimate natural wrapped height using the same native font, then
        # reserve six complete reader lines before allowing inline disclosure.
        tf = font.Font(font=text_font)
        width = max(40, self.body.winfo_width()-28)
        lines = 0
        glyphs = {}
        for paragraph in detail_content.split('\n'):
            line_width = 0
            lines += 1
            if tf.measure(paragraph) <= width:
                continue
            for char in paragraph:
                if char not in glyphs:
                    glyphs[char] = tf.measure(char)
                cw = glyphs[char]
                if line_width+cw > width:
                    lines += 1
                    line_width = 0
                line_width += cw
        natural = lines*tf.metrics('linespace')+26
        self.dedicated = show_detail and (narrow or self.body.winfo_height()-natural-8 < height+8+6*tf.metrics('linespace')+26)
        self.detail_frame.grid_remove()
        p.pair.grid_remove() if self.dedicated else p.pair.grid(row=0, column=0, sticky='nsew')
        if show_detail:
            self.detail_frame.grid(row=0 if self.dedicated else 1, column=0, sticky='nsew', pady=0 if self.dedicated else (8, 0))
            self.detail_frame.grid_propagate(self.dedicated)
            if not self.dedicated:
                self.detail_frame.configure(height=natural)
            self.detail_header.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 2*TOOLBAR_GAP)) if self.dedicated else self.detail_header.grid_remove()

    def release(self):
        self.set_active(False)

    def destroy(self):
        self.page.owner.pause.trace_remove('write', self.pause_trace)
        self.footer.destroy()
