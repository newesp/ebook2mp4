"""Reproducible CPU/offline/lifecycle experiment; run through verify.ps1."""
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import queue
import subprocess
import sys
import threading
import time
import psutil

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT/'docs/verification/kokoro-k01'
BUNDLE = ROOT/'outputs/kokoro-k01'
SCRATCH = ROOT/'.scratch/k01/runtime'
SAMPLES = json.loads((Path(__file__).with_name('samples.json')).read_text(encoding='utf-8'))


class Worker:
    def __init__(self, label):
        self.label = label
        private = SCRATCH/label
        assert not private.exists(), 'Use a fresh isolated cache directory'
        for sub in ('home', 'temp', 'hf', 'torch', 'xdg'):
            (private/sub).mkdir(parents=True)
        env = dict(os.environ, HF_HOME=str(private/'hf'), TORCH_HOME=str(private/'torch'),
                   XDG_CACHE_HOME=str(private/'xdg'), USERPROFILE=str(private/'home'),
                   HOME=str(private/'home'), TEMP=str(private/'temp'), TMP=str(private/'temp'),
                   HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1',
                   CUDA_VISIBLE_DEVICES='', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1',
                   OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', TOKENIZERS_PARALLELISM='false')
        self.errors = (EVIDENCE/f'{label}-stderr.txt').open('w', encoding='utf-8')
        self.started = time.perf_counter()
        self.process = subprocess.Popen([sys.executable, '-B', str(Path(__file__).with_name('worker.py'))],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.errors,
                                        text=True, encoding='utf-8', env=env,
                                        creationflags=subprocess.CREATE_NO_WINDOW)
        self.pid = self.process.pid
        self.ps = psutil.Process(self.pid)
        self.peak = 0
        self.events = []
        self.messages = queue.Queue()
        self.running = True
        def read():
            for line in self.process.stdout:
                try:
                    self.messages.put(json.loads(line))
                except json.JSONDecodeError:
                    self.messages.put({'event':'upstream_stdout', 'text':line.rstrip()})
        def measure():
            while self.running:
                try:
                    memory = self.ps.memory_info()
                    self.peak = max(self.peak, memory.rss, getattr(memory, 'peak_wset', 0))
                except psutil.NoSuchProcess:
                    break
                time.sleep(.05)
        self.reader = threading.Thread(target=read, daemon=True)
        self.monitor = threading.Thread(target=measure, daemon=True)
        self.reader.start()
        self.monitor.start()

    def wait(self, event, timeout=1800):
        deadline = time.perf_counter()+timeout
        while time.perf_counter()<deadline:
            try:
                message = self.messages.get(timeout=.1)
                self.events.append(dict(elapsed=time.perf_counter()-self.started, **message))
                if message['event'] == 'network_denied':
                    raise RuntimeError(f'Unexpected network attempt: {message}')
                if message['event'] == event:
                    return message
            except queue.Empty:
                if self.process.poll() is not None:
                    raise RuntimeError(f'{self.label} exited {self.process.returncode}; see stderr')
        raise TimeoutError(f'{self.label}: {event}')

    def send(self, command):
        self.process.stdin.write(json.dumps(command, ensure_ascii=True)+'\n')
        self.process.stdin.flush()

    def finish(self, reason):
        started = time.perf_counter()
        if reason == 'cancel':
            self.process.kill()
        elif reason == 'close':
            self.send({'action':'close'})
        self.process.wait(timeout=30)
        elapsed = time.perf_counter()-started
        self.running = False
        self.monitor.join(timeout=2)
        self.reader.join(timeout=2)
        while not self.messages.empty():
            self.events.append(self.messages.get())
        self.process.stdin.close()
        self.process.stdout.close()
        self.errors.close()
        # No Python child should survive this experiment worker.
        alive = psutil.pid_exists(self.pid)
        assert not alive
        result = dict(label=self.label, pid=self.pid, reason=reason,
                      termination_seconds=elapsed, peak_working_set_bytes=self.peak,
                      returncode=self.process.returncode, pid_alive=alive, events=self.events,
                      cache_files=[str(p.relative_to(SCRATCH)) for p in (SCRATCH/self.label).rglob('*') if p.is_file()])
        (EVIDENCE/f'{self.label}.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(self.label, 'finished', 'peak MiB', round(self.peak/2**20,1), flush=True)
        return result


def main():
    assert os.environ.get('K01_FIREWALL_ACTIVE') == '1', 'Use verify.ps1 to enforce OS network isolation'
    EVIDENCE.mkdir(exist_ok=True)
    hardware = dict(windows=platform.platform(), python=sys.version, executable=sys.executable,
                    logical_cpus=psutil.cpu_count(), physical_cpus=psutil.cpu_count(logical=False),
                    ram=psutil.virtual_memory().total, threads=4,
                    dependencies={d.metadata['Name']:d.version for d in importlib.metadata.distributions()})
    (EVIDENCE/'environment.json').write_text(json.dumps(hardware, indent=2), encoding='utf-8')
    requirements = [
        'https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl'
        if k.lower().replace('_','-') == 'en-core-web-sm' else f'{k}=={v}'
        for k,v in sorted(hardware['dependencies'].items())
    ]
    (EVIDENCE/'requirements-lock.txt').write_text('\n'.join(requirements)+'\n', encoding='utf-8')
    current = None
    results = []
    try:
        current = Worker('first-offline')
        ready = current.wait('ready', 600)
        print('First offline load', ready, flush=True)
        for voice in ('zf_001','zm_010'):
            for sample in SAMPLES:
                if sample['id']=='long' and voice=='zm_010':
                    continue
                current.send(dict(action='synthesize', sample=sample, voice=voice))
                result = current.wait('completed')
                print(result, flush=True)
                if voice == 'zf_001' and sample['id'] == 'traditional':
                    for suffix in ('.wav', '.json'):
                        source = EVIDENCE/'audio'/f"traditional-zf_001-t2s{suffix}"
                        source.with_name('first-preview-'+source.name).write_bytes(source.read_bytes())
        current.send(dict(action='synthesize', sample=SAMPLES[1], voice='zf_001', policy='original'))
        print(current.wait('completed'), flush=True)
        # Wait for worker's own idle timeout; long active jobs above exceed this timeout.
        current.wait('unload', 15)
        results.append(current.finish('idle'))
        current = Worker('cancel-load')
        current.wait('loading', 10)
        time.sleep(.3)
        results.append(current.finish('cancel'))
        current = Worker('cancel-inference')
        current.wait('ready', 600)
        current.send(dict(action='synthesize', sample=SAMPLES[-1], voice='zf_001'))
        current.wait('inference', 60)
        time.sleep(.3)
        results.append(current.finish('cancel'))
        current = Worker('restart-close')
        current.wait('ready', 600)
        current.send(dict(action='synthesize', sample=SAMPLES[0], voice='zf_001'))
        print(current.wait('completed'), flush=True)
        results.append(current.finish('close'))
        current = None
        (EVIDENCE/'lifecycle.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    finally:
        if current is not None:
            current.finish('cancel')
    # The resource tree is retained as the reproducible experiment deliverable, not a final distributable pack.
    resources = [p for folder in (Path(sys.executable).resolve().parent, BUNDLE/'model')
                 for p in folder.rglob('*') if p.is_file()]
    (EVIDENCE/'resource-size.json').write_text(json.dumps(dict(files=len(resources),
        bytes=sum(p.stat().st_size for p in resources), model_bytes=sum(p.stat().st_size for p in (BUNDLE/'model').rglob('*') if p.is_file())), indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
