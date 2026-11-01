"""Book-wide still-image video, independent of speech synthesis and batch video."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import asyncio
import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
import wave
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from .workflow import ProjectError, ProjectWorkflow, digest, encode, now
from .voice import VoiceJob
from .voice_media import ffmpeg, media_command
from .assembly import (captions, checked_file, checked_file_async, copy_verified_source,
                       file_digest_async, file_signature, inspect_total_audio, total_audio)


@dataclass(frozen=True)
class VideoImage:
    name: str
    data: bytes
    sha256: str
    width: int
    height: int
    format: str


def inspect_image(path: str | Path) -> VideoImage:
    path = Path(path)
    try:
        if path.suffix.lower() not in ('.jpg', '.jpeg', '.png') or path.stat().st_size > 25_000_000:
            raise ProjectError('請選擇 25 MB 以下的 JPEG 或 PNG 圖片。')
        data = path.read_bytes()
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if image.format not in ('JPEG', 'PNG') or image.width*image.height > 40_000_000:
                    raise ProjectError('圖片須為 JPEG／PNG，且不超過四千萬像素。')
                image.load()
                oriented = ImageOps.exif_transpose(image)
                return VideoImage(path.name, data, digest(data), oriented.width, oriented.height, image.format)
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ProjectError('圖片無法解碼。請另選可讀取的 JPEG 或 PNG；原設定保留。') from None


def settings(flow: ProjectWorkflow) -> dict:
    value = deepcopy(flow.state.get('total_video_settings', dict(image=None, resolution='1080p')))
    try:
        if value['resolution'] not in ('1080p', '720p'):
            raise ValueError()
        image = value['image']
        if image is not None:
            flow._path(image['path'])
            if not all(image[k] for k in ('name', 'sha256', 'width', 'height', 'format')):
                raise ValueError()
        return value
    except (KeyError, TypeError, ValueError):
        raise ProjectError('總影片設定損壞，請重新選圖及儲存設定。') from None


def save_settings(flow: ProjectWorkflow, image: VideoImage | None, resolution: str) -> None:
    from .production_lock import ProductionLease
    if resolution not in ('1080p', '720p'):
        raise ProjectError('影片解析度只支援 1080p 或 720p。')
    lease = ProductionLease(flow.root/'.production.lock')
    try:
        flow._check_current()
        value = settings(flow)
        files = []
        if image is not None:
            # Reinspect caller-supplied bytes before accepting a saved asset.
            if not isinstance(image, VideoImage) or digest(image.data) != image.sha256:
                raise ProjectError('圖片預覽已失效，請重新選擇圖片。')
            path = f'visual/image-{image.sha256}.{image.format.lower()}'
            value['image'] = dict(name=image.name, path=path, sha256=image.sha256,
                                  width=image.width, height=image.height, format=image.format)
            files.append((path, image.data))
        value['resolution'] = resolution
        manifest = flow.state
        manifest['total_video_settings'] = value
        flow._commit(manifest, files)
    finally:
        lease.release()


def current_audio(flow: ProjectWorkflow, *, verify_media=False) -> dict:
    product = total_audio(flow, verify_media=verify_media)
    if product is None or product['stale']:
        raise ProjectError('總音訊缺少或已失效。請先更新總 MP3／SRT，再製作影片。')
    return {k: deepcopy(product[k]) for k in ('id', 'mp3', 'srt', 'duration_ms')}


def total_video(flow: ProjectWorkflow, *, verify_media=True) -> dict | None:
    product = deepcopy(flow.state.get('total_video'))
    if product is None:
        return None
    try:
        for kind in ('mp4', 'srt'):
            if verify_media:
                checked_file(flow, product[kind])
            elif not flow._path(product[kind]['path']).is_file():
                raise ProjectError('總影片檔案遺失，請重新製作；總音訊保留。')
        product['stale'] = product['visual'] != settings(flow)
        try:
            product['stale'] |= product['audio'] != current_audio(flow, verify_media=verify_media)
        except ProjectError:
            product['stale'] = True
        return product
    except (KeyError, TypeError, ValueError):
        raise ProjectError('總影片成品記錄損壞，請重新製作。') from None


async def inspect_video(flow: ProjectWorkflow) -> dict:
    warning = ''
    try:
        audio = await inspect_total_audio(flow)
        if audio is None or audio['stale']:
            warning = '總音訊缺少或已失效。請先更新總 MP3／SRT。'
    except ProjectError as error:
        audio = None
        warning = str(error)
    try:
        product = total_video(flow, verify_media=False)
        if product:
            for kind in ('mp4', 'srt'):
                await checked_file_async(flow, product[kind])
            if audio is None or audio['stale']:
                product['stale'] = True
    except ProjectError as error:
        product = None
        warning += f' 舊總影片無法驗證：{error}'
    visual = settings(flow)
    preview = None
    if visual['image']:
        try:
            path = await checked_file_async(flow, visual['image'])
            preview = thumbnail(path.read_bytes())
        except ProjectError as error:
            warning += f' 圖片無法驗證：{error}'
    try:
        history = runs(flow)
    except ProjectError as error:
        history = []
        warning += ' '+str(error)
    return dict(audio=audio, product=product, visual=visual, preview=preview, warning=warning, runs=history)


def flattened(data: bytes) -> Image.Image:
    with Image.open(BytesIO(data)) as source:
        image = ImageOps.exif_transpose(source).convert('RGBA')
        black = Image.new('RGBA', image.size, 'black')
        black.alpha_composite(image)
        return black.convert('RGB')


def thumbnail(data: bytes) -> bytes:
    try:
        image = flattened(data)
        image.thumbnail((960, 540))
        output = BytesIO()
        image.save(output, format='PNG')
        return output.getvalue()
    except (OSError, ValueError, Image.DecompressionBombError):
        raise ProjectError('圖片無法解碼，請重新選圖。') from None


class TotalVideoJob(VoiceJob):
    def __init__(self, snapshot: dict, folder: Path, root: Path, tool: str, lease):
        self.snapshot, self.folder, self.root = deepcopy(snapshot), folder, root
        self.tool, self.lease, self.published = tool, lease, False
        self.report: dict = dict(status='running', phase='準備影片', completed=0, total=100, error='')
        super().__init__(self.produce, timeout=None)

    def progress(self, **changes):
        self.report.update(changes)
        ProjectWorkflow._atomic(self.folder/'progress.json', encode(self.report))
        with self._lock:
            self._state.update({k: v for k, v in self.report.items() if k not in ('status', 'error')})

    def _run(self):
        super()._run()
        if self.state['error'].startswith('TTS '):
            with self._lock:
                self._state['error'] = '影片處理失敗。請檢查圖片、媒體工具及磁碟空間；舊成品保留。'
        try:
            self.progress(status=self.state['status'], error=self.state['error'])
        except OSError:
            with self._lock:
                self._state.update(status='failed', error='無法保存影片進度，請檢查磁碟空間。')
                self._result = None

    async def command(self, args: list[str], *, phase: str, duration_ms: int) -> dict:
        self.progress(phase=phase)
        process = await asyncio.create_subprocess_exec(self.tool, '-nostdin', '-v', 'error', '-progress', 'pipe:1',
            '-nostats', *args, stdout=asyncio.subprocess.PIPE, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        values: dict[str, str] = {}
        last = 0.0
        try:
            assert process.stdout is not None
            async with asyncio.timeout(86400):
                while line := await process.stdout.readline():
                    key, _, value = line.decode('ascii', errors='replace').strip().partition('=')
                    values[key] = value
                    if key == 'progress' and time.monotonic()-last > .5:
                        elapsed = max(0, int(values.get('out_time_us', '0'))//1000)
                        self.progress(completed=min(99, round(elapsed/max(1, duration_ms)*100)))
                        last = time.monotonic()
                await process.wait()
            if process.returncode:
                raise ProjectError('影片無法編碼或完整解碼。請檢查素材與磁碟，再重試；舊成品保留。')
            return values
        finally:
            if process.returncode is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                await process.communicate()

    async def produce(self):
        media = self.folder/'media'
        success = False
        try:
            media.mkdir()
            audio = self.snapshot['audio']
            checked = await inspect_total_audio(ProjectWorkflow.open(self.root))
            if checked is None or checked['stale'] or any(checked[k] != audio[k] for k in audio):
                raise ProjectError('總音訊缺少或已失效。請先更新總 MP3／SRT。')
            for kind in ('mp3', 'srt'):
                await copy_verified_source(self.root, audio[kind], media/('source.'+kind))
            await copy_verified_source(self.root, self.snapshot['visual']['image'], media/'image.source')
            flattened((media/'image.source').read_bytes()).save(media/'image.png')
            self.progress(phase='驗證總音訊與字幕')
            await media_command(self.tool, ['-y', '-xerror', '-err_detect', 'explode', '-i', str(media/'source.mp3'),
                '-ac', '1', '-ar', '24000', '-c:a', 'pcm_s16le', str(media/'source.wav')], timeout=86400)
            with wave.open(str(media/'source.wav'), 'rb') as wav:
                duration = round(wav.getnframes()/24)
            if duration <= 0 or abs(duration-audio['duration_ms']) > 1:
                raise ProjectError('總音訊實際長度與版本記錄不一致，請更新總音訊。')
            captions(media/'source.srt', duration)
            width, height = (1920, 1080) if self.snapshot['visual']['resolution'] == '1080p' else (1280, 720)
            await self.command(['-y', '-loop', '1', '-framerate', '30', '-i', str(media/'image.png'),
                '-i', str(media/'source.mp3'), '-map', '0:v:0', '-map', '1:a:0', '-vf',
                f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,setsar=1',
                '-c:v', 'libx264', '-preset', 'fast', '-tune', 'stillimage', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-profile:a', 'aac_low', '-b:a', '192k', '-ar', '48000', '-ac', '2',
                '-t', f'{duration/1000:.3f}', '-movflags', '+faststart', str(media/'total.mp4')],
                phase='製作總 MP4', duration_ms=duration)
            info = await self.command(['-xerror', '-err_detect', 'explode', '-i', str(media/'total.mp4'),
                '-map', '0:v:0', '-an', '-f', 'null', '-'], phase='完整驗證影片', duration_ms=duration)
            video_ms = round(int(info.get('frame', '0'))*1000/30)
            sound = await self.command(['-xerror', '-err_detect', 'explode', '-i', str(media/'total.mp4'),
                '-map', '0:a:0', '-vn', '-af', 'asetpts=N/SR/TB', '-f', 'null', '-'],
                phase='完整驗證音訊', duration_ms=duration)
            audio_ms = round(int(sound.get('out_time_us', '0'))/1000)
            if video_ms <= 0 or abs(video_ms-duration) > 200 or abs(audio_ms-duration) > 200:
                raise ProjectError('總影片與總音訊的時長差超過 200 毫秒，未發布成品。')
            shutil.copyfile(media/'source.srt', media/'total.srt')
            captions(media/'total.srt', video_ms)
            artifacts = {k: dict(path=(media/('total.'+k)).relative_to(self.root).as_posix(),
                                sha256=await file_digest_async(media/('total.'+k))) for k in ('mp4', 'srt')}
            for name in ('image.source', 'image.png', 'source.mp3', 'source.srt', 'source.wav', 'verified.wav'):
                (media/name).unlink(missing_ok=True)
            self.progress(phase='等待保存', completed=100)
            success = True
            return dict(duration_ms=video_ms, audio_duration_ms=audio_ms, artifacts=artifacts,
                        artifact_stats={k: file_signature(media/('total.'+k)) for k in ('mp4', 'srt')})
        except OSError:
            raise ProjectError('製片讀寫失敗。請檢查圖片、磁碟空間及權限；舊成品保留。') from None
        finally:
            if not success and media.exists():
                shutil.rmtree(media)

    def release(self, *, discard: bool):
        if not self.wait(0):
            raise ProjectError('請等待製片任務停止後再釋放。')
        try:
            if discard and not self.published and (self.folder/'media').exists():
                shutil.rmtree(self.folder/'media')
            if self.lease is not None:
                self.lease.release()
                self.lease = None
        except OSError:
            raise ProjectError('無法釋放製片暫存或任務鎖，請解除占用後重試。') from None


def start(flow: ProjectWorkflow) -> TotalVideoJob:
    from .production_lock import ProductionLease
    if flow._total_video_job is not None:
        raise ProjectError('已有製片任務，請先保存或捨棄結果。')
    tool = ffmpeg()
    lease = ProductionLease(flow.root/'.production.lock')
    folder = None
    committed = False
    try:
        flow._check_current()
        visual = settings(flow)
        if not visual['image']:
            raise ProjectError('請先選擇並儲存全片共用圖片。')
        audio = current_audio(flow)
        flow._space(flow.root, audio['duration_ms']*600 + 50_000_000)
        snapshot = dict(id=uuid.uuid4().hex, created_at=now(), audio=audio, visual=visual)
        folder = flow._path(f'video/run-{snapshot["id"]}')
        folder.mkdir(parents=True)
        flow._atomic(folder/'progress.json', encode(dict(status='pending', phase='準備', completed=0, total=100)))
        data = encode(snapshot)
        path = (folder/'plan.json').relative_to(flow.root).as_posix()
        manifest = flow.state
        manifest.setdefault('total_video_runs', []).append(dict(id=snapshot['id'], path=path, sha256=digest(data),
                                         progress_path=(folder/'progress.json').relative_to(flow.root).as_posix()))
        flow._commit(manifest, [(path, data)])
        committed = True
        job = TotalVideoJob(snapshot, folder, flow.root, tool, lease)
        flow._total_video_job = job
        return job
    except OSError:
        raise ProjectError('無法準備製片。請檢查磁碟空間與權限。') from None
    finally:
        if flow._total_video_job is None:
            lease.release()
            if folder is not None and folder.exists() and not committed:
                shutil.rmtree(folder)


def finish(flow: ProjectWorkflow, job: TotalVideoJob) -> dict:
    if job is not flow._total_video_job or not job.wait(0):
        raise ProjectError('請等待所屬製片任務停止。')
    report = job.result
    if not job.published:
        product = dict(deepcopy(job.snapshot), duration_ms=report['duration_ms'], completed_at=now())
        for kind in ('mp4', 'srt'):
            ref = report['artifacts'][kind]
            if file_signature(flow._path(ref['path'])) != report['artifact_stats'][kind]:
                raise ProjectError('已驗證的影片在發布前變更，請重新製作。舊成品保留。')
            product[kind] = deepcopy(ref)
        manifest = flow.state
        manifest['total_video'] = product
        next(r for r in manifest['total_video_runs'] if r['id'] == product['id'])['published'] = True
        flow._commit(manifest, [])
        job.published = True
    job.release(discard=False)
    flow._total_video_job = None
    result = total_video(flow, verify_media=False)
    assert result is not None
    return result


def runs(flow: ProjectWorkflow) -> list[dict]:
    from .production_lock import production_active
    try:
        result = []
        for ref in flow.state.get('total_video_runs', []):
            progress = json.loads(flow._path(ref['progress_path']).read_bytes())
            if progress['status'] in ('pending', 'running', 'cancelling') and not production_active(flow.root/'.production.lock'):
                progress['status'] = 'interrupted'
            result.append(dict(snapshot=json.loads(flow._read(ref)), progress=progress, published=ref.get('published', False)))
        return result
    except (OSError, KeyError, TypeError, ValueError):
        raise ProjectError('製片進度無法讀取。請還原專案備份。') from None


async def export(flow: ProjectWorkflow, folder: str | Path) -> None:
    product = total_video(flow, verify_media=False)
    if product is None:
        raise ProjectError('尚無成功總影片。')
    target = Path(folder).resolve()
    if target.exists():
        raise ProjectError('另存資料夾已存在，請選擇新的資料夾名稱。')
    temporary = None
    try:
        flow._space(target.parent, sum(flow._path(product[k]['path']).stat().st_size for k in ('mp4', 'srt')))
        temporary = Path(tempfile.mkdtemp(prefix='.video-export-', dir=target.parent))
        for kind in ('mp4', 'srt'):
            await copy_verified_source(flow.root, product[kind], temporary/('total.'+kind))
        temporary.rename(target)
        temporary = None
    except OSError:
        raise ProjectError('無法另存總影片。請檢查磁碟空間與權限。') from None
    finally:
        if temporary is not None:
            shutil.rmtree(temporary)


async def prepare_playback(flow: ProjectWorkflow, product: dict, folder: Path) -> dict:
    """Decode the delivered still-image MP4, including an old product's own frame."""
    tool = ffmpeg()
    flow._space(flow.root, product['duration_ms']*48 + flow._path(product['mp4']['path']).stat().st_size + 10_000_000)
    source = folder/'source.mp4'
    await copy_verified_source(flow.root, product['mp4'], source)
    await media_command(tool, ['-y', '-xerror', '-i', str(source), '-frames:v', '1', '-vf',
                              'scale=960:540', str(folder/'frame.png')], timeout=86400)
    await media_command(tool, ['-y', '-xerror', '-i', str(source), '-vn', '-ac', '1', '-ar', '24000',
                              '-c:a', 'pcm_s16le', str(folder/'audio.wav')], timeout=86400)
    source.unlink()
    return dict(audio=folder/'audio.wav', frame=(folder/'frame.png').read_bytes())
