"""Shared book assembly selections and local, measured total-audio production."""
from __future__ import annotations

from copy import deepcopy
import asyncio
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import uuid
import wave

from .workflow import ProjectError, ProjectWorkflow, digest, encode, now
from .voice import VoiceJob
from .voice_media import ffmpeg, media_command
from .narration import timestamp


def settings(flow: ProjectWorkflow) -> dict:
    value = deepcopy(flow.state.get('assembly_settings', dict(sources=[], pause_ms=500)))
    try:
        if (type(value['pause_ms']) is not int or not 0 <= value['pause_ms'] <= 86_400_000
                or not isinstance(value['sources'], list)):
            raise ValueError()
        ids = [source['batch_id'] for source in value['sources']]
        if len(set(ids)) != len(ids) or any(not isinstance(i, str) for i in ids):
            raise ValueError()
        accepted = value.get('accepted_joins', [])
        if not isinstance(accepted, list) or any(not isinstance(key, str) for key in accepted):
            raise ValueError()
        return value
    except (KeyError, TypeError, ValueError):
        raise ProjectError('全書合併設定損壞，請還原專案備份。') from None


def checked_file(flow: ProjectWorkflow, ref: dict) -> Path:
    path = flow._path(ref['path'])
    try:
        hasher = hashlib.sha256()
        with path.open('rb') as stream:
            while data := stream.read(1024 * 1024):
                hasher.update(data)
        if path.stat().st_size == 0 or hasher.hexdigest() != ref['sha256']:
            raise ProjectError('批次音訊或字幕已損壞，請重新製作該批次。')
        return path
    except OSError:
        raise ProjectError('缺少批次 MP3／SRT，請重新製作該批次。') from None


def source_ref(flow: ProjectWorkflow, batch_id: str, *, verify_media=True) -> dict:
    batch = flow._batch(batch_id)
    product = batch.get('narration')
    if product is None:
        raise ProjectError('缺少 MP3／SRT')
    try:
        if (not batch.get('current_reading') or product['reading_id'] != batch['current_reading']
                or product['settings'] != flow.voice_settings(batch_id)):
            raise ProjectError('待更新：朗讀稿或語音設定已變更')
        if not product['chunks'] or any(c['status'] != 'completed' for c in product['chunks']):
            raise ProjectError('批次音訊未完整完成')
        ref = dict(batch_id=batch_id, product_id=product['id'], reading_id=product['reading_id'],
                   settings_sha256=digest(encode(product['settings'])),
                   mp3=deepcopy(product['mp3']), srt=deepcopy(product['srt']))
        for kind in ('mp3', 'srt'):
            if verify_media:
                checked_file(flow, ref[kind])
            elif not flow._path(ref[kind]['path']).is_file():
                raise ProjectError('缺少 MP3／SRT，請重新製作該批次。')
        return ref
    except (KeyError, TypeError):
        raise ProjectError('批次成品記錄損壞，請重新製作該批次。') from None


async def inspect(flow: ProjectWorkflow) -> list[dict]:
    flow._check_current()
    rows = []
    saved = {s['batch_id']: s for s in settings(flow)['sources']}
    tool = ffmpeg()
    with tempfile.TemporaryDirectory(prefix='.assembly-check-', dir=flow.root) as temp:
        decoded_path = Path(temp)/'source.wav'
        from .assembly_joins import ordered_batches
        for batch in ordered_batches(flow):
            await asyncio.sleep(0)
            row = dict(batch_id=batch['id'], name=batch['name'], valid=False,
                       duration_ms=batch.get('narration', {}).get('duration_ms', 0))
            try:
                ref = source_ref(flow, batch['id'], verify_media=False)
                for kind in ('mp3', 'srt'):
                    await checked_file_async(flow, ref[kind])
                await media_command(tool, ['-y', '-xerror', '-err_detect', 'explode', '-i',
                    str(flow._path(ref['mp3']['path'])), '-ac', '1', '-ar', '24000', '-c:a', 'pcm_s16le', str(decoded_path)], timeout=3600)
                with wave.open(str(decoded_path), 'rb') as decoded:
                    frames = decoded.getnframes()
                    if frames <= 0:
                        raise ProjectError('批次音訊為空，請重新製作。')
                    captions(flow._path(ref['srt']['path']), round(frames/24))
                row.update(source=ref, valid=True, reason='有效 · 音訊與字幕已驗證', duration_ms=round(frames/24),
                           version_changed=batch['id'] in saved and saved[batch['id']] != ref)
            except (OSError, wave.Error):
                row['reason'] = '無法檢查媒體，請檢查來源及磁碟空間。'
            except ProjectError as error:
                row['reason'] = str(error)
            rows.append(row)
    return rows


