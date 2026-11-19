"""Version overview and source comparison inside the production workspace."""
import tkinter as tk
from tkinter import ttk, filedialog

from .workflow import ProjectError
from .voice import VoiceJob
from .voice_media import PreviewPlayer
from .output_versions import describe, TASK_NAMES
from .ui_controls import AutoHideScrollbar
from .workspace_layout import TOOLBAR_GAP


class OutputVersionsPage(ttk.Frame):
    kind = 'versions'
    page_id = 'outputs.versions'

    def __init__(self, app):
        super().__init__(app.production.host)
        self.app, self.flow = app, app.flow
        self.job = self.check_job = self.timer = None
        self.rows = []
        self.return_page = None
        self.requested_route: str | None = None
        self.detail_open = self.closing = self.production_busy = False
        self.movie_player = None
        self.player = PreviewPlayer()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.shell_header = header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky='ew', pady=(0, 8))
        header.columnconfigure(0, weight=1)
        self.heading = ttk.Label(header, text='成品版本', style='Heading.TLabel')
        self.heading.grid(row=0, column=0, sticky='w')
        self.refresh_button = ttk.Button(header, text='重新檢查', command=self.recheck)
        self.refresh_button.grid(row=0, column=1)
        self.content = ttk.Frame(self)
        self.content.grid(row=1, column=0, sticky='nsew')
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)
        self.table = ttk.Treeview(self.content, columns=('route', 'status', 'source'), show='headings', height=3,
                                  selectmode='browse')
        for key, title, width in (('route', '成品路徑', 190), ('status', '狀態', 165), ('source', '使用來源', 260)):
            self.table.heading(key, text=title)
            self.table.column(key, width=width, minwidth=90, stretch=True)
        self.table.grid(row=0, column=0, sticky='nsew')
        self.table.tag_configure('stale', foreground='#895c1e')
        self.table.tag_configure('error', foreground='#963b32')
        self.table.tag_configure('ready', foreground='#315d43')
        self.table.bind('<<TreeviewSelect>>', lambda e: self.update_controls())
        self.table.bind('<Return>', lambda e: self.details())
        self.detail_frame = ttk.Frame(self.content)
        self.detail_frame.columnconfigure(0, weight=1)
        self.detail_frame.rowconfigure(0, weight=1)
        self.text = tk.Text(self.detail_frame, wrap='word', width=1, height=1, relief='flat',
                            font=('Microsoft JhengHei', 10), padx=12, pady=12)
        self.text.grid(row=0, column=0, sticky='nsew')
        scroll = AutoHideScrollbar(self.detail_frame, command=self.text.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        self.text.configure(yscrollcommand=scroll.set, state='disabled')
        self.technical = tk.BooleanVar(value=False)
        self.technical_button = ttk.Checkbutton(self.detail_frame, text='展開技術版本與檔案參照',
                                               variable=self.technical, command=self.draw_detail)
        self.technical_button.grid(row=1, column=0, sticky='w', pady=4)
        self.status = ttk.Label(self, text='正在檢查成品…', width=1, wraplength=650)
        self.status.grid(row=2, column=0, sticky='ew', pady=8)
        self.shell_footer=footer=app.shell.create_footer(self,workspace_aligned=True)
        footer.columnconfigure(0,weight=1)
        actions = ttk.Frame(footer)
        actions.grid(row=0,column=0,sticky='ew',pady=4)
        actions.columnconfigure(1, weight=1)
        self.back_button = footer.button('← 返回全書合併',self.back,parent=actions,role='back')
        self.back_button.grid(row=0, column=0)
        self.detail_button = footer.button('查看來源與版本 ▸',self.details,parent=actions)
        self.detail_button.grid(row=0, column=2)
        outputs = ttk.Frame(footer)
        outputs.grid(row=1,column=0,sticky='ew',pady=4)
        outputs.columnconfigure(0, weight=1)
        self.play_button = footer.button('播放成品',self.play,parent=outputs)
        self.stop_button = footer.button('停止播放',self.stop,parent=outputs)
        self.export_button = footer.button('另存成品／SRT',self.export,parent=outputs)
        self.goto_button = footer.button('前往製作 →',self.goto,parent=outputs,role='primary')
        outputs.columnconfigure((1, 2, 3), uniform='output-actions')
        for col, button in enumerate((self.play_button, self.stop_button, self.export_button, self.goto_button), 1):
            button.grid(row=0, column=col, padx=(TOOLBAR_GAP, 0), sticky='ew')
        self.bind('<Configure>', lambda e: self.status.configure(wraplength=max(200, self.winfo_width()-12)))
        self.update_controls()

    def selected(self):
        selection = self.table.selection()
        return next((r for r in self.rows if selection and r['route'] == selection[0]), None)

    def recheck(self):
        if self.check_job is not None or self.closing:
            return
        async def inspect():
            from .output_versions import inspect_versions
            return await inspect_versions(self.flow)
        self.action = 'inspect'
        self.check_job = VoiceJob(inspect, timeout=None)
        self.status.configure(text='正在檢查各路徑的來源與成品…')
        self.update_controls()
        self.schedule()

    def schedule(self):
        if self.timer is None:
            self.timer = self.after(60, self.poll)

    def poll(self):
        self.timer = None
        if self.check_job is not None and self.check_job.wait(0):
            job, self.check_job = self.check_job, None
            try:
                result = None if self.action == 'stop-play' else job.result
                if self.action == 'inspect':
                    chosen = self.table.selection()
                    if self.requested_route:
                        chosen = (self.requested_route,)
                    self.requested_route = None
                    self.rows = result
                    self.table.delete(*self.table.get_children())
                    for row in result:
                        product = row['product']
                        summary = '尚無來源快照'
                        if product and not row['error']:
                            if row['route'] == 'total-audio':
                                visual = product['visual']
                                asset = visual.get('background') if visual.get('source_type') == 'video' else visual.get('image')
                                summary = '總 MP3／SRT ＋ '+(asset['name'] if asset else '全片素材')
                            else:
                                names = {b['id']: b['name'] for b in self.flow.state['batches']}
                                summary = ' → '.join(names.get(s['batch_id'], '已移除批次') for s in row['sources'])
                        state = row['status']
                        if row['task'] and row['task']['progress']['status'] in ('running', 'pending', 'cancelling'):
                            state = '製作中 · 使用啟動快照'
                        tag = 'error' if row['error'] else 'stale' if row['reasons'] else 'ready'
                        self.table.insert('', 'end', iid=row['route'], values=(row['name'], state, summary), tags=(tag,))
                    self.table.selection_set(chosen[0] if chosen and self.table.exists(chosen[0]) else 'audio')
                    if self.detail_open:
                        self.draw_detail()
                    self.status.configure(text='選取一條路徑，查看來源與待更新原因。上一版成品保留。')
                elif self.action == 'play':
                    self.player.play(result)
                    self.status.configure(text='正在播放所選總音訊。')
                elif self.action == 'export':
                    self.status.configure(text='已另存所選成品及同版 SRT。')
            except (ProjectError, OSError) as error:
                self.status.configure(text=str(error))
        if self.player.alias is not None:
            try:
                self.player.playing()
            except ProjectError as error:
                self.stop()
                self.status.configure(text=str(error))
        self.update_controls()
        if self.closing:
            self.close()
        elif self.check_job is not None or self.playback_active():
            self.schedule()

    def playback_active(self):
        return ((self.check_job is not None and self.action == 'play') or self.player.alias is not None
                or (self.movie_player is not None and self.movie_player.allow))

    def set_production_busy(self, busy):
        self.production_busy = busy
        self.update_controls()

    def update_controls(self):
        row = self.selected()
        locked = self.production_busy or self.check_job is not None or self.closing
        usable = bool(row and row['product'] and not row['error'])
        for button in (self.play_button, self.export_button):
            button.configure(state='normal' if usable and not locked else 'disabled')
        self.stop_button.configure(state='normal' if self.playback_active() and not self.closing else 'disabled')
        self.play_button.configure(text='播放上一版' if row and row['reasons'] else '播放成品')
        self.goto_button.configure(state='normal' if row and not locked else 'disabled',
                                   text='前往更新來源 →' if row and row['reasons'] else '前往製作 →')
        self.detail_button.configure(state='normal' if row and self.check_job is None else 'disabled')
        self.refresh_button.configure(state='disabled' if self.check_job is not None else 'normal')
        self.back_button.configure(state='disabled' if self.check_job is not None else 'normal')
        if row and not self.detail_open and self.check_job is None and not self.playback_active():
            task = row.get('task')
            state = task['progress']['status'] if task else ''
            reason = row['error'] or ' '.join(row['reasons']) or '來源與目前設定一致。'
            if not row['product'] and not row['error']:
                reason = '尚未製作。先完成有效來源，再前往此路徑製作。'
            if state in ('failed', 'cancelled', 'interrupted'):
                reason += ' 最近任務：'+TASK_NAMES[state]+'。成功成品保留。'
            elif state in ('pending', 'running', 'cancelling'):
                reason += ' 任務執行中，固定使用啟動快照。'
            self.status.configure(text=reason)

    def details(self):
        if not self.selected():
            return
        self.stop()
        self.detail_open = True
        self.table.grid_remove()
        self.detail_frame.grid(row=0, column=0, sticky='nsew')
        self.detail_button.grid_remove()
        self.back_button.configure(text='← 返回成品版本')
        self.draw_detail()

    def draw_detail(self):
        row = self.selected()
        if not row:
            return
        self.heading.configure(text=row['name']+' · 來源與版本')
        self.text.configure(state='normal')
        self.text.delete('1.0', 'end')
        self.text.insert('1.0', describe(self.flow, row, technical=self.technical.get()))
        self.text.configure(state='disabled')

    def back(self):
        self.stop()
        if self.detail_open:
            self.detail_open = False
            self.detail_frame.grid_remove()
            self.table.grid()
            self.heading.configure(text='成品版本')
            self.detail_button.grid()
            self.back_button.configure(text='← 返回全書合併')
        elif self.return_page is not None and self.return_page.winfo_exists():
            self.app.production.activate(self.return_page)
        else:
            self.app.total_audio()

    def play(self):
        row = self.selected()
        if not row or self.play_button.instate(['disabled']):
            return
        self.stop()
        if row['route'] != 'audio':
            from .movie_playback import MoviePlayback
            if self.movie_player is None:
                self.movie_player = MoviePlayback(self.content, self.flow, self.close_movie)
            try:
                self.movie_player.start(row['product'])
            except ProjectError as error:
                self.status.configure(text=str(error))
                return
            self.table.grid_remove()
            self.detail_frame.grid_remove()
            self.movie_player.grid(row=0, column=0, sticky='nsew')
            self.update_controls()
            self.schedule()
            return
        async def prepare():
            from .assembly import checked_file_async
            return await checked_file_async(self.flow, row['product']['mp3'])
        self.action = 'play'
        self.check_job = VoiceJob(prepare, timeout=None)
        self.update_controls()
        self.schedule()

    def close_movie(self):
        (self.detail_frame if self.detail_open else self.table).grid(row=0, column=0, sticky='nsew')
        self.update_controls()

    def stop(self):
        if self.check_job is not None and self.action == 'play':
            self.check_job.cancel()
            self.action = 'stop-play'
        try:
            self.player.stop()
            if self.movie_player is not None:
                self.movie_player.stop()
                self.movie_player.grid_remove()
                self.close_movie()
        except ProjectError as error:
            self.status.configure(text=str(error))
        self.stop_button.configure(state='disabled')

    def export(self):
        row = self.selected()
        if not row or self.export_button.instate(['disabled']):
            return
        target = filedialog.asksaveasfilename(parent=self.app.root, title='另存成品與同版 SRT：輸入新資料夾名稱', initialfile='成品副本')
        if not target:
            return
        async def copy():
            if row['route'] == 'audio':
                from .assembly import export
                await export(self.flow, target)
            else:
                from .total_video import export as export_video
                await export_video(self.flow, target, method=row['route'])
        self.action = 'export'
        self.check_job = VoiceJob(copy, timeout=None)
        self.update_controls()
        self.schedule()

    def goto(self):
        try:
            self.goto_source()
        except ProjectError as error:
            self.status.configure(text=str(error))

    def goto_source(self):
        row = self.selected()
        if not row or self.goto_button.instate(['disabled']):
            return
        self.stop()
        invalid = next((s for s in row['current_sources'] if s.get('error') and s.get('batch_id')), None)
        if invalid:
            if not self.app.may_leave():
                return
            self.app.batch_id = invalid['batch_id']
            self.app.refresh()
            if row['route'] == 'batch-videos' and '批次影片待更新' in invalid['error']:
                self.app.batch_video()
            else:
                self.app.narration()
            return
        route = row['route']
        if route == 'batch-videos':
            self.flow.save_total_video_method('batch-videos')
            self.app.production.show('merge')
        else:
            self.flow.save_total_video_method('total-audio')
            audio = self.flow.total_audio()
            if route == 'total-audio':
                self.app.total_video()
            else:
                self.app.total_audio()

    def close(self):
        self.closing = True
        self.stop()
        if self.check_job is not None:
            self.check_job.cancel()
            self.schedule()
            return False
        if self.movie_player is not None and not self.movie_player.release():
            self.schedule()
            return False
        if self.timer is not None:
            self.after_cancel(self.timer)
            self.timer = None
        self.destroy()
