"""Preserve final T17 media evidence and an isolated project for native/package inspection."""
import json
import os
from pathlib import Path
import shutil
import subprocess
from unittest.mock import patch

import test_total_video_background as fixture


def run():
    case = fixture.BackgroundJourney()
    case.setUp()
    out = Path('docs/verification/T17')
    (out/'media').mkdir(parents=True, exist_ok=True)
    rows = []
    try:
        tone = case.path/'旁白音調.mp3'
        subprocess.run([os.environ['EBOOK2MP4_FFMPEG'], '-v', 'error', '-y', '-f', 'lavfi', '-i',
                        'sine=frequency=440:duration=1.2', str(tone)], check=True)
        ids = case.prepare(2, audio=tone.read_bytes())
        case.flow.save_assembly_settings(ids)
        case.merge()
        case.flow.export_total_audio(out/'media/audio')
        for name, seconds, mode, resolution, portrait in [
                ('loop', .3, 'loop', '720p', False),
                ('hold', .3, 'hold', '1080p', True),
                ('trim', 4.8, 'loop', '720p', False)]:
            source = fixture.background(case.path/(name+'.mp4'), seconds, portrait)
            case.flow.save_total_video_settings(background=case.flow.inspect_total_video_background(source),
                source_type='video', background_mode=mode, resolution=resolution)
            source.unlink()
            with patch('edge_tts.Communicate', side_effect=AssertionError('no TTS')):
                job = case.flow.start_total_video()
                assert job.wait(60), job.state
                assert job.state['status'] == 'completed', job.state
                product = case.flow.finish_total_video(job)
            target = out/'media'/name
            case.flow.export_total_video(target)
            probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
                '-show_format', '-of', 'json', str(target/'total.mp4')]))
            assert abs(float(probe['format']['duration'])*1000-2900)<=200
            assert (target/'total.srt').read_bytes() == (out/'media/audio/total.srt').read_bytes()
            rows.append(dict(case=name, source_ms=round(seconds*1000), resolution=resolution, mode=mode,
                duration_ms=product['duration_ms'], new_tts_requests=0, srt_bytes_identical=True,
                sample_pixel=fixture.pixel(target/'total.mp4', 2.5), probe=probe))
        # A longer short background makes the native preview/hold inspection easy to observe.
        source = fixture.background(case.path/'原生測試背景.mp4', .9, True)
        case.flow.save_total_video_settings(background=case.flow.inspect_total_video_background(source),
            source_type='video', background_mode='hold', resolution='720p')
        project = Path('.scratch/t17-native/book')
        project.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(case.flow.root, project)
        (out/'real-media.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(rows, ensure_ascii=False, default=str), flush=True)
    finally:
        case.doCleanups()


if __name__ == '__main__':
    run()
