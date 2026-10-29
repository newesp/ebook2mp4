"""Local TTS profiles and cancellable provider transports; no credentials in projects."""
import base64
import json
import re
from .workflow import ProjectError, ProjectWorkflow, encode

class RetryableServiceError(ProjectError):
    def __init__(self, message, retry_after=0):
        super().__init__(message)
        self.retry_after=retry_after


MODELS = ('gemini-3.8-flash-lite-tts', 'gemini-3.8-flash-tts')
VOICES = ('Kore', 'Puck', 'Charon', 'Aoede', 'Fenrir', 'Zephyr')


def profiles():
    from .voice import cache_path
    path = cache_path().parent / 'services.json'
    try:
        value = json.loads(path.read_bytes()) if path.exists() else {}
        if not isinstance(value, dict): raise ValueError()
        return value
    except (OSError, ValueError):
        raise ProjectError('TTS 服務設定損壞，請還原本機設定備份。') from None


def save_profile(name, provider, key='', reuse=False, profile_id=None):
    import uuid
    from .voice import cache_path
    from .gemini import protect
    if provider not in ('gemini-tts', 'fish-audio') or not name.strip():
        raise ProjectError('請填服務名稱並選擇服務類型。')
    if '\n' in key or '\r' in key: raise ProjectError('金鑰不可含換行。')
    values = profiles()
    identity = profile_id or uuid.uuid4().hex
    previous = values.get(identity, {})
    if previous and previous.get('provider') != provider:
        raise ProjectError('既有設定檔不能更換服務類型；請新增設定檔並填入該服務金鑰。')
    protected = base64.b64encode(protect(key.strip().encode())).decode() if key.strip() else previous.get('key', '')
    if not protected and not (reuse and provider == 'gemini-tts'):
        raise ProjectError('請輸入 API 金鑰。')
    values[identity] = dict(name=name.strip(), provider=provider, key=protected,
                            reuse=bool(reuse and provider == 'gemini-tts'))
    ProjectWorkflow._atomic(cache_path().parent / 'services.json', encode(values))
    return identity


def credential(value):
    from .gemini import protect, load_settings
    profile = profiles().get(value.get('profile', ''))
    if not profile or profile.get('provider') != value['provider']:
        raise ProjectError('本機尚未設定此 TTS 服務，請在管理服務重新連結金鑰。')
    if profile.get('reuse'):
        key = load_settings()['key']
    else:
        try: key = protect(base64.b64decode(profile['key']), decrypt=True).decode()
        except (KeyError, ValueError): raise ProjectError('無法讀取 TTS 金鑰，請重新設定。') from None
    if not key: raise ProjectError('缺少 TTS 金鑰，請在管理服務設定。')
    return key


def validate_model(model):
    if not isinstance(model, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,199}', model):
        raise ProjectError('請填有效模型 ID；可直接輸入未來的新模型名稱。')


async def request_audio(text, value):
    import aiohttp
    key = credential(value)
    if value['provider'] == 'gemini-tts':
        url = 'https://generativelanguage.googleapis.com/v1beta/interactions'
        headers = {'x-goog-api-key': key}
        speed = 1 + int(value['rate'].strip('%')) / 100
        body = dict(model=value['model'], input=[dict(type='user_input', content=[dict(type='text', text=text,
            annotations=[dict(type='speech_metadata', style=f'Read the transcript verbatim at {speed:g} times normal speaking speed.')])])],
            response_format=dict(type='audio'), generation_config=dict(speech_config=[dict(voice=value['voice'])]))
    else:
        url = 'https://api.fish.audio/v1/tts'
        headers = {'Authorization': 'Bearer '+key, 'model': value['model']}
        body = dict(text=text, reference_id=value['voice'], format='wav', normalize=False,
                    prosody=dict(speed=1+int(value['rate'].strip('%'))/100))
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=90)) as session:
        async with session.post(url, headers=headers, json=body) as response:
            if response.status != 200:
                status = response.status
                reasons = {400:'請求或模型設定不支援',401:'金鑰無效',402:'帳戶額度不足',403:'無權限或帳務未啟用',
                           404:'模型或音色不存在',429:'請求過多或配額不足，請稍後再試'}
                error_type=RetryableServiceError if status==429 or status>=500 else ProjectError
                if error_type is RetryableServiceError:
                    delay=response.headers.get('Retry-After','0')
                    try: seconds=max(0,float(delay))
                    except ValueError:
                        from email.utils import parsedate_to_datetime
                        from datetime import datetime, timezone
                        try: seconds=max(0,(parsedate_to_datetime(delay)-datetime.now(timezone.utc)).total_seconds())
                        except (ValueError,TypeError,OverflowError): seconds=0
                    if seconds>60: raise ProjectError('服務要求等待超過60秒，請稍後重試。')
                    raise RetryableServiceError(f'TTS HTTP {status}：服務暫時不可用，請稍後重試。',seconds)
                raise ProjectError(f'TTS HTTP {status}：{reasons.get(status, "服務暫時故障，請稍後重試")}；不會自動換模型或服務。')
            data = bytearray()
            async for block in response.content.iter_chunked(65536):
                data.extend(block)
                if len(data) > 40_000_000: raise ProjectError('TTS 回應過大，請縮短稿件。')
    if value['provider'] == 'gemini-tts':
        try:
            result = json.loads(data)
            audio = [item for step in result['steps'] if step.get('type') == 'model_output'
                     for item in step.get('content', []) if item.get('type') == 'audio']
            if not audio: raise ValueError()
            data = bytearray(base64.b64decode(audio[-1]['data'], validate=True))
        except (ValueError, KeyError, TypeError):
            raise ProjectError('Gemini 未回傳有效音訊；請檢查模型與音色。') from None
    if not data: raise ProjectError('TTS 回傳空音訊。')
    return bytes(data)


async def check_profile(identity):
    import aiohttp
    profile=profiles()[identity]
    value=dict(provider=profile['provider'],profile=identity)
    key=credential(value)
    google=profile['provider']=='gemini-tts'
    url='https://generativelanguage.googleapis.com/v1beta/voices' if google else 'https://api.fish.audio/model'
    headers={'x-goog-api-key':key} if google else {'Authorization':'Bearer '+key}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=25)) as session:
        async with session.get(url,headers=headers) as response:
            if response.status!=200:raise ProjectError(f'服務檢查 HTTP {response.status}；請核對金鑰、權限與額度。')
            data=bytearray()
            async for block in response.content.iter_chunked(65536):
                data.extend(block)
                if len(data)>2_000_000:raise ProjectError('音色清單過大。')
            try:
                result=json.loads(data)
                if not isinstance(result,dict):raise ValueError()
            except ValueError:raise ProjectError('音色清單格式無法辨識。') from None
    return '連線檢查通過；請返回並用短文試聽驗證模型及音色。'
