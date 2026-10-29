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
        self.bind('<Escape>', lambda e: self.close())

    def save(self, *, announce=True):
        try:
            ProjectWorkflow.save_gemini_settings(self.key.get(), self.model.get())
            self.status.configure(text='已保存於目前 Windows 使用者設定。')
            if announce:
                self.app.notify('Gemini 設定已儲存。', owner=self)
            return True
        except ProjectError as e:
            self.status.configure(text=str(e))
            self.app.notify(str(e), owner=self, kind='error')
            return False

    def test(self):
        if self.job is not None or not self.save(announce=False):
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
        if not self.closing:
            self.app.notify('Gemini 連線測試成功。' if state['status'] == 'completed' else state['error'],
                            owner=self, kind='success' if state['status'] == 'completed' else 'error')
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
        self.save_error = ''
        self.operation_error = ''
        self.details_open = False
        self.candidate_edits: dict[tuple[str, int], str] = {}
        self.displayed_candidate: tuple[str, int] | None = None
        self.title('Gemini 候選校對稿 · 原文與差異')
        preferences = getattr(app, '_gemini_review_window', {})
        self.normal_geometry = preferences.get('geometry', '940x650')
        self.geometry(self.normal_geometry)
        self.minsize(740, 570)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        header = ttk.Frame(self, padding=(12, 8, 12, 0))
        header.grid(row=0, column=0, sticky='ew')
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text='校對記錄').grid(row=0, column=0, padx=(0, 8))
        self.selector = ttk.Combobox(header, state='readonly', width=28)
        self.selector.grid(row=0, column=1, sticky='ew')
        self.selector.bind('<<ComboboxSelected>>', self.load)
        progress_frame = ttk.Frame(header)
        progress_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(6, 0))
        progress_frame.columnconfigure(0, weight=1)
        self.progress = ttk.Label(progress_frame, foreground='#58695f')
        self.progress.grid(row=0, column=0, columnspan=3, sticky='w')
        self.retry_button = ttk.Button(progress_frame, text='只重試失敗', command=lambda: self.retry(True))
        self.retry_button.grid(row=1, column=0, sticky='w', pady=4)
        self.resume_button = ttk.Button(progress_frame, text='繼續未完成', command=lambda: self.retry(False))
        self.resume_button.grid(row=1, column=1, padx=6)
        self.cancel_button = ttk.Button(progress_frame, text='取消並保留', command=self.cancel)
        self.cancel_button.grid(row=1, column=2)

        self.info = ttk.Label(self, wraplength=700, foreground='#58695f')
        self.info.grid(row=1, column=0, sticky='ew', padx=12, pady=(4, 0))
        navigation = ttk.Frame(self, padding=(12, 6))
        navigation.grid(row=2, column=0, sticky='ew')
        navigation.columnconfigure(1, weight=1)
        self.previous_button = ttk.Button(navigation, text='上一段', command=lambda: self.change_paragraph(-1))
        self.previous_button.grid(row=0, column=0)
        self.paragraph = ttk.Combobox(navigation, state='readonly', width=15)
        self.paragraph.grid(row=0, column=1, sticky='ew', padx=6)
        self.paragraph.bind('<<ComboboxSelected>>', self.show_paragraph)
        self.next_button = ttk.Button(navigation, text='下一段', command=lambda: self.change_paragraph(1))
        self.next_button.grid(row=0, column=2)
        self.pending_button = ttk.Button(navigation, text='下一待確認', command=self.next_pending)
        self.pending_button.grid(row=0, column=3, padx=(6, 0))
        self.counts = ttk.Label(navigation, foreground='#58695f')
        self.counts.grid(row=1, column=0, columnspan=4, sticky='w', pady=(4, 0))
        self.panes = ttk.Panedwindow(self, orient='horizontal')
        self.panes.grid(row=3, column=0, sticky='nsew')
        for title, name in (('送出時原文 · 唯讀', 'original'), ('候選文字 · 可編輯，標色為差異', 'candidate')):
            frame, text = text_pane(self.panes, title)
            self.panes.add(frame, weight=1)
            text.tag_configure('diff', background='#f7dfad', foreground='#332b1b')
            setattr(self, name, text)
        self.candidate.configure(undo=True, autoseparators=True)
        self.candidate.bind('<<Modified>>', self.candidate_modified)
        detail = ttk.Frame(self, padding=(12, 0))
        detail.grid(row=4, column=0, sticky='ew')
        detail.columnconfigure(0, weight=1)
        self.notes_summary = ttk.Label(detail, wraplength=570)
        self.notes_summary.grid(row=0, column=0, sticky='ew')
        self.details_button = ttk.Button(detail, text='疑點與規則', command=self.toggle_details)
        self.details_button.grid(row=0, column=1, padx=(8, 0))
        self.notes_frame = ttk.Frame(detail)
        self.notes_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=4)
        self.notes_frame.columnconfigure(0, weight=1)
        self.notes = tk.Text(self.notes_frame, height=4, wrap='word', relief='flat', padx=8,
                             font=('Microsoft JhengHei', 10), bg='#fffef9', fg='#263d34')
        self.notes.grid(row=0, column=0, sticky='ew')
        notes_scroll = ttk.Scrollbar(self.notes_frame, command=self.notes.yview)
        notes_scroll.grid(row=0, column=1, sticky='ns')
        self.notes.configure(yscrollcommand=notes_scroll.set)
        self.notes_frame.grid_remove()
        footer = ttk.Frame(self, padding=(12, 6, 12, 8))
        footer.grid(row=5, column=0, sticky='ew')
        footer.columnconfigure(0, weight=1)
        self.blocking = ttk.Label(footer, wraplength=700, foreground='#963b32')
        self.blocking.grid(row=0, column=0, sticky='ew')
        self.status = ttk.Label(footer, wraplength=700)
        self.status.grid(row=1, column=0, sticky='ew', pady=(2, 6))
        actions = ttk.Frame(footer)
        actions.grid(row=2, column=0, sticky='ew')
        actions.columnconfigure(1, weight=1)
        self.accept_button = ttk.Button(actions, text='採用本段', style='Primary.TButton', command=lambda: self.decide('accepted'))
        self.reject_button = ttk.Button(actions, text='拒絕本段', command=lambda: self.decide('rejected'))
        # Keep the existing invokable command widgets for callers and UI tests.
        # Their visible entry points are the explicitly named batch menu commands.
        self.all_button = ttk.Button(actions, text='採用全部待確認段', command=lambda: self.decide('accepted', all_pending=True))
        self.undo_button = ttk.Button(actions, text='撤回本次全部採用', command=self.undo)
        self.batch_button = ttk.Menubutton(actions, text='批次操作')
        self.batch_menu = tk.Menu(self.batch_button, tearoff=False)
        self.batch_menu.add_command(label='採用全部待確認段', command=self.all_button.invoke)
        self.batch_menu.add_command(label='撤回本次全部採用', command=self.undo_button.invoke)
        self.batch_button.configure(menu=self.batch_menu)
        self.batch_button.grid(row=0, column=0, sticky='w')
        self.save_candidate_button = ttk.Button(actions, text='保存候選修改', command=self.save_candidate_edits)
        self.save_candidate_button.grid(row=0, column=1, sticky='w', padx=6)
        self.close_button = ttk.Button(actions, text='關閉／取消', command=self.close)
        self.close_button.grid(row=0, column=2, padx=3)
        self.reject_button.grid(row=0, column=3, padx=3)
        self.accept_button.grid(row=0, column=4, padx=(3, 0))
        self.bind('<Configure>', self.resize_text)
        self.bind('<FocusIn>', lambda e: self.update_availability())
        self.bind('<Escape>', lambda e: self.close())
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.editor_binding = self.app.editor.bind('<<Modified>>', lambda e: self.update_availability(), add='+')
        self.bind('<Destroy>', self.destroyed, add='+')
        self.refresh()
        if preferences.get('maximized', True):
            try:
                self.state('zoomed')
            except tk.TclError:
                pass  # Keep standard resizable window controls on non-Windows Tk.
        if job is not None:
            self.status.configure(text='Gemini 校對中…原稿仍可人工編輯；成功範圍會保存，取消後可續作。')
            self.poll_token = self.after(60, self.poll)

    def resize_text(self, event):
        if event.widget is not self:
            return
        if self.state() == 'normal':
            # Remember the restored size only; do not restore stale screen coordinates.
            self.normal_geometry = f'{self.winfo_width()}x{self.winfo_height()}'
        width = max(320, self.winfo_width() - 24)
        for label in (self.info, self.blocking, self.status):
            label.configure(wraplength=width)
        self.notes_summary.configure(wraplength=max(200, width - 135))

    def geometry(self, new_geometry=None):
        if new_geometry and self.state() == 'zoomed':
            self.state('normal')
        return super().geometry(new_geometry)

    def toggle_details(self):
        self.details_open = not self.details_open
        if self.details_open:
            self.notes_frame.grid()
        else:
            self.notes_frame.grid_remove()
        self.details_button.configure(text='收合疑點與規則' if self.details_open else '疑點與規則')

    def change_paragraph(self, offset):
        if not self.review:
            return
        index = self.paragraph.current() + offset
        if 0 <= index < len(self.review['paragraphs']):
            self.paragraph.current(index)
            self.show_paragraph()

    def next_pending(self):
        if not self.review:
            return
        parts = self.review['paragraphs']
        current = self.paragraph.current()
        for offset in range(1, len(parts) + 1):
            index = (current + offset) % len(parts)
            if parts[index]['decision'] == 'pending' and parts[index]['candidate'] is not None:
                self.paragraph.current(index)
                self.show_paragraph()
                return

    def update_availability(self):
        review = self.review
        warning = []
        batch = next((b for b in self.flow.state['batches'] if b['id'] == self.batch_id), None)
        stale = bool(review and (batch is None or review['expected'] != batch['draft']
                                 or review['expected_revision'] != batch['revision']))
        dirty = self.app.flow is self.flow and self.app.batch_id == self.batch_id and self.app.dirty
        if self.save_error:
            warning.append(self.save_error)
        if stale:
            warning.append('原稿版本已變更；舊候選不可覆蓋，請重新送出校對。')
        if dirty:
            warning.append('目前有未存編輯；請先保存後比較版本，再重新送出校對。')
        if review and review['status'] != 'completed':
            warning.append(review['error'] or '本次尚無完整有效候選，原稿未變更。')
        if self.operation_error and self.operation_error not in warning:
            warning.append(self.operation_error)
        self.blocking.configure(text='\n'.join(warning))
        if warning:
            self.blocking.grid()
        else:
            self.blocking.grid_remove()
        enabled = bool(review and not stale and not dirty and self.job is None and not self.save_error)
        parts = review['paragraphs'] if review else []
        current = self.paragraph.current()
        has_candidate = bool(parts and any(p['candidate'] is not None for p in parts))
        selected = bool(0 <= current < len(parts) and parts[current]['candidate'] is not None)
        editable = enabled and selected
        self.candidate.configure(state='normal' if editable else 'disabled')
        self.save_candidate_button.configure(state='normal' if self.candidate_edits and self.job is None else 'disabled')
        for button in (self.accept_button, self.reject_button):
            button.configure(state='normal' if enabled and selected else 'disabled')
        for action in (self.all_button, self.undo_button, self.batch_button):
            action.configure(state='normal' if enabled and has_candidate else 'disabled')
        for index in (0, 1):
            self.batch_menu.entryconfigure(index, state='normal' if enabled and has_candidate else 'disabled')
        requests = review.get('requests', []) if review else []
        failed = any(r['status'] == 'failed' for r in requests)
        unfinished = any(r['status'] != 'completed' for r in requests)
        self.retry_button.configure(state='normal' if enabled and failed else 'disabled')
        self.resume_button.configure(state='normal' if enabled and unfinished else 'disabled')
        self.cancel_button.configure(state='normal' if self.job is not None and not self.closing else 'disabled')
        self.selector.configure(state='disabled' if self.job is not None else 'readonly')

    def retry(self, failed_only):
        if self.review is None or self.job is not None:
            return
        if not self.save_candidate_edits(announce=False):
            return
        try:
            if self.app.flow is self.flow and self.app.batch_id == self.batch_id and self.app.dirty:
                raise ProjectError('目前有未存編輯；請先保存後比較版本。')
            self.job = self.flow.start_gemini_retry(self.batch_id, self.review['id'], failed_only=failed_only)
            self.operation_error = ''
            self.status.configure(text='正在續作；成功候選及既有決定保留，原稿不會自動變更。')
            self.poll()
        except ProjectError as exc:
            self.operation_error = str(exc)
            self.update_availability()

    def cancel(self):
        if self.job is not None:
            self.job.cancel()
            self.status.configure(text='取消中，等待目前連線釋放；成功候選保留。')


    def refresh(self, review_id=None):
        if self.job is None:
            self.reviews = self.flow.gemini_reviews(self.batch_id)
        else:
            live = self.job.snapshot
            self.reviews = [live if r['id'] == live['id'] else r for r in self.reviews]
        states = dict(completed='全部完成', partial='部分成功', interrupted='未完成', failed='失敗', cancelled='已取消', running='執行中')
        self.selector.configure(values=[f'{r["created_at"][:19].replace("T", " ")} · {r["model"]} · v{r["revision"]} · '
                                       f'{states.get(r["status"], r["status"])}' for r in self.reviews])
        if self.reviews:
            selected_id = self.job.snapshot['id'] if self.job is not None else review_id
            index = next((i for i, r in enumerate(self.reviews) if r['id'] == selected_id), len(self.reviews)-1)
            self.selector.current(index)
        self.load()

    def load(self, _event=None):
        index = self.selector.current()
        self.review = self.reviews[index] if index >= 0 else None
        review = self.review
        if review:
            from .proofreading import describe
            self.info.configure(text=f'Gemini · {review["model"]} · 原校對稿 v{review["revision"]} · '
                f'第 {review["start"]+1}～{review["end"]} 字元')
            labels = {'pending': '待確認', 'accepted': '已採用', 'rejected': '已拒絕'}
            request_states = dict(completed='完成', failed='失敗', cancelled='已取消', pending='未完成', running='執行中')
            requests = review.get('requests', [])
            states = [r['status'] for r in requests]
            self.progress.configure(text=f'請求 {len(requests)} · 完成 {states.count("completed")} · 失敗 {states.count("failed")} · '
                f'未完成 {len(states)-states.count("completed")-states.count("failed")}')
            values = []
            for i, part in enumerate(review['paragraphs']):
                request = next((r for r in requests if r['first'] <= i < r['last']), None)
                label = labels[part['decision']] if part['candidate'] is not None else request_states.get(request['status'], '未完成') if request else '未完成'
                values.append(f'第 {i+1} 段 · {label} · {part["start"]+1}～{part["end"]} 字元')
            self.paragraph.configure(values=values)
            if review['paragraphs']:
                self.paragraph.current(0)
            notes = review['notes']
            first_note = notes[0].replace('\n', ' ') if notes else ''
            summary = f'本次疑點 {len(notes)} 項：{first_note[:65]}' + ('…' if len(first_note) > 65 else '') if notes else '無額外疑點；仍請對照原文人工檢查。'
            self.notes_summary.configure(text=summary)
            details = '\n'.join(notes) or '無額外疑點。'
            if 'normalization' in review:
                details += '\n\n' + describe(review['normalization'])
            if requests:
                details += '\n\n請求範圍（來源字元，含原有分隔空白）：\n' + '\n'.join(
                    f'{i+1}. {r["start"]+1}～{r["end"]} · {request_states[r["status"]]} · 已嘗試 {r["attempts"]} 次'
                    + (f' · {r["error"]}' if r['error'] else '') for i, r in enumerate(requests))
            details += '\n\n只採用成功且明確確認的段落；採用全部只處理成功待確認段，採用後須重新確認朗讀稿。'
            self.app.fill(self.notes, details)
        else:
            self.progress.configure(text='尚無分段進度。')
            self.info.configure(text='尚無保存的 Gemini 候選。可回工作台選取文字或整批送出。')
            self.paragraph.configure(values=[])
            self.paragraph.set('')
            self.notes_summary.configure(text='候選完成後可逐段檢查疑點與差異。')
            self.app.fill(self.notes, '')
        self.show_paragraph()

    def show_paragraph(self, _event=None):
        self.capture_candidate_edit()
        self.displayed_candidate = None
        self.update_availability()
        parts = self.review['paragraphs'] if self.review else []
        current = max(0, self.paragraph.current())
        decisions = [p['decision'] for p in parts if p['candidate'] is not None]
        self.counts.configure(text=f'第 {current+1 if parts else 0}／{len(parts)} 段 · 待確認 {decisions.count("pending")} · '
                              f'已採用 {decisions.count("accepted")} · 已拒絕 {decisions.count("rejected")}')
        self.previous_button.configure(state='normal' if current > 0 else 'disabled')
        self.next_button.configure(state='normal' if current + 1 < len(parts) else 'disabled')
        self.pending_button.configure(state='normal' if 'pending' in decisions else 'disabled')
        if not parts:
            self.app.fill(self.original, '')
            self.app.fill(self.candidate, '')
            return
        part = parts[current]
        assert self.review is not None
        key = (self.review['id'], current)
        old, new = part['original'], self.candidate_edits.get(key, part['candidate']) or ''
        self.app.fill(self.original, old)
        review = self.review or {}
        request = next((r for r in review.get('requests', []) if r['first'] <= current < r['last']), None)
        content = new if part['candidate'] is not None else (
            request['error'] or '本範圍尚未完成，可續作。' if request else review.get('error', ''))
        self.app.fill(self.candidate, content)
        if part['candidate'] is None:
            self.candidate.edit_modified(False)
            return
        self.displayed_candidate = key
        self.candidate.edit_reset()
        self.candidate.edit_modified(False)
        self.update_availability()
        self.highlight_candidate(old, new)

    def highlight_candidate(self, old, new):
        self.original.tag_remove('diff', '1.0', 'end')
        self.candidate.tag_remove('diff', '1.0', 'end')
        for tag, a, b, c, d in difflib.SequenceMatcher(None, old, new, autojunk=len(old) > 2000).get_opcodes():
            if tag != 'equal':
                self.original.tag_add('diff', f'1.0+{a}c', f'1.0+{b}c')
                self.candidate.tag_add('diff', f'1.0+{c}c', f'1.0+{d}c')

    def capture_candidate_edit(self):
        key = self.displayed_candidate
        if key is None:
            return
        review = next(r for r in self.reviews if r['id'] == key[0])
        text = self.candidate.get('1.0', 'end-1c')
        if text != review['paragraphs'][key[1]]['candidate']:
            self.candidate_edits[key] = text
        else:
            self.candidate_edits.pop(key, None)

    def candidate_modified(self, _event=None):
        if not self.candidate.edit_modified():
            return
        self.capture_candidate_edit()
        self.candidate.edit_modified(False)
        if self.displayed_candidate is not None:
            review = next(r for r in self.reviews if r['id'] == self.displayed_candidate[0])
            self.highlight_candidate(review['paragraphs'][self.displayed_candidate[1]]['original'],
                                     self.candidate.get('1.0', 'end-1c'))
            self.status.configure(text='候選有未存修改；可保存候選，採用或關閉時也會保存。保存候選尚不改原稿。')
        self.update_availability()

    def save_candidate_edits(self, *, announce=True):
        self.capture_candidate_edit()
        had_edits = bool(self.candidate_edits)
        try:
            for review_id in dict.fromkeys(key[0] for key in self.candidate_edits):
                edits = {index: text for (rid, index), text in self.candidate_edits.items() if rid == review_id}
                self.flow.edit_gemini_candidates(self.batch_id, review_id, edits)
                review = next(r for r in self.reviews if r['id'] == review_id)
                for index, text in edits.items():
                    if review['paragraphs'][index]['decision'] == 'accepted':
                        review['paragraphs'][index]['decision'] = 'pending'
                    review['paragraphs'][index]['candidate'] = text
                    self.candidate_edits.pop((review_id, index))
            if had_edits:
                paragraph = self.paragraph.current()
                self.load()
                self.paragraph.current(paragraph)
                self.show_paragraph()
            self.operation_error = ''
            self.status.configure(text='候選修改已保存；採用後才會更新校對稿。')
            if announce and had_edits:
                self.app.notify('候選修改已儲存，尚未套用到校對稿。', owner=self)
            self.update_availability()
            return True
        except ProjectError as exc:
            self.operation_error = str(exc) + ' 候選修改仍保留於視窗，請修正後重試保存。'
            self.update_availability()
            self.status.configure(text=self.operation_error)
            self.app.notify(str(exc), owner=self, kind='error')
            return False

    def poll(self):
        if self.poll_token is not None:
            self.after_cancel(self.poll_token)
            self.poll_token = None
        if self.job is None:
            return
        if not self.job.wait(0):
            signature = [(r['status'], r['attempts']) for r in self.job.state['requests']]
            if signature != getattr(self, '_live_signature', None):
                self._live_signature = signature
                current = self.paragraph.current()
                self.refresh()
                if current >= 0:
                    self.paragraph.current(current)
                    self.show_paragraph()
            self.poll_token = self.after(60, self.poll)
            return
        try:
            paragraph = self.paragraph.current()
            review_id = self.flow.finish_gemini_review(self.job)
            self.job = None
            self.save_error = ''
            self.refresh(review_id)
            if paragraph >= 0:
                self.paragraph.current(paragraph)
                self.show_paragraph()
            saved = next(r for r in self.reviews if r['id'] == review_id)
            self.status.configure(text='候選已保存，尚未採用。' if saved['status'] == 'completed' else saved['error'])
            if not self.closing:
                self.app.notify('Gemini 候選已儲存，尚未採用。' if saved['status'] == 'completed' else saved['error'],
                                owner=self, kind='success' if saved['status'] == 'completed' else 'warning')
            if self.closing:
                self.close()
        except ProjectError as e:
            self.save_error = str(e) + ' 候選尚未保存；關閉時會重試。'
            self.update_availability()
            self.status.configure(text=str(e) + ' 關閉時會重試保存。')
            if self.closing:
                if messagebox.askyesno('候選未能保存',
                        str(e) + '\n捨棄尚未保存的候選並關閉？原稿不會變更。\n選「否」可保留候選視窗。', parent=self):
                    self.flow.discard_gemini_review(self.job)
                    self.job = None
                    self.close()
                else:
                    self.closing = False

    def perform(self, operation, success='已儲存決定；文字變更後須重新確認朗讀稿。', summary=None):
        if self.review is None:
            return
        if not self.save_candidate_edits(announce=False):
            return
        try:
            if self.app.flow is self.flow and self.app.batch_id == self.batch_id and self.app.dirty:
                raise ProjectError('目前有未存編輯；請先保存後比較版本，再重新送出校對。')
            index = self.selector.current()
            paragraph = self.paragraph.current()
            operation()
            self.operation_error = ''
            if self.app.flow is self.flow and self.app.batch_id == self.batch_id:
                self.app.refresh()
            self.refresh()
            self.selector.current(index)
            self.load()
            self.paragraph.current(paragraph)
            self.show_paragraph()
            self.status.configure(text=success)
            self.app.notify(summary or success, owner=self, detail=success)
        except ProjectError as e:
            self.operation_error = str(e)
            self.update_availability()
            self.status.configure(text=str(e))
            self.app.notify(str(e), owner=self, kind='error')

    def decide(self, decision, all_pending=False):
        if self.review is None:
            return
        review_id = self.review['id']
        if decision == 'accepted':
            success = ('已儲存並採用全部待確認段。' if all_pending else '已儲存並採用本段。')
            success += '可繼續編輯候選，再次採用才更新校對稿。'
        else:
            success = '已儲存：本段已拒絕。'
        self.perform(lambda: self.flow.decide_gemini(self.batch_id, review_id,
                     None if all_pending else self.paragraph.current(), decision),
                     success, '已儲存並採用全部待確認段。' if all_pending else
                     f'已儲存並採用第 {self.paragraph.current()+1} 段。' if decision == 'accepted' else
                     f'已儲存並拒絕第 {self.paragraph.current()+1} 段。')

    def undo(self):
        if self.review is None:
            return
        review_id = self.review['id']
        self.perform(lambda: self.flow.undo_gemini(self.batch_id, review_id),
                     '已撤回本次全部採用並儲存；校對稿已恢復送出前版本。', '已撤回本次全部採用並儲存。')

    def close(self):
        if self.job is not None:
            self.closing = True
            self.job.cancel()
            self.status.configure(text='取消中，正在等待連線釋放並保存狀態…')
            if self.job.wait(0):
                self.poll()
            return
        self.app._gemini_review_window = dict(geometry=self.normal_geometry, maximized=self.state() == 'zoomed')
        if not self.save_candidate_edits(announce=False):
            if not messagebox.askyesno('候選修改尚未保存', self.operation_error +
                    '\n要捨棄尚未保存的候選修改並關閉嗎？', parent=self):
                return
        self.app.gemini_dialog = None
        if self.poll_token is not None:
            self.after_cancel(self.poll_token)
        self.destroy()

    def destroyed(self, event):
        if event.widget is self:
            try:
                self.app.editor.unbind('<<Modified>>', self.editor_binding)
            except tk.TclError:
                pass
