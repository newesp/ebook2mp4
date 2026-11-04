"""Local preview assembly and Windows playback, shared with narration output."""
from __future__ import annotations

import asyncio
import ctypes
import os
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import uuid
import wave

from .workflow import ProjectError


def ffmpeg() -> str:
    configured = os.environ.get('EBOOK2MP4_FFMPEG')
    bundled = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / 'tools/ffmpeg/ffmpeg.exe'
    target = configured or (str(bundled) if bundled.is_file() else shutil.which('ffmpeg'))
    if not target or not Path(target).is_file():
        raise ProjectError('缺少 FFmpeg 音訊工具，請重新安裝完整程式；仍可校對。')
    return target


async def media_command(tool: str, arguments: list[str], *, timeout: float = 30):
    process = await asyncio.create_subprocess_exec(
        tool, '-nostdin', '-v', 'error', *arguments, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    try:
        await asyncio.wait_for(process.communicate(), timeout)
        if process.returncode != 0:
            raise ProjectError('音訊無法解碼或組裝，請重試；上一份成功結果保留。')
    finally:
        if process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            await process.communicate()


def block_paths(text: str, settings: dict, cache: Path):
    from .workflow import digest, encode
    identity = dict(text=text, provider=settings['provider'], voice=settings['voice'],
                             rate=settings['rate'], processing=settings['processing'],
                             model=settings.get('model', ''), profile=settings.get('profile', ''), decoding='pcm-s16le-24000-v1')
    if settings['provider']=='kokoro':
        from opencc import OpenCC
        identity.update(package=settings['package'],synthesis_text=OpenCC('t2s').convert(text))
    key = digest(encode(identity))
    return cache / (key + '.wav'), cache / (key + '.json')


def cached_block(text: str, settings: dict, cache: Path) -> Path | None:
    """Validate both checksum and the complete declared PCM payload."""
    from .workflow import digest
    target, manifest = block_paths(text, settings, cache)
    try:
        metadata = json.loads(manifest.read_bytes())
        if digest(target.read_bytes()) == metadata['sha256']:
            with wave.open(str(target), 'rb') as source:
                frames = source.getnframes()
                if ((source.getnchannels(), source.getsampwidth(), source.getframerate()) == (1, 2, 24000)
                        and frames > 0):
                    remaining = frames
                    while remaining:
                        data = source.readframes(min(remaining, 24000))
                        if not data or len(data) % 2:
                            return None
                        remaining -= len(data) // 2
                    return target
    except (OSError, ValueError, KeyError, TypeError, EOFError, wave.Error):
        pass
    return None


async def speech_block(text: str, settings: dict, tool: str, cache: Path, progress=None, *, allow_network=True):
    """Keep verified, immutable PCM speech independent of added pauses."""
    from .tts_backend import capabilities, write_speech
    from .workflow import ProjectWorkflow, digest, encode
    from .tts_services import RetryableServiceError
    from aiohttp import ClientError
    from edge_tts.exceptions import EdgeTTSException
    policy = capabilities(settings['provider'])
    cache.mkdir(parents=True, exist_ok=True)
    target, manifest = block_paths(text, settings, cache)
    valid = cached_block(text, settings, cache)
    if valid is not None:
        return valid, True
    if policy.requires_network and not allow_network:
        raise ProjectError('音訊區塊已缺少或失效。請重新檢查並勾選同意傳送文字後續作。')
    from .voice import require_voice
    require_voice(settings['voice'], settings)
    with tempfile.TemporaryDirectory(prefix='.block-', dir=cache) as directory:
        raw = Path(directory) / ('speech.mp3' if policy.requires_network else 'speech-source.wav')
        decoded = Path(directory) / 'speech.wav'
        for attempt in range(1, policy.max_attempts + 1):
            if progress:
                progress(attempt)
            try:
                if policy.requires_network:
                    await asyncio.wait_for(write_speech(text, settings, raw), policy.synthesis_timeout_seconds)
                else:
                    # Local verification/load and inference have separate bounds.
                    await write_speech(text,settings,raw)
                break
            except (OSError, asyncio.TimeoutError, ClientError, EdgeTTSException, RetryableServiceError) as exc:
                if attempt == policy.max_attempts:
                    raise ProjectError(f'區塊連線或服務錯誤，{policy.max_attempts} 次嘗試後仍失敗。請檢查連線、更新音色後重試。') from None
                await asyncio.sleep(max(attempt, getattr(exc, 'retry_after', 0)))
        await media_command(tool, ['-y', '-i', str(raw), '-ac', '1', '-ar', '24000',
                                   '-c:a', 'pcm_s16le', str(decoded)])
        with wave.open(str(decoded), 'rb') as source:
            if source.getnframes() <= 0:
                raise ProjectError('區塊音訊為空，請重試。')
        data = decoded.read_bytes()
        ProjectWorkflow._atomic(target, data)
        ProjectWorkflow._atomic(manifest, encode(dict(sha256=digest(data))))
    return target, False


async def synthesize(text: str, settings: dict, tool: str, cache: Path) -> bytes:
    from .kokoro_runtime import local_session
    async with local_session(settings):
        return await assemble_preview(text,settings,tool,cache)


async def assemble_preview(text: str, settings: dict, tool: str, cache: Path) -> bytes:
    from .narration import plan
    chunks = plan(text, settings, 'preview', 'preview')['chunks']
    with tempfile.TemporaryDirectory(prefix='ebook2mp4-voice-') as directory:
        folder = Path(directory)
        pcm_file = folder / 'assembled.wav'
        with wave.open(str(pcm_file), 'wb') as assembled:
            assembled.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
            for chunk in chunks:
                decoded, _ = await speech_block(chunk['text'], settings, tool, cache)
                with wave.open(str(decoded), 'rb') as source:
                    while data := source.readframes(24000):
                        assembled.writeframesraw(data)
                assembled.writeframesraw(b'\0\0' * (24 * chunk['pause_after_ms']))
        output = folder / 'preview.mp3'
        await media_command(tool, ['-y', '-i', str(pcm_file), '-c:a', 'libmp3lame', '-b:a', '96k', str(output)])
        await media_command(tool, ['-i', str(output), '-f', 'null', '-'])
        return output.read_bytes()


class PreviewPlayer:
    """Own one MCI alias; release the decoder and file handle when stopped."""
    def __init__(self):
        self.alias: str | None = None

    @staticmethod
    def _send(command: str):
        if os.name != 'nt':
            raise ProjectError('試聽播放目前支援 Windows。')
        api = ctypes.WinDLL('winmm')
        api.mciSendStringW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p]
        api.mciSendStringW.restype = ctypes.c_uint
        buffer = ctypes.create_unicode_buffer(256)
        error = api.mciSendStringW(command, buffer, len(buffer), None)
        if error:
            raise ProjectError('Windows 無法播放試聽音訊，請停止後重試或重新開啟程式。')
        return buffer.value

    def play(self, path: Path):
        self.stop()
        if '"' in str(path):
            raise ProjectError('音訊路徑包含不支援的引號。')
        alias = 'preview' + uuid.uuid4().hex
        self._send(f'open "{path}" type mpegvideo alias {alias}')
        self.alias = alias
        try:
            self._send(f'play {alias}')
        except ProjectError:
            self.stop()
            raise

    def playing(self) -> bool:
        if self.alias is None:
            return False
        if self._send(f'status {self.alias} mode') == 'playing':
            return True
        self.stop()
        return False

    def stop(self):
        if self.alias is not None:
            alias, self.alias = self.alias, None
            self._send(f'close {alias}')
