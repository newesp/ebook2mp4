"""Read-only comparison of delivered outputs with their route-specific sources."""
from copy import deepcopy
import asyncio

from . import assembly, total_video, video_merge
from .workflow import ProjectError


ROUTES = (('audio', '總音訊 MP3／SRT'), ('total-audio', '總影片 · 總音訊製片'),
          ('batch-videos', '總影片 · 批次影片合併'))
TASK_NAMES = dict(pending='準備中', running='處理中', cancelling='取消中', cancelled='已取消',
                  completed='已完成', failed='失敗', interrupted='已中斷')


async def inspect_versions(flow) -> list[dict]:
    flow._check_current()
    rows = []
    for route, name in ROUTES:
        await asyncio.sleep(0)
        row: dict = dict(route=route, name=name, product=None, reasons=[], sources=[], current_sources=[],
                   settings={}, current_settings={}, status='尚未製作', error='', task=None, version=0)
        try:
            history = flow.total_audio_runs() if route == 'audio' else flow.total_video_runs(method=route)
            if history:
                row['task'] = history[-1]
            raw = flow.state.get('total_audio') if route == 'audio' else None
            if route != 'audio':
                raw = flow.state.get('total_video_products', {}).get(route)
                legacy = flow.state.get('total_video')
                if raw is None and legacy and legacy.get('method', 'total-audio') == route:
                    raw = legacy
            row['product'] = deepcopy(raw)
            if raw:
                published = [r for r in history if r['published']]
                row['version'] = next((i for i, r in enumerate(published, 1) if r['snapshot']['id'] == raw['id']), 0)
            shared = assembly.settings(flow)
            if route == 'total-audio':
                row['current_settings'] = total_video.settings(flow)
                audio = assembly.total_audio(flow, verify_media=False)
                if audio:
                    names = {b['id']: b['name'] for b in flow.state['batches']}
                    row['current_sources'] = [dict(name=names.get(s['batch_id'], '已移除批次'),
                                                  total_audio_id=audio['id'], **s) for s in audio['sources']]
                if raw:
                    row['sources'] = [deepcopy(raw['audio'])]
                    row['settings'] = deepcopy(raw['visual'])
                    if total_video.normalized_visual(raw['visual']) != row['current_settings']:
                        row['reasons'].append('全片素材、背景模式或解析度已變更。')
                    if not audio or audio['stale']:
                        row['reasons'].append('總音訊缺少或待更新。先更新總 MP3／SRT。')
                    elif raw['audio'] != {k: audio[k] for k in ('id', 'mp3', 'srt', 'duration_ms')}:
                        row['reasons'].append('總 MP3／SRT 來源版本已更新。')
            else:
                row['current_settings'] = dict(batch_ids=[s['batch_id'] for s in shared['sources']],
                                               pause_ms=shared['pause_ms'])
                if route == 'batch-videos':
                    row['current_settings']['resolution'] = video_merge.resolution(flow)
                if raw:
                    row['sources'] = deepcopy(raw['sources'])
                    row['settings'] = dict(batch_ids=[s['batch_id'] for s in raw['sources']], pause_ms=raw['pause_ms'])
                    if route == 'batch-videos':
                        row['settings']['resolution'] = raw['visual']['resolution']
                    if row['settings'] != row['current_settings']:
                        row['reasons'].append('合併選取、順序、停頓或此路徑解析度已變更。')
                saved_sources = {s['batch_id']: s for s in raw['sources']} if raw else {}
                for saved in shared['sources']:
                    identity = saved['batch_id']
                    batch_name = next((b['name'] for b in flow.state['batches'] if b['id'] == identity), '已移除批次')
                    try:
                        current = (assembly.source_ref(flow, identity, verify_media=False) if route == 'audio'
                                   else video_merge.source_ref(flow, identity))
                        row['current_sources'].append(dict(name=batch_name, voice=flow.voice_settings(identity), **current))
                        if raw and saved_sources.get(identity) != current:
                            row['reasons'].append(batch_name+'：來源成品版本已更新。')
                    except ProjectError as error:
                        row['current_sources'].append(dict(batch_id=identity, name=batch_name, error=str(error)))
                        if raw:
                            row['reasons'].append(batch_name+'：'+str(error))
            if raw:
                # Validate delivered artifacts separately. Stale sources do not prevent old playback/export.
                for kind in (('mp3', 'srt') if route == 'audio' else ('mp4', 'srt')):
                    await assembly.checked_file_async(flow, raw[kind])
                product = (assembly.total_audio(flow, verify_media=False) if route == 'audio'
                           else total_video.total_video(flow, verify_media=False, method=route))
                if product and product['stale'] and not row['reasons']:
                    row['reasons'].append('選入來源或設定已變更。請更新此路徑。')
                row['status'] = '待更新 · 上一版保留' if row['reasons'] else '有效 · 與目前一致'
        except (ProjectError, KeyError, TypeError, ValueError) as error:
            row['error'] = str(error)
            row['status'] = '無法驗證成品' if row['product'] else '無法讀取來源'
        rows.append(row)
    return rows


