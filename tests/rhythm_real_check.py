"""Real Edge/FFmpeg evidence: synthetic texts only; listening is a human gate."""
from pathlib import Path
import json
import os
import shutil
import subprocess
from unittest.mock import patch

from ebook2mp4.workflow import ProjectWorkflow
from ebook2mp4.voice_media import PreviewPlayer


def complete(flow, batch):
    job = flow.start_narration(batch)
    try:
        assert job.wait(240), job.state
        assert job.state['status'] == 'completed', job.state
        return flow.finish_narration(job)
    finally:
        if not job.wait(0):
            job.cancel()
            assert job.wait(15)
        if flow._narration_job is job:
            flow.discard_narration(job)


def main():
    import edge_tts
    base = Path('.scratch/T11/real')
    base.mkdir()
    flow = ProjectWorkflow.create(base / 'book', 'T11 合成短稿')
    job = flow.start_voice_refresh()
    assert job.wait(90) and job.state['status'] == 'completed', job.state
    texts = {
        'zh': ('zh-TW-HsiaoChenNeural', '今天一起讀書。請慢慢呼吸。\n\n這是最後一段。'),
        'en': ('en-US-JennyNeural', 'Hello, Dr. Chen. The value is 3.14.\n\nThis is the final paragraph.'),
        'mixed': ('zh-TW-HsiaoChenNeural', '現在開始。Hello, welcome to your audiobook.\n\n今天讀到這裡。'),
    }
    evidence = dict(edge_tts=edge_tts.__version__, synthetic_only=True, cases=[], manual_listening='pending user')
    for language, (voice, text) in texts.items():
        source = base / (language + '.txt')
        source.write_text(text, encoding='utf-8')
        batch = flow.import_txt(flow.inspect_txt(source))
        flow.confirm_reading(batch)
        case = dict(language=language, voice=voice, text=text, variants=[])
        for name, sentence, paragraph in [('natural', 0, 500), ('relaxed', 200, 800), ('custom', 600, 1000)]:
            flow.save_voice_settings(voice, batch_id=batch, sentence_pause_ms=sentence, paragraph_pause_ms=paragraph)
            if name == 'custom':
                with patch('edge_tts.Communicate', side_effect=AssertionError('unnecessary service request')):
                    product = complete(flow, batch)
            else:
                product = complete(flow, batch)
            stem = f'T11-real-{language}-{name}'
            for kind in ('mp3', 'srt'):
                shutil.copy2(flow.narration_path(batch, kind), Path('docs/verification') / (stem + '.' + kind))
            pcm = subprocess.check_output([os.environ['EBOOK2MP4_FFMPEG'], '-v', 'error', '-i',
                str(flow.narration_path(batch)), '-f', 's16le', '-ac', '1', '-ar', '24000', '-'])
            assert abs(len(pcm) / 48 - product['duration_ms']) <= 2
            case['variants'].append(dict(name=name, duration_ms=product['duration_ms'], decoded_ms=len(pcm)/48,
                chunks=[{k:c[k] for k in ('text', 'start_ms', 'end_ms', 'duration_ms', 'pause_after_ms', 'reused')}
                        for c in product['chunks']]))
        assert case['variants'][2]['duration_ms'] - case['variants'][1]['duration_ms'] == 600
        preview = flow.start_voice_preview(batch, text=text, start=0, end=len(text))
        assert preview.wait(90) and preview.state['status'] == 'completed', preview.state
        flow.finish_voice_preview(preview)
        assert flow.voice_preview_path(batch).read_bytes() == flow.narration_path(batch).read_bytes()
        player = PreviewPlayer()
        try:
            player.play(flow.narration_path(batch))
            assert player.playing()
        finally:
            player.stop()
        case.update(preview_matches_formal=True, windows_play_stop=True)
        evidence['cases'].append(case)
        Path('docs/verification/T11-real.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
        print(language, 'verified', flush=True)


if __name__ == '__main__':
    main()
