"""Gemini settings and paragraph comparison in native, resizable Tk windows."""
import difflib
import tkinter as tk
from tkinter import ttk, messagebox

from .desktop import text_pane
from .workflow import ProjectError, ProjectWorkflow


class SettingsDialog(tk.Toplevel):
    def __init__(self, app):
        error = ''
        try:
            settings = ProjectWorkflow.gemini_settings()
        except ProjectError as e:
            from .gemini import DEFAULT_MODEL
            settings = dict(key='', model=DEFAULT_MODEL)
            error = str(e)
        super().__init__(app.root)
        self.app, self.job, self.closing = app, None, False
        self.poll_token = None
        self.title('Gemini 本機設定')
        self.geometry('540x410')
        self.minsize(500, 390)
        self.columnconfigure(0, weight=1)
        body = ttk.Frame(self, padding=20)
        body.grid(sticky='nsew')
        body.columnconfigure(0, weight=1)
        ttk.Label(body, text='API Key（僅本機 Windows 帳號加密保存）').grid(sticky='w')
        self.key = tk.StringVar(value=settings['key'])
        ttk.Entry(body, textvariable=self.key, show='●').grid(sticky='ew', pady=(6, 16))
        ttk.Label(body, text='Gemini 模型 ID（可自行輸入）').grid(sticky='w')
        self.model = tk.StringVar(value=settings['model'])
        ttk.Combobox(body, textvariable=self.model, values=('gemini-3.8-flash', 'gemini-flash-latest', 'gemini-pro-latest')).grid(sticky='ew', pady=6)
        ttk.Label(body, text='金鑰不放進書籍專案。測試只送固定「連線測試。」\n清空後保存可移除本機金鑰；環境金鑰仍可用。', wraplength=450).grid(sticky='w', pady=12)
        actions = ttk.Frame(body)
        actions.grid(sticky='ew')
        self.save_button = ttk.Button(actions, text='保存設定', command=self.save)
        self.save_button.pack(side='left')
        self.test_button = ttk.Button(actions, text='保存並測試連線', command=self.test)
        self.test_button.pack(side='left', padx=8)
        ttk.Button(actions, text='關閉／取消', command=self.close).pack(side='right')
        self.status = ttk.Label(body, text=error, wraplength=450)
        self.status.grid(sticky='w', pady=16)
        self.protocol('WM_DELETE_WINDOW', self.close)

    def save(self):
        try:
            ProjectWorkflow.save_gemini_settings(self.key.get(), self.model.get())
            self.status.configure(text='已保存於目前 Windows 使用者設定。')
            return True
        except ProjectError as e:
            self.status.configure(text=str(e))
            return False

    def test(self):
        if self.job is not None or not self.save():
            return
        try:
            self.job = ProjectWorkflow.test_gemini_connection()
            self.test_button.configure(state='disabled')
            self.save_button.configure(state='disabled')
            self.status.configure(text='Gemini 連線測試中…可取消；等待連線釋放。')
            self.poll_token = self.after(60, self.poll)
        except ProjectError as e:
            self.status.configure(text=str(e))

    def poll(self):
        if self.poll_token is not None:
            self.after_cancel(self.poll_token)
            self.poll_token = None
        if self.job is None:
            return
        if not self.job.wait(0):
            self.poll_token = self.after(60, self.poll)
            return
        state = self.job.state
        self.job = None
        self.test_button.configure(state='normal')
        self.save_button.configure(state='normal')
        self.status.configure(text='連線成功，模型可產生校對候選。' if state['status'] == 'completed' else state['error'])
        if self.closing:
            self.close()

    def close(self):
        if self.job is not None:
            self.closing = True
            self.job.cancel()
            self.status.configure(text='取消中，正在等待連線釋放…')
            return
        self.key.set('')
        if self.poll_token is not None:
            self.after_cancel(self.poll_token)
        self.app.gemini_settings_dialog = None
        self.destroy()


