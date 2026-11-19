"""Book-wide assembly within the existing main production workspace."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta, timezone
import os
import tkinter as tk
from tkinter import filedialog, ttk

from .voice import VoiceJob
from .voice_media import PreviewPlayer
from .workflow import ProjectError
from .ui_controls import AutoHideScrollbar


class AssemblyPage(ttk.Frame):
    kind = 'assembly'

    def __init__(self, app, *, movie=False):
        super().__init__(app.production.host)
        self.movie = movie
        self.page_id = 'video.merge' if movie else 'audio.assembly'
        self.output_controls = None
        self.movie_player = None
        self.app, self.flow = app, app.flow
        self.job = self.check_job = self.timer = None
        self.closing = self.production_busy = self.info_open = False
        self.external_busy = False
        self.player = PreviewPlayer()
        value = self.flow.assembly_settings()
        self.selected = [s['batch_id'] for s in value['sources']]
        self.pause = tk.StringVar(value=f'{value["pause_ms"]/1000:g}')
        self.rows: list[dict] = []
        self.product = None
        self.last_status = ''
        self.check_action = 'inspect'
        self.accepted_joins = set(value.get('accepted_joins', []))
        self.edit_return = False
        self.join_page = None
        self.rebuild_requested = False
        if not movie:
            from .assembly_workspace import AudioAssemblyWorkspace
            self.assembly_workspace = AudioAssemblyWorkspace(self)
            self.pause.trace_add('write', lambda *args: self.changed())
            self.recheck()
            return
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.main = main = ttk.Frame(self)
        main.grid(row=0, column=0, sticky='nsew')
        main.columnconfigure(0, weight=1)
        main.rowconfigure(2, weight=1, minsize=70)

        header = ttk.Frame(main)
        header.grid(row=0, column=0, sticky='ew', pady=(0, 6))
        header.columnconfigure(0, weight=1)
        steps = ttk.Frame(header)
        steps.grid(row=0, column=0, sticky='w')
        ttk.Button(steps, text='① 合併音訊', style='CompactActive.TButton').pack(side='left')
        ttk.Label(steps, text=' → ').pack(side='left')
        self.video_step = ttk.Button(steps, text='② 製作影片', command=self.open_video, style='Compact.TButton')
        self.video_step.pack(side='left')
        self.versions_button = ttk.Button(header, text='成品版本 ▸', command=app.production.show_versions)
        self.versions_button.grid(row=0, column=1, sticky='e')
        toolbar = ttk.Frame(main)
        toolbar.grid(row=1, column=0, sticky='ew', pady=(0, 6))
        toolbar.columnconfigure(0, weight=1)
        ttk.Label(toolbar, text='1 選取批次，再調整順序').grid(row=0, column=0, sticky='w')
        self.select_button = ttk.Button(toolbar, text='選取全部有效批次', command=self.select_valid)
        self.up_button = ttk.Button(toolbar, text='上移', command=lambda: self.move(-1))
        self.down_button = ttk.Button(toolbar, text='下移', command=lambda: self.move(1))
        self.info_button = ttk.Button(toolbar, text='來源詳情 ▸', command=self.toggle_info)
        for column, button in enumerate((self.select_button, self.up_button, self.down_button, self.info_button), 1):
            button.grid(row=0, column=column, padx=(4, 0))
        self.info_button.grid_remove()

        self.table_frame = table_frame = ttk.Frame(main)
        table_frame.grid(row=2, column=0, sticky='nsew')
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        self.table = ttk.Treeview(table_frame, columns=('pick', 'order', 'name', 'duration', 'status'),
                                  show='headings', selectmode='browse', height=5)
        for key, label, width, stretch in (('pick', '選取', 46, False), ('order', '順序', 46, False),
                    ('name', '批次', 170, True), ('duration', '時長', 70, False), ('status', '來源狀態', 240, True)):
            self.table.heading(key, text=label)
            self.table.column(key, width=width, minwidth=40, stretch=stretch)
        self.table.grid(row=0, column=0, sticky='nsew')
        scroll = AutoHideScrollbar(table_frame, command=self.table.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        self.table.configure(yscrollcommand=scroll.set)
        self.table.bind('<ButtonRelease-1>', self.toggle_selected)
        self.table.bind('<space>', self.toggle_selected)
        self.table.bind('<<TreeviewSelect>>', lambda e: self.update_controls())
        self.table.bind('<Return>', lambda e: self.toggle_info())
        from .ui_controls import CellTooltip
        self.tooltip = CellTooltip(self.table, self.cell_help)

        self.info_frame = ttk.Frame(main)
        self.info_frame.columnconfigure(0, weight=1)
        self.info_frame.rowconfigure(0, weight=1)
        self.info_text = tk.Text(self.info_frame, wrap='word', height=4, width=1, relief='flat',
                                  font=('Microsoft JhengHei', 10), padx=12, pady=10)
        self.info_text.grid(row=0, column=0, sticky='nsew')
        info_scroll = AutoHideScrollbar(self.info_frame, command=self.info_text.yview)
        info_scroll.grid(row=0, column=1, sticky='ns')
        self.info_text.configure(yscrollcommand=info_scroll.set, state='disabled')
        detail_actions = ttk.Frame(self.info_frame)
        detail_actions.grid(row=1, column=0, columnspan=2, sticky='ew')
        self.fix_button = ttk.Button(detail_actions, text='前往此批次製作 →', command=self.fix_source)
        self.fix_button.pack(side='left')
        ttk.Button(detail_actions, text='返回批次清單', command=self.toggle_info).pack(side='right')

        options = ttk.Frame(main)
        options.grid(row=3, column=0, sticky='ew', pady=6)
        options.columnconfigure(3, weight=1)
        ttk.Label(options, text='額外交接停頓' if self.movie else '2 額外交接停頓').grid(row=0, column=0, sticky='w')
        self.pause_control = ttk.Combobox(options, textvariable=self.pause, values=('0', '0.5', '1', '2', '5'), width=6)
        self.pause_control.grid(row=0, column=1, padx=6)
        ttk.Label(options, text='秒').grid(row=0, column=2)
        self.summary = ttk.Label(options, text='', width=1)
        self.summary.grid(row=0, column=3, sticky='ew', padx=6)
        self.save_button = ttk.Button(options, text='儲存合併設定', command=self.save)
        self.save_button.grid(row=0, column=4)
        self.options = options
        options.grid_remove()
        join_actions = ttk.Frame(main)
        join_actions.grid(row=4, column=0, sticky='ew', pady=(0, 4))
        join_actions.columnconfigure(0, weight=1)
        self.join_summary = ttk.Label(join_actions, text='3 檢查交接接點')
        self.join_summary.grid(row=0, column=0, sticky='w')
        self.join_button = ttk.Button(join_actions, text='對照文字與試聽接點 →', command=self.open_joins)
        self.join_button.grid(row=0, column=1, sticky='e')
        self.settings_button = ttk.Menubutton(join_actions, text='合併設定 ▾')
        self.settings_button.grid(row=0, column=2, padx=(6, 0))
        settings_menu = tk.Menu(self.settings_button, tearoff=False)
        settings_menu.add_command(label='交接停頓與儲存…', command=self.toggle_options)
        settings_menu.add_command(label='來源詳情…', command=self.toggle_info)
        self.settings_button.configure(menu=settings_menu)
        from .ui_controls import MessageLine
        self.status = MessageLine(main, text='正在檢查來源…') if movie else ttk.Label(main, text='正在檢查來源…', wraplength=620)
        self.status.grid(row=5, column=0, sticky='ew', pady=(0, 4))
        self.progress = ttk.Progressbar(main, mode='determinate')
        self.shell_footer = actions = app.shell.create_footer(self)
        actions.columnconfigure(1, weight=1)
        self.back_button = actions.button('← 返回批次製作',app.narration,role='back')
        self.back_button.grid(row=0, column=0, sticky='w')
        self.saved_label = ttk.Label(actions, text='合併設定已儲存' if self.selected else '尚未選取批次', width=1)
        self.saved_label.grid(row=0, column=1, sticky='ew', padx=6)
        self.start_button = actions.button('4 製作總 MP3／SRT →',self.start,role='primary')
        self.start_button.grid(row=0, column=2, sticky='e')
        self.video_button = actions.button('加入視覺素材，製作 MP4 →',self.open_video,role='primary')
        self.video_button.grid(row=0, column=2, sticky='e')
        self.video_button.grid_remove()
        self.cancel_button = actions.button('取消任務',self.cancel)
        self.cancel_button.grid(row=0, column=3, padx=(6, 0))

        self.result_info = ttk.Label(main, text='', width=1)
        self.result_info.grid(row=8, column=0, sticky='ew', pady=(4, 0))
        outputs = ttk.Frame(main)
        outputs.grid(row=9, column=0, sticky='ew', pady=(4, 0))
        outputs.columnconfigure(1, weight=1)
        self.result_info.destroy()
        self.result_info = ttk.Label(outputs, text='', width=1)
        self.result_info.grid(row=0, column=0, columnspan=4, sticky='ew', padx=(0, 6))
        self.play_button = ttk.Button(outputs, text='播放總音訊', command=self.play)
        self.stop_button = ttk.Button(outputs, text='停止播放', command=self.stop)
        self.export_button = ttk.Button(outputs, text='另存 MP3／SRT', command=self.export)
        self.folder_button = ttk.Button(outputs, text='開啟資料夾', command=self.open_folder)
        for col, button in zip((0, 2, 3, 4), (self.play_button, self.stop_button, self.export_button, self.folder_button)):
            button.grid(row=0, column=col, padx=(0, 6))
            button.grid_remove()
        self.outputs_button = ttk.Menubutton(outputs, text='成品操作 ▾')
        self.outputs_button.grid(row=0, column=4, sticky='e')
        self.outputs_menu = tk.Menu(self.outputs_button, tearoff=False, postcommand=self.output_menu)
        self.outputs_button.configure(menu=self.outputs_menu)
        self.rebuild_requested = False
        self.bind('<Configure>', self.resized)
        self.pause.trace_add('write', lambda *args: self.changed())
        if self.movie:
            from .video_merge import resolution
            self.resolution = tk.StringVar(value=resolution(self.flow))
            self.resolution_control = ttk.Combobox(options, textvariable=self.resolution, state='readonly',
                values=('1080p', '720p'), width=7)
            ttk.Label(options, text='解析度').grid(row=0, column=5, padx=(6, 0))
            self.resolution_control.grid(row=0, column=6, padx=(6, 0))
            self.resolution.trace_add('write', lambda *_: self.changed())
            options.grid()
            for child in steps.winfo_children(): child.destroy()
            ttk.Label(steps, text='1 選批次 → 2 檢查接點 → 3 合併 MP4', style='Heading.TLabel').pack(side='left')
            self.video_step = ttk.Button(steps)  # Kept detached for shared control updates.
        from .outputs_desktop import OutputControls
        self.output_controls = OutputControls(self)
        if self.movie:
            self.build_video_workspace(header, toolbar, join_actions)
        self.recheck()

    def build_video_workspace(self, header, toolbar, joins):
        from .video_workspace import VideoTabs, readonly_text, workspace_styles
        header.grid_remove()
        self.notebook = VideoTabs(self.main)
        self.notebook.grid(row=2, column=0, sticky='nsew')
        visual, sources, results = self.notebook.panels
        visual.rowconfigure(0, weight=0)
        ttk.Label(visual, text='沿用各批影片的畫面與原聲。\n不需要總 MP3 或全片素材。\n交接停頓使用前批末格；字幕清空。',
                  justify='left').grid(row=0, column=0, sticky='nw', pady=8)
        self.options.grid(in_=visual, row=1, column=0, sticky='ew')
        for child in self.options.grid_slaves():
            column = int(child.grid_info()['column'])
            if column >= 5:
                child.grid_configure(row=1, column=column-5, pady=(8, 0))
        visual.rowconfigure(2, weight=1)
        ttk.Button(visual, text='檢查各批畫面與接點', command=self.open_joins).grid(row=3, column=0, sticky='e')
        toolbar.grid(in_=sources, row=0, column=0, sticky='ew')
        sources.rowconfigure(0, weight=0)
        sources.rowconfigure(1, weight=1)
        self.table_frame.grid(in_=sources, row=1, column=0, sticky='nsew')
        self.info_frame.grid(in_=sources, row=1, column=0, sticky='nsew')
        self.info_frame.grid_remove()
        joins.grid(in_=sources, row=3, column=0, sticky='ew')
        self.settings_button.grid_remove()
        self.info_button.grid()
        self.output_controls.frame.grid(in_=results, row=0, column=0, sticky='ew')
        self.output_controls.results.grid(in_=results, row=1, column=0, sticky='ew')
        self.output_controls.summary.grid(in_=results, row=2, column=0, sticky='ew')
        for widget in (toolbar, self.table_frame, self.info_frame, joins, self.options,
                       self.output_controls.frame, self.output_controls.results, self.output_controls.summary):
            widget.lift()
        results.rowconfigure(0, weight=0)
        results.rowconfigure(3, weight=1)
        self.task_panel, self.task_text = readonly_text(results)
        self.task_panel.grid(row=3, column=0, sticky='nsew')
        ttk.Button(results, text='版本與來源比較', command=self.app.production.show_versions).grid(row=4, column=0, sticky='e')
        self.back_button.configure(text='← 全書合併', command=self.return_to_audio)
        # Product actions stay reachable outside the tab's bounded content.
        self.result_info.master.grid_remove()
        actions = self.start_button.master
        self.outputs_button = ttk.Menubutton(actions, text='成品操作', menu=self.outputs_menu)
        self.outputs_button.grid(row=0, column=2, padx=6)
        self.start_button.grid_configure(column=4)
        self.notebook.select(1)
        workspace_styles(self)

    def return_to_audio(self):
        self.app.production.return_from_video(self, lambda: self.app.production.show('audio_assembly'))

    def save_settings(self, *args, **kwargs):
        if not self.movie:
            return self.flow.save_assembly_settings(*args, **kwargs)
        return self.flow.save_output_plan(*args, resolution=self.resolution.get() if self.movie else
            self.flow.state.get('video_merge_resolution', '1080p'), **kwargs)

    def begin_job(self):
        return self.flow.start_video_merge() if self.movie else self.flow.start_total_audio()

    def finish_job(self, job):
        return self.flow.finish_total_video(job) if self.movie else self.flow.finish_total_audio(job)

    def discard_job(self, job):
        return self.flow.discard_total_video(job) if self.movie else self.flow.discard_total_audio(job)

    def output_menu(self):
        self.outputs_menu.delete(0, 'end')
        for button in (self.play_button, self.stop_button, self.export_button, self.folder_button):
            self.outputs_menu.add_command(label=button.cget('text'), command=button.invoke,
                                         state='disabled' if button.instate(['disabled']) else 'normal')
        self.outputs_menu.add_command(label='重新合併影片' if self.movie else '重新合併音訊', command=self.rebuild,
            state='disabled' if self.job is not None or self.check_job is not None or self.production_busy else 'normal')

    def rebuild(self):
        self.rebuild_requested = True
        self.update_controls()

    def toggle_options(self):
        if self.options.winfo_manager():
            self.options.grid_remove()
        else:
            self.options.grid()

    def open_video(self):
        if not self.video_step.instate(['disabled']):
            self.app.total_video()

    def resized(self, event):
        if event.widget is self:
            self.status.configure(wraplength=0 if self.movie else max(180, event.width-12))
            self.result_info.configure(wraplength=max(180, event.width-12))
            if self.movie and hasattr(self, 'notebook'):
                required = sum(w.winfo_reqwidth() for w in (self.back_button, self.outputs_button, self.start_button)) + 160
                row = 1 if event.width < required else 0
                self.outputs_button.grid_configure(row=row)
                self.start_button.grid_configure(row=row)
                if self.cancel_button.winfo_manager():
                    self.cancel_button.grid_configure(row=row)

    def cell_help(self, x, y):
        row = self.table.identify_row(y)
        column = self.table.identify_column(x)
        if row and column in ('#3', '#5') and self.table.identify_region(x, y) == 'cell':
            value = self.table.set(row, 'name' if column == '#3' else 'status')
            return f'{row}:{column}:{value}', value
        return None

    def pause_ms(self):
        try:
            value = Decimal(self.pause.get())*1000
            if not value.is_finite() or value != value.to_integral_value() or not 0 <= value <= 5000:
                raise ValueError()
            return int(value)
        except (ValueError, InvalidOperation):
            raise ProjectError('請輸入 0～5 秒，最多 3 位小數。') from None

    def changed(self):
        if self.join_page is not None:
            self.join_page.stop()
        self.saved_label.configure(text='合併設定尚未儲存')
        if not self.movie:
            self.status.configure(text='合併設定尚未儲存；製作時會先儲存。')
        self.load_result()
        self.update_controls()

    def render_rows(self):
        focus = self.table.selection()
        offset = self.table.yview()[0]
        self.tooltip.hide()
        self.table.delete(*self.table.get_children())
        by_id = {r['batch_id']: r for r in self.rows}
        ordered = self.selected + [r['batch_id'] for r in self.rows if r['batch_id'] not in self.selected]
        for identity in ordered:
            row = by_id.get(identity, dict(name='已移除批次', duration_ms=0, valid=False, reason='來源批次已移除'))
            seconds = row['duration_ms']//1000
            reason = row['reason']
            if row.get('version_changed'):
                reason = '有新成品 · 儲存設定後採用目前版本'
            self.table.insert('', 'end', iid=identity, values=('☑' if identity in self.selected else '☐',
                self.selected.index(identity)+1 if identity in self.selected else '—', row['name'],
                (f'{row["duration_ms"]/1000:g} 秒' if seconds < 60 else f'{seconds//60}:{seconds%60:02}')
                if row['duration_ms'] > 0 else '—', reason))
        if focus and self.table.exists(focus[0]):
            self.table.selection_set(focus)
        self.table.yview_moveto(offset)
        self.update_controls()

    def toggle_selected(self, event=None):
        if self.job is not None or self.check_job is not None or self.production_busy:
            return 'break'
        identities = self.table.selection()
        if event is not None and getattr(event, 'num', None) == 1:
            if self.table.identify_region(event.x, event.y) != 'cell' or self.table.identify_column(event.x) != '#1':
                return
            identities = (self.table.identify_row(event.y),)
        for identity in identities:
            if identity in self.selected:
                self.selected.remove(identity)
            elif any(r['batch_id'] == identity for r in self.rows):
                self.selected.append(identity)
            else:
                self.status.configure(text='此來源無效。請查看來源詳情，或前往該批次製作。')
        self.render_rows()
        self.changed()
        return 'break'

    def select_valid(self):
        if self.job is None and self.check_job is None and not self.production_busy:
            if not self.rows:
                self.recheck()
                return
            self.selected = [r['batch_id'] for r in self.rows if r['valid']]
            self.render_rows()
            self.changed()

    def move(self, delta):
        focus = self.table.selection()
        if not focus or focus[0] not in self.selected or self.job is not None or self.production_busy:
            return
        index = self.selected.index(focus[0])
        if 0 <= index+delta < len(self.selected):
            self.selected[index], self.selected[index+delta] = self.selected[index+delta], self.selected[index]
            self.render_rows()
            self.changed()

    def recheck(self):
        if self.job is not None or self.check_job is not None or self.closing:
            return
        async def inspect():
            from .assembly import inspect, inspect_total_audio
            if self.movie:
                from .video_merge import inspect
            rows = await inspect(self.flow)
            warning = ''
            try:
                if self.movie:
                    from .total_video import total_video
                    from .assembly import checked_file_async
                    product = total_video(self.flow, verify_media=False, method='batch-videos')
                    if product:
                        for kind in ('mp4', 'srt'): await checked_file_async(self.flow, product[kind])
                else:
                    product = await inspect_total_audio(self.flow)
            except ProjectError as error:
                product = None
                warning = f'舊總成品無法驗證：{error} 可使用有效批次重新合併。'
            try:
                runs = self.flow.total_video_runs(method='batch-videos') if self.movie else self.flow.total_audio_runs()
            except ProjectError as error:
                runs = []
                warning += f' 合併進度無法讀取：{error}'
            output_plan = None
            if self.movie:
                from .outputs import inspect as inspect_outputs
                output_plan = await inspect_outputs(self.flow)
            return rows, product, runs, warning, output_plan
        self.check_action = 'inspect'
        self.check_job = VoiceJob(inspect, timeout=None)
        self.status.configure(text='正在檢查來源與成品版本…')
        self.update_controls()
        self.schedule()

    def save(self):
        try:
            self.require_current()
            self.save_settings(self.selected, self.pause_ms(), accepted_joins=list(self.accepted_joins))
            if not self.movie and self.join_page is not None:
                self.join_page.workspace.save_error = False
            self.saved_label.configure(text='合併設定已儲存')
            self.status.configure(text='合併設定已儲存。尚未開始合併，不傳送文字。')
            self.app.notify('全書合併設定已儲存。')
            self.recheck()
            return True
        except ProjectError as error:
            if not self.movie and self.join_page is not None:
                self.join_page.workspace.save_error = True
            self.status.configure(text=str(error))
            self.app.notify(str(error), kind='error')
            return False

    def require_current(self):
        if self.app.flow is not self.flow:
            raise ProjectError('書籍已切換，請回目前書籍重新開啟全書合併。')
        if self.job is not None or self.check_job is not None:
            raise ProjectError('請先等待目前檢查或製作停止。')
        # A pending batch form must not be silently ignored during book assembly.
        for key, page in self.app.production.pages.items():
            if key[0] == id(self.flow) and key[1] in self.selected and key[2] == 'voice' and page.winfo_exists():
                if page.scope.get() == '本批次' and page.current_settings() != self.flow.voice_settings(page.batch_id):
                    raise ProjectError('所選批次有未儲存的語音設定。請先返回語音頁儲存或重讀。')

    def start(self):
        try:
            if self.job is not None:
                from .outputs import OutputJob
                if isinstance(self.job, OutputJob) and self.job.publish_pending:
                    self.job.retry_save()
                    self.schedule()
                    return
                if self.job.wait(0) and self.job.state['status'] == 'completed':
                    self.publish()
                return
            self.require_current()
            self.stop()
            self.save_settings(self.selected, self.pause_ms(), accepted_joins=list(self.accepted_joins))
            self.saved_label.configure(text='合併設定已儲存')
            self.job = self.flow.start_outputs() if self.movie else self.begin_job()
            self.status.configure(text='開始合併；本次來源版本與順序已固定。')
            self.update_controls()
            self.schedule()
        except ProjectError as error:
            self.status.configure(text=str(error))
            self.app.notify(str(error), kind='error')

    def schedule(self):
        if self.timer is not None:
            self.after_cancel(self.timer)
        self.timer = self.after(100, self.poll)

    def publish(self):
        self.product = self.finish_job(self.job)
        self.job = None
        self.rebuild_requested = False
        self.production_busy = self.app.production.busy_for(self.flow)
        self.load_result()
        label='總 MP4／SRT' if self.movie else '總 MP3／SRT'
        self.status.configure(text=label+' 已完成並保存。請播放檢查。')
        self.app.notify(label+' 已完成並保存。')

    def poll(self):
        self.timer = None
        from .outputs import OutputJob
        if isinstance(self.job, OutputJob):
            assert self.output_controls is not None
            self.output_controls.poll()
            return
        if self.check_job is not None:
            if not self.check_job.wait(0):
                self.schedule()
                return
            try:
                if self.check_job.state['status'] == 'cancelled':
                    if self.check_action == 'inspect':
                        self.rows = []
                    self.status.configure(text='已取消檢查或檔案操作。舊成品保留；可重新檢查來源。')
                elif self.check_action == 'inspect':
                    self.rows, self.product, runs, warning, output_plan = self.check_job.result
                    if self.output_controls is not None:
                        self.output_controls.plan = output_plan
                        for kind, value in self.output_controls.values.items():
                            value.set(kind in output_plan['formats'])
                    self.render_rows()
                    self.load_result()
                    last = runs[-1]['progress'] if runs else None
                    self.last_status = last['status'] if last else ''
                    labels = dict(cancelled='已取消', failed='失敗', interrupted='已中斷', completed='已完成')
                    self.status.configure(text=(f'上次合併：{labels.get(last["status"], "未完成")}。'+last.get('error', '')+' 舊成品保留，可重新合併。'
                        if last and last['status'] != 'completed' else '合併 MP3 與同版 SRT 已完成並保存。'
                        if self.product and not self.product['stale'] else '請依序選批次、設定交接停頓，再製作總音訊。'))
                    if self.movie and self.product and not self.product['stale']:
                        self.status.configure(text='總影片已完成。可從成品操作播放、另存或開啟資料夾。')
                    if output_plan and output_plan['status'] == 'completed':
                        self.status.configure(text='各要求格式與同版 SRT 均已保存。可從成品操作播放或另存。')
                    elif output_plan and output_plan['status'] == 'partial':
                        self.status.configure(text='請補齊缺項或查看失敗原因，再只重試未完成格式；成功成品保留。')
                    if warning:
                        self.status.configure(text=warning)
                        self.app.notify(warning, kind='warning')
                else:
                    path = self.check_job.result
                    if (self.check_action == 'play' and not self.closing and self.app.step == 4
                            and self.app.production.current is self and self.app.flow is self.flow):
                        self.player.play(path)
                        self.status.configure(text='正在播放總音訊。可按「停止播放」結束。')
                    elif self.check_action == 'folder':
                        os.startfile(path)
                        self.status.configure(text='已開啟總成品資料夾。')
                    elif self.check_action == 'export':
                        label='總 MP4 與 SRT' if self.movie else '總 MP3 與 SRT'
                        self.status.configure(text=label+' 已另存至新資料夾。')
                        self.app.notify(label+' 已另存至新資料夾。')
            except (ProjectError, OSError) as error:
                self.status.configure(text=str(error))
                self.app.notify(str(error), kind='error')
            self.check_job = None
            if (self.check_action == 'inspect' and self.join_page is not None
                    and self.join_page.winfo_viewable() and not self.closing):
                self.join_page.load()
        if self.job is not None:
            state = self.job.state
            if not self.job.wait(0):
                self.status.configure(text='取消中，正在停止媒體程序並釋放檔案…' if state['status'] == 'cancelling' else
                    f'{state.get("phase", "準備")} · 完成 {state.get("completed", 0)}/{state.get("total", 0)}')
                self.progress.configure(maximum=max(1, state.get('total', 1)), value=state.get('completed', 0))
                self.schedule()
                return
            try:
                self.last_status = state['status']
                if self.closing or state['status'] != 'completed':
                    self.discard_job(self.job)
                    self.job = None
                    self.production_busy = self.app.production.busy_for(self.flow)
                    self.status.configure(text='已取消。上一版總成品保留。' if state['status'] == 'cancelled' else state['error'])
                    if state['status'] == 'failed':
                        for entry in state.get('sources', []):
                            if entry['status'] == 'failed':
                                row = next((r for r in self.rows if r['batch_id'] == entry['batch_id']), None)
                                if row is not None:
                                    row.update(valid=False, reason=state['error'])
                        self.render_rows()
                    self.app.notify(self.status.cget('text'), kind='error' if state['status'] == 'failed' else 'info')
                else:
                    self.publish()
            except ProjectError as error:
                self.closing = False
                self.status.configure(text=str(error)+' 請重試保存，或關閉以捨棄本次結果。')
                self.app.notify(self.status.cget('text'), kind='error')
        if self.closing and self.movie_player is not None and self.movie_player.has_work():
            self.schedule()
            return
        if self.closing and self.join_page is not None and self.join_page.has_work():
            self.schedule()
            return
        if self.closing and self.job is None and self.check_job is None:
            self.release()
            return
        self.update_controls()
        try:
            was_playing = self.player.alias is not None
            if self.player.playing():
                self.schedule()
            elif was_playing:
                self.status.configure(text='播放已結束。')
        except ProjectError as error:
            self.status.configure(text=str(error))
            self.stop()

    def update_controls(self):
        if not self.movie:
            self.assembly_workspace.refresh()
            return
        busy = self.job is not None or self.check_job is not None or self.production_busy
        valid = bool(self.selected) and all(any(r['batch_id'] == i and r['valid'] for r in self.rows) for i in self.selected)
        try:
            pause = self.pause_ms()
            self.summary.configure(text=f'已選 {len(self.selected)} 批 · 額外 {max(0,len(self.selected)-1)*pause/1000:g} 秒（末批不補）')
        except ProjectError:
            valid = False
            self.summary.configure(text='請輸入有效停頓秒數')
        stopped = self.job is not None and self.job.wait(0)
        can_save = stopped and self.job is not None and self.job.state['status'] == 'completed'
        self.start_button.configure(state='normal' if can_save or valid and not busy else 'disabled',
            text='重試保存' if can_save else '4 重試合併 MP3／SRT →' if self.last_status in ('failed', 'cancelled', 'interrupted') else
            '4 更新總 MP3／SRT →' if self.product else '4 製作總 MP3／SRT →')
        from .assembly_joins import metadata
        try:
            joins = metadata(self.flow, self.selected)
            pending = sum(bool(j['warning']) and j['key'] not in self.accepted_joins for j in joins)
            self.join_summary.configure(text=f'3 檢查 {len(joins)} 個接點' + (f' · {pending} 個頁碼警告待確認' if pending else ''))
            if pending and not can_save:
                self.start_button.configure(state='disabled')
        except ProjectError:
            joins = []
        self.join_button.configure(state='normal' if len(self.selected) >= 2 and not busy and joins else 'disabled')
        self.save_button.configure(state='disabled' if busy or not valid else 'normal')
        self.select_button.configure(state='disabled' if busy else 'normal')
        self.select_button.configure(text='選取全部有效批次' if self.rows else '重新檢查來源')
        self.pause_control.configure(state='disabled' if busy else 'normal')
        focus = self.table.selection()
        index = self.selected.index(focus[0]) if focus and focus[0] in self.selected else -1
        self.up_button.configure(state='normal' if not busy and index > 0 else 'disabled')
        self.down_button.configure(state='normal' if not busy and 0 <= index < len(self.selected)-1 else 'disabled')
        self.play_button.configure(state='normal' if self.product and self.check_job is None else 'disabled')
        self.stop_button.configure(state='normal' if self.player.alias is not None or
            self.check_job is not None and self.check_action == 'play' else 'disabled')
        self.export_button.configure(state='normal' if self.product and not busy else 'disabled')
        self.folder_button.configure(state='normal' if self.product and self.check_job is None else 'disabled')
        if self.check_job is not None or self.job is not None and not stopped:
            mode = 'indeterminate' if self.check_job is not None else 'determinate'
            if str(self.progress.cget('mode')) != mode:
                self.progress.stop()
                self.progress.configure(mode='indeterminate' if self.check_job is not None else 'determinate')
                if self.check_job is not None:
                    self.progress.start(15)
            self.progress.grid(row=9, column=0, sticky='ew')
            self.cancel_button.grid()
        else:
            self.progress.stop()
            self.progress.grid_remove()
            self.cancel_button.grid_remove()
        if self.join_page is not None:
            self.join_page.update_controls()
        product = self.product
        current = bool(product and not product['stale'])
        if current and product:
            try:
                current = (self.selected == [s['batch_id'] for s in product.get('sources', [])]
                           and self.pause_ms() == product.get('pause_ms')
                           and (not self.movie or product['visual']['resolution'] == self.resolution.get()))
            except ProjectError:
                current = False
        self.video_step.configure(state='normal' if current and not busy else 'disabled')
        self.video_button.configure(state='normal' if current and not busy else 'disabled')
        if current and not self.rebuild_requested and not busy:
            self.start_button.grid_remove()
            self.video_button.grid()
        else:
            self.video_button.grid_remove()
            self.start_button.grid()
        self.start_button.configure(text='重試保存' if can_save else '重試合併 MP3／SRT' if self.last_status in
            ('failed', 'cancelled', 'interrupted') else '合併 MP3／SRT')
        if self.movie:
            self.video_step.configure(state='disabled')
            self.video_button.grid_remove()
            self.start_button.grid()
            self.start_button.configure(text='重試保存' if can_save else '重試合併 MP4／SRT' if self.last_status in
                ('failed', 'cancelled', 'interrupted') else '合併 MP4／SRT')
            self.resolution_control.configure(state='disabled' if busy else 'readonly')
            self.movie_labels()
        self.settings_button.configure(state='disabled' if busy else 'normal')
        self.join_button.configure(text='檢查接點')
        self.join_summary.configure(text=(f'2 檢查 {len(joins)} 個接點' if self.movie else self.summary.cget('text'))
            + (f' · {pending} 個警告待確認' if joins and pending else ''))
        if self.output_controls is not None:
            self.output_controls.refresh()
        if hasattr(self, 'notebook'):
            from .video_workspace import replace_text
            text = self.status.full_text + '\n\n' + self.result_info.cget('text')
            if self.product:
                text += '\n\n' + '\n'.join(f'{k.upper()}：{self.product[k]["path"]}' for k in ('mp4', 'srt'))
            replace_text(self.task_text, text)

    def open_joins(self):
        if self.join_button.instate(['disabled']):
            return
        self.stop()
        if self.join_page is None:
            from .assembly_joins_desktop import JoinPage
            self.join_page = JoinPage(self)
        self.main.grid_remove()
        if not self.movie:
            self.assembly_workspace.header.grid_remove()
            self.assembly_workspace.set_active(False)
        self.join_page.grid(row=0, column=0, rowspan=2 if not self.movie else 1, sticky='nsew')
        self.app.production.sync_chrome()
        self.join_page.load()

    def return_from_joins(self):
        if self.join_page is None:
            return
        self.join_page.stop()
        self.join_page.grid_remove()
        self.main.grid(row=1 if not self.movie else 0, column=0, sticky='nsew')
        if not self.movie:
            self.assembly_workspace.header.grid()
            self.assembly_workspace.set_active(True)
        self.edit_return = False
        self.app.production.sync_chrome()
        self.update_controls()

    def set_production_busy(self, busy):
        was_external = self.external_busy
        self.external_busy = busy and self.job is None
        self.production_busy = busy
        if busy and self.job is None and self.check_job is None:
            self.status.configure(text='專案另有製作任務。請等待完成或取消該任務後，再合併。')
        elif was_external and not busy:
            self.recheck()
        self.update_controls()

    def load_result(self):
        p = self.product
        pending = False
        if p:
            try:
                pending = (self.selected != [s['batch_id'] for s in p.get('sources', [])]
                           or self.pause_ms() != p.get('pause_ms')
                           or self.movie and (p.get('method') != 'batch-videos'
                               or p['visual']['resolution'] != self.resolution.get()))
            except ProjectError:
                pending = True
        self.result_info.configure(text=(f'{"待更新 · 上一版總成品" if p["stale"] or pending else "目前總成品"}：'
            f'{datetime.fromisoformat(p["completed_at"]).astimezone(timezone(timedelta(hours=8))):%Y-%m-%d %H:%M:%S} · '
            f'{len(p.get("sources", []))} 批 · {p["duration_ms"]/1000:g} 秒'
            if p else '尚無總成品。先選有效批次，再製作總音訊。'))

    def toggle_info(self):
        self.info_open = not self.info_open
        self.table_frame.grid_remove()
        self.info_frame.grid_remove()
        (self.info_frame if self.info_open else self.table_frame).grid(row=1 if hasattr(self, 'notebook') else 2, column=0, sticky='nsew')
        self.info_button.configure(text=('← 返回清單' if self.info_open else '來源詳情 →') if not self.movie else '返回清單 ▾' if self.info_open else '來源詳情 ▸')
        if self.info_open:
            focus = self.table.selection()
            row = next((r for r in self.rows if focus and r['batch_id'] == focus[0]), None)
            source = row.get('source', {}) if row else {}
            content = (f'{row["name"]}\n{row["reason"]}\n版本：{source.get("product_id", "無有效成品")}\n'
                       f'MP3：{source.get("mp3", {}).get("path", "—")}\nSRT：{source.get("srt", {}).get("path", "—")}\n\n' if row else '請先選擇批次列。\n\n')
            content += '只合併目前確認稿與語音設定一致的 MP3／SRT。開始後完整解碼，依實際時長移動字幕。\n保留每批原有頭尾；只在相鄰批次間加靜音，靜音內不顯示字幕。\n全書選取與順序供後續總影片共用。不需圖片或批次 MP4，不呼叫 TTS。'
            if self.movie:
                content = (f'{row["name"]}\n{row["reason"]}\nMP4：{source.get("mp4",{}).get("path","—")}\n'
                    f'SRT：{source.get("srt",{}).get("path","—")}\n\n' if row else '') + '只使用有效批次 MP4／SRT。保持比例補黑邊，統一解析度。額外停頓維持前批最後一格，字幕清空。保留原聲，不呼叫 TTS。'
            self.info_text.configure(state='normal')
            self.info_text.delete('1.0', 'end')
            self.info_text.insert('1.0', content)
            self.info_text.configure(state='disabled')
            self.fix_button.configure(state='normal' if row and not row['valid'] else 'disabled')

    def fix_source(self):
        focus = self.table.selection()
        if focus and any(b['id'] == focus[0] for b in self.flow.state['batches']):
            if not self.app.may_leave():
                return
            self.app.batch_id = focus[0]
            self.app.refresh()
            (self.app.batch_video if self.movie else self.app.narration)()
            if self.movie:
                destination = self.app.production.current
                destination.return_origin = self
                destination.back_button.configure(text='← 返回全書影片')

    def movie_labels(self):
        def visit(widget):
            if self.output_controls is not None and widget in (self.output_controls.frame, self.output_controls.results):
                return
            try:
                text=widget.cget('text')
                if isinstance(text,str): widget.configure(text=text.replace('MP3／SRT','MP4／SRT')
                    .replace('總音訊','總影片').replace('音訊已完成','影片已完成').replace('合併音訊','合併影片'))
            except tk.TclError: pass
            for child in widget.winfo_children(): visit(child)
        visit(self.main)

    def close_movie(self):
        if hasattr(self, 'notebook'):
            (self.info_frame if self.info_open else self.table_frame).grid(row=1, column=0, sticky='nsew')
            self.notebook.grid()
            return
        (self.info_frame if self.info_open else self.table_frame).grid(row=2,column=0,sticky='nsew')

    def play(self):
        if self.movie and self.product:
            from .movie_playback import MoviePlayback
            try:
                if self.movie_player is None:
                    self.movie_player=MoviePlayback(self.main,self.flow,self.close_movie)
                self.table_frame.grid_remove();self.info_frame.grid_remove()
                if hasattr(self, 'notebook'):
                    self.notebook.grid_remove()
                self.movie_player.grid(row=2,column=0,sticky='nsew')
                self.movie_player.start(self.product)
            except ProjectError as error: self.status.configure(text=str(error))
            return
        self.file_action('play')

    def stop(self):
        if self.movie_player is not None: self.movie_player.stop()
        if self.join_page is not None:
            self.join_page.stop()
        was_playing = self.player.alias is not None
        if self.check_job is not None and self.check_action == 'play':
            self.check_job.cancel()
        try:
            self.player.stop()
            if was_playing:
                self.status.configure(text='播放已停止。')
        except ProjectError as error:
            self.status.configure(text=str(error))
        self.update_controls()

    def export(self):
        target = filedialog.asksaveasfilename(parent=self.app.root, title='另存總 MP4／SRT：輸入新資料夾名稱' if self.movie else '另存總 MP3／SRT：輸入新資料夾名稱', initialfile='總影片成品' if self.movie else '總音訊成品')
        if target:
            self.file_action('export', target)

    def open_folder(self):
        self.file_action('folder')

    def file_action(self, action, target=None):
        if self.check_job is not None:
            return
        self.stop()
        async def operation():
            from .assembly import export, inspect_total_audio
            if self.movie:
                from .total_video import export as export_video, total_video
                from .assembly import checked_file_async
                if action == 'export':
                    await export_video(self.flow, target, method='batch-videos')
                    return None
                product = total_video(self.flow, verify_media=False, method='batch-videos')
                if product is None: raise ProjectError('尚無總影片。')
                path = await checked_file_async(self.flow, product['mp4'])
                return path.parent
            if action == 'export':
                await export(self.flow, target)
                return None
            product = await inspect_total_audio(self.flow)
            if product is None:
                raise ProjectError('尚無成功總成品。')
            path = self.flow._path(product['mp3']['path'])
            return path.parent if action == 'folder' else path
        self.check_action = action
        self.check_job = VoiceJob(operation, timeout=None)
        self.status.configure(text='正在驗證成品並處理檔案…')
        self.update_controls()
        self.schedule()

    def cancel(self):
        if self.check_job is not None:
            self.check_job.cancel()
            self.status.configure(text='取消中，正在停止檢查並釋放檔案…')
        if self.job is not None:
            self.job.cancel()
            self.status.configure(text='取消中，正在停止媒體程序並釋放檔案…')

    def close(self):
        self.stop()
        self.closing = True
        if self.check_job is not None:
            self.check_job.cancel()
        if self.job is not None:
            self.cancel()
        if self.check_job is not None or self.job is not None or self.join_page is not None and self.join_page.has_work():
            self.schedule()
        else:
            self.release()

    def release(self):
        if self.timer is not None:
            self.after_cancel(self.timer)
        if self.movie_player is not None and not self.movie_player.release():
            self.schedule()
            return
        self.tooltip.hide()
        self.progress.stop()
        self.stop()
        if self.join_page is not None:
            self.join_page.release()
        if not self.movie:
            self.assembly_workspace.pause_help.hide()
            self.assembly_workspace.set_active(False)
            self.assembly_workspace.actions.destroy()
        self.destroy()
