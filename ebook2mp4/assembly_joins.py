"""Version-bound join warnings and local previews of existing batch audio."""
from __future__ import annotations

from copy import deepcopy
import asyncio
from pathlib import Path
import shutil
import tempfile
import wave

from .workflow import ProjectError, ProjectWorkflow, digest, encode
from .voice import VoiceJob
from .voice_media import ffmpeg, media_command


def ordered_batches(flow: ProjectWorkflow) -> list[dict]:
    """Sort each PDF source's slots by physical page; retain TXT/name order."""
    batches = flow.state['batches']
    groups: dict[str, list[dict]] = {}
    for batch in batches:
        if batch['kind'] == 'pdf':
            groups.setdefault(batch['source']['sha256'], []).append(batch)
    for group in groups.values():
        group.sort(key=lambda b: b['pdf']['start'])
    return [groups[b['source']['sha256']].pop(0) if b['kind'] == 'pdf' else b for b in batches]


def metadata(flow: ProjectWorkflow, batch_ids: list[str] | None = None) -> list[dict]:
    """Cheap metadata only. Media and manuscript reads belong in background work."""
    value = flow.assembly_settings()
    ids = [s['batch_id'] for s in value['sources']] if batch_ids is None else batch_ids
    if len(set(ids)) != len(ids):
        raise ProjectError('交接批次不可重複。')
    batches = [flow._batch(i) for i in ids]
    accepted = value.get('accepted_joins', [])
    result = []
    for left, right in zip(batches, batches[1:]):
        sides = []
        for batch in (left, right):
            sides.append(dict(batch_id=batch['id'], name=batch['name'], kind=batch['kind'],
                              pages=deepcopy(batch.get('pdf', {})),
                              source_name=batch['source']['original_name']))
        warning = None
        if left['kind'] == right['kind'] == 'pdf' and left['source']['sha256'] == right['source']['sha256']:
            a, b = left['pdf'], right['pdf']
            if b['start'] <= a['end'] and b['end'] >= a['start']:
                warning = dict(kind='overlap', start=max(a['start'], b['start']), end=min(a['end'], b['end']))
            elif b['start'] > a['end']+1:
                warning = dict(kind='gap', start=a['end']+1, end=b['start']-1)
            elif b['start'] < a['start']:
                warning = dict(kind='reverse', start=b['start'], end=b['end'])
            if warning is not None:
                warning['source_name'] = left['source']['original_name']
        # Bind decisions to ordered source identities, ranges, and exact audio versions.
        versions = [dict(id=b['id'], source=b['source']['sha256'],
                         pages=[b['pdf']['start'], b['pdf']['end']] if b['kind'] == 'pdf' else None,
                         reading=b.get('current_reading'), narration=b.get('narration'),
                         settings=flow.voice_settings(b['id'])) for b in (left, right)]
        key = digest(encode(dict(versions=versions)))
        result.append(dict(left=sides[0], right=sides[1], warning=warning, key=key, accepted=key in accepted))
    return result


def inspect(flow: ProjectWorkflow, batch_ids: list[str] | None = None) -> list[dict]:
    from .assembly import source_ref
    flow._check_current()
    joins = metadata(flow, batch_ids)
    for join in joins:
        for side, tail in (('left', True), ('right', False)):
            item = join[side]
            try:
                ref = source_ref(flow, item['batch_id'], verify_media=False)
                text = flow.reading_text(item['batch_id'], ref['reading_id'])
                item.update(valid=True, text=text[-1000:] if tail else text[:1000], error='')
            except ProjectError as error:
                item.update(valid=False, text='', error=str(error))
    return joins


