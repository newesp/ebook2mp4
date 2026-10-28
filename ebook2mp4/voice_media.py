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


async def speech_block(text: str, settings: dict, tool: str, cache: Path, progress=None):
    """Keep verified, immutable PCM speech independent of added pauses."""
    from .voice import edge_module
    from .workflow import ProjectWorkflow, digest, encode
    from aiohttp import ClientError
    from edge_tts.exceptions import EdgeTTSException
    key = digest(encode(dict(text=text, provider=settings['provider'], voice=settings['voice'],
                             rate=settings['rate'], processing=settings['processing'],
                             decoding='pcm-s16le-24000-v1')))
    cache.mkdir(parents=True, exist_ok=True)
    target, manifest = cache / (key + '.wav'), cache / (key + '.json')
    try:
        metadata = json.loads(manifest.read_bytes())
        if digest(target.read_bytes()) == metadata['sha256']:
            with wave.open(str(target), 'rb') as source:
                if (source.getnchannels(), source.getsampwidth(), source.getframerate()) == (1, 2, 24000) and source.getnframes() > 0:
                    return target, True
    except (OSError, ValueError, KeyError, TypeError, EOFError, wave.Error):
        pass  # Missing or damaged blocks are synthesized again; no corrupt reuse.
    with tempfile.TemporaryDirectory(prefix='.block-', dir=cache) as directory:
        raw, decoded = Path(directory) / 'speech.mp3', Path(directory) / 'speech.wav'
        for attempt in range(1, 4):
            if progress:
                progress(attempt)
            try:
                async def receive():
                    size = 0
                    with raw.open('wb') as stream:
                        speaker = edge_module().Communicate(text, settings['voice'], rate=settings['rate'],
                                                            connect_timeout=10, receive_timeout=30)
                        async for packet in speaker.stream():
                            if packet['type'] == 'audio':
                                size += len(packet['data'])
                                if size > 30_000_000:
                                    raise ProjectError('區塊音訊回應過大，請縮短段落後重試。')
                                stream.write(packet['data'])
                        if not size:
                            raise ProjectError('Edge-TTS 未傳回音訊，請更新音色後重試。')
                await asyncio.wait_for(receive(), 90)
                break
            except (OSError, asyncio.TimeoutError, ClientError, EdgeTTSException):
                if attempt == 3:
                    raise ProjectError('區塊連線或服務錯誤，3 次嘗試後仍失敗。請檢查連線、更新音色後重試。') from None
                await asyncio.sleep(attempt)
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
