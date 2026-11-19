"""Audit measured native chrome and retain this fixture's decoded products."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
BASE=ROOT/'docs/verification/v2-shell-refactor'


def audit():
    results={}
    for phase in ('before-track-fix','native-final'):
        records=json.loads((BASE/phase/'measurements.json').read_text(encoding='utf-8'))
        rows=[];parents={};voice=[];joins=[]
        for record in records:
            boxes=record['boxes'];document=boxes['list_header']
            for name in ('navigation','documents','workspace','footer','editor'):
                parents.setdefault(name,set()).add((boxes[name]['widget'],boxes[name]['parent']))
            if 'voice_spacing' in record:
                spacing=dict(name=record['name'],**record['voice_spacing'])
                save=next((c for c in record.get('controls',[]) if c['text'] in ('儲存設定','只儲存設定')),None)
                primary=next((c for c in record.get('controls',[]) if c['text'].startswith(('前往音訊','套用到既有'))),None)
                if save and primary:
                    spacing['active_next_label']=primary['text']
                    spacing['raw_footer_gap']=spacing['footer_gap']
                    spacing['footer_gap']=primary['x']-save['x']-save['width']
                voice.append(spacing)
            if document['mapped']:
                for name,box in boxes.items():
                    if name.startswith('header-') and box['mapped']:
                        delta=[box['y']-document['y'],box['height']-document['height']]
                        rows.append(dict(view=record['name'],header=name,delta=delta,passed=max(map(abs,delta))<=2))
                if record.get('page_id','').startswith('audio.joins') and 'active_content' in boxes:
                    delta=boxes['active_content']['y']-boxes['list_content']['y']
                    joins.append(dict(view=record['name'],content_delta=delta,passed=abs(delta)<=2))
        results[phase]=dict(frames=len(records),headers=rows,failed_headers=sum(not r['passed'] for r in rows),
            fixed_instances={k:len(v)==1 for k,v in parents.items()},voice_spacing=voice,join_content=joins,
            callback_errors=[e for r in records for e in r['errors']])
    final=results['native-final']
    explicit=json.loads((BASE/'join-tests/shell-anchors.json').read_text(encoding='utf-8'))
    results['expanded_join_anchors']=dict(rows=len(explicit),maximum_delta=max(
        abs(value) for row in explicit for value in row.get('deltas',[])))
    (BASE/'native-audit.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    assert not final['failed_headers'] and not final['callback_errors']
    assert all(final['fixed_instances'].values())
    assert all(row['passed'] for row in final['join_content'])
    assert explicit and results['expanded_join_anchors']['maximum_delta']<=2
    for row in final['voice_spacing']:
        assert row['pair'][0]==row['pair'][1]
        assert (row['pair_gap'],row['footer_gap'],row['text_gap'])==(4,4,8)
    print(f'Native audit: {final["frames"]} frames, no header/instance/callback regressions.')


def products():
    from ebook2mp4.workflow import ProjectWorkflow
    flow=ProjectWorkflow.open(ROOT/'.scratch/v2-shell-refactor/package-book')
    tools=ROOT/'dist/ebook2mp4/_internal/tools/ffmpeg'
    folder=BASE/'products';folder.mkdir(exist_ok=True)
    records=[]
    for route,product in (('audio',flow.total_audio()),('uniform-video',flow.total_video(method='total-audio')),
                          ('merged-video',flow.total_video(method='batch-videos'))):
        assert product is not None,route
        media='mp3' if route=='audio' else 'mp4'
        for kind in (media,'srt'):
            source=flow._path(product[kind]['path']);target=folder/(route+'.'+kind)
            shutil.copy2(source,target)
        path=folder/(route+'.'+media)
        options=dict(check=True,creationflags=subprocess.CREATE_NO_WINDOW)
        probe=json.loads(subprocess.check_output([str(tools/'ffprobe.exe'),'-v','error','-show_streams',
            '-show_format','-of','json',str(path)],creationflags=subprocess.CREATE_NO_WINDOW))
        subprocess.run([str(tools/'ffmpeg.exe'),'-v','error','-i',str(path),'-f','null','-'],**options)
        records.append(dict(route=route,id=product['id'],sources=len(product.get('sources',[])),
            duration=probe['format']['duration'],streams=[s['codec_name'] for s in probe['streams']],
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),decoded=True,
            stale_after_deliberate_selection_change=product['stale']))
    (BASE/'exe-products.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    print('All three EXE output routes decoded using bundled media tools.')


if __name__=='__main__':
    if '--products' in sys.argv:products()
    else:audit()