def describe(flow, row, *, technical=False) -> str:
    product = row['product']
    if row['error']:
        message = row['name']+' · '+row['status']+'\n\n'+row['error']+'\n請檢查檔案或重新製作此路徑。其他成品保留。'
        if technical:
            import json
            message += '\n\n技術版本與檔案參照\n'+json.dumps(product, ensure_ascii=False, indent=2)
        return message
    lines = [row['name']+' · '+row['status'], '', '與目前版本比較',
             '\n'.join(row['reasons']) or row['error'] or '來源與目前設定一致。']
    if product:
        lines += ['', '這份成品使用的來源', '完成時間：'+product.get('completed_at', '未記錄'),
                  '時長：'+str(product['duration_ms'])+' 毫秒']
        if row['version']:
            lines.append(f'成品版本：第 {row["version"]} 版')
        sources = product.get('audio_snapshot', {}).get('sources', row['sources'])
        for index, source in enumerate(sources, 1):
            name = next((b['name'] for b in flow.state['batches'] if b['id'] == source.get('batch_id')), '總音訊')
            lines.append(f'{index}. {name} · 已保存的來源成品')
        details = product.get('audio_snapshot', product).get('source_details', [])
        for detail in details:
            voice = detail['voice']
            lines.append(detail['name']+'：'+voice.get('voice', '')+' · 語速 '+voice.get('rate', '')+
                         f' · 句間 {voice.get("sentence_pause_ms", 0)} 毫秒 · 段間 {voice.get("paragraph_pause_ms", 0)} 毫秒')
            if detail.get('visual'):
                lines.append('批次畫面：'+readable_settings(detail['visual']))
        if row['route'] == 'total-audio':
            lines.append('總音訊：使用製片啟動時的 MP3 與同版 SRT。')
        lines += ['', '成品設定', readable_settings(row['settings']), '', '目前設定', readable_settings(row['current_settings'])]
        for index, source in enumerate(row['current_sources'], 1):
            if 'batch_id' in source:
                lines.append(f'{index}. '+source.get('name', '')+' · '+(source.get('error') or '來源有效'))
                if source.get('voice'):
                    voice = source['voice']
                    lines.append('目前語音：'+voice.get('voice', '')+' · 語速 '+voice.get('rate', ''))
    else:
        lines += ['', '尚無成功成品。先完成有效來源，再前往此路徑製作。']
    if row['task']:
        progress = row['task']['progress']
        lines += ['', '最近任務：'+TASK_NAMES.get(progress['status'], progress['status'])+' · '+progress.get('phase', ''),
                  '任務使用啟動時的來源與設定快照。']
        if progress.get('error'):
            lines.append(str(progress['error']))
    if technical:
        import json
        lines += ['', '技術版本與檔案參照', json.dumps(dict(product=product, current_sources=row['current_sources'],
                    current_settings=row['current_settings']), ensure_ascii=False, indent=2)]
    return '\n'.join(lines)


def readable_settings(value) -> str:
    lines = []
    if 'pause_ms' in value:
        lines.append(f'額外交接停頓：{value["pause_ms"]/1000:g} 秒')
    if 'resolution' in value:
        lines.append('解析度：'+value['resolution'])
    asset = value.get('background') if value.get('source_type') == 'video' else value.get('image')
    if asset:
        lines.append('素材：'+asset.get('name', asset['path']))
        if value.get('source_type') == 'video':
            lines.append('背景模式：'+('循環' if value.get('background_mode') == 'loop' else '最後一格定格'))
    if 'batch_ids' in value:
        lines.append('批次數：'+str(len(value['batch_ids'])))
    return '\n'.join(lines) or '不使用視覺素材'