def save_settings(flow: ProjectWorkflow, batch_ids: list[str], pause_ms: int, accepted_joins: list[str] | None = None) -> None:
    from .production_lock import ProductionLease
    if not batch_ids or len(set(batch_ids)) != len(batch_ids):
        raise ProjectError('請至少選取一個批次，不可重複。')
    if type(pause_ms) is not int or not 0 <= pause_ms <= 5000:
        raise ProjectError('額外交接停頓須為 0～5 秒，精確至毫秒。')
    lease = ProductionLease(flow.root / '.production.lock')
    try:
        flow._check_current()
        value = dict(sources=[source_ref(flow, batch_id, verify_media=False) for batch_id in batch_ids], pause_ms=pause_ms)
        from .assembly_joins import metadata
        if accepted_joins is not None and (not isinstance(accepted_joins, list) or
                any(not isinstance(key, str) for key in accepted_joins)):
            raise ProjectError('接點確認記錄無效，請重新檢查。')
        accepted = settings(flow).get('accepted_joins', []) if accepted_joins is None else accepted_joins
        value['accepted_joins'] = [j['key'] for j in metadata(flow, batch_ids) if j['key'] in accepted]
        manifest = flow.state
        manifest['assembly_settings'] = value
        flow._commit(manifest, [])
    finally:
        lease.release()


def captions(path: Path, duration_ms: int) -> list[tuple[int, int, str]]:
    """Validate SRT against decoded media; permit only the specified 200 ms tail."""
    try:
        text = path.read_text(encoding='utf-8-sig').replace('\r\n', '\n').strip()
        result = []
        previous = 0
        for block in re.split(r'\n[ \t]*\n', text):
            match = re.fullmatch(r'\d+\n(\d{2,}):([0-5]\d):([0-5]\d),(\d{3}) --> '
                                 r'(\d{2,}):([0-5]\d):([0-5]\d),(\d{3})\n(.+)', block, re.S)
            if match is None or not match[9].strip():
                raise ValueError()
            values = [int(match[i]) for i in range(1, 9)]
            start = values[0]*3600000 + values[1]*60000 + values[2]*1000 + values[3]
            end = values[4]*3600000 + values[5]*60000 + values[6]*1000 + values[7]
            if start < previous or start >= end or end > duration_ms+200:
                raise ValueError()
            end = min(end, duration_ms)
            if start >= end:
                raise ValueError()
            result.append((start, end, match[9]))
            previous = end
        if not result:
            raise ValueError()
        return result
    except (OSError, UnicodeError, ValueError):
        raise ProjectError('字幕格式、順序或時間無效，請重新製作該批次 MP3／SRT。') from None


async def copy_verified_source(root: Path, ref: dict, target: Path):
    source = (root/ref['path']).resolve()
    if not source.is_relative_to(root):
        raise ProjectError('來源路徑不安全，請還原可信任專案。')
    hasher = hashlib.sha256()
    with source.open('rb') as stream, target.open('wb') as dest:
        while data := stream.read(1024*1024):
            await asyncio.sleep(0)
            hasher.update(data)
            dest.write(data)
    if hasher.hexdigest() != ref['sha256']:
        raise ProjectError('已選來源在檢查後變更。請重新檢查全書合併設定。')


async def write_silence(output, pause_ms: int) -> int:
    frames = pause_ms*24
    remaining = frames
    while remaining:
        await asyncio.sleep(0)
        take = min(remaining, 24000)
        output.writeframesraw(b'\0\0'*take)
        remaining -= take
    return frames


