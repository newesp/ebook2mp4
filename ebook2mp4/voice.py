"""Edge service adapter, cancellable work, and shared narration settings."""
from __future__ import annotations

import asyncio
from copy import deepcopy
import json
import os
import re
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
    local=isinstance(value,dict) and value.get('provider')=='kokoro'
    allowed=(set(DEFAULT_SETTINGS)|{'model','package'},) if local else (set(DEFAULT_SETTINGS),set(DEFAULT_SETTINGS)|{'model','profile'})
    if (not isinstance(value, dict) or set(value) not in allowed
            or value['provider'] not in ('edge-tts', 'gemini-tts', 'fish-audio','kokoro') or not isinstance(value['voice'], str)
            or value['rate'] not in RATES or value['processing'] != ('kokoro-t2s-v1' if local else 'identity-v1')
            or type(value['sentence_pause_ms']) is not int or not 0 <= value['sentence_pause_ms'] <= 1500
            or type(value['paragraph_pause_ms']) is not int or not 0 <= value['paragraph_pause_ms'] <= 3000):
        raise ProjectError('語音設定無效。句尾須為 0～1,500 ms；段落須為 0～3,000 ms。')
    if local:
        if (not isinstance(value.get('package'),str) or not re.fullmatch(r'kokoro-zh-cpu-[0-9a-f]{16}',value['package'])
                or not isinstance(value.get('model'),str) or not re.fullmatch(r'[0-9a-f]{40}',value['model'])):
            raise ProjectError('本機語音包版本設定無效，請重新選擇語音包。')
    elif value['provider'] != 'edge-tts':
        from .tts_services import validate_model
        validate_model(value.get('model'))
        if value['provider']=='fish-audio' and value.get('model') not in ('s2.1-pro','s2.1-pro-free'):
            raise ProjectError('Fish 模型尚未驗證；請選 s2.1-pro 或 s2.1-pro-free，避免服務自動換模型。')
        if not isinstance(value.get('profile'), str) or not value['profile']:
            raise ProjectError('請選擇 TTS 服務設定檔。')
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


def require_voice(voice: str, value=None):
    if value and value['provider']=='kokoro':
        from .kokoro_packages import package
        _,metadata=package(value['package'])
        if metadata['model']!=value['model'] or metadata['processing']!=value['processing']:
            raise ProjectError('語音包模型或處理版本不符，請匯入專案所需版本。')
        if voice not in {v['id'] for v in metadata['voices']}:
            raise ProjectError('本機音色不存在，請從已安裝語音包重新選擇音色。')
        return
    if value and value['provider'] != 'edge-tts':
        if not isinstance(voice, str) or not voice.strip() or any(ord(c)<32 for c in voice):
            raise ProjectError('請選擇或輸入音色 ID。')
        from .tts_services import credential
        credential(value)
        return
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
        error_details={}
        try:
            result = asyncio.run(run())
        except asyncio.CancelledError:
            status = 'cancelled'
        except ProjectError as exc:
            status, error = 'failed', str(exc)
            if hasattr(exc,'category'):error_details['error_category']=exc.category
        except Exception:
            status, error = 'failed', 'TTS 網路或服務錯誤。請檢查連線及服務設定；不會自動換聲，仍可校對。'
        with self._lock:
            if self._cancel.is_set():
                status, result = 'cancelled', None
            self._loop = self._task = None
            self._state.update(status=status, error=error)
            self._state.update(error_details)
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
