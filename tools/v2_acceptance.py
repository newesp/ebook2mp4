"""Isolated synthetic fixtures and genuine source/EXE launch evidence."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'.scratch/v2-work'
DEPS = ROOT/'.scratch/build-tools'


def environment(home, *, package=False):
    home.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(DEPS),
        EBOOK2MP4_APP_HOME=str(home), EBOOK2MP4_VOICE_HOME=str(home/'voice'),
        EBOOK2MP4_KOKORO_HOME=str(home/'kokoro'), EBOOK2MP4_OCR_HOME=str(home/'ocr'),
        LOCALAPPDATA=str(home/'local'), APPDATA=str(home/'roaming'))
    if package:
        env['PATH'] = r'C:\Windows\System32;C:\Windows'
        for key in ('EBOOK2MP4_FFMPEG', 'EBOOK2MP4_FFPROBE', 'EBOOK2MP4_TESSERACT', 'PYTHONPATH'):
            env.pop(key, None)
    return env


def fixtures():
    # Only the frozen source/test tree may implement this baseline journey.
    source = ROOT/'archives/v1/source'
    sys.path[:0] = [str(source), str(source/'tests')]
    tools = ROOT/'archives/v1/ebook2mp4/_internal/tools/ffmpeg'
    os.environ.update(environment(BASE/'fixture-home'))
    os.environ['PATH'] = str(tools)+os.pathsep+os.environ['PATH']
    os.environ['EBOOK2MP4_FFMPEG'] = str(tools/'ffmpeg.exe')
    os.environ['EBOOK2MP4_FFPROBE'] = str(tools/'ffprobe.exe')
    from test_outputs import OutputsJourney
    import ebook2mp4.workflow as workflow
    case = OutputsJourney('test_missing_visual_publishes_audio_reopen_only_encodes_video')
    case.setUp()
    try:
        wave = case.path/'controlled.mp3'
        subprocess.run([str(tools/'ffmpeg.exe'), '-v', 'error', '-f', 'lavfi', '-i',
                        'sine=frequency=440:duration=3', str(wave)], check=True)
        case.plan(case.prepare(2, audio=wave.read_bytes()))
        case.visual()
        result = case.run_outputs()
        assert result['status'] == 'completed'
        export = BASE/'export'
        export.mkdir(parents=True, exist_ok=True)
        for folder in (export/'audio', export/'video'):
            if folder.exists() and not any(folder.iterdir()):
                folder.rmdir()
        case.flow.export_total_audio(export/'audio')
        case.flow.export_total_video(export/'video')
        media = {}
        for kind, path in (('mp3', case.flow.total_audio_path()), ('mp4', case.flow.total_video_path())):
            probe = json.loads(subprocess.check_output([str(tools/'ffprobe.exe'), '-v', 'error',
                '-show_streams', '-show_format', '-of', 'json', str(path)]))
            subprocess.run([str(tools/'ffmpeg.exe'), '-v', 'error', '-i', str(path), '-f', 'null', '-'], check=True)
            destination = ROOT/'docs/verification/v1-baseline'/('synthetic.'+kind)
            shutil.copy2(path, destination)
            media[kind] = dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                              duration=probe['format']['duration'],
                              streams=[s['codec_name'] for s in probe['streams']])
        shutil.copy2(case.flow.total_video_path('srt'), ROOT/'docs/verification/v1-baseline/synthetic.srt')
        for name in ('v1-source', 'v1-package', 'v2-package'):
            target = BASE/name
            shutil.copytree(case.flow.root, target/'book')
            home = target/'home'
            home.mkdir()
            (home/'session.json').write_text(json.dumps(dict(last_project=str(target/'book'))), encoding='utf-8')
        evidence = dict(implementation=str(workflow.__file__), real_ffmpeg=True,
                        controlled_tts='synthetic sine wave; no network or paid request',
                        exported=True, media=media)
        (ROOT/'docs/verification/v1-baseline/media.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
        print(json.dumps(evidence))
    finally:
        case.doCleanups()


def launch(name):
    target = BASE/name
    package = name != 'v1-source'
    cwd = ROOT/'archives/v1/source' if name == 'v1-source' else target
    exe = (ROOT/'archives/v1/ebook2mp4/ebook2mp4.exe' if name == 'v1-package'
           else ROOT/'dist/ebook2mp4/ebook2mp4.exe')
    cmd = [str(exe)] if package else [sys.executable, '-m', 'ebook2mp4']
    env = environment(target/'home', package=package)
    if not package:
        tools = ROOT/'archives/v1/ebook2mp4/_internal/tools'
        env.update(EBOOK2MP4_FFMPEG=str(tools/'ffmpeg/ffmpeg.exe'),
                   EBOOK2MP4_FFPROBE=str(tools/'ffmpeg/ffprobe.exe'))
    evidence = ROOT/('docs/verification/v1-baseline' if name.startswith('v1') else 'docs/verification/v2-manuscript')
    evidence.mkdir(parents=True, exist_ok=True)
    with (evidence/(name+'-stderr.txt')).open('w', encoding='utf-8') as errors:
        child = subprocess.Popen(cmd, cwd=cwd, env=env, stderr=errors)
        record = dict(command=cmd, cwd=str(cwd), pid=child.pid, isolated_settings=True,
                      system_only_path=package, book=str(target/'book'))
        output = evidence/(name+'-launch.json')
        output.write_text(json.dumps(record, indent=2), encoding='utf-8')
        print(json.dumps(record), flush=True)
        record['exit_code'] = child.wait()
        record['normal_exit'] = record['exit_code'] == 0
        output.write_text(json.dumps(record, indent=2), encoding='utf-8')
        print(json.dumps(record), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('fixtures', 'v1-source', 'v1-package', 'v2-package'))
    args = parser.parse_args()
    fixtures() if args.action == 'fixtures' else launch(args.action)