class ReviewDialog(tk.Toplevel):
    original: tk.Text
    candidate: tk.Text
    def __init__(self, app, *, job=None):
        self.flow, self.batch_id = app.flow, app.batch_id
        reviews = self.flow.gemini_reviews(self.batch_id)
        super().__init__(app.root)
        self.app, self.job, self.closing = app, job, False
        self.poll_token = None
        self.reviews = reviews
        self.review = None
        self.title('Gemini 候選校對稿 · 原文與差異')
        self.geometry('940x650')
        self.minsize(740, 570)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        self.selector = ttk.Combobox(self, state='readonly')
        self.selector.grid(row=0, column=0, sticky='ew', padx=12, pady=8)
        self.selector.bind('<<ComboboxSelected>>', self.load)
        self.info = ttk.Label(self, wraplength=700)
        self.info.grid(row=1, column=0, sticky='ew', padx=12)
        self.paragraph = ttk.Combobox(self, state='readonly')
        self.paragraph.grid(row=2, column=0, sticky='ew', padx=12, pady=8)
        self.paragraph.bind('<<ComboboxSelected>>', self.show_paragraph)
        panes = ttk.Frame(self)
        panes.grid(row=3, column=0, sticky='nsew')
        panes.columnconfigure((0, 1), weight=1, uniform='compare')
        panes.rowconfigure(0, weight=1)
        for column, title, name in ((0, '送出時原文', 'original'), (1, 'Gemini 候選 · 標色為差異', 'candidate')):
            frame, text = text_pane(panes, title)
            frame.grid(row=0, column=column, sticky='nsew')
            text.tag_configure('diff', background='#f7dfad', foreground='#332b1b')
            setattr(self, name, text)
        self.notes = tk.Text(self, height=3, wrap='word', relief='flat', padx=12)
        self.notes.grid(row=4, column=0, sticky='ew', padx=12)
        actions = ttk.Frame(self, padding=12)
        actions.grid(row=5, column=0, sticky='ew')
        actions.columnconfigure((0, 1, 2), weight=1, uniform='actions')
        self.accept_button = ttk.Button(actions, text='採用本段', style='Primary.TButton', command=lambda: self.decide('accepted'))
        self.reject_button = ttk.Button(actions, text='拒絕本段', command=lambda: self.decide('rejected'))
        self.all_button = ttk.Button(actions, text='採用全部待確認段', command=lambda: self.decide('accepted', all_pending=True))
        self.undo_button = ttk.Button(actions, text='撤回本次全部採用', command=self.undo)
        self.close_button = ttk.Button(actions, text='關閉／取消', command=self.close)
        for row, col, button in ((0, 0, self.accept_button), (0, 1, self.reject_button), (0, 2, self.all_button),
                                  (1, 0, self.undo_button), (1, 2, self.close_button)):
            button.grid(row=row, column=col, sticky='ew', padx=3, pady=3)
        self.status = ttk.Label(self, wraplength=700)
        self.status.grid(row=6, column=0, sticky='ew', padx=12, pady=(0, 12))
        self.bind('<Configure>', lambda e: self.info.configure(wraplength=max(350, self.winfo_width()-40)))
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.refresh()
        if job is not None:
            self.status.configure(text='Gemini 校對中…原稿仍可人工編輯；取消後不採用結果。')
            self.poll_token = self.after(60, self.poll)

    def refresh(self):
        self.reviews = self.flow.gemini_reviews(self.batch_id)
        self.selector.configure(values=[f'{r["created_at"][:19]} · {r["model"]} · v{r["revision"]} · {r["status"]}' for r in self.reviews])
        if self.reviews:
            self.selector.current(len(self.reviews)-1)
        self.load()

    def load(self, _event=None):
        index = self.selector.current()
        self.review = self.reviews[index] if index >= 0 else None
        review = self.review
        if review:
            self.info.configure(text=f'Gemini · {review["model"]} · 原校對稿 v{review["revision"]} · '
                f'第 {review["start"]+1}～{review["end"]} 字元\n' +
                ('原稿版本已變更；請對照目前編輯稿，重新送出校對。舊候選不可覆蓋。' if review['stale'] else '只採用明確確認的段落；採用後須重新確認朗讀稿。'))
            labels = {'pending': '待確認', 'accepted': '已採用', 'rejected': '已拒絕'}
            self.paragraph.configure(values=[f'第 {i+1} 段 · {labels[p["decision"]]}' for i, p in enumerate(review['paragraphs'])])
            self.paragraph.current(0)
            self.app.fill(self.notes, '\n'.join(review['notes']) or '無額外疑點；仍請對照原文人工檢查。')
        else:
            self.info.configure(text='尚無保存的 Gemini 候選。可回工作台選取文字或整批送出。')
        self.show_paragraph()

    def show_paragraph(self, _event=None):
        enabled = self.review is not None and self.review['status'] == 'completed' and not self.review['stale'] and self.job is None
        for button in (self.accept_button, self.reject_button, self.all_button, self.undo_button):
            button.configure(state='normal' if enabled else 'disabled')
        if self.review is None:
            return
        part = self.review['paragraphs'][max(0, self.paragraph.current())]
        old, new = part['original'], part['candidate'] or ''
        self.app.fill(self.original, old)
        self.app.fill(self.candidate, new or self.review['error'])
        for tag, a, b, c, d in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
            if tag != 'equal':
                self.original.tag_add('diff', f'1.0+{a}c', f'1.0+{b}c')
                self.candidate.tag_add('diff', f'1.0+{c}c', f'1.0+{d}c')

    def poll(self):
        if self.poll_token is not None:
            self.after_cancel(self.poll_token)
            self.poll_token = None
        if self.job is None:
            return
        if not self.job.wait(0):
            self.poll_token = self.after(60, self.poll)
            return
        try:
            self.flow.finish_gemini_review(self.job)
            state = self.job.state
            self.job = None
            self.refresh()
            self.status.configure(text='候選已保存，尚未採用。' if state['status'] == 'completed' else state['error'])
            if self.closing:
                self.close()
        except ProjectError as e:
            self.status.configure(text=str(e) + ' 關閉時會重試保存。')
            if self.closing:
                if messagebox.askyesno('候選未能保存',
                        str(e) + '\n捨棄尚未保存的候選並關閉？原稿不會變更。\n選「否」可保留候選視窗。', parent=self):
                    self.flow.discard_gemini_review(self.job)
                    self.job = None
                    self.close()
                else:
                    self.closing = False

    def perform(self, operation):
        if self.review is None:
            return
        try:
            if self.app.flow is self.flow and self.app.batch_id == self.batch_id and self.app.dirty:
                raise ProjectError('目前有未存編輯；請先保存後比較版本，再重新送出校對。')
            index = self.selector.current()
            paragraph = self.paragraph.current()
            operation()
            if self.app.flow is self.flow and self.app.batch_id == self.batch_id:
                self.app.refresh()
            self.refresh()
            self.selector.current(index)
            self.load()
            self.paragraph.current(paragraph)
            self.show_paragraph()
            self.status.configure(text='已保存決定；文字變更後須重新確認朗讀稿。')
        except ProjectError as e:
            self.status.configure(text=str(e))

    def decide(self, decision, all_pending=False):
        if self.review is None:
            return
        review_id = self.review['id']
        self.perform(lambda: self.flow.decide_gemini(self.batch_id, review_id,
                     None if all_pending else self.paragraph.current(), decision))

    def undo(self):
        if self.review is None:
            return
        review_id = self.review['id']
        self.perform(lambda: self.flow.undo_gemini(self.batch_id, review_id))

    def close(self):
        if self.job is not None:
            self.closing = True
            self.job.cancel()
            self.status.configure(text='取消中，正在等待連線釋放並保存狀態…')
            if self.job.wait(0):
                self.poll()
            return
        self.app.gemini_dialog = None
        if self.poll_token is not None:
            self.after_cancel(self.poll_token)
        self.destroy()
