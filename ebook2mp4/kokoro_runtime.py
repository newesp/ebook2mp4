"""One managed CPU worker with cancellation, idle unload and Windows job ownership."""
import asyncio
import atexit
from contextlib import asynccontextmanager
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import queue
import subprocess
import tempfile
import threading
import time

from .workflow import ProjectError
from .kokoro_packages import home, package, PackageLease, verify

IDLE_SECONDS=120
LOAD_SECONDS=300  # Fresh Windows install paths exceeded 180 seconds under load.
SYNTHESIS_SECONDS=180


class LocalSpeechError(ProjectError):
    def __init__(self,category,message):
        super().__init__(message)
        self.category=category


class ProcessTree:
    """Closing this Windows handle kills the worker and all its descendants."""
    def __init__(self,pid):
        class Basic(ctypes.Structure):
            _fields_=[('process_time',ctypes.c_int64),('job_time',ctypes.c_int64),('flags',wintypes.DWORD),
                      ('minimum',ctypes.c_size_t),('maximum',ctypes.c_size_t),('active',wintypes.DWORD),
                      ('affinity',ctypes.c_size_t),('priority',wintypes.DWORD),('scheduling',wintypes.DWORD)]
        class Extended(ctypes.Structure):
            _fields_=[('basic',Basic),('io',ctypes.c_uint64*6),('process_memory',ctypes.c_size_t),
                      ('job_memory',ctypes.c_size_t),('peak_process',ctypes.c_size_t),('peak_job',ctypes.c_size_t)]
        self.api=ctypes.WinDLL('kernel32',use_last_error=True)
        self.api.CreateJobObjectW.argtypes=[ctypes.c_void_p,wintypes.LPCWSTR]
        self.api.CreateJobObjectW.restype=wintypes.HANDLE
        self.api.SetInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
        self.api.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE]
        self.api.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        self.api.OpenProcess.restype=wintypes.HANDLE
        self.api.CloseHandle.argtypes=[wintypes.HANDLE]
        self.handle=self.api.CreateJobObjectW(None,None)
        limits=Extended();limits.basic.flags=0x2000
        process=self.api.OpenProcess(0x0100|0x0001,False,pid)
        try:
            if (not self.handle or not process or not self.api.SetInformationJobObject(self.handle,9,ctypes.byref(limits),ctypes.sizeof(limits))
                    or not self.api.AssignProcessToJobObject(self.handle,process)):
                self.close()
                raise ProjectError('無法管理本機推論子程序，請檢查 Windows 權限後重試。')
        finally:
            if process:self.api.CloseHandle(process)

    def close(self):
        if self.handle:self.api.CloseHandle(self.handle);self.handle=None


