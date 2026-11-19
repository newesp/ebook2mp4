"""Single-window manuscript workspace. Background jobs belong to this workspace."""
from concurrent.futures import ThreadPoolExecutor
from difflib import unified_diff
from functools import partial
from pathlib import Path
from typing import Any, TYPE_CHECKING
import tkinter as tk
from tkinter import ttk, filedialog

from .workflow import ProjectError, ProjectWorkflow




class ManuscriptWorkspace(ttk.Frame):
    # Host context is supplied by Workbench before building the embedded surface.
    root: tk.Tk
    flow: Any
    batch_id: Any
    production: Any
    workspace_job: Any
    connection_job: Any
    source_job: Any
    source_future: Any
    source_pending: Any
    import_preview: Any
    source_image: Any
    display_image: Any
    loaded_identity: Any
    workspace_review: Any
    source_selection: Any
    source_sash: Any
    autosave_token: Any
    workspace_timer: Any
    retry_baseline: Any
    focus_mode: bool
    tool_fit_token: str | None = None
    resize_token: str | None = None
    close_timer: str | None = None
    source_region_start: tuple[int, int] | None = None
    if TYPE_CHECKING:
        def __getattr__(self, name: str) -> Any: ...  # Shared Workbench commands.

    def _build(self):
        from .desktop import text_pane
        from .ui_controls import MenuAction, CellTooltip, command_menu
        self.workspace_job = self.connection_job = self.source_job = None
        self.workspace_review = None
        self.allow_partial = False
        self.autosave_token = None
        self.workspace_timer = None
        self.source_future = None
        self.source_pending = None
        self.import_preview = None
        self.source_selection = None
        self.source_visible = True
        self.narrow_source = False
        self.source_sash = None
        self.loaded_identity = None
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='Manuscript source')
        from .desktop_shell import DesktopShell
        self.shell = DesktopShell(self, dict(
            manuscript=partial(self.show_step, 1), production=partial(self.show_step, 4),
            messages=self.show_messages, create=self.create, open=self.open,
            folder=self.open_folder, source_info=self.show_source_info,
            toggle_files=self.toggle_focus, import_txt=self.import_txt, import_pdf=self.import_pdf,
            rename=self.rename_batch, move_up=partial(self.move_batch, -1),
            move_down=partial(self.move_batch, 1), remove_pdf=self.remove_pdf,
            select_batch=self.select_batch, batch_help=self.batch_status_help,
            next=self.publish_or_continue))
        self.shell.install_legacy_handles(self)
        center = self.center
        self.metadata = ttk.Frame(center)  # Compatibility only; no extra toolbar band.
        self.source_meta = ttk.Label(center, width=1)
        self.panes = panes = ttk.Panedwindow(center, orient='horizontal')
        panes.grid(row=2, column=0, sticky='nsew')
        panes.bind('<ButtonRelease-1>', self.remember_source_sash)
        self.source_frame = ttk.Frame(panes)
        self.source_frame.rowconfigure(1, weight=1)
        self.source_frame.columnconfigure(0, weight=1)
        self.source_nav = source_nav = ttk.Frame(self.source_frame)
        source_nav.grid(row=0, column=0, sticky='ew')
        source_nav.columnconfigure(0, weight=1)
        self.source_title = ttk.Frame(source_nav)
        self.source_title.grid(row=0, column=0, sticky='w')
        self.source_reopen = ttk.Button(self.source_title, text='›', width=2, command=self.toggle_focus, style='Workspace.TButton')
        self.source_heading = ttk.Label(self.source_title, text='原稿', style='Heading.TLabel')
        self.source_heading.pack(side='left')
        self.source_return = ttk.Button(self.source_title, text='文稿', command=self.toggle_source, style='Workspace.TButton')
        self.pdf_controls = ttk.Frame(source_nav)
        self.pdf_controls.grid(row=0, column=1, sticky='e')
        self.pdf_previous = ttk.Button(self.pdf_controls, text='‹', width=2, command=partial(self.change_source_page, -1), style='Workspace.TButton')
        self.pdf_previous.pack(side='left')
        self.page_number = tk.StringVar(value='1')
        self.page_entry = ttk.Entry(self.pdf_controls, textvariable=self.page_number, width=4)
        self.page_entry.pack(side='left')
        self.page_entry.bind('<Return>', lambda e: self.render_source_page())
        self.page_total = ttk.Label(self.pdf_controls, text='')
        self.page_total.pack(side='left')
        self.pdf_next = ttk.Button(self.pdf_controls, text='›', width=2, command=partial(self.change_source_page, 1), style='Workspace.TButton')
        self.pdf_next.pack(side='left')
        self.source_zoom = tk.StringVar(value='符合頁寬')
        self.zoom_control = ttk.Combobox(self.pdf_controls, textvariable=self.source_zoom, state='readonly', width=10,
            values=('符合頁寬', '75%', '100%', '125%', '150%', '200%'))
        self.zoom_control.pack(side='left', padx=4)
        self.zoom_control.bind('<<ComboboxSelected>>', lambda e: self.draw_source_image())
        self.source_control, self.source_menu = command_menu(self.pdf_controls, '來源')
        self.source_control.configure(width=4)
        self.source_control.pack(side='left')
        self.open_pdf_action = MenuAction(self.source_menu, '開啟來源 PDF', self.open_source_pdf)
        self.source_menu.add_separator()
        self.source_process_action = MenuAction(self.source_menu, '來源處理', self.compare_pdf_pages)
        self.pages_button = MenuAction(self.source_menu, '來源異常', self.review_source_issues)
        self.source_text_frame, self.source = text_pane(self.source_frame, '')
        self.source_text_frame.configure(padding=0)
        self.source_text_frame.grid_slaves(row=0)[0].grid_remove()
        self.source_text_frame.grid(row=1, column=0, sticky='nsew')
        self.image_frame = ttk.Frame(self.source_frame)
        self.image_frame.rowconfigure(0, weight=1)
        self.image_frame.columnconfigure(0, weight=1)
        self.image_canvas = tk.Canvas(self.image_frame, background='#edf0ed', highlightthickness=0, width=1)
        self.image_canvas.grid(row=0, column=0, sticky='nsew')
        image_scroll = ttk.Scrollbar(self.image_frame, command=self.image_canvas.yview)
        image_scroll.grid(row=0, column=1, sticky='ns')
        self.image_canvas.configure(yscrollcommand=image_scroll.set)
        self.image_xscroll = image_xscroll = ttk.Scrollbar(self.image_frame, orient='horizontal', command=self.image_canvas.xview)
        image_xscroll.grid(row=1, column=0, sticky='ew')
        self.image_canvas.configure(xscrollcommand=image_xscroll.set)
        from .desktop import bind_canvas_wheel
        bind_canvas_wheel(self.image_canvas)
        self.image_canvas.bind('<Configure>', lambda e: self.draw_source_image())
        self.image_canvas.bind('<Map>', lambda e: self.draw_source_image())
        self.image_canvas.bind('<ButtonPress-1>', self.begin_source_region)
        self.image_canvas.bind('<B1-Motion>', self.drag_source_region)
        self.image_canvas.bind('<ButtonRelease-1>', self.end_source_region)
        self.source_image = self.display_image = None
        self.right_stack = ttk.Panedwindow(panes, orient='vertical')
        self.editor_frame, self.editor = text_pane(self.right_stack, '', True)
        self.editor_frame.configure(padding=0)
        self.editor_frame.grid_slaves(row=0)[0].grid_remove()
        self.editor_nav = ttk.Frame(self.editor_frame)
        self.editor_nav.grid(row=0, column=0, columnspan=2, sticky='ew')
        self.editor_nav.columnconfigure(0, weight=1)
        self.editor_title = ttk.Frame(self.editor_nav)
        self.editor_title.grid(row=0, column=0, sticky='w')
        self.editor_reopen = ttk.Button(self.editor_title, text='›', width=2, command=self.toggle_focus, style='Workspace.TButton')
        self.editor_heading = ttk.Label(self.editor_title, text='文稿', style='Heading.TLabel')
        self.editor_heading.pack(side='left')
        self.editor_actions = ttk.Frame(self.editor_nav)
        self.editor_actions.grid(row=0, column=1, sticky='e')
        self.source_toggle = ttk.Button(self.editor_actions, text='隱藏原稿', command=self.toggle_source, style='Workspace.TButton')
        self.source_toggle.pack(side='left')
        self.edit_control, self.edit_menu = command_menu(self.editor_actions, '編輯')
        self.edit_control.configure(width=4)
        self.edit_control.pack(side='left', padx=4)
        MenuAction(self.edit_menu, '搜尋與取代 Ctrl+F / Ctrl+H', self.focus_search)
        self.cleanup_button = MenuAction(self.edit_menu, '整理換行預覽', self.cleanup_line_breaks)
        self.edit_menu.add_separator()
        self.export_button = MenuAction(self.edit_menu, '匯出目前全文 TXT', self.export_txt)
        self.reload_button = MenuAction(self.edit_menu, '重載外部稿', partial(self.import_txt, True))
        self.proof_control, self.proof_menu = command_menu(self.editor_actions, '校對')
        self.proof_control.configure(width=4)
        self.proof_control.pack(side='left')
        self.gemini_start_button = MenuAction(self.proof_menu, 'AI 全文校對', self.gemini_review)
        self.settings_action = MenuAction(self.proof_menu, 'AI 設定', self.gemini_settings)
        self.proof_menu.add_separator()
        self.diff_action = MenuAction(self.proof_menu, '顯示／隱藏差異', self.toggle_diff)
        self.restore_change_action = MenuAction(self.proof_menu, '還原游標處改動', self.restore_change)
        self.proof_menu.add_separator()
        self.discard_action = MenuAction(self.proof_menu, '放棄本次 AI 結果', self.discard_candidate)
        self.version_control = ttk.Button(self.editor_actions, text='版本紀錄',
            command=self.show_versions, style='Workspace.TButton')
        self.version_control.pack(side='left', padx=4)
        self.history_action = self.version_control
        self.save_button = ttk.Button(self.editor_actions, text='暫存草稿', command=self.save, style='Workspace.TButton')
        self.save_button.pack(side='left')
        from .workspace_layout import ManuscriptLayout
        self.manuscript_layout = ManuscriptLayout(
            self.source_title, self.pdf_controls, self.editor_title, self.editor_actions,
            (self.source_toggle, self.edit_control, self.proof_control, self.version_control, self.save_button),
            ((self.pdf_previous,), (self.page_entry, self.page_total), (self.pdf_next,), (self.zoom_control,)),
            self.source_control)
        self.manuscript_layout.show_pdf_controls(True)
        self.right_stack.add(self.editor_frame, weight=1)
        panes.add(self.right_stack, weight=1)
        self.editor.configure(exportselection=False)
        self.editor.bind('<<Modified>>', self.edited)
        self.editor.tag_configure('ai_change', background='#dceee3')
        self.editor.tag_configure('find_match', background='#ffedaa')
        self.diff_visible = True
        self.diff_base = ''
        self.search_bar = ttk.Frame(self.editor_frame)
        self.search_bar.columnconfigure(1, weight=1)
        self.find_text = tk.StringVar()
        self.replace_text = tk.StringVar()
        ttk.Label(self.search_bar, text='搜尋').grid(row=0, column=0)
        self.find_entry = ttk.Entry(self.search_bar, textvariable=self.find_text, width=12)
        self.find_entry.grid(row=0, column=1, sticky='ew')
        self.find_entry.bind('<Return>', lambda e: self.find_next())
        self.find_button = ttk.Button(self.search_bar, text='下一筆', command=self.find_next)
        self.find_button.grid(row=0, column=2)
        ttk.Button(self.search_bar, text='上一筆', command=self.find_previous).grid(row=0, column=3)
        self.find_count = ttk.Label(self.search_bar, text='0 筆')
        self.find_count.grid(row=0, column=4)
        ttk.Button(self.search_bar, text='收合', command=lambda: self.search_bar.grid_remove()).grid(row=0, column=5)
        ttk.Label(self.search_bar, text='取代').grid(row=1, column=0)
        ttk.Entry(self.search_bar, textvariable=self.replace_text, width=12).grid(row=1, column=1, sticky='ew')
        self.replace_button = ttk.Button(self.search_bar, text='取代一處', command=self.replace_one)
        self.replace_button.grid(row=1, column=2)
        self.replace_all_button = ttk.Button(self.search_bar, text='全部取代', command=self.replace_all)
        self.replace_all_button.grid(row=1, column=3)
        self.undo_button = ttk.Button(self.search_bar, text='復原', command=self.undo)
        self.undo_button.grid(row=1, column=4)
        self.editor_frame.rowconfigure(1, weight=0)
        self.editor_frame.rowconfigure(2, weight=1)
        self.editor.grid_configure(row=2)
        for widget in self.editor_frame.grid_slaves(row=1):
            widget.grid_configure(row=2)
        self.find_text.trace_add('write', lambda *args: self.count_matches())
        self.tool_panel = ttk.Frame(center)
        self.tool_panel.columnconfigure(0, weight=1)
        self.tool_panel.rowconfigure(1, weight=1)
        panel_nav = ttk.Frame(self.tool_panel)
        panel_nav.grid(row=0, column=0, sticky='ew', pady=(0, 12))
        self.tool_reopen = ttk.Button(panel_nav, text='›', width=2, command=self.toggle_focus, style='Workspace.TButton')
        self.tool_back = ttk.Button(panel_nav, text='← 返回文稿', command=self.close_tools, style='Workspace.TButton')
        self.tool_back.pack(side='left')
        self.tool_title = ttk.Label(panel_nav, style='Heading.TLabel')
        self.tool_title.pack(side='left', padx=12)
        self.tool_host = ttk.Frame(self.tool_panel)
        self.tool_host.grid(row=1, column=0, sticky='nsew')
        self.tool_host.rowconfigure(0, weight=1)
        self.tool_host.columnconfigure(0, weight=1)
        self.tool_pages = [ttk.Frame(self.tool_host) for _ in range(3)]
        from .manuscript_source import SourceTools
        self.inner_host = self.center.create_inner_host(self.toggle_focus)
        from .manuscript_versions import VersionPage
        self.version_page = VersionPage(self, self.inner_host)
        from .manuscript_settings import AiSettingsPage
        self.ai_settings_page = AiSettingsPage(self, self.inner_host)
        from .manuscript_source_page import SourcePage
        self.source_page = SourcePage(self, self.inner_host)
        self.source_tools = SourceTools(self, self.source_page)
        self.source_page.tools = self.source_tools
        from .manuscript_cleanup import LineBreakPreview
        self.cleanup_preview = LineBreakPreview(self, self.inner_host)
        self.import_panel = ttk.Frame(center, padding=24)
        self.import_panel.columnconfigure(0, weight=1)
        self.import_panel.rowconfigure(1, weight=1)
        ttk.Label(self.import_panel, text='建立或開啟專案，然後匯入文稿', style='Title.TLabel').grid(row=0, column=0)
        self.new_name = tk.StringVar()
        self.new_folder = tk.StringVar()
        form = ttk.Frame(self.import_panel)
        form.grid(row=1, column=0)
        ttk.Label(form, text='書籍名稱').grid(row=0, column=0)
        ttk.Entry(form, textvariable=self.new_name, width=28).grid(row=0, column=1, pady=6)
        ttk.Label(form, text='新專案資料夾').grid(row=1, column=0)
        ttk.Entry(form, textvariable=self.new_folder, width=28).grid(row=1, column=1)
        ttk.Button(form, text='選擇位置', command=self.choose_new_folder).grid(row=1, column=2)
        ttk.Button(form, text='建立專案', command=self.create).grid(row=2, column=1, sticky='e', pady=6)
        ttk.Button(form, text='開啟既有專案', command=self.open).grid(row=2, column=0)
        imports = ttk.Frame(self.import_panel)
        imports.grid(row=2, column=0)
        self.import_pdf_cta = ttk.Button(imports, text='匯入 PDF', command=self.import_pdf)
        self.import_pdf_cta.pack(side='left', padx=6)
        self.import_txt_cta = ttk.Button(imports, text='匯入 TXT', command=self.import_txt)
        self.import_txt_cta.pack(side='left')
        for content in (self.panes,self.inner_host,self.tool_panel,self.import_panel):
            self.shell.register_content_root(content)
        self.creating_project=False
        self.job_bar = ttk.Frame(self)
        self.job_bar.grid(row=3, column=0, sticky='ew')
        self.job_bar.columnconfigure(0, weight=1)
        self.job_status = ttk.Label(self.job_bar, width=1)
        self.job_status.grid(row=0, column=0, sticky='ew')
        self.partial_actions = ttk.Frame(self.job_bar)
        self.partial_actions.grid(row=0, column=1, sticky='e', padx=(12, 0))
        self.retry_button = ttk.Button(self.partial_actions, text='繼續未完成範圍', command=self.retry_workspace)
        self.retry_button.grid(row=0, column=0)
        self.keep_partial_button = ttk.Button(self.partial_actions, text='保留未完成處原文', command=self.keep_partial)
        self.keep_partial_button.grid(row=0, column=1, padx=4)
        self.cancel_job_button = ttk.Button(self.partial_actions, text='取消', command=self.cancel_workspace_job)
        self.cancel_job_button.grid(row=0, column=2)
        self.job_bar.grid_remove()
        self.notice = self.status
        self.list_hints = []
        for control in (self.focus_button, self.source_reopen, self.editor_reopen, self.tool_reopen):
            hint = '隱藏文件列表' if control is self.focus_button else '顯示文件列表'
            control.help_text = hint
            tooltip = CellTooltip(control, lambda x, y, hint=hint: (hint, hint))
            control.bind('<FocusIn>', lambda e, tip=tooltip: tip.motion(type('Focus', (), {'x': 0, 'y': 0})()), add='+')
            control.bind('<FocusOut>', tooltip.hide, add='+')
            self.list_hints.append(tooltip)
        self.active_tool = None
        self.editor_view = None
        def style_inputs(widget):
            for child in widget.winfo_children():
                if isinstance(child, ttk.Combobox):
                    child.configure(style='Workspace.TCombobox')
                elif isinstance(child, ttk.Entry):
                    child.configure(style='Workspace.TEntry')
                style_inputs(child)
        style_inputs(self)
        # Keep old entry points available for integrations; all route into this surface.
        self.versions_button = self.history_action
        self.gemini_all_button = self.gemini_selected_button = self.gemini_history_button = self.gemini_start_button
        self.confirm_button = self.next_button
        self.ai_tools_button = self.gemini_start_button
        self.root.bind('<Control-h>', self.focus_search)
        self.root.bind('<Escape>', self.hide_workspace_tools)
        self.root.bind('<Configure>', self.workspace_resize, add='+')
        self.center.bind('<Configure>', self.workspace_resize, add='+')
        self.source_frame.bind('<Configure>', self.workspace_resize, add='+')
        self.right_stack.bind('<Configure>', self.workspace_resize, add='+')
        self.resize_token = self.after(200, self.layout_workspace)
        self.workspace_timer = self.after(100, self.poll_workspace)
        self.bind('<Destroy>', self.workspace_destroyed, add='+')
    def workspace_destroyed(self, event):
        if event.widget is not self:
            return
        if hasattr(self, 'file_drop'):
            self.file_drop.close()
        for name in ('workspace_timer', 'autosave_token', 'tool_fit_token', 'resize_token', 'close_timer'):
            token = getattr(self, name, None)
            if token:
                self.after_cancel(token)
                setattr(self, name, None)
        self.executor.shutdown(wait=True, cancel_futures=True)

    def hide_workspace_tools(self, _event=None):
        self.search_bar.grid_remove()
        self.close_tools()
        return 'break'

    def show_source_info(self):
        self.open_tools(2)
        detail = f'專案位置：{self.flow.root}' if self.flow else '尚未建立專案。'
        detail += '\n原始來源檔不會被改寫。'
        if self.flow and self.batch_id:
            source = self.flow._batch(self.batch_id)['source']
            detail += f'\n來源：{source["original_name"]} · {source["size"]:,} 位元組'
        self.source_tools.detail.configure(text=detail)

    @property
    def workspace_busy(self):
        return any((self.workspace_job, self.source_job, self.source_future, self.connection_job))

    def create(self):
        if not self.may_leave():
            return
        if not self.new_name.get().strip() or not self.new_folder.get().strip():
            self.batch_id = None if not self.flow else self.batch_id
            self.creating_project=True
            self.step=1
            self.render_step()
            self.status.configure(text='輸入書籍名稱，並選擇空白的新專案資料夾。')
            return
        try:
            self.flow = ProjectWorkflow.create(self.new_folder.get(), self.new_name.get())
            self.new_name.set('')
            self.new_folder.set('')
            self.batch_id = None
            self.creating_project=False
            self.step = 1
            self.refresh()
            self.remember_project()
        except ProjectError as error:
            self.report(error)

    def choose_new_folder(self):
        folder = filedialog.askdirectory(parent=self.root, title='選擇新專案的上層位置')
        if folder:
            self.new_folder.set(str(Path(folder) / (self.new_name.get().strip() or '新書籍')))

    def show_step(self, n):
        if self.workspace_busy:
            return
        if n == 4 and self.batch_id and not self.reading_ready():
            self.status.configure(text='請先儲存為朗讀稿。')
            return
        self.step = 4 if n == 4 else 1
        self.render_step()

    def render_step(self):
        if not hasattr(self, 'production'):
            return
        production = self.step == 4
        self.inner_host.set_active(not production)
        self.shell.navigation.select(self.step)
        if production:
            if self.flow:
                current = self.production.current
                key = next((k for k, p in self.production.pages.items() if p is current), None)
                if current is None or key is None or key[0] != id(self.flow) or key[1] not in (None, self.batch_id):
                    self.production.show(key[2] if key and key[0] == id(self.flow) else 'voice')
        else:
            self.step = 1
            self.production.hide()
        for control in (self.source_reopen, self.editor_reopen, self.tool_reopen):
            control.pack_forget()
            if self.focus_mode:
                packed = control.master.pack_slaves()
                control.pack(side='left', **({'before': packed[0]} if packed else {}))
        self.inner_host.show_document_toggle(self.focus_mode)
        self.layout_workspace()
        self.sync_next_action_visibility()

    def sync_next_action_visibility(self):
        if hasattr(self,'production') and self.step==4:
            self.production.sync_chrome()

    def toggle_focus(self, _event=None):
        self.focus_mode = not self.focus_mode
        self.render_step()
        self.save_source_view()
        return 'break'

    def refresh(self, *, keep_step=False):
        self.creating_project=False
        previous = self.loaded_identity
        # The original refresh validates source records and batch ordering.
        self.workspace_review = None
        self._refresh_records(keep_step=True)
        identity = (id(self.flow), self.batch_id)
        if identity != previous:
            self.workspace_review = None
            self.allow_partial = False
            self.source_selection = None
            self.source_tools.reset_source()
            self.close_tools()
            options = self.flow.state.get('manuscript_settings', {}) if self.flow else {}
            if previous is None or identity[0] != previous[0]:
                view = self.flow.state.get('manuscript_view', {}) if self.flow else {}
                self.source_visible = view.get('source_visible', True)
                self.source_sash = view.get('source_ratio')
                if self.source_sash is None and view.get('source_sash'):
                    self.source_sash = .5  # Migrate the former pixel value at the next save.
                self.focus_mode = view.get('list_collapsed', False)
            self.font_size.set(str(options.get('font_size', 12)))
            self.script.set(options.get('script', '自動'))
            self.normalize_punctuation.set(options.get('punctuation', True))
            if options.get('model'):
                self.model.set(options['model'])
            self.editor.configure(font=('Microsoft JhengHei', int(self.font_size.get())))
            self.source.configure(font=('Microsoft JhengHei', int(self.font_size.get())))
            if self.source_image is not None:
                self.source_image.close()
                self.source_image = None
            self.image_canvas.delete('all')
            if self.flow and self.batch_id:
                batch = self.flow._batch(self.batch_id)
                self.page_number.set(str(batch.get('pdf', {}).get('start', 1)))
        self.loaded_identity = identity
        if self.flow and self.batch_id:
            state = self.flow.workspace_state(self.batch_id)
            self.workspace_review = state.get('review_id')
            self.allow_partial = state.get('allow_partial', False)
            text = state.get('text', self.saved_text)
            if not state:
                reviews = self.flow.gemini_reviews(self.batch_id)
                published = {s.get('review_id') for s in self.flow._batch(self.batch_id).get('readings', [])}
                review = next((r for r in reversed(reviews) if not r['stale'] and
                               any(p['candidate'] is not None for p in r['paragraphs']) and
                               not r['history'] and r['id'] not in published), None)
                if review:
                    self.workspace_review = review['id']
                    text, _ = self.flow.full_candidate(self.batch_id, review['id'])
            self.set_editor(text)
            self.diff_base = self.saved_text
            self.mark_diff()
            if self.source_visible:
                self.render_source_page()
        self.render_step()
        self.adapt_source()
        self.update_stats()

    def set_editor(self, text):
        position, view = self.editor.index('insert'), self.editor.yview()
        self._loading = True
        self.editor.edit_separator()
        self.editor.configure(autoseparators=False)
        self.fill(self.editor, text, True)
        self.editor.configure(autoseparators=True)
        self.editor.edit_separator()
        self.editor.mark_set('insert', position)
        self.editor.yview_moveto(view[0])
        self.editor.edit_modified(False)
        self._loading = False

    def edited(self, _event=None):
        if self.editor.edit_modified():
            self.editor.edit_modified(False)
            if not self._loading and self.batch_id:
                try:
                    self.flow.invalidate_reading(self.batch_id)
                except ProjectError as error:
                    self.report(error)
                if self.autosave_token:
                    self.after_cancel(self.autosave_token)
                self.autosave_token = self.after(600, self.autosave_workspace)
                self.update_source_metadata()
                self.update_stats()

    def autosave_workspace(self):
        if self.autosave_token:
            self.after_cancel(self.autosave_token)
        self.autosave_token = None
        if not self.flow or not self.batch_id or self.workspace_job:
            return True
        try:
            self.flow.save_workspace(self.batch_id, self.current_text,
                review_id=self.workspace_review, allow_partial=self.allow_partial)
            self.status.configure(text='草稿已暫存' + (' · 尚未儲存為朗讀稿' if not self.reading_ready() else ''))
            return True
        except ProjectError as error:
            self.report(error)
            return False

    def save(self, *, announce=True):
        return self.autosave_workspace()

    def may_leave(self):
        if self.workspace_busy or self.source_pending:
            self.status.configure(text='請先完成或取消目前工作。')
            return False
        return self.autosave_workspace()

    def reading_ready(self):
        if not self.flow or not self.batch_id:
            return False
        batch = self.flow._batch(self.batch_id)
        return bool(batch.get('current_reading')) and self.current_text == self.saved_text

    def update_stats(self):
        if not hasattr(self, 'next_button'):
            return
        batch = self.flow._batch(self.batch_id) if self.flow and self.batch_id else None
        blockers = self.flow.confirmation_blockers(self.batch_id) if batch else []
        busy = self.workspace_busy or bool(self.source_pending)
        ready = self.reading_ready()
        partial = False
        if self.workspace_review and batch and not self.workspace_job:
            try:
                review = next(r for r in self.flow.gemini_reviews(self.batch_id) if r['id'] == self.workspace_review)
                partial = review['status'] != 'completed'
            except (ProjectError, StopIteration):
                partial = True
        source_summary = ''
        if batch and batch['kind'] == 'pdf':
            pdf = batch['pdf']
            source_summary = f'PDF {pdf["start"]}–{pdf["end"]} · '
        summary = ((f'{batch["name"]} · ' if batch else '') + source_summary + f'文稿 v{batch["revision"] if batch else 0} · {len(self.current_text):,} 字元'
            + (f' · 來源異常 {len(blockers)} 項' if blockers else '')
            + (' · 已儲存，可朗讀' if ready else '')
            + (' · 文稿已更新，語音尚未更新' if batch and batch.get('narration') and not ready else ''))
        self.reading_status.configure(text='已儲存，可朗讀' if ready else
            f'來源異常 {len(blockers)} 項，請先處理' if blockers else
            '尚有未校對範圍' if partial else '尚未儲存為朗讀稿')
        from .desktop_shell import ActionSpec, PagePresentation
        inner_page = self.inner_host.active_id is not None
        self.shell.footer.present(PagePresentation(self.step, self.inner_host.presentation.title if inner_page else '文稿', summary, () if inner_page else (
            ActionSpec('manuscript.next', '前往試聽與製作 →' if ready else '儲存為朗讀稿',
                       'primary', self.publish_or_continue,
                       bool(batch and self.current_text.strip() and not blockers
                            and (not partial or self.allow_partial))),), busy=busy))
        if inner_page:
            self.inner_host.refresh(self.inner_host.active_id)
        self.sync_next_action_visibility()
        self.save_button.configure(state='normal' if batch and not busy else 'disabled')
        for control in (self.edit_control, self.proof_control, self.version_control):
            control.configure(state='normal' if batch and not busy else 'disabled')
        for control in (self.rename_button, self.up_button, self.down_button, self.remove_pdf_button):
            if busy:
                control.configure(state='disabled')
        if not busy:
            self.update_batch_actions()
        for control in (self.diff_action, self.restore_change_action, self.discard_action):
            control.configure(state='normal' if batch and self.workspace_review and not busy else 'disabled')
        is_pdf = bool(self.import_preview or (batch and batch['kind'] == 'pdf'))
        self.open_pdf_action.configure(state='normal' if is_pdf else 'disabled')
        self.settings_action.configure(state='disabled' if busy else 'normal')
        self.editor.configure(state='disabled' if busy else 'normal' if batch else 'disabled')
        self.shell.refresh_document_commands()
        self.gemini_start_button.configure(state='normal' if batch and not busy else 'disabled')
        self.steps[1].configure(state='normal' if ready and not busy else 'disabled')
        for button in (self.import_pdf_cta, self.import_txt_cta):
            button.configure(state='normal' if self.flow and not busy else 'disabled')
        for control in (self.export_button, self.reload_button, self.history_action, self.cleanup_button):
            control.configure(state='normal' if batch and not busy else 'disabled')
        if self.flow:
            for item in self.flow.state['batches']:
                if self.batch_list.exists(item['id']):
                    self.batch_list.item(item['id'], text=self.batch_label(item), values=(self.batch_status(item),))
            self.batch_summary.configure(text=f'{len(self.flow.state["batches"])} 個文件')
        self.root.title((self.flow.state['name'] if self.flow else '書籍製作工作台') + ' — ebook2mp4 v2')
        self.retry_button.grid() if partial and not busy else self.retry_button.grid_remove()
        self.keep_partial_button.grid() if partial and not busy else self.keep_partial_button.grid_remove()
        self.keep_partial_button.configure(state='disabled' if self.allow_partial else 'normal')
        if partial and not busy:
            self.job_status.configure(text='已保留未完成處原文，可儲存。' if self.allow_partial else '尚有未校對範圍，請選擇處理方式。')
        self.cancel_job_button.grid() if self.workspace_busy else self.cancel_job_button.grid_remove()
        if (partial or self.workspace_busy) and not inner_page:
            self.job_bar.grid()
        else:
            self.job_bar.grid_remove()

    def publish_or_continue(self):
        if self.reading_ready():
            self.show_step(4)
        else:
            self.confirm_reading()

    def confirm_reading(self):
        if not self.flow or not self.batch_id or self.workspace_busy or self.source_pending:
            return False
        try:
            text = self.current_text
            self.flow.save_reading_manuscript(self.batch_id, text,
                review_id=self.workspace_review, allow_partial=self.allow_partial)
            self.saved_text = text
            self.workspace_review = None
            self.allow_partial = False
            self.mark_diff()
            self.update_stats()
            self.status.configure(text='已儲存，可朗讀')
            return True
        except ProjectError as error:
            self.report(error)
            return False

    def save_and_review(self):
        return self.confirm_reading()

    def confirm_and_continue(self):
        if self.confirm_reading():
            self.show_step(4)

    def focus_search(self, _event=None):
        self.close_tools()
        if str(self.right_stack) not in self.panes.panes():
            self.toggle_source()
        self.search_bar.grid(row=1, column=0, columnspan=2, sticky='ew')
        self.find_entry.focus_set()
        return 'break'

    def count_matches(self):
        needle = self.find_text.get()
        self.find_count.configure(text=f'{self.current_text.count(needle) if needle else 0} 筆')

    def find_previous(self):
        needle = self.find_text.get()
        if needle:
            index = self.editor.search(needle, 'insert-1c', stopindex='1.0', backwards=True)
            if not index:
                index = self.editor.search(needle, 'end', stopindex='1.0', backwards=True)
            if index:
                self.editor.tag_remove('sel', '1.0', 'end')
                self.editor.tag_add('sel', index, f'{index}+{len(needle)}c')
                self.editor.mark_set('insert', index)
                self.editor.see(index)

    def open_tools(self, index=0):
        if self.step == 4:
            self.show_step(1)
        if not self.tools_open:
            self.editor_view = (self.editor.index('insert'), self.editor.yview()[0], self.editor.tag_ranges('sel'))
        self.tools_open = True
        self.active_tool = index
        if index == 3:
            self.cleanup_preview.prepare()
            self.inner_host.show(self.cleanup_preview.page_id, self.cleanup_preview)
            self.inner_host.show_document_toggle(self.focus_mode)
            self.update_stats()
            self.layout_workspace()
            self.inner_host.back.focus_set()
            return
        if index == 0:
            self.version_page.prepare()
            self.inner_host.show(self.version_page.page_id, self.version_page)
            self.inner_host.show_document_toggle(self.focus_mode)
            self.update_stats()
            self.layout_workspace()
            return
        if index == 1:
            self.inner_host.show(self.ai_settings_page.page_id, self.ai_settings_page)
            self.inner_host.show_document_toggle(self.focus_mode)
            self.update_stats()
            self.layout_workspace()
            return
        if index == 2:
            self.source_tools.open_processing_view()
            self.inner_host.show(self.source_page.page_id, self.source_page)
            self.inner_host.show_document_toggle(self.focus_mode)
            self.update_stats()
            self.layout_workspace()
            return
        self.inner_host.hide()
        self.tool_title.configure(text=('版本紀錄', 'AI 設定', '來源處理', '整理換行預覽')[index])
        for i, page in enumerate(self.tool_pages):
            page.grid_remove()
        self.tool_pages[index].grid(row=0, column=0, sticky='nsew')
        if index == 0:
            self.refresh_versions()
        if index == 2:
            self.source_tools.open_processing_view()
        self.update_stats()
        self.layout_workspace()
        self.tool_back.focus_set()

    def close_tools(self):
        self.cleanup_preview.clear()
        self.inner_host.hide()
        self.tools_open = False
        self.active_tool = None
        self.adapt_source()
        if self.editor_view:
            position, view, selection = self.editor_view
            self.editor.mark_set('insert', position)
            self.editor.yview_moveto(view)
            self.editor.tag_remove('sel', '1.0', 'end')
            if selection:
                self.editor.tag_add('sel', *selection)
            self.editor_view = None
        self.editor.focus_set()
        self.update_stats()
        self.layout_workspace()

    def fit_tool_panel(self):
        self.tool_fit_token = None

    def workspace_resize(self, event):
        if event.widget in (self.root, self.center, self.source_frame, self.right_stack):
            if self.resize_token is not None:
                self.after_cancel(self.resize_token)
            self.resize_token = self.after(60, self.layout_workspace)

    def layout_workspace(self):
        if self.resize_token is not None:self.after_cancel(self.resize_token)
        self.resize_token=None
        if self.step==4:
            self.production.sync_chrome()
            return
        from .desktop_shell import HeaderBand, ShellPresentation
        self.adapt_source()
        if self.inner_host.active_id:
            if self.inner_host.active_id==self.source_page.page_id:
                self.source_tools.layout_preview()
                self.inner_host.refresh(self.source_page.page_id)
            bands=(HeaderBand(self.inner_host,0,(self.inner_host.header,)),)
            owner=self.inner_host.page
            page_id=self.inner_host.active_id
            content=self.inner_host
        else:
            width=self.center.winfo_width()
            two=len(self.panes.panes())==2
            self.manuscript_layout.reflow(self.source_frame.winfo_width() if two else width,
                                         self.right_stack.winfo_width() if two else width)
            bands=(HeaderBand(self.source_frame,0,(self.source_nav,)),
                   HeaderBand(self.editor_frame,0,(self.editor_nav,))) if self.batch_id else ()
            owner=self
            page_id='manuscript' if self.batch_id else 'project.create'
            content=self.panes if self.batch_id else self.import_panel
        if self.creating_project:
            owner=self;page_id='project.create';content=self.import_panel;bands=()
        self.shell.present(ShellPresentation(page_id,owner,content,bands=bands))


    def remember_source_sash(self, _event=None):
        if self.source_visible and len(self.panes.panes()) == 2:
            self.source_sash = self.panes.sashpos(0) / max(1, self.panes.winfo_width()-5)
            self.save_source_view()

    def toggle_source(self):
        if self.root.winfo_width() < 950:
            self.narrow_source = not self.narrow_source
        else:
            self.source_visible = not self.source_visible
        self.adapt_source()
        if self.source_visible or self.narrow_source:
            self.render_source_page()
        self.save_source_view()

    def save_source_view(self):
        if self.flow:
            try:
                manifest = self.flow.state
                manifest['manuscript_view'] = dict(source_visible=self.source_visible, source_ratio=self.source_sash,
                    list_collapsed=self.focus_mode)
                self.flow._commit(manifest, [])
            except ProjectError as error:
                self.report(error)

    def adapt_source(self):
        if not self.winfo_exists():
            return
        narrow = self.root.winfo_width() < 950
        show_source = self.narrow_source if narrow else self.source_visible
        members = self.panes.panes()
        visible = str(self.source_frame) in members
        if show_source and not visible:
            self.panes.insert(0, self.source_frame, weight=1)
        elif not show_source and visible:
            self.panes.forget(self.source_frame)
        right_visible = str(self.right_stack) in self.panes.panes()
        if narrow and show_source and right_visible:
            self.panes.forget(self.right_stack)
        elif (not narrow or not show_source) and not right_visible:
            self.panes.add(self.right_stack, weight=1)
        if not narrow and self.source_visible and len(self.panes.panes()) == 2:
            width = self.panes.winfo_width()
            ratio = self.source_sash if isinstance(self.source_sash, (int, float)) and 0 < self.source_sash < 1 else .5
            self.panes.sashpos(0, max(int(width*.2), min(int(width*.8), int((width-5)*ratio))))
        self.source_toggle.configure(text='原稿' if narrow else '隱藏原稿' if self.source_visible else '顯示原稿')
        self.source_return.pack(side='left') if narrow else self.source_return.pack_forget()
        self.editor_reopen.pack_forget()
        if self.focus_mode and (narrow or not show_source):
            self.editor_reopen.pack(side='left', before=self.editor_heading)

    def toggle_diff(self):
        self.diff_visible = not self.diff_visible
        self.mark_diff()

    def mark_diff(self):
        self.editor.tag_remove('ai_change', '1.0', 'end')
        from .manuscript import change_spans
        self.changes = change_spans(self.diff_base, self.current_text)
        if self.diff_visible:
            for _tag, _a, _b, start, end in self.changes:
                self.editor.tag_add('ai_change', f'1.0+{start}c', f'1.0+{max(start+1, end)}c')
        self.editor_heading.configure(text='文稿')

    def restore_change(self):
        if self.workspace_busy:
            return
        self.mark_diff()
        position = len(self.editor.get('1.0', 'insert'))
        for _tag, a, b, start, end in self.changes:
            if start <= position <= end:
                self.editor.edit_separator()
                self.editor.delete(f'1.0+{start}c', f'1.0+{end}c')
                self.editor.insert(f'1.0+{start}c', self.diff_base[a:b])
                self.editor.edit_separator()
                self.mark_diff()
                return

    def gemini_review(self, selected=False):
        if not self.flow or not self.batch_id or self.workspace_busy or self.source_pending:
            return
        try:
            if self.workspace_review:
                self.status.configure(text='請先儲存或放棄本次 AI 結果；可繼續未完成範圍。')
                return
            self.flow.backup_manuscript(self.batch_id, self.current_text, label='AI 校對前全文')
            self.flow.save_draft(self.batch_id, self.current_text)
            self.saved_text = self.current_text
            self.diff_base = self.current_text
            self.workspace_job = self.flow.start_gemini_review(self.batch_id,
                script={'自動': 'auto', '繁體': 'traditional', '簡體': 'simplified', '保留原樣': 'preserve'}[self.script.get()],
                punctuation=self.normalize_punctuation.get())
            self.workspace_identity = (self.flow, self.batch_id, self.current_text)
            self.workspace_review = self.workspace_job.snapshot['id']
            self.flow.save_workspace(self.batch_id, self.current_text, review_id=self.workspace_review)
            self.update_stats()
        except ProjectError as error:
            self.report(error)

    def gemini_history(self):
        if not self.flow or not self.batch_id or self.workspace_busy:
            return
        self.open_tools(0)
        self.version_selector.configure(values=self.version_labels)
        self.status.configure(text='版本記錄包含舊版 AI 候選；選取後可預覽或還原到編輯稿。')

    def retry_workspace(self):
        if not self.workspace_review or self.workspace_busy:
            return
        try:
            candidate, _ = self.flow.full_candidate(self.batch_id, self.workspace_review)
            self.retry_baseline = (candidate, self.current_text)
            self.autosave_workspace()
            self.workspace_job = self.flow.start_gemini_retry(self.batch_id, self.workspace_review)
            self.workspace_identity = (self.flow, self.batch_id, self.current_text)
            self.update_stats()
        except ProjectError as error:
            self.report(error)

    def keep_partial(self):
        self.allow_partial = True
        self.autosave_workspace()
        self.update_stats()
        self.job_status.configure(text='已保留未完成處原文；此稿含未校對範圍。')

    def discard_candidate(self):
        if not self.workspace_review or self.workspace_busy:
            return
        try:
            self.flow.backup_manuscript(self.batch_id, self.current_text, label='放棄前 AI 候選')
            self.set_editor(self.flow.texts(self.batch_id)[1])
            self.workspace_review = None
            self.allow_partial = False
            self.autosave_workspace()
            self.mark_diff()
            self.update_stats()
        except ProjectError as error:
            self.report(error)

    def cancel_workspace_job(self):
        for job in (self.workspace_job, self.source_job, self.connection_job):
            if job:
                job.cancel()
        self.job_status.configure(text='取消中，正在保留已完成範圍…')

    def poll_workspace(self):
        self.workspace_timer = None
        if self.workspace_job:
            job = self.workspace_job
            snapshot = job.snapshot
            completed = sum(r['status'] == 'completed' for r in snapshot.get('requests', []))
            self.job_status.configure(text=f'AI 校對中 · {completed}／{len(snapshot.get("requests", []))} 範圍')
            if job.wait(0):
                flow, batch_id, submitted = self.workspace_identity
                try:
                    review_id = flow.finish_gemini_review(job)
                    if self.flow is flow and self.batch_id == batch_id and self.current_text == submitted:
                        candidate, review = flow.full_candidate(batch_id, review_id)
                        conflicts = 0
                        if hasattr(self, 'retry_baseline'):
                            from .manuscript import merge_candidate
                            candidate, conflicts = merge_candidate(self.retry_baseline[0], candidate, self.retry_baseline[1])
                            del self.retry_baseline
                        self.set_editor(candidate)
                        self.workspace_review = review_id
                        self.allow_partial = False
                        self.job_status.configure(text='AI 全文校對完成' if review['status'] == 'completed' else '尚有未校對範圍，可繼續或保留原文。')
                        self.status.configure(text=f'已保留 {conflicts} 處人工修改，請檢查差異。' if conflicts else self.job_status.cget('text'))
                        self.mark_diff()
                    else:
                        self.status.configure(text='已拒絕過期 AI 結果；人工文字保留。')
                except ProjectError as error:
                    self.report(error)
                finally:
                    # Keep completed workers until their immutable review is committed.
                    if flow._gemini_job is not job:
                        self.workspace_job = None
                        self.autosave_workspace()
                    self.update_stats()
        self.source_tools.poll()
        if self.connection_job and self.connection_job.wait(0):
            value = self.connection_job.review
            self.settings_status.configure(text='連線成功' if value['status'] == 'completed' else value.get('error', '連線失敗'))
            self.connection_job = None
            self.update_stats()
        if self._closing and not self.workspace_busy:
            self.close()
            return
        self.workspace_timer = self.after(100, self.poll_workspace)

    def close(self):
        if self.close_timer is not None:
            self.after_cancel(self.close_timer)
            self.close_timer = None
        self._closing = True
        if self.workspace_busy:
            self.cancel_workspace_job()
            return
        if not self.autosave_workspace():
            self._closing = False
            return
        if self.source_pending:
            self.flow.discard_pdf_extraction(self.source_pending)
            self.source_pending = None
        shutdown = self.production.shutdown()
        if shutdown == 'cancelled':
            self._closing = False
            return
        if shutdown == 'pending':
            self.close_timer = self.after(100, self.close)
            return
        if self.workspace_timer:
            self.after_cancel(self.workspace_timer)
        if self.autosave_token:
            self.after_cancel(self.autosave_token)
        self.executor.shutdown(wait=True, cancel_futures=True)
        if self.source_image is not None:
            self.source_image.close()
        from .kokoro_runtime import shutdown as shutdown_kokoro
        shutdown_kokoro()
        self.root.destroy()

    def show_versions(self):
        self.open_tools(0)

    def refresh_versions(self):
        selected = self.version_selector.get()
        view = self.version_diff.yview()[0]
        self.version_rows = []
        if self.flow and self.batch_id:
            batch = self.flow._batch(self.batch_id)
            self.version_rows += [(f'朗讀稿 v{s["revision"]} · {s["confirmed_at"][:19]}',
                self.flow.reading_text(self.batch_id, s['id']), None) for s in batch.get('readings', [])]
            self.version_rows += [(f'{s.get("label", "重載備份")} · {s["created_at"][:19]}',
                self.flow.draft_copy_text(self.batch_id, s['id']), None) for s in batch.get('draft_copies', [])]
            for review in self.flow.gemini_reviews(self.batch_id):
                text = self.flow._read(review['before']).decode('utf-8')
                for p in reversed(review['paragraphs']):
                    if p['candidate'] is not None:
                        text = text[:p['start']] + p['candidate'] + text[p['end']:]
                self.version_rows.append((f'AI 候選 · {review["created_at"][:19]} · {review["status"]}', text, review))
        self.version_labels = [row[0] for row in self.version_rows]
        self.version_selector.configure(values=self.version_labels)
        if self.version_rows:
            self.version_selector.current(self.version_labels.index(selected) if selected in self.version_labels else len(self.version_rows)-1)
            self.preview_version()
            self.version_diff.yview_moveto(view)
        else:
            self.version_selector.set('尚無版本')
            self.fill(self.version_diff, '首次匯入尚無版本。儲存為朗讀稿後，可在此預覽與還原。')
            self.version_can_delete = False

    def preview_version(self, _event=None):
        index = self.version_selector.current()
        if index < 0 or index >= len(self.version_rows):
            return
        _label, text, _review = self.version_rows[index]
        readings = self.flow._batch(self.batch_id).get('readings', [])
        self.version_can_delete = index < len(readings)
        diff = ''.join(unified_diff(self.current_text.splitlines(True), text.splitlines(True),
                                   fromfile='目前編輯稿', tofile='所選版本'))
        self.fill(self.version_diff, diff or '與目前全文相同。')
        self.version_page.decorate()

    def delete_reading_version(self):
        from tkinter import messagebox
        index = self.version_selector.current()
        readings = self.flow._batch(self.batch_id).get('readings', []) if self.flow and self.batch_id else []
        if self.workspace_busy or not 0 <= index < len(readings):
            return
        if not messagebox.askyesno('刪除朗讀版本', '刪除此朗讀版本？目前編輯稿與其他版本保留。', parent=self.root, default='no'):
            return
        try:
            warning = self.flow.delete_reading(self.batch_id, readings[index]['id'])
            self.refresh_versions()
            self.update_stats()
            self.status.configure(text=warning or '所選朗讀版本已刪除；編輯稿保留。')
        except ProjectError as error:
            self.report(error)

    def restore_version(self):
        index = self.version_selector.current()
        if self.workspace_busy or index < 0 or index >= len(self.version_rows):
            return
        try:
            _label, text, review = self.version_rows[index]
            self.flow.backup_manuscript(self.batch_id, self.current_text, label='還原前編輯稿')
            self.flow.invalidate_reading(self.batch_id)
            self.set_editor(text)
            self.workspace_review = review['id'] if review and not review['stale'] else None
            self.allow_partial = False
            if review and review['stale']:
                # A historical candidate is a manual draft, never an applicable old job.
                self.status.configure(text='歷史候選已還原為編輯稿；需重新儲存為朗讀稿。')
            self.autosave_workspace()
            self.mark_diff()
            self.update_stats()
        except ProjectError as error:
            self.report(error)

    def gemini_settings(self):
        self.open_tools(1)

    def save_manuscript_settings(self, _event=None):
        if not self.flow or self.workspace_busy or self._loading:
            return
        try:
            from .gemini import validate_model
            model = validate_model(self.model.get().strip())
            size = int(self.font_size.get())
            if not 8 <= size <= 32:
                raise ValueError()
            manifest = self.flow.state
            manifest['manuscript_settings'] = dict(font_size=size, script=self.script.get(),
                punctuation=self.normalize_punctuation.get(), model=model)
            self.flow._commit(manifest, [])
            self.editor.configure(font=('Microsoft JhengHei', size))
            self.source.configure(font=('Microsoft JhengHei', size))
            self.settings_status.configure(text='設定已儲存')
            return True
        except (ProjectError, ValueError) as error:
            self.settings_status.configure(text=str(error) if isinstance(error, ProjectError) else '字級必須介於 8 至 32。')
            return False

    def toggle_connection(self):
        self.ai_settings_page.toggle_connection()

    def save_connection(self):
        if self.workspace_busy:
            return False
        try:
            from .gemini import validate_model
            validate_model(self.model.get().strip())
            size = int(self.font_size.get())
            if not 8 <= size <= 32:
                raise ProjectError('字級必須介於 8 至 32。')
            ProjectWorkflow.save_gemini_settings(self.api_key.get(), self.model.get().strip())
            if not self.save_manuscript_settings():
                self.settings_status.configure(text='本機連線已儲存；偏好保存失敗：'+self.settings_status.cget('text'))
                return False
            self.settings_status.configure(text='設定已儲存（含本機連線）')
            return True
        except (ProjectError, ValueError) as error:
            self.settings_status.configure(text=str(error))
            return False

    def test_connection(self):
        if self.workspace_busy:
            return
        if not self.save_connection():
            return
        try:
            self.connection_job = ProjectWorkflow.test_gemini_connection()
            self.settings_status.configure(text='測試連線中…')
            self.update_stats()
        except ProjectError as error:
            self.settings_status.configure(text=str(error))

    def import_txt(self, reload=False):
        self.source_tools.import_file('txt', reload=reload)

    def import_pdf(self):
        self.source_tools.import_file('pdf')

    def compare_pdf_pages(self):
        self.open_tools(2)

    def open_source_pdf(self):
        if not self.flow:
            return
        try:
            import os
            if self.import_preview:
                path = self.import_preview.path
            else:
                self.flow.pdf_source_preview(self.batch_id)  # Validate the retained source bytes.
                path = self.flow._path(self.flow._batch(self.batch_id)['source']['path'])
            if not path.is_file():
                raise OSError('來源檔不存在')
            os.startfile(path)
        except (ProjectError, OSError) as error:
            self.status.configure(text=f'無法開啟來源 PDF：{error}。請從匯入選擇可讀的 PDF；目前文稿保留。')

    def review_source_issues(self):
        self.open_tools(2)
        self.source_tools.open_issue_view()
        self.inner_host.refresh(self.source_page.page_id)

    def cleanup_line_breaks(self):
        if self.workspace_busy or self.source_pending or not self.flow or not self.batch_id:
            return
        self.open_tools(3)

    def render_source_page(self):
        self.source_tools.render_page()

    def change_source_page(self, increment):
        try:
            self.page_number.set(str(int(self.page_number.get()) + increment))
            self.render_source_page()
        except ValueError:
            self.status.configure(text='頁碼必須為整數。')

    def draw_source_image(self):
        if self.source_image is None:
            return
        from PIL import ImageTk
        image = self.source_image.copy()
        canvases = [self.image_canvas]
        if hasattr(self, 'source_tools'):
            canvases.append(self.source_tools.page_canvas)
        for canvas in canvases:
            if not canvas.winfo_ismapped():
                continue
            zoom = self.source_zoom.get()
            ratio = 1 if zoom == '符合頁寬' else float(zoom.rstrip('%'))/100
            if canvas is self.image_canvas:
                self.image_xscroll.grid() if ratio > 1 else self.image_xscroll.grid_remove()
            width = max(1, int((canvas.winfo_width()-16)*ratio))
            height = max(1, round(image.height*width/image.width))
            resized = image.resize((width, height))
            canvas.page_image = ImageTk.PhotoImage(resized,master=canvas)
            canvas.delete('all')
            canvas.create_image(8, 8, image=canvas.page_image, anchor='nw')
            canvas.configure(scrollregion=(0, 0, width+16, height+16))
            if canvas is self.image_canvas:
                self.display_image = canvas.page_image
            resized.close()
        image.close()

    def begin_source_region(self, event):
        if self.source_tools.scope.get() != '框選區域' or self.source_image is None or self.workspace_busy:
            return
        self.source_region_start = (event.widget.canvasx(event.x), event.widget.canvasy(event.y))
        event.widget.delete('region')

    def drag_source_region(self, event):
        if self.source_region_start is None:
            return
        x, y = self.source_region_start
        event.widget.delete('region')
        event.widget.create_rectangle(x, y, event.widget.canvasx(event.x), event.widget.canvasy(event.y), outline='#248361', width=2, tags='region')

    def end_source_region(self, event):
        start = getattr(self, 'source_region_start', None)
        self.source_region_start = None
        image = getattr(event.widget, 'page_image', None)
        if start and image:
            x, y = start
            width, height = image.width(), image.height()
            ex, ey = event.widget.canvasx(event.x), event.widget.canvasy(event.y)
            box = (min(x,ex), min(y,ey), max(x,ex), max(y,ey))
            self.source_selection = tuple(max(0., min(1., (value-8)/(width if i%2 == 0 else height))) for i,value in enumerate(box))