class TotalAudioJob(VoiceJob):
    def __init__(self, snapshot: dict, folder: Path, root: Path, tool: str, lease):
        self.snapshot, self.folder, self.root = deepcopy(snapshot), folder, root
        self.tool, self.lease, self.published = tool, lease, False
        self.report: dict = dict(status='running', phase='準備', current=0, total=len(snapshot['sources']),
                           completed=0, error='', sources=[dict(batch_id=s['batch_id'], status='pending',
                           attempts=0) for s in snapshot['sources']])
        super().__init__(self.produce, timeout=None)

    def save_progress(self, **changes):
        self.report.update(changes)
        ProjectWorkflow._atomic(self.folder/'progress.json', encode(self.report))
        with self._lock:
            self._state.update({k: deepcopy(v) for k, v in self.report.items() if k not in ('status', 'error')})

    def _run(self):
        super()._run()
        state = self.state
        if state['status'] in ('failed', 'cancelled'):
            for entry in self.report['sources']:
                if entry['status'] == 'running':
                    entry.update(status=state['status'], attempts=self.report.get('attempt', 0))
            self.report['phase'] = '已取消' if state['status'] == 'cancelled' else '失敗'
        if state['error'].startswith('TTS '):
            with self._lock:
                self._state['error'] = '全書合併失敗。請檢查媒體、磁碟空間與檔案占用；舊成品保留。'
        try:
            self.save_progress(status=self.state['status'], error=self.state['error'])
        except OSError:
            with self._lock:
                self._state.update(status='failed', error='無法保存合併進度，請檢查磁碟空間與權限。')
                self._result = None

    async def command(self, args: list[str]):
        for attempt in range(1, 4):
            self.save_progress(attempt=attempt)
            try:
                await media_command(self.tool, args, timeout=3600)
                return
            except ProjectError:
                if attempt == 3:
                    raise ProjectError('媒體處理 3 次嘗試後仍失敗。請檢查來源及磁碟，再重試合併。') from None
                await asyncio.sleep(attempt/2)

    async def produce(self):
        media = self.folder/'media'
        success = False
        try:
            media.mkdir()
            frames = 0
            cues: list[str] = []
            with wave.open(str(media/'assembled.wav'), 'wb') as assembled:
                assembled.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
                for index, source in enumerate(self.snapshot['sources']):
                    self.save_progress(phase='驗證批次音訊與字幕', current=index+1)
                    entry = self.report['sources'][index]
                    entry.update(status='running')
                    for kind in ('mp3', 'srt'):
                        await copy_verified_source(self.root, source[kind], media/('source.'+kind))
                    await self.command(['-y', '-xerror', '-err_detect', 'explode', '-i', str(media/'source.mp3'),
                                        '-ac', '1', '-ar', '24000', '-c:a', 'pcm_s16le', str(media/'source.wav')])
                    with wave.open(str(media/'source.wav'), 'rb') as decoded:
                        count = decoded.getnframes()
                        if count <= 0:
                            raise ProjectError('已選批次音訊為空，請重新製作該批次。')
                        source_cues = captions(media/'source.srt', round(count/24))
                        ProjectWorkflow._space(self.root, count*2 + 1024*1024)
                        start = round(frames/24)
                        for begin, end, text in source_cues:
                            begin_ms = round((frames+min(begin*24, count))/24)
                            end_ms = round((frames+min(end*24, count))/24)
                            cues.append(f'{len(cues)+1}\n{timestamp(begin_ms)} --> {timestamp(end_ms)}\n{text}\n\n')
                        while data := decoded.readframes(24000):
                            await asyncio.sleep(0)
                            assembled.writeframesraw(data)
                    entry.update(status='completed', frames=count, start_ms=start,
                                 duration_ms=round(count/24), attempts=self.report.get('attempt', 1))
                    frames += count
                    if index < len(self.snapshot['sources'])-1:
                        frames += await write_silence(assembled, self.snapshot['pause_ms'])
                    self.save_progress(completed=index+1)
            self.save_progress(phase='組裝總 MP3／SRT')
            output = media/'total.mp3'
            await self.command(['-y', '-i', str(media/'assembled.wav'), '-c:a', 'libmp3lame', '-b:a', '96k', str(output)])
            ProjectWorkflow._atomic(media/'total.srt', ''.join(cues).encode('utf-8'))
            self.save_progress(phase='完整驗證總成品')
            await self.command(['-y', '-xerror', '-i', str(output), '-ac', '1', '-ar', '24000',
                                '-c:a', 'pcm_s16le', str(media/'verified.wav')])
            with wave.open(str(media/'verified.wav'), 'rb') as decoded:
                actual = decoded.getnframes()
                # MP3 gapless metadata can round a few decoded samples at the tail.
                # Measure the delivered media, and reject any discrepancy over 1 ms.
                if abs(actual-frames) > 24:
                    raise ProjectError('總音訊的解碼時間與拼接時間不一致，未發布成品。')
                remaining = actual
                while data := decoded.readframes(24000):
                    await asyncio.sleep(0)
                    remaining -= len(data)//2
                if remaining:
                    raise ProjectError('總音訊解碼資料不完整，未發布成品。')
            captions(media/'total.srt', round(actual/24))
            for name in ('assembled.wav', 'verified.wav', 'source.wav', 'source.mp3', 'source.srt'):
                (media/name).unlink(missing_ok=True)
            self.save_progress(status='completed', phase='等待保存', duration_ms=round(actual/24), frames=actual,
                               planned_frames=frames, artifacts={kind: dict(
                                   path=(media/('total.'+kind)).relative_to(self.root).as_posix(),
                                   sha256=await file_digest_async(media/('total.'+kind))) for kind in ('mp3', 'srt')})
            self.report['artifact_stats'] = {kind: file_signature(media/('total.'+kind)) for kind in ('mp3', 'srt')}
            success = True
            return deepcopy(self.report)
        except asyncio.CancelledError:
            self.report.update(status='cancelled', phase='已取消')
            raise
        except OSError:
            raise ProjectError('合併讀寫失敗。請檢查磁碟空間、來源檔與寫入權限；舊成品保留。') from None
        finally:
            if not success:
                if media.exists():
                    shutil.rmtree(media)

    def release(self, *, discard: bool):
        if not self.wait(0):
            raise ProjectError('請等待合併任務停止後再釋放。')
        try:
            if discard and not self.published and (self.folder/'media').exists():
                shutil.rmtree(self.folder/'media')
            if self.lease is not None:
                self.lease.release()
                self.lease = None
        except OSError:
            raise ProjectError('無法釋放合併暫存或任務鎖。請解除占用後重試，已發布成品保留。') from None


