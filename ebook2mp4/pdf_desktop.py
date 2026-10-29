"""PDF source selection and immutable page comparison, with a responsive Tk shell."""
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any
import tkinter as tk
from tkinter import ttk, filedialog

from .workflow import ProjectError


class _OperationMessage(ttk.Label):
    """Keep long failures in the details view instead of expanding the reading footer."""
    full_text = ''

    def configure(self, cnf=None, **kwargs):
        if 'text' in kwargs:
            self.full_text = str(kwargs['text'])
            kwargs['text'] = self.full_text[:180] + ('…（資訊可查看完整訊息）' if len(self.full_text) > 180 else '')
        return super().configure(cnf, **kwargs)


class PdfDialog(tk.Toplevel):
    def __init__(self, app, *, path=None, batch_id=None):
        super().__init__(app.root)
        self.app, self.flow, self.batch_id = app, app.flow, batch_id
        self.preview = None
        self.ready = False
        self.job = None
        self.pending_job = None
        self.model_job = None
        self.candidate_pages = None
        self.ocr_info_pending = True
        self.accepted_pages: set[int] = set()
        self.model_info_language = None
        self.model_state: dict | None = None
        self.model_install_error = ''
        self.future = None
        self.callback: Callable[[Any], None] | None = None
        self.closing = False
        self.image: Any = None
        self.display_image: Any = None
        self.source_image: Any = None
        self.region: tuple[float, float, float, float] | None = None
        self.region_mode = False
        self.refining = False
        self.resize_token: str | None = None
        self.page_error_text = ''
        self.document_details = ''
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='PDF preview')
        self.title('PDF 原頁與文字對照' if batch_id else '匯入 PDF：選頁與文字預覽')
        width = max(740, min(960, app.root.winfo_width() - 60))
        height = max(570, min(720, app.root.winfo_height() - 60))
        self.geometry(f'{width}x{height}+20+20')
        self.minsize(740, 570)
        self.grab_set()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        header = ttk.Frame(self, padding=(12, 8, 12, 4))
        header.grid(row=0, column=0, sticky='ew')
        header.columnconfigure(0, weight=1)
        self.info = ttk.Label(header, width=1, style='Heading.TLabel')
        self.info.grid(row=0, column=0, sticky='ew')
        self.settings_button = ttk.Button(header, text='範圍／OCR 設定', command=self.toggle_settings)
        self.settings_button.grid(row=0, column=1, padx=4)
        ttk.Button(header, text='資訊', command=self.show_details).grid(row=0, column=2)
        self.settings_window = tk.Toplevel(self)
        self.settings_window.withdraw()
        self.settings_window.title('PDF 範圍與 OCR 設定')
        self.settings_window.geometry('650x450')
        self.settings_window.minsize(600, 430)
        self.settings_window.transient(self)
        self.settings_window.protocol('WM_DELETE_WINDOW', self.hide_settings)
        self.settings_window.bind('<Escape>', lambda e: self.hide_settings())
        self.settings_window.columnconfigure(0, weight=1)
        options = ttk.Frame(self.settings_window, padding=16)
        self.options = options
        options.grid(row=0, column=0, sticky='nsew')
        self.start, self.end, self.page = tk.StringVar(value='1'), tk.StringVar(value='1'), tk.StringVar(value='1')
        self.replace_button = ttk.Button(options, text='更換 PDF', command=self.replace)
        self.replace_button.grid(row=0, column=0, padx=(0, 10))
        for column, (label, variable) in enumerate((('起始', self.start), ('結束（含）', self.end)), 1):
            field = ttk.Frame(options)
            field.grid(row=0, column=column, padx=4)
            ttk.Label(field, text=label).pack(side='left')
            ttk.Entry(field, textvariable=variable, width=6).pack(side='left')
        self.mode = tk.StringVar(value='自動')
        self.language = tk.StringVar(value='自動中英')
        self.layout = tk.StringVar(value='自動版面')
        self.ocr_options = ttk.Frame(options)
        self.ocr_options.grid(row=1, column=0, columnspan=4, sticky='ew', pady=(8, 0))
        self.mode_select = ttk.Combobox(self.ocr_options, textvariable=self.mode,
                                       values=['自動', '文字層', '全部強制 OCR'], state='readonly', width=15)
        ttk.Label(self.ocr_options, text='擷取方式').grid(row=0, column=0, sticky='w')
        self.mode_select.grid(row=1, column=0, sticky='w', pady=4)
        self.language_select = ttk.Combobox(self.ocr_options, textvariable=self.language,
                                           values=['自動中英', '繁中＋英文', '簡中＋英文', '英文'], state='readonly', width=13)
        ttk.Label(self.ocr_options, text='辨識語言').grid(row=0, column=1, sticky='w', padx=8)
        self.language_select.grid(row=1, column=1, padx=8)
        self.install_button = ttk.Button(self.ocr_options, text='下載／安裝模型', command=self.install_models, state='disabled')
        self.install_button.grid(row=4, column=0, columnspan=3, sticky='w', pady=8)
        self.model_info = ttk.Label(self.ocr_options, text='OCR 語言獨立於語音；全部強制 OCR 僅處理所選頁範圍。', wraplength=660)
        self.model_info.configure(wraplength=550)
        self.model_info.grid(row=3, column=0, columnspan=3, sticky='w', pady=8)
        self.layout_select = ttk.Combobox(self.ocr_options, textvariable=self.layout,
                                         values=['自動版面', '單一區塊', '單行標題'], state='readonly', width=15)
        ttk.Label(self.ocr_options, text='辨識版面').grid(row=0, column=2, sticky='w')
        self.layout_select.grid(row=1, column=2, sticky='w', pady=4)
        ttk.Label(self.ocr_options, text='頁次為實際 PDF 頁次，第一頁為 1；起訖皆包含。\n擷取方式只用於範圍擷取；本頁／框選重辨固定使用 OCR。\n語言與版面用於下一次辨識；先前採用的修正保留。\n旋轉用於整頁重辨；局部重辨依目前頁圖方向。', wraplength=550).grid(row=2, column=0, columnspan=3, sticky='w', pady=8)
        ttk.Button(options, text='完成設定', command=self.hide_settings).grid(row=2, column=0, columnspan=3, sticky='e', pady=8)
        self.mode_select.bind('<<ComboboxSelected>>', lambda e: self.ocr_changed())
        self.language_select.bind('<<ComboboxSelected>>', lambda e: self.ocr_changed())
        if batch_id:
            self.replace_button.grid_remove()
        navigation = ttk.Frame(self, padding=(12, 4, 12, 8))
        navigation.grid(row=2, column=0, sticky='ew')
        navigation.columnconfigure(3, weight=1)
        self.previous_button = ttk.Button(navigation, text='上一頁', width=6, command=lambda: self.change_page(-1))
        self.previous_button.grid(row=0, column=0)
        self.page_list = ttk.Combobox(navigation, textvariable=self.page, width=5)
        self.page_list.grid(row=0, column=1, padx=6)
        self.page_list.bind('<Return>', lambda e: self.view())
        self.page_list.bind('<<ComboboxSelected>>', self.select_list_page)
        self.next_button = ttk.Button(navigation, text='下一頁', width=6, command=lambda: self.change_page(1))
        self.next_button.grid(row=0, column=2)
        self.page_total = ttk.Label(navigation, text='實際 PDF 頁次', width=1)
        self.page_total.grid(row=0, column=3, sticky='ew', padx=8)
        self.view_button = ttk.Button(navigation, text='前往', width=4, command=self.view, state='disabled')
        self.view_button.grid(row=0, column=4, padx=4)
        self.rotation = tk.StringVar(value='0')
        rotation_box = ttk.Frame(navigation)
        rotation_box.grid(row=0, column=5, padx=4)
        ttk.Label(rotation_box, text='重辨旋轉').pack(side='left')
        self.rotation_select = ttk.Combobox(rotation_box, textvariable=self.rotation,
                                          values=['0', '90', '180', '270'], width=5, state='readonly')
        self.rotation_select.pack(side='left', padx=4)
        self.retry_menu_button = ttk.Menubutton(navigation, text='重辨 ▾', width=7)
        self.retry_menu_button.grid(row=0, column=6, padx=(4, 0))
        # Keep callable button objects for the public desktop journeys; menus invoke them.
        self.command_store = ttk.Frame(self)
        self.retry_page_button = ttk.Button(self.command_store, text='本頁強制 OCR', command=self.retry_page)
        self.failed_button = ttk.Button(self.command_store, text='只重試失敗頁', command=lambda: self.retry_page(failed_only=True))
        self.retry_menu = tk.Menu(self.retry_menu_button, tearoff=False, postcommand=self.update_retry_menu)
        self.retry_menu.add_command(label='本頁強制 OCR', command=self.retry_page_button.invoke)
        self.retry_menu.add_command(label='框選區域重辨…', command=self.enter_region_mode)
        self.retry_menu.add_command(label='只重試失敗頁', command=self.failed_button.invoke)
        self.retry_menu_button.configure(menu=self.retry_menu)
        self.panes = panes = ttk.Panedwindow(self, orient='horizontal')
        panes.grid(row=3, column=0, sticky='nsew', padx=12)
        image_frame = ttk.Frame(panes)
        image_frame.rowconfigure(1, weight=1)
        image_frame.columnconfigure(0, weight=1)
        image_tools = ttk.Frame(image_frame, padding=(0, 4, 4, 4))
        image_tools.grid(row=0, column=0, columnspan=2, sticky='ew')
        image_tools.columnconfigure(0, weight=1)
        ttk.Label(image_tools, text='來源頁圖').grid(row=0, column=0, sticky='w')
        self.zoom = tk.StringVar(value='適合整頁')
        self.zoom_select = ttk.Combobox(image_tools, textvariable=self.zoom, values=('適合整頁', '適合寬度', '100%', '150%'), width=10, state='readonly')
        self.zoom_select.grid(row=0, column=1)
        self.zoom_select.bind('<<ComboboxSelected>>', lambda e: self.resize_image())
        self.canvas = tk.Canvas(image_frame, width=320, height=300, bg='#e4e8e0', highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(image_frame, command=self.canvas.yview)
        scroll.grid(row=1, column=1, sticky='ns')
        self.canvas.configure(yscrollcommand=scroll.set)
        horizontal = ttk.Scrollbar(image_frame, orient='horizontal', command=self.canvas.xview)
        horizontal.grid(row=2, column=0, sticky='ew')
        self.canvas.configure(xscrollcommand=horizontal.set)
        self.canvas.bind('<ButtonPress-1>', self.begin_region)
        self.canvas.bind('<B1-Motion>', self.drag_region)
        self.canvas.bind('<ButtonRelease-1>', self.end_region)
        self.canvas.bind('<Configure>', self.schedule_resize)
        self.canvas.bind('<MouseWheel>', self.scroll_image)
        self.canvas.bind('<ButtonPress-2>', lambda e: self.canvas.scan_mark(e.x, e.y))
        self.canvas.bind('<B2-Motion>', lambda e: self.canvas.scan_dragto(e.x, e.y, gain=1))
        from .desktop import text_pane
        self.text_tabs = ttk.Notebook(panes)
        text_frame, self.text = text_pane(self.text_tabs, '本頁目前文字 · 辨識修正先在此預覽，尚未存成新批次')
        self.text_tabs.add(text_frame, text='目前頁面文字')
        previous_frame, self.previous_text = text_pane(self.text_tabs, '本批次建立時保存的擷取文字 · 不隨後續修正改變')
        self.text_tabs.add(previous_frame, text='本批次擷取原文')
        draft_frame, self.draft_text = text_pane(self.text_tabs, '本批次人工校對全文 · 可能無精確頁次對應')
        self.text_tabs.add(draft_frame, text='本批次校對稿')
        for frame in (text_frame, previous_frame, draft_frame):
            heading = frame.grid_slaves(row=0, column=0)[0]
            frame.bind('<Configure>', lambda e, label=heading: label.configure(wraplength=max(120, e.width - 30)))
        self.text.configure(exportselection=False)
        if batch_id:
            from .desktop import Workbench
            Workbench.fill(self.draft_text, app.current_text)
        panes.add(image_frame, weight=1)
        panes.add(self.text_tabs, weight=1)
        self.footer = ttk.Frame(self, padding=(12, 6, 12, 8))
        self.footer.grid(row=4, column=0, sticky='ew')
        self.footer.columnconfigure(0, weight=1)
        self.page_info = ttk.Label(self.footer, text='', width=1)
        self.page_info.grid(row=0, column=0, sticky='ew')
        self.page_error = ttk.Label(self.footer, foreground='#963b32', width=1)
        self.page_error.grid(row=1, column=0, sticky='ew')
        self.page_error.grid_remove()
        self.progress = _OperationMessage(self.footer, text='', width=1)
        self.progress.grid(row=2, column=0, sticky='ew', pady=(2, 4))
        self.busy_bar = ttk.Progressbar(self.footer, mode='indeterminate', length=100)
        self.busy_bar.grid(row=3, column=0, sticky='ew', pady=(0, 5))
        self.busy_bar.grid_remove()
        self.busy_active = False
        self.page_choice = ttk.Frame(self.footer)
        self.page_choice.grid(row=4, column=0, sticky='ew', pady=(0, 5))
        self.choice_label = ttk.Label(self.page_choice, text='這頁存入新批次：')
        self.choice_label.pack(side='left', padx=(0, 8))
        self.adopt_page = tk.BooleanVar(value=True)
        self.adopt_check = ttk.Radiobutton(self.page_choice, text='使用辨識修正', value=True,
                                          variable=self.adopt_page, command=self.choose_page)
        self.adopt_check.pack(side='left', padx=4)
        self.original_choice = ttk.Radiobutton(self.page_choice, text='保留擷取原文', value=False,
                                              variable=self.adopt_page, command=self.choose_page)
        self.original_choice.pack(side='left', padx=4)
        self.page_choice.grid_remove()
        self.footer.bind('<Configure>', self.resize_footer)
        self.retry_options = ttk.Frame(self.footer)
        self.retry_options.grid(row=5, column=0, sticky='ew')
        self.retry_options.columnconfigure(3, weight=1)
        self.retain_button = ttk.Button(self.retry_options, text='本頁已核對', command=lambda: self.resolve_page('resolved'))
        self.retain_button.grid(row=0, column=0, padx=(0, 4))
        self.skip_button = ttk.Button(self.retry_options, text='略過本頁警告', command=self.confirm_skip)
        self.skip_button.grid(row=0, column=1, padx=4)
        self.continue_button = ttk.Button(self.retry_options, text='保留選擇，繼續修正', command=self.continue_regions)
        self.continue_button.grid(row=0, column=0, columnspan=2, sticky='w')
        self.continue_button.grid_remove()
        self.region_button = ttk.Button(self.retry_options, text='辨識框選區', command=self.retry_region)
        self.region_button.grid(row=0, column=0, columnspan=2, sticky='w')
        self.region_button.grid_remove()
        self.extract_button = ttk.Button(self.retry_options, text='重新擷取此範圍' if batch_id else '擷取所選頁面', command=self.extract, state='disabled', style='Primary.TButton')
        self.extract_button.grid(row=0, column=4, padx=4)
        self.stop_button = ttk.Button(self.retry_options, text='取消辨識', command=self.cancel_work)
        self.stop_button.grid(row=0, column=4, padx=4)
        self.stop_button.grid_remove()
        self.accept_button = ttk.Button(self.retry_options, text='存成新批次', command=self.accept_candidate, style='Primary.TButton')
        self.accept_button.grid(row=0, column=4, padx=4)
        self.accept_button.grid_remove()
        self.cancel_button = ttk.Button(self.retry_options, text='關閉', command=self.close)
        self.cancel_button.grid(row=0, column=5, padx=(4, 0))
        if not batch_id:
            self.retain_button.grid_remove()
            self.skip_button.grid_remove()
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.bind('<Escape>', lambda e: self.close())
        self.bind('<Destroy>', self.destroyed)
        self.poll_id = self.after(40, self.poll)
        preferences = getattr(app, '_pdf_reading_preferences', {})
        self.zoom.set(preferences.get('zoom', '適合整頁'))
        if preferences.get('geometry'):
            self.geometry(preferences['geometry'])
        self.normal_geometry = self.geometry()
        self.bind('<Configure>', self.remember_geometry)
        if preferences.get('state', 'zoomed') == 'zoomed':
            self.maximize()
        if batch_id:
            batch = next(b for b in self.flow.state['batches'] if b['id'] == batch_id)
            pdf = batch['pdf']
            self.pages: list[dict] = []
            self.start.set(str(pdf['start']))
            self.end.set(str(pdf['end']))
            self.page.set(str(pdf['start']))
            self.info.configure(text=f'{batch["source"]["original_name"]} · 第 {pdf["start"]}–{pdf["end"]} 頁')
            self.document_details = (f'{batch["source"]["original_name"]} · 共 {pdf["page_count"]} 頁\n'
                                     '本批次擷取原文為建立批次時的記錄；目前頁面文字會顯示尚未保存的辨識修正。')
            def loaded_batch(result):
                self.pages, self.preview = result
                self.update_page_list()
                self.view()
            self.submit(lambda: (self.flow.pdf_pages(batch_id), self.flow.pdf_source_preview(batch_id)), loaded_batch)
        else:
            self.load(path)

    def maximize(self):
        try:
            self.state('zoomed')
        except tk.TclError:
            pass

    def remember_geometry(self, event):
        if event.widget is self and self.state() == 'normal':
            self.normal_geometry = self.geometry()

    def destroy(self):
        if self.winfo_exists():
            self.app._pdf_reading_preferences = dict(geometry=self.normal_geometry, state=self.state(), zoom=self.zoom.get())
        super().destroy()

    def resize_footer(self, event):
        width = max(300, event.width - 24)
        for label in (self.page_info, self.page_error, self.progress):
            label.configure(wraplength=width)

    def show_details(self):
        window = tk.Toplevel(self)
        window.title('PDF 資訊與目前訊息')
        window.geometry('660x420')
        window.transient(self)
        from .desktop import text_pane, Workbench
        frame, text = text_pane(window, '文件資訊／頁面異常／作業訊息')
        frame.pack(fill='both', expand=True)
        Workbench.fill(text, self.document_details + '\n\n' + self.page_info.cget('text') +
                       '\n' + self.page_error_text + '\n\n' + self.progress.full_text +
                       '\n\n頁圖：滾輪上下移動，Shift＋滾輪左右移動。\n本頁已核對：確認警告已處理；略過本頁警告：僅解除警告，本頁文字仍保留。\n框選原頁＋反白「目前頁面文字」可只辨識該段；可保留結果後繼續修正其他段。')
        ttk.Button(window, text='關閉', command=window.destroy).pack(anchor='e', padx=12, pady=8)
        window.bind('<Escape>', lambda e: window.destroy())

    def hide_settings(self):
        self.settings_window.withdraw()
        self.grab_set()
        self.settings_button.focus_set()

    def update_retry_menu(self):
        for index, button in ((0, self.retry_page_button), (2, self.failed_button)):
            self.retry_menu.entryconfigure(index, state='disabled' if button.instate(['disabled']) else 'normal')
        self.retry_menu.entryconfigure(1, state='disabled' if self.region_button.instate(['disabled']) else 'normal')

    def candidate_numbers(self):
        return set(getattr(self.pending_job, 'candidate_numbers', self.pending_job.numbers)) if self.pending_job else set()

    def decision_numbers(self):
        if self.pending_job and self.pending_job.region is not None:
            return set(self.pending_job.numbers)
        return self.candidate_numbers()

    def baseline_pages(self):
        baseline = getattr(self.pending_job, 'publication_baseline', None) if self.pending_job else None
        if baseline is not None:
            return baseline
        return getattr(self, 'pages', []) or self.candidate_pages or []

    def visible_pages(self):
        pages = self.candidate_pages if self.candidate_pages is not None else getattr(self, 'pages', [])
        if self.refining and self.pending_job:
            baseline = {p['number']: p for p in (self.pending_job.decision_baseline or self.baseline_pages())}
            return [p if p['number'] in self.accepted_pages else baseline.get(p['number'], p) for p in pages]
        return pages

    def enter_region_mode(self):
        if self.pending_job and not self.refining:
            self.continue_regions()
            return
        if not self.ready or (not self.batch_id and not self.pending_job) or self.job or self.model_job:
            return
        self.region_mode = True
        self.region_button.grid()
        self.text_tabs.select(0)
        self.progress.configure(text='① 框選原頁中的一段　② 反白右側對應文字　③ 辨識框選區。可逐段累積修正。')
        self.canvas.focus_set()
        self.update_actions()

    def continue_regions(self):
        if not self.pending_job or not self.ready or self.job or self.model_job:
            return
        self.refining = True
        self.region_mode = True
        self.region = None
        self.text.tag_remove('sel', '1.0', 'end')
        self.text_tabs.select(0)
        self.view()
        self.progress.configure(text='已套用本次選擇，先前採用的修正保留；請框下一段並反白對應文字，再按「辨識框選區」。')
        self.app.notify('已保留本次選擇，可繼續修正。尚未存成新批次。', owner=self)
        self.update_actions()

    def change_page(self, increment):
        if not self.ready:
            return
        numbers = getattr(self, 'list_numbers', [])
        if not numbers and self.preview:
            numbers = list(range(1, self.preview.page_count + 1))
        try:
            index = numbers.index(int(self.page.get()))
            self.page.set(str(numbers[max(0, min(len(numbers) - 1, index + increment))]))
            self.view()
        except (ValueError, IndexError):
            self.progress.configure(text='請先輸入有效的實際 PDF 頁次。')

    def cancel_work(self):
        if self.job:
            self.job.cancel()
            self.stop_button.configure(state='disabled', text='取消中…')
        elif self.model_job:
            self.model_job.cancel()
            self.stop_button.configure(state='disabled', text='取消下載中…')

    def update_actions(self):
        busy = self.job is not None or self.model_job is not None
        candidate = self.pending_job is not None
        self.ocr_controls(not busy and not self.closing)
        if busy and not self.busy_active:
            self.busy_bar.grid()
            self.busy_bar.start(12)
            self.busy_active = True
        elif not busy and self.busy_active:
            self.busy_bar.stop()
            self.busy_bar.grid_remove()
            self.busy_active = False
        if busy:
            cancelling = self.closing or (self.job is not None and self.job.status == 'cancelling')
            self.stop_button.configure(text='取消下載' if self.model_job else '取消辨識',
                                       state='disabled' if cancelling else 'normal')
            self.stop_button.grid()
            self.extract_button.grid_remove()
            self.cancel_button.configure(state='disabled', text='關閉')
        else:
            self.stop_button.grid_remove()
            self.cancel_button.configure(state='normal', text='捨棄未保存修正並關閉' if candidate else '關閉')
            if candidate:
                self.extract_button.grid_remove()
            else:
                self.extract_button.grid()
        if candidate and getattr(self.pending_job, 'base_pages', None) is not None:
            region_choice = self.pending_job is not None and self.pending_job.region is not None
            self.choice_label.configure(text='本次框選辨識：' if region_choice else '這頁存入新批次：')
            self.adopt_check.configure(text='採用本次結果' if region_choice else '使用辨識修正')
            self.original_choice.configure(text='捨棄本次結果' if region_choice else '保留擷取原文')
            self.page_choice.grid()
        else:
            self.page_choice.grid_remove()
        try:
            current_number = int(self.page.get())
        except ValueError:
            current_number = None
        selectable = candidate and not busy and self.ready and current_number in self.decision_numbers()
        for choice in (self.adopt_check, self.original_choice):
            choice.configure(state='normal' if selectable else 'disabled')
        if hasattr(self, 'accept_button'):
            if candidate and not busy:
                self.accept_button.grid()
                self.accept_button.configure(state='normal' if self.ready else 'disabled')
            else:
                self.accept_button.grid_remove()
        if candidate and not busy and not self.refining:
            self.continue_button.grid()
            self.continue_button.configure(state='normal' if self.ready else 'disabled')
        else:
            self.continue_button.grid_remove()
        if self.region_mode and not busy and (not candidate or self.refining):
            self.region_button.grid()
        else:
            self.region_button.grid_remove()
        if self.batch_id and not candidate and not busy and not self.region_mode:
            self.retain_button.grid()
            self.skip_button.grid()
            batch: dict[str, Any] = next((b for b in self.flow.state['batches'] if b['id'] == self.batch_id), {})
            pending_warning = any(i.get('page') == current_number and i['status'] == 'pending'
                                  for i in batch.get('source_issues', []))
        else:
            self.retain_button.grid_remove()
            self.skip_button.grid_remove()
            pending_warning = False
        enabled = self.ready and not busy
        for control in (self.previous_button, self.next_button, self.view_button):
            control.configure(state='normal' if enabled else 'disabled')
        can_retry = enabled and (self.batch_id is not None or candidate) and (not candidate or self.refining)
        self.retry_controls(can_retry)
        for control in (self.retain_button, self.skip_button):
            control.configure(state='normal' if enabled and pending_warning else 'disabled')
        self.retry_menu_button.configure(state='normal' if can_retry else 'disabled')

    def submit(self, task, callback):
        if self.future is not None:
            return
        self.future = self.executor.submit(task)
        self.callback = callback
        self.ready = False
        self.view_button.configure(state='disabled')
        self.extract_button.configure(state='disabled')
        self.replace_button.configure(state='disabled')
        self.page_list.configure(state='disabled')

    def toggle_settings(self):
        if self.settings_window.winfo_viewable():
            self.hide_settings()
        else:
            self.settings_window.deiconify()
            self.settings_window.lift()
            self.settings_window.grab_set()

    def load(self, path):
        self.preview = None
        self.canvas.delete('all')
        self.image = self.display_image = None
        if self.source_image is not None:
            self.source_image.close()
        self.source_image = None
        self.region = None
        self.page_info.configure(text='')
        self.page_error_text = ''
        self.page_error.grid_remove()
        self.progress.configure(text='')
        from pathlib import Path
        self.info.configure(text=f'{Path(path).name} · 正在檢查 PDF…')
        self.document_details = str(path)
        def loaded(preview):
            self.preview = preview
            self.start.set('1')
            self.end.set(str(preview.page_count))
            self.page.set('1')
            self.info.configure(text=f'{preview.path.name} · 共 {preview.page_count} 頁')
            self.document_details = (f'{preview.path.name} · {preview.size:,} 位元組 · 可讀 · 共 {preview.page_count} 頁\n'
                                     f'專案：{self.flow.root}\n來源副本：{preview.size:,} 位元組；另需逐頁原稿與校對稿空間，保存時檢查。預設整份，兩端包含。')
            self.page_list.configure(values=[str(number) for number in range(1, preview.page_count + 1)])
            self.page_total.configure(text=f'／ {preview.page_count} 頁（實際頁次）')
            self.view()
        self.submit(lambda: self.flow.inspect_pdf(path), loaded)

    def replace(self):
        path = filedialog.askopenfilename(title='更換 PDF', filetypes=[('PDF', '*.pdf')], parent=self)
        if path:
            self.load(path)

    def view(self):
        if self.future is not None or self.job is not None:
            return
        try:
            number = int(self.page.get())
            if self.batch_id or self.candidate_pages is not None:
                selected = next((p for p in self.visible_pages() if p['number'] == number), None)
                if selected is None:
                    raise ProjectError('請輸入此批次範圍內的頁次。')
                from .desktop import Workbench
                Workbench.fill(self.text, selected['text'])
                previous = next((p for p in self.baseline_pages() if p['number'] == number), None)
                Workbench.fill(self.previous_text, previous['text'] if previous else '')
                self.adopt_page.set(number in self.accepted_pages)
                self.adopt_check.configure(state='normal' if self.pending_job and self.pending_job.base_pages is not None
                                           and number in self.decision_numbers() else 'disabled')
                issue: dict = next((i for i in self.flow.state['batches'] if i['id'] == self.batch_id), {})
                disposition = next((i['status'] for i in issue.get('source_issues', []) if i.get('page') == number), '')
                if self.candidate_pages is not None:
                    disposition = ''
                states = dict(success='成功', pending='待檢查', failed='擷取失敗', cancelled='已取消',
                              skipped='已明確略過', resolved='已處理')
                method = ('OCR ' + selected['settings'].get('selected_language', selected['settings'].get('language', ''))
                          if selected['method'] == 'ocr' else '文字層')
                if 'confidence' in selected['settings']:
                    method += f' · 信心指標 {selected["settings"]["confidence"]:.1f}'
                rotation = selected['settings'].get('rotation', 0)
                page_state = states.get(disposition, states[selected['status']])
                self.page_info.configure(text=f'第 {number} 頁 · {method} · {page_state} · {rotation}°')
                self.page_error_text = selected['error']
                if self.page_error_text and disposition not in ('resolved', 'skipped'):
                    self.page_error.configure(text=('原擷取記錄：' if disposition in ('resolved', 'skipped') else '來源異常：') + self.page_error_text[:120] + ('…（資訊可查看完整訊息）' if len(self.page_error_text) > 120 else ''))
                    self.page_error.grid()
                else:
                    self.page_error.grid_remove()
                from .pdf import render
                preview = self.preview
                if preview is None:
                    return
                task = lambda: render(preview.data, number, preview.page_count, rotation=rotation)
            else:
                if self.preview is None:
                    return
                preview = self.preview
                from .pdf import validate_range
                validate_range(number, number, preview.page_count)
                task = lambda: self.flow.preview_pdf_page(preview, number)
                self.page_info.configure(text=f'第 {number} 頁 · 原始頁圖')
            self.canvas.delete('all')
            self.image = self.display_image = None
            if self.source_image is not None:
                self.source_image.close()
            self.source_image = None
            self.region = None
            if hasattr(self, 'region_origin'):
                del self.region_origin
            self.submit(task, self.show_image)
        except (ValueError, ProjectError) as error:
            self.progress.configure(text=str(error) if isinstance(error, ProjectError) else '頁次必須為整數。')

    def show_image(self, data):
        # Resampling only changes the bounded preview, never the OCR input resolution.
        from io import BytesIO
        from PIL import Image
        with Image.open(BytesIO(data)) as source:
            self.source_image = source.convert('RGB')
        self.region = None
        if hasattr(self, 'region_origin'):
            del self.region_origin
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)
        self.resize_image()

    def schedule_resize(self, _event=None):
        if self.resize_token is not None:
            self.after_cancel(self.resize_token)
        self.resize_token = self.after(70, self.resize_image)

    def resize_image(self):
        if self.resize_token is not None:
            self.after_cancel(self.resize_token)
            self.resize_token = None
        source = getattr(self, 'source_image', None)
        if source is None or not self.winfo_exists():
            return
        from PIL import Image, ImageTk
        width, height = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        if width < 10 or height < 10:
            return
        if self.zoom.get() == '適合整頁':
            scale = min(max(1, width - 16) / source.width, max(1, height - 16) / source.height)
        elif self.zoom.get() == '適合寬度':
            scale = max(1, width - 16) / source.width
        else:
            try:
                scale = max(.1, min(3, float(self.zoom.get().rstrip('%')) / 100))
            except ValueError:
                scale = 1
        image_width, image_height = max(1, int(source.width * scale)), max(1, int(source.height * scale))
        with source.resize((image_width, image_height), Image.Resampling.LANCZOS) as resized:
            self.image = self.display_image = ImageTk.PhotoImage(resized, master=self)
        x, y = max(8, (width - image_width) / 2), 8
        self.image_origin = (x, y)
        self.canvas.delete('all')
        self.canvas.create_image(x, y, image=self.image, anchor='nw')
        self.canvas.configure(scrollregion=(0, 0, max(width, image_width + 16), max(height, image_height + 16)))
        self.draw_region()

    def scroll_image(self, event):
        units = -int(event.delta / 120) if abs(event.delta) >= 120 else (-1 if event.delta > 0 else 1)
        if event.state & 1:
            self.canvas.xview_scroll(units, 'units')
        else:
            self.canvas.yview_scroll(units, 'units')
        return 'break'

    def image_point(self, event):
        x, y = self.image_origin
        return (max(0., min(1., (self.canvas.canvasx(event.x) - x) / self.image.width())),
                max(0., min(1., (self.canvas.canvasy(event.y) - y) / self.image.height())))

    def draw_region(self):
        self.canvas.delete('region')
        if self.region is not None and self.image is not None:
            x, y = self.image_origin
            left, top, right, bottom = self.region
            self.canvas.create_rectangle(x + left * self.image.width(), y + top * self.image.height(),
                                         x + right * self.image.width(), y + bottom * self.image.height(),
                                         outline='#315d43', width=2, tags='region')

    def begin_region(self, event):
        if not self.ready or not self.image or (not self.batch_id and not self.pending_job) or (self.pending_job and not self.refining) or self.job:
            return
        self.region_mode = True
        self.region_button.grid()
        self.region_origin = self.image_point(event)
        self.region = None
        self.canvas.delete('region')

    def drag_region(self, event):
        if not hasattr(self, 'region_origin') or not self.ready:
            return
        x, y = self.region_origin
        right, bottom = self.image_point(event)
        self.region = (min(x, right), min(y, bottom), max(x, right), max(y, bottom))
        self.draw_region()

    def end_region(self, event):
        if not hasattr(self, 'region_origin') or not self.ready or self.image is None:
            return
        x, y = self.region_origin
        del self.region_origin
        right, bottom = self.image_point(event)
        x0, x1 = sorted((x, right))
        y0, y1 = sorted((y, bottom))
        if (x1-x0) * self.image.width() < 5 or (y1-y0) * self.image.height() < 5:
            self.region = None
            self.canvas.delete('region')
            self.region_button.configure(text='辨識框選區')
            return
        self.region = (x0, y0, x1, y1)
        self.region_button.configure(text='辨識框選區')
        self.progress.configure(text='已框選原頁；請在「目前頁面文字」反白對應文字，再按「辨識框選區」。')

    def retry_region(self):
        ranges = self.text.tag_ranges('sel')
        if self.region is None or not ranges:
            self.enter_region_mode()
            self.progress.configure(text='請先框選左側原頁中的一段，並在「目前頁面文字」反白對應段落。')
            return
        begin = len(self.text.get('1.0', ranges[0]))
        end = len(self.text.get('1.0', ranges[1]))
        self.retry_page(region=self.region, text_range=(begin, end))

    def extract(self):
        if not self.ready or not self.preview or self.job or self.pending_job or self.model_job:
            return
        try:
            self.job = self.flow.start_pdf_extraction(self.preview, int(self.start.get()), int(self.end.get()),
                                                       mode={'全部強制 OCR': 'ocr', '文字層': 'text-layer', '自動': 'auto'}[self.mode.get()],
                                                       language=self.language.get(), layout=self.layout_code())
            self.ocr_controls(False)
            self.ready = False
            self.extract_button.configure(state='disabled')
            self.view_button.configure(state='disabled')
            self.replace_button.configure(state='disabled')
            self.cancel_button.configure(text='取消擷取並保留完整頁')
            self.retry_controls(False)
            self.progress.configure(text='正在擷取所選頁面…')
            self.hide_settings()
            self.update_actions()
        except (ValueError, ProjectError) as error:
            self.progress.configure(text=str(error) if isinstance(error, ProjectError) else '起始／結束頁必須為整數。')

    def update_page_list(self):
        pages = self.candidate_pages if self.candidate_pages is not None else getattr(self, 'pages', [])
        self.list_numbers = [p['number'] for p in pages]
        batch: dict = next((b for b in self.flow.state['batches'] if b['id'] == self.batch_id), {})
        issues = ({i.get('page'): i['status'] for i in batch.get('source_issues', [])}
                  if self.candidate_pages is None else {})
        self.page_list.configure(values=[str(p['number']) for p in pages])
        count = sum(p['status'] != 'success' and issues.get(p['number']) not in ('resolved', 'skipped') for p in pages)
        self.page_total.configure(text=f'範圍 {self.list_numbers[0]}–{self.list_numbers[-1]} · 待檢查 {count}' if pages else '尚無頁面')

    def select_list_page(self, _event=None):
        if self.ready:
            self.view()

    def retry_controls(self, enabled):
        for widget in (self.retry_page_button, self.failed_button, self.retain_button, self.skip_button, self.region_button):
            widget.configure(state='normal' if enabled and (self.batch_id or self.pending_job) else 'disabled')
        self.rotation_select.configure(state='readonly' if enabled else 'disabled')

    def layout_code(self):
        return {'自動版面': 'auto', '單一區塊': 'block', '單行標題': 'line'}[self.layout.get()]

    def retry_page(self, *, failed_only=False, region=None, text_range=None):
        if not self.ready or (not self.batch_id and not self.pending_job) or self.job or self.model_job:
            return
        if self.pending_job and not self.refining:
            self.progress.configure(text='請先選「保留選擇，繼續修正」，再辨識下一段。')
            return
        try:
            number = int(self.page.get())
            rotation = (next(p for p in self.visible_pages() if p['number'] == number)['settings'].get('rotation', 0)
                        if region else int(self.rotation.get()))
            settings = dict(pages=None if failed_only else [number], language=self.language.get(),
                            rotation=rotation, layout=self.layout_code(), region=region, text_range=text_range)
            if self.pending_job:
                if failed_only:
                    settings['pages'] = [p['number'] for p in self.visible_pages() if p['status'] == 'failed']
                job = self.flow.start_pdf_candidate_retry(self.pending_job, accepted_pages=sorted(self.accepted_pages), **settings)
                self.pending_job = None
            else:
                job = self.flow.start_pdf_retry(self.batch_id, failed_only=failed_only, **settings)
            self.job = job
            self.refining = False
            self.ready = False
            self.retry_controls(False)
            self.ocr_controls(False)
            self.extract_button.configure(state='disabled')
            self.view_button.configure(state='disabled')
            self.cancel_button.configure(text='取消辨識')
            self.progress.configure(text='正在辨識框選區…' if region else '正在重新辨識所選頁面…')
            self.hide_settings()
            self.update_actions()
        except (ProjectError, ValueError) as error:
            self.progress.configure(text=str(error))

    def choose_page(self):
        if not self.pending_job:
            return
        try:
            number = int(self.page.get())
        except ValueError:
            return
        if number in self.decision_numbers():
            if self.adopt_page.get():
                self.accepted_pages.add(number)
            else:
                self.accepted_pages.discard(number)
            if self.refining:
                self.view()
            if self.pending_job.region is not None:
                self.progress.configure(text='將採用本次框選辨識，保留先前採用的修正。' if self.adopt_page.get() else
                                        '將捨棄本次框選辨識；先前採用的修正保留，這一段恢復到本次辨識前。')
            else:
                self.progress.configure(text='此頁將使用辨識修正。尚未存成新批次。' if self.adopt_page.get() else
                                        '此頁將保留本批次擷取原文；不使用目前修正。原始 PDF 不會被刪除。')

    def confirm_skip(self):
        from tkinter import messagebox
        if messagebox.askyesno('略過本頁警告',
                '這只會略過來源警告、解除本頁的朗讀確認阻擋。\n本頁文字仍會保留，不會從書稿刪除。\n已核對來源，仍要略過警告？', parent=self, default='no'):
            self.resolve_page('skipped')

    def resolve_page(self, disposition):
        if not self.ready or not self.batch_id or self.pending_job or self.job:
            return
        try:
            number = int(self.page.get())
            batch = next(b for b in self.flow.state['batches'] if b['id'] == self.batch_id)
            handled = False
            for index, issue in enumerate(batch.get('source_issues', [])):
                if issue.get('page') == number and issue['status'] == 'pending':
                    self.flow.resolve_source_issue(self.batch_id, index, disposition)
                    handled = True
            self.app.update_stats()
            self.update_page_list()
            self.view()
            if handled:
                self.app.notify(f'第 {number} 頁警告已略過。' if disposition == 'skipped' else
                                f'第 {number} 頁已核對。', owner=self)
        except (ValueError, ProjectError) as error:
            self.progress.configure(text=str(error))

    def ocr_controls(self, enabled):
        self.mode_select.configure(state='readonly' if enabled else 'disabled')
        self.language_select.configure(state='readonly' if enabled else 'disabled')
        self.layout_select.configure(state='readonly' if enabled else 'disabled')
        info = self.model_state or {}
        can_install = enabled and self.future is None and bool(info.get('missing')) and not info.get('engine_error')
        self.install_button.configure(state='normal' if can_install else 'disabled')

    def ocr_changed(self):
        self.ocr_info_pending = True
        self.model_state = None
        self.install_button.configure(state='disabled', text='檢查模型中…')
        if self.future is not None or self.job or self.model_job:
            return
        self.ocr_info_pending = False
        language = self.language.get()
        def show(info):
            if language != self.language.get():
                self.ocr_info_pending = True
                return
            self.model_info_language = language
            self.model_state = info
            if not info['missing']:
                self.model_install_error = ''
                summary = f'{info["codes"]} · 模型已就緒，不需下載。'
                if info['engine_error']:
                    summary += '\n' + info['engine_error']
                self.install_button.configure(text='模型已就緒', state='disabled')
            else:
                summary = f'{info["codes"]} · 尚需下載 {info["download_bytes"]:,} 位元組。\n'
                summary += info['engine_error'] or '按「下載缺少的模型」取得所選語言。'
                self.install_button.configure(text='下載缺少的模型', state='disabled' if info['engine_error'] else 'normal')
            self.model_info.configure(text=(self.model_install_error + '\n' if self.model_install_error else '') + summary)
        self.model_info.configure(text=(self.model_install_error + '\n' if self.model_install_error else '') + '正在檢查所選語言的模型與下載大小…')
        self.submit(lambda: self.flow.ocr_models(language), show)

    def install_models(self):
        if self.future is not None or self.job or self.model_job:
            return
        if self.model_info_language != self.language.get() or self.model_state is None:
            self.ocr_changed()
            return
        if not self.model_state['missing']:
            self.install_button.configure(text='模型已就緒', state='disabled')
            self.model_info.configure(text=f'{self.model_state["codes"]} · 模型已就緒，不需下載。')
            return
        if self.model_state['engine_error']:
            self.model_info.configure(text=self.model_state['engine_error'])
            return
        self.model_install_error = ''
        self.model_job = self.flow.start_ocr_model_install(self.language.get())
        self.ocr_controls(False)
        self.extract_button.configure(state='disabled')
        self.replace_button.configure(state='disabled')
        self.progress.configure(text='正在下載缺少的 OCR 模型…')
        self.update_actions()

    def accept_candidate(self):
        if not self.pending_job or self.future is not None:
            return
        try:
            if not self.app.may_leave():
                return
            accepted = sorted(self.accepted_pages) if self.pending_job.base_pages is not None else None
            self.app.batch_id = self.flow.finish_pdf_extraction(self.pending_job, accepted_pages=accepted)
            self.pending_job = None
            self.app.step = 2
            self.app.refresh()
            self.destroy()
            self.app.notify('PDF 修正已儲存為新批次。')
        except ProjectError as error:
            self.progress.configure(text=str(error) + '\n候選保留，可重試採用或關閉捨棄。')

    def poll(self):
        if self.future is not None and self.future.done():
            future, callback = self.future, self.callback
            self.future = None
            try:
                result = future.result()
                if not self.closing and callback is not None:
                    callback(result)
            except Exception as error:
                self.progress.configure(text=str(error) if isinstance(error, ProjectError) else 'PDF 處理失敗，請更換來源。')
            if self.future is None and not self.closing:
                self.ready = self.preview is not None
                self.view_button.configure(state='normal' if self.ready else 'disabled')
                self.page_list.configure(state='normal' if self.ready else 'disabled')
                self.extract_button.configure(state='normal' if self.preview and not self.pending_job and not self.model_job and not self.job else 'disabled')
                self.replace_button.configure(state='disabled' if self.pending_job or self.model_job else 'normal')
                self.retry_controls(self.ready and (not self.pending_job or self.refining) and not self.model_job and not self.job)
        if self.model_job is not None:
            state = self.model_job.state
            text = (f'{state["phase"]} · {state["downloaded"]:,}／{state["total"]:,} 位元組' if state['total'] else '模型已就緒，不需下載。')
            text += ('\n' + state['error']) if state['error'] else ''
            self.model_info.configure(text=text)
            self.progress.configure(text=text)
            if self.model_job.wait(0):
                if not self.closing and state['status'] == 'completed':
                    self.app.notify('OCR 模型已就緒。', owner=self)
                self.model_install_error = state['error'] if state['status'] == 'failed' else ''
                self.model_job = None
                self.ocr_info_pending = True
                self.ocr_controls(True)
                self.cancel_button.configure(text='關閉', state='normal')
                self.extract_button.configure(state='normal' if self.preview else 'disabled')
                self.replace_button.configure(state='normal')
        if self.job is not None:
            status = dict(running='執行中', cancelling='取消中', cancelled='已取消', completed='完成')[self.job.status]
            self.progress.configure(text=f'{status} · 已完成 {len(self.job.pages)}／{len(self.job.numbers)} 頁；取消時保留完整頁，未完成頁標待檢查。')
            if self.job.wait(0):
                if (self.job.mode in ('ocr', 'auto') or self.batch_id) and not self.closing:
                    self.pending_job, self.job = self.job, None
                    # Include cancelled pages with original page numbers in the comparison.
                    self.candidate_pages = self.flow.pdf_extraction_pages(self.pending_job)
                    self.accepted_pages = self.candidate_numbers()
                    self.refining = False
                    self.region_mode = False
                    self.update_page_list()
                    self.hide_settings()
                    self.cancel_button.configure(text='關閉並捨棄候選', state='normal')
                    self.accept_button.grid(row=0, column=4, padx=4)
                    self.page.set(str(self.pending_job.numbers[0]))
                    self.info.configure(text='辨識修正預覽 · 尚未存成新批次')
                    self.document_details += ('\n\n辨識修正存成新的 PDF 批次；本批次人工校對與朗讀稿仍保留。'
                                              '\n局部辨識的「捨棄本次結果」只恢復本次辨識前的文字，先前採用的修正保留。'
                                              '\n整頁重辨選擇保留原文時使用本批次擷取原文；本批次人工校對全文不會自動帶入新批。')
                    self.progress.configure(text='請選擇各頁要使用的文字；可保留選擇後繼續局部修正，最後存成一個新批次。原批不覆寫。')
                    if self.batch_id:
                        self.retry_options.grid()
                    self.view()
                    self.update_actions()
                    self.app.notify('辨識完成，尚未存成新批次。' if self.pending_job.status == 'completed' else
                                    '辨識已停止；請檢查完成頁與未完成頁。', owner=self,
                                    kind='success' if self.pending_job.status == 'completed' else 'warning')
                    self.poll_id = self.after(40, self.poll)
                    return
                try:
                    self.app.batch_id = self.flow.finish_pdf_extraction(self.job)
                    self.job = None
                    self.app.step = 2
                    self.app.refresh()
                    self.destroy()
                    self.app.notify('PDF 已匯入新批次。')
                    return
                except ProjectError as error:
                    self.closing = False
                    self.progress.configure(text=str(error) + '\n可重試保存或關閉以捨棄候選；既有校對稿未改變。')
                    self.cancel_button.configure(state='normal', text='關閉並捨棄未存候選')
                    self.pending_job = self.job
                    self.job = None
                    self.ready = False
                    self.retry_button = ttk.Button(self.retry_options, text='重試保存', command=self.retry, style='Primary.TButton')
                    self.retry_button.grid(row=0, column=4, padx=4)
        if (self.ocr_info_pending and not self.closing and self.future is None
                and self.job is None and self.model_job is None):
            self.ocr_changed()
        if self.closing and self.future is None and self.job is None and self.model_job is None:
            self.destroy()
            return
        self.update_actions()
        self.poll_id = self.after(40, self.poll)

    def retry(self):
        self.job = self.pending_job
        self.pending_job = None
        self.retry_button.destroy()
        self.update_actions()

    def close(self):
        self.closing = True
        if self.job:
            self.job.cancel()
            if self.job.mode in ('ocr', 'auto') or self.batch_id:
                self.closing = False
            self.cancel_button.configure(state='disabled', text='取消中，等待目前頁完成…')
        elif self.model_job:
            self.model_job.cancel()
            self.cancel_button.configure(state='disabled', text='取消下載中…')
        elif self.future is None:
            self.destroy()

    def destroyed(self, event):
        if event.widget is not self:
            return
        self.after_cancel(self.poll_id)
        try:
            self.busy_bar.stop()
        except tk.TclError:
            pass
        if self.resize_token is not None:
            self.after_cancel(self.resize_token)
            self.resize_token = None
        if self.job:
            self.job.cancel()
            self.job.wait()
        if self.model_job:
            self.model_job.cancel()
            self.model_job.wait()
        self.executor.shutdown(wait=True, cancel_futures=True)
        if getattr(self, 'source_image', None) is not None:
            self.source_image.close()
            self.source_image = None
        self.image = self.display_image = None
        candidate = self.job or self.pending_job
        if candidate is not None:
            self.flow.discard_pdf_extraction(candidate)
        self.app.pdf_dialog = None
