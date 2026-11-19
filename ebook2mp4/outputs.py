"""Book output planning and resumable, format-local delivery on one production lease.

The caller polls/waits on its owning thread. Media stays in existing cancellable
workers; manifest publication and the Windows mutex stay on the caller thread.
"""
from __future__ import annotations

from copy import deepcopy
import time
import uuid

from . import assembly, total_video, video_merge
from .production_lock import ProductionLease, production_active
from .voice import VoiceJob
from .workflow import ProjectError, digest, encode, now


def selection(flow) -> list[str]:
    value = flow.state.get('output_formats', ['mp4'] if flow.state.get('total_video_method') == 'batch-videos' else ['mp3'])
    if (not isinstance(value, list) or not value or any(k not in ('mp3', 'mp4') for k in value)
            or len(set(value)) != len(value)):
        raise ProjectError('請選擇總 MP3、總 MP4 或兩者。')
    return list(value)


def save_selection(flow, formats: list[str]) -> None:
    # Validate before acquiring or writing any state.
    if (not isinstance(formats, list) or not formats or any(k not in ('mp3', 'mp4') for k in formats)
            or len(set(formats)) != len(formats)):
        raise ProjectError('請至少選擇一種輸出格式，不可重複。')
    lease = ProductionLease(flow.root/'.production.lock')
    try:
        flow._check_current()
        state = flow.state
        state['output_formats'] = [k for k in ('mp3', 'mp4') if k in formats]
        flow._commit(state, [])
    finally:
        lease.release()


def save_plan(flow, batch_ids: list[str], pause_ms: int, *, accepted_joins=None, resolution='1080p') -> None:
    """Save intent even with missing inputs so each format can list its blockers."""
    if (not isinstance(batch_ids, list) or not batch_ids or any(not isinstance(i, str) for i in batch_ids)
            or len(set(batch_ids)) != len(batch_ids) or type(pause_ms) is not int
            or not 0 <= pause_ms <= 5000 or resolution not in ('720p', '1080p')):
        raise ProjectError('請選批次，並設定 0～5 秒停頓及有效解析度。')
    if accepted_joins is not None and (not isinstance(accepted_joins, list)
            or any(not isinstance(k, str) for k in accepted_joins)):
        raise ProjectError('接點確認記錄無效。')
    lease = ProductionLease(flow.root/'.production.lock')
    try:
        flow._check_current()
        refs = []
        for identity in batch_ids:
            flow._batch(identity)
            try:
                refs.append(video_merge.audio_identity(flow, identity))
            except ProjectError:
                refs.append(dict(batch_id=identity))
        from .assembly_joins import metadata
        accepted = assembly.settings(flow).get('accepted_joins', []) if accepted_joins is None else accepted_joins
        value = dict(sources=refs, pause_ms=pause_ms,
                     accepted_joins=[j['key'] for j in metadata(flow, batch_ids) if j['key'] in accepted])
        state = flow.state
        state['assembly_settings'] = value
        state['video_merge_resolution'] = resolution
        flow._commit(state, [])
    finally:
        lease.release()


def fingerprint(flow) -> str:
    shared = assembly.settings(flow)
    state = flow.state
    batches = []
    for source in shared['sources']:
        batch = flow._batch(source['batch_id'])
        batches.append(dict(id=batch['id'], reading=batch.get('current_reading'),
            voice=flow.voice_settings(batch['id']), narration=batch.get('narration'), video=batch.get('video')))
    return digest(encode(dict(shared=shared, formats=selection(flow),
        method=state.get('total_video_method', 'total-audio'), visual=total_video.settings(flow),
        resolution=video_merge.resolution(flow), batches=batches)))


def overall(formats: list[str], rows: dict) -> str:
    states = [rows[k]['status'] for k in formats]
    if all(s == 'completed' for s in states):
        return 'completed'
    if any(s == 'completed' for s in states):
        return 'partial'
    if any(s == 'failed' for s in states):
        return 'failed'
    if any(s == 'cancelled' for s in states):
        return 'cancelled'
    return 'incomplete'


