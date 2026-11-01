"""Second step of book production, in the existing main window."""
from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
import shutil
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog

from PIL import Image, ImageTk

from .voice import VoiceJob
from .voice_media import PreviewPlayer
from .workflow import ProjectError


class TotalVideoPage(ttk.Frame):
    kind = 'video'
    details_panel: ttk.Frame

    def __init__(self, app):
        super().__init__(app.production.host)
        self.app, self.flow = app, app.flow
        self.job = self.check_job = self.timer = None
        self.production_busy = self.closing = self.loaded = self.dirty = False
        self.product = self.audio = self.pending_image = self.preview_image = self.photo = None
        self.action = ''
        self.last_status = ''
        self.publish_error = False
        self.player = PreviewPlayer()
        self.playback_folder: Path | None = None
        self.playback_image = None
        self.resolution = tk.StringVar(value='1080p')
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        steps = ttk.Frame(self)
        steps.grid(row=0, column=0, sticky='ew', pady=(0, 6))
        ttk.Button(steps, text='① 合併音訊', command=app.total_audio).pack(side='left')
        ttk.Label(steps, text=' → ').pack(side='left')
        ttk.Button(steps, text='② 製作影片', style='CompactActive.TButton').pack(side='left')
        ttk.Label(steps, text='本機製片 · 不呼叫 TTS').pack(side='right')
        source = ttk.Frame(self)
        source.grid(row=1, column=0, sticky='ew', pady=(0, 6))
        source.columnconfigure(0, weight=1)
        self.source_info = ttk.Label(source, text='正在檢查總音訊…', width=1)
        self.source_info.grid(row=0, column=0, sticky='ew')
        self.repair_button = ttk.Button(source, text='更新總音訊 →', command=app.total_audio)
        self.repair_button.grid(row=0, column=1)
        self.detail_button = ttk.Button(source, text='來源詳情 ▸', command=self.details)
        self.detail_button.grid(row=0, column=2)
        self.editor = editor = ttk.Frame(self)
        editor.grid(row=2, column=0, sticky='nsew')
        editor.columnconfigure(0, weight=2, uniform='video')
        editor.columnconfigure(1, weight=3, uniform='video')
        editor.rowconfigure(0, weight=1)
        material = ttk.Frame(editor)
        material.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        material.columnconfigure(0, weight=1)
        ttk.Label(material, text='選擇全片共用圖片', style='Heading.TLabel').grid(row=0, column=0, sticky='w')
        self.choose_button = ttk.Button(material, text='選擇圖片…', command=self.choose)
        self.choose_button.grid(row=1, column=0, sticky='ew', pady=6)
        self.image_info = ttk.Label(material, text='尚未選擇圖片。請選 JPEG 或 PNG。', width=1, wraplength=250)
        self.image_info.grid(row=2, column=0, sticky='ew')
        ttk.Label(material, text='圖片將複製到專案。\n保持比例，黑邊補齊。\n透明區黑底，不拉伸、不裁切。',
                  wraplength=250).grid(row=3, column=0, sticky='w', pady=8)
        preview = ttk.Frame(editor)
        preview.grid(row=0, column=1, sticky='nsew')
        preview.columnconfigure(0, weight=1)
        preview.rowconfigure(1, weight=1)
        ttk.Label(preview, text='檢查畫面，再選解析度', style='Heading.TLabel').grid(row=0, column=0, sticky='w')
        self.canvas = tk.Canvas(preview, width=1, height=1, highlightthickness=0, background='#e9eee6')
        self.canvas.grid(row=1, column=0, sticky='nsew', pady=6)
        self.canvas.bind('<Configure>', self.draw)
        controls = ttk.Frame(preview)
        controls.grid(row=2, column=0, sticky='ew')
        controls.columnconfigure(1, weight=1)
        ttk.Label(controls, text='解析度').grid(row=0, column=0, padx=(0, 6))
        self.resolution_control = ttk.Combobox(controls, textvariable=self.resolution, state='readonly',
                                             values=('1080p', '720p'), width=7)
        self.resolution_control.grid(row=0, column=1, sticky='w')
        ttk.Label(controls, text='16:9 · 30 fps').grid(row=0, column=2)
        self.explanation = ttk.Label(self, text='沿用完整總 MP3／SRT。交接停頓已在音訊內，不再添加。', wraplength=650)
        self.explanation.grid(row=3, column=0, sticky='ew', pady=6)
        self.status = ttk.Label(self, text='請選擇圖片，再檢查右側畫面。', width=1, wraplength=650)
        self.status.grid(row=4, column=0, sticky='ew', pady=4)
        self.progress = ttk.Progressbar(self, maximum=100)
        actions = ttk.Frame(self)
        actions.grid(row=6, column=0, sticky='ew', pady=4)
        actions.columnconfigure(1, weight=1)
        self.back_button = ttk.Button(actions, text='← 返回合併音訊', command=app.total_audio)
        self.back_button.grid(row=0, column=0)
        ttk.Label(actions, text='製作時一併儲存設定', width=1).grid(row=0, column=1, sticky='ew', padx=6)
        self.cancel_button = ttk.Button(actions, text='取消任務', command=self.cancel)
        self.cancel_button.grid(row=0, column=2, padx=6)
        self.start_button = ttk.Button(actions, text='製作總 MP4', command=self.start, style='Primary.TButton')
        self.start_button.grid(row=0, column=3)
        result = ttk.Frame(self)
        result.grid(row=7, column=0, sticky='ew', pady=4)
        result.columnconfigure(0, weight=1)
        self.result_info = ttk.Label(result, text='尚無總影片。', width=1)
        self.result_info.grid(row=0, column=0, sticky='ew')
        self.outputs_button = ttk.Menubutton(result, text='成品操作 ▾')
        self.outputs_button.grid(row=0, column=1)
        self.menu = tk.Menu(self.outputs_button, tearoff=False, postcommand=self.output_menu)
        self.outputs_button.configure(menu=self.menu)
        self.resolution.trace_add('write', lambda *_: self.changed())
        self.bind('<Configure>', self.resized)
        self.update_controls()

    def resized(self, event):
        if event.widget is self:
            self.status.configure(wraplength=max(180, event.width-12))
            self.explanation.configure(wraplength=max(180, event.width-12))
            self.image_info.configure(wraplength=max(140, event.width*2//5-12))

    def draw(self, event=None):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        self.canvas.delete('all')
        fw, fh = min(w, h*16/9), min(h, w*9/16)
        x, y = w/2, h/2
        self.canvas.create_rectangle(x-fw/2, y-fh/2, x+fw/2, y+fh/2, fill='black', outline='')
        original = self.playback_image if self.player.alias else self.preview_image
        if original:
            scale = min(fw/original.width, fh/original.height)
            image = original.resize((max(1, round(original.width*scale)), max(1, round(original.height*scale))), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(image, master=self.canvas)
            self.canvas.create_image(x, y, image=self.photo)
        else:
            self.canvas.create_text(x, y, text='選擇圖片後顯示預覽', fill='white', width=max(1, int(fw)-16))

    def changed(self):
        self.dirty = True
        self.stop()
        self.update_controls()

    def output_menu(self):
        self.menu.delete(0, 'end')
        locked = self.job is not None or self.check_job is not None or self.production_busy
        for label, command, enabled in (
                ('儲存視覺設定', self.save, not locked),
                ('播放上一版影片' if self.product and (self.product['stale'] or self.dirty) else '播放總影片',
                 lambda: self.file_action('play'), bool(self.product) and not locked),
                ('停止播放', self.stop, self.player.alias is not None),
                ('另存 MP4／SRT', self.export, bool(self.product) and not locked),
                ('開啟資料夾', lambda: self.file_action('folder'), bool(self.product) and not locked)):
            self.menu.add_command(label=label, command=command, state='normal' if enabled else 'disabled')

    def require_current(self):
        if self.app.flow is not self.flow:
            raise ProjectError('書籍已切換。請返回目前書籍重新開啟製片頁。')
        if self.check_job is not None or self.job is not None:
            raise ProjectError('請等待目前操作停止。')

    def choose(self):
        path = filedialog.askopenfilename(parent=self.app.root, title='選擇全片共用圖片',
                                         filetypes=[('JPEG／PNG 圖片', '*.jpg *.jpeg *.png')])
        if not path:
            return
        try:
            self.require_current()
            self.stop()
            async def inspect():
                from .total_video import thumbnail
                image = self.flow.inspect_total_video_image(path)
                return image, thumbnail(image.data)
            self.action = 'image'
            self.check_job = VoiceJob(inspect, timeout=None)
            self.status.configure(text='正在檢查圖片…')
            self.update_controls()
            self.schedule()
        except ProjectError as error:
            self.report(error)

    def save(self):
        try:
            self.require_current()
            self.flow.save_total_video_settings(image=self.pending_image, resolution=self.resolution.get())
            self.pending_image = None
            self.dirty = False
            from .total_video import total_video
            try:
                self.product = total_video(self.flow, verify_media=False)
            except ProjectError:
                self.product = None  # A missing old movie must still permit rebuilding.
            self.status.configure(text='視覺設定已儲存。總音訊保留。')
            self.update_controls()
            return True
        except ProjectError as error:
            self.report(error)
            return False

    def start(self):
        if self.job is not None:
            if self.job.wait(0) and self.job.state['status'] == 'completed':
                self.publish()
            return
        if not self.save():
            return
        try:
            self.stop()
            self.job = self.flow.start_total_video()
            self.last_status = ''
            self.publish_error = False
            self.status.configure(text='開始製片。本次音訊、字幕、圖片及解析度已固定。')
            self.update_controls()
            self.schedule()
        except ProjectError as error:
            self.report(error)

    def publish(self):
        self.publish_error = False
        try:
            self.product = self.flow.finish_total_video(self.job)
            self.job = None
            self.production_busy = self.app.production.busy_for(self.flow)
            self.status.configure(text='總 MP4 已完成並保存。請播放檢查。')
            self.app.notify('總 MP4 已完成並保存。')
            self.update_controls()
        except ProjectError as error:
            self.publish_error = True
            self.report(error)

    def recheck(self):
        if self.job is not None or self.check_job is not None or self.closing:
            return
        async def inspect():
            from .total_video import inspect_video
            return await inspect_video(self.flow)
        self.action = 'inspect'
        self.check_job = VoiceJob(inspect, timeout=None)
        self.status.configure(text='正在檢查總音訊、圖片與影片版本…')
        self.update_controls()
        self.schedule()

    def file_action(self, action, target=None):
        if self.job is not None or self.check_job is not None:
            return
        self.stop()
        if action == 'play':
            if self.playback_folder is not None:
                return  # Keep the retained cleanup path until the old lock is released.
            self.playback_folder = Path(tempfile.mkdtemp(prefix='.video-preview-', dir=self.flow.root))
        async def operation():
            from .total_video import export, total_video, prepare_playback
            from .assembly import checked_file_async
            if action == 'export':
                await export(self.flow, target)
                return None
            product = total_video(self.flow, verify_media=False)
            if product is None:
                raise ProjectError('尚無成功總影片。')
            for kind in ('mp4', 'srt'):
                await checked_file_async(self.flow, product[kind])
            path = self.flow._path(product['mp4']['path'])
            if action == 'play':
                assert self.playback_folder is not None
                return await prepare_playback(self.flow, product, self.playback_folder)
            return path.parent if action == 'folder' else path
        self.action = action
        self.check_job = VoiceJob(operation, timeout=None)
        self.update_controls()
        self.schedule()

    def export(self):
        target = filedialog.asksaveasfilename(parent=self.app.root, title='另存總 MP4／SRT：輸入新資料夾名稱', initialfile='總影片成品')
        if target:
            self.file_action('export', target)

    def details(self):
        audio = self.audio
        text = ('總音訊版本：'+audio['id']+'\nMP3：'+audio['mp3']['path']+'\nSRT：'+audio['srt']['path'] if audio else '尚無有效總音訊。')
        text += '\n\nH.264／yuv420p · AAC-LC／48 kHz／立體聲 · faststart\n字幕以同版 SRT 一併另存。圖片顯示至音訊結束，不再次添加交接停頓。'
        if hasattr(self, 'details_panel') and self.details_panel.winfo_manager():
            self.details_panel.grid_remove()
            self.editor.grid()
            return
        if not hasattr(self, 'details_panel'):
            self.details_panel = ttk.Frame(self)
            self.details_panel.columnconfigure(0, weight=1)
            self.details_panel.rowconfigure(0, weight=1)
            self.details_text = tk.Text(self.details_panel, width=1, height=1, wrap='word', font=('Microsoft JhengHei', 10))
            self.details_text.grid(row=0, column=0, sticky='nsew')
            scroll = ttk.Scrollbar(self.details_panel, command=self.details_text.yview)
            scroll.grid(row=0, column=1, sticky='ns')
            self.details_text.configure(yscrollcommand=scroll.set)
            ttk.Button(self.details_panel, text='返回圖片預覽', command=self.details).grid(row=1, column=0)
        self.details_text.configure(state='normal')
        self.details_text.delete('1.0', 'end')
        self.details_text.insert('1.0', text)
        self.details_text.configure(state='disabled')
        self.editor.grid_remove()
        self.details_panel.grid(row=2, column=0, sticky='nsew')

    def poll(self):
        self.timer = None
        if self.check_job is not None and self.check_job.wait(0):
            task, self.check_job = self.check_job, None
            try:
                if task.state['status'] == 'cancelled':
                    self.status.configure(text='已取消檢查或檔案操作。')
                else:
                    value = task.result
                    if self.action == 'inspect':
                        self.audio, self.product = value['audio'], value['product']
                        if not self.loaded or not self.dirty:
                            self.resolution.set(value['visual']['resolution'])
                            self.dirty = False
                            self.preview_image = Image.open(BytesIO(value['preview'])) if value['preview'] else None
                            info = value['visual']['image']
                            self.image_info.configure(text=f'{info["name"]} · {info["width"]} × {info["height"]}' if info else '尚未選擇圖片。')
                        self.loaded = True
                        last = value['runs'][-1]['progress'] if value['runs'] else None
                        self.last_status = last['status'] if last else ''
                        previous = ('上次製片：'+dict(failed='失敗', cancelled='已取消', interrupted='已中斷').get(self.last_status, '')+
                                    '。'+last.get('error', '')+' 舊成品保留，可重試。'
                                    if last and self.last_status in ('failed', 'cancelled', 'interrupted') else '')
                        self.status.configure(text=value['warning'] or previous or '選擇圖片並檢查預覽，再製作總 MP4。')
                    elif self.action == 'image' and not self.closing:
                        self.pending_image, preview = value
                        self.preview_image = Image.open(BytesIO(preview))
                        self.dirty = True
                        self.image_info.configure(text=f'{self.pending_image.name} · {self.pending_image.width} × {self.pending_image.height}')
                        self.status.configure(text='圖片已就緒。請檢查預覽。')
                    elif self.action == 'play' and not self.closing and self.app.step == 4 and self.app.production.current is self:
                        self.playback_image = Image.open(BytesIO(value['frame']))
                        self.player.play(value['audio'])
                        self.status.configure(text='正在播放總影片的畫面與音軌。可在成品操作停止。')
                    elif self.action == 'folder' and not self.closing:
                        os.startfile(value)
                    elif self.action == 'export':
                        self.status.configure(text='總 MP4 與 SRT 已另存。')
                self.draw()
            except (ProjectError, OSError) as error:
                self.report(error)
            finally:
                if self.action == 'play' and self.player.alias is None:
                    self.cleanup_playback()
        if self.job is not None:
            stopped = self.job.wait(0)
            state = self.job.state
            if not stopped:
                self.progress.configure(value=state.get('completed', 0))
                self.status.configure(text='取消中，正在釋放媒體程序…' if state['status'] == 'cancelling' else
                                      f'{state.get("phase", "準備")} · {state.get("completed", 0)}%')
            elif self.closing or state['status'] != 'completed':
                try:
                    self.last_status = state['status']
                    self.flow.discard_total_video(self.job)
                    self.job = None
                    self.production_busy = self.app.production.busy_for(self.flow)
                    self.status.configure(text='已取消。舊成品保留。' if state['status'] == 'cancelled' else state['error'])
                except ProjectError as error:
                    self.publish_error = True
                    self.report(error)
            elif not self.publish_error:
                self.publish()
        if self.closing and self.job is None and self.check_job is None:
            self.stop()
            if self.playback_folder is not None:
                self.closing = False
                return
            self.photo = self.preview_image = self.pending_image = None
            self.destroy()
            return
        self.update_controls()
        try:
            if self.player.alias and not self.player.playing():
                self.cleanup_playback()
                self.draw()
                self.status.configure(text='影片播放已結束。')
        except ProjectError as error:
            self.report(error)
            self.stop()
        if self.job is not None and not self.publish_error or self.check_job is not None or self.player.alias:
            self.schedule()

    def update_controls(self):
        busy = self.job is not None or self.check_job is not None or self.production_busy
        valid = self.audio is not None and not self.audio['stale']
        image = self.pending_image is not None or self.preview_image is not None
        completed = self.job is not None and self.job.wait(0) and self.job.state['status'] == 'completed'
        self.start_button.configure(state='normal' if completed or valid and image and not busy else 'disabled',
                                    text='重試保存' if completed else '重試製片' if self.last_status in ('failed', 'cancelled', 'interrupted') else
                                    '更新總 MP4' if self.product else '製作總 MP4')
        self.choose_button.configure(state='disabled' if busy else 'normal')
        self.resolution_control.configure(state='disabled' if busy else 'readonly')
        audio = self.audio
        self.source_info.configure(text=f'總 MP3／SRT 有效 · {audio["duration_ms"]/1000:g} 秒' if valid and audio else '總音訊缺少或已失效，請先更新。')
        if valid:
            self.repair_button.grid_remove()
        else:
            self.repair_button.grid()
        if self.job is not None or self.check_job is not None:
            if self.check_job is not None:
                if str(self.progress.cget('mode')) != 'indeterminate':
                    self.progress.configure(mode='indeterminate')
                    self.progress.start(15)
            else:
                self.progress.stop()
                self.progress.configure(mode='determinate')
            self.progress.grid(row=5, column=0, sticky='ew')
            self.cancel_button.grid()
        else:
            self.progress.stop()
            self.progress.grid_remove()
            self.cancel_button.grid_remove()
        p = self.product
        self.result_info.configure(text=(f'{"待更新 · 上一版總影片" if p["stale"] or self.dirty else "目前總影片"} · '
            f'{p["duration_ms"]/1000:g} 秒 · {p["visual"]["resolution"]}' if p else '尚無總影片。'))

    def set_production_busy(self, busy):
        self.production_busy = busy
        self.update_controls()

    def schedule(self):
        if self.timer is not None:
            self.after_cancel(self.timer)
        self.timer = self.after(100, self.poll)

    def report(self, error):
        self.status.configure(text=str(error))
        self.app.notify(str(error), kind='error')

    def cancel(self):
        for task in (self.job, self.check_job):
            if task is not None:
                task.cancel()

    def stop(self):
        if self.check_job is not None and self.action == 'play':
            self.check_job.cancel()
        try:
            self.player.stop()
            if self.check_job is None or self.action != 'play':
                self.cleanup_playback()
            self.draw()
        except ProjectError as error:
            self.report(error)

    def cleanup_playback(self):
        self.playback_image = None
        if self.playback_folder is not None:
            try:
                shutil.rmtree(self.playback_folder)
                self.playback_folder = None
            except OSError:
                self.status.configure(text='播放暫存仍被占用。請停止播放後再關閉程式。')

    def close(self):
        self.closing = True
        self.stop()
        self.cancel()
        self.schedule()
