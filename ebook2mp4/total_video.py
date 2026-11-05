"""Book-wide image/background video, independent of speech synthesis and batch video."""
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
import sys

from PIL import Image, ImageOps, UnidentifiedImageError

from .workflow import ProjectError, ProjectWorkflow, digest, encode, now
from .voice import VoiceJob
from .video_target import BatchVideoTarget
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


@dataclass(frozen=True)
class VideoBackground:
    path: Path
    name: str
    sha256: str
    width: int
    height: int
    duration_ms: int
    size: int
    signature: tuple


def probe_tool() -> str:
    bundled = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))/'tools/ffmpeg/ffprobe.exe'
    target = os.environ.get('EBOOK2MP4_FFPROBE') or (str(bundled) if bundled.is_file() else shutil.which('ffprobe'))
    if not target or not Path(target).is_file():
        raise ProjectError('缺少 FFprobe 影片檢查工具，請重新安裝完整程式。')
    return target


async def probe_background(path: Path) -> dict:
    process = await asyncio.create_subprocess_exec(probe_tool(), '-v', 'error', '-protocol_whitelist', 'file,pipe',
        '-show_streams', '-show_format', '-of', 'json', str(path), stdout=asyncio.subprocess.PIPE,
        stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    try:
        output, _ = await asyncio.wait_for(process.communicate(), 60)
        info = json.loads(output)
        stream = next(s for s in info['streams'] if s['codec_type'] == 'video' and not s.get('disposition', {}).get('attached_pic'))
        duration = round(float(stream.get('duration', info['format']['duration']))*1000)
        if (process.returncode or 'mp4' not in info['format']['format_name'].split(',') or duration <= 0
                or not 0 < int(stream['width'])*int(stream['height']) <= 40_000_000):
            raise ValueError()
        return dict(width=int(stream['width']), height=int(stream['height']), duration_ms=duration)
    except (ValueError, KeyError, TypeError, StopIteration, asyncio.TimeoutError):
        raise ProjectError('背景須為含有效視訊串流的 MP4，且不超過四千萬像素。請另選素材。') from None
    finally:
        if process.returncode is None:
            process.kill()
            await process.communicate()


async def inspect_background(path: str | Path, *, project_root: Path | None = None) -> VideoBackground:
    path = Path(path).resolve()
    try:
        if path.suffix.lower() != '.mp4':
            raise ProjectError('背景影片請選 MP4。')
        signature = file_signature(path)
        sha = await file_digest_async(path)
        info = await probe_background(path)
        await media_command(ffmpeg(), ['-xerror', '-err_detect', 'explode', '-protocol_whitelist', 'file,pipe',
            '-i', str(path), '-map', '0:v:0', '-an', '-f', 'null', '-'], timeout=86400)
        if signature != file_signature(path):
            raise ProjectError('背景在檢查期間變更，請重新選擇。')
        background = VideoBackground(path, path.name, sha, **info, size=path.stat().st_size, signature=signature)
        if project_root is not None:
            return await stage_background(project_root, background)
        return background
    except OSError:
        raise ProjectError('背景無法讀取或保存。請檢查檔案、空間與權限；原設定保留。') from None


async def stage_background(root: Path, background: VideoBackground) -> VideoBackground:
    """Stream a validated asset into an immutable project-local file, without loading it into RAM."""
    target = root/'visual'/f'background-{background.sha256}.mp4'
    target.parent.mkdir(exist_ok=True)
    ProjectWorkflow._space(root, background.size+10_000_000)
    fd, name = tempfile.mkstemp(prefix='.background-', suffix='.mp4', dir=target.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        await copy_verified_source(background.path.parent, dict(path=background.path.name, sha256=background.sha256), temporary)
        temporary.replace(target)
        return VideoBackground(target, background.name, background.sha256, background.width, background.height,
                               background.duration_ms, background.size, file_signature(target))
    finally:
        temporary.unlink(missing_ok=True)


async def background_frame(path: Path, seconds: float = 0, *, last=False) -> bytes:
    with tempfile.TemporaryDirectory(prefix='.background-frame-', dir=path.parent) as folder:
        frame = Path(folder)/'frame.png'
        await media_command(ffmpeg(), ['-y', '-ss', f'{max(0, seconds-1 if last else seconds):.6f}', '-protocol_whitelist', 'file,pipe',
            '-i', str(path), '-map', '0:v:0', '-an', *(['-update', '1'] if last else ['-frames:v', '1']), '-vf',
            'scale=960:540:force_original_aspect_ratio=decrease,pad=960:540:(ow-iw)/2:(oh-ih)/2:black,setsar=1',
            str(frame)], timeout=60)
        try:
            return frame.read_bytes()
        except OSError:
            raise ProjectError('背景畫面無法預覽。請重新選擇素材。') from None


async def stream_frames(path: Path, duration_ms: int, mode: str, emit) -> None:
    # Demuxer looping follows container duration, including excluded audio tails.
    # Loop a video-only remux so original sound cannot create visual gaps.
    with tempfile.TemporaryDirectory(prefix='.background-stream-', dir=path.parent) as directory:
        if mode == 'loop':
            silent = Path(directory)/'visual.mp4'
            await visual_only(path, silent)
            path = silent
        await _stream_frames(path, duration_ms, mode, emit)


async def visual_only(source: Path, target: Path) -> None:
    await media_command(ffmpeg(), ['-y', '-xerror', '-protocol_whitelist', 'file,pipe', '-i', str(source),
        '-map', '0:v:0', '-an', '-c:v', 'copy', str(target)], timeout=86400)


async def _stream_frames(path: Path, duration_ms: int, mode: str, emit) -> None:
    """Bounded frame stream, paced by its consumer clock; no background sound is decoded."""
    inputs = (['-stream_loop', '-1'] if mode == 'loop' else []) + ['-protocol_whitelist', 'file,pipe', '-i', str(path)]
    filters = 'setpts=PTS-STARTPTS,scale=960:540:force_original_aspect_ratio=decrease,pad=960:540:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps=10'
    if mode == 'hold':
        filters += f',tpad=stop_mode=clone:stop_duration={duration_ms/1000:.3f}'
    process = await asyncio.create_subprocess_exec(ffmpeg(), '-nostdin', '-v', 'error', *inputs,
        '-map', '0:v:0', '-an', '-vf', filters, '-t', f'{duration_ms/1000:.3f}', '-pix_fmt', 'rgb24',
        '-f', 'rawvideo', 'pipe:1', stdout=asyncio.subprocess.PIPE, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    try:
        assert process.stdout is not None
        start = None
        index = 0
        while True:
            try:
                frame = await process.stdout.readexactly(960*540*3)
            except asyncio.IncompleteReadError as error:
                if error.partial:
                    raise ProjectError('預覽畫面解碼不完整，請重新檢查素材。') from None
                break
            if start is None:
                start = time.monotonic()
            await asyncio.sleep(max(0, start+index/10-time.monotonic()))
            emit(frame, index*100)
            index += 1
        await process.wait()
        if process.returncode or not index:
            raise ProjectError('影片畫面無法播放，請重新檢查素材。')
    finally:
        if process.returncode is None:
            process.kill()
            await process.communicate()


def normalized_visual(value: dict) -> dict:
    value = deepcopy(value)
    value.setdefault('source_type', 'image')
    value.setdefault('background', None)
    value.setdefault('background_mode', 'loop')
    return value


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


def settings(flow: ProjectWorkflow | BatchVideoTarget) -> dict:
    value = normalized_visual(flow.state.get('total_video_settings', dict(image=None, resolution='1080p')))
    try:
        if value['resolution'] not in ('1080p', '720p'):
            raise ValueError()
        if value['source_type'] not in ('image', 'video') or value['background_mode'] not in ('loop', 'hold'):
            raise ValueError()
        if value['background'] is not None:
            background = value['background']
            flow._path(background['path'])
            if not all(background[k] for k in ('name', 'sha256', 'width', 'height', 'duration_ms', 'size')):
                raise ValueError()
        image = value['image']
        if image is not None:
            flow._path(image['path'])
            if not all(image[k] for k in ('name', 'sha256', 'width', 'height', 'format')):
                raise ValueError()
        return value
    except (KeyError, TypeError, ValueError):
        raise ProjectError('總影片設定損壞，請重新選擇素材及儲存設定。') from None


def save_settings(flow: ProjectWorkflow | BatchVideoTarget, image: VideoImage | None, resolution: str, *,
                  background: VideoBackground | None = None, source_type: str | None = None,
                  background_mode: str | None = None) -> None:
    from .production_lock import ProductionLease
    if resolution not in ('1080p', '720p'):
        raise ProjectError('影片解析度只支援 1080p 或 720p。')
    lease = ProductionLease(flow.root/'.production.lock')
    try:
        flow._check_current()
        value = settings(flow)
        if source_type is not None:
            value['source_type'] = source_type
        if background_mode is not None:
            value['background_mode'] = background_mode
        if value['source_type'] not in ('image', 'video') or value['background_mode'] not in ('loop', 'hold'):
            raise ProjectError('素材類型或背景模式無效。')
        files = []
        if background is not None:
            if not isinstance(background, VideoBackground) or file_signature(background.path) != background.signature:
                raise ProjectError('背景預覽已失效，請重新選擇。')
            target = flow.root/'visual'/f'background-{background.sha256}.mp4'
            if background.path != target:
                background = asyncio.run(stage_background(flow.root, background))
            value['background'] = dict(name=background.name, path=target.relative_to(flow.root).as_posix(),
                sha256=background.sha256, width=background.width, height=background.height,
                duration_ms=background.duration_ms, size=background.size)
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
    except OSError:
        raise ProjectError('素材無法保存。請檢查檔案、磁碟空間與權限；原設定保留。') from None
    finally:
        lease.release()


def current_audio(flow: ProjectWorkflow | BatchVideoTarget, *, verify_media=False) -> dict:
    product = flow.audio(verify_media=verify_media) if isinstance(flow, BatchVideoTarget) else total_audio(flow, verify_media=verify_media)
    if product is None or product.get('stale', False):
        raise ProjectError('總音訊缺少或已失效。請先更新總 MP3／SRT，再製作影片。')
    return {k: deepcopy(product[k]) for k in ('id', 'mp3', 'srt', 'duration_ms')}


def total_video(flow: ProjectWorkflow | BatchVideoTarget, *, verify_media=True) -> dict | None:
    product = deepcopy(flow.state.get('total_video'))
    if product is None:
        return None
    try:
        for kind in ('mp4', 'srt'):
            if verify_media:
                checked_file(flow.project if isinstance(flow, BatchVideoTarget) else flow, product[kind])
            elif not flow._path(product[kind]['path']).is_file():
                raise ProjectError('總影片檔案遺失，請重新製作；總音訊保留。')
        if product.get('method') == 'batch-videos' and isinstance(flow, ProjectWorkflow):
            from .video_merge import stale
            product['stale'] = stale(flow, product, verify_media=verify_media)
            return product
        product['stale'] = normalized_visual(product['visual']) != settings(flow)
        try:
            product['stale'] |= product['audio'] != current_audio(flow, verify_media=verify_media)
        except ProjectError:
            product['stale'] = True
        return product
    except (KeyError, TypeError, ValueError):
        raise ProjectError('總影片成品記錄損壞，請重新製作。') from None


async def inspect_video(flow: ProjectWorkflow | BatchVideoTarget) -> dict:
    warning = ''
    try:
        audio = await flow.inspect_audio() if isinstance(flow, BatchVideoTarget) else await inspect_total_audio(flow)
        if audio is None or audio['stale']:
            warning = '總音訊缺少或已失效。請先更新總 MP3／SRT。'
    except ProjectError as error:
        audio = None
        warning = str(error)
    try:
        product = total_video(flow, verify_media=False)
        if product:
            for kind in ('mp4', 'srt'):
                await checked_file_async(flow.project if isinstance(flow, BatchVideoTarget) else flow, product[kind])
            if audio is None or audio['stale']:
                product['stale'] = True
    except ProjectError as error:
        product = None
        warning += f' 舊總影片無法驗證：{error}'
    visual = settings(flow)
    preview = None
    asset = visual['background'] if visual['source_type'] == 'video' else visual['image']
    if asset:
        try:
            path = await checked_file_async(flow.project if isinstance(flow, BatchVideoTarget) else flow, asset)
            preview = await background_frame(path) if visual['source_type'] == 'video' else thumbnail(path.read_bytes())
        except ProjectError as error:
            warning += f' 素材無法驗證：{error}'
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
        super().__init__(self.diagnosed_produce, timeout=None)

    def progress(self, **changes):
        self.report.update(changes)
        ProjectWorkflow._atomic(self.folder/'progress.json', encode(self.report))
        with self._lock:
            self._state.update({k: v for k, v in self.report.items() if k not in ('status', 'error')})

    def _run(self):
        super()._run()
        if self.state['error'].startswith('TTS '):
            with self._lock:
                self._state['error'] = '影片處理失敗。請檢查素材、媒體工具及磁碟空間；舊成品保留。'
        try:
            self.progress(status=self.state['status'], error=self.state['error'])
        except OSError:
            with self._lock:
                self._state.update(status='failed', error='無法保存影片進度。請確認專案磁碟有空間且資料夾可寫入 → 重試製片。舊成品保留。')
                self._result = None

    def failure(self, detail, *, category=None):
        """Keep evidence locally; show a specific, actionable message in the existing status area."""
        from .video_diagnostics import diagnose
        info = diagnose(detail, category=category)
        self.progress(diagnostic=dict(info, phase=self.report.get('phase', '準備影片')))
        return ProjectError(info['message']+' 舊成品保留。')

    async def diagnosed_produce(self):
        try:
            return await self.produce()
        except asyncio.CancelledError:
            raise
        except ProjectError as error:
            if 'diagnostic' not in self.report:
                self.progress(diagnostic=dict(category='validation', message=str(error),
                    detail=str(error), phase=self.report.get('phase', '準備影片')))
            raise
        except asyncio.TimeoutError:
            raise self.failure('媒體處理超過時間限制', category='timeout') from None
        except Exception as error:
            raise self.failure(type(error).__name__+': '+str(error), category='internal') from None

    async def command(self, args: list[str], *, phase: str, duration_ms: int) -> dict:
        self.progress(phase=phase)
        # A separate file prevents stderr pipe deadlock. Only its bounded tail is retained.
        with tempfile.TemporaryFile() as errors:
            process = None
            try:
                process = await asyncio.create_subprocess_exec(self.tool, '-nostdin', '-v', 'error', '-progress', 'pipe:1',
                    '-nostats', *args, stdout=asyncio.subprocess.PIPE, stderr=errors,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                values: dict[str, str] = {}
                last = 0.0
                assert process.stdout is not None
                async with asyncio.timeout(86400):
                    while line := await process.stdout.readline():
                        key, _, value = line.decode('ascii', errors='replace').strip().partition('=')
                        values[key] = value
                        if key == 'progress' and time.monotonic()-last > .5:
                            from .video_diagnostics import progress_time
                            elapsed = progress_time(values.get('out_time_us'))
                            if elapsed is not None:
                                self.progress(completed=min(99, round(elapsed/max(1, duration_ms)*100)))
                            last = time.monotonic()
                    await process.wait()
                if process.returncode:
                    errors.seek(0, 2)
                    errors.seek(max(0, errors.tell()-16384))
                    detail = errors.read().decode('utf-8', errors='replace')
                    raise self.failure(detail or f'FFmpeg 結束碼 {process.returncode}')
                return values
            except OSError as error:
                raise self.failure(str(error)) from None
            finally:
                if process is not None and process.returncode is None:
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
            reopened = ProjectWorkflow.open(self.root)
            if self.snapshot.get('batch_id'):
                from .video_target import BatchVideoTarget
                checked = await BatchVideoTarget(reopened, self.snapshot['batch_id']).inspect_audio()
            else:
                checked = await inspect_total_audio(reopened)
            if checked is None or checked['stale'] or any(checked[k] != audio[k] for k in audio):
                raise ProjectError('總音訊缺少或已失效。請先更新總 MP3／SRT。')
            for kind in ('mp3', 'srt'):
                await copy_verified_source(self.root, audio[kind], media/('source.'+kind))
            visual = self.snapshot['visual']
            is_background = visual['source_type'] == 'video'
            if is_background:
                await copy_verified_source(self.root, visual['background'], media/'background.mp4')
                await probe_background(media/'background.mp4')
            else:
                await copy_verified_source(self.root, visual['image'], media/'image.source')
                flattened((media/'image.source').read_bytes()).save(media/'image.png')
            self.progress(phase='驗證總音訊與字幕')
            await self.command(['-y', '-xerror', '-err_detect', 'explode', '-i', str(media/'source.mp3'),
                '-ac', '1', '-ar', '24000', '-c:a', 'pcm_s16le', str(media/'source.wav')], phase='驗證音訊與字幕', duration_ms=audio['duration_ms'])
            with wave.open(str(media/'source.wav'), 'rb') as wav:
                duration = round(wav.getnframes()/24)
            if duration <= 0 or abs(duration-audio['duration_ms']) > 1:
                raise ProjectError('總音訊實際長度與版本記錄不一致，請更新總音訊。')
            captions(media/'source.srt', duration)
            width, height = (1920, 1080) if self.snapshot['visual']['resolution'] == '1080p' else (1280, 720)
            inputs = ['-loop', '1', '-framerate', '30', '-i', str(media/'image.png')]
            extra_filter = ''
            if is_background:
                # Never loop the narration input. All background audio streams are excluded by explicit maps.
                loop = visual['background_mode'] == 'loop' and visual['background']['duration_ms'] < duration
                path = media/'background.mp4'
                if loop:
                    await self.command(['-y', '-xerror', '-protocol_whitelist', 'file,pipe', '-i', str(path),
                        '-map', '0:v:0', '-an', '-c:v', 'copy', str(media/'background.visual.mp4')],
                        phase='準備無聲背景', duration_ms=visual['background']['duration_ms'])
                    path = media/'background.visual.mp4'
                inputs = (['-stream_loop', '-1'] if loop else []) + ['-i', str(path)]
                if visual['background_mode'] == 'hold':
                    extra_filter = f',tpad=stop_mode=clone:stop_duration={duration/1000:.3f}'
            await self.command(['-y', *inputs,
                '-i', str(media/'source.mp3'), '-map', '0:v:0', '-map', '1:a:0', '-vf',
                f'setpts=PTS-STARTPTS,scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps=30{extra_filter}',
                '-c:v', 'libx264', '-preset', 'fast', '-pix_fmt', 'yuv420p',
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
            for name in ('background.mp4', 'background.visual.mp4', 'image.source', 'image.png', 'source.mp3', 'source.srt', 'source.wav', 'verified.wav'):
                (media/name).unlink(missing_ok=True)
            self.progress(phase='等待保存', completed=100)
            success = True
            return dict(duration_ms=video_ms, audio_duration_ms=audio_ms, artifacts=artifacts,
                        artifact_stats={k: file_signature(media/('total.'+k)) for k in ('mp4', 'srt')})
        except OSError as error:
            raise self.failure(str(error)) from None
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


def start(flow: ProjectWorkflow | BatchVideoTarget) -> TotalVideoJob:
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
        asset = visual['background'] if visual['source_type'] == 'video' else visual['image']
        if not asset:
            raise ProjectError('請先選擇並儲存全片共用素材。')
        audio = current_audio(flow)
        flow._space(flow.root, audio['duration_ms']*600 + asset.get('size', 0)*2 + 50_000_000)
        snapshot = dict(id=uuid.uuid4().hex, created_at=now(), audio=audio, visual=visual)
        if isinstance(flow, BatchVideoTarget):
            snapshot['batch_id'] = flow.batch_id
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


def finish(flow: ProjectWorkflow | BatchVideoTarget, job: TotalVideoJob) -> dict:
    if (job is not flow._total_video_job or not job.wait(0)
            or job.snapshot.get('batch_id') != getattr(flow, 'batch_id', None)):
        raise ProjectError('請等待所屬製片任務停止。')
    report = job.result
    if not job.published:
        if job.snapshot.get('method') == 'batch-videos' and isinstance(flow, ProjectWorkflow):
            from .video_merge import validate_snapshot
            validate_snapshot(flow, job)
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


def runs(flow: ProjectWorkflow | BatchVideoTarget) -> list[dict]:
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


async def export(flow: ProjectWorkflow | BatchVideoTarget, folder: str | Path) -> None:
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


async def prepare_playback(flow: ProjectWorkflow | BatchVideoTarget, product: dict, folder: Path) -> dict:
    """Prepare the delivered MP4's actual frame, audio and moving-picture source."""
    tool = ffmpeg()
    flow._space(flow.root, product['duration_ms']*48 + flow._path(product['mp4']['path']).stat().st_size + 10_000_000)
    source = folder/'source.mp4'
    await copy_verified_source(flow.root, product['mp4'], source)
    await media_command(tool, ['-y', '-xerror', '-i', str(source), '-frames:v', '1', '-vf',
                              'scale=960:540', str(folder/'frame.png')], timeout=86400)
    await media_command(tool, ['-y', '-xerror', '-i', str(source), '-vn', '-ac', '1', '-ar', '24000',
                              '-c:a', 'pcm_s16le', str(folder/'audio.wav')], timeout=86400)
    return dict(audio=folder/'audio.wav', video=source, duration_ms=product['duration_ms'],
                frame=(folder/'frame.png').read_bytes())