async def inspect(flow) -> dict:
    """Hash-check products and route inputs without decoding or producing media."""
    flow._check_current()
    formats = selection(flow)
    method = flow.state.get('total_video_method', 'total-audio')
    if method not in ('total-audio', 'batch-videos'):
        raise ProjectError('影片方式無效。')
    value = assembly.settings(flow)
    rows: dict[str, dict] = {k: dict(status='ready', reason='', product=None, missing=[]) for k in ('mp3', 'mp4')}
    for kind, get_product in (('mp3', lambda: assembly.total_audio(flow, verify_media=False)),
                              ('mp4', lambda: total_video.total_video(flow, verify_media=False, method=method))):
        row = rows[kind]
        try:
            product = get_product()
            if product:
                for key in (kind, 'srt'):
                    await assembly.checked_file_async(flow, product[key])
                # A product is reusable only while its immutable inputs still match.
                for source in product.get('sources', []):
                    for key in (('mp3', 'srt') if kind == 'mp3' else ('mp4', 'srt')):
                        await assembly.checked_file_async(flow, source[key])
                if kind == 'mp4' and method == 'total-audio':
                    for key in ('mp3', 'srt'):
                        await assembly.checked_file_async(flow, product['audio'][key])
                row.update(product=product, status='stale' if product['stale'] else 'completed',
                           reason='來源已變更，需更新；上一版保留。' if product['stale'] else '有效成品與同版 SRT 已保存。')
        except (ProjectError, KeyError, TypeError) as error:
            row.update(status='stale', reason='成品無法驗證，需更新：'+str(error))
    audio_missing, video_missing = [], []
    if not value['sources']:
        audio_missing.append('請選取至少一個批次並儲存合併設定。')
        video_missing.append('請選取至少一個批次並儲存合併設定。')
    for saved in value['sources']:
        identity = saved['batch_id']
        name = flow._batch(identity)['name']
        for movie, missing in ((False, audio_missing), (True, video_missing)):
            if movie and method != 'batch-videos':
                continue
            try:
                ref = video_merge.source_ref(flow, identity) if movie else assembly.source_ref(flow, identity, verify_media=False)
                if (ref['audio'] if movie else ref) != saved:
                    raise ProjectError('來源版本已變更，請重新儲存合併設定。')
                for key in (('mp4', 'srt') if movie else ('mp3', 'srt')):
                    await assembly.checked_file_async(flow, ref[key])
            except ProjectError as error:
                missing.append(name+'：'+str(error))
    from .assembly_joins import metadata
    if any(j['warning'] and not j['accepted'] for j in metadata(flow)):
        audio_missing.append('請檢查並確認 PDF 接點頁碼警告。')
        video_missing.append('請檢查並確認 PDF 接點頁碼警告。')
    if method == 'total-audio':
        visual = total_video.settings(flow)
        asset = visual['background'] if visual['source_type'] == 'video' else visual['image']
        if not asset:
            video_missing.append('請加入並儲存全片圖片或背景 MP4。')
        else:
            try:
                await assembly.checked_file_async(flow, asset)
            except ProjectError as error:
                video_missing.append('全片素材：'+str(error))
        if rows['mp3']['status'] != 'completed':
            video_missing.extend('前置總音訊：'+m for m in audio_missing)
    for k, missing in (('mp3', audio_missing), ('mp4', video_missing)):
        rows[k]['missing'] = missing
        if rows[k]['status'] != 'completed' and missing:
            rows[k].update(status='missing', reason='\n'.join(missing))
    record = flow.state.get('output_run', {})
    if record.get('fingerprint') == fingerprint(flow) and record.get('method') == method:
        for k, old in record.get('formats', {}).items():
            if k in rows and rows[k]['status'] in ('ready', 'stale') and old['status'] in ('failed', 'cancelled'):
                rows[k].update(status=old['status'], reason=old.get('reason', ''))
            elif (k in rows and rows[k]['status'] in ('ready', 'stale') and old['status'] == 'running'
                  and not production_active(flow.root/'.production.lock')):
                rows[k].update(status='cancelled', reason='上次任務已中斷，可只重試未完成輸出。')
    return dict(formats=formats, method=method, rows=rows, status=overall(formats, rows),
                needs_audio='mp4' in formats and method == 'total-audio' and rows['mp3']['status'] != 'completed')