def start(flow: ProjectWorkflow) -> TotalAudioJob:
    from .production_lock import ProductionLease
    if flow._total_audio_job is not None:
        raise ProjectError('已有全書合併任務，請先保存或捨棄結果。')
    tool = ffmpeg()
    lease = ProductionLease(flow.root/'.production.lock')
    folder = None
    committed = False
    try:
        flow._check_current()
        value = settings(flow)
        if not 0 <= value['pause_ms'] <= 5000:
            raise ProjectError('請將舊交接停頓調整為 0～5 秒，再儲存合併設定。')
        if not value['sources']:
            raise ProjectError('請至少選取一個有效批次，並儲存合併設定。')
        for source in value['sources']:
            if source != source_ref(flow, source['batch_id'], verify_media=False):
                raise ProjectError('已選來源版本變更，請重新檢查並儲存合併設定。')
        from .assembly_joins import metadata
        if any(j['warning'] and not j['accepted'] for j in metadata(flow)):
            raise ProjectError('請先檢查交接接點的 PDF 頁碼警告，並明確確認保留內容。')
        total_ms = sum(flow._batch(s['batch_id'])['narration']['duration_ms'] for s in value['sources'])
        total_ms += (len(value['sources'])-1)*value['pause_ms']
        # WAV/RF64 support is explicit: reject instead of producing an invalid RIFF.
        if total_ms*48 > 4_000_000_000:
            raise ProjectError('總音訊超過目前 WAV 組裝上限（約 23 小時）。請減少批次或交接停頓。')
        flow._space(flow.root, total_ms*48*3+25_000_000)
        snapshot = dict(id=uuid.uuid4().hex, created_at=now(), **value)
        folder = flow._path(f'assembly/run-{snapshot["id"]}')
        folder.mkdir(parents=True)
        flow._atomic(folder/'progress.json', encode(dict(status='pending', sources=[])))
        data = encode(snapshot)
        relative = (folder/'plan.json').relative_to(flow.root).as_posix()
        ref = dict(id=snapshot['id'], path=relative, sha256=digest(data),
                   progress_path=(folder/'progress.json').relative_to(flow.root).as_posix())
        manifest = flow.state
        manifest.setdefault('total_audio_runs', []).append(ref)
        flow._commit(manifest, [(relative, data)])
        committed = True
        job = TotalAudioJob(snapshot, folder, flow.root, tool, lease)
        flow._total_audio_job = job
        return job
    except OSError:
        raise ProjectError('無法準備全書合併。請檢查磁碟空間與權限。') from None
    finally:
        if flow._total_audio_job is None:
            lease.release()
            if folder is not None and folder.exists() and not committed:
                shutil.rmtree(folder)


def finish(flow: ProjectWorkflow, job: TotalAudioJob) -> dict:
    if job is not flow._total_audio_job or not job.wait(0):
        raise ProjectError('請等待所屬全書合併任務停止。')
    report = job.result
    if not job.published:
        product = dict(deepcopy(job.snapshot), duration_ms=report['duration_ms'], frames=report['frames'],
                       planned_frames=report['planned_frames'], timeline=report['sources'], completed_at=now())
        for kind in ('mp3', 'srt'):
            path = flow._path(report['artifacts'][kind]['path'])
            if file_signature(path) != report['artifact_stats'][kind]:
                raise ProjectError('已驗證的總成品在發布前變更。舊成品保留，請重新合併。')
            product[kind] = deepcopy(report['artifacts'][kind])
        manifest = flow.state
        manifest['total_audio'] = product
        next(r for r in manifest['total_audio_runs'] if r['id'] == product['id'])['published'] = True
        flow._commit(manifest, [])
        job.published = True
    job.release(discard=False)
    flow._total_audio_job = None
    result = total_audio(flow, verify_media=False)
    assert result is not None
    return result


