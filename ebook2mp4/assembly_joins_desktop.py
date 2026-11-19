"""Join inspection inside the existing book assembly workspace."""
from io import BytesIO
from PIL import Image, ImageTk
from pathlib import Path
from functools import partial
import tkinter as tk
from tkinter import ttk

from .voice import VoiceJob
from .voice_media import PreviewPlayer
from .workflow import ProjectError


class JoinPage(ttk.Frame):
    left_text: tk.Text
    right_text: tk.Text
    left_edit: ttk.Button
    right_edit: ttk.Button
    def __init__(self, owner):
        super().__init__(owner)
        self.owner, self.app, self.flow = owner, owner.app, owner.flow
        self.page_id = 'video.joins' if owner.movie else 'audio.joins'
        self.job = self.info_job = self.timer = None
        self.movie_player = None
        self.movie = getattr(owner, 'movie', False)
        self.player = PreviewPlayer()
        self.playing = self.allow_play = False
        self.joins: list[dict] = []
        self.index = 0
        self.clip = tk.StringVar(value='5')
        self.accepted = tk.BooleanVar(value=False)
        self.content_kind = 'source'
        self._displayed_key = self._source_signature = None
        self._reading_positions = {}
        self._reading_restore = None
        self._reading_timer = None
        self._reading_anchor = self._reading_reflow = None
        self._invalid_pause = self._preview_failed = False
        if not self.movie:
            from .assembly_join_workspace import AudioJoinWorkspace
            self.workspace = AudioJoinWorkspace(self)
            for pane in self.workspace.panes:
                for event in ('<ButtonPress-1>', '<MouseWheel>', '<KeyPress>'):
                    pane.text.bind(event, self.cancel_reading_restore, add='+')
                pane.scroll.bind('<ButtonPress-1>', self.cancel_reading_restore, add='+')
                pane.text.bind('<Configure>', self.reflow_reading, add='+')
            self.bind('<Destroy>', self.destroyed, add='+')
            return
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1, minsize=70)
        ttk.Label(self, text='2 檢查影音接點 · 對照畫面與文字，再播放' if self.movie else '檢查交接接點 · 對照文字，再試聽', style='Heading.TLabel').grid(row=0, column=0, sticky='w')
        selection = ttk.Frame(self)
        selection.grid(row=1, column=0, sticky='ew', pady=4)
        selection.columnconfigure(1, weight=1)
        ttk.Label(selection, text='接點').grid(row=0, column=0, padx=(0, 6))
        self.pair_control = ttk.Combobox(selection, state='readonly', width=20)
        self.pair_control.grid(row=0, column=1, sticky='ew')
        self.pair_control.bind('<<ComboboxSelected>>', self.select_pair)
        self.previous = ttk.Button(selection, text='上一個', command=lambda: self.move(-1))
        self.previous.grid(row=0, column=2, padx=4)
        self.next = ttk.Button(selection, text='下一個', command=lambda: self.move(1))
        self.next.grid(row=0, column=3)
        self.pair = pair = ttk.Frame(self)
        pair.grid(row=2, column=0, sticky='nsew')
        pair.columnconfigure((0, 1), weight=1, uniform='join')
        pair.rowconfigure(0, weight=1)
        self.headings = []
        self.frame_labels = []
        self.frame_photos = []
        for column, side in enumerate(('left', 'right')):
            panel = ttk.Frame(pair)
            panel.grid(row=0, column=column, sticky='nsew', padx=(0, 6) if column == 0 else (6, 0))
            panel.columnconfigure(0, weight=1)
            panel.rowconfigure(1, weight=1)
            heading = ttk.Label(panel, text='前批結尾' if column == 0 else '後批開頭', width=1, wraplength=300)
            heading.grid(row=0, column=0, columnspan=2, sticky='ew')
            self.headings.append(heading)
            text = tk.Text(panel, width=1, height=2, wrap='word', state='disabled', font=('Microsoft JhengHei', 11))
            text.grid(row=2 if self.movie else 1, column=0, sticky='nsew')
            if self.movie:
                panel.rowconfigure(1,weight=0)
                panel.rowconfigure(2,weight=1)
                frame=ttk.Label(panel,anchor='center')
                frame.grid(row=1,column=0,columnspan=2,sticky='ew')
                self.frame_labels.append(frame)
            from .ui_controls import AutoHideScrollbar
            scrollbar = AutoHideScrollbar(panel, command=text.yview)
            scrollbar.grid(row=2 if self.movie else 1, column=1, sticky='ns')
            text.configure(yscrollcommand=scrollbar.set)
            edit = ttk.Button(panel, text='← 校對前批結尾' if column == 0 else '校對後批開頭 →',
                              command=partial(self.edit, side))
            edit.grid(row=3 if self.movie else 2, column=0, columnspan=2, sticky='ew', pady=(4, 0))
            setattr(self, side+'_text', text)
            setattr(self, side+'_edit', edit)
        self.warning = ttk.Frame(self)
        self.warning.grid(row=3, column=0, sticky='ew', pady=4)
        self.warning.columnconfigure(0, weight=1)
        self.warning_title = ttk.Label(self.warning, text='', foreground='#704c14', width=1)
        self.warning_title.grid(row=0, column=0, sticky='ew')
        self.ack_control = ttk.Checkbutton(self.warning, text='我已檢查此接點，保留內容並繼續',
                                         variable=self.accepted, command=self.acknowledge)
        self.ack_control.grid(row=0, column=1, sticky='e')
        self.warning_copy = ttk.Label(self.warning, text='', foreground='#704c14', wraplength=620)
        self.warning_copy.grid(row=1, column=0, columnspan=2, sticky='ew')
        options = ttk.Frame(self)
        options.grid(row=4, column=0, sticky='ew', pady=4)
        options.columnconfigure(3, weight=1)
        ttk.Label(options, text='額外交接停頓').grid(row=0, column=0)
        self.pause_control = ttk.Combobox(options, textvariable=owner.pause, values=('0', '0.5', '1', '2', '5'), width=6)
        self.pause_control.grid(row=0, column=1, padx=6)
        ttk.Label(options, text='秒 · 全書共用 · 0～5 秒').grid(row=0, column=2)
        ttk.Label(options, text='前後各播').grid(row=0, column=4)
        self.clip_control = ttk.Combobox(options, textvariable=self.clip, values=('3', '5', '10'), state='readonly', width=3)
        self.clip_control.grid(row=0, column=5, padx=6)
        self.clip_control.bind('<<ComboboxSelected>>', lambda e: self.stop())
        ttk.Label(options, text='秒').grid(row=0, column=6)
        self.timeline = ttk.Label(self, text='', anchor='center')
        self.timeline.grid(row=5, column=0, sticky='ew')
        ttk.Label(self, text='實際總間隔包含來源頭尾靜音；設定值只代表新增靜音。新增靜音不顯示字幕。',
                  wraplength=620).grid(row=6, column=0, sticky='ew', pady=4)
        playback = ttk.Frame(self)
        playback.grid(row=7, column=0, sticky='ew', pady=4)
        playback.columnconfigure(2, weight=1)
        self.play_button = ttk.Button(playback, text='播放交接試聽', style='Primary.TButton', command=self.play)
        self.play_button.grid(row=0, column=0)
        self.stop_button = ttk.Button(playback, text='停止試聽', command=self.stop)
        self.stop_button.grid(row=0, column=1, padx=6)
        self.status = ttk.Label(playback, text='重用批次音訊，不呼叫 TTS。', width=1, wraplength=350)
        self.status.grid(row=0, column=2, sticky='ew')
        self.cancel_button = ttk.Button(playback, text='取消準備', command=self.stop)
        self.cancel_button.grid(row=0, column=3)
        self.progress = ttk.Progressbar(self, mode='indeterminate')
        self.shell_footer = actions = self.app.shell.create_footer(self)
        actions.columnconfigure(1, weight=1)
        self.back_button = actions.button('← 返回全書合併',owner.return_from_joins,role='back')
        self.back_button.grid(row=0, column=0)
        ttk.Label(actions, text='返回保留輸入；按儲存才會保存。').grid(row=0, column=1, sticky='w', padx=6)
        self.save_button = actions.button('儲存設定並返回 →',self.save)
        self.save_button.grid(row=0, column=2)
        self.bind('<Configure>', self.resized)

    def resized(self, event):
        if event.widget is self:
            for heading in self.headings:
                heading.configure(wraplength=max(100, event.width//2-20))
            self.warning_copy.configure(wraplength=max(100, event.width-12))
            self.status.configure(wraplength=max(100, event.width-350))

    def has_work(self):
        return self.job is not None or self.info_job is not None

    def load(self):
        self.remember_reading()
        self.stop()
        if self.has_work():
            self.status.configure(text='請等待目前試聽停止，再返回檢查。')
            return
        ids = list(self.owner.selected)
        async def inspect():
            joins=self.flow.inspect_video_merge_joins(ids) if self.movie else self.flow.inspect_assembly_joins(ids)
            if self.movie:
                from .video_merge import source_ref
                from .total_video import background_frame
                from .assembly import checked_file_async
                for join in joins:
                    for side in ('left','right'):
                        item=join[side]
                        if item['valid']:
                            try:
                                ref=source_ref(self.flow,item['batch_id'])
                                path=await checked_file_async(self.flow,ref['mp4'])
                                item['frame']=await background_frame(path,ref['duration_ms']/1000 if side=='left' else 0,last=side=='left')
                            except ProjectError as error:
                                item.update(valid=False,error=str(error))
            return joins
        self.info_job = VoiceJob(inspect, timeout=None)
        self.status.configure(text='正在讀取接點文字與版本…')
        self.update_controls()
        self.schedule()

    @staticmethod
    def fill(widget, text):
        if widget.get('1.0', 'end-1c') == text:
            return
        widget.configure(state='normal')
        widget.delete('1.0', 'end')
        widget.insert('1.0', text)
        widget.configure(state='disabled')

    def render(self):
        if not self.movie:
            return self.render_audio()
        self.index = max(0, min(self.index, len(self.joins)-1))
        self.pair_control.configure(values=[f'{i+1}／{len(self.joins)}　{j["left"]["name"]} → {j["right"]["name"]}'
                                            for i, j in enumerate(self.joins)])
        if not self.joins:
            self.status.configure(text='請選取至少兩個批次。')
            return
        self.pair_control.current(self.index)
        join = self.joins[self.index]
        self.frame_photos=[]
        for index, side in enumerate(('left', 'right')):
            item = join[side]
            pages = item['pages']
            title = f'{"前批結尾" if side == "left" else "後批開頭"} · {item["name"]}'
            if item['kind'] == 'pdf':
                title += f'（物理頁 {pages["start"]}～{pages["end"]}）'
            self.headings[index].configure(text=title)
            if self.movie:
                if item.get('frame'):
                    image=Image.open(BytesIO(item['frame']));image.thumbnail((240,100))
                    photo=ImageTk.PhotoImage(image,master=self.frame_labels[index]);self.frame_photos.append(photo)
                    self.frame_labels[index].configure(image=photo)
                else:self.frame_labels[index].configure(image='')
            self.fill(getattr(self, side+'_text'), item['text'] if item['valid'] else item['error'])
        warning = join['warning']
        if warning:
            labels = dict(overlap='頁碼重疊', gap='頁碼缺口', reverse='手動倒序')
            page_range = str(warning['start']) if warning['start'] == warning['end'] else f'{warning["start"]}～{warning["end"]}'
            self.warning_title.configure(text=f'{labels[warning["kind"]]} · 第 {page_range} 頁')
            a, b = join['left']['pages'], join['right']['pages']
            self.warning_copy.configure(text=f'前批：{a["start"]}～{a["end"]}；後批：{b["start"]}～{b["end"]}。不自動去重、補頁或補半句。來源：{warning["source_name"]}')
            self.warning.grid()
        else:
            self.warning.grid_remove()
        self.accepted.set(join['key'] in self.owner.accepted_joins)
        self.update_controls()

    def remember_reading(self):
        if not self.movie and self._displayed_key is not None and self._reading_restore is None:
            self._reading_positions[self._displayed_key] = (
                self._source_signature, self.left_text.yview()[0], self.right_text.yview()[0])

    def cancel_reading_restore(self, _event=None):
        # An explicit reader gesture takes priority over queued initial layout.
        if self._reading_timer is not None:
            self.after_cancel(self._reading_timer)
            self._reading_timer = None
        self._reading_restore = None
        self._reading_anchor = self._reading_reflow = None

    def reflow_reading(self, _event=None):
        # Keep the initial endpoint anchored through later native resizes.
        # A reader gesture releases this anchor before normal Tk scrolling.
        if (self._reading_anchor is not None and self._reading_timer is None
                and self.content_kind == 'source' and self.winfo_viewable()):
            self._reading_restore = self._reading_anchor
            self._reading_timer = self.after_idle(self._reading_reflow)

    def render_audio(self):
        self.remember_reading()
        restore = None
        self.index = max(0, min(self.index, len(self.joins)-1))
        self.pair_control.configure(values=[f'{i+1}／{len(self.joins)}　{j["left"]["name"]} → {j["right"]["name"]}'
                                            for i, j in enumerate(self.joins)])
        join = self.joins[self.index] if self.joins else None
        if join:
            self.pair_control.current(self.index)
            signature = tuple((join[s]['text'], join[s]['valid'], join[s].get('error', '')) for s in ('left','right'))
            unchanged = self._displayed_key == join['key'] and self._source_signature == signature
            if not unchanged:
                self.content_kind = 'source'
                for side in ('left','right'):
                    item = join[side]
                    self.fill(getattr(self, side+'_text'), item['text'] if item['valid'] else item['error'])
                previous = self._reading_positions.get(join['key'])
                restore = (join['key'], signature,
                           previous[1:] if previous and previous[0] == signature else (1., 0.))
            self._displayed_key, self._source_signature = join['key'], signature
            self.accepted.set(join['key'] in self.owner.accepted_joins)
            self.audio_headings()
        else:
            self.cancel_reading_restore()
            self._displayed_key = self._source_signature = None
            self.accepted.set(False)
            for text in (self.left_text, self.right_text):
                self.fill(text, '')
        self.workspace.render(join)
        self.update_controls()
        if restore is not None:
            self.restore_reading_position(restore)

    def restore_reading_position(self, restore):
        """One keyed restore path for initial load, pairs and secondary views."""
        self.cancel_reading_restore()
        self._reading_restore = restore
        self._reading_anchor = restore
        measured = None
        placed_views = None
        def apply_reading():
            nonlocal measured, placed_views
            self._reading_timer = None
            if (not self.winfo_exists() or self._reading_restore is not restore
                    or (self._displayed_key, self._source_signature) != restore[:2]):
                return
            geometry = tuple((w.winfo_width(),w.winfo_height()) for w in
                             (self, self.left_text, self.right_text, self.workspace.footer))
            views = (self.left_text.yview(),self.right_text.yview())
            if measured == geometry and placed_views == views:
                self._reading_restore = None
                return
            measured = geometry
            for text,position in zip((self.left_text,self.right_text),restore[2]):
                if position == 1.:
                    # Anchor an index. Text's fractional total can still be
                    # estimated while newly loaded line metrics resolve.
                    text.yview('end')
                elif position == 0.:
                    text.yview('1.0')
                else:
                    text.yview_moveto(position)
            placed_views = (self.left_text.yview(),self.right_text.yview())
            # Confirm both geometry and actual Text views across the
            # shell's 60ms reflow; line metrics can settle after geometry.
            self._reading_timer = self.after(80, apply_reading)
        # Run after the new pair and warning/footer tracks have settled.
        self._reading_reflow = apply_reading
        self._reading_timer = self.after_idle(apply_reading)

    def audio_headings(self):
        if self.movie or not self.joins:
            return
        join = self.joins[self.index]
        for i, side in enumerate(('left','right')):
            name = ('前批字幕' if i == 0 else '後批字幕') if self.content_kind == 'subtitle' else ('前批結尾' if i == 0 else '後批開頭')
            self.headings[i].full_text = f'{name} · {join[side]["name"]}'
            self.headings[i].configure(text=self.headings[i].full_text)

    def acknowledge(self):
        if self.joins:
            key = self.joins[self.index]['key']
            if self.accepted.get():
                self.owner.accepted_joins.add(key)
            else:
                self.owner.accepted_joins.discard(key)
            self.owner.saved_label.configure(text='接點確認尚未儲存')
            self.owner.update_controls()

    def select_pair(self, event=None):
        self.remember_reading()
        self.stop()
        self.index = self.pair_control.current()
        self.render()

    def move(self, delta):
        self.remember_reading()
        self.stop()
        self.index += delta
        self.render()

    def save(self):
        self.stop()
        if self.has_work():
            self.status.configure(text='請等待試聽停止後再儲存。')
        elif self.owner.save():
            if not self.movie:
                self.workspace.save_error = False
                self.update_controls()
            self.owner.return_from_joins()
        elif not self.movie:
            self.workspace.save_error = True
            self.status.configure(text='設定未寫入，輸入已保留。'+self.owner.status.cget('text'))
            self.update_controls()

    def edit(self, side):
        if not self.joins or not self.app.may_leave():
            return
        self.stop()
        self.owner.edit_return = True
        self.app.batch_id = self.joins[self.index][side]['batch_id']
        self.app.step = 2
        self.app.refresh()
        self.app.notice.configure(text='修改後請重新確認朗讀稿及製作批次音訊，再返回接點檢查。')

    def play(self):
        try:
            self.owner.require_current()
            if self.has_work():
                return
            start = self.flow.start_video_join_preview if self.movie else self.flow.start_assembly_join_preview
            self.job = start(list(self.owner.selected), self.index,
                         pause_ms=self.owner.pause_ms(), clip_ms=int(self.clip.get())*1000)
            self._preview_failed = False
            self.allow_play = True
            self.status.configure(text='正在驗證來源並準備接點試聽…')
            self.update_controls()
            self.schedule()
        except (ProjectError, ValueError) as error:
            self._preview_failed = True
            self.status.configure(text=str(error))
            self.app.notify(str(error), kind='error')
            self.update_controls()

    def restore_pair(self):
        self.pair.grid(row=2,column=0,sticky='nsew')
        self.stop()

    def stop(self):
        if self.movie_player is not None:
            self.movie_player.stop()
            self.movie_player.grid_remove()
            self.pair.grid(row=2,column=0,sticky='nsew')
        self.allow_play = self.playing = False
        try:
            self.player.stop()
            if self.job is not None:
                self.job.cancel()
                if self.job.wait(0) and (self.movie_player is None or not self.movie_player.has_work()):
                    if self.movie_player is not None and self.movie_player.has_work():
                        self.schedule()
                        return
                    self.flow.discard_assembly_join_preview(self.job)
                    self.job = None
            if self.info_job is not None:
                self.info_job.cancel()
            self.status.configure(text='試聽已停止。' if not self.has_work() else '取消中，正在釋放檔案…')
        except ProjectError as error:
            self.status.configure(text=str(error))
        if self.has_work():
            self.schedule()
        self.update_controls()

    def schedule(self):
        if self.timer is not None:
            self.after_cancel(self.timer)
        self.timer = self.after(100, self.poll)

    def poll(self):
        self.timer = None
        try:
            if self.info_job is not None and self.info_job.wait(0):
                job, self.info_job = self.info_job, None
                if job.state['status'] == 'completed':
                    self.joins = job.result
                    self.render()
                    self.status.configure(text='確認稿節錄。播放後顯示本次片段對應字幕文字。' if self.movie else self.workspace.NORMAL_HINT)
                elif job.state['status'] == 'failed':
                    raise ProjectError(job.state['error'])
            if self.job is not None and self.job.wait(0):
                if not self.allow_play or self.job.state['status'] != 'completed':
                    state = self.job.state
                    if self.movie_player is not None and self.movie_player.has_work():
                        self.schedule()
                        return
                    self.flow.discard_assembly_join_preview(self.job)
                    self.job = None
                    self.status.configure(text='已取消接點試聽。' if state['status'] == 'cancelled' else state['error'] or '試聽已停止。')
                elif not self.playing:
                    result = self.flow.finish_video_join_preview(self.job) if self.movie else self.flow.finish_assembly_join_preview(self.job)
                    if (self.winfo_viewable() and self.app.production.current is self.owner
                            and self.app.flow is self.flow and self.app.step == 4):
                        if self.movie:
                            from .movie_playback import MoviePlayback
                            if self.movie_player is None:
                                self.movie_player=MoviePlayback(self,self.flow,self.restore_pair)
                            self.pair.grid_remove()
                            self.movie_player.grid(row=2,column=0,sticky='nsew')
                            self.movie_player.start(result)
                        else:
                            self.player.play(Path(result['path']))
                        self.playing = True
                        self.cancel_reading_restore()
                        self.fill(self.left_text, result['left_text'] or '此片段沒有字幕文字。')
                        self.fill(self.right_text, result['right_text'] or '此片段沒有字幕文字。')
                        if not self.movie:
                            self.content_kind = 'subtitle'
                            self.audio_headings()
                        self.status.configure(text=f'正在試聽 · {result["duration_ms"]/1000:g} 秒 · 不呼叫 TTS')
                    else:
                        self.stop()
                elif (not self.movie_player.has_work() if self.movie and self.movie_player else not self.player.playing()):
                    self.stop()
                    self.status.configure(text='接點試聽已結束。')
        except (ProjectError, OSError) as error:
            self._preview_failed = True
            self.stop()
            self.status.configure(text=str(error))
            self.app.notify(str(error), kind='error')
        self.update_controls()
        if self.has_work():
            self.schedule()

    def update_controls(self):
        preparing = self.info_job is not None or self.job is not None and not self.playing
        busy = preparing or self.owner.job is not None or self.owner.check_job is not None or self.owner.production_busy
        try:
            pause = self.owner.pause_ms()
            valid = bool(self.joins) and all(self.joins[self.index][s]['valid'] for s in ('left', 'right'))
            if self._invalid_pause and not self.movie:
                self.status.configure(text=self.workspace.NORMAL_HINT)
            self._invalid_pause = False
            if self.movie:self.timeline.configure(text=f'前批結尾   →   ＋ {pause/1000:g} 秒額外靜音   →   後批開頭')
        except ProjectError:
            valid = False
            self._invalid_pause = True
            if self.movie:self.timeline.configure(text='請輸入 0～5 秒，最多三位小數。')
            else:self.status.configure(text='請輸入 0～5 秒，最多三位小數。')
        if self.movie:
            self.play_button.configure(text='播放影音接點')
        else:
            self.play_button.configure(text='重試試聽' if self._preview_failed else '準備中' if preparing else '播放接點')
        self.play_button.configure(state='normal' if valid and not busy and not self.playing else 'disabled')
        self.stop_button.configure(state='normal' if self.job is not None else 'disabled')
        self.save_button.configure(state='normal' if valid and not busy else 'disabled')
        self.pause_control.configure(state='disabled' if busy else 'normal')
        self.clip_control.configure(state='disabled' if busy else 'readonly')
        self.pair_control.configure(state='disabled' if busy else 'readonly')
        self.previous.configure(state='normal' if self.index > 0 and not busy else 'disabled')
        self.next.configure(state='normal' if self.index < len(self.joins)-1 and not busy else 'disabled')
        for button in (self.left_edit, self.right_edit):
            button.configure(state='normal' if self.joins and not preparing else 'disabled')
        self.ack_control.configure(state='disabled' if busy else 'normal')
        if not self.movie:
            self.workspace.update(preparing, busy, valid)
        elif preparing:
            self.cancel_button.grid()
            self.progress.grid(row=8, column=0, sticky='ew')
            self.progress.start(15)
        else:
            self.cancel_button.grid_remove()
            self.progress.stop()
            self.progress.grid_remove()

    def release(self):
        if not self.movie:
            self.cancel_reading_restore()
        self.stop()
        if self.movie_player is not None: self.movie_player.release()
        if self.timer is not None:
            self.after_cancel(self.timer)
            self.timer = None
        self.progress.stop()
        if not self.movie:
            self.workspace.release()

    def destroyed(self, event):
        if event.widget is self:
            self.cancel_reading_restore()
            self.workspace.destroy()
