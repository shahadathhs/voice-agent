import asyncio
import time

import numpy as np
from kokoro_onnx import Kokoro

from app.core.config import get_settings
from app.core.logger import logger
from app.core.models import KOKORO_BASE_URL, KOKORO_MODEL, KOKORO_VOICES, ensure_model


class KokoroTTS:
    def __init__(self) -> None:
        self._tts: Kokoro | None = None
        self._load_lock = asyncio.Lock()
        self._infer_lock = asyncio.Lock()

    @property
    def loaded(self) -> bool:
        return self._tts is not None

    async def ensure_loaded(self) -> None:
        if self._tts is None:
            await self._load()

    async def _load(self) -> Kokoro:
        async with self._load_lock:
            if self._tts is None:
                logger.info("Loading Kokoro TTS model...")
                start = time.perf_counter()

                def build() -> Kokoro:
                    model = ensure_model(KOKORO_MODEL, f"{KOKORO_BASE_URL}/{KOKORO_MODEL}")
                    voices = ensure_model(KOKORO_VOICES, f"{KOKORO_BASE_URL}/{KOKORO_VOICES}")
                    return Kokoro(str(model), str(voices))

                self._tts = await asyncio.to_thread(build)
                logger.info(f"Kokoro TTS loaded in {time.perf_counter() - start:.1f}s")
        return self._tts

    async def synth(self, text: str) -> tuple[np.ndarray, int]:
        settings = get_settings()
        tts = self._tts if self._tts is not None else await self._load()
        async with self._infer_lock:
            samples, sample_rate = await asyncio.to_thread(
                tts.create,
                text,
                settings.tts_voice,
                settings.tts_speed,
                settings.tts_lang,
            )
        audio = np.asarray(samples, dtype=np.float32).clip(-1.0, 1.0)
        return audio, int(sample_rate)
