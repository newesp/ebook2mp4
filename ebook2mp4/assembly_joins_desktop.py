"""Join inspection inside the existing book assembly workspace."""
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
        self.job = self.info_job = self.timer = None
        self.player = PreviewPlayer()
        self.playing = self.allow_play = False
        self.joins: list[dict] = []
        self.index = 0
        self.clip = tk.StringVar(value='5')
        self.accepted = tk.BooleanVar(value=False)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1, minsize=70)
        ttk.Label(self, text='3 檢查交接接點 · 對照文字，再試聽', style='Heading.TLabel').grid(row=0, column=0, sticky='w')
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
        pair = ttk.Frame(self)
        pair.grid(row=2, column=0, sticky='nsew')
        pair.columnconfigure((0, 1), weight=1, uniform='join')
        pair.rowconfigure(0, weight=1)
        self.headings = []
        for column, side in enumerate(('left', 'right')):
            panel = ttk.Frame(pair)
            panel.grid(row=0, column=column, sticky='nsew', padx=(0, 6) if column == 0 else (6, 0))
            panel.columnconfigure(0, weight=1)
            panel.rowconfigure(1, weight=1)
            heading = ttk.Label(panel, text='前批結尾' if column == 0 else '後批開頭', width=1, wraplength=300)
            heading.grid(row=0, column=0, columnspan=2, sticky='ew')
            self.headings.append(heading)
            text = tk.Text(panel, width=1, height=2, wrap='word', state='disabled', font=('Microsoft JhengHei', 11))
            text.grid(row=1, column=0, sticky='nsew')
            scrollbar = ttk.Scrollbar(panel, command=text.yview)
            scrollbar.grid(row=1, column=1, sticky='ns')
            text.configure(yscrollcommand=scrollbar.set)
            edit = ttk.Button(panel, text='← 校對前批結尾' if column == 0 else '校對後批開頭 →',
                              command=partial(self.edit, side))
            edit.grid(row=2, column=0, columnspan=2, sticky='ew', pady=(4, 0))
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
        actions = ttk.Frame(self)
        actions.grid(row=9, column=0, sticky='ew', pady=4)
        actions.columnconfigure(1, weight=1)
        self.back_button = ttk.Button(actions, text='← 返回全書合併', command=owner.return_from_joins)
        self.back_button.grid(row=0, column=0)
        ttk.Label(actions, text='返回保留輸入；按儲存才會保存。').grid(row=0, column=1, sticky='w', padx=6)
        self.save_button = ttk.Button(actions, text='儲存設定並返回 →', command=self.save)
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
        self.stop()
        if self.has_work():
            self.status.configure(text='請等待目前試聽停止，再返回檢查。')
            return
        ids = list(self.owner.selected)
        async def inspect():
            return self.flow.inspect_assembly_joins(ids)
        self.info_job = VoiceJob(inspect, timeout=None)
        self.status.configure(text='正在讀取接點文字與版本…')
        self.update_controls()
        self.schedule()

    @staticmethod
    def fill(widget, text):
        widget.configure(state='normal')
        widget.delete('1.0', 'end')
        widget.insert('1.0', text)
        widget.configure(state='disabled')

    def render(self):
        self.index = max(0, min(self.index, len(self.joins)-1))
        self.pair_control.configure(values=[f'{i+1}／{len(self.joins)}　{j["left"]["name"]} → {j["right"]["name"]}'
                                            for i, j in enumerate(self.joins)])
        if not self.joins:
            self.status.configure(text='請選取至少兩個批次。')
            return
        self.pair_control.current(self.index)
        join = self.joins[self.index]
        for index, side in enumerate(('left', 'right')):
            item = join[side]
            pages = item['pages']
            title = f'{"前批結尾" if side == "left" else "後批開頭"} · {item["name"]}'
            if item['kind'] == 'pdf':
                title += f'（物理頁 {pages["start"]}～{pages["end"]}）'
            self.headings[index].configure(text=title)
            self.fill(getattr(self, side+'_text'), item['text'] if item['valid'] else item['error'])
        warning = join['warning']
        if warning:
            labels = dict(overlap='頁碼重疊', gap='頁碼缺口', reverse='手動倒序')
            page_range = str(warning['start']) if warning['start'] == warning['end'] else f'{warning["start"]}～{warning["end"]}'
            self.warning_title.configure(text=f'{labels[warning["kind"]]} · {warning["source_name"]} 第 {page_range} 頁')
            a, b = join['left']['pages'], join['right']['pages']
            self.warning_copy.configure(text=f'前批：{a["start"]}～{a["end"]}；後批：{b["start"]}～{b["end"]}。不自動去重、補頁或補半句。')
            self.warning.grid()
        else:
            self.warning.grid_remove()
        self.accepted.set(join['key'] in self.owner.accepted_joins)
        self.update_controls()

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
        self.stop()
        self.index = self.pair_control.current()
        self.render()

    def move(self, delta):
        self.stop()
        self.index += delta
        self.render()

    def save(self):
        self.stop()
        if self.has_work():
            self.status.configure(text='請等待試聽停止後再儲存。')
        elif self.owner.save():
            self.owner.return_from_joins()

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
            self.job = self.flow.start_assembly_join_preview(list(self.owner.selected), self.index,
                         pause_ms=self.owner.pause_ms(), clip_ms=int(self.clip.get())*1000)
            self.allow_play = True
            self.status.configure(text='正在驗證來源並準備接點試聽…')
            self.update_controls()
            self.schedule()
        except (ProjectError, ValueError) as error:
            self.status.configure(text=str(error))
            self.app.notify(str(error), kind='error')

    def stop(self):
        self.allow_play = self.playing = False
        try:
            self.player.stop()
            if self.job is not None:
                self.job.cancel()
                if self.job.wait(0):
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
                    self.status.configure(text='確認稿節錄。播放後顯示本次片段對應字幕文字。')
                elif job.state['status'] == 'failed':
                    raise ProjectError(job.state['error'])
            if self.job is not None and self.job.wait(0):
                if not self.allow_play or self.job.state['status'] != 'completed':
                    state = self.job.state
                    self.flow.discard_assembly_join_preview(self.job)
                    self.job = None
                    self.status.configure(text='已取消接點試聽。' if state['status'] == 'cancelled' else state['error'] or '試聽已停止。')
                elif not self.playing:
                    result = self.flow.finish_assembly_join_preview(self.job)
                    if (self.winfo_viewable() and self.app.production.current is self.owner
                            and self.app.flow is self.flow and self.app.step == 4):
                        self.player.play(Path(result['path']))
                        self.playing = True
                        self.fill(self.left_text, result['left_text'] or '此片段沒有字幕文字。')
                        self.fill(self.right_text, result['right_text'] or '此片段沒有字幕文字。')
                        self.status.configure(text=f'正在試聽 · {result["duration_ms"]/1000:g} 秒 · 不呼叫 TTS')
                    else:
                        self.stop()
                elif not self.player.playing():
                    self.stop()
                    self.status.configure(text='接點試聽已結束。')
        except (ProjectError, OSError) as error:
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
            self.timeline.configure(text=f'前批結尾   →   ＋ {pause/1000:g} 秒額外靜音   →   後批開頭')
        except ProjectError:
            valid = False
            self.timeline.configure(text='請輸入 0～5 秒，最多三位小數。')
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
        if preparing:
            self.cancel_button.grid()
            self.progress.grid(row=8, column=0, sticky='ew')
            self.progress.start(15)
        else:
            self.cancel_button.grid_remove()
            self.progress.stop()
            self.progress.grid_remove()

    def release(self):
        self.stop()
        if self.timer is not None:
            self.after_cancel(self.timer)
            self.timer = None
        self.progress.stop()
