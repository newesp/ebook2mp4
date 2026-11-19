"""Embedded import, page comparison, extraction preview, and anomaly handling."""
from difflib import unified_diff
from io import BytesIO
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .ui_controls import AutoHideScrollbar
from .workflow import ProjectError, ProjectWorkflow


class SourceTools:
    def __init__(self, app, parent):
        from .production_desktop import ScrollPage
        self.app = app
        self.path = None
        self.kind = None
        self.reload = False
        self.text_candidate = None
        self.image_future = None
        self.image_identity = None
        self.image_dirty = False
        self.page_cache = None
        self.scope = tk.StringVar(value='指定頁面')
        self.start = tk.StringVar(value='1')
        self.end = tk.StringVar(value='1')
        self.mode = tk.StringVar(value='自動')
        self.language = tk.StringVar(value='自動中英')
        self.layout = tk.StringVar(value='自動版面')
        self.rotation = tk.StringVar(value='0')
        self.encoding = tk.StringVar(value='auto')
        self.model_job = None
        self.preview_kind = None
        self.base_text = ''
        self.preview_identity = None
        self.parent = parent
        self.issue_view = False
        self.page_focus = False
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        self.detail = ttk.Label(parent, text='', width=1, wraplength=750)
        self.detail.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 8))
        self.main = ttk.Frame(parent)
        self.main.grid(row=1, column=0, sticky='nsew')
        self.main.columnconfigure(0, weight=1)
        self.main.rowconfigure(0, weight=1)
        self.issue_empty = ttk.Label(self.main, text='目前沒有待處理的來源異常', anchor='nw', wraplength=260)
        self.scroll = scroll = ScrollPage(self.main)
        scroll.grid(row=0, column=0, sticky='nsew')
        # ScrollPage owns its canvas; hide its rail only when its content fits.
        scroll_bar = next(w for w in scroll.winfo_children() if isinstance(w, ttk.Scrollbar))
        def update_form_scroll(first, last):
            scroll_bar.set(first, last)
            if float(first) <= 0 and float(last) >= 1:
                scroll_bar.grid_remove()
            else:
                scroll_bar.grid()
        scroll.canvas.configure(yscrollcommand=update_form_scroll)
        content = scroll.content
        content.columnconfigure(0, weight=1)
        self.txt_fields = ttk.Frame(content)
        self.txt_fields.grid(row=0, column=0, sticky='ew')
        ttk.Label(self.txt_fields, text='TXT 編碼').pack(side='left', padx=8)
        self.encoding_combo = ttk.Combobox(self.txt_fields, textvariable=self.encoding,
            values=('auto', 'UTF-8', 'UTF-8 BOM', 'UTF-16 BOM', 'Big5', 'CP950'), state='readonly', width=15)
        self.encoding_combo.pack(side='left')
        self.encoding_combo.bind('<<ComboboxSelected>>', lambda e: self.load_txt())
        ttk.Button(self.txt_fields, text='重新載入預覽', command=self.load_txt).pack(side='left', padx=8)
        self.pdf_fields = ttk.Frame(content)
        self.pdf_fields.grid(row=1, column=0, sticky='ew', padx=12, pady=12)
        self.pdf_fields.columnconfigure((0, 1), weight=1, uniform='source-field')
        self.pdf_field_groups = []
        for row, (label, variable, values) in enumerate((
            ('起始頁', self.start, None), ('結束頁（含）', self.end, None),
            ('擷取方式', self.mode, ('自動', '文字層', '全部強制 OCR')),
            ('語言', self.language, ('自動中英', '繁中＋英文', '簡中＋英文', '英文')),
            ('版面', self.layout, ('自動版面', '單一區塊', '單行標題')),
            ('處理範圍', self.scope, ('指定頁面', '目前頁面', '框選區域', '失敗頁')),
            ('旋轉角度', self.rotation, ('0', '90', '180', '270')))):
            field = ttk.Frame(self.pdf_fields)
            self.pdf_field_groups.append(field)
            field.grid(row=row//2, column=row%2, sticky='ew', padx=(0, 12), pady=(0, 8))
            field.columnconfigure(0, weight=1)
            ttk.Label(field, text=label).grid(row=0, column=0, sticky='w', pady=(0, 8))
            control = (ttk.Combobox(field, textvariable=variable, values=values, state='readonly', width=12)
                       if values else ttk.Entry(field, textvariable=variable, width=8))
            control.grid(row=1, column=0, sticky='ew')
            if variable is self.scope:
                control.bind('<<ComboboxSelected>>', lambda e: self.scope_changed())
            if variable is self.rotation:
                control.bind('<<ComboboxSelected>>', lambda e: self.render_page())
        ocr_field = ttk.Frame(self.pdf_fields)
        ocr_field.columnconfigure(0, weight=1)
        ocr_field.grid(row=3, column=1, sticky='ew', padx=(0, 12), pady=(0, 8))
        self.pdf_field_groups.append(ocr_field)
        ttk.Label(ocr_field, text='OCR 模型').grid(row=0, column=0, sticky='w', pady=(0, 8))
        self.ocr_button = ttk.Button(ocr_field, text='下載／安裝 OCR 模型',
            command=self.install_models, style='Workspace.TButton')
        self.ocr_button.grid(row=1, column=0, sticky='ew')
        self.main.bind('<Configure>', self.reflow_fields)
        self.region_frame = ttk.Frame(self.main)
        self.region_frame.grid(row=0, column=0, sticky='nsew')
        self.region_frame.columnconfigure(0, weight=1)
        self.region_frame.rowconfigure(1, weight=1)
        ttk.Label(self.region_frame, text='框選右側原頁，再反白下方對應原頁文字。').grid(row=0, column=0, sticky='w')
        self.region_text = tk.Text(self.region_frame, wrap='word', height=3, width=1, exportselection=False)
        self.region_text.grid(row=1, column=0, sticky='nsew')
        region_scroll = ttk.Scrollbar(self.region_frame, command=self.region_text.yview)
        region_scroll.grid(row=1, column=1, sticky='ns')
        self.region_text.configure(yscrollcommand=region_scroll.set)
        self.region_frame.grid_remove()
        self.footer = ttk.Frame(parent)
        self.footer.grid(row=2, column=0, columnspan=2, sticky='ew', pady=8)
        ttk.Button(self.footer, text='返回文稿', command=app.close_tools).pack(side='left')
        self.run_button = ttk.Button(self.footer, text='重新擷取，預覽差異', command=self.extract, style='Primary.TButton')
        self.run_button.pack(side='right')
        self.form_button = ttk.Button(self.footer, text='處理設定', command=self.show_form)
        self.form_button.pack(side='left', padx=8)
        self.region_button = ttk.Button(self.footer, text='框選文字', command=self.show_region)
        self.issue_frame = ttk.Frame(content)
        self.issue_frame.grid(row=5, column=0, sticky='ew', padx=8)
        self.issue_frame.columnconfigure(0, weight=1)
        self.issue_selector = ttk.Combobox(self.issue_frame, state='readonly', width=18)
        self.issue_selector.grid(row=0, column=0, sticky='ew')
        self.issue_selector.bind('<<ComboboxSelected>>', self.locate_issue)
        decisions = ttk.Frame(self.issue_frame)
        decisions.grid(row=1, column=0, sticky='w')
        ttk.Button(decisions, text='已處理', command=lambda: self.resolve('resolved')).pack(side='left')
        ttk.Button(decisions, text='明確略過', command=lambda: self.resolve('skipped')).pack(side='left', padx=4)
        self.warning_accepted = tk.BooleanVar(value=False)
        self.warning_check = ttk.Checkbutton(parent, text='已核對異常字元，確認原文如此', variable=self.warning_accepted)
        self.preview = tk.Text(self.main, height=4, width=1, wrap='word', state='disabled', font=('Microsoft JhengHei', 12))
        self.preview.grid(row=0, column=0, sticky='nsew')
        self.preview_scroll = AutoHideScrollbar(self.main, command=self.preview.yview)
        self.preview_scroll.grid(row=0, column=1, sticky='ns')
        self.preview.configure(yscrollcommand=self.sync_preview_scroll)
        self.preview_scroll.grid_remove()
        self.preview.grid_remove()
        self.page_choices = ttk.Frame(parent)
        self.page_choices.grid(row=4, column=0, columnspan=2, sticky='ew')
        self.page_choice_menu = None
        self.page_choice_vars = {}
        self.preview_actions = ttk.Frame(parent)
        self.preview_actions.grid(row=5, column=0, columnspan=2, sticky='ew', pady=4)
        self.apply_button = ttk.Button(self.preview_actions, text='套用預覽', command=self.apply)
        self.apply_button.pack(side='right')
        self.continue_button = ttk.Button(self.preview_actions, text='保留選擇，繼續修正', command=self.continue_refining)
        self.continue_button.pack(side='right', padx=4)
        ttk.Button(self.preview_actions, text='放棄預覽', command=self.discard).pack(side='left')
        self.preview_actions.grid_remove()
        # Source region work needs the actual physical page. Each side owns its scroll.
        self.page_frame = ttk.Frame(parent, padding=(12, 0, 0, 0))
        self.page_frame.columnconfigure(0, weight=1)
        self.page_frame.rowconfigure(1, weight=1)
        nav = ttk.Frame(self.page_frame)
        nav.grid(row=0, column=0, sticky='ew', pady=(0, 8))
        ttk.Label(nav, text='來源原頁').pack(side='left')
        ttk.Button(nav, text='‹', width=2, command=lambda: app.change_source_page(-1)).pack(side='left')
        page = ttk.Entry(nav, textvariable=app.page_number, width=4)
        page.pack(side='left')
        page.bind('<Return>', lambda e: self.render_page())
        ttk.Button(nav, text='›', width=2, command=lambda: app.change_source_page(1)).pack(side='left')
        zoom = ttk.Combobox(nav, textvariable=app.source_zoom,
            values=('符合頁寬', '50%', '75%', '100%'), state='readonly', width=10)
        zoom.pack(side='left', padx=4)
        zoom.bind('<<ComboboxSelected>>', lambda e: app.draw_source_image())
        self.page_canvas = tk.Canvas(self.page_frame, highlightthickness=0, background='#edf0ed', width=1)
        self.page_canvas.grid(row=1, column=0, sticky='nsew')
        bar = ttk.Scrollbar(self.page_frame, command=self.page_canvas.yview)
        bar.grid(row=1, column=1, sticky='ns')
        def update_page_scroll(first, last):
            bar.set(first, last)
            if float(first) <= 0 and float(last) >= 1:
                bar.grid_remove()
            else:
                bar.grid()
        self.page_canvas.configure(yscrollcommand=update_page_scroll)
        from .desktop import bind_canvas_wheel
        bind_canvas_wheel(self.page_canvas)
        self.page_canvas.bind('<Configure>', lambda e: app.draw_source_image())
        self.page_canvas.bind('<Map>', lambda e: app.draw_source_image())
        self.page_canvas.bind('<ButtonPress-1>', app.begin_source_region)
        self.page_canvas.bind('<B1-Motion>', app.drag_source_region)
        self.page_canvas.bind('<ButtonRelease-1>', app.end_source_region)
        scroll.bind_scroll()

    def show_form(self):
        self.issue_empty.grid_remove()
        self.preview.grid_remove()
        self.preview_scroll.grid_remove()
        self.region_frame.grid_remove()
        self.scroll.grid()

    def reflow_fields(self, _event=None):
        columns = 2
        for index, field in enumerate(self.pdf_field_groups):
            field.grid_configure(row=index//columns, column=index%columns)

    def show_region(self):
        self.scroll.grid_remove()
        self.preview.grid_remove()
        self.preview_scroll.grid_remove()
        self.region_frame.grid()

    def layout_preview(self):
        app = self.app
        visible = self.has_pdf_page()
        narrow = self.app.root.winfo_width() < 1100
        if visible and narrow:
            self.parent.columnconfigure(0, weight=1, uniform='')
            self.parent.columnconfigure(1, weight=0, uniform='')
            if self.page_focus:
                self.main.grid_remove()
                self.page_frame.grid(row=1, column=0, sticky='nsew')
            else:
                self.main.grid()
                self.page_frame.grid_remove()
            return
        self.main.grid()
        if visible:
            self.page_frame.grid(row=1, column=1, sticky='nsew')
            if self.issue_view:
                self.parent.columnconfigure(0, weight=3, uniform='source-issue')
                self.parent.columnconfigure(1, weight=7, uniform='source-issue')
            else:
                self.parent.columnconfigure(0, weight=1, uniform='')
                self.parent.columnconfigure(1, weight=1, uniform='')
        else:
            self.page_frame.grid_remove()
            self.parent.columnconfigure(0, weight=1, uniform='')
            self.parent.columnconfigure(1, weight=0, uniform='')

    def has_pdf_page(self):
        app = self.app
        batch = app.flow._batch(app.batch_id) if app.flow and app.batch_id else None
        return bool(app.import_preview or (batch and batch['kind'] == 'pdf'))

    def open_issue_view(self):
        self.issue_view = True
        self.show_form()
        self.pdf_fields.grid_remove()
        self.txt_fields.grid_remove()
        self.run_button.pack_forget()
        self.form_button.pack_forget()
        self.region_button.pack_forget()
        self.show_issues()
        self.layout_preview()
        if self.issues:
            self.locate_issue()
        else:
            self.detail.configure(text='目前沒有待處理的來源異常。')

    def open_processing_view(self):
        was_issue = self.issue_view
        self.issue_view = False
        if was_issue:
            self.page_focus = False
            self.show_form()
            self.detail.configure(text='調整來源設定後，重新擷取並預覽差異。')
        self.form_button.pack(side='left', padx=8)
        self.refresh()

    def toggle_page_view(self):
        self.page_focus = not self.page_focus
        self.layout_preview()
        self.render_page()
        self.app.update_stats()

    def reset_source(self):
        self.path = None
        self.kind = None
        self.page_cache = None
        self.preview_kind = None
        self.text_candidate = None
        self.image_identity = None

    def refresh(self):
        app = self.app
        batch = app.flow._batch(app.batch_id) if app.flow and app.batch_id else None
        kind = self.kind or (batch['kind'] if batch else None)
        self.pdf_fields.grid() if kind == 'pdf' else self.pdf_fields.grid_remove()
        self.txt_fields.grid() if kind == 'txt' else self.txt_fields.grid_remove()
        self.run_button.pack(side='right') if kind == 'pdf' else self.run_button.pack_forget()
        self.layout_preview()
        if kind == 'pdf':
            self.render_page()
        self.run_button.configure(state='disabled' if app.workspace_busy or app.source_pending else 'normal')
        if batch and kind == 'pdf' and not self.path:
            if self.page_cache != (id(app.flow), app.batch_id):
                self.start.set(str(batch['pdf']['start']))
                self.end.set(str(batch['pdf']['end']))
                self.page_cache = (id(app.flow), app.batch_id)
        self.show_issues()

    def import_file(self, kind, reload=False, path=None):
        app = self.app
        if not app.flow or not app.may_leave():
            return
        path = path or filedialog.askopenfilename(parent=app.root, title='匯入文稿' if not reload else '重載外部稿',
            filetypes=[('PDF' if kind == 'pdf' else 'TXT', '*.pdf' if kind == 'pdf' else '*.txt')])
        if not path:
            return
        self.path, self.kind, self.reload = Path(path), kind, reload
        self.base_text = app.current_text if app.batch_id else ''
        self.preview_identity = (app.flow, app.batch_id)
        app.open_tools(2)
        self.refresh()
        if kind == 'txt':
            self.load_txt(auto_import=not reload)
        else:
            try:
                app.import_preview = ProjectWorkflow.inspect_pdf(path)
                self.start.set('1')
                self.end.set(str(app.import_preview.page_count))
                app.page_number.set('1')
                self.detail.configure(text=f'{self.path.name} · {app.import_preview.page_count} 頁。調整範圍後執行擷取。')
                app.source_visible = True
                if app.inner_host.active_id != app.source_page.page_id:
                    app.panes.grid()
                app.import_panel.grid_remove()
                app.adapt_source()
                self.render_page()
                self.run_button.configure(text='匯入所選頁面')
            except ProjectError as error:
                self.detail.configure(text=str(error))

    def load_txt(self, auto_import=False):
        app = self.app
        if app.workspace_busy or not app.flow:
            return
        try:
            path = self.path
            if path is None and app.batch_id:
                path = app.flow._path(app.flow._batch(app.batch_id)['source']['path'])
                self.reload = True
            if path is None:
                return
            self.txt_preview = app.flow.inspect_txt(path, self.encoding.get())
            if auto_import and not self.txt_preview.warnings:
                app.batch_id = app.flow.import_txt(self.txt_preview)
                app.import_preview = None
                self.path = self.kind = None
                app.refresh()
                return
            self.base_text = app.current_text
            self.preview_identity = (app.flow, app.batch_id)
            self.preview_text(self.txt_preview.text, 'TXT 重載' if self.reload else 'TXT 匯入')
            if self.txt_preview.warnings:
                self.detail.configure(text='；'.join(self.txt_preview.warnings))
                self.warning_check.grid(row=3, column=0, columnspan=2, sticky='w', padx=8)
            else:
                self.warning_check.grid_remove()
        except ProjectError as error:
            self.detail.configure(text=str(error))
        app.inner_host.refresh(app.source_page.page_id)

    def sync_preview_scroll(self, first, last):
        if self.preview.winfo_manager():
            self.preview_scroll.set(first, last)

    def preview_text(self, text, kind):
        app = self.app
        self.text_candidate = text
        self.preview_kind = kind
        self.base_text = app.current_text
        self.preview_identity = (app.flow, app.batch_id)
        app.fill(self.preview, ''.join(unified_diff(self.base_text.splitlines(True), text.splitlines(True),
            fromfile='目前文稿', tofile=kind)) or '與目前全文相同。')
        self.preview.yview_moveto(0)
        self.preview.grid()
        self.scroll.grid_remove()
        self.region_frame.grid_remove()
        self.preview_actions.grid()
        self.continue_button.pack(side='right', padx=4) if app.source_pending else self.continue_button.pack_forget()
        self.detail.configure(text=f'{kind} · 先檢查差異，再套用。現稿會先備份。')

    def scope_changed(self):
        app = self.app
        self.layout_preview()
        region = self.scope.get() == '框選區域'
        self.region_button.pack(side='left') if region else self.region_button.pack_forget()
        self.region_frame.grid() if region else self.region_frame.grid_remove()
        if region:
            self.scroll.grid_remove()
            self.preview.grid_remove()
            self.preview_scroll.grid_remove()
        elif not self.preview.winfo_manager():
            self.scroll.grid()
        if region:
            self.render_page()
        self.detail.configure(text='框選右側原頁，再反白對應原頁文字。' if region else '')

    def render_page(self):
        app = self.app
        if not app.flow:
            return
        self.layout_preview()
        batch = app.flow._batch(app.batch_id) if app.batch_id else None
        is_pdf = bool(app.import_preview) or (batch and batch['kind'] == 'pdf')
        app.manuscript_layout.show_pdf_controls(is_pdf)
        if not is_pdf:
            app.image_frame.grid_remove()
            app.source_text_frame.grid()
            return
        app.source_text_frame.grid_remove()
        app.image_frame.grid(row=1, column=0, sticky='nsew')
        try:
            number = int(app.page_number.get())
            preview = app.import_preview or app.flow.pdf_source_preview(app.batch_id)
            from .pdf import validate_range, render
            validate_range(number, number, preview.page_count)
            rotation = int(self.rotation.get())
            identity = (app.flow, app.batch_id, number, preview.path, rotation)
            if self.image_future:
                self.image_dirty = self.image_identity != identity
                return
            # Never leave a different physical page visible while rendering fails.
            if app.source_image is not None:
                app.source_image.close()
                app.source_image = None
            app.image_canvas.delete('all')
            self.page_canvas.delete('all')
            self.image_identity = identity
            self.image_future = app.executor.submit(render, preview.data, number, preview.page_count, rotation=rotation)
            app.source_heading.configure(text='PDF 原稿')
            app.page_total.configure(text=f'/{preview.page_count}')
            if batch and batch['kind'] == 'pdf':
                pages = app.flow.pdf_extraction_pages(app.source_pending) if app.source_pending else app.flow.pdf_pages(app.batch_id)
                if app.source_pending and app.source_pending.decision_baseline:
                    accepted = {n for n,v in self.page_choice_vars.items() if v.get()}
                    baseline = {p['number']: p for p in app.source_pending.decision_baseline}
                    pages = [p if p['number'] in accepted else baseline[p['number']] for p in pages]
                page = next((p for p in pages if p['number'] == number), None)
                if page:
                    app.fill(self.region_text, page['text'], True)
        except (ValueError, ProjectError) as error:
            self.detail.configure(text=str(error) if isinstance(error, ProjectError) else '頁碼必須為整數。')
            app.status.configure(text=self.detail.cget('text'))

    def extract(self):
        app = self.app
        if app.workspace_busy or app.source_pending:
            return
        try:
            app.autosave_workspace()
            self.base_text = app.current_text
            self.preview_identity = (app.flow, app.batch_id)
            if app.batch_id:
                app.flow.backup_manuscript(app.batch_id, app.current_text, label='重新擷取前編輯稿')
            layout = {'自動版面': 'auto', '單一區塊': 'block', '單行標題': 'line'}[self.layout.get()]
            if app.import_preview or self.scope.get() == '指定頁面':
                preview = app.import_preview or app.flow.pdf_source_preview(app.batch_id)
                app.source_job = app.flow.start_pdf_extraction(preview, int(self.start.get()), int(self.end.get()),
                    mode={'自動': 'auto', '文字層': 'text-layer', '全部強制 OCR': 'ocr'}[self.mode.get()],
                    language=self.language.get(), layout=layout)
            else:
                scope = self.scope.get()
                region = text_range = None
                if scope == '框選區域':
                    ranges = self.region_text.tag_ranges('sel')
                    if not app.source_selection or not ranges:
                        raise ProjectError('請先框選原頁，並反白對應原頁文字。')
                    region = app.source_selection
                    text_range = tuple(len(self.region_text.get('1.0', index)) for index in ranges)
                app.source_job = app.flow.start_pdf_retry(app.batch_id,
                    pages=None if scope == '失敗頁' else [int(app.page_number.get())], failed_only=scope == '失敗頁',
                    language=self.language.get(), layout=layout, rotation=int(self.rotation.get()),
                    region=region, text_range=text_range)
            self.detail.configure(text='擷取中…')
            self.refresh()
            app.update_stats()
        except (ProjectError, ValueError) as error:
            self.detail.configure(text=str(error) if isinstance(error, ProjectError) else '頁碼必須為整數。')

    def poll(self):
        app = self.app
        if self.image_future and self.image_future.done():
            future, self.image_future = self.image_future, None
            try:
                data = future.result()
                identity = self.image_identity
                if not self.image_dirty and identity and identity[:3] == (app.flow, app.batch_id, int(app.page_number.get())):
                    from PIL import Image
                    if app.source_image is not None:
                        app.source_image.close()
                    with Image.open(BytesIO(data)) as image:
                        app.source_image = image.copy()
                    app.draw_source_image()
            except (ProjectError, ValueError) as error:
                self.detail.configure(text=str(error))
            if self.image_dirty:
                self.image_dirty = False
                self.render_page()
        if self.model_job:
            state = self.model_job.state
            self.detail.configure(text=f'OCR 模型 · {state["status"]} · {state.get("error", "")}')
            if self.model_job.wait(0):
                self.model_job = None
                app.source_job = None
                app.update_stats()
        if app.source_job and not self.model_job:
            job = app.source_job
            app.job_status.configure(text=f'來源擷取 · {len(job.pages)}／{len(job.numbers)} 頁 · {job.status}')
            if job.wait(0):
                app.source_job = None
                try:
                    if app.import_preview:
                        app.batch_id = app.flow.finish_pdf_extraction(job)
                        app.import_preview = None
                        self.path = self.kind = None
                        app.refresh()
                        app.status.configure(text='PDF 已匯入。來源異常仍須處理。' if app.flow.confirmation_blockers(app.batch_id) else 'PDF 已匯入，可直接編輯全文。')
                    else:
                        app.source_pending = job
                        pages = app.flow.pdf_extraction_pages(job)
                        self.preview_text('\n\n'.join(p['text'] for p in pages), 'PDF 重新擷取')
                        self.page_choice_vars = {}
                        for widget in self.page_choices.winfo_children():
                            widget.destroy()
                        if job.base_pages is not None:
                            from .ui_controls import command_menu
                            control, menu = command_menu(self.page_choices, '套用頁面選擇')
                            control.pack(side='left')
                            self.page_choice_menu = menu
                            for number in job.candidate_numbers:
                                variable = tk.BooleanVar(value=True)
                                self.page_choice_vars[number] = variable
                                menu.add_checkbutton(label=f'套用第 {number} 頁', variable=variable, command=self.render_page)
                        self.render_page()
                except ProjectError as error:
                    app.source_pending = job
                    self.detail.configure(text=str(error))
                    self.preview_actions.grid()
                    self.preview_identity = (app.flow, app.batch_id)
                    self.base_text = app.current_text
                    self.continue_button.pack_forget()
                app.update_stats()

    def apply(self):
        app = self.app
        if self.preview_identity != (app.flow, app.batch_id) or app.current_text != self.base_text or app.workspace_busy:
            self.detail.configure(text='文稿已變更。請重新預覽；現稿保留。')
            return
        try:
            if self.preview_kind in ('TXT 匯入', 'TXT 重載') and self.txt_preview.warnings and not self.warning_accepted.get():
                raise ProjectError('請先核對異常字元。')
            if app.source_pending:
                job = app.source_pending
                accepted = [n for n, value in self.page_choice_vars.items() if value.get()] if job.base_pages is not None else None
                app.batch_id = app.flow.finish_pdf_extraction(job, accepted_pages=accepted)
                app.source_pending = None
                app.import_preview = None
                self.path = self.kind = None
                app.refresh()
                self.detail.configure(text='擷取結果已存為新批次；原批次與人工稿備份保留。')
            elif self.preview_kind == 'TXT 匯入':
                app.batch_id = app.flow.import_txt(self.txt_preview, accept_warnings=self.warning_accepted.get())
                self.path = self.kind = None
                app.refresh()
            elif self.text_candidate is not None:
                app.flow.backup_manuscript(app.batch_id, app.current_text, label='來源套用前編輯稿')
                app.flow.invalidate_reading(app.batch_id)
                app.set_editor(self.text_candidate)
                app.workspace_review = None
                app.allow_partial = False
                app.autosave_workspace()
                app.mark_diff()
            self.preview.grid_remove()
            self.preview_scroll.grid_remove()
            self.scroll.grid()
            self.preview_actions.grid_remove()
            self.warning_check.grid_remove()
            for widget in self.page_choices.winfo_children():
                widget.destroy()
            app.update_stats()
        except ProjectError as error:
            self.detail.configure(text=str(error))

    def continue_refining(self):
        app = self.app
        if not app.source_pending or app.workspace_busy:
            return
        try:
            if self.preview_identity != (app.flow, app.batch_id) or app.current_text != self.base_text:
                raise ProjectError('原稿已變更。請放棄預覽後重新擷取。')
            region = text_range = None
            if self.scope.get() == '框選區域':
                ranges = self.region_text.tag_ranges('sel')
                if not app.source_selection or not ranges:
                    raise ProjectError('請框選新範圍，並反白目前頁面中的對應文字。')
                region = app.source_selection
                text_range = tuple(len(self.region_text.get('1.0', index)) for index in ranges)
            app.source_job = app.flow.start_pdf_candidate_retry(app.source_pending,
                pages=[int(app.page_number.get())],
                accepted_pages=[n for n,v in self.page_choice_vars.items() if v.get()],
                language=self.language.get(), rotation=int(self.rotation.get()),
                layout={'自動版面': 'auto', '單一區塊': 'block', '單行標題': 'line'}[self.layout.get()],
                region=region, text_range=text_range)
            app.source_pending = None
            self.preview_actions.grid_remove()
            app.update_stats()
        except (ProjectError, ValueError) as error:
            self.detail.configure(text=str(error))

    def discard(self):
        app = self.app
        if app.source_pending:
            app.flow.discard_pdf_extraction(app.source_pending)
            app.source_pending = None
        self.text_candidate = None
        self.preview_kind = None
        self.preview_identity = None
        self.preview.grid_remove()
        self.preview_scroll.grid_remove()
        self.scroll.grid()
        self.preview_actions.grid_remove()
        self.warning_check.grid_remove()
        for widget in self.page_choices.winfo_children():
            widget.destroy()
        self.detail.configure(text='已放棄預覽。')
        app.update_stats()

    def show_issues(self):
        app = self.app
        self.issues = []
        if app.flow and app.batch_id:
            self.issues = [(i, issue) for i, issue in enumerate(app.flow._batch(app.batch_id).get('source_issues', [])) if issue['status'] == 'pending']
        if self.issues:
            self.issue_frame.grid()
            self.issue_selector.configure(values=[item['reason'] for _, item in self.issues])
            self.issue_selector.current(0)
        else:
            self.issue_frame.grid_remove()
        if self.issue_view and not self.issues:
            self.scroll.grid_remove()
            self.issue_empty.grid(row=0, column=0, sticky='nsew', padx=8, pady=8)
        else:
            self.issue_empty.grid_remove()
            if self.issue_view:
                self.scroll.grid()

    def locate_issue(self, _event=None):
        index = self.issue_selector.current()
        if 0 <= index < len(self.issues):
            issue = self.issues[index][1]
            self.detail.configure(text=issue['reason'])
            if issue.get('page'):
                self.app.page_number.set(str(issue['page']))
                self.app.source_visible = True
                self.app.adapt_source()
                self.render_page()

    def resolve(self, disposition):
        app = self.app
        index = self.issue_selector.current()
        if app.workspace_busy or not 0 <= index < len(self.issues):
            return
        if disposition == 'skipped' and not messagebox.askyesno('略過來源異常',
                '略過後，此項異常將不再阻擋朗讀保存。確定略過？', parent=app.root, default='no'):
            return
        try:
            app.flow.resolve_source_issue(app.batch_id, self.issues[index][0], disposition)
            self.show_issues()
            if self.issue_view:
                if self.issues:
                    self.locate_issue()
                else:
                    self.detail.configure(text='來源異常已全部處理。')
            app.update_stats()
        except ProjectError as error:
            self.detail.configure(text=str(error))

    def install_models(self):
        if self.app.workspace_busy:
            return
        try:
            self.model_job = self.app.flow.start_ocr_model_install(self.language.get())
            self.app.source_job = self.model_job
            self.app.update_stats()
        except ProjectError as error:
            self.detail.configure(text=str(error))
