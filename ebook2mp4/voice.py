"""Edge service adapter, cancellable work, and shared narration settings."""
from __future__ import annotations

import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import threading
from typing import Any

from .workflow import ProjectError, now

RATES = ('-20%', '-10%', '+0%', '+10%', '+20%')
EXAMPLE = '今天，讓我們一起聽一本好書。Hello, welcome to your audiobook. 這是語音試聽範例。'
DEFAULT_SETTINGS = dict(provider='edge-tts', voice='', rate='+0%',
                        processing='identity-v1', sentence_pause_ms=0, paragraph_pause_ms=500)


def settings(value: dict) -> dict:
    if (not isinstance(value, dict) or set(value) != set(DEFAULT_SETTINGS)
            or value['provider'] != 'edge-tts' or not isinstance(value['voice'], str)
            or value['rate'] not in RATES or value['processing'] != 'identity-v1'
            or type(value['sentence_pause_ms']) is not int or value['sentence_pause_ms'] != 0
            or type(value['paragraph_pause_ms']) is not int or value['paragraph_pause_ms'] != 500):
        raise ProjectError('語音設定無效，請重新選擇音色與語速。')
    return deepcopy(value)


def cache_path() -> Path:
    return Path(os.environ.get('EBOOK2MP4_VOICE_HOME') or
                str(Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'ebook2mp4/voice')) / 'voices.json'


def catalog() -> dict:
    path = cache_path()
    if not path.exists():
        return dict(voices=[], updated_at=None)
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(value['updated_at'], str) or not value['voices']:
            raise ValueError()
        ids = set()
        for voice in value['voices']:
            if not all(isinstance(voice[k], str) and voice[k] for k in ('id', 'name', 'locale', 'gender')):
                raise ValueError()
            if voice['id'] in ids:
                raise ValueError()
            ids.add(voice['id'])
        return value
    except (OSError, ValueError, KeyError, TypeError):
        raise ProjectError('音色快取無法讀取，請按「更新線上音色」重新取得。') from None


def require_voice(voice: str):
    if not voice or not any(v['id'] == voice for v in catalog()['voices']):
        raise ProjectError('音色未選擇或已不可用，請更新線上音色後明確重新選擇；不會自動換聲。')


def edge_module():
    try:
        import edge_tts
        return edge_tts
    except ImportError:
        raise ProjectError('缺少 Edge-TTS 語音依賴，請重新安裝完整程式；仍可離線校對。') from None


class VoiceJob:
    """A bounded async operation with prompt cancellation and joined resources."""
    def __init__(self, operation, *, timeout: float | None = 90):
        self._lock = threading.Lock()
        self._cancel = threading.Event()
        self._state = dict(status='running', error='')
        self._result: Any = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._task: asyncio.Task | None = None
        self._operation = operation
        self._timeout = timeout
        self._thread = threading.Thread(target=self._run, name='ebook2mp4-voice')
        self._thread.start()

    @property
    def state(self) -> dict:
        with self._lock:
            return deepcopy(self._state)

    @property
    def result(self):
        with self._lock:
            if self._state['status'] != 'completed':
                raise ProjectError(self._state['error'] or '語音工作尚未成功完成。')
            return deepcopy(self._result)

    def cancel(self):
        with self._lock:
            if self._state['status'] != 'running':
                return
            self._cancel.set()
            self._state['status'] = 'cancelling'
            if self._loop is not None and self._task is not None:
                try:
                    self._loop.call_soon_threadsafe(self._task.cancel)
                except RuntimeError:
                    pass  # The operation finished while the event loop was closing.

    def wait(self, timeout=None) -> bool:
        self._thread.join(timeout)
        return not self._thread.is_alive()

    def _run(self):
        async def run():
            with self._lock:
                self._loop = asyncio.get_running_loop()
                self._task = asyncio.current_task()
            if self._cancel.is_set():
                raise asyncio.CancelledError()
            return await asyncio.wait_for(self._operation(), self._timeout)
        status, error, result = 'completed', '', None
        try:
            result = asyncio.run(run())
        except asyncio.CancelledError:
            status = 'cancelled'
        except ProjectError as exc:
            status, error = 'failed', str(exc)
        except Exception:
            status, error = 'failed', 'Edge-TTS 網路或服務錯誤。請檢查連線、更新音色後重試；不會自動換聲，仍可校對。'
        with self._lock:
            if self._cancel.is_set():
                status, result = 'cancelled', None
            self._loop = self._task = None
            self._state.update(status=status, error=error)
            self._result = result


def refresh() -> VoiceJob:
    async def operation():
        raw = await edge_module().list_voices()
        voices = [dict(id=v['ShortName'], name=v.get('FriendlyName') or v['Name'],
                       locale=v['Locale'], gender=v.get('Gender') or '未提供') for v in raw]
        if not voices or len({v['id'] for v in voices}) != len(voices):
            raise ProjectError('線上音色清單為空或損壞，請稍後重試。舊快取保留。')
        if any(not all(isinstance(v[k], str) and v[k] for k in v) for v in voices):
            raise ProjectError('線上音色資料不完整，請稍後重試。舊快取保留。')
        value = dict(voices=voices, updated_at=now())
        path = cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
                temporary = Path(f.name)
                f.write(json.dumps(value, ensure_ascii=False).encode('utf-8'))
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary, path)
        except OSError:
            raise ProjectError('無法儲存音色快取，請檢查本機設定資料夾權限。') from None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return value
    return VoiceJob(operation)
