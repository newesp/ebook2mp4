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
        self.future = None
        self.callback: Callable[[Any], None] | None = None
        self.closing = False
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='PDF preview')
        self.title('逐頁原稿／頁圖' if batch_id else 'PDF 預覽與選頁')
        self.geometry(f'{min(960, self.winfo_screenwidth() - 60)}x{min(720, self.winfo_screenheight() - 80)}+20+20')
        self.minsize(740, 570)
        self.transient(app.root)
        self.grab_set()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        self.info = ttk.Label(self, padding=12, wraplength=850)
        self.info.grid(row=0, column=0, sticky='ew')
        self.bind('<Configure>', lambda e: self.info.configure(wraplength=max(200, self.winfo_width() - 40)))
        options = ttk.Frame(self, padding=(12, 0))
        options.grid(row=1, column=0, sticky='ew')
        self.start, self.end, self.page = tk.StringVar(value='1'), tk.StringVar(value='1'), tk.StringVar(value='1')
        self.replace_button = ttk.Button(options, text='更換 PDF', command=self.replace)
        self.replace_button.grid(row=0, column=0, padx=(0, 10))
        for column, (label, variable) in enumerate((('起始', self.start), ('結束（含）', self.end)), 1):
            field = ttk.Frame(options)
            field.grid(row=0, column=column, padx=4)
            ttk.Label(field, text=label).pack(side='left')
            ttk.Entry(field, textvariable=variable, width=6, state='readonly' if batch_id else 'normal').pack(side='left')
        self.extract_button = ttk.Button(options, text='擷取為新批次', command=self.extract, state='disabled', style='Primary.TButton')
        self.extract_button.grid(row=0, column=3, padx=8)
        if batch_id:
            self.extract_button.grid_remove()
            self.replace_button.grid_remove()
        navigation = ttk.Frame(self, padding=12)
        navigation.grid(row=2, column=0, sticky='ew')
        ttk.Label(navigation, text='PDF 實際頁次（第一頁為 1；可能與印刷頁碼不同）').grid(row=0, column=0, columnspan=4, sticky='w')
        ttk.Entry(navigation, textvariable=self.page, width=7).grid(row=1, column=0, sticky='w')
        self.view_button = ttk.Button(navigation, text='顯示頁面', command=self.view, state='disabled')
        self.view_button.grid(row=1, column=1, sticky='w', padx=6)
        self.page_info = ttk.Label(navigation, text='', wraplength=550)
        self.page_info.grid(row=1, column=2, sticky='w')
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
        text_frame, self.text = text_pane(panes, '逐頁擷取原稿 · 唯讀')
        panes.add(image_frame, weight=1)
        panes.add(text_frame, weight=1)
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
            self.start.set(str(pdf['start']))
            self.end.set(str(pdf['end']))
            self.page.set(str(pdf['start']))
            self.info.configure(text=f'{batch["source"]["original_name"]} · 共 {pdf["page_count"]} 頁 · 擷取 {pdf["start"]}–{pdf["end"]}（含兩端）\n逐頁原稿不隨全文校對變更；全文／外部編輯後無精確對應。')
            self.ready = True
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
            if self.batch_id:
                selected = next((p for p in self.pages if p['number'] == number), None)
                if selected is None:
                    raise ProjectError('請輸入此批次範圍內的頁次。')
                from .desktop import Workbench
                Workbench.fill(self.text, selected['text'])
                issue: dict = next((i for i in self.flow.state['batches'] if i['id'] == self.batch_id), {})
                disposition = next((i['status'] for i in issue.get('source_issues', []) if i.get('page') == number), '')
                states = dict(success='成功', pending='待檢查', failed='擷取失敗', cancelled='已取消',
                              skipped='已明確略過', resolved='已處理')
                self.page_info.configure(text=f'第 {number} 頁 · 文字層 · {states[selected["status"]]} {states.get(disposition, "")}')
                self.progress.configure(text=selected['error'])
                task = lambda: self.flow.pdf_page_image(self.batch_id, number)
            else:
                if self.preview is None:
                    return
                preview = self.preview
                from .pdf import validate_range
                validate_range(number, number, preview.page_count)
                task = lambda: self.flow.preview_pdf_page(preview, number)
                self.page_info.configure(text=f'第 {number} 頁 · 原始頁圖')
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
        if not self.ready or not self.preview or self.job:
            return
        try:
            self.job = self.flow.start_pdf_extraction(self.preview, int(self.start.get()), int(self.end.get()))
            self.ready = False
            self.extract_button.configure(state='disabled')
            self.view_button.configure(state='disabled')
            self.replace_button.configure(state='disabled')
            self.cancel_button.configure(text='取消擷取並保留完整頁')
        except (ValueError, ProjectError) as error:
            self.progress.configure(text=str(error) if isinstance(error, ProjectError) else '起始／結束頁必須為整數。')

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
                self.extract_button.configure(state='normal' if self.preview else 'disabled')
                self.replace_button.configure(state='normal')
        if self.job is not None:
            status = dict(running='執行中', cancelling='取消中', cancelled='已取消', completed='完成')[self.job.status]
            self.progress.configure(text=f'{status} · 已完成 {len(self.job.pages)}／{self.job.end - self.job.start + 1} 頁；取消時保留完整頁，未完成頁標待檢查。')
            if self.job.wait(0):
                try:
                    self.app.batch_id = self.flow.finish_pdf_extraction(self.job)
                    self.job = None
                    self.app.step = 2
                    self.app.refresh()
                    self.destroy()
                    return
                except ProjectError as error:
                    self.progress.configure(text=str(error) + '\n可重試保存或關閉以捨棄候選；既有校對稿未改變。')
                    self.cancel_button.configure(text='關閉並捨棄未存候選')
                    self.pending_job = self.job
                    self.job = None
                    self.ready = False
                    self.retry_button = ttk.Button(self, text='重試保存', command=self.retry)
                    self.retry_button.grid(row=5, column=0, sticky='w', padx=12)
        if self.closing and self.future is None and self.job is None:
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
            self.cancel_button.configure(state='disabled', text='取消中，等待目前頁完成…')
        elif self.future is None:
            self.destroy()

    def destroyed(self, event):
        if event.widget is not self:
            return
        self.after_cancel(self.poll_id)
        if self.job:
            self.job.cancel()
            self.job.wait()
        self.executor.shutdown(wait=True, cancel_futures=True)
        candidate = self.job or self.pending_job
        if candidate is not None:
            self.flow.discard_pdf_extraction(candidate)
        self.app.pdf_dialog = None