class JoinPreviewJob(VoiceJob):
    def __init__(self, root: Path, sources: list[dict], pause_ms: int, clip_ms: int):
        from .assembly import file_signature
        self.root, self.sources = root, deepcopy(sources)
        self.source_stats = {ref['path']: file_signature(root/ref['path'])
                             for source in sources for ref in (source['mp3'], source['srt'])}
        self.pause_ms, self.clip_ms = pause_ms, clip_ms
        self.tool = ffmpeg()
        self.folder = Path(tempfile.mkdtemp(prefix='.join-preview-', dir=root))
        super().__init__(self.produce, timeout=None)

    def _run(self):
        super()._run()
        if self.state['status'] != 'completed':
            try:
                shutil.rmtree(self.folder)
            except OSError:
                with self._lock:
                    self._state['error'] = '接點暫存無法釋放，請停止播放後重試。'

    async def produce(self):
        from .assembly import captions, copy_verified_source, file_signature, write_silence
        from .narration import timestamp
        try:
            texts: list[str] = []
            cues: list[str] = []
            frames = 0
            with wave.open(str(self.folder/'joined.wav'), 'wb') as output:
                output.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
                for index, source in enumerate(self.sources):
                    for kind in ('mp3', 'srt'):
                        await copy_verified_source(self.root, source[kind], self.folder/('source.'+kind))
                    await media_command(self.tool, ['-y', '-xerror', '-err_detect', 'explode', '-i',
                        str(self.folder/'source.mp3'), '-ac', '1', '-ar', '24000', '-c:a', 'pcm_s16le',
                        str(self.folder/'source.wav')], timeout=3600)
                    with wave.open(str(self.folder/'source.wav'), 'rb') as decoded:
                        count = decoded.getnframes()
                        if count <= 0:
                            raise ProjectError('批次音訊為空，請重新製作。')
                        source_cues = captions(self.folder/'source.srt', round(count/24))
                        take = min(count, self.clip_ms*24)
                        start = count-take if index == 0 else 0
                        decoded.setpos(start)
                        relevant = [(max(begin*24, start)-start, min(end*24, start+take)-start, text)
                                    for begin, end, text in source_cues if begin*24 < start+take and end*24 > start]
                        texts.append('\n'.join(text for _, _, text in relevant))
                        for begin, end, text in relevant:
                            cues.append(f'{len(cues)+1}\n{timestamp(round((frames+begin)/24))} --> '
                                        f'{timestamp(round((frames+end)/24))}\n{text}\n\n')
                        remaining = take
                        while remaining:
                            await asyncio.sleep(0)
                            data = decoded.readframes(min(remaining, 24000))
                            if not data:
                                raise ProjectError('批次音訊解碼資料不完整。')
                            output.writeframesraw(data)
                            remaining -= len(data)//2
                        frames += take
                    if index == 0:
                        frames += await write_silence(output, self.pause_ms)
            path = self.folder/'preview.mp3'
            await media_command(self.tool, ['-y', '-i', str(self.folder/'joined.wav'), '-c:a',
                                           'libmp3lame', '-b:a', '96k', str(path)])
            await media_command(self.tool, ['-y', '-xerror', '-i', str(path), '-ac', '1', '-ar', '24000',
                                           '-c:a', 'pcm_s16le', str(self.folder/'verified.wav')])
            with wave.open(str(self.folder/'verified.wav'), 'rb') as decoded:
                actual = decoded.getnframes()
                remaining = actual
                while data := decoded.readframes(24000):
                    await asyncio.sleep(0)
                    remaining -= len(data)//2
                if remaining or abs(actual-frames) > 24:
                    raise ProjectError('接點音訊時間或解碼資料不一致，未播放。')
            srt = self.folder/'preview.srt'
            srt.write_text(''.join(cues), encoding='utf-8')
            if cues:
                captions(srt, round(actual/24))
            for name in ('joined.wav', 'verified.wav', 'source.wav', 'source.mp3', 'source.srt'):
                (self.folder/name).unlink(missing_ok=True)
            return dict(path=str(path), srt_path=str(srt), duration_ms=round(actual/24),
                        left_text=texts[0], right_text=texts[1], signature=file_signature(path))
        except (OSError, wave.Error):
            raise ProjectError('接點試聽讀寫失敗。請檢查來源、磁碟空間與檔案占用。') from None

    def release(self):
        if not self.wait(0):
            raise ProjectError('請等待接點試聽停止後再釋放。')
        try:
            if self.folder.exists():
                shutil.rmtree(self.folder)
        except OSError:
            raise ProjectError('接點暫存仍被占用。請停止播放後重試。') from None


def start_preview(flow: ProjectWorkflow, batch_ids: list[str], index: int, pause_ms: int, clip_ms: int) -> JoinPreviewJob:
    from .assembly import source_ref
    from .production_lock import production_active
    flow._check_current()
    if flow._assembly_preview_job is not None:
        raise ProjectError('請先停止並釋放目前接點試聽。')
    if production_active(flow.root/'.production.lock'):
        raise ProjectError('專案另有製作任務，請等待完成後再試聽。')
    if type(index) is not int or not 0 <= index < len(batch_ids)-1:
        raise ProjectError('請選擇兩個相鄰批次的接點。')
    if type(pause_ms) is not int or not 0 <= pause_ms <= 5000:
        raise ProjectError('額外交接停頓須為 0～5 秒，精確至毫秒。')
    if type(clip_ms) is not int or clip_ms not in (3000, 5000, 10000):
        raise ProjectError('前後試聽長度須為 3、5 或 10 秒。')
    metadata(flow, batch_ids)
    sources = [source_ref(flow, i, verify_media=False) for i in batch_ids[index:index+2]]
    flow._space(flow.root, 25_000_000)
    job = JoinPreviewJob(flow.root, sources, pause_ms, clip_ms)
    flow._assembly_preview_job = job
    return job


def finish_preview(flow: ProjectWorkflow, job: JoinPreviewJob) -> dict:
    from .assembly import file_signature, source_ref
    if job is not flow._assembly_preview_job or not job.wait(0):
        raise ProjectError('請等待所屬接點試聽完成。')
    flow._check_current()
    for source in job.sources:
        if source_ref(flow, source['batch_id'], verify_media=False) != source:
            raise ProjectError('接點來源版本已變更，請重新檢查並試聽。')
    for path, signature in job.source_stats.items():
        if file_signature(flow._path(path)) != signature:
            raise ProjectError('接點來源檔在準備後變更，請重新檢查並試聽。')
    result = job.result
    if file_signature(Path(result['path'])) != result['signature']:
        raise ProjectError('接點試聽檔已變更，請重新產生。')
    return result
