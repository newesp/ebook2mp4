"""Explicit batch selection within the existing production workspace."""
from tkinter import ttk

from .workflow import ProjectError


class VoiceDefaultsPage(ttk.Frame):
    kind = 'defaults'

    def __init__(self, owner):
        super().__init__(owner.app.production.host, padding=6)
        self.owner, self.flow = owner, owner.flow
        self.production_busy = False
        self.selected: set[str] = set()
        self.value = self.flow.voice_settings()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        ttk.Label(self, text='套用全書預設：選擇批次 → 檢查影響 → 套用',
                  style='Heading.TLabel').grid(row=0, column=0, sticky='w')
        self.summary = ttk.Label(self)
        self.summary.grid(row=1, column=0, sticky='w', pady=6)
        table_frame = ttk.Frame(self)
        table_frame.grid(row=2, column=0, sticky='nsew')
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        self.table = ttk.Treeview(table_frame, columns=('pick', 'batch', 'settings', 'impact'),
                                  show='headings', selectmode='browse', height=6)
        for key, label, width in (('pick', '選取', 48), ('batch', '批次', 110),
                                   ('settings', '目前設定', 210), ('impact', '套用後影響', 210)):
            self.table.heading(key, text=label)
            self.table.column(key, width=width, minwidth=40, stretch=key != 'pick')
        self.table.grid(row=0, column=0, sticky='nsew')
        scrollbar = ttk.Scrollbar(table_frame, command=self.table.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.bind('<ButtonRelease-1>', self.toggle_selected)
        self.table.bind('<space>', self.toggle_selected)
        self.status = ttk.Label(self, text='尚未選取批次。套用只儲存設定，不會傳送文字。', wraplength=650)
        self.status.grid(row=3, column=0, sticky='ew', pady=6)
        footer = ttk.Frame(self)
        footer.grid(row=4, column=0, sticky='ew')
        footer.columnconfigure(1, weight=1)
        self.back_button = ttk.Button(footer, text='← 返回語音設定', command=self.back)
        self.back_button.grid(row=0, column=0)
        self.apply_button = ttk.Button(footer, text='套用至 0 個批次', command=self.apply,
                                       style='Primary.TButton', state='disabled')
        self.apply_button.grid(row=0, column=2)
        self.bind('<Configure>', lambda e: self.status.configure(wraplength=max(180, e.width-24))
                  if e.widget is self else None)
        self.refresh()

    def refresh(self):
        value = self.value
        self.summary.configure(text=f'{value["voice"] or "尚未選音色"} · {value["rate"]} · '
                               f'句尾 {value["sentence_pause_ms"]}／段落 {value["paragraph_pause_ms"]} ms')
        self.table.delete(*self.table.get_children())
        self.selected.intersection_update(batch['id'] for batch in self.flow.state['batches'])
        speech_keys = ('provider', 'profile', 'model', 'voice', 'rate', 'processing')
        for batch in self.flow.state['batches']:
            value = self.flow.voice_settings(batch['id'])
            impact = ('設定相同，不需更新' if value == self.value else
                      '語音需更新；重用符合設定的原音' if any(value.get(k) != self.value.get(k) for k in speech_keys)
                      else '重組音訊／字幕；必要時重新切分')
            self.table.insert('', 'end', iid=batch['id'], values=(
                '☑' if batch['id'] in self.selected else '☐', batch['name'],
                f'{value["voice"] or "未選音色"} · {value["rate"]} · '
                f'{value["sentence_pause_ms"]}/{value["paragraph_pause_ms"]} ms', impact))
        self.set_production_busy(self.production_busy)

    def toggle_selected(self, event=None):
        identities = self.table.selection()
        if event is not None and getattr(event, 'num', None) == 1:
            if self.table.identify_region(event.x, event.y) != 'cell':
                return
            identity = self.table.identify_row(event.y)
            identities = (identity,) if identity else ()
        for identity in identities:
            if identity in self.selected:
                self.selected.remove(identity)
            else:
                self.selected.add(identity)
            self.table.set(identity, 'pick', '☑' if identity in self.selected else '☐')
        count = len(self.selected)
        self.status.configure(text=f'已選 {count} 批。未選批次保持原設定。舊成品保留可播。')
        self.set_production_busy(self.production_busy)
        return 'break'

    def set_production_busy(self, busy):
        was_busy, self.production_busy = self.production_busy, busy
        self.apply_button.configure(text=f'套用至 {len(self.selected)} 個批次',
                                    state='normal' if self.selected and not busy else 'disabled')
        if busy:
            self.status.configure(text='專案正在製作。請等待任務停止後再套用設定。')
        elif was_busy:
            self.status.configure(text=f'已選 {len(self.selected)} 批。請核對影響後套用。')

    def apply(self):
        try:
            if self.owner.app.flow is not self.flow:
                raise ProjectError('書籍已切換，請返回目前書籍重新開啟。')
            if self.flow.voice_settings() != self.value:
                raise ProjectError('全書預設已變更，請返回後重新開啟套用頁。')
            pages = [page for key, page in self.owner.app.production.pages.items()
                     if key[0] == id(self.flow) and key[1] in self.selected and key[2] == 'voice'
                     and page.winfo_exists() and page.scope.get() == '本批次']
            for page in pages:
                if page.current_settings() != self.flow.voice_settings(page.batch_id):
                    raise ProjectError('選取批次有未儲存的語音設定。請先儲存或重讀，再重新開啟套用頁。')
            self.flow.apply_voice_defaults(list(self.selected))
            for page in pages:
                page.load_settings()
            self.refresh()
            self.status.configure(text=f'已套用 {len(self.selected)} 個批次。未開始合成。舊成品保留可播。')
        except (ProjectError, ValueError) as error:
            self.status.configure(text=str(error))

    def back(self):
        self.owner.app.production.activate(self.owner)

    def close(self):
        self.destroy()
        return True
