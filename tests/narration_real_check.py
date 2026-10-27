"""Explicit real Edge acceptance. Sends only synthetic text; retains evidence."""
from pathlib import Path
import json
import shutil
import subprocess
import time

from ebook2mp4.workflow import ProjectWorkflow
from ebook2mp4.voice_media import PreviewPlayer


def main():
    import edge_tts
    folder = Path('.scratch/T10-real')
    folder.mkdir()
    flow = ProjectWorkflow.create(folder / 'book', 'T10 真實合成驗證')
    source = folder / 'synthetic.txt'
    source.write_text('今天一起讀書。「你準備好了嗎？」\n\nHello, Dr. Chen. The value is 3.14. '
                      'Visit https://example.com.\n\n第三段，保留原文與自然停頓……這是結尾。', encoding='utf-8')
    batch = flow.import_txt(flow.inspect_txt(source))
    job = flow.start_voice_refresh()
    assert job.wait(90), job.state
    assert job.state['status'] == 'completed', job.state
    voices = flow.voice_catalog()['voices']
    voice = next(v['id'] for v in voices if v['id'] == 'zh-TW-HsiaoChenNeural')
    flow.save_voice_settings(voice, batch_id=batch)
    flow.confirm_reading(batch)
    started = time.monotonic()
    job = flow.start_narration(batch)
    published = False
    try:
        assert job.wait(240), job.state
        assert job.state['status'] == 'completed', job.state
        product = flow.finish_narration(job)
        published = True
    finally:
        if not job.wait(0):
            job.cancel()
            job.wait(10)
        if not published:
            flow.discard_narration(job)
    reopened = ProjectWorkflow.open(flow.root)
    assert reopened.narration(batch)['id'] == product['id']
    mp3 = reopened.narration_path(batch)
    srt = reopened.narration_path(batch, 'srt')
    shutil.copy2(mp3, 'docs/verification/T10-real.mp3')
    shutil.copy2(srt, 'docs/verification/T10-real.srt')
    pcm = subprocess.check_output([__import__('os').environ['EBOOK2MP4_FFMPEG'], '-v', 'error', '-i', str(mp3),
                                   '-f', 's16le', '-ac', '1', '-ar', '24000', '-'])
    assert abs(len(pcm)/48 - product['duration_ms']) <= 2
    player = PreviewPlayer()
    try:
        player.play(mp3)
        playing = player.playing()
        assert playing
    finally:
        player.stop()
    result = dict(edge_tts=edge_tts.__version__, voice=voice, voices=len(voices),
                  synthetic_only=True, seconds=round(time.monotonic()-started, 3),
                  duration_ms=product['duration_ms'], decoded_ms=len(pcm)/48,
                  bytes=mp3.stat().st_size, windows_playing=playing,
                  chunks=[{k: c[k] for k in ('id', 'order', 'attempts', 'status', 'duration_ms', 'start_ms', 'end_ms', 'pause_after_ms')}
                          for c in product['chunks']], manual_listening='pending user')
    Path('docs/verification/T10-real.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
