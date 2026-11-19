"""Check artifacts produced by the packaged native UI and retain final evidence."""
from pathlib import Path
import json
import shutil
import subprocess

from ebook2mp4.workflow import ProjectWorkflow


root = Path(__file__).resolve().parents[1]
fixture = root/'.scratch/t21-package'
flow = ProjectWorkflow.open(fixture/'書籍')
before = json.loads((fixture/'before.json').read_bytes())
audio, video = flow.total_audio(), flow.total_video(method='total-audio')
assert audio['id'] == before['audio_id']
assert audio['mp3']['sha256'] == before['audio_sha256']
assert not audio['stale'] and not video['stale']
assert audio['duration_ms'] == before['expected_duration_ms']
assert abs(video['duration_ms']-audio['duration_ms']) <= 200
assert flow.total_audio_path('srt').read_bytes() == flow.total_video_path('srt').read_bytes()
assert len(flow.total_audio_runs()) == 1
assert len(flow.total_video_runs()) == 1
assert [len(flow.narration_runs(b['id'])) for b in flow.state['batches']] == before['narration_counts']
assert flow.output_formats() == ['mp3', 'mp4']
assert flow.inspect_outputs()['status'] == 'completed'
assert not (flow.root/'.production.lock').exists()
assert not list(flow.root.glob('.video-preview-*'))
tool = root/'.scratch/voice-runtime/ffprobe.exe'
probe = json.loads(subprocess.check_output([str(tool), '-v', 'error', '-show_streams', '-show_format', '-of', 'json',
                                          str(flow.total_video_path())]))
media = root/'docs/verification/T21/media'
media.mkdir(exist_ok=True)
for source, name in ((flow.total_audio_path(), 'total.mp3'), (flow.total_video_path(), 'total.mp4'),
                     (flow.total_audio_path('srt'), 'total.srt')):
    shutil.copyfile(source, media/name)
result = dict(audio_id_unchanged=True, audio_hash_unchanged=True, audio_runs=1, video_runs=1,
              narration_counts=before['narration_counts'], audio_ms=audio['duration_ms'], video_ms=video['duration_ms'],
              matching_srt=True, output_status='completed', lock_absent=True, playback_temp_absent=True, probe=probe)
(media.parent/'packaged-journey.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('Packaged UI outputs verified: 900 ms, unchanged MP3, one movie, matching SRT, no TTS or leaked lock.')
