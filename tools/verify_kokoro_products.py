"""Independent decoded-media checks for the synthetic integration delivery."""
from array import array
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

from kokoro_real_check import OUT,EVIDENCE
from ebook2mp4.workflow import ProjectWorkflow

tool=shutil.which('ffmpeg');probe=shutil.which('ffprobe')
assert tool and probe
flow=ProjectWorkflow.open(OUT/'book')
product=flow.total_audio();assert product
sources=product['sources']


def pcm(path):
    return subprocess.check_output([tool,'-nostdin','-v','error','-i',str(path),'-ac','1','-ar','24000','-f','s16le','-'])


def cues(path):
    text=path.read_text(encoding='utf-8-sig')
    values=[]
    for block in re.split(r'\n\s*\n',text.strip()):
        lines=block.splitlines();a,b=lines[1].split(' --> ')
        def milliseconds(value):
            h,m,s,ms=map(int,re.split('[:,]',value));return ((h*60+m)*60+s)*1000+ms
        values.append((milliseconds(a),milliseconds(b),'\n'.join(lines[2:])))
    return values


expected=[];offset_frames=0;boundaries=[]
for index,source in enumerate(sources):
    batch=source['batch_id'];decoded=pcm(flow.narration_path(batch));frames=len(decoded)//2
    expected.extend((a+round(offset_frames/24),b+round(offset_frames/24),text)
                    for a,b,text in cues(flow.narration_path(batch,'srt')))
    offset_frames+=frames
    if index<len(sources)-1:
        boundaries.append(offset_frames);offset_frames+=24*product['pause_ms']
decoded=pcm(flow.total_audio_path())
assert len(decoded)//2==offset_frames,(len(decoded)//2,offset_frames)
assert cues(flow.total_audio_path('srt'))==expected
silences=[]
for boundary in boundaries:
    center=boundary+12*product['pause_ms']
    samples=array('h',decoded[(center-120)*2:(center+120)*2]);peak=max(map(abs,samples))
    assert peak<=2,peak
    silences.append(dict(center_ms=center/24,window_ms=10,peak=peak))
videos=[];audio_hashes=[]
for path in sorted((OUT/'delivery').glob('*.mp4')):
    info=json.loads(subprocess.check_output([probe,'-v','error','-show_streams','-show_format','-of','json',str(path)]))
    video=[s for s in info['streams'] if s['codec_type']=='video'];audio=[s for s in info['streams'] if s['codec_type']=='audio']
    assert len(video)==len(audio)==1
    assert (video[0]['width'],video[0]['height'])==(1280,720)
    assert abs(float(info['format']['duration'])-offset_frames/24000)<.2
    payload=subprocess.check_output([tool,'-v','error','-i',str(path),'-map','0:a','-c','copy','-f','adts','-'])
    audio_hashes.append(hashlib.sha256(payload).hexdigest())
    videos.append(dict(path=str(path),duration=info['format']['duration'],audio_sha256=audio_hashes[-1]))
assert len(videos)==2 and len(set(audio_hashes))==1
result=dict(frames=offset_frames,duration_ms=offset_frames/24,cues=len(expected),
            exact_subtitle_offsets=True,pause_ms=product['pause_ms'],silences=silences,
            videos=videos,changed_image_preserves_audio=True)
(EVIDENCE/'decoded-products.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False),flush=True)
