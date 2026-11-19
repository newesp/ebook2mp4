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
    from .ui_controls import AutoHideScrollbar
    scroll = AutoHideScrollbar(frame, command=text.yview)
    scroll.grid(row=1, column=1, sticky='ns')
    text.configure(yscrollcommand=scroll.set)
    if not editable:
        text.configure(state='disabled')
    return frame, text


from .manuscript_desktop import ManuscriptWorkspace


class Workbench(ManuscriptWorkspace):
    def __init__(self, root, *, restore_last_project=False):
        super().__init__(root, padding=16)
        self.root = root
        self.remember_last_project = restore_last_project
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
        from .manuscript_drop import FileDrop
        self.file_drop = FileDrop(self)
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.bind('<Control-s>', lambda e: self.save())
        self.root.bind('<Control-f>', self.focus_search)
        self.root.bind('<F6>', self.toggle_focus)
        self.refresh()

    def restore_project(self) -> None:
        from .app_session import last_project
        try:
            path = last_project()
            if path is None:
                return
            flow = ProjectWorkflow.open(path)
            self.flow = flow
            self.batch_id = None
            self.step = 2 if flow.state['batches'] else 1
            self.refresh()
            self.status.configure(text='已自動載入上次專案。')
            self.after_idle(lambda: self.notify('已載入上次專案。', kind='info') if not self._closing else None)
        except ProjectError as error:
            self.status.configure(text='無法自動載入上次專案。'+str(error)+
                                  ' 請從「專案 → 開啟專案」重新選擇。')

    def remember_project(self) -> None:
        if not self.remember_last_project or self.flow is None:
            return
        from .app_session import remember_project
        try:
            remember_project(self.flow.root)
        except ProjectError as error:
            self.status.configure(text=str(error))
            self.notify(str(error), kind='error')

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

    def _legacy_source_info(self):
        batch = next((b for b in self.flow.state['batches'] if b['id'] == self.batch_id), None) if self.flow else None
        detail = f'專案位置：{self.flow.root}' if self.flow else '尚未建立書籍專案。'
        if batch:
            source = batch['source']
            detail += f'\n來源：{source["original_name"]}\n大小：{source["size"]:,} 位元組\n'
            detail += self.source_meta.cget('text')
        messagebox.showinfo('專案與來源資訊', detail, parent=self.root)

    def batch_label(self, batch):
        source = batch.get('pdf', {})
        scope = f'PDF {source["start"]}–{source["end"]}' if source else 'TXT'
        return f'{batch["name"]}\n{scope} · {self.batch_status(batch)}'

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

    @staticmethod
    def fill(widget, content, editable=False):
        widget.configure(state='normal')
        widget.delete('1.0', 'end')
        widget.insert('1.0', content)
        if not editable:
            widget.configure(state='disabled')

    def _refresh_records(self, *, keep_step=False):
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
        if self.step == 1 and batches and not keep_step:
            self.step = 2
        self.render_step()
        self.status.configure(text='所有書稿資料保存在本機。' if not self.flow else '已載入專案 · 原始來源檔不會被改寫')

    def update_source_metadata(self):
        if not self.flow or not self.batch_id:
            return
        batch = next(b for b in self.flow.state['batches'] if b['id'] == self.batch_id)
        source = batch['source']
        self.source_heading.configure(text='PDF 原稿' if batch['kind'] == 'pdf' else 'TXT 原稿')
        if batch['kind'] == 'pdf':
            pdf = batch['pdf']
            if self.source_visible:
                self.source_heading.configure(text='PDF 原稿')
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
            self.refresh(keep_step=True)
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
        self.status.remember(str(error))

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
            self.remember_project()
        except ProjectError as e:
            self.report(e)

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

    def open_folder(self):
        import os
        if self.flow:
            try:
                os.startfile(self.flow.root)
            except OSError:
                self.report(ProjectError('無法開啟檔案總管。可從左側複製專案位置後手動開啟。'))

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

    def batch_video(self):
        if not self.flow or not self.batch_id:
            return
        self.step = 4
        self.render_step()
        self.production.show('batch_video')

    def total_video(self):
        if not self.flow:
            return
        self.step = 4
        self.render_step()
        self.production.show('video')

def make_app(*, restore_last_project=False):
    root = tk.Tk()
    from .window_layout import install_dialog_placement
    install_dialog_placement(root)
    root.geometry('1360x820')
    root.minsize(900, 640)
    root.configure(background=BG)
    root.option_add('*Font', ('Microsoft JhengHei', 10))
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('.', font=('Microsoft JhengHei', 10), background=BG, foreground=INK)
    style.configure('TButton', padding=(10, 7), background='#ffffff', bordercolor='#c7d2c6')
    style.configure('TMenubutton', padding=(10, 7), background='#ffffff')
    style.configure('Workspace.TButton', padding=(10, 7))
    style.configure('WorkspaceActive.TButton', padding=(10, 7), background='#e2ebdf', foreground='#254f32')
    style.map('WorkspaceActive.TButton', background=[('active', '#d5e3d1')])
    style.configure('Workspace.TEntry', padding=(8, 8))
    style.configure('Workspace.TSpinbox', padding=(8, 8))
    style.configure('Workspace.TCombobox', padding=(8, 8))
    style.configure('Workspace.TMenubutton', padding=(10, 7))
    style.configure('Tool.TFrame', background='#ffffff', bordercolor='#dfe5dd')
    style.configure('Tool.TLabel', background='#ffffff')
    style.configure('Tool.Heading.TLabel', background='#ffffff')
    style.configure('Compact.TButton', padding=(10, 3))
    style.configure('CompactActive.TButton', padding=(10, 3), background=GREEN, foreground='#ffffff')
    style.configure('Treeview', background='#ffffff', fieldbackground='#ffffff', rowheight=25)
    style.configure('Workspace.Treeview', rowheight=40)
    style.map('Treeview', background=[('selected', GREEN)], foreground=[('selected', '#ffffff')])
    style.configure('Manuscript.Treeview', rowheight=68)
    style.map('Manuscript.Treeview', background=[('selected', '#e7efe4')], foreground=[('selected', INK)])
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
    app = Workbench(root, restore_last_project=restore_last_project)
    if restore_last_project:
        app.restore_project()
    return root, app


def main():
    root, _app = make_app(restore_last_project=True)
    root.mainloop()
