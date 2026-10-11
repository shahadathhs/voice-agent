import asyncio

from app.llm import GroqClient
from app.stt import WhisperSTT
from app.tts import KokoroTTS
from app.vad import SileroVAD

stt = WhisperSTT()
tts = KokoroTTS()
llm = GroqClient()

_vad: SileroVAD | None = None
_vad_lock = asyncio.Lock()


async def get_vad() -> SileroVAD:
    global _vad
    if _vad is None:
        async with _vad_lock:
            if _vad is None:
                _vad = await SileroVAD.create()
    return _vad
