"""K01 experiment worker. Official inference, local paths, no network or engine patches."""
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import socket
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/verification/kokoro-k01'
BUNDLE = ROOT / 'outputs/kokoro-k01'


def emit(event, **values):
    print(json.dumps(dict(event=event, **values), ensure_ascii=True), flush=True)


def deny_network(event, args):
    if event in ('socket.connect', 'socket.connect_ex', 'socket.getaddrinfo', 'socket.sendto'):
        emit('network_denied', operation=event)
        raise PermissionError('K01 offline worker: networking is prohibited')


def main():
    # Test OS blocking before the Python audit guard is installed.
    probe = time.perf_counter()
    try:
        with socket.create_connection(('1.1.1.1', 443), timeout=2):
            emit('os_network_probe', blocked=False)
            raise RuntimeError('OS firewall did not block worker')
    except (TimeoutError, OSError) as error:
        emit('os_network_probe', blocked=True, error=repr(error), seconds=time.perf_counter()-probe)
    sys.addaudithook(deny_network)
    emit('loading', pid=os.getpid())
    start = time.perf_counter()
    import numpy as np
    import soundfile as sf
    import torch
    from kokoro import KModel, KPipeline
    from misaki import en, espeak
    from opencc import OpenCC
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    imports = time.perf_counter() - start
    model_start = time.perf_counter()
    model_dir = BUNDLE / 'model'
    emit('model_loading')
    model = KModel(repo_id='hexgrad/Kokoro-82M-v1.1-zh', config=str(model_dir/'config.json'),
                   model=str(model_dir/'kokoro-v1_1-zh.pth')).to('cpu').eval()
    english = en.G2P(trf=False, british=False, fallback=espeak.EspeakFallback(british=False))
    pipeline = KPipeline(lang_code='z', repo_id='hexgrad/Kokoro-82M-v1.1-zh', model=model,
                         en_callable=lambda text: english(text)[0], device='cpu')
    converter = OpenCC('t2s')
    assert torch.version.cuda is None
    assert {str(p.device) for p in model.parameters()} == {'cpu'}
    emit('ready', import_seconds=imports, model_frontend_seconds=time.perf_counter()-model_start,
         load_seconds=time.perf_counter()-start, torch=torch.__version__, cuda=torch.version.cuda,
         devices=sorted({str(p.device) for p in model.parameters()}), threads=torch.get_num_threads())
    commands = queue.Queue()

    def read_commands():
        for line in sys.stdin:
            commands.put(json.loads(line))
        commands.put({'action': 'close'})

    threading.Thread(target=read_commands, daemon=True).start()
    while True:
        try:
            command = commands.get(timeout=5)
        except queue.Empty:
            emit('unload', reason='idle', idle_seconds=5)
            return
        if command['action'] == 'close':
            emit('unload', reason='close')
            return
        sample = command['sample']
        voice = command['voice']
        policy = command.get('policy', 't2s')
        original = sample['text']
        synthesis = converter.convert(original) if policy == 't2s' else original
        filename = f"{sample['id']}-{voice}-{policy}"
        started = time.perf_counter()
        pack = pipeline.load_voice(str(model_dir/'voices'/f'{voice}.pt'))
        segments = []
        # Keep every source character, including punctuation and whitespace.
        pieces = re.findall(r'[^。！？；\n]+[。！？；\n]*|[。！？；\n]+', synthesis)
        assert ''.join(pieces) == synthesis
        pending = list(pieces)
        arrays = []
        offset = 0
        while pending:
            text = pending.pop(0)
            if not text.strip():
                segments.append(dict(text=text, start=offset, end=offset, phonemes=''))
                continue
            phonemes, _ = pipeline.g2p(text)
            if len(phonemes) > 510:
                if len(text) < 2:
                    raise ValueError('Unsplitable phoneme overflow')
                # Preserve text exactly; do not use the upstream silent truncation path.
                pivot = len(text)//2
                pending[:0] = [text[:pivot], text[pivot:]]
                continue
            assert phonemes
            emit('inference', sample=filename, segment=len(segments), phonemes=len(phonemes))
            with torch.inference_mode():
                result = next(pipeline.generate_from_tokens(phonemes, voice=pack, speed=1.0))
            audio = result.audio.detach().cpu().numpy()
            assert audio.size > 0 and np.isfinite(audio).all()
            seconds = audio.size/24000
            segments.append(dict(text=text, phonemes=phonemes, start=offset, end=offset+seconds,
                                 unknown_characters=sorted(set(p for p in phonemes if p not in model.vocab)),
                                 peak=float(np.max(np.abs(audio)))))
            arrays.append(audio)
            offset += seconds
            emit('segment_done', sample=filename, segments=len(segments), audio_seconds=offset)
        assert ''.join(s['text'] for s in segments) == synthesis
        audio = np.concatenate(arrays)
        target = EVIDENCE/'audio'/f'{filename}.wav'
        target.parent.mkdir(exist_ok=True)
        sf.write(target, audio, 24000, subtype='PCM_16')
        decoded, rate = sf.read(target)
        assert rate == 24000 and decoded.size == audio.size
        record = dict(id=sample['id'], voice=voice, policy=policy, original=original, synthesis=synthesis,
                      original_sha256=hashlib.sha256(original.encode()).hexdigest(), segments=segments,
                      seconds=time.perf_counter()-started, audio_seconds=offset,
                      real_time_factor=(time.perf_counter()-started)/offset,
                      clipped_samples=int((np.abs(audio)>=1).sum()), bytes=target.stat().st_size,
                      sha256=hashlib.file_digest(target.open('rb'), 'sha256').hexdigest())
        target.with_suffix('.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        emit('completed', file=target.name, **{k: record[k] for k in ('seconds','audio_seconds','real_time_factor')})


if __name__ == '__main__':
    main()