class Engine:
    def __init__(self):
        self.guard=threading.RLock();self.busy=False;self.owner=None
        self.process: subprocess.Popen[str] | None=None
        self.tree: ProcessTree | None=None
        self.lease: PackageLease | None=None
        self.timer: threading.Timer | None=None
        self.temp: tempfile.TemporaryDirectory[str] | None=None
        self.reader: threading.Thread | None=None
        self.messages: queue.Queue[dict]=queue.Queue()
        self.identity: str | None=None
        self.phase='尚未載入';self.loads=0
        self.last_error=''

    def status(self):
        with self.guard:
            return dict(busy=self.busy,phase=self.phase,pid=self.process.pid if self.process and self.process.poll() is None else None,
                        loads=self.loads,package=self.identity,idle_seconds=IDLE_SECONDS,last_error=self.last_error,
                        device='cpu' if self.identity else None)

    def stop_if_idle(self):
        with self.guard:
            if self.busy:raise ProjectError('本機語音工作進行中，請先取消或等待完成後管理語音包。')
            self.stop()

    def unload_idle(self):
        with self.guard:
            if not self.busy:self.stop()

    def stop(self):
        with self.guard:
            if self.timer:self.timer.cancel();self.timer=None
            if self.tree:self.tree.close();self.tree=None
            if self.process:
                if self.process.poll() is None:self.process.kill()
                self.process.wait(timeout=15)
                if self.process.stdin:self.process.stdin.close()
                if self.reader:self.reader.join(timeout=2)
                if self.process.stdout:self.process.stdout.close()
                handle=getattr(self.process,'_handle',None)
                if handle:handle.Close()
                self.process=None
                self.reader=None
            try:
                if self.temp:
                    temporary=self.temp
                    for attempt in range(5):
                        try:temporary.cleanup();self.temp=None;break
                        except OSError:
                            if attempt==4:raise ProjectError('推論已停止，但暫存檔仍被占用。請關閉占用程式後重試釋放。') from None
                            time.sleep(.1*(attempt+1))
            finally:
                if self.lease:self.lease.close();self.lease=None
            self.phase='模型已卸載';self.identity=None

    @asynccontextmanager
    async def session(self):
        with self.guard:
            if self.busy:raise ProjectError('已有本機語音工作，請等待或取消後再開始。')
            self.busy=True;self.owner=threading.get_ident()
            self.last_error=''
            if self.timer:self.timer.cancel();self.timer=None
        try:yield
        except BaseException as error:
            self.last_error=type(error).__name__
            self.stop()
            if isinstance(error,(ProjectError,asyncio.CancelledError)):raise
            raise ProjectError('本機語音處理失敗，請重試或重新匯入語音包；不會改用雲端。') from None
        finally:
            with self.guard:
                self.busy=False;self.owner=None
                if self.process:
                    self.timer=threading.Timer(IDLE_SECONDS,self.unload_idle)
                    self.timer.daemon=True;self.timer.start()

    def send(self,value):
        if self.process is None or self.process.stdin is None:raise ProjectError('本機推論程序尚未啟動，請重試。')
        self.process.stdin.write(json.dumps(value,ensure_ascii=True)+'\n');self.process.stdin.flush()

    async def wait(self,event,seconds):
        if self.process is None:raise ProjectError('本機推論程序尚未啟動，請重試。')
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            try:message=self.messages.get_nowait()
            except queue.Empty:
                if self.process.poll() is not None:
                    category='load' if event=='ready' else 'synthesis'
                    raise LocalSpeechError(category,'本機推論程序已結束。請重試；持續失敗時重新匯入語音包。')
                await asyncio.sleep(.03);continue
            if message['event']=='error':
                kind=message.get('kind')
                category='memory' if kind=='memory' else 'load' if event=='ready' else 'synthesis'
                reasons=dict(memory='記憶體不足，請關閉其他程式後重試',load='本機模型載入失敗，請重新匯入完整語音包',
                             synthesis='本機語音合成失敗，請核對文字與音色後重試')
                raise LocalSpeechError(category,reasons[category]+'；不會改用雲端服務。')
            if message['event']=='phase':self.phase=message['phase']
            if message['event']==event:return message
        category='load-timeout' if event=='ready' else 'synthesis-timeout'
        phase='模型載入' if event=='ready' else '語音合成'
        raise LocalSpeechError(category,f'本機{phase}逾時，請釋放系統資源或縮短文字後重試。')

    async def synthesize(self,text,settings,output):
        try:
            folder,metadata=package(settings['package'])
            if self.process and (self.identity!=settings['package'] or self.process.poll() is not None):self.stop()
            if self.process is None:
                self.phase='檢查語音包';self.lease=PackageLease()
                def verification_progress(done,total):self.phase=f'檢查語音包 {done}/{total}'
                await asyncio.wait_for(verify(folder,metadata,runtime_only=True,progress=verification_progress),LOAD_SECONDS)
                self.temp=tempfile.TemporaryDirectory(prefix='.worker-',dir=home())
                private=Path(self.temp.name)
                for sub in ('home','temp','hf','torch','xdg'):(private/sub).mkdir()
                env=dict(os.environ,HOME=str(private/'home'),USERPROFILE=str(private/'home'),
                         TEMP=str(private/'temp'),TMP=str(private/'temp'),HF_HOME=str(private/'hf'),
                         TORCH_HOME=str(private/'torch'),XDG_CACHE_HOME=str(private/'xdg'),
                         HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',
                         CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',
                         PYTHONPATH='',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',TOKENIZERS_PARALLELISM='false')
                self.process=subprocess.Popen([str(folder/metadata['python']),'-I','-B',str(folder/'worker.py')],
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                    text=True,encoding='utf-8',env=env,creationflags=subprocess.CREATE_NO_WINDOW)
                self.tree=ProcessTree(self.process.pid)
                self.messages=queue.Queue()
                process=self.process;messages=self.messages
                def receive():
                    assert process.stdout is not None
                    for line in process.stdout:
                        try:
                            value=json.loads(line)
                            if isinstance(value,dict) and isinstance(value.get('event'),str):messages.put(value)
                        except ValueError:pass  # Upstream informational stdout is not protocol.
                self.reader=threading.Thread(target=receive,daemon=True);self.reader.start()
                self.send(dict(action='load'));ready=await self.wait('ready',LOAD_SECONDS)
                if ready.get('device')!='cpu' or ready.get('cuda') is not None:
                    raise LocalSpeechError('load','語音包未使用指定的 CPU 引擎，請重新匯入完整語音包。')
                self.identity=settings['package'];self.loads+=1
            self.phase='本機合成'
            self.send(dict(action='synthesize',text=text,voice=settings['voice'],
                           speed=1+int(settings['rate'].strip('%'))/100,output=str(output.resolve())))
            await self.wait('completed',SYNTHESIS_SECONDS)
            self.phase='本機合成完成'
        except asyncio.TimeoutError:
            raise LocalSpeechError('load-timeout','本機語音包檢查逾時，請釋放系統資源後重試。') from None
        except OSError as error:
            category='memory' if getattr(error,'winerror',None) in (8,14,1450,1455) else 'synthesis' if self.identity else 'load'
            raise LocalSpeechError(category,'無法載入或執行本機語音包。請檢查權限、記憶體或重新匯入語音包。') from None


_engines: dict[str,Engine]={}
def engine():
    key=str(home().resolve())
    if key not in _engines:_engines[key]=Engine()
    return _engines[key]


def shutdown():
    for value in list(_engines.values()):value.stop()


@asynccontextmanager
async def local_session(settings):
    if settings['provider']=='kokoro':
        async with engine().session():yield
    else:yield


atexit.register(shutdown)
