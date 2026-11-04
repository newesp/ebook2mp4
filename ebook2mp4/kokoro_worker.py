"""Bundled Python 3.12 worker; stdin/stdout protocol, no network or service port."""
import json
import os
from pathlib import Path
import sys

stage='load'


def send(event,**values):
    print(json.dumps(dict(event=event,**values),ensure_ascii=True),flush=True)


def guard(event,args):
    if event in ('socket.connect','socket.connect_ex','socket.getaddrinfo','socket.sendto'):
        raise PermissionError('Offline Kokoro worker cannot access the network')


def main():
    global stage
    sys.addaudithook(guard)
    line=sys.stdin.readline()
    if not line:return
    command=json.loads(line)
    if command['action']!='load':return
    base=Path(__file__).resolve().parent
    send('phase',phase='載入本機模型')
    import numpy as np
    import torch
    import soundfile as sf
    from kokoro import KModel,KPipeline
    from misaki import en,espeak
    from opencc import OpenCC
    torch.set_num_threads(4);torch.set_num_interop_threads(1)
    if torch.version.cuda is not None:raise RuntimeError('CPU runtime required')
    model=KModel(repo_id='hexgrad/Kokoro-82M-v1.1-zh',config=str(base/'model/config.json'),
                 model=str(base/'model/kokoro-v1_1-zh.pth')).to('cpu').eval()
    english=en.G2P(trf=False,british=False,fallback=espeak.EspeakFallback(british=False))
    pipeline=KPipeline(lang_code='z',repo_id='hexgrad/Kokoro-82M-v1.1-zh',model=model,
                       en_callable=lambda text:english(text)[0],device='cpu')
    converter=OpenCC('t2s')
    assert all(p.device.type=='cpu' for p in model.parameters())
    send('ready',device='cpu',cuda=None,pid=os.getpid())
    stage='synthesis'
    while True:
        # Job ownership handles parent death while inference is active. At idle,
        # EOF ends this loop. No reader thread holds the CRT stdin lock while
        # numerical libraries import or perform lazy native initialization.
        line=sys.stdin.readline()
        if not line:return
        command=json.loads(line)
        if command['action']=='close':return
        if command['action']!='synthesize':raise ValueError('Unknown action')
        text=converter.convert(command['text'])
        pending=[text];segments=[]
        pack=pipeline.load_voice(str(base/'model/voices'/f"{command['voice']}.pt"))
        while pending:
            part=pending.pop(0)
            phonemes,_=pipeline.g2p(part)
            if len(phonemes)>510:
                if len(part)<2:raise ValueError('Phoneme overflow')
                at=len(part)//2;pending[:0]=[part[:at],part[at:]];continue
            if not phonemes:raise ValueError('Empty phonemes')
            if any(p not in model.vocab for p in phonemes):raise ValueError('Unsupported phonemes')
            send('phase',phase='本機合成')
            with torch.inference_mode():
                result=next(pipeline.generate_from_tokens(phonemes,voice=pack,speed=command['speed']))
            audio=result.audio.detach().cpu().numpy()
            if audio.size==0 or not np.isfinite(audio).all():raise ValueError('Invalid audio')
            segments.append((part,audio))
        assert ''.join(p for p,_ in segments)==text
        sf.write(command['output'],np.concatenate([a for _,a in segments]),24000,subtype='PCM_16')
        send('completed',synthesis=text)


if __name__=='__main__':
    try:main()
    except Exception as error:
        memory=isinstance(error,MemoryError) or getattr(error,'winerror',None) in (8,14,1450,1455)
        if isinstance(error,RuntimeError):
            memory=memory or any(x in str(error).lower() for x in ('out of memory','cannot allocate','can\'t allocate','bad_alloc','defaultcpuallocator'))
        send('error',kind='memory' if memory else stage,error_type=type(error).__name__)
        sys.exit(1)
