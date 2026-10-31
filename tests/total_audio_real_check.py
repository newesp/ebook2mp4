"""Retained media evidence: real FFmpeg, synthetic TTS bytes, zero merge requests."""
from pathlib import Path
import array
import hashlib
import json
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_total_audio as fixture


def run():
    case = fixture.TotalAudioJourney()
    case.setUp()
    out = Path('docs/verification/T14/media')
    out.mkdir(parents=True, exist_ok=True)
    try:
        ids = case.prepare(3)
        source_frames = [len(case.pcm(case.flow.narration_path(i)))//2 for i in ids]
        measurements = []
        for count in (1, 2, 3):
            case.flow.save_assembly_settings(ids[:count])
            product = case.merge()
            case.flow.export_total_audio(out/f'{count}-batch')
            pcm = case.pcm(case.flow.total_audio_path())
            samples = array.array('h', pcm)
            silence_peaks = []
            boundary = 0
            for index in range(count-1):
                boundary += source_frames[index]
                # Inspect the middle 300 ms, excluding lossy encoder ringing at each edge.
                silence_peaks.append(max(abs(s) for s in samples[boundary+2400:boundary+9600]))
                boundary += 12000
            assert all(peak <= 2 for peak in silence_peaks), silence_peaks
            actual_ms = len(pcm)//48
            assert actual_ms-sum(source_frames[:count])//24 == (count-1)*500
            srt = case.flow.total_audio_path('srt').read_text(encoding='utf-8')
            measurements.append(dict(batches=count, source_frames=source_frames[:count],
                decoded_frames=len(pcm)//2, duration_ms=actual_ms,
                added_silence_ms=(count-1)*500, silence_peaks=silence_peaks,
                new_tts_requests=0, cues=srt, mp3_sha256=hashlib.sha256(case.flow.total_audio_path().read_bytes()).hexdigest()))
        report = dict(tool=subprocess.check_output([shutil.which('ffmpeg'), '-version'], text=True).splitlines()[0],
                      service='synthetic response fixture, no live service', measurements=measurements)
        (out.parent/'real-media.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(measurements, ensure_ascii=False), flush=True)
    finally:
        case.doCleanups()


if __name__ == '__main__':
    run()