async def file_digest_async(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        while data := stream.read(1024*1024):
            await asyncio.sleep(0)
            hasher.update(data)
    return hasher.hexdigest()


def file_signature(path: Path) -> tuple[int, int, int]:
    try:
        stat = path.stat()
        return stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns
    except OSError:
        raise ProjectError('已驗證的總成品遺失。舊成品保留，請重新合併。') from None


async def checked_file_async(flow: ProjectWorkflow, ref: dict) -> Path:
    path = flow._path(ref['path'])
    try:
        if path.stat().st_size == 0 or await file_digest_async(path) != ref['sha256']:
            raise ProjectError('音訊或字幕已損壞，請重新製作對應成品。')
        return path
    except OSError:
        raise ProjectError('找不到音訊或字幕，請重新製作對應成品。') from None


def total_audio(flow: ProjectWorkflow, *, verify_media=True) -> dict | None:
    product = deepcopy(flow.state.get('total_audio'))
    if product is None:
        return None
    try:
        for kind in ('mp3', 'srt'):
            if verify_media:
                checked_file(flow, product[kind])
            elif not flow._path(product[kind]['path']).is_file():
                raise ProjectError('找不到總成品，請重新合併。')
        value = settings(flow)
        stale = (value['sources'] != product['sources'] or value['pause_ms'] != product['pause_ms'])
        for source in product['sources']:
            try:
                stale = stale or source != source_ref(flow, source['batch_id'], verify_media=verify_media)
            except ProjectError:
                stale = True
        product['stale'] = stale
        return product
    except (KeyError, TypeError, ValueError):
        raise ProjectError('總成品記錄損壞，請還原備份或重新合併。') from None


async def inspect_total_audio(flow: ProjectWorkflow) -> dict | None:
    product = total_audio(flow, verify_media=False)
    if product is not None:
        for kind in ('mp3', 'srt'):
            await checked_file_async(flow, product[kind])
        for source in product['sources']:
            for kind in ('mp3', 'srt'):
                try:
                    await checked_file_async(flow, source[kind])
                except ProjectError:
                    product['stale'] = True
    return product


async def export(flow: ProjectWorkflow, folder: str | Path) -> None:
    product = total_audio(flow, verify_media=False)
    if product is None:
        raise ProjectError('尚無成功總成品。')
    target = Path(folder).resolve()
    if target.exists():
        raise ProjectError('另存資料夾已存在，請選擇新的資料夾名稱。')
    temporary = None
    try:
        flow._space(target.parent, sum(flow._path(product[k]['path']).stat().st_size for k in ('mp3', 'srt')))
        temporary = Path(tempfile.mkdtemp(prefix='.total-export-', dir=target.parent))
        for kind in ('mp3', 'srt'):
            ref = product[kind]
            hasher = hashlib.sha256()
            with flow._path(ref['path']).open('rb') as source, (temporary/('total.'+kind)).open('wb') as dest:
                while data := source.read(1024*1024):
                    await asyncio.sleep(0)
                    hasher.update(data)
                    dest.write(data)
            if hasher.hexdigest() != ref['sha256']:
                raise ProjectError('總成品已損壞，無法另存。請重新合併。')
        temporary.rename(target)
        temporary = None
    except OSError:
        raise ProjectError('無法另存總成品。請檢查資料夾權限與磁碟空間。') from None
    finally:
        if temporary is not None:
            shutil.rmtree(temporary)


def runs(flow: ProjectWorkflow) -> list[dict]:
    from .production_lock import production_active
    result = []
    try:
        for ref in flow.state.get('total_audio_runs', []):
            snapshot = json.loads(flow._read(ref))
            progress = json.loads(flow._path(ref['progress_path']).read_bytes())
            if progress['status'] in ('pending', 'running', 'cancelling') and not production_active(flow.root/'.production.lock'):
                progress['status'] = 'interrupted'
            result.append(dict(snapshot=snapshot, progress=progress, published=ref.get('published', False)))
        return result
    except (OSError, KeyError, ValueError, TypeError):
        raise ProjectError('全書合併進度無法讀取，請還原專案備份。') from None
