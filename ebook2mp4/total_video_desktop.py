"""Second step of book production, in the existing main window."""
from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
import shutil
import tempfile
import queue
import tkinter as tk
from tkinter import ttk, filedialog
from tkinter import font as tkfont

from PIL import Image, ImageTk

from .voice import VoiceJob
from .voice_media import PreviewPlayer
from .workflow import ProjectError


class TotalVideoPage(ttk.Frame):
    kind = 'video'
    details_panel: ttk.Frame

    def __init__(self, app, batch_id=None):
        super().__init__(app.production.host)
        self.app, self.flow = app, app.flow
        self.batch_id = batch_id
        self.video_flow = app.flow.batch_video_target(batch_id) if batch_id else app.flow
        self.return_page = app.narration if batch_id else app.total_audio
        self.job = self.check_job = self.timer = None
        self.production_busy = self.closing = self.loaded = self.dirty = False
        self.product = self.audio = self.pending_image = self.preview_image = self.photo = None
        self.action = ''
        self.last_status = ''
        self.publish_error = False
        self.player = PreviewPlayer()
        self.playback_folder: Path | None = None
        self.playback_image = None
        self.pending_background = None
        self.background_info = None
        self.saved_image_info = None
        self.frame_job = None
        self.frames: queue.Queue[tuple[bytes, int]] = queue.Queue(maxsize=1)
        self.preview_playing = False
        self.playback_audio = None
        self.source_kind = tk.StringVar(value='圖片（JPEG／PNG）')
        self.mode = tk.StringVar(value='循環播放（預設）')
        self.seek = tk.DoubleVar(value=0)
        self.resolution = tk.StringVar(value='1080p')
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        steps = ttk.Frame(self)
        steps.grid(row=0, column=0, sticky='ew', pady=(0, 6))
        ttk.Button(steps, text='① 合併音訊', command=self.return_page, style='Compact.TButton').pack(side='left')
        ttk.Label(steps, text=' → ').pack(side='left')
        ttk.Button(steps, text='② 製作影片', style='CompactActive.TButton').pack(side='left')
        ttk.Label(steps, text=(app.flow._batch(batch_id)['name']+' · 批次影片' if batch_id else '全書 · 總影片')).pack(side='right')
        source = ttk.Frame(self)
        source.grid(row=1, column=0, sticky='ew', pady=(0, 6))
        source.columnconfigure(0, weight=1)
        self.source_info = ttk.Label(source, text='正在檢查總音訊…', width=1)
        self.source_info.grid(row=0, column=0, sticky='ew')
        self.repair_button = ttk.Button(source, text='更新總音訊 →', command=self.return_page)
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
        ttk.Label(material, text='選擇全片共用素材', style='Heading.TLabel').grid(row=0, column=0, sticky='w')
        self.kind_control = ttk.Combobox(material, textvariable=self.source_kind, state='readonly',
                                        values=('圖片（JPEG／PNG）', '背景影片（MP4）'))
        self.kind_control.grid(row=1, column=0, sticky='ew', pady=4)
        self.kind_control.bind('<<ComboboxSelected>>', self.kind_changed)
        self.choose_button = ttk.Button(material, text='選擇圖片…', command=self.choose)
        self.choose_button.grid(row=2, column=0, sticky='ew', pady=4)
        self.image_info = ttk.Label(material, text='尚未選擇圖片。請選 JPEG 或 PNG。', width=1, wraplength=250)
        self.image_info.grid(row=3, column=0, sticky='ew')
        self.mode_label = ttk.Label(material, text='背景短於總音訊時')
        self.mode_label.grid(row=4, column=0, sticky='w', pady=(6, 0))
        self.mode_control = ttk.Combobox(material, textvariable=self.mode, state='readonly',
                                       values=('循環播放（預設）', '最後一格定格'))
        self.mode_control.grid(row=5, column=0, sticky='ew', pady=4)
        self.material_rule = ttk.Label(material, text='', wraplength=250)
        self.material_rule.grid(row=6, column=0, sticky='w', pady=4)
        self.material_note = ttk.Label(material, text='素材將複製到專案，供離線製片。\n保持比例，黑邊補齊。', wraplength=250)
        self.material_note.grid(row=7, column=0, sticky='w', pady=4)
        # Keep the material controls visible at the supported minimum height.
        # Detailed guidance belongs in the existing explanation row and details page.
        self.material_rule.grid_remove()
        self.material_note.grid_remove()
        preview = ttk.Frame(editor)
        preview.grid(row=0, column=1, sticky='nsew')
        preview.columnconfigure(0, weight=1)
        preview.rowconfigure(1, weight=1)
        ttk.Label(preview, text='檢查畫面，再選解析度', style='Heading.TLabel').grid(row=0, column=0, sticky='w')
        self.canvas = tk.Canvas(preview, width=1, height=1, highlightthickness=0, background='#e9eee6')
        self.canvas.grid(row=1, column=0, sticky='nsew', pady=6)
        self.canvas.bind('<Configure>', self.draw)
        self.preview_controls = ttk.Frame(preview)
        self.preview_controls.grid(row=2, column=0, sticky='ew')
        self.preview_controls.columnconfigure(1, weight=1)
        self.preview_button = ttk.Button(self.preview_controls, text='播放預覽', command=self.preview)
        self.preview_button.grid(row=0, column=0)
        self.seek_control = ttk.Scale(self.preview_controls, variable=self.seek, from_=0, to=1)
        self.seek_control.grid(row=0, column=1, sticky='ew', padx=6)
        self.seek_control.bind('<ButtonRelease-1>', self.scrub)
        self.seek_control.bind('<KeyRelease>', self.scrub)
        self.seek_info = ttk.Label(self.preview_controls, text='無聲預覽')
        self.seek_info.grid(row=1, column=0, columnspan=2, sticky='w')
        controls = ttk.Frame(preview)
        controls.grid(row=3, column=0, sticky='ew')
        controls.columnconfigure(1, weight=1)
        ttk.Label(controls, text='解析度').grid(row=0, column=0, padx=(0, 6))
        self.resolution_control = ttk.Combobox(controls, textvariable=self.resolution, state='readonly',
                                             values=('1080p', '720p'), width=7)
        self.resolution_control.grid(row=0, column=1, sticky='w')
        ttk.Label(controls, text='16:9 · 30 fps').grid(row=0, column=2)
        self.explanation = ttk.Label(self, text='沿用完整總 MP3／SRT。交接停頓已在音訊內，不再添加。', wraplength=650)
        self.explanation.grid(row=3, column=0, sticky='ew', pady=6)
        self.status = ttk.Label(self, text='請選擇素材，再檢查右側畫面。', width=1, wraplength=650)
        self.status.grid(row=4, column=0, sticky='ew', pady=4)
        self.progress = ttk.Progressbar(self, maximum=100)
        actions = ttk.Frame(self)
        actions.grid(row=6, column=0, sticky='ew', pady=4)
        actions.columnconfigure(1, weight=1)
        self.back_button = ttk.Button(actions, text='← 返回合併音訊', command=self.return_page)
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
        self.mode.trace_add('write', lambda *_: self.changed())
        self.bind('<Configure>', self.resized)
        self.update_controls()

    def resized(self, event):
        if event.widget is self:
            self.status.configure(wraplength=max(180, event.width-12))
            self.explanation.configure(wraplength=max(180, event.width-12))
            self.image_info.configure(wraplength=max(140, event.width*2//5-12))
            for label in (self.material_rule, self.material_note):
                label.configure(wraplength=max(140, event.width*2//5-12))
            self.update_controls()

    def draw(self, event=None):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        self.canvas.delete('all')
        fw, fh = min(w, h*16/9), min(h, w*9/16)
        x, y = w/2, h/2
        self.canvas.create_rectangle(x-fw/2, y-fh/2, x+fw/2, y+fh/2, fill='black', outline='')
        original = self.playback_image if self.player.alias or self.preview_playing else self.preview_image
        if original:
            scale = min(fw/original.width, fh/original.height)
            image = original.resize((max(1, round(original.width*scale)), max(1, round(original.height*scale))), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(image, master=self.canvas)
            self.canvas.create_image(x, y, image=self.photo)
        else:
            self.canvas.create_text(x, y, text='選擇素材後顯示預覽', fill='white', width=max(1, int(fw)-16))

    def is_background(self):
        return self.source_kind.get() == '背景影片（MP4）'

    def kind_changed(self, event=None):
        self.stop()
        self.preview_image = None
        self.changed()
        async def frame():
            from .total_video import background_frame, thumbnail
            if self.is_background():
                return await background_frame(self.background_path()) if self.background_info else None
            if self.pending_image is not None:
                return thumbnail(self.pending_image.data)
            return thumbnail(self.video_flow._path(self.saved_image_info['path']).read_bytes()) if self.saved_image_info else None
        self.action = 'frame'
        self.check_job = VoiceJob(frame, timeout=None)
        self.update_controls()
        self.schedule()

    def background_path(self):
        if self.pending_background is not None:
            return self.pending_background.path
        if self.background_info is not None:
            return self.video_flow._path(self.background_info['path'])
        raise ProjectError('請先選擇背景影片。')

    def emit_frame(self, data, milliseconds):
        try:
            self.frames.get_nowait()
        except queue.Empty:
            pass
        self.frames.put_nowait((data, milliseconds))

    def launch_frames(self, path, duration_ms, mode):
        from .total_video import stream_frames
        if self.frame_job is not None:
            raise ProjectError('請等待上一段預覽停止後再播放。')
        async def frames():
            await stream_frames(path, duration_ms, mode, self.emit_frame)
        self.frame_job = VoiceJob(frames, timeout=None)
        self.schedule()

    def preview(self):
        if self.preview_playing:
            self.stop()
            self.update_controls()
            return
        if self.check_job is not None or self.job is not None:
            return
        try:
            self.stop()
            self.seek.set(0)
            self.preview_playing = True
            info = self.background_info
            if info is None:
                raise ProjectError('請先選擇背景影片。')
            duration = self.audio['duration_ms'] if self.audio else info['duration_ms']
            mode = 'hold' if self.mode.get() == '最後一格定格' else 'loop'
            self.launch_frames(self.background_path(), duration, mode if info['duration_ms'] < duration else '')
            self.status.configure(text='正在無聲預覽背景畫面。總音訊不會重複播放。')
            self.update_controls()
        except (ProjectError, OSError) as error:
            self.preview_playing = False
            self.report(error)

    def scrub(self, event=None):
        if not self.is_background() or self.check_job is not None or self.job is not None:
            return
        self.stop()
        position = float(self.seek.get())
        info = self.background_info
        if info is None:
            return
        duration = info['duration_ms']/1000
        hold = self.mode.get() == '最後一格定格' and position >= duration
        seconds = min(position, duration) if self.mode.get() == '最後一格定格' else position % duration
        async def frame():
            from .total_video import background_frame
            return await background_frame(self.background_path(), seconds, last=hold)
        self.action = 'frame'
        self.check_job = VoiceJob(frame, timeout=None)
        self.seek_info.configure(text=f'總影片 {position:.1f} 秒 · 素材 {seconds:.1f} 秒 · 無聲')
        self.update_controls()
        self.schedule()

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
            self.menu.add_command(label=self.scope_text(label), command=command, state='normal' if enabled else 'disabled')

    def require_current(self):
        if self.app.flow is not self.flow or self.batch_id and self.app.batch_id != self.batch_id:
            raise ProjectError('書籍已切換。請返回目前書籍重新開啟製片頁。')
        if self.check_job is not None or self.job is not None:
            raise ProjectError('請等待目前操作停止。')

    def choose(self):
        background = self.is_background()
        path = filedialog.askopenfilename(parent=self.app.root, title='選擇全片共用素材',
            filetypes=[('MP4 背景影片', '*.mp4')] if background else [('JPEG／PNG 圖片', '*.jpg *.jpeg *.png')])
        if not path:
            return
        try:
            self.require_current()
            self.stop()
            async def inspect():
                from .total_video import thumbnail, inspect_background, background_frame
                if background:
                    video = await inspect_background(path, project_root=self.video_flow.root)
                    return video, await background_frame(video.path)
                image = self.video_flow.inspect_total_video_image(path)
                return image, thumbnail(image.data)
            self.action = 'background' if background else 'image'
            self.check_job = VoiceJob(inspect, timeout=None)
            self.status.configure(text='正在檢查背景串流、完整解碼並保存素材…' if background else '正在檢查圖片…')
            self.update_controls()
            self.schedule()
        except ProjectError as error:
            self.report(error)

    def save(self):
        try:
            self.require_current()
            self.video_flow.save_total_video_settings(image=self.pending_image, resolution=self.resolution.get(),
                background=self.pending_background, source_type='video' if self.is_background() else 'image',
                background_mode='hold' if self.mode.get() == '最後一格定格' else 'loop')
            self.pending_image = None
            self.pending_background = None
            visual = self.video_flow.total_video_settings()
            self.saved_image_info, self.background_info = visual['image'], visual['background']
            self.dirty = False
            from .total_video import total_video
            try:
                self.product = total_video(self.video_flow, verify_media=False)
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
            self.job = self.video_flow.start_total_video()
            self.last_status = ''
            self.publish_error = False
            self.status.configure(text='開始製片。本次音訊、字幕、素材及設定已固定。')
            self.update_controls()
            self.schedule()
        except ProjectError as error:
            self.report(error)

    def publish(self):
        self.publish_error = False
        try:
            self.product = self.video_flow.finish_total_video(self.job)
            self.job = None
            self.production_busy = self.app.production.busy_for(self.video_flow)
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
            return await inspect_video(self.video_flow)
        self.action = 'inspect'
        self.check_job = VoiceJob(inspect, timeout=None)
        self.status.configure(text='正在檢查總音訊、素材與影片版本…')
        self.update_controls()
        self.schedule()

    def file_action(self, action, target=None):
        if self.job is not None or self.check_job is not None:
            return
        self.stop()
        if action == 'play':
            if self.playback_folder is not None:
                return  # Keep the retained cleanup path until the old lock is released.
            self.playback_folder = Path(tempfile.mkdtemp(prefix='.video-preview-', dir=self.video_flow.root))
        async def operation():
            from .total_video import export, total_video, prepare_playback
            from .assembly import checked_file_async
            if action == 'export':
                await export(self.video_flow, target)
                return None
            product = total_video(self.video_flow, verify_media=False)
            if product is None:
                raise ProjectError('尚無成功總影片。')
            for kind in ('mp4', 'srt'):
                await checked_file_async(self.video_flow, product[kind])
            path = self.video_flow._path(product['mp4']['path'])
            if action == 'play':
                assert self.playback_folder is not None
                return await prepare_playback(self.video_flow, product, self.playback_folder)
            return path.parent if action == 'folder' else path
        self.action = action
        self.check_job = VoiceJob(operation, timeout=None)
        self.update_controls()
        self.schedule()

    def export(self):
        target = filedialog.asksaveasfilename(parent=self.app.root, title=self.scope_text('另存總 MP4／SRT：輸入新資料夾名稱'), initialfile=self.scope_text('總影片成品'))
        if target:
            self.file_action('export', target)

    def details(self):
        audio = self.audio
        text = ('總音訊版本：'+audio['id']+'\nMP3：'+audio['mp3']['path']+'\nSRT：'+audio['srt']['path'] if audio else '尚無有效總音訊。')
        try:
            history = self.video_flow.total_video_runs()
            diagnostic = history[-1]['progress'].get('diagnostic') if history else None
            if diagnostic:
                text += '\n\n最近失敗診斷：'+diagnostic['message']+'\n階段：'+diagnostic['phase']+'\n原因：'+diagnostic['detail']
        except ProjectError:
            pass
        text += '\n\nH.264／yuv420p · AAC-LC／48 kHz／立體聲 · faststart\n字幕以同版 SRT 一併另存。不再次添加交接停頓。\n保持比例，黑邊補齊。背景原聲完全排除。'
        info = self.background_info if self.is_background() else self.pending_image or self.saved_image_info
        if info:
            get = (lambda key: info[key]) if isinstance(info, dict) else (lambda key: getattr(info, key))
            text += f'\n\n素材：{get("name")}\n尺寸：{get("width")} × {get("height")}\n素材保存於專案，可重開與離線製片。'
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
            ttk.Button(self.details_panel, text='返回素材預覽', command=self.details).grid(row=1, column=0)
        self.details_text.configure(state='normal')
        self.details_text.delete('1.0', 'end')
        self.details_text.insert('1.0', self.scope_text(text))
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
                            self.source_kind.set('背景影片（MP4）' if value['visual']['source_type'] == 'video' else '圖片（JPEG／PNG）')
                            self.mode.set('最後一格定格' if value['visual']['background_mode'] == 'hold' else '循環播放（預設）')
                            self.dirty = False
                            self.preview_image = Image.open(BytesIO(value['preview'])) if value['preview'] else None
                        self.saved_image_info = value['visual']['image']
                        if self.pending_background is None:
                            self.background_info = value['visual']['background']
                        if self.dirty and self.is_background() and self.background_info and self.pending_background is None:
                            self.scrub()
                        self.loaded = True
                        last = value['runs'][-1]['progress'] if value['runs'] else None
                        self.last_status = last['status'] if last else ''
                        previous = ('上次製片：'+dict(failed='失敗', cancelled='已取消', interrupted='已中斷').get(self.last_status, '')+
                                    '。'+last.get('error', '')+' 舊成品保留，可重試。'
                                    if last and self.last_status in ('failed', 'cancelled', 'interrupted') else '')
                        self.status.configure(text=value['warning'] or previous or '選擇素材並檢查預覽，再製作總 MP4。')
                    elif self.action == 'image' and not self.closing:
                        self.pending_image, preview = value
                        self.preview_image = Image.open(BytesIO(preview))
                        self.dirty = True
                        self.image_info.configure(text=f'{self.pending_image.name} · {self.pending_image.width} × {self.pending_image.height}')
                        self.status.configure(text='圖片已就緒。請檢查預覽。')
                    elif self.action == 'background' and not self.closing:
                        self.pending_background, preview = value
                        video = self.pending_background
                        self.background_info = dict(name=video.name, width=video.width, height=video.height,
                                                    duration_ms=video.duration_ms)
                        self.preview_image = Image.open(BytesIO(preview))
                        self.seek.set(0)
                        self.dirty = True
                        self.status.configure(text='背景已完整解碼並保存至專案。請檢查無聲預覽。')
                    elif self.action == 'frame' and not self.closing:
                        self.preview_image = Image.open(BytesIO(value)) if value else None
                    elif self.action == 'play' and not self.closing and self.app.step == 4 and self.app.production.current is self:
                        self.playback_image = Image.open(BytesIO(value['frame']))
                        self.player.play(value['audio'])
                        self.launch_frames(value['video'], value['duration_ms'], '')
                        self.status.configure(text='正在播放總影片的畫面與音軌。可在成品操作停止。')
                    elif self.action == 'folder' and not self.closing:
                        os.startfile(value)
                    elif self.action == 'export':
                        self.status.configure(text='總 MP4 與 SRT 已另存。')
                self.draw()
            except (ProjectError, OSError) as error:
                self.report(error)
            finally:
                if self.action == 'play' and self.player.alias is None and self.frame_job is None:
                    self.cleanup_playback()
        if self.frame_job is not None:
            try:
                data, milliseconds = self.frames.get_nowait()
                self.playback_image = Image.frombytes('RGB', (960, 540), data)
                if self.playback_audio is not None:
                    self.player.play(self.playback_audio)
                    self.playback_audio = None
                if self.preview_playing:
                    self.seek.set(milliseconds/1000)
                    self.seek_info.configure(text=f'總影片 {milliseconds/1000:.1f} 秒 · 無聲預覽')
                self.draw()
            except queue.Empty:
                pass
            except ProjectError as error:
                self.report(error)
                self.stop()
            if self.frame_job is not None and self.frame_job.wait(0):
                task, self.frame_job = self.frame_job, None
                if task.state['status'] == 'failed':
                    self.report(ProjectError(task.state['error']))
                    self.stop()
                elif self.preview_playing:
                    self.preview_playing = False
                    self.preview_image = self.playback_image
                    self.status.configure(text='背景預覽已結束。')
                if self.player.alias is None:
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
                    self.video_flow.discard_total_video(self.job)
                    self.job = None
                    self.production_busy = self.app.production.busy_for(self.video_flow)
                    self.status.configure(text='已取消。舊成品保留。' if state['status'] == 'cancelled' else state['error'])
                except ProjectError as error:
                    self.publish_error = True
                    self.report(error)
            elif not self.publish_error:
                self.publish()
        if self.closing and self.job is None and self.check_job is None and self.frame_job is None:
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
                self.stop()
                self.draw()
                self.status.configure(text='影片播放已結束。')
        except ProjectError as error:
            self.report(error)
            self.stop()
        if self.job is not None and not self.publish_error or self.check_job is not None or self.player.alias or self.frame_job is not None:
            self.schedule()

    def update_controls(self):
        busy = self.job is not None or self.check_job is not None or self.production_busy
        valid = self.audio is not None and not self.audio['stale']
        background = self.is_background()
        image = bool(self.background_info) if background else self.pending_image is not None or self.saved_image_info is not None
        info = self.background_info if background else self.pending_image or self.saved_image_info
        if info:
            get = (lambda key: info[key]) if isinstance(info, dict) else (lambda key: getattr(info, key))
            name = get('name')
            suffix = f' · {get("duration_ms")/1000:g} 秒' if background else f' · {get("width")} × {get("height")}'
            font = tkfont.Font(font=self.image_info.cget('font'))
            available = max(140, self.choose_button.winfo_width()-8)
            display = name
            while len(display)>4 and font.measure(display+suffix)>available:
                display = display[:-2]+'…'
            self.image_info.configure(text=display+suffix, wraplength=0)
        else:
            self.image_info.configure(text='尚未選擇 MP4。' if background else '尚未選擇圖片。')
        short = background and info is not None and self.audio is not None and info['duration_ms'] < self.audio['duration_ms']
        for widget in (self.mode_label, self.mode_control):
            widget.grid() if short else widget.grid_remove()
        self.material_rule.configure(text=('背景循環至總音訊結束。' if self.mode.get() != '最後一格定格' else '播完背景，再保持最後一格至音訊結束。')
            if short else '背景從開頭播放，於總音訊結束時裁切。' if background else '圖片顯示至音訊結束。透明區黑底。')
        self.explanation.configure(text=('背景原聲排除 · 保持比例補黑邊 · '+self.material_rule.cget('text')) if background else
                                   '沿用完整總 MP3／SRT。交接停頓已在音訊內，不再添加。')
        self.material_note.configure(text='背景原聲排除。只使用總音訊。\n保持比例，黑邊補齊。\n素材保存於專案，可離線使用。' if background else '圖片將複製到專案。\n保持比例，黑邊補齊。')
        if background:
            self.preview_controls.grid()
        else:
            self.preview_controls.grid_remove()
        self.seek_control.configure(to=self.audio['duration_ms']/1000 if self.audio else 1, state='disabled' if busy or not info else 'normal')
        self.preview_button.configure(text='停止預覽' if self.preview_playing else '播放預覽', state='disabled' if busy or not info else 'normal')
        self.kind_control.configure(state='disabled' if busy else 'readonly')
        self.mode_control.configure(state='disabled' if busy else 'readonly')
        completed = self.job is not None and self.job.wait(0) and self.job.state['status'] == 'completed'
        self.start_button.configure(state='normal' if completed or valid and image and not busy else 'disabled',
                                    text='重試保存' if completed else '重試製片' if self.last_status in ('failed', 'cancelled', 'interrupted') else
                                    '更新總 MP4' if self.product else '製作總 MP4')
        self.choose_button.configure(state='disabled' if busy else 'normal', text='選擇背景影片…' if background else '選擇圖片…')
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

        self.scope_labels()

    def scope_text(self, text):
        if not self.batch_id:
            return text
        return (text.replace('總音訊', '本批音訊').replace('總 MP', '本批 MP')
                .replace('總影片', '本批影片').replace('全片共用', '本批次')
                .replace('合併音訊', '製作與成品')
                .replace('交接停頓已在音訊內，不再添加。', '不添加全書交接停頓。'))

    def scope_labels(self):
        if not self.batch_id:
            return
        def visit(widget):
            try:
                text = widget.cget('text')
                if isinstance(text, str):
                    widget.configure(text=self.scope_text(text))
            except tk.TclError:
                pass
            for child in widget.winfo_children():
                visit(child)
        visit(self)

    def set_production_busy(self, busy):
        self.production_busy = busy
        self.update_controls()

    def schedule(self):
        if self.timer is not None:
            self.after_cancel(self.timer)
        self.timer = self.after(100, self.poll)

    def report(self, error):
        self.status.configure(text=str(error))
        self.app.notify(self.scope_text(str(error)), kind='error')

    def cancel(self):
        for task in (self.job, self.check_job):
            if task is not None:
                task.cancel()

    def stop(self):
        if self.check_job is not None and self.action == 'play':
            self.check_job.cancel()
        try:
            self.preview_playing = False
            self.playback_audio = None
            if self.frame_job is not None:
                self.frame_job.cancel()
                if self.frame_job.wait(.5):
                    self.frame_job = None
                    while not self.frames.empty():
                        self.frames.get_nowait()
                else:
                    self.schedule()
            self.player.stop()
            if self.check_job is None or self.action != 'play':
                self.cleanup_playback()
            self.draw()
        except ProjectError as error:
            self.report(error)

    def cleanup_playback(self):
        if self.frame_job is not None:
            return
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
