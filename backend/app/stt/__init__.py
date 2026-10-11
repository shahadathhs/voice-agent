import asyncio
import time

import numpy as np
from faster_whisper import WhisperModel

from app.core.config import get_settings
from app.core.logger import logger


class TranscriptionResult:
    __slots__ = ("text", "elapsed_ms", "audio_ms", "language")

    def __init__(self, text: str, elapsed_ms: float, audio_ms: float, language: str | None):
        self.text = text
        self.elapsed_ms = elapsed_ms
        self.audio_ms = audio_ms
        self.language = language


class WhisperSTT:
    def __init__(self) -> None:
        self._model: WhisperModel | None = None
        self._load_lock = asyncio.Lock()
        self._infer_lock = asyncio.Lock()

    @property
    def loaded(self) -> bool:
        return self._model is not None

    async def get_model(self) -> WhisperModel:
        if self._model is None:
            async with self._load_lock:
                if self._model is None:
                    self._model = await self._load()
        return self._model

    async def _load(self) -> WhisperModel:
        settings = get_settings()
        logger.info(
            f"Loading Whisper model '{settings.whisper_model}' "
            f"(device={settings.whisper_device}, compute={settings.whisper_compute_type})..."
        )
        start = time.perf_counter()
        model = await asyncio.to_thread(
            WhisperModel,
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
        logger.info(f"Whisper model loaded in {time.perf_counter() - start:.1f}s")
        return model

    async def transcribe(self, pcm16: bytes, sample_rate: int = 16000) -> TranscriptionResult:
        audio_ms = len(pcm16) / 2 / sample_rate * 1000
        audio = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) / 32768.0

        model = await self.get_model()
        async with self._infer_lock:
            start = time.perf_counter()
            segments, info = await asyncio.to_thread(
                model.transcribe,
                audio,
                beam_size=1,
                language=None,
                condition_on_previous_text=False,
                vad_filter=False,
            )
            text = " ".join(segment.text.strip() for segment in segments).strip()

        elapsed_ms = (time.perf_counter() - start) * 1000
        return TranscriptionResult(text, elapsed_ms, audio_ms, info.language)
