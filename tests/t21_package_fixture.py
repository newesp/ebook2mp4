"""Prepare only synthetic portable inputs for the final packaged-app journey."""
from pathlib import Path
import json
import shutil

from test_outputs import OutputsJourney


def main():
    case = OutputsJourney('test_missing_visual_publishes_audio_reopen_only_encodes_video')
    case.setUp()
    try:
        case.plan(case.prepare(2))
        result = case.run_outputs()
        assert result['status'] == 'partial'
        target = Path(__file__).resolve().parents[1]/'.scratch/t21-package'
        target.mkdir()
        shutil.copytree(case.flow.root, target/'書籍')
        shutil.copyfile(case.picture(), target/'cover.png')
        app = target/'app'
        app.mkdir()
        (app/'session.json').write_text(json.dumps(dict(last_project=str(target/'書籍'))), encoding='utf-8')
        evidence = dict(audio_id=case.flow.total_audio()['id'], audio_sha256=case.flow.total_audio()['mp3']['sha256'],
                        narration_counts=[len(case.flow.narration_runs(b['id'])) for b in case.flow.state['batches']],
                        expected_duration_ms=900, source='synthetic sine-wave TTS substitute; no real service')
        (target/'before.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
        print(json.dumps(dict(project=str(target/'書籍'), before=evidence), ensure_ascii=False))
    finally:
        case.doCleanups()


if __name__ == '__main__':
    main()
