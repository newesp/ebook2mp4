"""Local preview assembly and Windows playback, shared with narration output."""
from __future__ import annotations

import asyncio
import ctypes
import os
from pathlib import Path
import re
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


async def media_command(tool: str, arguments: list[str]):
    process = await asyncio.create_subprocess_exec(
        tool, '-nostdin', '-v', 'error', *arguments, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    try:
        await asyncio.wait_for(process.communicate(), 30)
        if process.returncode != 0:
            raise ProjectError('試聽音訊無法解碼或組裝，請重試；上一份成功結果保留。')
    finally:
        if process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            await process.communicate()


async def synthesize(text: str, settings: dict, tool: str) -> bytes:
    from .voice import edge_module
    # Keep every character within a paragraph; only blank-line boundaries add silence.
    paragraphs = [p for p in re.split(r'(?:\r?\n)[ \t]*(?:\r?\n)(?:[ \t]*\r?\n)*', text) if p.strip()]
    edge = edge_module()
    with tempfile.TemporaryDirectory(prefix='ebook2mp4-voice-') as directory:
        folder = Path(directory)
        pcm_file = folder / 'assembled.wav'
        with wave.open(str(pcm_file), 'wb') as assembled:
            assembled.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
            for index, paragraph in enumerate(paragraphs):
                raw, decoded = folder / 'chunk.mp3', folder / 'chunk.wav'
                size = 0
                with raw.open('wb') as stream:
                    speaker = edge.Communicate(paragraph, settings['voice'], rate=settings['rate'],
                                               connect_timeout=10, receive_timeout=30)
                    async for chunk in speaker.stream():
                        if chunk['type'] == 'audio':
                            size += len(chunk['data'])
                            if size > 20_000_000:
                                raise ProjectError('試聽回應過大，請縮短選取文字後重試。')
                            stream.write(chunk['data'])
                if size == 0:
                    raise ProjectError('Edge-TTS 未傳回音訊，音色可能已不可用。請更新音色後重試。')
                await media_command(tool, ['-y', '-i', str(raw), '-ac', '1', '-ar', '24000', '-c:a', 'pcm_s16le', str(decoded)])
                with wave.open(str(decoded), 'rb') as source:
                    if source.getnframes() == 0:
                        raise ProjectError('試聽音訊為空，請重試。')
                    assembled.writeframes(source.readframes(source.getnframes()))
                if index < len(paragraphs) - 1:
                    assembled.writeframes(b'\0\0' * (24 * settings['paragraph_pause_ms']))
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
