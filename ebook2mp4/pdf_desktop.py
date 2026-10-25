"""PDF source selection and immutable page comparison, with a responsive Tk shell."""
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any
import tkinter as tk
from tkinter import ttk, filedialog

from .workflow import ProjectError


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
        self.future = None
        self.callback: Callable[[Any], None] | None = None
        self.closing = False
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='PDF preview')
        self.title('逐頁原稿／頁圖' if batch_id else 'PDF 預覽與選頁')
        width = max(740, min(960, app.root.winfo_width() - 60))
        height = max(570, min(720, app.root.winfo_height() - 60))
        self.geometry(f'{width}x{height}+20+20')
        self.minsize(740, 570)
        self.transient(app.root)
        self.grab_set()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky='ew')
        header.columnconfigure(0, weight=1)
        self.info = ttk.Label(header, padding=12, wraplength=600)
        self.info.grid(row=0, column=0, sticky='ew')
        self.settings_button = ttk.Button(header, text='範圍／OCR 設定', command=self.toggle_settings)
        self.settings_button.grid(row=0, column=1, padx=12)
        self.bind('<Configure>', lambda e: self.info.configure(wraplength=max(200, self.winfo_width() - 210)))
        options = ttk.Frame(self, padding=(12, 0))
        self.options = options
        options.grid(row=1, column=0, sticky='ew')
        self.start, self.end, self.page = tk.StringVar(value='1'), tk.StringVar(value='1'), tk.StringVar(value='1')
        self.replace_button = ttk.Button(options, text='更換 PDF', command=self.replace)
        self.replace_button.grid(row=0, column=0, padx=(0, 10))
        for column, (label, variable) in enumerate((('起始', self.start), ('結束（含）', self.end)), 1):
            field = ttk.Frame(options)
            field.grid(row=0, column=column, padx=4)
            ttk.Label(field, text=label).pack(side='left')
            ttk.Entry(field, textvariable=variable, width=6).pack(side='left')
        self.extract_button = ttk.Button(options, text='擷取為新批次', command=self.extract, state='disabled', style='Primary.TButton')
        self.extract_button.grid(row=0, column=3, padx=8)
        self.mode = tk.StringVar(value='自動')
        self.language = tk.StringVar(value='繁中＋英文')
        self.ocr_options = ttk.Frame(options)
        self.ocr_options.grid(row=1, column=0, columnspan=4, sticky='ew', pady=(8, 0))
        self.mode_select = ttk.Combobox(self.ocr_options, textvariable=self.mode,
                                       values=['自動', '文字層', '全部強制 OCR'], state='readonly', width=15)
        self.mode_select.grid(row=0, column=0, sticky='w')
        self.language_select = ttk.Combobox(self.ocr_options, textvariable=self.language,
                                           values=['繁中＋英文', '簡中＋英文', '英文'], state='readonly', width=13)
        self.language_select.grid(row=0, column=1, padx=8)
        self.install_button = ttk.Button(self.ocr_options, text='下載／安裝模型', command=self.install_models, state='disabled')
        self.install_button.grid(row=0, column=2, sticky='w')
        self.model_info = ttk.Label(self.ocr_options, text='OCR 語言獨立於語音；全部強制 OCR 僅處理所選頁範圍。', wraplength=660)
        self.model_info.grid(row=1, column=0, columnspan=3, sticky='w', pady=4)
        self.mode_select.bind('<<ComboboxSelected>>', lambda e: self.ocr_changed())
        self.language_select.bind('<<ComboboxSelected>>', lambda e: self.ocr_changed())
        if batch_id:
            self.extract_button.configure(text='依範圍建立候選')
            self.replace_button.grid_remove()
            self.options.grid_remove()
        navigation = ttk.Frame(self, padding=12)
        navigation.grid(row=2, column=0, sticky='ew')
        navigation.columnconfigure(2, weight=1)
        ttk.Label(navigation, text='PDF 實際頁次（第一頁為 1；可能與印刷頁碼不同）').grid(row=0, column=0, columnspan=4, sticky='w')
        ttk.Entry(navigation, textvariable=self.page, width=7).grid(row=1, column=0, sticky='w')
        self.view_button = ttk.Button(navigation, text='顯示頁面', command=self.view, state='disabled')
        self.view_button.grid(row=1, column=1, sticky='w', padx=6)
        self.page_info = ttk.Label(navigation, text='', wraplength=430)
        self.page_info.grid(row=1, column=2, sticky='w')
        self.page_list = ttk.Combobox(navigation, state='readonly', width=55)
        self.page_list.grid(row=2, column=0, columnspan=4, sticky='ew', pady=4)
        self.page_list.bind('<<ComboboxSelected>>', self.select_list_page)
        self.rotation = tk.StringVar(value='0')
        self.retry_options = ttk.Frame(navigation)
        self.retry_options.grid(row=3, column=0, columnspan=4, sticky='w')
        ttk.Label(self.retry_options, text='順時針旋轉').grid(row=0, column=0)
        self.rotation_select = ttk.Combobox(self.retry_options, textvariable=self.rotation,
                                          values=['0', '90', '180', '270'], width=5, state='readonly')
        self.rotation_select.grid(row=0, column=1, padx=4)
        self.retry_page_button = ttk.Button(self.retry_options, text='本頁強制 OCR', command=self.retry_page)
        self.retry_page_button.grid(row=0, column=2, padx=4)
        self.failed_button = ttk.Button(self.retry_options, text='只重試失敗頁', command=lambda: self.retry_page(failed_only=True))
        self.failed_button.grid(row=0, column=3, padx=4)
        self.retain_button = ttk.Button(self.retry_options, text='確認保留本頁', command=lambda: self.resolve_page('resolved'))
        self.retain_button.grid(row=1, column=0, columnspan=2, pady=4)
        self.skip_button = ttk.Button(self.retry_options, text='明確略過本頁', command=lambda: self.resolve_page('skipped'))
        self.skip_button.grid(row=1, column=2, pady=4)
        self.adopt_page = tk.BooleanVar(value=True)
        self.adopt_check = ttk.Checkbutton(self.retry_options, text='採用本頁候選', variable=self.adopt_page, command=self.choose_page)
        self.adopt_check.grid(row=1, column=3)
        if not batch_id:
            self.retry_options.grid_remove()
            self.page_list.grid_remove()
        panes = ttk.Panedwindow(self, orient='horizontal')
        panes.grid(row=3, column=0, sticky='nsew', padx=12)
        image_frame = ttk.Frame(panes)
        image_frame.rowconfigure(0, weight=1)
        image_frame.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(image_frame, width=320, height=300, bg='#e4e8e0', highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(image_frame, command=self.canvas.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        self.canvas.configure(yscrollcommand=scroll.set)
        horizontal = ttk.Scrollbar(image_frame, orient='horizontal', command=self.canvas.xview)
        horizontal.grid(row=1, column=0, sticky='ew')
        self.canvas.configure(xscrollcommand=horizontal.set)
        from .desktop import text_pane
        self.text_tabs = ttk.Notebook(panes)
        text_frame, self.text = text_pane(self.text_tabs, '逐頁擷取原稿／候選 · 唯讀')
        self.text_tabs.add(text_frame, text='本次文字')
        previous_frame, self.previous_text = text_pane(self.text_tabs, '原逐頁原稿 · 唯讀')
        self.text_tabs.add(previous_frame, text='原逐頁原稿')
        draft_frame, self.draft_text = text_pane(self.text_tabs, '原批校對稿全文 · 無精確頁次對應 · 唯讀')
        self.text_tabs.add(draft_frame, text='原批校對稿全文')
        for frame in (text_frame, previous_frame, draft_frame):
            heading = frame.grid_slaves(row=0, column=0)[0]
            frame.bind('<Configure>', lambda e, label=heading: label.configure(wraplength=max(120, e.width - 30)))
        if batch_id:
            from .desktop import Workbench
            Workbench.fill(self.draft_text, app.current_text)
        panes.add(image_frame, weight=1)
        panes.add(self.text_tabs, weight=1)
        self.progress = ttk.Label(self, padding=12, wraplength=850)
        self.progress.grid(row=4, column=0, sticky='ew')
        self.cancel_button = ttk.Button(self, text='關閉', command=self.close)
        self.cancel_button.grid(row=5, column=0, sticky='e', padx=12, pady=(0, 12))
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.bind('<Escape>', lambda e: self.close())
        self.bind('<Destroy>', self.destroyed)
        self.poll_id = self.after(40, self.poll)
        if batch_id:
            batch = next(b for b in self.flow.state['batches'] if b['id'] == batch_id)
            pdf = batch['pdf']
            self.pages = self.flow.pdf_pages(batch_id)
            self.preview = self.flow.pdf_source_preview(batch_id)
            self.start.set(str(pdf['start']))
            self.end.set(str(pdf['end']))
            self.page.set(str(pdf['start']))
            self.info.configure(text=f'{batch["source"]["original_name"]} · 共 {pdf["page_count"]} 頁 · 擷取 {pdf["start"]}–{pdf["end"]}（含兩端）\n逐頁原稿不隨全文校對變更；全文／外部編輯後無精確對應。')
            self.ready = True
            self.update_page_list()
            self.view()
        else:
            self.load(path)

    def submit(self, task, callback):
        if self.future is not None:
            return
        self.future = self.executor.submit(task)
        self.callback = callback
        self.ready = False
        self.view_button.configure(state='disabled')
        self.extract_button.configure(state='disabled')
        self.replace_button.configure(state='disabled')

    def toggle_settings(self):
        if self.options.winfo_ismapped():
            self.options.grid_remove()
        else:
            self.options.grid()

    def load(self, path):
        self.preview = None
        self.canvas.delete('all')
        self.page_info.configure(text='')
        self.progress.configure(text='')
        self.info.configure(text=f'{path}\n正在檢查 PDF…')
        def loaded(preview):
            self.preview = preview
            self.start.set('1')
            self.end.set(str(preview.page_count))
            self.page.set('1')
            self.info.configure(text=f'{preview.path.name} · {preview.size:,} 位元組 · 可讀 · 共 {preview.page_count} 頁\n專案：{self.flow.root}\n來源副本：{preview.size:,} 位元組；另需逐頁原稿與校對稿空間，保存時檢查。預設整份，兩端包含。')
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
                selected = next((p for p in (self.candidate_pages if self.candidate_pages is not None else self.pages) if p['number'] == number), None)
                if selected is None:
                    raise ProjectError('請輸入此批次範圍內的頁次。')
                from .desktop import Workbench
                Workbench.fill(self.text, selected['text'])
                if self.batch_id:
                    previous = next((p for p in self.pages if p['number'] == number), None)
                    Workbench.fill(self.previous_text, previous['text'] if previous else '')
                self.adopt_page.set(number in self.accepted_pages)
                self.adopt_check.configure(state='normal' if self.pending_job and self.pending_job.base_pages is not None
                                           and number in self.pending_job.numbers else 'disabled')
                issue: dict = next((i for i in self.flow.state['batches'] if i['id'] == self.batch_id), {})
                disposition = next((i['status'] for i in issue.get('source_issues', []) if i.get('page') == number), '')
                if self.candidate_pages is not None:
                    disposition = ''
                states = dict(success='成功', pending='待檢查', failed='擷取失敗', cancelled='已取消',
                              skipped='已明確略過', resolved='已處理')
                method = 'OCR ' + selected['settings'].get('language', '') if selected['method'] == 'ocr' else '文字層'
                rotation = selected['settings'].get('rotation', 0)
                self.page_info.configure(text=f'第 {number} 頁 · {method} · {states[selected["status"]]} · {rotation}° {states.get(disposition, "")}')
                self.progress.configure(text=selected['error'])
                if number in getattr(self, 'list_numbers', []):
                    self.page_list.current(self.list_numbers.index(number))
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
            self.image = None
            self.submit(task, self.show_image)
        except (ValueError, ProjectError) as error:
            self.progress.configure(text=str(error) if isinstance(error, ProjectError) else '頁次必須為整數。')

    def show_image(self, data):
        # PhotoImage decodes PNG without keeping native PDF handles or files open.
        self.image = tk.PhotoImage(master=self, data=data)
        self.canvas.delete('all')
        self.canvas.create_image(0, 0, image=self.image, anchor='nw')
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def extract(self):
        if not self.ready or not self.preview or self.job or self.pending_job or self.model_job:
            return
        try:
            self.job = self.flow.start_pdf_extraction(self.preview, int(self.start.get()), int(self.end.get()),
                                                       mode={'全部強制 OCR': 'ocr', '文字層': 'text-layer', '自動': 'auto'}[self.mode.get()],
                                                       language=self.language.get())
            self.ocr_controls(False)
            self.ready = False
            self.extract_button.configure(state='disabled')
            self.view_button.configure(state='disabled')
            self.replace_button.configure(state='disabled')
            self.cancel_button.configure(text='取消擷取並保留完整頁')
            self.retry_controls(False)
        except (ValueError, ProjectError) as error:
            self.progress.configure(text=str(error) if isinstance(error, ProjectError) else '起始／結束頁必須為整數。')

    def update_page_list(self):
        pages = self.candidate_pages if self.candidate_pages is not None else getattr(self, 'pages', [])
        self.list_numbers = [p['number'] for p in pages]
        states = dict(success='成功', pending='待檢查', failed='失敗', cancelled='取消／未完成')
        batch: dict = next((b for b in self.flow.state['batches'] if b['id'] == self.batch_id), {})
        issues = ({i.get('page'): i['status'] for i in batch.get('source_issues', [])}
                  if self.candidate_pages is None else {})
        self.page_list.configure(values=[f'第 {p["number"]} 頁 · {"OCR" if p["method"] == "ocr" else "文字層"} · {states[p["status"]]}'
                                         + (' · 已確認' if issues.get(p['number']) in ('resolved', 'skipped') else '') for p in pages])
        self.page_list.grid()

    def select_list_page(self, _event=None):
        if self.ready and self.page_list.current() >= 0:
            self.page.set(str(self.list_numbers[self.page_list.current()]))
            self.view()

    def retry_controls(self, enabled):
        for widget in (self.retry_page_button, self.failed_button, self.retain_button, self.skip_button):
            widget.configure(state='normal' if enabled and self.batch_id else 'disabled')
        self.rotation_select.configure(state='readonly' if enabled else 'disabled')
        self.page_list.configure(state='readonly' if enabled else 'disabled')

    def retry_page(self, *, failed_only=False):
        if not self.ready or not self.batch_id or self.pending_job or self.job or self.model_job:
            return
        try:
            self.job = self.flow.start_pdf_retry(self.batch_id, pages=None if failed_only else [int(self.page.get())],
                                                 failed_only=failed_only, language=self.language.get(),
                                                 rotation=int(self.rotation.get()))
            self.ready = False
            self.retry_controls(False)
            self.ocr_controls(False)
            self.extract_button.configure(state='disabled')
            self.view_button.configure(state='disabled')
            self.cancel_button.configure(text='取消擷取並保留完整頁')
        except (ProjectError, ValueError) as error:
            self.progress.configure(text=str(error))

    def choose_page(self):
        if not self.pending_job or self.pending_job.base_pages is None:
            return
        try:
            number = int(self.page.get())
        except ValueError:
            return
        if number in self.pending_job.numbers:
            if self.adopt_page.get():
                self.accepted_pages.add(number)
            else:
                self.accepted_pages.discard(number)

    def resolve_page(self, disposition):
        if not self.ready or not self.batch_id or self.pending_job or self.job:
            return
        try:
            number = int(self.page.get())
            batch = next(b for b in self.flow.state['batches'] if b['id'] == self.batch_id)
            for index, issue in enumerate(batch.get('source_issues', [])):
                if issue.get('page') == number and issue['status'] == 'pending':
                    self.flow.resolve_source_issue(self.batch_id, index, disposition)
            self.app.update_stats()
            self.update_page_list()
            self.view()
        except (ValueError, ProjectError) as error:
            self.progress.configure(text=str(error))

    def ocr_controls(self, enabled):
        self.mode_select.configure(state='readonly' if enabled else 'disabled')
        self.language_select.configure(state='readonly' if enabled else 'disabled')
        self.install_button.configure(state='normal' if enabled else 'disabled')

    def ocr_changed(self):
        self.ocr_info_pending = True
        self.install_button.configure(state='disabled')
        if self.future is not None or self.job or self.pending_job or self.model_job:
            return
        self.ocr_info_pending = False
        language = self.language.get()
        def show(info):
            if language != self.language.get():
                self.ocr_info_pending = True
                return
            self.model_info_language = language
            self.model_info.configure(text=(f'{info["codes"]} · 尚需下載 {info["download_bytes"]:,} 位元組\n'
                                            + (info['engine_error'] or ('模型已就緒。OCR 仍需人工校對。' if info['ready'] else
                                               '請按下載／安裝模型；需網路與模型目錄寫入權限。'))))
            self.install_button.configure(state='normal')
        self.model_info.configure(text='正在檢查所選 OCR 語言模型與下載大小…')
        self.submit(lambda: self.flow.ocr_models(language), show)

    def install_models(self):
        if self.future is not None or self.job or self.pending_job or self.model_job:
            return
        if self.model_info_language != self.language.get():
            self.ocr_changed()
            return
        self.model_job = self.flow.start_ocr_model_install(self.language.get())
        self.ocr_controls(False)
        self.extract_button.configure(state='disabled')
        self.replace_button.configure(state='disabled')
        self.cancel_button.configure(text='取消下載並關閉')

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
                self.ready = self.preview is not None or self.batch_id is not None
                self.view_button.configure(state='normal' if self.ready else 'disabled')
                self.extract_button.configure(state='normal' if self.preview and not self.pending_job and not self.model_job and not self.job else 'disabled')
                self.replace_button.configure(state='disabled' if self.pending_job or self.model_job else 'normal')
                self.retry_controls(not self.pending_job and not self.model_job and not self.job)
        if self.model_job is not None:
            state = self.model_job.state
            self.model_info.configure(text=f'{state["phase"]} · {state["downloaded"]:,}／{state["total"]:,} 位元組\n{state["error"]}')
            if self.model_job.wait(0):
                self.model_job = None
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
                    self.accepted_pages = set(self.pending_job.numbers)
                    self.update_page_list()
                    self.options.grid_remove()
                    self.cancel_button.configure(text='關閉並捨棄候選', state='normal')
                    self.accept_button = ttk.Button(self, text='採用為新批次', command=self.accept_candidate, style='Primary.TButton')
                    self.accept_button.grid(row=5, column=0, sticky='w', padx=12)
                    self.page.set(str(self.pending_job.numbers[0]))
                    self.info.configure(text='擷取候選 · 對照後採用為新批次；新批以逐頁原稿組成，原批人工校對與朗讀快照保留。\n重試頁可勾選採用，未採用頁沿用原逐頁原稿；可切換頁籤比較原稿及校對全文。')
                    if self.batch_id:
                        self.retry_options.grid()
                    self.view()
                    self.poll_id = self.after(40, self.poll)
                    return
                try:
                    self.app.batch_id = self.flow.finish_pdf_extraction(self.job)
                    self.job = None
                    self.app.step = 2
                    self.app.refresh()
                    self.destroy()
                    return
                except ProjectError as error:
                    self.closing = False
                    self.progress.configure(text=str(error) + '\n可重試保存或關閉以捨棄候選；既有校對稿未改變。')
                    self.cancel_button.configure(state='normal', text='關閉並捨棄未存候選')
                    self.pending_job = self.job
                    self.job = None
                    self.ready = False
                    self.retry_button = ttk.Button(self, text='重試保存', command=self.retry)
                    self.retry_button.grid(row=5, column=0, sticky='w', padx=12)
        if (self.ocr_info_pending and not self.closing and self.future is None
                and self.job is None and self.pending_job is None and self.model_job is None):
            self.ocr_changed()
        if self.closing and self.future is None and self.job is None and self.model_job is None:
            self.destroy()
            return
        self.poll_id = self.after(40, self.poll)

    def retry(self):
        self.job = self.pending_job
        self.pending_job = None
        self.retry_button.destroy()

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
        if self.job:
            self.job.cancel()
            self.job.wait()
        if self.model_job:
            self.model_job.cancel()
            self.model_job.wait()
        self.executor.shutdown(wait=True, cancel_futures=True)
        candidate = self.job or self.pending_job
        if candidate is not None:
            self.flow.discard_pdf_extraction(candidate)
        self.app.pdf_dialog = None
