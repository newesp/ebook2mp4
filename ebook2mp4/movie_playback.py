"""Bounded native playback of delivered video, with explicit cancellation and cleanup."""
from io import BytesIO
from pathlib import Path
import queue
import shutil
import tempfile
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from .voice import VoiceJob
from .voice_media import PreviewPlayer
from .workflow import ProjectError


class MoviePlayback(ttk.Frame):
    def __init__(self,parent,flow,on_close):
        super().__init__(parent)
        self.flow,self.on_close=flow,on_close
        self.player=PreviewPlayer()
        self.prepare_job=self.frame_job=self.timer=None
        self.folder=None
        self.frames: queue.Queue=queue.Queue(maxsize=1)
        self.image=self.photo=None
        self.allow=False
        self.columnconfigure(0,weight=1);self.rowconfigure(0,weight=1)
        self.canvas=tk.Canvas(self,width=1,height=1,background='black',highlightthickness=0)
        self.canvas.grid(row=0,column=0,sticky='nsew');self.canvas.bind('<Configure>',lambda e:self.draw())
        self.caption=ttk.Label(self,text='',anchor='center',width=1)
        self.caption.grid(row=1,column=0,sticky='ew')
        actions=ttk.Frame(self);actions.grid(row=2,column=0,sticky='ew');actions.columnconfigure(0,weight=1)
        self.status=ttk.Label(actions,text='準備播放…',width=1);self.status.grid(row=0,column=0,sticky='ew')
        ttk.Button(actions,text='停止並返回',command=self.leave).grid(row=0,column=1)
        self.cues=[]

    def has_work(self):
        return self.prepare_job is not None or self.frame_job is not None or self.folder is not None

    def start(self,product):
        from .total_video import prepare_playback
        self.stop()
        if self.has_work(): raise ProjectError('請等待上一段播放釋放檔案。')
        self.allow=True
        folder=self.folder=Path(tempfile.mkdtemp(prefix='.movie-play-',dir=self.flow.root))
        async def prepare():
            from .assembly import checked_file_async,captions
            path=await checked_file_async(self.flow,product['srt'])
            self.cues=captions(path,product['duration_ms']) if path.stat().st_size else []
            return await prepare_playback(self.flow,product,folder)
        self.prepare_job=VoiceJob(prepare,timeout=None)
        self.schedule()

    def emit(self,data,milliseconds):
        try:self.frames.get_nowait()
        except queue.Empty:pass
        self.frames.put_nowait((data,milliseconds))

    def draw(self):
        self.canvas.delete('all')
        if self.image:
            image=self.image.copy();image.thumbnail((max(1,self.canvas.winfo_width()),max(1,self.canvas.winfo_height())))
            self.photo=ImageTk.PhotoImage(image,master=self.canvas)
            self.canvas.create_image(self.canvas.winfo_width()/2,self.canvas.winfo_height()/2,image=self.photo)

    def schedule(self):
        if self.timer is not None:self.after_cancel(self.timer)
        self.timer=self.after(50,self.poll)

    def poll(self):
        self.timer=None
        try:
            if self.prepare_job is not None and self.prepare_job.wait(0):
                task,self.prepare_job=self.prepare_job,None
                if self.allow:
                    result=task.result
                    self.image=Image.open(BytesIO(result['frame']));self.draw()
                    self.player.play(result['audio'])
                    async def frames():
                        from .total_video import stream_frames
                        await stream_frames(result['video'],result['duration_ms'],'',self.emit)
                    self.frame_job=VoiceJob(frames,timeout=None)
                    self.status.configure(text='正在播放影音')
            if self.frame_job is not None:
                try:
                    data,milliseconds=self.frames.get_nowait()
                    self.image=Image.frombytes('RGB',(960,540),data);self.draw()
                    self.caption.configure(text='\n'.join(t for a,b,t in self.cues if a<=milliseconds<b))
                except queue.Empty:pass
                if self.frame_job.wait(0):
                    task,self.frame_job=self.frame_job,None
                    if self.allow and task.state['status']=='failed':raise ProjectError(task.state['error'])
                    self.stop();self.status.configure(text='播放已結束。')
            if not self.allow and self.prepare_job is None and self.frame_job is None:
                self.cleanup()
        except (ProjectError,OSError) as error:
            try:self.stop()
            except ProjectError:pass
            self.status.configure(text=str(error))
        if self.prepare_job is not None or self.frame_job is not None:self.schedule()

    def cleanup(self):
        if self.folder is not None:
            try:shutil.rmtree(self.folder);self.folder=None
            except OSError:raise ProjectError('播放暫存仍被占用，請停止後重試。') from None

    def stop(self):
        self.allow=False
        self.player.stop()
        for task in (self.prepare_job,self.frame_job):
            if task is not None:task.cancel()
        if self.prepare_job is None and self.frame_job is None:self.cleanup()
        else:self.schedule()

    def leave(self):
        self.stop();self.grid_remove();self.on_close()

    def release(self):
        self.stop()
        if self.has_work():return False
        if self.timer is not None:self.after_cancel(self.timer);self.timer=None
        return True
