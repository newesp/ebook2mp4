"""Explicit online acceptance: synthetic text only; leaves final MP3 evidence."""
from pathlib import Path
import json
import shutil
import subprocess
import time
from ebook2mp4.workflow import ProjectWorkflow


def main():
    root = Path('.scratch/t09/real-book-final')
    flow = ProjectWorkflow.create(root, 'T09 真實合成驗證')
    source = root.parent / 'synthetic.txt'
    source.write_bytes('今天一起讀書。Hello, welcome.\n\n第二段有數字 3.14，這是結尾。'.encode('utf-8'))
    batch = flow.import_txt(flow.inspect_txt(source))
    voices = flow.voice_catalog()['voices']
    voice = next(v['id'] for v in voices if v['locale'] == 'zh-TW' and 'HsiaoChen' in v['id'])
    flow.save_voice_settings(voice, '+0%', batch_id=batch)
    started = time.monotonic()
    job = flow.start_voice_preview(batch, start=0, end=len(flow.texts(batch)[1]))
    assert job.wait(90)
    assert job.state['status'] == 'completed', job.state
    snapshot = flow.finish_voice_preview(job)
    path = flow.voice_preview_path(batch)
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
        'format=duration:stream=codec_name,sample_rate,channels', '-of', 'json', str(path)]))
    shutil.copy2(path, 'docs/verification/T09-real-preview.mp3')
    import edge_tts
    result = dict(edge_tts=edge_tts.__version__, voices=len(voices),
        locales={loc: sum(v['locale'].startswith(loc) for v in voices) for loc in ['zh-TW', 'zh-CN', 'en-']},
        voice=voice, settings=snapshot['settings'], bytes=path.stat().st_size,
        seconds=round(time.monotonic() - started, 3), probe=probe, synthetic_only=True,
        manual_listening='pending user')
    Path('docs/verification/T09-real-edge.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
