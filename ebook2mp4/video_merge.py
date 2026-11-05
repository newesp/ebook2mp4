"""Offline assembly of versioned batch MP4/SRT, independent of total audio."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import asyncio
import shutil
import tempfile
import uuid

from .workflow import ProjectWorkflow, ProjectError, digest, encode, now
from . import assembly
from .assembly_joins import metadata, ordered_batches
from .narration import timestamp
from .total_video import TotalVideoJob, probe_background, normalized_visual
from .voice_media import ffmpeg


def audio_identity(flow: ProjectWorkflow, batch_id: str) -> dict:
    """Compare version metadata without requiring the original MP3 to exist."""
    batch = flow._batch(batch_id)
    product = batch.get('narration')
    if (not product or not batch.get('current_reading') or product['reading_id'] != batch['current_reading']
            or product['settings'] != flow.voice_settings(batch_id)
            or not product['chunks'] or any(c['status'] != 'completed' for c in product['chunks'])):
        raise ProjectError('朗讀稿或語音設定已變更，請更新本批音訊及影片。')
    return dict(batch_id=batch_id, product_id=product['id'], reading_id=product['reading_id'],
        settings_sha256=digest(encode(product['settings'])), mp3=deepcopy(product['mp3']), srt=deepcopy(product['srt']))


def source_ref(flow: ProjectWorkflow, batch_id: str, *, verify_media=False) -> dict:
    try:
        batch = flow._batch(batch_id)
        saved = batch.get('video', {})
        product = saved.get('total_video')
        if not product:
            raise ProjectError('缺少批次 MP4／SRT，請先製作本批影片。')
        audio = audio_identity(flow, batch_id)
        expected_audio = dict(id=audio['product_id'], mp3=audio['mp3'], srt=audio['srt'],
                              duration_ms=batch['narration']['duration_ms'])
        if (product['audio'] != expected_audio or normalized_visual(product['visual']) !=
                normalized_visual(saved['total_video_settings'])):
            raise ProjectError('批次影片待更新，請重新製作本批 MP4／SRT。')
        result = dict(batch_id=batch_id, product_id=product['id'], audio=audio,
                      duration_ms=product['duration_ms'], mp4=deepcopy(product['mp4']), srt=deepcopy(product['srt']))
        for kind in ('mp4', 'srt'):
            if verify_media:
                assembly.checked_file(flow, result[kind])
            elif not flow._path(result[kind]['path']).is_file():
                raise ProjectError('缺少批次 MP4／SRT，請重新製作本批影片。')
        return result
    except (KeyError, TypeError):
        raise ProjectError('批次影片記錄損壞，請重新製作本批影片。') from None


def resolution(flow: ProjectWorkflow) -> str:
    value = flow.state.get('video_merge_resolution', '1080p')
    if value not in ('1080p', '720p'):
        raise ProjectError('合併影片解析度無效，請重新儲存設定。')
    return value


def save_settings(flow: ProjectWorkflow, batch_ids: list[str], pause_ms: int = 500, *,
                  resolution: str = '1080p', accepted_joins: list[str] | None = None) -> None:
    from .production_lock import ProductionLease
    if not batch_ids or len(set(batch_ids)) != len(batch_ids):
        raise ProjectError('請至少選取一個有效批次，不可重複。')
    if type(pause_ms) is not int or not 0 <= pause_ms <= 5000:
        raise ProjectError('額外交接停頓須為 0～5 秒，精確至毫秒。')
    if resolution not in ('1080p', '720p'):
        raise ProjectError('影片解析度只支援 1080p 或 720p。')
    if accepted_joins is not None and (not isinstance(accepted_joins, list) or any(not isinstance(k,str) for k in accepted_joins)):
        raise ProjectError('接點確認記錄無效。')
    lease = ProductionLease(flow.root/'.production.lock')
    try:
        flow._check_current()
        for identity in batch_ids:
            source_ref(flow, identity)
        accepted = assembly.settings(flow).get('accepted_joins', []) if accepted_joins is None else accepted_joins
        manifest = flow.state
        manifest['assembly_settings'] = dict(sources=[audio_identity(flow, i) for i in batch_ids], pause_ms=pause_ms,
            accepted_joins=[j['key'] for j in metadata(flow, batch_ids) if j['key'] in accepted])
        manifest['video_merge_resolution'] = resolution
        flow._commit(manifest, [])
    finally:
        lease.release()


async def validate_source(flow: ProjectWorkflow, source: dict, command) -> dict:
    for kind in ('mp4','srt'):
        await assembly.checked_file_async(flow, source[kind])
    path = flow._path(source['mp4']['path'])
    info = await probe_background(path)
    duration = info['duration_ms']
    # Both streams must decode, even when only a short join will be shown.
    await command(['-xerror','-err_detect','explode','-i',str(path),'-map','0:v:0','-map','0:a:0',
                   '-f','null','-'], phase='驗證批次影音', duration_ms=duration)
    if abs(duration-source['duration_ms']) > 200:
        raise ProjectError('批次影片實際時長與成品記錄不符，請重新製作。')
    return dict(info, cues=assembly.captions(flow._path(source['srt']['path']),duration))


async def inspect(flow: ProjectWorkflow) -> list[dict]:
    from .voice_media import media_command
    async def command(args, **kwargs):
        await media_command(ffmpeg(), args, timeout=86400)
    flow._check_current()
    rows = []
    for batch in ordered_batches(flow):
        row = dict(batch_id=batch['id'],name=batch['name'],valid=False,duration_ms=0)
        try:
            source = source_ref(flow,batch['id'])
            info = await validate_source(flow,source,command)
            row.update(valid=True,source=source,duration_ms=info['duration_ms'],reason='有效 · MP4／SRT 已驗證')
        except (ProjectError,OSError) as error:
            row['reason'] = str(error)
        rows.append(row)
    voices = {digest(encode(flow.voice_settings(r['batch_id']))) for r in rows if r['valid']}
    if len(voices)>1:
        for row in rows:
            if row['valid']: row['reason'] += ' · 音色／語速可能不同，保留原聲'
    return rows


def stale(flow: ProjectWorkflow, product: dict, *, verify_media=False) -> bool:
    value=assembly.settings(flow)
    if (product['pause_ms'] != value['pause_ms'] or product['visual']['resolution'] != resolution(flow)
            or [s['batch_id'] for s in product['sources']] != [s['batch_id'] for s in value['sources']]):
        return True
    try:
        return any(s != source_ref(flow,s['batch_id'],verify_media=verify_media) for s in product['sources'])
    except ProjectError:
        return True


class MergeVideoJob(TotalVideoJob):
    async def command(self, args, *, phase, duration_ms):
        for attempt in range(1,4):
            self.progress(attempt=attempt)
            try:
                return await super().command(args,phase=phase,duration_ms=duration_ms)
            except ProjectError:
                if attempt==3: raise
                await asyncio.sleep(attempt/2)
        raise AssertionError('unreachable')

    async def produce(self):
        media=self.folder/'media'
        success=False
        try:
            media.mkdir()
            flow=ProjectWorkflow.open(self.root)
            source_stats={ref['path']:assembly.file_signature(flow._path(ref['path']))
                          for source in self.snapshot['sources'] for ref in (source['mp4'],source['srt'])}
            cues: list[str]=[]
            texts=[]
            timeline=[]
            offset=0
            concat=[]
            width,height=(1920,1080) if self.snapshot['visual']['resolution']=='1080p' else (1280,720)
            for index,source in enumerate(self.snapshot['sources']):
                if source_ref(flow,source['batch_id']) != source:
                    raise ProjectError('批次影片版本已變更，請重新檢查來源。')
                info=await validate_source(flow,source,self.command)
                path=media/f'source-{index}.mp4'
                await assembly.copy_verified_source(self.root,source['mp4'],path)
                duration=info['duration_ms']
                start=0
                if self.snapshot.get('clip_ms'):
                    take=min(duration,self.snapshot['clip_ms'])
                    start=duration-take if index==0 else 0
                    duration=take
                pause=self.snapshot['pause_ms'] if index<len(self.snapshot['sources'])-1 else 0
                relevant=[]
                for begin,end,text in info['cues']:
                    begin,end=max(0,begin-start),min(duration,end-start)
                    if begin<end:
                        cues.append(f'{len(cues)+1}\n{timestamp(offset+begin)} --> {timestamp(offset+end)}\n{text}\n\n')
                        relevant.append(text)
                texts.append('\n'.join(relevant))
                segment=media/f'segment-{index}.mkv'
                length=duration+pause
                # PCM avoids encoder padding at intermediate joins. Exact concat durations preserve millisecond pauses.
                await self.command(['-y','-ss',f'{start/1000:.6f}','-i',str(path),
                    '-map','0:v:0','-map','0:a:0','-vf',
                    f'setpts=PTS-STARTPTS,scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps=30,tpad=stop_mode=clone:stop_duration={pause/1000+1:.6f}',
                    '-af',f'atrim=duration={duration/1000:.6f},asetpts=PTS-STARTPTS,apad',
                    '-c:v','libx264','-preset','fast','-pix_fmt','yuv420p','-c:a','pcm_s16le','-ar','48000','-ac','2',
                    '-t',f'{length/1000:.6f}',str(segment)],phase=f'處理批次 {index+1}/{len(self.snapshot["sources"])}',duration_ms=length)
                concat.append(f"file '{segment.name}'\nduration {length/1000:.6f}\n")
                timeline.append(dict(batch_id=source['batch_id'],start_ms=offset,duration_ms=duration,pause_ms=pause))
                offset+=length
                path.unlink()
            (media/'concat.txt').write_text(''.join(concat),encoding='utf-8')
            await self.command(['-y','-f','concat','-safe','1','-i',str(media/'concat.txt'),
                '-map','0:v:0','-map','0:a:0','-vf','fps=30','-af','aresample=async=1:first_pts=0',
                '-c:v','libx264','-preset','fast','-pix_fmt','yuv420p','-c:a','aac','-profile:a','aac_low',
                '-b:a','192k','-ar','48000','-ac','2','-t',f'{offset/1000:.6f}',
                '-movflags','+faststart',str(media/'total.mp4')],phase='合併總 MP4',duration_ms=offset)
            info=await self.command(['-xerror','-err_detect','explode','-i',str(media/'total.mp4'),'-map','0:v:0',
                '-an','-f','null','-'],phase='完整驗證總影片',duration_ms=offset)
            video_ms=round(int(info.get('frame','0'))*1000/30)
            sound=await self.command(['-xerror','-err_detect','explode','-i',str(media/'total.mp4'),'-map','0:a:0',
                '-vn','-af','asetpts=N/SR/TB','-f','null','-'],phase='完整驗證總音軌',duration_ms=offset)
            sound_ms=round(int(sound.get('out_time_us','0'))/1000)
            if video_ms<=0 or abs(video_ms-offset)>200 or abs(sound_ms-offset)>200:
                raise ProjectError('總影片時長差超過 200 毫秒，未發布成品。')
            (media/'total.srt').write_text(''.join(cues),encoding='utf-8')
            if cues: assembly.captions(media/'total.srt',video_ms)
            artifacts={k:dict(path=(media/f'total.{k}').relative_to(self.root).as_posix(),
                sha256=await assembly.file_digest_async(media/f'total.{k}')) for k in ('mp4','srt')}
            for path in list(media.iterdir()):
                if path.name not in ('total.mp4','total.srt'): path.unlink()
            self.progress(phase='等待保存',completed=100,timeline=timeline)
            success=True
            return dict(duration_ms=video_ms,audio_duration_ms=sound_ms,artifacts=artifacts,
                artifact_stats={k:assembly.file_signature(media/f'total.{k}') for k in ('mp4','srt')},texts=texts,source_stats=source_stats)
        finally:
            if not success and media.exists(): shutil.rmtree(media)


def start(flow: ProjectWorkflow) -> MergeVideoJob:
    from .production_lock import ProductionLease
    if flow._total_video_job is not None:
        raise ProjectError('已有製片任務，請先保存或捨棄結果。')
    lease=ProductionLease(flow.root/'.production.lock')
    folder=None
    committed=False
    try:
        flow._check_current()
        value=assembly.settings(flow)
        if not value['sources'] or not 0<=value['pause_ms']<=5000:
            raise ProjectError('請選取有效批次並儲存 0～5 秒交接停頓。')
        sources=[source_ref(flow,s['batch_id']) for s in value['sources']]
        if any(s['audio']!=a for s,a in zip(sources,value['sources'])):
            raise ProjectError('來源版本已變更，請重新儲存合併設定。')
        if any(j['warning'] and not j['accepted'] for j in metadata(flow)):
            raise ProjectError('請先確認 PDF 頁碼警告，再合併影片。')
        total=sum(s['duration_ms'] for s in sources)+(len(sources)-1)*value['pause_ms']
        flow._space(flow.root,total*1000+50_000_000)
        snapshot=dict(id=uuid.uuid4().hex,created_at=now(),method='batch-videos',sources=sources,
            pause_ms=value['pause_ms'],visual=dict(resolution=resolution(flow)))
        folder=flow._path(f'video/run-{snapshot["id"]}')
        folder.mkdir(parents=True)
        flow._atomic(folder/'progress.json',encode(dict(status='pending',phase='準備',completed=0,total=100)))
        data=encode(snapshot);relative=(folder/'plan.json').relative_to(flow.root).as_posix()
        manifest=flow.state
        manifest.setdefault('total_video_runs',[]).append(dict(id=snapshot['id'],path=relative,sha256=digest(data),
            progress_path=(folder/'progress.json').relative_to(flow.root).as_posix()))
        flow._commit(manifest,[(relative,data)])
        committed=True
        job=MergeVideoJob(snapshot,folder,flow.root,ffmpeg(),lease)
        flow._total_video_job=job
        return job
    finally:
        if flow._total_video_job is None:
            lease.release()
            if folder is not None and folder.exists() and not committed: shutil.rmtree(folder)


class VideoJoinPreviewJob(MergeVideoJob):
    def release(self, *, discard=True):
        if not self.wait(0):
            raise ProjectError('請等待影音接點準備停止。')
        try:
            if self.folder.exists(): shutil.rmtree(self.folder)
        except OSError:
            raise ProjectError('影音接點暫存仍被占用，請停止播放後重試。') from None


def start_preview(flow: ProjectWorkflow, batch_ids: list[str], index: int, *, pause_ms=500, clip_ms=5000):
    from .production_lock import production_active
    flow._check_current()
    if flow._assembly_preview_job is not None or production_active(flow.root/'.production.lock'):
        raise ProjectError('請先停止其他任務及接點預覽。')
    if type(index) is not int or not 0<=index<len(batch_ids)-1 or len(set(batch_ids))!=len(batch_ids):
        raise ProjectError('請選取相鄰兩批的接點。')
    if type(pause_ms) is not int or not 0<=pause_ms<=5000 or type(clip_ms) is not int or clip_ms not in (3000,5000,10000):
        raise ProjectError('停頓須為 0～5 秒，前後預覽須為 3、5 或 10 秒。')
    sources=[source_ref(flow,i) for i in batch_ids[index:index+2]]
    flow._space(flow.root,100_000_000)
    folder=Path(tempfile.mkdtemp(prefix='.video-join-',dir=flow.root))
    job=VideoJoinPreviewJob(dict(method='batch-videos',sources=sources,pause_ms=pause_ms,
        clip_ms=clip_ms,visual=dict(resolution='720p')),folder,flow.root,ffmpeg(),None)
    flow._assembly_preview_job=job
    return job


def validate_snapshot(flow: ProjectWorkflow, job: TotalVideoJob) -> None:
    flow._check_current()
    report=job.result
    for source in job.snapshot['sources']:
        if source!=source_ref(flow,source['batch_id']):
            raise ProjectError('批次影片版本已變更，請重新合併或預覽。')
    for path,signature in report['source_stats'].items():
        if signature!=assembly.file_signature(flow._path(path)):
            raise ProjectError('批次影音檔已變更，請重新合併或預覽。')


def finish_preview(flow: ProjectWorkflow, job: VideoJoinPreviewJob) -> dict:
    if job is not flow._assembly_preview_job or not job.wait(0):
        raise ProjectError('請等待所屬影音接點預覽完成。')
    validate_snapshot(flow,job)
    result=job.result
    for kind,ref in result['artifacts'].items():
        if assembly.file_signature(flow._path(ref['path']))!=result['artifact_stats'][kind]:
            raise ProjectError('影音接點檔已變更，請重新預覽。')
    return dict(mp4=result['artifacts']['mp4'],srt=result['artifacts']['srt'],
        duration_ms=result['duration_ms'],left_text=result['texts'][0],right_text=result['texts'][1])


def inspect_joins(flow: ProjectWorkflow, batch_ids: list[str]) -> list[dict]:
    joins=metadata(flow,batch_ids)
    for join in joins:
        for side,tail in (('left',True),('right',False)):
            item=join[side]
            try:
                source=source_ref(flow,item['batch_id'])
                text=flow.reading_text(item['batch_id'],source['audio']['reading_id'])
                item.update(valid=True,text=text[-1000:] if tail else text[:1000],error='')
            except ProjectError as error:
                item.update(valid=False,text='',error=str(error))
    return joins
