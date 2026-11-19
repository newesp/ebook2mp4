"""Read the isolated EXE result, decode it with bundled tools, retain evidence."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from ebook2mp4.workflow import ProjectWorkflow


def main():
    root=Path(__file__).resolve().parents[1]
    flow=ProjectWorkflow.open(root/'.scratch/audio-assembly-review/book')
    output=root/'docs/verification/audio-assembly-workspace'
    product=flow.total_audio()
    assert product is not None and not product['stale']
    assert len(product['sources'])==4
    assert product['pause_ms']==500 and product['duration_ms']==2300
    assert flow.output_formats()==['mp4']
    assert flow.state['total_video_method']=='batch-videos'
    assert not list(flow.root.rglob('*.mp4'))
    tools=root/'dist/ebook2mp4/_internal/tools/ffmpeg'
    mp3=flow.total_audio_path()
    probe=json.loads(subprocess.check_output([str(tools/'ffprobe.exe'),'-v','error','-show_format','-show_streams','-of','json',str(mp3)]))
    subprocess.run([str(tools/'ffmpeg.exe'),'-v','error','-i',str(mp3),'-f','null','-'],check=True)
    files=[]
    for kind in ('mp3','srt'):
        path=flow.total_audio_path(kind)
        destination=output/('synthetic-merged.'+kind)
        shutil.copy2(path,destination)
        files.append(dict(file=destination.name,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    result=dict(valid=True,source_count=4,pause_ms=500,decoded_timeline_ms=2300,
                video_preferences_preserved=True,mp4_created=False,real_bundled_decode=True,
                media_streams=[s['codec_name'] for s in probe['streams']],files=files)
    (output/'exe-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