class _BorrowedLease:
    def release(self) -> None:
        # The coordinator keeps the real lease across stage boundaries.
        pass


class OutputJob:
    def __init__(self, flow):
        self.flow = flow
        self.lease = ProductionLease(flow.root/'.production.lock')
        self.child = None
        self.current = None
        self.cancelled = False
        self.closed = False
        self.publish_pending = False
        self.queue: list[str] = []
        try:
            flow._check_current()
            self.identity = fingerprint(flow)
            self.formats = selection(flow)
            self.method = flow.state.get('total_video_method', 'total-audio')
            self.report = dict(id=uuid.uuid4().hex, fingerprint=self.identity, method=self.method,
                requested=self.formats, started_at=now(), status='running', phase='檢查各格式來源',
                completed=0, total=len(self.formats), error='', formats={})
            self._persist()
            self.child = VoiceJob(lambda: inspect(flow), timeout=None)
        except Exception:
            self.lease.release()
            raise

    def _persist(self) -> None:
        state = self.flow.state
        state['output_run'] = deepcopy(self.report)
        self.flow._commit(state, [])

    def _finish(self) -> None:
        rows = self.report['formats']
        # A reused result can become stale while another format is running.
        # Recheck metadata before declaring the whole request complete.
        for k, row in rows.items():
            if row['status'] != 'completed':
                continue
            try:
                product = (assembly.total_audio(self.flow, verify_media=False) if k == 'mp3' else
                           total_video.total_video(self.flow, verify_media=False, method=self.method))
                if not product or product['stale']:
                    row.update(status='stale', reason='來源或設定已變更，成品保留但需更新。')
            except ProjectError as error:
                row.update(status='stale', reason=str(error))
        self.report.update(status=overall(self.formats, rows), phase='已停止', completed=sum(
            rows.get(k, {}).get('status') == 'completed' for k in self.formats), finished_at=now())
        self._persist()
        self.lease.release()
        self.closed = True

    def _discard(self) -> None:
        if self.current == 'mp3':
            self.flow.discard_total_audio(self.child)
        elif self.current == 'mp4':
            self.flow.discard_total_video(self.child)
        self.child = None

    def _advance(self) -> None:
        if self.closed or self.publish_pending:
            return
        try:
            if self.child is not None:
                if not self.child.wait(0):
                    return
                state = self.child.state
                if self.current is None:
                    if state['status'] != 'completed':
                        raise ProjectError(state.get('error') or '已取消來源檢查。')
                    plan = self.child.result
                    self.report['formats'] = plan['rows']
                    # Product snapshots belong to their existing route records.
                    for row in self.report['formats'].values():
                        row.pop('product', None)
                    self.child = None
                    if ('mp3' in self.formats or plan['needs_audio']) and plan['rows']['mp3']['status'] not in ('completed', 'missing'):
                        self.queue.append('mp3')
                    if 'mp4' in self.formats and plan['rows']['mp4']['status'] not in ('completed', 'missing'):
                        self.queue.append('mp4')
                else:
                    k = self.current
                    row = self.report['formats'][k]
                    try:
                        if state['status'] == 'completed':
                            product = (self.flow.finish_total_audio(self.child) if k == 'mp3'
                                       else self.flow.finish_total_video(self.child))
                            row.update(status='stale' if product['stale'] else 'completed',
                                reason='來源在製作中變更，成品保留但需更新。' if product['stale'] else '成品及同版 SRT 已保存。')
                            self.child = None
                        else:
                            row.update(status='cancelled' if self.cancelled or state['status'] == 'cancelled' else 'failed',
                                       reason=state.get('error') or '已取消；成功成品保留。')
                            self._discard()
                    except (ProjectError, OSError) as error:
                        # A completed worker whose publication fails remains available
                        # for explicit retry; do not silently discard verified media.
                        row.update(status='failed', reason='保存失敗：'+str(error))
                        self.publish_pending = True
                        self.report.update(phase='重試保存或取消', error=str(error))
                        self._persist()
                        return
                    self.current = None
                    self.report['completed'] = sum(self.report['formats'][key]['status'] == 'completed'
                                                   for key in self.formats)
                    self._persist()
            if self.cancelled:
                for k in self.queue:
                    self.report['formats'][k].update(status='cancelled', reason='尚未執行，任務已取消。')
                self.queue.clear()
            if not self.queue:
                self._finish()
                return
            if fingerprint(self.flow) != self.identity:
                for k in self.queue:
                    self.report['formats'][k].update(status='stale', reason='來源或設定已變更，請重新檢查後續作。')
                self.queue.clear()
                self._finish()
                return
            k = self.queue.pop(0)
            if k == 'mp4' and self.method == 'total-audio' and self.report['formats']['mp3']['status'] != 'completed':
                self.report['formats'][k].update(status='missing', reason='前置總音訊未完成，請先重試總音訊。')
                self._finish()
                return
            self.current = k
            try:
                begin = assembly.start if k == 'mp3' else total_video.start if self.method == 'total-audio' else video_merge.start
                self.child = begin(self.flow, _lease=_BorrowedLease())
                self.report['formats'][k].update(status='running', reason='處理中')
                self.report['phase'] = '製作總 MP3／SRT' if k == 'mp3' else '製作總 MP4／SRT'
            except (ProjectError, OSError) as error:
                self.report['formats'][k].update(status='failed', reason=str(error))
                self.report['error'] = str(error)
                self.current = None
            self._persist()
        except (ProjectError, OSError) as error:
            if self.child is not None and not self.child.wait(0):
                self.child.cancel()
                return
            if self.current is not None and self.child is not None:
                self._discard()
            if not self.report['formats']:
                self.report['formats'] = {k: dict(status='cancelled' if self.cancelled else 'failed', reason=str(error))
                                          for k in ('mp3', 'mp4')}
            self.report.update(status='cancelled' if self.cancelled else 'failed', error=str(error), phase='已停止')
            try:
                self._persist()
            finally:
                self.lease.release()
                self.closed = True

    @property
    def state(self) -> dict:
        self._advance()
        result = deepcopy(self.report)
        if self.child is not None and self.current is not None:
            child = self.child.state
            result['phase'] = child.get('phase', result['phase'])
        return result

    def wait(self, timeout: float | None = None) -> bool:
        end = None if timeout is None else time.monotonic()+timeout
        while True:
            self._advance()
            if self.closed:
                return True
            if end is not None and time.monotonic() >= end:
                return False
            time.sleep(.02)

    def cancel(self) -> None:
        if self.closed:
            return
        self.cancelled = True
        self.publish_pending = False
        if self.child is not None:
            if self.current and self.child.wait(0) and self.child.state['status'] == 'completed':
                self._discard()
                self.report['formats'][self.current].update(status='cancelled', reason='已取消未保存結果。')
                self.current = None
            else:
                self.child.cancel()

    def retry_save(self) -> None:
        if not self.publish_pending:
            raise ProjectError('目前沒有待重試的保存結果。')
        self.publish_pending = False
        self._advance()

    @property
    def result(self) -> dict:
        if not self.wait(0):
            raise ProjectError('請等待輸出任務停止。')
        return deepcopy(self.report)


def start(flow) -> OutputJob:
    if getattr(flow, '_output_job', None) is not None:
        raise ProjectError('請先保存或結束上一個逐格式任務。')
    if flow._total_audio_job is not None or flow._total_video_job is not None:
        raise ProjectError('請先保存或捨棄目前成品任務。')
    job = OutputJob(flow)
    flow._output_job = job
    return job


def finish(flow, job: OutputJob) -> dict:
    if job is not getattr(flow, '_output_job', None) or not job.wait(0):
        raise ProjectError('請等待所屬逐格式任務停止。')
    result = job.result
    flow._output_job = None
    return result
