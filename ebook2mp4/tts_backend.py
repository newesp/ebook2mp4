"""Built-in speech service policies and the single-block transport boundary."""
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .workflow import ProjectError


@dataclass(frozen=True, slots=True)
class ServiceCapabilities:
    execution: Literal['cloud', 'local']
    voice_source: Literal['online-catalog', 'service-or-manual', 'manual', 'package']
    request_escaped_utf8_bytes: int
    load_timeout_seconds: float | None
    synthesis_timeout_seconds: float
    max_attempts: int

    @property
    def requires_network(self) -> bool:
        return self.execution == 'cloud'


# A local capability alone does not mean its optional package is installed.
_SERVICES = {
    'edge-tts': ServiceCapabilities('cloud', 'online-catalog', 3000, None, 90, 3),
    'gemini-tts': ServiceCapabilities('cloud', 'service-or-manual', 3000, None, 90, 3),
    'fish-audio': ServiceCapabilities('cloud', 'manual', 3000, None, 90, 3),
    'kokoro': ServiceCapabilities('local','package',240,300,180,1),
}


def capabilities(provider: str) -> ServiceCapabilities:
    try:
        return _SERVICES[provider]
    except KeyError:
        raise ProjectError('語音服務尚未支援；請明確選擇已安裝且可用的服務。') from None


async def write_speech(text: str, settings: dict, target: Path):
    """Receive one original audio block; callers own caching, decode and publish."""
    capabilities(settings['provider'])
    if settings['provider']=='kokoro':
        from .kokoro_runtime import engine
        await engine().synthesize(text,settings,target)
        return
    if settings['provider'] != 'edge-tts':
        from .tts_services import request_audio
        target.write_bytes(await request_audio(text, settings))
        return
    from .voice import edge_module
    size = 0
    with target.open('wb') as stream:
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
