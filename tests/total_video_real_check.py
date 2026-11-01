"""Real FFmpeg encoding evidence; all speech bytes come from a synthetic fixture."""
from pathlib import Path
import json
import os
import shutil
import subprocess
from unittest.mock import patch
from PIL import Image

import test_total_audio as fixture
from ebook2mp4.workflow import ProjectWorkflow


def run():
    case = fixture.TotalAudioJourney()
    case.setUp()
    out = Path('docs/verification/T16/media')
    out.mkdir(parents=True, exist_ok=True)
    try:
        tone = case.path/'tone.mp3'
        subprocess.run([os.environ['EBOOK2MP4_FFMPEG'], '-v', 'error', '-f', 'lavfi', '-i',
                        'sine=frequency=440:duration=1.2', '-y', str(tone)], check=True)
        ids = case.prepare(2, audio=tone.read_bytes())
        case.flow.save_assembly_settings(ids)
        case.merge()
        case.flow.export_total_audio(out/'audio')
        measurements = []
        for resolution, kind in [('720p', 'portrait'), ('1080p', 'transparent'), ('1080p', 'landscape')]:
            path = case.path/('cover.jpg' if kind == 'portrait' else 'cover.png')
            if kind == 'transparent':
                image = Image.new('RGBA', (80, 120), (0, 0, 0, 0))
                image.paste((255, 0, 0, 128), (0, 0, 80, 60))
            else:
                image = Image.new('RGB', (80, 120) if kind == 'portrait' else (160, 90), 'red')
            image.save(path)
            case.flow.save_total_video_settings(image=case.flow.inspect_total_video_image(path), resolution=resolution)
            path.unlink()
            case.flow = ProjectWorkflow.open(case.flow.root)
            with patch('edge_tts.Communicate', side_effect=AssertionError('no new TTS')):
                job = case.flow.start_total_video()
                assert job.wait(60), job.state
                assert job.state['status'] == 'completed', job.state
                product = case.flow.finish_total_video(job)
            destination = out/(resolution+'-'+kind)
            case.flow.export_total_video(destination)
            video = destination/'total.mp4'
            probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(video)]))
            frame = destination/'frame.png'
            subprocess.run([os.environ['EBOOK2MP4_FFMPEG'], '-v', 'error', '-i', str(video), '-frames:v', '1', str(frame)], check=True)
            with Image.open(frame) as decoded:
                w, h = decoded.size
                black = decoded.getpixel((10, h//2))
                top = decoded.getpixel((w//2, h//4))
                bottom = decoded.getpixel((w//2, 3*h//4))
                if kind != 'landscape':
                    assert max(black[:3]) <= 5, black
                if kind == 'transparent':
                    assert 118 <= top[0] <= 138 and max(top[1:3]) <= 8, top
                    assert max(bottom[:3]) <= 5, bottom
            duration = float(probe['format']['duration'])*1000
            assert abs(duration-2900) <= 200, duration
            assert (destination/'total.srt').read_bytes() == (out/'audio/total.srt').read_bytes()
            measurements.append(dict(resolution=resolution, picture=kind, audio_ms=2900, video_ms=duration,
                new_tts_requests=0, left_pixel=black, top_pixel=top, bottom_pixel=bottom, probe=probe,
                report_duration_ms=product['duration_ms']))
        target = Path('.scratch/t16-native/book')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(case.flow.root, target)
        (out.parent/'real-media.json').write_text(json.dumps(measurements, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps([dict(resolution=m['resolution'], picture=m['picture'], video_ms=m['video_ms']) for m in measurements]), flush=True)
    finally:
        case.doCleanups()


if __name__ == '__main__':
    run()
